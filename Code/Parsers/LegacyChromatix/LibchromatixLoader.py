import os
import struct
from typing import List, Optional, Tuple
import re

# ── Parser version imports ───────────────────────────────────────────────
try:
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0300 as inpars_300
    import Code.Parsers.LegacyChromatix.parse_DefPrevSnap_chromatix_0301 as DefPrevSnap_301
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0301 as inpars_301
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0302 as inpars_302
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0303 as inpars_303
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0304 as inpars_304
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0305 as inpars_305
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0306 as inpars_306
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0307 as inpars_307
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0308 as inpars_308
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0309 as inpars_309
    import Code.Parsers.LegacyChromatix.parse_common_chromatix_0310 as inpars_310
    import Code.Parsers.LegacyChromatix.Load_Chromatix_Data as lc
except ImportError:
    import LegacyChromatix.parse_common_chromatix_0300 as inpars_300
    import LegacyChromatix.parse_DefPrevSnap_chromatix_0301 as DefPrevSnap_301
    import LegacyChromatix.parse_common_chromatix_0301 as inpars_301
    import LegacyChromatix.parse_common_chromatix_0302 as inpars_302
    import LegacyChromatix.parse_common_chromatix_0303 as inpars_303
    import LegacyChromatix.parse_common_chromatix_0304 as inpars_304
    import LegacyChromatix.parse_common_chromatix_0305 as inpars_305
    import LegacyChromatix.parse_common_chromatix_0306 as inpars_306
    import LegacyChromatix.parse_common_chromatix_0307 as inpars_307
    import LegacyChromatix.parse_common_chromatix_0308 as inpars_308
    import LegacyChromatix.parse_common_chromatix_0309 as inpars_309
    import LegacyChromatix.parse_common_chromatix_0310 as inpars_310
    import LegacyChromatix.Load_Chromatix_Data as lc





# an external module that returns the .so (LCOFF, LCLENGTH)


# ── Global variables ────────────────────────────────────────────────
AllowDebug = 0
LOAD_CHROMATIX_VER: str = "" # '0300'..'0310' — primary value from file (u16 LE @ LCOFF)

# Profiles of known libraries (historical mode, "old style")
# They are no longer required in dynamic mode, but we retain them
# for backward compatibility Get_chromatix_intro_rows_parser()

#LEGACY_CHROMATIX_LIB_PATH = "libchromatix_0302_common.so"
#LCOFF     = 12292
#LCLENGTH  = 42044
#
#LEGACY_CHROMATIX_LIB_PATH = "libchromatix_0304_common.so"
#LCOFF     = 12292
#LCLENGTH  = 44140

LEGACY_CHROMATIX_LIB_PATH = ""
LCOFF     = ""
LCLENGTH  = ""

#
#LEGACY_CHROMATIX_LIB_PATH = "libchromatix_imx179_common.so"
#LCOFF     = 12292
#LCLENGTH  = 42044
#
#LEGACY_CHROMATIX_LIB_PATH = "libchromatix_0309_common.so"
#LCOFF     = 1340
#LCLENGTH  = 53360

# ── Constants for auto-detection 0300 vs 0301 ───────────────────────────────
_GAIN_MIN = 1.0
_GAIN_MAX = 10.0
SCAN_FLOAT_COUNT = 130 # We're looking for a block of 130 float32s in a row
TAG_EXPECT_13x10 = 130 # If u32LE before the block == 130 → old format (0300)
TAG_EXPECT_17x13 = 221 # If u32LE == 221 → new format (0301)


def _dbg(*args):
    if AllowDebug:
        print(*args)

def _u16_le(b: bytes, off: int) -> int:
    return struct.unpack_from("<H", b, off)[0]

def _u32_le(b: bytes, off: int) -> int:
    return struct.unpack_from("<I", b, off)[0]

def _all_in_gain_range(vals: Tuple[float, ...]) -> bool:
    """All values ​​are in the range 1.0..10.0 (typical GainMap)."""
    for v in vals:
        if not (_GAIN_MIN <= v <= _GAIN_MAX):
            return False
    return True

