import os
import struct
from typing import List, Tuple, Optional

# ──────────────────────────── ─────────────────────────────
# Configuration / Globals
# ─ ... LSC/Golden
LOAD_CHROMATIX_VER = "" # will be filled from .so

# ---- intro field numbering ----
ID_START_NORMAL = 0x0C00
ID_END_REVERSE = 0x0CBF # if REVERSE_INDEX=1, the last line of the intro will receive this ID
REVERSE_INDEX = 1 # 0 — forward, 1 — "from the end"
WRITEVALUETONAME = 1 # substitute numeric values ​​directly into the name

# ---- IMPORTANT: substitute under your .so ----
LEGACY_CHROMATIX_LIB_PATH = "libchromatix_s5k3l2xx_common.so"
LCOFF = 12292 # absolute section offset
LCLENGTH = 67128 # max region length
# example for imx179:
#LEGACY_CHROMATIX_LIB_PATH = "libchromatix_imx179_common.so"
#LCOFF = 12292
#LCLENGTH = 42044

BYPASSEMPTYGAINMAPS = 0 # 1 → skip all "1.0" maps (all channels ≈1.0)

# ---- GainMap / Golden (RawMap) analysis constants ----
SEQ_LEN = 221 # floats per channel
CHANNELS = 4 # RGGB → 4 channels in a row
GAIN_MIN, GAIN_MAX = 1.0, 10.0
RAW_MIN, RAW_MAX = 64.0, 4095.0 # as in the production version
LEN_TAG_13x10 = 0x00000082 # 130 (LE)
LEN_TAG_17x13 = 0x000000DD #221 (LE)
FIRST_13x10 = 130
EPS_ONE     = 1e-4

# fields where we want to insert values ​​in the intro
_NAME_VALUE_FLOAT = {
    "Gain_Start", "Gain_End",
    "Rolloff_LED_Mesh_Rolloff_Start", "Rolloff_LED_Mesh_Rolloff_End",
    "Rolloff_Strobe_Mesh_Rolloff_Start", "Rolloff_Strobe_Mesh_Rolloff_End",
}
_NAME_VALUE_U16 = {"Lux_Index_Start", "Lux_Index_End"}

# ─────────────────────────────────────────────────────────
# General utilities
# ─────────────────────────────────────────────────────────

def _dbg(*args, **kwargs):
    if AllowDebug:
        print(*args, **kwargs)

def _chk(b: bytes, off: int, size: int):
    if not (0 <= off <= len(b) - size):
        raise ValueError(f"Out of range: off=0x{off:X}, size={size}, len={len(b)}")

def hx8(v: int) -> str:
    return f"{v:08X}"

def f32(b: bytes, o: int) -> float:
    _chk(b, o, 4)
    return struct.unpack_from("<f", b, o)[0]

def u16(b: bytes, o: int) -> int:
    _chk(b, o, 2)
    return struct.unpack_from("<H", b, o)[0]

def _u32le_at(b: bytes, o: int) -> int:
    _chk(b, o, 4)
    return struct.unpack_from("<I", b, o)[0]

def _read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def _fmt_f32(v: float) -> str:
    s = f"{v:.6g}"
    if "e" in s or "E" in s:
        s = f"{v:.6f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

def _is_f32_in(b: bytes, off: int, lo: float, hi: float) -> bool:
    try:
        v = f32(b, off)
    except Exception:
        return False
    return lo <= v <= hi

# ---- GainMap/Golden helpers ----

def _in_range_all(vals, vmin, vmax) -> bool:
    return all((vmin <= v <= vmax) for v in vals)

def _are_ones(vals) -> bool:
    return all(abs(v - 1.0) <= EPS_ONE for v in vals)

def _rawmap_13x10_pattern(vals) -> bool:
    """
    Rough heuristics for a "stripped down" 13x10 raw map:
    the first 130 values ​​are ~RAW_MIN..RAW_MAX,
    the rest up to 221 are almost 1.0
    """
    return _in_range_all(vals[:FIRST_13x10], RAW_MIN, RAW_MAX) and _are_ones(vals[FIRST_13x10:])

