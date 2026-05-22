from typing import List, Tuple
import struct

MODULE_VER = "0309"

# ── Indexing / Names / Addresses Settings ─────────────────────────────────────
ID_START_NORMAL = 0x0C00
ID_END_REVERSE = 0x0CBF # if REVERSE_INDEX=1
REVERSE_INDEX = 1 # 0 — normal ID growth, 1 — from end down to 0x0CBF
WRITEVALUETONAME = 1 # 1 — append value to name ( ..._(123) )
USEDUMPOFFSETINSTEAD = 0 # 1 — absolute offset base_off_in_buf, 0 — lc_off+base_off_in_buf


AllowDebug = 0
def _dbg(*args, **kwargs):
    if AllowDebug:
        print(*args, **kwargs)

def align_up(v: int, a: int) -> int:
    return (v + (a - 1)) & ~(a - 1)

def hx8(v: int) -> str:
    return f"{v:08X}"

def _fmt_f32(v: float) -> str:
    # human-readable without exponent and without extra zeros
    s = f"{v:.6g}"
    if "e" in s or "E" in s:
        s = f"{v:.6f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

def _read_prim(b: bytes, off: int, kind: str):
    if kind == "u8":
        return struct.unpack_from("<B", b, off)[0]
    if kind == "u16":
        return struct.unpack_from("<H", b, off)[0]
    if kind == "u32":
        return struct.unpack_from("<I", b, off)[0]
    if kind == "f32":
        return struct.unpack_from("<f", b, off)[0]
    raise ValueError(f"unknown prim kind {kind}")

# ── a small "type system" to describe C structures ────────────────

class PrimSpec:
    def __init__(self, kind: str, add_value: bool = False):
        """
        kind: 'u8' | 'u16' | 'u32' | 'f32'
        add_value: whether to append _(value) to the field name
        """
        self.kind = kind
        self.add_value = add_value

    def sizeof(self) -> int:
        if self.kind == "u8":  return 1
        if self.kind == "u16": return 2
        if self.kind in ("u32", "f32"):
            return 4
        raise ValueError

    def alignof(self) -> int:
        if self.kind == "u8":  return 1
        if self.kind == "u16": return 2
        if self.kind in ("u32", "f32"):
            return 4
        raise ValueError

class ArraySpec:
    def __init__(self, elem, count: int, expand_elems: bool):
        """
        elem: PrimSpec or StructSpec
        count: array length
        expand_elems:
        True -> expand as [0], [1], ... and recursively go inside
        (used for arrays of structures)
        False -> DO NOT expand element-by-element; treat the entire block as a single field
        (used for arrays of primitives like U16[130])
        """
        self.elem = elem
        self.count = count
        self.expand_elems = expand_elems

    def sizeof(self) -> int:
        return sizeof(self.elem) * self.count

    def alignof(self) -> int:
        return alignof(self.elem)

class FieldSpec:
    def __init__(self, name: str, tspec):
        self.name = name
        self.tspec = tspec

class StructSpec:
    def __init__(self, fields: List[FieldSpec]):
        self.fields = fields
        self._layout_cache = None  # (offsets, total_size, max_align)

    def layout(self):
        """
        We calculate the layout of a C structure:
        - each field is aligned to alignof(field)
        - the struct size is aligned to max_align(struct)
        """
        if self._layout_cache is not None:
            return self._layout_cache

        offsets: List[int] = []
        cur = 0
        max_align = 1

        for f in self.fields:
            al = alignof(f.tspec)
            max_align = max(max_align, al)
            cur = align_up(cur, al)
            offsets.append(cur)
            cur += sizeof(f.tspec)

        total = align_up(cur, max_align)
        self._layout_cache = (offsets, total, max_align)
        return self._layout_cache

    def sizeof(self) -> int:
        return self.layout()[1]

    def alignof(self) -> int:
        return self.layout()[2]

def sizeof(spec) -> int:
    if isinstance(spec, PrimSpec):   return spec.sizeof()
    if isinstance(spec, ArraySpec):  return spec.sizeof()
    if isinstance(spec, StructSpec): return spec.sizeof()
    raise ValueError

def alignof(spec) -> int:
    if isinstance(spec, PrimSpec):   return spec.alignof()
    if isinstance(spec, ArraySpec):  return spec.alignof()
    if isinstance(spec, StructSpec): return spec.alignof()
    raise ValueError

# convenient primitive constructors
def u8 (add_value: bool = False) -> PrimSpec:  return PrimSpec("u8",  add_value)
def u16(add_value: bool = False) -> PrimSpec:  return PrimSpec("u16", add_value)
def u32(add_value: bool = False) -> PrimSpec:  return PrimSpec("u32", add_value)
def f32(add_value: bool = False) -> PrimSpec:  return PrimSpec("f32", add_value)

