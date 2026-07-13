import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .strict_json import dump, load


@dataclass
class JsonDocument:
    path: Path
    data: Any

    @classmethod
    def load(cls, path: str | Path, *, allow_duplicate_keys: bool = False) -> "JsonDocument":
        doc_path = Path(path).expanduser()
        with doc_path.open("r", encoding="utf-8") as handle:
            data = load(handle, allow_duplicate_keys=allow_duplicate_keys)
        return cls(doc_path, data)

    def backup(self) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = self.path.with_name(f"{self.path.name}.bak_{timestamp}")
        suffix = 1
        while backup_path.exists():
            backup_path = self.path.with_name(f"{self.path.name}.bak_{timestamp}_{suffix}")
            suffix += 1
        shutil.copy2(self.path, backup_path)
        return backup_path

    def save(self, backup: bool = True) -> Path | None:
        if self.path.is_symlink():
            raise ValueError("Refusing to replace symlink; edit the target path directly")

        original_stat = self.path.stat() if self.path.exists() else None
        backup_path = self.backup() if backup and self.path.exists() else None
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

            if original_stat is not None:
                shutil.copystat(self.path, tmp_path)
                os.chmod(tmp_path, original_stat.st_mode)

            os.replace(tmp_path, self.path)
            dir_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            raise
        return backup_path

    def root_keys(self) -> list[str]:
        if isinstance(self.data, dict):
            return list(self.data.keys())
        if isinstance(self.data, list):
            return [str(i) for i in range(len(self.data))]
        return []