def _classify_first_channel(vals221) -> Optional[str]:
    """
    We classify only the first channel (221 float32s in a row):
    GainMap → all ∈ [1..10]
    RawMap → all ∈ [64..4095] OR pattern rawmap_13x10
    otherwise None
    """
    if _in_range_all(vals221, GAIN_MIN, GAIN_MAX):
        return "GainMap"
    if _in_range_all(vals221, RAW_MIN, RAW_MAX) or _rawmap_13x10_pattern(vals221):
        return "RawMap"
    return None

def _is_fullblock_all_ones(data: bytes, start: int) -> bool:
    """
    Checking an "empty" GainMap:
    the entire block of 4*221 float32s == ~1.0
    """
    total_floats = SEQ_LEN * CHANNELS  # 884
    total_bytes  = total_floats * 4    # 3536
    if start + total_bytes > len(data):
        return False
    fmt = "<" + "f" * total_floats
    vals = struct.unpack_from(fmt, data, start)
    return _are_ones(vals)

def _size_from_backtag(data: bytes, start_off: int) -> str:
    """
    We take the 4 bytes directly BEFORE the map as u32 LE.
    0x00000082 -> "13x10"
    0x000000DD -> "17x13"
    otherwise "unknown"
    """
    tag_off = start_off - 4
    if tag_off < 0 or tag_off + 4 > len(data):
        return "unknown"
    tag = _u32le_at(data, tag_off)
    if tag == LEN_TAG_13x10:
        return "13x10"
    if tag == LEN_TAG_17x13:
        return "17x13"
    return "unknown"

def _resolve_size(klass: str, vals221, backtag_size: str) -> str:
    """
    Final grid selection:
    - for GainMap: just the tag ("13x10" or "17x13")
    - for RawMap (golden):
    if the values ​​are all in the RAW range → consider it "17x13"
    if the pattern is 13x10 → "13x10"
    otherwise, keep the tag
    """
    if klass == "GainMap":
        return backtag_size
    # RawMap
    if _in_range_all(vals221, RAW_MIN, RAW_MAX):
        return "17x13"
    if _rawmap_13x10_pattern(vals221):
        return "13x10"
    return backtag_size

def _format_version_from_two_bytes_strip_leading_zero(data: bytes, off: int) -> str:
    """
    We take two bytes in a section, treat them as an LE word,
    convert them to a string like '0301', and if it has a leading '0',
    we trim exactly one.
    """
    if off < 0 or off + 2 > len(data):
        return ""
    b0, b1 = data[off], data[off+1]
    be = f"{b1:02X}{b0:02X}"          # for example "0301"
    return be[1:] if be.startswith("0") else be

# ─────────────────────────────────────────────────────────
#  Generating ID strings for intros
# ─────────────────────────────────────────────────────────

def _finalize_entries(entries: List[Tuple[str, int, int]]) -> List[str]:
    """
    entries = [(name, file_off, size), ...]
    Returning strings:
    ID_HEX, name, OFFSET_HEX, LENGTH_HEX
    taking into account REVERSE_INDEX.
    """
    n = len(entries)
    rows: List[str] = []
    if REVERSE_INDEX:
        start_id = ID_END_REVERSE - (n - 1)
    else:
        start_id = ID_START_NORMAL
    cur_id = start_id
    for name, file_off, size in entries:
        rows.append(f"{hx8(cur_id)},{name},{hx8(file_off)},{hx8(size)}")
        cur_id += 1
    return rows