# ── 0309 version structure specification ───────────────────────────────────────
#
# Everything below is taken from chromartix_common_0309.h / chromatix_0309.h:
# - chromatix_version_info (version, id, flags)
# - chromatix_pedestal_correction (enable/control + pctable[2])
# pctable[*] = mesh_pedestal_table_size + 4 channels of 130 U16 each
# - chromatix_L (linearization_enable..., control_linearization(u8),
# trigger_point_type, then two lowlight/normal linearization tables)
# ➜ 0309 DOES NOT have last_region_unity_slope_enable and DOES NOT have linearization_v2_data. :contentReference[oaicite:5]{index=5}
# - Chromatix_BLSS_data (BLSS_enable, trigger, offsets) :contentReference[oaicite:6]{index=6}
# - chromatix_rolloff (CCT triggers H/A/D65, LED/Strobe start/end,
# scale_cubic, subgrid offsets, + a bunch of RGGB rolloff grids of 221 floats)
# :contentReference[oaicite:7]{index=7}
# - chromatix_LA_special_effects (5 LUTs of 64 floats) :contentReference[oaicite:8]{index=8}
#

# sub-struct: chromatix_app_version_type
chromatix_app_version_type = StructSpec([
    FieldSpec("major",    u8()),
    FieldSpec("minor",    u8()),
    FieldSpec("revision", u8()),
    FieldSpec("build",    u8()),
])

# main header block: ChromatixVersionInfoType
ChromatixVersionInfoType = StructSpec([
    FieldSpec("chromatix_version",          u16()),
    FieldSpec("revision_number",            u16()),
    FieldSpec("chromatix_app_version",      chromatix_app_version_type),
    FieldSpec("chromatix_header_type",      u32()),
    FieldSpec("is_compressed",              u8()),
    FieldSpec("is_mono",                    u8()),
    FieldSpec("is_video",                   u8()),
    FieldSpec("reserved_align",             u8()),
    FieldSpec("chromatix_mode",             u32()),
    FieldSpec("target_id",                  u32()),
    FieldSpec("chromatix_id",               u32()),
    # it's 16 bytes in total, usually 4 * U32
    FieldSpec("reserved",                   ArraySpec(u32(), 4, expand_elems=False)),
])

# pedestal correction single table (mesh / black levels)
pedestalcorrection_table = StructSpec([
    FieldSpec("mesh_pedestal_table_size",   u16(add_value=True)),
    FieldSpec("channel_black_level_r",     ArraySpec(u16(), 130, expand_elems=False)),
    FieldSpec("channel_black_level_gr",    ArraySpec(u16(), 130, expand_elems=False)),
    FieldSpec("channel_black_level_gb",    ArraySpec(u16(), 130, expand_elems=False)),
    FieldSpec("channel_black_level_b",     ArraySpec(u16(), 130, expand_elems=False)),
])

# chromatix_pedestalcorrection_type (0309: enable/control + pctable[2])
chromatix_pedestalcorrection_type = StructSpec([
    FieldSpec("pedestalcorrection_enable",         u32()),
    FieldSpec("pedestalcorrection_control_enable", u32()),
    FieldSpec("pctable", ArraySpec(pedestalcorrection_table, 2, expand_elems=True)),
])

# linearization LUT block (8+9 entries for R,GR,GB,B)
chromatix_linearization_type = StructSpec([
    FieldSpec("r_lut_p",      ArraySpec(u16(), 8, expand_elems=False)),
    FieldSpec("r_lut_base",   ArraySpec(u16(), 9, expand_elems=False)),
    FieldSpec("gr_lut_p",     ArraySpec(u16(), 8, expand_elems=False)),
    FieldSpec("gr_lut_base",  ArraySpec(u16(), 9, expand_elems=False)),
    FieldSpec("gb_lut_p",     ArraySpec(u16(), 8, expand_elems=False)),
    FieldSpec("gb_lut_base",  ArraySpec(u16(), 9, expand_elems=False)),
    FieldSpec("b_lut_p",      ArraySpec(u16(), 8, expand_elems=False)),
    FieldSpec("b_lut_base",   ArraySpec(u16(), 9, expand_elems=False)),
])

# trigger_point_type (gain_start/end f32, lux_index_start/end U32)
trigger_point_type = StructSpec([
    FieldSpec("gain_start",        f32(add_value=True)),
    FieldSpec("gain_end",          f32(add_value=True)),
    FieldSpec("lux_index_start",   u32(add_value=True)),
    FieldSpec("lux_index_end",     u32(add_value=True)),
])

