# -*- coding: utf-8 -*-
"""
Parser chromatix VFE common 0x0306.

Structures based on chromatix_0306.h and chromatix_common_0306.h:
- At 0x0305, the top type chromatix_VFE_common_type contains:
    * chromatix_version (u16)
    * chromatix_app_version (major/minor/revision/build according to u8)
    * is_compressed (u8)
    * revision_number (u16)
    * chromatix_pedestal_correction (2 HDR pedestal tables)
    * chromatix_L (linearization, ALREADY truncated in 0x0305: only lowlight/normal)
    * Chromatix_BLSS_data (new Black Level Subtract & Scale block)
    * chromatix_rolloff (rolloff + LED/Strobe + mesh grid)
    * chromatix_LA_special_effects (LA LUTs)
:contentReference[oaicite:3]{index=3}

Output:
List of strings like:
    ID_HEX,name,ABS_OFFSET_HEX,LEN_HEX

Flags:
REVERSE_INDEX = 1 → Number IDs from the end (ID_END_REVERSE ..)
WRITEVALUETONAME = 1 → Add the value to the name for gain_start_(...), etc.
USEDUMPOFFSETINSTEAD = 1 → Calculate the absolute offset "as in the dump"
                                (i.e., from base_off_in_buf), not lc_off+base_off_in_buf

Exported function:
  intro_row_parser(data: bytes, lc_off: int, base_off_in_buf: int = 0) -> List[str]
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional
import struct

# ── Global settings ─ ... Prints
MODULE_VER              = "0306"
ID_START_NORMAL         = 0x0C00
ID_END_REVERSE          = 0x0CBF
REVERSE_INDEX           = 1      
WRITEVALUETONAME        = 1      
USEDUMPOFFSETINSTEAD    = 0      
AllowDebug              = 0     

def _dbg(*args, **kwargs):
    if AllowDebug:
        print(*args, **kwargs)

def _align_up(off: int, align: int) -> int:
    if align <= 1:
        return off
    return (off + (align - 1)) & ~(align - 1)

@dataclass(frozen=True)
class PrimType:
    name: str
    fmt: str
    size: int
    align: int

U8   = PrimType("u8",   "<B", 1, 1)
U16  = PrimType("u16",  "<H", 2, 2)
I32  = PrimType("i32",  "<i", 4, 4)
U32  = PrimType("u32",  "<I", 4, 4)
F32  = PrimType("f32",  "<f", 4, 4)

@dataclass
class FieldSpec:
    name: str
    type_spec: Union['StructSpec', PrimType]
    count: int = 1 # array (>1) or scalar (=1)

@dataclass
class StructSpec:
    name: str
    fields: List[FieldSpec] = field(default_factory=list)
    _layout_cached: Optional[dict] = field(default=None, init=False, repr=False)

    def align(self) -> int:
        if not self.fields:
            return 1
        return max(_get_align(f.type_spec) for f in self.fields)

    def calc_layout(self) -> dict:
        if self._layout_cached is not None:
            return self._layout_cached

        cur_off = 0
        layout_fields = []
        struct_align = self.align()

        for fs in self.fields:
            f_align = _get_align(fs.type_spec)
            cur_off = _align_up(cur_off, f_align)

            elem_size = _get_size(fs.type_spec)
            total_size = elem_size * fs.count

            layout_fields.append({
                'field': fs,
                'offset': cur_off,
                'size_each': elem_size,
                'size_total': total_size,
                'align': f_align,
            })
            cur_off += total_size

        struct_size = _align_up(cur_off, struct_align)

        self._layout_cached = {
            'fields': layout_fields,
            'size': struct_size,
            'align': struct_align,
        }
        return self._layout_cached

def _get_align(t: Union[StructSpec, PrimType]) -> int:
    if isinstance(t, PrimType):
        return t.align
    return t.align()

def _get_size(t: Union[StructSpec, PrimType]) -> int:
    if isinstance(t, PrimType):
        return t.size
    return t.calc_layout()['size']

def _safe_read_prim_scalar(buf: bytes, off: int, prim: PrimType):
    """
    Read a single simple value at offset off in buf.
    If the slice extends beyond the dump, we discard it, and we won't embed the value later.
    """
    end = off + prim.size
    if end > len(buf):
        raise ValueError("out of range for value embed")
    return struct.unpack_from(prim.fmt, buf, off)[0]

def _fmt_f32(v: float) -> str:
    s = f"{v:.6g}"
    if "e" in s or "E" in s:
        s = f"{v:.6f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

def _append_value_if_needed(field_path: str, val, prim: PrimType) -> str:
    """
    If the field is familiar (gain_start, lux_index_start, mesh_pedestal_table_size,
    rolloff_LED_start, etc.), then add _(value) to the end of the name.
    This is definitely in 0305: trigger_point_type (gain_start, lux_index_start, ...),
    LED/Strobe rolloff start/end, mesh_pedestal_table_size. :contentReference[oaicite:4]{index=4}
    """
    if not WRITEVALUETONAME or val is None:
        return field_path

    tail = field_path.split(".")[-1]

    NEED_FLOAT = {
        "gain_start",
        "gain_end",
        "rolloff_LED_start",
        "rolloff_LED_end",
        "rolloff_Strobe_start",
        "rolloff_Strobe_end",
    }
    NEED_U32 = {
        "lux_index_start",
        "lux_index_end",
        "CCT_start",
        "CCT_end",
    }
    NEED_U16 = {
        "mesh_pedestal_table_size",
    }

    try:
        if tail in NEED_FLOAT and prim is F32:
            return f"{field_path}_({_fmt_f32(float(val))})"
        if tail in NEED_U32 and prim in (I32, U32):
            return f"{field_path}_({int(val)})"
        if tail in NEED_U16 and prim is U16:
            return f"{field_path}_({int(val)})"
    except Exception:
        pass

    return field_path

# ── array size constants from 0x0305 ──────────────────────────────────
MESH_PEDESTALTABLE_SIZE = 13 * 10 # 130 U16 points in the pedestal table per channel :contentReference[oaicite:5]{index=5}
MESH_ROLLOFF_SIZE = 17 * 13 # 221 F32 points for rolloff gain grids :contentReference[oaicite:6]{index=6}
ROLLOFF_MAX_LIGHT       = 3         # TL84 / A / D65 (ROLLOFF_MAX_LIGHT) :contentReference[oaicite:7]{index=7}

# ── structures 0x0305 (minimum required for common header) ───────────────

# from chromatix_0305.h: camera tuning version, 4 bytes major/minor/revision/build :contentReference[oaicite:8]{index=8}
chromatix_app_version_type = StructSpec("chromatix_app_version_type", [
    FieldSpec("major",    U8),
    FieldSpec("minor",    U8),
    FieldSpec("revision", U8),
    FieldSpec("build",    U8),
])

# trigger_point_type: gain_start/gain_end/lux_index_start/lux_index_end :contentReference[oaicite:9]{index=9}
trigger_point_type = StructSpec("trigger_point_type", [
    FieldSpec("gain_start",      F32),
    FieldSpec("gain_end",        F32),
    FieldSpec("lux_index_start", I32),
    FieldSpec("lux_index_end",   I32),
])

# chromatix_CCT_trigger_type: CCT_start / CCT_end (u32) :contentReference[oaicite:10]{index=10}
chromatix_CCT_trigger_type = StructSpec("chromatix_CCT_trigger_type", [
    FieldSpec("CCT_start", U32),
    FieldSpec("CCT_end",   U32),
])

# pedestalcorrection_table: grid size + 4 channels of 130 U16 each :contentReference[oaicite:11]{index=11}
pedestalcorrection_table = StructSpec("pedestalcorrection_table", [
    FieldSpec("mesh_pedestal_table_size", U16),
    FieldSpec("channel_black_level_r",    U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gr",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gb",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_b",    U16, MESH_PEDESTALTABLE_SIZE),
])

# chromatix_pedestalcorrection_type: enable, control_enable, and pctable[2] :contentReference[oaicite:12]{index=12}
chromatix_pedestalcorrection_type = StructSpec("chromatix_pedestalcorrection_type", [
    FieldSpec("pedestalcorrection_enable",         I32),
    FieldSpec("pedestalcorrection_control_enable", I32),
    FieldSpec("pctable", pedestalcorrection_table, 2),
])

# chromatix_linearization_type for 0x0305:
# *_lut_delta[9] was removed from 0305, leaving only *_lut_p[8] and *_lut_base[9] per channel. :contentReference[oaicite:13]{index=13}
chromatix_linearization_type = StructSpec("chromatix_linearization_type", [
    # R
    FieldSpec("r_lut_p",     U16, 8),
    FieldSpec("r_lut_base",  U16, 9),
    # GR
    FieldSpec("gr_lut_p",    U16, 8),
    FieldSpec("gr_lut_base", U16, 9),
    # GB
    FieldSpec("gb_lut_p",    U16, 8),
    FieldSpec("gb_lut_base", U16, 9),
    # B
    FieldSpec("b_lut_p",     U16, 8),
    FieldSpec("b_lut_base",  U16, 9),
])

# chromatix_L_type in 0x0305:
#  - linearization_enable / control_enable (int)
#  - control_linearization (tuning_control_type = U8)
#  - linearization_lowlight_trigger (trigger_point_type)
#  - linear_table_lowlight / normal (chromatix_linearization_type)
# 0x0305 NO LONGER has A/TL84/D65 separate tables and CCT triggers.
# They were in 0x0304 and were removed. :contentReference[oaicite:14]{index=14}
chromatix_L_type = StructSpec("chromatix_L_type", [
    FieldSpec("linearization_enable",          I32),
    FieldSpec("linearization_control_enable",  I32),

    FieldSpec("control_linearization",         U8),
    FieldSpec("linearization_lowlight_trigger", trigger_point_type),

    FieldSpec("linear_table_lowlight",         chromatix_linearization_type),
    FieldSpec("linear_table_normal",           chromatix_linearization_type),
])

# BLSS (Black Level Subtract & Scale), new in 0x0305 common: :contentReference[oaicite:15]{index=15}
Chromatix_BLSS_type = StructSpec("Chromatix_BLSS_type", [
    FieldSpec("black_level_offset", U16),
    FieldSpec("black_level_scale",  U16),
])

Chromatix_blk_subtract_scale_type = StructSpec("Chromatix_blk_subtract_scale_type", [
    FieldSpec("BLSS_enable",         I32),
    FieldSpec("BLSS_control_enable", I32),

    FieldSpec("control_BLSS",        U8),
    FieldSpec("BLSS_low_light_trigger", trigger_point_type),

    FieldSpec("black_level_lowlight", Chromatix_BLSS_type),
    FieldSpec("black_level_normal",   Chromatix_BLSS_type),
])

# rolloff tables: grids of 221 float values ​​per channel, plus three sets
# by light type + lowlight/golden + LED/Strobe. :contentReference[oaicite:16]{index=16}
mesh_rolloff_array_type = StructSpec("mesh_rolloff_array_type", [
    FieldSpec("mesh_rolloff_table_size", U16),
    FieldSpec("r_gain",   F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gr_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gb_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("b_gain",   F32, MESH_ROLLOFF_SIZE),
])

chromatix_rolloff_type = StructSpec("chromatix_rolloff_type", [
    FieldSpec("rolloff_A_trigger",    chromatix_CCT_trigger_type),
    FieldSpec("rolloff_D65_trigger",  chromatix_CCT_trigger_type),

    FieldSpec("rolloff_LED_start",    F32),
    FieldSpec("rolloff_LED_end",      F32),
    FieldSpec("rolloff_Strobe_start", F32),
    FieldSpec("rolloff_Strobe_end",   F32),

    FieldSpec("scale_cubic",          I32),
    FieldSpec("subgridh_offset",      I32),
    FieldSpec("subgridv_offset",      I32),

    FieldSpec("mesh_rolloff_table",               mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_lowlight",      mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_golden_module", mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_LED",           mesh_rolloff_array_type),
    FieldSpec("mesh_rolloff_table_Strobe",        mesh_rolloff_array_type),
])

# LA special effects LUTs: 5 arrays of 64 floats. :contentReference[oaicite:17]{index=17}
chromatix_LA_special_effects_type = StructSpec("chromatix_LA_special_effects_type", [
    FieldSpec("LA_LUT_backlit",    F32, 64),
    FieldSpec("LA_LUT_solarize",   F32, 64),
    FieldSpec("LA_LUT_posterize",  F32, 64),
    FieldSpec("LA_LUT_blackboard", F32, 64),
    FieldSpec("LA_LUT_whiteboard", F32, 64),
])

# Top-level structure at 0x0305:
# field order and types taken from chromatix_VFE_common_type in chromatix_common_0305.h. :contentReference[oaicite:18]{index=18}
chromatix_VFE_common_type = StructSpec("chromatix_VFE_common_type_0305", [
    FieldSpec("chromatix_version",      U16),
    FieldSpec("chromatix_app_version",  chromatix_app_version_type),
    FieldSpec("is_compressed",          U8),
    FieldSpec("revision_number",        U16),
    FieldSpec("pedestal_correction", chromatix_pedestalcorrection_type),
    FieldSpec("chromatix_L",                    chromatix_L_type),
    FieldSpec("BLSS_data",            Chromatix_blk_subtract_scale_type),
    FieldSpec("rolloff",              chromatix_rolloff_type),
    FieldSpec("LA_special_effects",   chromatix_LA_special_effects_type),
])

# ── Recursive traversal of a structure, building a list of fields ───────────────
def _walk_struct_entries(
    buf: bytes,
    base_abs_off: int, # absolute offset of this structure "in the file"
    struct_off: int, # offset of this structure within buf
    spec: StructSpec,
    prefix: str = ""
) -> List[Tuple[str, int, int]]:
    """
    Returns [(full_field_name, abs_offset, length_bytes), ...]
    Leaf elements = primitive or array of primitives.
    Nested structures - expand with dot notation and indices [i].
    """
    out: List[Tuple[str, int, int]] = []

    layout = spec.calc_layout()
    for ent in layout['fields']:
        fs = ent['field']
        foff = ent['offset']
        elem_size = ent['size_each']
        field_abs_off = base_abs_off + foff

        if isinstance(fs.type_spec, PrimType):
            prim = fs.type_spec

            if fs.count == 1:
                # single scalar → read value for name (if possible)
                try:
                    raw_val = _safe_read_prim_scalar(buf, struct_off + foff, prim)
                except Exception:
                    raw_val = None

                full_name = prefix + fs.name
                full_name = _append_value_if_needed(full_name, raw_val, prim)
                out.append((full_name, field_abs_off, prim.size))

            else:
                # array of simple types → one entry for the entire array
                full_name = prefix + fs.name
                out.append((full_name, field_abs_off, prim.size * fs.count))

        else:
            # nested structure
            sub_spec: StructSpec = fs.type_spec
            sub_size = _get_size(sub_spec)

            if fs.count == 1:
                out.extend(_walk_struct_entries(
                    buf,
                    base_abs_off=field_abs_off,
                    struct_off=struct_off + foff,
                    spec=sub_spec,
                    prefix=prefix + fs.name + "."
                ))
            else:
                for i in range(fs.count):
                    idx_abs_off = field_abs_off + i * sub_size
                    idx_struct_off = struct_off + foff + i * sub_size
                    out.extend(_walk_struct_entries(
                        buf,
                        base_abs_off=idx_abs_off,
                        struct_off=idx_struct_off,
                        spec=sub_spec,
                        prefix=prefix + f"{fs.name}[{i}]."
                    ))

    return out

def _finalize_rows(entries: List[Tuple[str, int, int]]) -> List[str]:
    """
    Assign ID and generate CSV:
      ID_HEX,name,ABS_OFFSET_HEX,LEN_HEX
    """
    n = len(entries)
    if REVERSE_INDEX:
        start_id = ID_END_REVERSE - (n - 1)
    else:
        start_id = ID_START_NORMAL

    rows: List[str] = []
    cur_id = start_id
    for name, file_off, size in entries:
        rows.append(f"{cur_id:08X},{name},{file_off:08X},{size:08X}")
        cur_id += 1
    return rows

# ── public functions ─ ...
def parse_chromatix_common(
    introdatabuffer: bytes,
    lc_off: int,
    base_off_in_buf: int = 0
) -> List[str]:
    """
    We build the final lines ID_HEX,name,OFFSET_HEX,SIZE_HEX 
    for structure chromatix_VFE_common_type (0x0305). 

    introdatabuffer - binary bytes (your .bin dump or ELF slice). 
    lc_off — "LCOFF" from the large file, if any. 
    base_off_in_buf — where chromatix_VFE_common_type actually starts in the introdatabuffer. 

    If USEDUMPOFFSETINSTEAD == 1: 
    absolute offset = base_off_in_buf + offset_in_structure 
    (that is, pure offsets relative to the dump). 
    Otherwise: 
    absolute offset = lc_off + base_off_in_buf + offset_in_structure 
    (old behavior for blocks extracted from ELF).
    """
    if USEDUMPOFFSETINSTEAD:
        start_abs = base_off_in_buf
    else:
        start_abs = lc_off + base_off_in_buf

    start_buf = base_off_in_buf

    entries = _walk_struct_entries(
        introdatabuffer,
        base_abs_off=start_abs,
        struct_off=start_buf,
        spec=chromatix_VFE_common_type,
        prefix=""
    )

    return _finalize_rows(entries)

def intro_row_parser(
    introdatabuffer: bytes,
    lc_off: int,
    base_off_in_buf: int = 0
) -> List[str]:
    """
    A wrapper for your old call.
    Returns CSV strings for version 0x0305.
    """
    return parse_chromatix_common(introdatabuffer, lc_off, base_off_in_buf)