# ─────────────────────────────────────────────────────────
# LSC Parser / Golden → professional names
# ─────────────────────────────────────────────────────────
#
# Now each map (GainMap or Golden RawMap) is expanded into 5 entries:
#
# GainMap index i = (idx_gain-1):
# chromatix_rolloff.chromatix_mesh_rolloff_table[i].mesh_rolloff_table_size_130|221
# chromatix_rolloff.chromatix_mesh_rolloff_table[i].r_gain
# chromatix_rolloff.chromatix_mesh_rolloff_table[i].gr_gain
# chromatix_rolloff.chromatix_mesh_rolloff_table[i].gb_gain
# chromatix_rolloff.chromatix_mesh_rolloff_table[i].b_gain
#
# Golden RawMap index j = (idx_raw-1):
# chromatix_rolloff.chromatix_mesh_rolloff_table_golden_module[j].mesh_rolloff_table_size_221
# chromatix_rolloff.chromatix_mesh_rolloff_table_golden_module[j].r_gain
# chromatix_rolloff.chromatix_mesh_rolloff_table_golden_module[j].gr_gain
# chromatix_rolloff.chromatix_mesh_rolloff_table_golden_module[j].gb_gain
# chromatix_rolloff.chromatix_mesh_rolloff_table_golden_module[j].b_gain
#
# IMPORTANT: golden is ALWAYS marked as size_221, even if the tag was 130.
#
# channel offsets inside the block:
# r_gain : start + 0*884
# gr_gain : start + 1*884
# gb_gain : start + 2*884
# b_gain : start + 3*884
#
# where 884 = 221 * 4 bytes = 0x374.
#

