import os, sys, struct, string
from typing import List, Tuple, Dict

# ===== behavior =====
_QTIParameterReaderVersion = "Parameter Reader - Beta 1.0" # version specified
ProgressTitle = _QTIParameterReaderVersion # window title
EnableDebug = 0 # 0 — silent; 1 — print via _dbg() (stdout)
AllowExportTxt = 0 # when running as a script, saves TXT files next to it
FILENAME        = "com.qti.tuned.apollo_semco_s5khmx_wide20000.bin"
MAX_TO_PRINT    = 10
AddBaseOffset   = 1   # 1 -> Data Offset += Header.DATA_OFFSET
ShowProgress=1

def _dbg(msg: str) -> None:
    if EnableDebug:
        print(msg, file=sys.stdout)

try:
    import Code.Parsers.ParaParser_1to6._QTIHeadParser as _QTIHeadParserImport
except ImportError:
    import _QTIHeadParser as _QTIHeadParserImport

PRINTABLE = set(bytes(string.printable, 'ascii'))

# ── helpers ───────────────────────────────────────────────────────────────
def _u16_le(b, off): return struct.unpack_from("<H", b, off)[0]
def _u32_le(b, off): return struct.unpack_from("<I", b, off)[0]
def _u64_le(b, off): return struct.unpack_from("<Q", b, off)[0]

def _hx8(v: int) -> str: return f"0x{v:08X}"
def _hx_id(v: int) -> str: return f"0x{v:08X}" if v <= 0xFFFFFFFF else f"0x{v:016X}"
def _hx_mode(v: int) -> str: return f"0x{v:08X}" if v <= 0xFFFFFFFF else f"0x{v:016X}"

def _is_printable_ascii_zeropad(buf: bytes) -> bool:
    if not buf: return False
    if any((c not in PRINTABLE and c != 0) for c in buf): return False
    if 0 in buf:
        i = buf.index(0)
        if any(c != 0 for c in buf[i:]): return False
        if all(c == 0 or chr(c).isspace() for c in buf[:i]): return False
    return True

def _plausible_entry(e: Dict) -> bool:
    t = e.get("Type","")
    if not (3 <= len(t) <= 32): return False
    if any(ord(ch) < 32 for ch in t): return False
    sz  = e.get("DataSize", 0)
    if not (0 < sz < (1<<40)): return False
    return True

# ── SYMBOL format parsers ────────────────────────────────────────────────────────────────────────
def parse_unaligned56(b, off):
    ID        = _u32_le(b, off + 0)
    Type_raw  = b[off+4:off+4+32]
    if not _is_printable_ascii_zeropad(Type_raw): raise ValueError("type not ascii/zeropad")
    Type      = Type_raw.split(b"\x00",1)[0].decode('ascii','replace')
    Maj       = _u16_le(b, off + 36)
    Min       = _u16_le(b, off + 38)
    Patch     = _u32_le(b, off + 40)
    ModeID    = _u32_le(b, off + 44)
    DataOff   = _u32_le(b, off + 48)
    DataSize  = _u32_le(b, off + 52)
    return dict(ID=ID, Type=Type, Version=(Maj,Min,Patch),
                ModeID=ModeID, DataOffset=DataOff, DataSize=DataSize)

def parse_modern60(b, off):
    e = parse_unaligned56(b, off)
    e["DuplicateID"] = _u32_le(b, off + 56)
    return e

def parse_legacy60(b, off):
    ID        = _u32_le(b, off + 0)
    Type_raw  = b[off+4:off+4+32]
    if not _is_printable_ascii_zeropad(Type_raw): raise ValueError("type not ascii/zeropad")
    Type      = Type_raw.split(b"\x00",1)[0].decode('ascii','replace')
    Maj       = _u16_le(b, off + 36)
    Min       = _u16_le(b, off + 38)
    Patch     = _u32_le(b, off + 40)
    Mode      = _u16_le(b, off + 44)
    Selector  = _u16_le(b, off + 46)
    SelData   = _u32_le(b, off + 48)
    ModeID    = _u32_le(b, off + 52)
    DataOff   = _u32_le(b, off + 56)
    DataSize  = _u32_le(b, off + 60 - 4)
    return dict(ID=ID, Type=Type, Version=(Maj,Min,Patch),
                Mode=Mode, Selector=Selector, SelectorData=SelData,
                ModeID=ModeID, DataOffset=DataOff, DataSize=DataSize)