# chromatix_L (0309):
# int linearization_enable;
# int linearization_control_enable;
# tuning_control_type control_linearization; // U8
# trigger_point_type linearization_lowlight_trigger;
# chromatix_linearization_type linear_table_lowlight;
# chromatix_linearization_type linear_table_normal;
chromatix_L_type = StructSpec([
    FieldSpec("linearization_enable",          u32()),
    FieldSpec("linearization_control_enable",  u32()),
    FieldSpec("control_linearization",         u8()),
    FieldSpec("linearization_lowlight_trigger", trigger_point_type),
    FieldSpec("linear_table_lowlight",         chromatix_linearization_type),
    FieldSpec("linear_table_normal",           chromatix_linearization_type),
])

# BLSS part
Chromatix_BLSS_type = StructSpec([
    FieldSpec("black_level_offset", u16()),
])

Chromatix_blk_subtract_scale_type = StructSpec([
    FieldSpec("BLSS_enable",              u32()),
    FieldSpec("BLSS_control_enable",      u32()),
    FieldSpec("control_BLSS",             u8()),
    FieldSpec("BLSS_low_light_trigger",   trigger_point_type),
    FieldSpec("black_level_lowlight",     Chromatix_BLSS_type),
    FieldSpec("black_level_normal",       Chromatix_BLSS_type),
])

# rolloff triggers
chromatix_CCT_trigger_type = StructSpec([
    FieldSpec("CCT_start", u32(add_value=True)),
    FieldSpec("CCT_end",   u32(add_value=True)),
])

# mesh_rolloff_array_type:
# U16 mesh_rolloff_table_size;
# float r_gain[221], gr_gain[221], gb_gain[221], b_gain[221];
mesh_rolloff_array_type = StructSpec([
    FieldSpec("mesh_rolloff_table_size", u16(add_value=True)),
    FieldSpec("r_gain",   ArraySpec(f32(), 221, expand_elems=False)),
    FieldSpec("gr_gain",  ArraySpec(f32(), 221, expand_elems=False)),
    FieldSpec("gb_gain",  ArraySpec(f32(), 221, expand_elems=False)),
    FieldSpec("b_gain",   ArraySpec(f32(), 221, expand_elems=False)),
])

# chromatix_rolloff (0309):
chromatix_rolloff_type = StructSpec([
    FieldSpec("rolloff_H_trigger",         chromatix_CCT_trigger_type),
    FieldSpec("rolloff_A_trigger",         chromatix_CCT_trigger_type),
    FieldSpec("rolloff_D65_trigger",       chromatix_CCT_trigger_type),
    FieldSpec("rolloff_LED_start",         f32(add_value=True)),
    FieldSpec("rolloff_LED_end",           f32(add_value=True)),
    FieldSpec("rolloff_Strobe_start",      f32(add_value=True)),
    FieldSpec("rolloff_Strobe_end",        f32(add_value=True)),
    FieldSpec("scale_cubic",               u32()),
    FieldSpec("subgridh_offset",           u32()),
    FieldSpec("subgridv_offset",           u32()),
    # ROLLOFF_MAX_LIGHT == 4 (TL84, A, D65, H)
    FieldSpec("mesh_rolloff_table",
              ArraySpec(mesh_rolloff_array_type, 4, expand_elems=True)),
    FieldSpec("mesh_rolloff_table_lowlight",
              ArraySpec(mesh_rolloff_array_type, 4, expand_elems=True)),
    FieldSpec("mesh_rolloff_table_golden_module",
              ArraySpec(mesh_rolloff_array_type, 4, expand_elems=True)),
    FieldSpec("mesh_rolloff_table_LED",
              mesh_rolloff_array_type),
    FieldSpec("mesh_rolloff_table_Strobe",
              mesh_rolloff_array_type),
])

# LA (special effects LUTs), every LUT — 64 float
chromatix_LA_special_effects_type = StructSpec([
    FieldSpec("LA_LUT_backlit",    ArraySpec(f32(), 64, expand_elems=False)),
    FieldSpec("LA_LUT_solarize",   ArraySpec(f32(), 64, expand_elems=False)),
    FieldSpec("LA_LUT_posterize",  ArraySpec(f32(), 64, expand_elems=False)),
    FieldSpec("LA_LUT_blackboard", ArraySpec(f32(), 64, expand_elems=False)),
    FieldSpec("LA_LUT_whiteboard", ArraySpec(f32(), 64, expand_elems=False)),
])

# This is the same root common block for 0309
chromatix_VFE_common_type_0309 = StructSpec([
    FieldSpec("version_info",        ChromatixVersionInfoType),
    FieldSpec("pedestal_correction", chromatix_pedestalcorrection_type),
    FieldSpec("L",                   chromatix_L_type),
    FieldSpec("BLSS_data",           Chromatix_blk_subtract_scale_type),
    FieldSpec("rolloff",             chromatix_rolloff_type),
    FieldSpec("LA_special_effects",  chromatix_LA_special_effects_type),
])

