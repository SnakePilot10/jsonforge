import json
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class JsonDocument:
    path: Path
    data: Any

    @classmethod
    def load(cls, path: str | Path) -> "JsonDocument":
        doc_path = Path(path).expanduser()
        with doc_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
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
                json.dump(self.data, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            with tmp_path.open("r", encoding="utf-8") as handle:
                json.load(handle)

            os.replace(tmp_path, self.path)
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