def parse_legacy64(b, off):
    ID        = _u32_le(b, off + 0)
    Type_raw  = b[off+4:off+4+32]
    if not _is_printable_ascii_zeropad(Type_raw): raise ValueError("type not ascii/zeropad")
    Type      = Type_raw.split(b"\x00",1)[0].decode('ascii','replace')
    Maj       = _u16_le(b, off + 36)
    Min       = _u16_le(b, off + 38)
    Patch     = _u32_le(b, off + 40)
    Mode      = _u16_le(b, off + 44)
    Selector  = _u16_le(b, off + 46)
    SelData   = _u32_le(b, off + 48)
    ModeID    = _u32_le(b, off + 52)
    DataOff   = _u32_le(b, off + 56)
    DataSize  = _u32_le(b, off + 60)
    return dict(ID=ID, Type=Type, Version=(Maj,Min,Patch),
                Mode=Mode, Selector=Selector, SelectorData=SelData,
                ModeID=ModeID, DataOffset=DataOff, DataSize=DataSize)

def parse_aligned76(b, off):
    ID        = _u64_le(b, off + 0)
    Type_raw  = b[off+8:off+8+32]
    if not _is_printable_ascii_zeropad(Type_raw): raise ValueError("type not ascii/zeropad")
    Type      = Type_raw.split(b"\x00",1)[0].decode('ascii','replace')
    Maj       = _u16_le(b, off + 40)
    Min       = _u16_le(b, off + 42)
    Patch     = _u64_le(b, off + 44)
    ModeID    = _u64_le(b, off + 52)
    DataOff   = _u64_le(b, off + 60)
    DataSize  = _u64_le(b, off + 68)
    return dict(ID=int(ID), Type=Type, Version=(Maj,Min,Patch),
                ModeID=int(ModeID), DataOffset=int(DataOff), DataSize=int(DataSize))

def parse_aligned72(b, off):
    ID        = _u64_le(b, off + 0)
    Type_raw  = b[off+8:off+8+32]
    if not _is_printable_ascii_zeropad(Type_raw): raise ValueError("type not ascii/zeropad")
    Type      = Type_raw.split(b"\x00",1)[0].decode('ascii','replace')
    Maj       = _u16_le(b, off + 40)
    Min       = _u16_le(b, off + 42)
    Patch     = _u32_le(b, off + 44)
    ModeID    = _u64_le(b, off + 48)
    DataOff   = _u64_le(b, off + 56)
    DataSize  = _u64_le(b, off + 64)
    return dict(ID=int(ID), Type=Type, Version=(Maj,Min,Patch),
                ModeID=int(ModeID), DataOffset=int(DataOff), DataSize=int(DataSize))

# ── format detection ─ ... ─ ... _hx8(e.get("DataSize",0))] # ModeID is empty
def detect_format_by_stride(sym: bytes):
    n = len(sym)
    if n < 56 + 8:
        return None
    # aligned76
    if n >= 76 + 8:
        try:
            id0 = _u64_le(sym, 0); id1 = _u64_le(sym, 76)
            if id1 == id0 + 1 and _plausible_entry(parse_aligned76(sym, 0)) and _plausible_entry(parse_aligned76(sym, 76)):
                return ("aligned76", 76)
        except Exception: pass
    # aligned72
    if n >= 72 + 8:
        try:
            id0 = _u64_le(sym, 0); id1 = _u64_le(sym, 72)
            if id1 == id0 + 1 and _plausible_entry(parse_aligned72(sym, 0)) and _plausible_entry(parse_aligned72(sym, 72)):
                return ("aligned72", 72)
        except Exception: pass
    # legacy64
    if n >= 64 + 4:
        try:
            id0 = _u32_le(sym, 0); id1 = _u32_le(sym, 64)
            if id1 == id0 + 1 and _plausible_entry(parse_legacy64(sym, 0)) and _plausible_entry(parse_legacy64(sym, 64)):
                return ("legacy64", 64)
        except Exception: pass
    # unaligned56
    if n >= 56 + 4:
        try:
            id0 = _u32_le(sym, 0); id1 = _u32_le(sym, 56)
            if id1 == id0 + 1 and _plausible_entry(parse_unaligned56(sym, 0)) and _plausible_entry(parse_unaligned56(sym, 56)):
                return ("unaligned56", 56)
        except Exception: pass
    # 60 (modern60 → legacy60)
    if n >= 60 + 4:
        try:
            id0 = _u32_le(sym, 0); id1 = _u32_le(sym, 60)
            if id1 == id0 + 1 and _plausible_entry(parse_modern60(sym, 0)) and _plausible_entry(parse_modern60(sym, 60)):
                return ("modern60", 60)
        except Exception: pass
        try:
            if _plausible_entry(parse_legacy60(sym, 0)) and _plausible_entry(parse_legacy60(sym, 60)):
                return ("legacy60", 60)
        except Exception: pass
    # fallback
    for name, size, fn in (("aligned76",76,parse_aligned76),
                           ("aligned72",72,parse_aligned72),
                           ("legacy64",64,parse_legacy64),
                           ("unaligned56",56,parse_unaligned56),
                           ("modern60",60,parse_modern60),
                           ("legacy60",60,parse_legacy60)):
        if n >= size:
            try:
                if _plausible_entry(fn(sym, 0)):
                    return (name, size)
            except Exception:
                continue
    return None