def get_chromatix_LscAndGolden(
    data: Optional[bytes] = None,
    lc_off: Optional[int] = None, # absolute offset of the start of the chromatix region in the FILE
    lc_length: Optional[int] = None, # region length
    start_at_abs: Optional[int] = None, # absolute lower boundary of the scan start
    data_origin_abs: int = 0, # << NEW: absolute offset corresponding to data[0]
) -> List[str]:
    """
    Correct addressing:
    - If data=None → read the file, data_origin_abs=0.
    - If data is a file slice, where data[0] physically coincides with file_offset=data_origin_abs,
    then convert all calculated local offsets to absolute values: abs = data_origin_abs + rel.
    The scan is performed within [lc_off .. lc_off + lc_length).
    """
    global LOAD_CHROMATIX_VER

    # ---- data source / addressing mode ----
    file_mode = (data is None)
    if file_mode:
        lib = LEGACY_CHROMATIX_LIB_PATH
        if not os.path.isfile(lib):
            if AllowDebug: print(f"[ERROR] File not found: {lib}")
            return []
        try:
            data = _read_file(lib)
        except Exception as e:
            if AllowDebug: print(f"[ERROR] Read failed: {e}")
            return []
        data_origin_abs = 0  # whole file - start at 0
        _lc_off = LCOFF if lc_off is None else lc_off
        _lc_len = LCLENGTH if lc_length is None else lc_length
    else:
        # received an external buffer; it corresponds to the file segment starting at data_origin_abs
        _lc_off = LCOFF if lc_off is None else lc_off
        _lc_len = LCLENGTH if lc_length is None else lc_length

    # ---- region boundaries in LOCAL buffer coordinates ----
    # local offset of the region start:
    region_rel_start = max(0, _lc_off - data_origin_abs)
    if region_rel_start > len(data):
        if AllowDebug: print(f"[ERROR] Region starts outside data: rel=0x{region_rel_start:X}, len={len(data)}")
        return []
    region_rel_end = min(len(data), region_rel_start + max(0, _lc_len))
    if region_rel_end <= region_rel_start:
        if AllowDebug: print("[ERROR] Chromatix data region is empty or invalid.")
        return []

    # ---- version (informative) - read 2 bytes at the ABSOLUTE beginning of the region ----
    ver_abs = _lc_off
    ver_rel = ver_abs - data_origin_abs
    if 0 <= ver_rel + 1 < len(data):
        LOAD_CHROMATIX_VER = _format_version_from_two_bytes_strip_leading_zero(data, ver_rel)
    else:
        LOAD_CHROMATIX_VER = ""
    _dbg(f"LOAD_CHROMATIX_VER={LOAD_CHROMATIX_VER}")

    # ---- Preparation ----
    fmt_221          = "<" + "f" * SEQ_LEN
    block_full_bytes = SEQ_LEN * CHANNELS * 4  # 3536
    channel_bytes    = SEQ_LEN * 4             # 884
    channel_names    = ["r_gain", "gr_gain", "gb_gain", "b_gain"]

    rows: List[str] = []
    next_id = 0x00000CC0
    idx_gain = 1
    idx_raw  = 1

    # relative coordinates of the scan start/finish
    if start_at_abs is None:
        scan_rel_start = region_rel_start
    else:
        scan_rel_start = max(region_rel_start, start_at_abs - data_origin_abs)
    scan_rel_stop = region_rel_end
    last_rel_for_full_block = scan_rel_stop - block_full_bytes

    start_rel = scan_rel_start
    while start_rel <= last_rel_for_full_block:
        try:
            vals221 = struct.unpack_from(fmt_221, data, start_rel)  # ONLY Channel 1
        except struct.error:
            break

        klass = _classify_first_channel(vals221)
        if klass is not None:
            # the entire 4-channel block will fit (already guaranteed by last_rel_for_full_block)
            # skipping neutral GainMaps
            if klass == "GainMap" and BYPASSEMPTYGAINMAPS and _is_fullblock_all_ones(data, start_rel):
                _dbg(f"[SKIP] Neutral GainMap @ 0x{(data_origin_abs+start_rel):08X}")
                start_rel += block_full_bytes
                continue

            # grid size (read the tag BEFORE the block, but in local coordinates)
            backtag_size = _size_from_backtag(data, start_rel)   # uses local rel offsets
            final_size   = _resolve_size(klass, vals221, backtag_size)

            # name/indexes
            if klass == "GainMap":
                table_idx   = idx_gain - 1
                base_name   = f"rolloff.mesh_rolloff_table[{table_idx}]"
                size_suffix = "130" if final_size == "13x10" else "221"
                idx_gain   += 1
            else:
                table_idx   = idx_raw - 1
                base_name   = f"rolloff.mesh_rolloff_table_golden_module[{table_idx}]"
                size_suffix = "221"
                idx_raw    += 1

            # absolute offsets = buffer base + local
            tag_rel = start_rel - 4
            if 0 <= tag_rel <= len(data) - 4:
                rows.append(
                    f"{next_id:08X},{base_name}.mesh_rolloff_table_size_{size_suffix},"
                    f"{(data_origin_abs+tag_rel):08X},00000004"
                )
                next_id += 1

            for ch_i, ch_field in enumerate(channel_names):
                ch_rel = start_rel + ch_i * channel_bytes
                rows.append(
                    f"{next_id:08X},{base_name}.{ch_field},"
                    f"{(data_origin_abs+ch_rel):08X},{channel_bytes:08X}"
                )
                next_id += 1

            start_rel += block_full_bytes
            continue

        start_rel += 4

    if AllowDebug and rows:
        print("\n".join(rows))

    if TESTEXPORTTOTXT == 1:
        try:
            base = os.path.splitext(os.path.basename(LEGACY_CHROMATIX_LIB_PATH))[0]
            out_path = os.path.join(os.path.dirname(LEGACY_CHROMATIX_LIB_PATH), f"{base}_Common_s1.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(rows))
                if rows: f.write("\n")
            _dbg(f"[OK] Saved: {out_path}")
        except Exception as e:
            _dbg(f"[ERROR] Write TXT failed: {e}")

    return rows



# ─────────────────────────────────────────────────────────
# intro parser (header / ruler / triggers / rolloffs)
# and adding tables from get_chromatix_LscAndGolden()
# ─────────────────────────────────────────────────────────

def intro_row_parser(
    introdatabuffer: bytes,
    lc_off: int, # absolute file offset of the buffer start (usually LCOFF)
    base_off_in_buf: int = 0 # offset of intro within the buffer
) -> List[str]:
    b = introdatabuffer
    entries: List[Tuple[str, int, int]] = []

    def _add(name: str, rel_off: int, size: int):
        file_off = lc_off + base_off_in_buf + rel_off
        entries.append((name, file_off, size))

    def _add_with_value(name: str, rel_off: int, size: int, kind: str):
        if not WRITEVALUETONAME:
            return _add(name, rel_off, size)
        try:
            if kind == "f32":
                val = _fmt_f32(f32(b, base_off_in_buf + rel_off))
                entries.append((f"{name}_({val})", lc_off + base_off_in_buf + rel_off, size))
            elif kind == "u16":
                val = u16(b, base_off_in_buf + rel_off)
                entries.append((f"{name}_({val})", lc_off + base_off_in_buf + rel_off, size))
            else:
                _add(name, rel_off, size)
        except Exception:
            _add(name, rel_off, size)

    # --- Header ---
    header_fields: List[Tuple[str, int, int]] = [
        ("chromatix_version", 0x00, 2),
        ("Revision",          0x02, 1),
        ("Major",             0x03, 1),
        ("Minor",             0x04, 1),
        ("Revision",          0x05, 1),
        ("Build",             0x08, 1),
        ("Gain_Start",        0x0C, 4),
        ("Gain_End",          0x10, 4),
        ("Lux_Index_Start",   0x14, 2),
        ("Lux_Index_End",     0x18, 2),
        ("CCTTrigger",        0x1C, 2),
        ("CCTTrigger",        0x20, 2),
        ("CCTTrigger",        0x24, 2),
        ("CCTTrigger",        0x28, 2),
    ]
    _chk(b, base_off_in_buf + 0x28, 2)

    for name, rel, size in header_fields:
        if name == "CCTTrigger" and WRITEVALUETONAME:
            try:
                val = u16(b, base_off_in_buf + rel)
                entries.append((f"CCTTrigger_({val})", lc_off + base_off_in_buf + rel, size))
            except Exception:
                _add("CCTTrigger", rel, size)
        elif name in _NAME_VALUE_FLOAT:
            _add_with_value(name, rel, size, "f32")
        elif name in _NAME_VALUE_U16:
            _add_with_value(name, rel, size, "u16")
        else:
            _add(name, rel, size)

    # --- Linearization cluster detection ---
    FLOATS_CNT, FLOATS_SIZE, SLOPES_SIZE = 8, 32, 34
    GAP_BEFORE, LOF, HIF = 6, 0.85, 1.00

    floats_hits: List[int] = []
    i = 0
    end_scan = len(b) - FLOATS_SIZE
    while i <= end_scan:
        try:
            vals = [f32(b, i + 4*k) for k in range(FLOATS_CNT)]
        except Exception:
            break
        if all(LOF <= v <= HIF for v in vals):
            floats_hits.append(i)
            i += FLOATS_SIZE
        else:
            i += 4
    floats_hits.sort()

    main_group: List[int] = []
    if floats_hits:
        CLUSTER_GAP_MAX = 0x100
        main_group.append(floats_hits[0])
        prev_off = floats_hits[0]
        for off_v in floats_hits[1:]:
            if (off_v - prev_off) <= CLUSTER_GAP_MAX:
                main_group.append(off_v); prev_off = off_v
            else:
                break

    last_floats_end_rel: Optional[int] = None
    for idx, f_rel in enumerate(main_group, start=1):
        slopes_end_rel   = f_rel - GAP_BEFORE
        slopes_start_rel = slopes_end_rel - SLOPES_SIZE
        if 0 <= slopes_start_rel and slopes_end_rel <= len(b):
            entries.append(("Linearization_Slopes_%d" % idx, lc_off + base_off_in_buf + slopes_start_rel, SLOPES_SIZE))
        entries.append(("Linearization_Floats_%d" % idx, lc_off + base_off_in_buf + f_rel, FLOATS_SIZE))
        last_floats_end_rel = f_rel + FLOATS_SIZE

    # --- If you can't find the ruler: immediately intro + LSC and exit ---
    if last_floats_end_rel is None:
        rows_intro   = _finalize_entries(entries)
        start_at_abs = lc_off + base_off_in_buf
        rows_lsc = get_chromatix_LscAndGolden(
            introdatabuffer,
            lc_off,
            LCLENGTH,
            start_at_abs=start_at_abs,
            data_origin_abs=lc_off  # the buffer starts on the file with lc_off
        )
        return rows_intro + rows_lsc  # ←HERE return MUST BE INSIDE if

    # --- Control_Trigger (4×1 byte) ---
    for ofs_add in range(4):
        rel = last_floats_end_rel + ofs_add
        if 0 <= rel < len(b):
            entries.append(("Control_Trigger", lc_off + base_off_in_buf + rel, 1))
    next_rel = last_floats_end_rel + 4

    # --- Trigger_Points (up to 3 blocks of 16 bytes) ---
    TP_BLOCK_SIZE, TP_MAX_BLOCKS = 16, 3
    TP_LO, TP_HI = 1.0, 100.0

    rel_cursor = next_rel
    tp_scanned_upto = rel_cursor
    tp_index = 0
    while tp_index < TP_MAX_BLOCKS and rel_cursor + TP_BLOCK_SIZE <= len(b):
        if not (_is_f32_in(b, rel_cursor + 0x00, TP_LO, TP_HI) and _is_f32_in(b, rel_cursor + 0x04, TP_LO, TP_HI)):
            break
        try:
            lux_s = u16(b, rel_cursor + 0x08)
            pad1  = u16(b, rel_cursor + 0x0A)
            lux_e = u16(b, rel_cursor + 0x0C)
            pad2  = u16(b, rel_cursor + 0x0E)
        except Exception:
            break
        if not (1 <= lux_s <= 2000 and 1 <= lux_e <= 2000 and pad1 == 0 and pad2 == 0):
            break

        tp_index += 1
        for nm, ofs_rel, sz, kind in (
            ("Gain_Start",      0x00, 4, "f32"),
            ("Gain_End",        0x04, 4, "f32"),
            ("Lux_Index_Start", 0x08, 2, "u16"),
            ("Lux_Index_End",   0x0C, 2, "u16"),
        ):
            if nm in _NAME_VALUE_FLOAT or nm in _NAME_VALUE_U16:
                try:
                    if kind == "f32":
                        vv = _fmt_f32(f32(b, rel_cursor + ofs_rel))
                        nm_full = f"{nm}_({vv})" if WRITEVALUETONAME else nm
                    else:
                        vv = u16(b, rel_cursor + ofs_rel)
                        nm_full = f"{nm}_({vv})" if WRITEVALUETONAME else nm
                except Exception:
                    nm_full = nm
            else:
                nm_full = nm
            entries.append((nm_full, lc_off + base_off_in_buf + rel_cursor + ofs_rel, sz))

        rel_cursor += TP_BLOCK_SIZE
        tp_scanned_upto = rel_cursor

    # --- CCTTrigger to Rolloff_LED ---
    ROLL_LO, ROLL_HI = 1.0, 10.0
    scan = tp_scanned_upto
    rolloff_led_rel = None
    while scan + 8 <= len(b):
        if _is_f32_in(b, scan, ROLL_LO, ROLL_HI) and _is_f32_in(b, scan + 4, ROLL_LO, ROLL_HI):
            rolloff_led_rel = scan
            break
        scan += 2

    cct_end_rel = rolloff_led_rel if rolloff_led_rel is not None else len(b)
    cct_ptr = tp_scanned_upto
    while cct_ptr + 4 <= cct_end_rel:
        try:
            val = u16(b, cct_ptr + 0)
            pad = u16(b, cct_ptr + 2)
        except Exception:
            break
        if not (1 <= val <= 30000 and pad == 0):
            break
        nm = f"CCTTrigger_({val})" if WRITEVALUETONAME else "CCTTrigger"
        entries.append((nm, lc_off + base_off_in_buf + cct_ptr + 0, 2))
        cct_ptr += 4

    # --- Rolloff_LED / Strobe ---
    if rolloff_led_rel is not None:
        try:
            vs = _fmt_f32(f32(b, rolloff_led_rel + 0x00))
            nm_s = f"Rolloff_LED_Mesh_Rolloff_Start_({vs})" if WRITEVALUETONAME else "Rolloff_LED_Mesh_Rolloff_Start"
        except Exception:
            nm_s = "Rolloff_LED_Mesh_Rolloff_Start"
        entries.append((nm_s, lc_off + base_off_in_buf + rolloff_led_rel + 0x00, 4))

        try:
            ve = _fmt_f32(f32(b, rolloff_led_rel + 0x04))
            nm_e = f"Rolloff_LED_Mesh_Rolloff_End_({ve})" if WRITEVALUETOHAME else "Rolloff_LED_Mesh_Rolloff_End"
        except Exception:
            nm_e = "Rolloff_LED_Mesh_Rolloff_End"
        entries.append((nm_e, lc_off + base_off_in_buf + rolloff_led_rel + 0x04, 4))

        strobe_scan_start = rolloff_led_rel + 8
    else:
        strobe_scan_start = cct_ptr

    if strobe_scan_start is not None and strobe_scan_start + 8 <= len(b):
        if _is_f32_in(b, strobe_scan_start, ROLL_LO, ROLL_HI) and _is_f32_in(b, strobe_scan_start + 4, ROLL_LO, ROLL_HI):
            try:
                vs2 = _fmt_f32(f32(b, strobe_scan_start + 0x00))
                nm_s2 = f"Rolloff_Strobe_Mesh_Rolloff_Start_({vs2})" if WRITEVALUETONAME else "Rolloff_Strobe_Mesh_Rolloff_Start"
            except Exception:
                nm_s2 = "Rolloff_Strobe_Mesh_Rolloff_Start"
            entries.append((nm_s2, lc_off + base_off_in_buf + strobe_scan_start + 0x00, 4))

            try:
                ve2 = _fmt_f32(f32(b, strobe_scan_start + 0x04))
                nm_e2 = f"Rolloff_Strobe_Mesh_Rolloff_End_({ve2})" if WRITEVALUETOHAME else "Rolloff_Strobe_Mesh_Rolloff_End"
            except Exception:
                nm_e2 = "Rolloff_Strobe_Mesh_Rolloff_End"
            entries.append((nm_e2, lc_off + base_off_in_buf + strobe_scan_start + 0x04, 4))

    # --- Finale: Intro + LSC ---
    rows_intro = _finalize_entries(entries)

    # lower limit for LSC scan
    if 'strobe_scan_start' in locals() and strobe_scan_start is not None:
        scan_after_rel = strobe_scan_start + 8
    elif 'rolloff_led_rel' in locals() and rolloff_led_rel is not None:
        scan_after_rel = rolloff_led_rel + 8
    elif 'cct_ptr' in locals() and cct_ptr is not None:
        scan_after_rel = cct_ptr
    elif 'last_floats_end_rel' in locals() and last_floats_end_rel is not None:
        scan_after_rel = last_floats_end_rel
    else:
        scan_after_rel = 0

    start_at_abs = lc_off + base_off_in_buf + (scan_after_rel or 0)

    rows_lsc = get_chromatix_LscAndGolden(
        introdatabuffer,
        lc_off,          # absolute
        LCLENGTH,
        start_at_abs=start_at_abs,
        data_origin_abs=lc_off
    )

    return rows_intro + rows_lsc