def _detect_old_vs_0301(introdatabuffer: bytes) -> Optional[bool]:
    """
    We're trying to figure out if this is the old format (parser 0300 / "OLD")
    or the new 0301.

    Algorithm:
    - walk the buffer (which starts with a block on LCOFF),
    - at each position p, try to read 130 float32 LE in a row,
    - check that ALL are in the range [1.0 .. 10.0] (similar to GainMap),
    - look up the 4 bytes BEFORE this sequence as u32 LE.
    * if it's 130 → old layout (13x10 as base) → return True (OLD)
    * if it's 221 → new layout (17x13 as base) → return False (0301)
    - if nothing found → return None.

    Returns:
    True → Use the "OLD" parser (0300)
    False → Use the "0301" parser
    None → Could not distinguish
    """
    data = introdatabuffer
    total_len = len(data)
    block_bytes = SCAN_FLOAT_COUNT * 4  # 130 * 4 = 520 bytes

    # we need at least p-4 >= 0 => p >= 4
    p = 4
    limit = total_len - block_bytes
    while p <= limit:
        try:
            vals = struct.unpack_from("<" + "f"*SCAN_FLOAT_COUNT, data, p)
        except struct.error:
            break

        if _all_in_gain_range(vals):
            # Let's look at the length tag right before the block.
            tag_val = _u32_le(data, p - 4)
            if tag_val == TAG_EXPECT_13x10:
                _dbg(f"[ver-scan] found tag=130 @rel 0x{p-4:04X} → OLD/0300 style")
                return True
            if tag_val == TAG_EXPECT_17x13:
                _dbg(f"[ver-scan] found tag=221 @rel 0x{p-4:04X} → 0301 style")
                return False
            # If you've hit gain-like data, but the tag is non-standard, continue.
        p += 4

    _dbg("[ver-scan] couldn't confidently classify OLD vs 0301")
    return None