# ── formatting ───────────────────────────────────────────────────────
def _build_header(fmt_name: str, include_idlink: bool) -> str:
    cols = ["ID", "Type", "Ver"]
    if fmt_name in ("legacy60","legacy64"):
        cols += ["Mode", "Selector", "SelectorData"]
    cols += ["ModeID", "Data Offset", "DataSize"]
    if fmt_name == "modern60":
        cols.append("DuplicateID")
    if include_idlink:
        cols.append("IDLINK")
    return " | ".join(cols)

def _format_symbol_row(e: Dict, fmt_name: str, base_off: int, include_idlink: bool) -> str:
    v = e.get("Version",(0,0,0))
    data_off = e.get("DataOffset",0) + (base_off if AddBaseOffset else 0)
    parts = [ _hx_id(e.get("ID",0)), e.get("Type",""), f"{v[0]}.{v[1]}.{v[2]}" ]
    if fmt_name in ("legacy60","legacy64"):
        parts += [ str(e.get("Mode",0)), str(e.get("Selector",0)), _hx8(e.get("SelectorData",0)) ]
    parts += [ _hx_mode(e.get("ModeID",0)), _hx8(data_off), _hx8(e.get("DataSize",0)) ]
    if fmt_name == "modern60":
        parts.append(_hx8(e.get("DuplicateID",0)))
    if include_idlink:
        parts.append("")  # at symbol no IDLINK
    return " | ".join(parts)

def _format_idlink_row(e: Dict, fmt_name: str, base_off: int, include_idlink: bool) -> str:
    # e: {ID, DataOffset, DataSize, IDLINK}
    data_off = e.get("DataOffset",0) + (base_off if AddBaseOffset else 0)
    # empty fields instead of Type/Ver/Mode/ModeID/... to match the header
    parts = [ _hx_id(e.get("ID",0)), "", "" ]
    if fmt_name in ("legacy60","legacy64"):
        parts += ["", "", ""]
    parts += ["", _hx8(data_off), _hx8(e.get("DataSize",0))]  # ModeID empty
    if fmt_name == "modern60":
        parts.append("") # DuplicateID is empty
    if include_idlink:
        parts.append(_hx8(e.get("IDLINK",0)))
    return " | ".join(parts)

# ── SYMBOL section parser ──────────────────────── ─────────────────────────
def _parse_symbol_section(bin_data: bytes, sym_off: int, sym_len: int) -> Tuple[str, List[Dict]]:
    sym = bin_data[sym_off: sym_off + sym_len]
    det = detect_format_by_stride(sym)
    if not det:
        raise RuntimeError("cannot detect symbol entry format by stride")
    fmt_name, step = det
    total = len(sym)
    n_full = total // step
    if total % step != 0:
        _dbg(f"[WARN] SYMBOL_SIZE ({total}) trimmed to {n_full*step} to fit step={step}")
        sym = sym[:n_full * step]
    parse_fn = {
        "unaligned56": parse_unaligned56,
        "modern60":    parse_modern60,
        "legacy60":    parse_legacy60,
        "legacy64":    parse_legacy64,
        "aligned76":   parse_aligned76,
        "aligned72":   parse_aligned72,
    }[fmt_name]
    entries: List[Dict] = []
    off = 0
    for _ in range(n_full):
        e = parse_fn(sym, off)
        entries.append(e)
        off += step
    return fmt_name, entries