# ── a recursive emitter that turns spec into CSV strings ───────────

def _emit_spec(
    tspec,
    prefix: str,
    rel_off: int,
    entries: List[Tuple[str, int, int, object, object]],
    b: bytes,
    start_abs: int,
    base_in_buf: int
):
    """
    tspec: PrimSpec | ArraySpec | StructSpec
    prefix: current name (without leading dot)
    rel_off: offset relative to base_in_buf from the start of the structure
    entries: accumulate [(name, abs_off, size, tspec_for_value, raw_value_or_None), ...]
    b: entire introdatabuffer
    start_abs: absolute "base" for output (either lc_off+base_off_in_buf or base_off_in_buf)
    base_in_buf: where the 0th byte of the structure is located within b
    """

    if isinstance(tspec, StructSpec):
        field_offsets, _total, _al = tspec.layout()
        for f, f_rel in zip(tspec.fields, field_offsets):
            new_prefix = prefix + ("." if prefix else "") + f.name
            _emit_spec(
                f.tspec,
                new_prefix,
                rel_off + f_rel,
                entries,
                b,
                start_abs,
                base_in_buf
            )

    elif isinstance(tspec, ArraySpec):
        elem = tspec.elem
        elem_size = sizeof(elem)

        if tspec.expand_elems:
            # array of structures → pctable[0]..., chromatix_mesh_rolloff_table[3]...
            for idx in range(tspec.count):
                new_prefix = f"{prefix}[{idx}]"
                _emit_spec(
                    elem,
                    new_prefix,
                    rel_off + idx * elem_size,
                    entries,
                    b,
                    start_abs,
                    base_in_buf
                )
        else:
            # array of primitives → single row with common block
            abs_off = start_abs + rel_off
            size = elem_size * tspec.count
            entries.append((prefix, abs_off, size, None, None))

    elif isinstance(tspec, PrimSpec):
        abs_off = start_abs + rel_off
        size = tspec.sizeof()
        val = None
        if tspec.add_value and WRITEVALUETONAME:
            val = _read_prim(b, base_in_buf + rel_off, tspec.kind)
        entries.append((prefix, abs_off, size, tspec, val))

    else:
        raise ValueError("Unknown tspec type in _emit_spec")

def _finalize_entries(
    entries: List[Tuple[str, int, int, object, object]]
) -> List[str]:
    """
    We convert the accumulated entries into ready-made CSV strings:
    ID_HEX, field_name, OFFSET_HEX, SIZE_HEX
    """
    n = len(entries)
    rows: List[str] = []

    if REVERSE_INDEX:
        start_id = ID_END_REVERSE - (n - 1)
    else:
        start_id = ID_START_NORMAL

    cur_id = start_id
    for (name, abs_off, size, tspec, val) in entries:
        out_name = name
        if isinstance(tspec, PrimSpec) and tspec.add_value and WRITEVALUETONAME and val is not None:
            if tspec.kind == "f32":
                vs = _fmt_f32(val)
            else:
                vs = str(val)
            out_name = f"{name}_({vs})"
        rows.append(f"{hx8(cur_id)},{out_name},{hx8(abs_off)},{hx8(size)}")
        cur_id += 1

    return rows

# ── public API (important: the name intro_row_parser is expected by your tool) ──

def intro_row_parser(
    introdatabuffer: bytes,
    lc_off: int,
    base_off_in_buf: int = 0
) -> List[str]:
    """
    Returns a list of strings:
    ID_HEX, field_path, ABS_OFFSET_HEX, SIZE_HEX

    introdatabuffer: section/dump bytes
    lc_off: absolute offset of the section in the source file
    base_off_in_buf: offset of the structure within the introdatabuffer (usually 0)

    USEDUMPOFFSETINSTEAD:
    0 => absolute offset = lc_off + base_off_in_buf + local_offset
    1 => absolute offset = base_off_in_buf + local_offset
    (useful if the introdatabuffer has already been extracted from the dump and lc_off is not needed)
    """

    b = introdatabuffer
    if USEDUMPOFFSETINSTEAD:
        start_abs = base_off_in_buf
    else:
        start_abs = lc_off + base_off_in_buf

    entries: List[Tuple[str, int, int, object, object]] = []

    # expand the ENTIRE chromatix_VFE_common_type_0309
    _emit_spec(
        chromatix_VFE_common_type_0309,
        prefix="",
        rel_off=0,
        entries=entries,
        b=b,
        start_abs=start_abs,
        base_in_buf=base_off_in_buf,
    )

    return _finalize_entries(entries)
