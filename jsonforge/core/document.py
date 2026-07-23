import hashlib
import os
import stat
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
    st_uid: int
    st_gid: int
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
            st_uid=stat_result.st_uid,
            st_gid=stat_result.st_gid,
            content_hash=content_hash,
        )

    def matches_stat(self, stat_result: os.stat_result) -> bool:
        current = self.from_stat(stat_result, self.content_hash)
        return self == current


@dataclass(frozen=True)
class ReadStabilitySignature:
    st_dev: int
    st_ino: int
    st_size: int
    st_mtime_ns: int

    @classmethod
    def from_stat(cls, stat_result: os.stat_result) -> "ReadStabilitySignature":
        return cls(
            st_dev=stat_result.st_dev,
            st_ino=stat_result.st_ino,
            st_size=stat_result.st_size,
            st_mtime_ns=stat_result.st_mtime_ns,
        )


@dataclass(frozen=True)
class SaveResult:
    backup_path: Path | None
    replaced: bool
    durability_confirmed: bool
    snapshot_confirmed: bool


class ConcurrentModificationError(RuntimeError):
    pass


@dataclass
class JsonDocument:
    path: Path
    data: Any
    snapshot: FileSnapshot | None = None
    max_bytes: int | None = None

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        allow_duplicate_keys: bool = False,
        max_bytes: int | None = None,
    ) -> "JsonDocument":
        doc_path = Path(path).expanduser()
        raw_data, stable_stat = read_stable_bytes(
            doc_path,
            error_message="File remained unstable across multiple load attempts",
            max_bytes=max_bytes,
        )
        text = raw_data.decode("utf-8")
        try:
            data = loads(text, allow_duplicate_keys=allow_duplicate_keys)
        except RecursionError as exc:
            raise ValueError("JSON nesting exceeds the parser depth limit") from exc
        snapshot = FileSnapshot.from_stat(
            stable_stat,
            hashlib.sha256(raw_data).hexdigest(),
        )
        return cls(doc_path, data, snapshot, max_bytes)

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
                    preserve_file_ownership(destination.fileno(), snapshot)
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
        ensure_not_symlink(self.path)

        current_snapshot = self._snapshot_path_or_none()
        if not force_write and self.snapshot != current_snapshot:
            if self.snapshot is not None and current_snapshot is None:
                message = "File was deleted since it was loaded"
            elif self.snapshot is None:
                message = "File already exists and was not loaded by this document"
            else:
                message = "File changed since it was loaded"
            raise ConcurrentModificationError(message)
        backup_path = (
            self.backup(current_snapshot) if backup and current_snapshot is not None else None
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
                try:
                    dump(self.data, handle, indent=2, ensure_ascii=False)
                except RecursionError as exc:
                    raise ValueError("JSON nesting exceeds the serializer depth limit") from exc
                handle.write("\n")
                handle.flush()
                if (
                    self.max_bytes is not None
                    and os.fstat(handle.fileno()).st_size > self.max_bytes
                ):
                    raise ValueError(f"JSON output exceeds the {self.max_bytes}-byte limit")
                if current_snapshot is not None:
                    preserve_file_ownership(handle.fileno(), current_snapshot)
                    os.fchmod(handle.fileno(), current_snapshot.st_mode & 0o7777)
                os.fsync(handle.fileno())

            with tmp_path.open("r", encoding="utf-8") as handle:
                load(handle)

            if not force_write:
                if self._snapshot_path_or_none() != current_snapshot:
                    raise ConcurrentModificationError("File changed before replacement")

            ensure_not_symlink(self.path)
            os.replace(tmp_path, self.path)
            durability_confirmed = sync_parent_directory(self.path)
        except Exception:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            raise
        try:
            self.snapshot = self._snapshot_path()
        except (OSError, ConcurrentModificationError):
            return SaveResult(
                backup_path=backup_path,
                replaced=True,
                durability_confirmed=durability_confirmed,
                snapshot_confirmed=False,
            )
        return SaveResult(
            backup_path=backup_path,
            replaced=True,
            durability_confirmed=durability_confirmed,
            snapshot_confirmed=True,
        )

    def root_keys(self) -> list[str]:
        if isinstance(self.data, dict):
            return list(self.data.keys())
        if isinstance(self.data, list):
            return [str(i) for i in range(len(self.data))]
        return []

    def _snapshot_path(self) -> FileSnapshot:
        raw_data, stable_stat = read_stable_bytes(
            self.path,
            error_message="File remained unstable while it was being inspected",
            max_bytes=self.max_bytes,
        )
        return FileSnapshot.from_stat(stable_stat, hashlib.sha256(raw_data).hexdigest())

    def _snapshot_path_or_none(self) -> FileSnapshot | None:
        try:
            return self._snapshot_path()
        except FileNotFoundError:
            return None


def read_stable_bytes(
    path: Path,
    *,
    error_message: str,
    attempts: int = 3,
    max_bytes: int | None = None,
) -> tuple[bytes, os.stat_result]:
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("Maximum file size must not be negative")
    for attempt in range(attempts):
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            raw_data = handle.read() if max_bytes is None else handle.read(max_bytes + 1)
            after = os.fstat(handle.fileno())
        if max_bytes is not None and len(raw_data) > max_bytes:
            raise ValueError(f"JSON file exceeds the {max_bytes}-byte limit")
        if ReadStabilitySignature.from_stat(before) == ReadStabilitySignature.from_stat(after):
            return raw_data, after
        if attempt + 1 < attempts:
            time.sleep(0.01 * (2**attempt))
    raise ConcurrentModificationError(error_message)


def ensure_not_symlink(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode):
        raise ValueError("Refusing to replace symlink; edit the target path directly")


def preserve_file_ownership(fd: int, snapshot: FileSnapshot) -> None:
    current = os.fstat(fd)
    if current.st_uid == snapshot.st_uid and current.st_gid == snapshot.st_gid:
        return
    if not hasattr(os, "fchown"):
        raise OSError("Cannot preserve file ownership on this platform")
    os.fchown(fd, snapshot.st_uid, snapshot.st_gid)
    updated = os.fstat(fd)
    if updated.st_uid != snapshot.st_uid or updated.st_gid != snapshot.st_gid:
        raise OSError("File ownership could not be preserved")


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