# ── IDLINK section parser ─ ... ────────────────────────────────────
# recording format (16 bytes):
#u32ID | u32 DataOffset | u32 DataSize | u32 IDLINK
def _parse_idlink_section(bin_data: bytes, idl_off: int, idl_len: int) -> List[Dict]:
    if idl_len <= 0:
        return []
    if idl_off < 0 or idl_off + idl_len > len(bin_data):
        _dbg(f"[WARN] IDLINK range out of file: off=0x{idl_off:X} len=0x{idl_len:X}")
        idl_len = max(0, len(bin_data) - max(0, idl_off))
    size = 16
    n = idl_len // size
    if n <= 0:
        return []
    out: List[Dict] = []
    base = idl_off
    for i in range(n):
        o = base + i*size
        ID       = _u32_le(bin_data, o + 0)
        DataOff  = _u32_le(bin_data, o + 4)
        DataSize = _u32_le(bin_data, o + 8)
        LinkID   = _u32_le(bin_data, o + 12)
        out.append({"ID": ID, "DataOffset": DataOff, "DataSize": DataSize, "IDLINK": LinkID})
    return out

# ── PUBLIC FUNCTION (WITHOUT ARGUMENTS) ──────────────────────────────────
def READ_SYMBOL_TABLE() -> List[str]:
    """
    Returns TXT export lines:
    [ "ID | Type | Ver | ...", "<row1>", "<row2>", ... ]
    The path to the binary is taken ONLY from the local FILENAME variable.
    """
    # Prepare HeaderParser and extract offsets
    _QTIHeadParserImport.QTI_LIBHEAD_FILE_NAME = FILENAME
    _QTIHeadParserImport.FILE_SIZE             = ""
    _QTIHeadParserImport.CRC32                 = ""
    _QTIHeadParserImport.VERSION               = ""
    _QTIHeadParserImport.BINARY_TAG            = ""
    _QTIHeadParserImport.SECTBLOCK_OFFSET      = ""
    _QTIHeadParserImport.SECTBLOCK_COUNT       = ""
    _QTIHeadParserImport.ZEROS_DETECTED        = "0"
    _QTIHeadParserImport.SYMBOL_OFFSET         = ""
    _QTIHeadParserImport.SYMBOL_SIZE           = ""
    _QTIHeadParserImport.DATA_OFFSET           = ""
    _QTIHeadParserImport.DATA_SIZE             = ""
    _QTIHeadParserImport.MODE_OFFSET           = ""
    _QTIHeadParserImport.MODE_SIZE             = ""
    _QTIHeadParserImport.IDLINK_OFFSET         = ""
    _QTIHeadParserImport.IDLINK_SIZE           = ""
    _QTIHeadParserImport.RESERVED_OFFSET       = ""
    _QTIHeadParserImport.RESERVED_SIZE         = ""
    _QTIHeadParserImport.GetVariablesFromHeader()

    def _hx(s):
        if not s: return 0
        s = s.strip()
        return int(s, 16) if s.lower().startswith("0x") else int(s)

    sym_off = _hx(_QTIHeadParserImport.SYMBOL_OFFSET)
    sym_len = _hx(_QTIHeadParserImport.SYMBOL_SIZE)
    idl_off = _hx(_QTIHeadParserImport.IDLINK_OFFSET)
    idl_len = _hx(_QTIHeadParserImport.IDLINK_SIZE)
    data_base_off = _hx(_QTIHeadParserImport.DATA_OFFSET) if AddBaseOffset else 0

    with open(FILENAME, "rb") as f:
        data = f.read()

    # Safe boundaries
    if sym_off < 0 or sym_off >= len(data) or sym_len <= 0:
        raise RuntimeError(f"bad SYMBOL range off=0x{sym_off:X} len=0x{sym_len:X}")
    if sym_off + sym_len > len(data):
        new_len = len(data) - sym_off
        _dbg(f"[WARN] SYMBOL_SIZE (0x{sym_len:X}) goes past EOF; trimming to 0x{new_len:X}")
        sym_len = new_len

    # Parse SYMBOLS
    fmt_name, sym_entries = _parse_symbol_section(data, sym_off, sym_len)

    # Parse IDLINK (if any)
    idlink_entries: List[Dict] = []
    include_idlink_col = False
    if idl_len > 0 and 0 <= idl_off < len(data):
        if idl_off + idl_len > len(data):
            idl_len = len(data) - idl_off
            _dbg(f"[WARN] IDLINK_SIZE trimmed to 0x{idl_len:X}")
        idlink_entries = _parse_idlink_section(data, idl_off, idl_len)
        include_idlink_col = len(idlink_entries) > 0

    # Generate strings
    header = _build_header(fmt_name, include_idlink_col)
    lines: List[str] = [header]

    # SYMBOL rows
    for e in sym_entries:
        lines.append(_format_symbol_row(e, fmt_name, data_base_off, include_idlink_col))

    # IDLINK rows (if any)
    if include_idlink_col:
        for e in idlink_entries:
            lines.append(_format_idlink_row(e, fmt_name, data_base_off, include_idlink_col))

    return lines