def _read_intro_region(
    lib_path: str,
    lc_off: int,
    lc_len: int
) -> bytes:
    """
    Internal helper: read the [lc_off : lc_off+lc_len] chunk from lib_path.
    No versions are affected.
    """
    if not os.path.isfile(lib_path):
        raise FileNotFoundError(f"File not found: {lib_path}")

    with open(lib_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        fsize = f.tell()
        if lc_off >= fsize:
            raise ValueError(f"LCOFF (0x{lc_off:X}) is beyond file size ({fsize} bytes)")
        f.seek(lc_off)
        to_read = min(lc_len, fsize - lc_off)
        introdatabuffer = f.read(to_read)

    return introdatabuffer

def get_chromatix_intro_data() -> bytes:
    """
    OLD MODE (back-compat):
    - reads LEGACY_CHROMATIX_LIB_PATH,
    - uses global LCOFF/LCLENGTH,
    - defines LOAD_CHROMATIX_VER as the first 2 bytes of LE.
    """
    global LOAD_CHROMATIX_VER

    introdatabuffer = _read_intro_region(
        LEGACY_CHROMATIX_LIB_PATH,
        LCOFF,
        LCLENGTH
    )

    # Primary version: first 2 bytes as u16 LE
    ver_u16 = _u16_le(introdatabuffer, 0)
    LOAD_CHROMATIX_VER = f"{ver_u16:04X}"

    _dbg(f"[ver-base] RAW LOAD_CHROMATIX_VER = {LOAD_CHROMATIX_VER}")
    _dbg(f"[buf] introdatabuffer size = {len(introdatabuffer)} bytes "
         f"(LCOFF=0x{LCOFF:X}, LCLENGTH=0x{LCLENGTH:X})")

    return introdatabuffer

def get_chromatix_intro_data_dynamic(lib_path: str) -> Tuple[bytes, int, int]:
    """
    NEW MODE:
    - lc.load_chromatix_offsets(lib_path) -> (lc_off, lc_len)
    - read intro
    - set LOAD_CHROMATIX_VER
    - return (introdatabuffer, lc_off, lc_len)
    """
    global LOAD_CHROMATIX_VER

    lc_off, lc_len = lc.load_chromatix_offsets(lib_path)
    introdatabuffer = _read_intro_region(lib_path, lc_off, lc_len)

    ver_u16 = _u16_le(introdatabuffer, 0)
    LOAD_CHROMATIX_VER = f"{ver_u16:04X}"

    _dbg(f"[ver-base] RAW LOAD_CHROMATIX_VER = {LOAD_CHROMATIX_VER}")
    _dbg(f"[buf] introdatabuffer size = {len(introdatabuffer)} bytes "
         f"(LCOFF=0x{lc_off:X}, LCLENGTH=0x{lc_len:X})")
    _dbg(f"[file] lib_path = {lib_path}")

    return introdatabuffer, lc_off, lc_len


# "effective version" match → module
# "OLD" = 0300 format
_PARSER_BY_VER = {
    "OLD":  inpars_300,
    "0301": inpars_301,
    "0302": inpars_302,
    "0303": inpars_303,
    "0304": inpars_304,
    "0305": inpars_305,
    "0306": inpars_306,
    "0307": inpars_307,
    "0308": inpars_308,
    "0309": inpars_309,
    "0310": inpars_310,
    # formally 0300 → the same as "OLD""
    "0300": inpars_300,
}

def _resolve_effective_version(introdatabuffer: bytes) -> str:
    """
        Returns the version string by which to select a parser module.
        Rule:
        - If the primary version == "0300":
        → this is definitely the old format → "OLD"
        - If the primary version == "0301":
        → check using _detect_old_vs_0301():
        True → "OLD" (tag=130 → base grid 13x10 → behavior 0300)
        False → "0301" (tag=221 → base grid 17x13 → new format)
        None → "0301" (fallback)
        - otherwise:
        → return as is (0302, 0310, etc.)
    """
    base_ver = LOAD_CHROMATIX_VER

    if base_ver == "0300":
        _dbg("[ver-final] base_ver=0300 → use OLD parser")
        return "OLD"

    if base_ver == "0301":
        probe = _detect_old_vs_0301(introdatabuffer)
        if probe is True:
            _dbg("[ver-final] 0301 but scan→OLD, using OLD parser")
            return "OLD"
        if probe is False:
            _dbg("[ver-final] 0301 and scan→0301, using 0301 parser")
            return "0301"
        _dbg("[ver-final] 0301 but scan inconclusive, fallback to 0301 parser")
        return "0301"

    _dbg(f"[ver-final] base_ver={base_ver} → use {base_ver} parser")
    return base_ver

def _run_intro_parser(
    introdatabuffer: bytes,
    lc_off: int
) -> List[str]:
    """
    General executor:
    1. Determine eff_ver (OLD / 0301 / 0302 ...).
    2. Take the corresponding module from _PARSER_BY_VER.
    3. Call intro_row_parser(introdatabuffer, lc_off).
    4. Return rows (List[str]).
    """
    eff_ver = _resolve_effective_version(introdatabuffer)

    if eff_ver not in _PARSER_BY_VER:
        raise ValueError(f"Unsupported version {eff_ver}; no parser module mapped")

    parser_mod = _PARSER_BY_VER[eff_ver]
    if not hasattr(parser_mod, "intro_row_parser"):
        raise AttributeError(
            f"Parser module for {eff_ver} has no 'intro_row_parser'"
        )

    _dbg(f"[call] {parser_mod.__name__}.intro_row_parser(...) as version {eff_ver}")
    rows = parser_mod.intro_row_parser(introdatabuffer, lc_off)
    if rows is None:
        rows = []

    _dbg(f"[rows] received {len(rows)} rows from {eff_ver}")
    return rows


# ─────────────────────────────────────────────────────────
# ADDITIONS FOR NEW REQUIREMENT (_common only)
# ─────────────────────────────────────────────────────────

def _extract_type_from_hex(lib_path: str, introdatabuffer: Optional[bytes] = None) -> str:
    """
    Search the file for the ASCII substring:
    libchromatix_{sensor}_{type}.so
    Take {type} as everything after the second '_' up to '.so'.
    """
    prefix = b"libchromatix_"

    # 1) Byte source
    if introdatabuffer is None:
        try:
            with open(lib_path, "rb") as f:
                data = f.read()
        except Exception:
            return "unknown"
    else:
        data = introdatabuffer

    # 2) Find "libchromatix_"
    i = data.find(prefix)
    if i == -1:
        return "unknown"

    # 3) Skip sensor to next '_'
    j = data.find(b"_", i + len(prefix))
    if j == -1:
        return "unknown"

    # 4) Take everything before ".so" as type
    k = data.find(b".so", j + 1)
    if k == -1:
        return "unknown"

    chroma_type = data[j + 1:k].decode("ascii", "ignore").strip().strip("_")
    return chroma_type if chroma_type else "unknown"



def _format_single_row_no_common(
    version_str: str,
    chroma_type: str,
    lc_off: int,
    lc_len: int
) -> List[str]:
    """
    Produces a single string:
    "000,Chromatix_Data_{version}_{type},{offset},{length}"
    offset/length without the 0x, just decimal values.
    """
    row = (
        f"000,Chromatix_Data_{version_str}_{chroma_type},"
        f"{lc_off},{lc_len}"
    )
    return [row]




# ── Public function of the NEW REGIME ──────────────────────────────────────
def get_module_list_simple(lib_path: str) -> List[str]:
    introdatabuffer, lc_off, _lc_len = get_chromatix_intro_data_dynamic(lib_path)
    rows = _run_intro_parser(introdatabuffer, lc_off)
    return rows



def get_module_list(lib_path: str) -> List[str]:
    """
    Logic:
    1) Read (introdatabuffer, lc_off, lc_len)
    2) If the file name does NOT contain '_common' → don't parse, but return a single string:
    "000,Chromatix_Data_{version}_{type},{offset},{length}"
    3) Otherwise, parse as before
    """
    introdatabuffer, lc_off, lc_len = get_chromatix_intro_data_dynamic(lib_path)

    base_name = os.path.basename(lib_path)
    has_common = ("_common" in base_name)

    version_be = LOAD_CHROMATIX_VER
    chroma_type = _extract_type_from_hex(lib_path)

    if not has_common:
        _dbg("[flow] no _common in filename → return single row only, skip parsing")
        return _format_single_row_no_common(
            version_str=version_be,
            chroma_type=chroma_type,
            lc_off=lc_off,
            lc_len=lc_len
        )

    _dbg("[flow] '_common' detected → full parsing enabled")
    rows = _run_intro_parser(introdatabuffer, lc_off)
    return rows



# ── Old public interface (backward compatibility)) ──────────────────
def Get_chromatix_intro_rows_parser() -> List[str]:
    """
    Legacy mode:
    1. Reads data from .so files via the global LEGACY_CHROMATIX_LIB_PATH/LCOFF/LCLENGTH
    2. Determines the actual parser version (taking into account the OLD/0301 trick)
    3. Calls the appropriate intro_row_parser(introdatabuffer, LCOFF)
    4. Returns the prepared rows
    """
    introdatabuffer = get_chromatix_intro_data()
    rows = _run_intro_parser(introdatabuffer, LCOFF)
    return rows

# ── Example of independent launch (manual test) ────────────────────────
if __name__ == "__main__":
    try:
        # mode A: old (uses global LEGACY_* constants above)
        _dbg("=== Legacy test ===")
        legacy_rows = Get_chromatix_intro_rows_parser()
        for i, r in enumerate(legacy_rows[:300]):
            print(f"{i:03d}: {r}")

        # Mode B: New (Dynamic Path)
        _dbg("=== Dynamic test ===")
        dynamic_rows = get_module_list(LEGACY_CHROMATIX_LIB_PATH)
        for i, r in enumerate(dynamic_rows[:300]):
            print(f"[dyn]{i:03d}: {r}")

    except Exception as e:
        print("[ERROR]", e)
