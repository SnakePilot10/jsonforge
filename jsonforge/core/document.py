import hashlib
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .strict_json import dump, load, loads


@dataclass(frozen=True)
class FileSnapshot:
    st_dev: int
    st_ino: int
    st_size: int
    st_mtime_ns: int
    st_ctime_ns: int
    st_mode: int
    content_hash: str | None = None

    @classmethod
    def from_stat(
        cls,
        stat_result: os.stat_result,
        content_hash: str | None = None,
    ) -> "FileSnapshot":
        return cls(
            st_dev=stat_result.st_dev,
            st_ino=stat_result.st_ino,
            st_size=stat_result.st_size,
            st_mtime_ns=stat_result.st_mtime_ns,
            st_ctime_ns=stat_result.st_ctime_ns,
            st_mode=stat_result.st_mode,
            content_hash=content_hash,
        )

    def matches(self, stat_result: os.stat_result) -> bool:
        current = self.from_stat(stat_result, self.content_hash)
        return self == current


@dataclass(frozen=True)
class SaveResult:
    backup_path: Path | None
    replaced: bool
    durability_confirmed: bool


class ConcurrentModificationError(RuntimeError):
    pass


@dataclass
class JsonDocument:
    path: Path
    data: Any
    snapshot: FileSnapshot | None = None

    @classmethod
    def load(cls, path: str | Path, *, allow_duplicate_keys: bool = False) -> "JsonDocument":
        doc_path = Path(path).expanduser()
        with doc_path.open("rb") as handle:
            before = FileSnapshot.from_stat(os.fstat(handle.fileno()))
            raw_data = handle.read()
            after = FileSnapshot.from_stat(os.fstat(handle.fileno()))
        if before != after:
            raise ConcurrentModificationError("File changed while it was being loaded")
        text = raw_data.decode("utf-8")
        data = loads(text, allow_duplicate_keys=allow_duplicate_keys)
        snapshot = FileSnapshot.from_stat(
            doc_path.stat(),
            hashlib.sha256(raw_data).hexdigest(),
        )
        return cls(doc_path, data, snapshot)

    def backup(self, snapshot: FileSnapshot | None = None) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        suffix = 1
        while True:
            suffix_text = "" if suffix == 1 else f"_{suffix - 1}"
            backup_path = self.path.with_name(f"{self.path.name}.bak_{timestamp}{suffix_text}")
            try:
                return self._copy_backup_exclusive(backup_path, snapshot)
            except FileExistsError:
                suffix += 1

    def _copy_backup_exclusive(
        self,
        backup_path: Path,
        snapshot: FileSnapshot | None,
    ) -> Path:
        try:
            with backup_path.open("xb") as destination:
                if snapshot is not None:
                    os.fchmod(destination.fileno(), snapshot.st_mode & 0o7777)
                with self.path.open("rb") as source:
                    before = FileSnapshot.from_stat(os.fstat(source.fileno()))
                    file_hash = hashlib.sha256()
                    while chunk := source.read(1024 * 1024):
                        file_hash.update(chunk)
                        destination.write(chunk)
                    after = FileSnapshot.from_stat(os.fstat(source.fileno()))
                copied_snapshot = FileSnapshot.from_stat(after, file_hash.hexdigest())
                if before != after or (snapshot is not None and copied_snapshot != snapshot):
                    raise ConcurrentModificationError("File changed while backup was being created")
                destination.flush()
                os.fsync(destination.fileno())
        except FileExistsError:
            raise
        except Exception:
            try:
                backup_path.unlink()
            except FileNotFoundError:
                pass
            raise
        return backup_path

    def save(self, backup: bool = True, *, force_write: bool = False) -> SaveResult:
        if self.path.is_symlink():
            raise ValueError("Refusing to replace symlink; edit the target path directly")

        current_snapshot = self._snapshot_path() if self.path.exists() else None
        if current_snapshot is not None and self.snapshot is not None:
            if self.snapshot != current_snapshot and not force_write:
                raise ConcurrentModificationError("File changed since it was loaded")
        backup_path = (
            self.backup(current_snapshot)
            if backup and current_snapshot is not None
            else None
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
            text=True,
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                dump(self.data, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            with tmp_path.open("r", encoding="utf-8") as handle:
                load(handle)

            if current_snapshot is not None and not force_write:
                if self._snapshot_path() != current_snapshot:
                    raise ConcurrentModificationError("File changed before replacement")

            if current_snapshot is not None:
                os.chmod(tmp_path, current_snapshot.st_mode & 0o7777)

            os.replace(tmp_path, self.path)
            durability_confirmed = sync_parent_directory(self.path)
        except Exception:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            raise
        self.snapshot = self._snapshot_path()
        return SaveResult(
            backup_path=backup_path,
            replaced=True,
            durability_confirmed=durability_confirmed,
        )

    def root_keys(self) -> list[str]:
        if isinstance(self.data, dict):
            return list(self.data.keys())
        if isinstance(self.data, list):
            return [str(i) for i in range(len(self.data))]
        return []

    def _snapshot_path(self) -> FileSnapshot:
        with self.path.open("rb") as handle:
            before = FileSnapshot.from_stat(os.fstat(handle.fileno()))
            file_hash = hashlib.sha256()
            while chunk := handle.read(1024 * 1024):
                file_hash.update(chunk)
            after = FileSnapshot.from_stat(os.fstat(handle.fileno()))
        if before != after:
            raise ConcurrentModificationError("File changed while it was being inspected")
        return FileSnapshot.from_stat(self.path.stat(), file_hash.hexdigest())


def sync_parent_directory(path: Path) -> bool:
    try:
        dir_fd = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return False
    try:
        os.fsync(dir_fd)
    except OSError:
        return False
    finally:
        os.close(dir_fd)
    return True