def _hex_noprefix_padded(s: str) -> str:
    """
    '0x12' -> '00000012'
    '0x123456789ABCDEF0' -> '123456789ABCDEF0' (zfill to 16 if needed)
    """
    t = s.strip()
    if t.lower().startswith("0x"):
        t = t[2:]
    t = t.upper()
    if len(t) <= 8:
        return t.zfill(8)
    # for 64-bit values
    return t.zfill(16)

def _to_int_from_hex_string(s: str) -> int:
    t = s.strip()
    return int(t, 16) if t.lower().startswith("0x") else int(t)

def _hex8_be(v: int) -> str:
    # interpret v as u32 LE and output big-endian hex
    return struct.pack("<I", v)[::-1].hex().upper().zfill(8)


def get_module_list(filename: str) -> List[str]:
    """
    Returns a list of strings of the following format:
      '000006CB,revision,00001B38,00000008'
    For IDLINK strings (Type == ''), substitutes Name:
      'ID,NameCode:<IDLINK_BE>,offset,size'
    """
    global FILENAME
    FILENAME = filename

    lines = READ_SYMBOL_TABLE()
    if not lines:
        return []

    # Header parsing
    header = lines[0]
    cols = [c.strip() for c in header.split("|")]
    try:
        idx_id   = cols.index("ID")
        idx_type = cols.index("Type")
        idx_off  = cols.index("Data Offset")
        idx_sz   = cols.index("DataSize")
    except ValueError:
        return []

    # IDLINK column may be missing (if there is no section)
    try:
        idx_idlink = cols.index("IDLINK")
    except ValueError:
        idx_idlink = -1

    out: List[str] = []
    for row in lines[1:]:
        parts = [p.strip() for p in row.split("|")]
        if len(parts) <= max(idx_id, idx_type, idx_off, idx_sz):
            continue

        id_hex   = parts[idx_id]
        type_str = parts[idx_type]
        off_hex  = parts[idx_off]
        sz_hex   = parts[idx_sz]

        # If this is an IDLINK string (Type is empty), use NameCode:<IDLINK_BE>
        if not type_str:
            if idx_idlink != -1 and idx_idlink < len(parts):
                try:
                    idlink_le = _to_int_from_hex_string(parts[idx_idlink])
                    type_str = f"NameCode:{_hex8_be(idlink_le)}"
                except Exception:
                    # If parsing failed, provide a fallback label
                    type_str = "NameCode:UNKNOWN"
            else:
                type_str = "NameCode:ABSENT"

        # Normalize HEX without 0x and padding
        def _hex_noprefix_padded(s: str) -> str:
            t = s.strip()
            if t.lower().startswith("0x"):
                t = t[2:]
            t = t.upper()
            if len(t) <= 8:
                return t.zfill(8)
            return t.zfill(16)

        id_hex_norm  = _hex_noprefix_padded(id_hex)
        off_hex_norm = _hex_noprefix_padded(off_hex)
        sz_hex_norm  = _hex_noprefix_padded(sz_hex)

        out.append(f"{id_hex_norm},{type_str},{off_hex_norm},{sz_hex_norm}")

    return out



# ── "CLI" without arguments ────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        lines = READ_SYMBOL_TABLE()
    except Exception as ex:
        _dbg(f"[ERR] {ex}")
        sys.exit(1)

    for i, ln in enumerate(lines):
        if i == 0 or i < MAX_TO_PRINT:
            _dbg(ln)

    if AllowExportTxt:
        out_name = (getattr(_QTIHeadParserImport, "QTI_LIBHEAD_FILE_NAME", "") or FILENAME) + ".txt"
        try:
            with open(out_name, "w", encoding="utf-8") as out:
                out.write("\n".join(lines) + "\n")
            _dbg(f"[EXPORT] Saved: {out_name}")
        except Exception as ex:
            _dbg(f"[EXPORT][ERR] {ex}")
