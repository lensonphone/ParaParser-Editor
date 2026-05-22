import os
import re  
from typing import Sequence, Any, Optional

# ── Imports of your modules (with fallback to local ones) ──────────────────────
import Code.Parsers.LegacyChromatix.LibchromatixLoader as LegacyMX
import Code.Parsers.ParaParser_1to6._QTIParameterReader as MX


def _disable_txt_export_if_present() -> None:
    """Disables TXT export for MX if such flags exist.."""
    try:
        if hasattr(MX, 'AllowExportTxt'):
            MX.AllowExportTxt = 0
    except Exception:
        pass
    try:
        if MX is not None and hasattr(MX, 'AllowExportTxt'):
            MX.AllowExportTxt = 0
    except Exception:
        pass


def _read_file_slice(path: str, offset: int, size: int) -> bytes:
    with open(path, 'rb') as f:
        f.seek(offset)
        return f.read(size)


def _is_legacy_so_by_sniff(path: str) -> bool:
    """
        A quick sniff for .so: look for 'load_chromatix' (case insensitive)
        in the first ~2 MB. Older libchromatixes usually contain it.
    """
    try:
        with open(path, "rb") as f:
            sniff = f.read(2 * 1024 * 1024)
        return b"load_chromatix" in sniff.lower()
    except Exception:
        return False


def _major_from_bin_header(path: str) -> int:
    """
        We're trying to extract the major version from the .bin file:
        - at offset 0x3A, we read 5 bytes of ASCII 'X.Y.Z'
        - if not, we check 'Chromatix' at 0x28 → we count it as 1.x (legacy)
    """
    major = 0
    try:
        version_bytes = _read_file_slice(path, 0x3A, 5)
        version_str = version_bytes.decode('ascii', errors='ignore').replace('\x00', '').strip()
        parts = version_str.split('.') if version_str else []
        major = int(parts[0]) if parts and parts[0].isdigit() else 0
    except Exception:
        major = 0

    if major == 0:
        try:
            sig = _read_file_slice(path, 0x28, 10)
            if sig.lower() == b'chromatix':
                major = 1
        except Exception:
            pass
    return major


def _build_rows_from_bin(path: str) -> Sequence[Any]:
    """
        Logic for .bin:
        - major >= 5 → (if present), otherwise MX
        - disable TXT export for readers
    """
    _disable_txt_export_if_present()
    return MX.get_module_list(path)


def _build_rows_from_so(path: str) -> Sequence[Any]:
    """
        Logic for .so:
        - If 'load_chromatix' is found → LegacyMX (old libchromatix)
        - Otherwise, try → MX
        - Disable TXT export before calling
    """
    _disable_txt_export_if_present()

    if _is_legacy_so_by_sniff(path):
        # Old libchromatix — via LegacyMX
        if hasattr(LegacyMX, "get_module_list"):
            return LegacyMX.get_module_list(path)
        # fallback option (if another entrypoint)
        if hasattr(LegacyMX, "read") and callable(getattr(LegacyMX, "read")):
            return LegacyMX.read(path)

    # Not Legacy: Trying v5 → Fallback on MX

    return MX.get_module_list(path)


def getrowsfromlib(lib_path: str) -> Sequence[Any]:
    """
        Main function: accepts a path to a .bin or .so file and returns rows.
        We don't swallow exceptions—if something goes wrong, let them rise.
    """
    if not lib_path or not os.path.exists(lib_path):
        raise FileNotFoundError(f"Path does not exist: {lib_path!r}")

    ext = os.path.splitext(lib_path)[1].lower()
    if ext == ".so":
        return _build_rows_from_so(lib_path)
    # Default (including .bin)
    return _build_rows_from_bin(lib_path)



