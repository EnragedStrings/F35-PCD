from __future__ import annotations

import shutil
import textwrap
import zipfile
from pathlib import Path
from typing import List, Set

PMD_PLUGIN_ARCHIVE_EXTS: Set[str] = {".pmd", ".zip"}


def sanitize_pmd_id(value: object) -> str:
    raw = str(value).strip()
    if raw == "":
        return ""
    cleaned = "".join(ch if (ch.isalnum() or ch in {"-", "_"}) else "_" for ch in raw)
    cleaned = cleaned.strip("._-")
    return cleaned[:64]


def pmd_wrap_text(text: object, max_len: int, max_lines: int) -> List[str]:
    raw = str(text).strip()
    if raw == "":
        return [""]
    wrapped = textwrap.wrap(raw, width=max(1, int(max_len)), break_long_words=True, break_on_hyphens=False)
    if len(wrapped) <= max_lines:
        return wrapped
    out = list(wrapped[: max(1, int(max_lines))])
    if len(out[-1]) >= 1:
        out[-1] = out[-1][:-1] + "."
    return out


def pmd_extract_archive(archive_path: Path, target_dir: Path) -> bool:
    if not archive_path.exists():
        return False
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    try:
        with zipfile.ZipFile(str(archive_path), "r") as zf:
            base = target_dir.resolve()
            for info in zf.infolist():
                member = str(info.filename).replace("\\", "/")
                if member.startswith("/") or ".." in Path(member).parts:
                    continue
                out_path = (base / member).resolve()
                if not str(out_path).startswith(str(base)):
                    continue
                if info.is_dir():
                    out_path.mkdir(parents=True, exist_ok=True)
                    continue
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        return True
    except Exception:
        return False
