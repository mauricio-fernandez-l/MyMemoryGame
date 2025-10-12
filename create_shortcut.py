#!/usr/bin/env python
"""Create a desktop shortcut for the Memory game using settings from config.yaml."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import subprocess
import sys
from pathlib import Path
from typing import Iterable
from uuid import UUID

import yaml
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
MEMORY_SCRIPT = BASE_DIR / "memory.py"
DESKTOP_FALLBACK = Path.home() / "Desktop"
KNOWN_FOLDER_DESKTOP = "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}"
INVALID_FILENAME_CHARS = set('<>:"/\\|?*')
INVALID_FILENAME_CHARS.add("\0")


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_uuid(cls, uuid_obj: UUID) -> "GUID":
        data = uuid_obj.bytes_le
        data4 = (ctypes.c_ubyte * 8).from_buffer_copy(data[8:])
        return cls(
            int.from_bytes(data[0:4], byteorder="little"),
            int.from_bytes(data[4:6], byteorder="little"),
            int.from_bytes(data[6:8], byteorder="little"),
            data4,
        )


def sanitize_filename(name: str) -> str:
    cleaned = ["_" if ch in INVALID_FILENAME_CHARS else ch for ch in name]
    normalized = "".join(cleaned).strip()
    return normalized or "Memory"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file) or {}


def resolve_path(path_value: str | None) -> Path:
    if not path_value:
        raise FileNotFoundError("shortcut image path is not configured")
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    candidate = candidate.expanduser().resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"Icon image not found: {candidate}")
    if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError(
            f"Shortcut image must be a .png, .jpg, or .jpeg file: {candidate}"
        )
    return candidate


def get_desktop_path() -> Path:
    if sys.platform != "win32":
        return DESKTOP_FALLBACK

    try:
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.LPWSTR),
        ]
        SHGetKnownFolderPath.restype = wintypes.HRESULT

        folder_id = GUID.from_uuid(UUID(KNOWN_FOLDER_DESKTOP))
        p_path = wintypes.LPWSTR()
        result = SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, None, ctypes.byref(p_path)
        )
        if result == 0 and p_path.value:
            path = Path(p_path.value)
            try:
                buffer_ptr = ctypes.cast(p_path, ctypes.c_void_p)
                if buffer_ptr:
                    ctypes.windll.ole32.CoTaskMemFree(buffer_ptr)
            except Exception:
                pass
            if path.exists():
                return path
    except Exception:
        pass

    return DESKTOP_FALLBACK


def find_python_executable() -> Path:
    candidates: Iterable[Path] = [
        BASE_DIR / ".venv" / "Scripts" / "pythonw.exe",
        BASE_DIR / ".venv" / "Scripts" / "python.exe",
    ]

    executable = Path(sys.executable)
    candidates = list(candidates)
    if executable.exists():
        candidates.append(executable)
        pythonw = executable.with_name("pythonw.exe")
        candidates.append(pythonw)

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    return executable.resolve()


def convert_image_to_ico(image_path: Path, ico_path: Path) -> Path:
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(image_path) as img:
        img = img.convert("RGBA")
        max_dim = max(img.size)
        base_sizes = [256, 128, 96, 64, 48, 32, 24, 16]
        sizes = [(size, size) for size in base_sizes if size <= max_dim]
        if not sizes:
            sizes = [(max_dim, max_dim)]
        img.save(ico_path, format="ICO", sizes=sizes)
    return ico_path


def escape_for_powershell(value: str) -> str:
    return value.replace("`", "``").replace('"', '""')


def create_shortcut(
    shortcut_path: Path, target_executable: Path, working_dir: Path, icon_path: Path
) -> None:
    arguments = f'"{str(MEMORY_SCRIPT)}"'
    ps_lines = [
        "$shell = New-Object -ComObject WScript.Shell",
        f'$shortcut = $shell.CreateShortcut("{escape_for_powershell(str(shortcut_path))}")',
        f'$shortcut.TargetPath = "{escape_for_powershell(str(target_executable))}"',
        f'$shortcut.Arguments = "{escape_for_powershell(arguments)}"',
        f'$shortcut.WorkingDirectory = "{escape_for_powershell(str(working_dir))}"',
        f'$shortcut.IconLocation = "{escape_for_powershell(str(icon_path))}"',
        "$shortcut.Save()",
    ]
    ps_script = "\n".join(ps_lines)

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "Failed to create shortcut."
            + f"\nSTDOUT: {completed.stdout or '[no output]'}"
            + f"\nSTDERR: {completed.stderr or '[no output]'}"
        )


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Shortcut creation is only supported on Windows.")

    config = load_config()
    title_cfg = config.get("title", {})
    shortcut_cfg = config.get("shortcut", {})

    shortcut_name = title_cfg.get("text", "Memory")
    image_path = resolve_path(shortcut_cfg.get("image"))

    python_executable = find_python_executable()
    if not python_executable.exists():
        raise SystemExit(f"Python executable not found: {python_executable}")

    working_dir = MEMORY_SCRIPT.parent
    shortcut_path = get_desktop_path() / f"{sanitize_filename(shortcut_name)}.lnk"
    icon_path = BASE_DIR / "icons" / f"{sanitize_filename(shortcut_name)}.ico"

    convert_image_to_ico(image_path, icon_path)
    create_shortcut(shortcut_path, python_executable, working_dir, icon_path)

    print(f"Shortcut created: {shortcut_path}")
    print(f"Icon stored at: {icon_path}")
    print(f"Target will run: {python_executable} {MEMORY_SCRIPT}")


if __name__ == "__main__":
    main()
