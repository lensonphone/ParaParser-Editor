# -*- coding: utf-8 -*-
"""
Chromatix VFE common 0x0304 parser.

Based on structures from chromatix_common_0304.h / chromatix_0304.h:
- chromatix_VFE_common_type (version 0x304) contains:
    * chromatix_version_info fields (version/app_version/is_compressed/revision_number)
    * chromatix_pedestal_correction (2 HDR pedestal tables)
    * chromatix_L (linearization + CCT triggers + 6 tables)
    * chromatix_rolloff (CCT triggers, rolloff_LED/rolloff_Strobe, mesh_rolloff_table[*])
    * chromatix_LA_special_effects (LA LUTs)
and does not contain BLSS blocks or linearization_v2. :contentReference[oaicite:2]{index=2}

Output:
List of strings like:
    ID_HEX,full.path.to.field,ABS_OFFSET_HEX,LENGTH_HEX

Flags:
- REVERSE_INDEX = 1 → IDs come from ID_END_REVERSE (as you're using now)
- WRITEVALUETONAME = 1 → Mix scalar values ​​into the name (_(28.8))
- USEDUMPOFFSETINSTEAD = 1 → Absolute offset in CSV = base_off_in_buf,
                            Otherwise lc_off + base_off_in_buf

Exported function:
  intro_row_parser(data: bytes, lc_off: int, base_off_in_buf: int = 0) -> List[str]
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional
import struct

# ── Indexing/numbering settings ────────────────────────────────────────────
MODULE_VER              = "0304"
ID_START_NORMAL         = 0x0C00
ID_END_REVERSE          = 0x0CBF
REVERSE_INDEX = 1 # numbering from the tail
WRITEVALUETONAME = 1 # embed the value in the name
USEDUMPOFFSETINSTEAD = 0 # calculate offsets relative to the dump
AllowDebug = 0 # debug print

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
    count: int = 1 # array? (>1) or a single field (=1)

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
    """Read a single simple value by absolute offset within buf.
    If the offset is outside the dump (truncated binary), discard it,
    to avoid mixing garbage into the name.
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
    Embed the value into the name:
    gain_start_(28.8), lux_index_start_(375),
    mesh_pedestal_table_size_(130), rolloff_LED_start_(1.0), etc.

    Select by the tail of the name (the last segment after '.').
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

# ── array size constants from 0x0304 header ──────────────────────────
MESH_PEDESTALTABLE_SIZE = 13 * 10 # 130 U16 elements per channel :contentReference[oaicite:3]{index=3}
MESH_ROLLOFF_SIZE       = 17 * 13     # 221 float gain entries per channel :contentReference[oaicite:4]{index=4}
ROLLOFF_MAX_LIGHT = 3 # TL84, A, D65 → 3 sets of tables :contentReference[oaicite:5]{index=5}

# ── base structures from 0x0304 ────────────────────────────────────────────
chromatix_app_version_type = StructSpec("chromatix_app_version_type", [
    FieldSpec("major",    U8),
    FieldSpec("minor",    U8),
    FieldSpec("revision", U8),
    FieldSpec("build",    U8),
])  # :contentReference[oaicite:6]{index=6}

trigger_point_type = StructSpec("trigger_point_type", [
    FieldSpec("gain_start",      F32),
    FieldSpec("gain_end",        F32),
    FieldSpec("lux_index_start", I32),
    FieldSpec("lux_index_end",   I32),
])  # :contentReference[oaicite:7]{index=7}

chromatix_CCT_trigger_type = StructSpec("chromatix_CCT_trigger_type", [
    FieldSpec("CCT_start", U32),
    FieldSpec("CCT_end",   U32),
])  # :contentReference[oaicite:8]{index=8}

# pedestal (2D black correction) in 0x0304:
pedestalcorrection_table = StructSpec("pedestalcorrection_table", [
    FieldSpec("mesh_pedestal_table_size", U16),
    FieldSpec("channel_black_level_r",    U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gr",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gb",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_b",    U16, MESH_PEDESTALTABLE_SIZE),
])  # :contentReference[oaicite:9]{index=9}

chromatix_pedestalcorrection_type = StructSpec("chromatix_pedestalcorrection_type", [
    FieldSpec("pedestalcorrection_enable",         I32),
    FieldSpec("pedestalcorrection_control_enable", I32),
    # 0x0304 holds only pctable[2], without lowlight variants and without trigger inside the block. :contentReference[oaicite:10]{index=10}
    FieldSpec("pctable", pedestalcorrection_table, 2),
])

# linearization tables for multiple illuminants:
chromatix_linearization_type = StructSpec("chromatix_linearization_type", [
    # R channel
    FieldSpec("r_lut_p",     U16, 8),
    FieldSpec("r_lut_base",  U16, 9),
    FieldSpec("r_lut_delta", F32, 9),
    # GR channel
    FieldSpec("gr_lut_p",     U16, 8),
    FieldSpec("gr_lut_base",  U16, 9),
    FieldSpec("gr_lut_delta", F32, 9),
    # GB channel
    FieldSpec("gb_lut_p",     U16, 8),
    FieldSpec("gb_lut_base",  U16, 9),
    FieldSpec("gb_lut_delta", F32, 9),
    # B channel
    FieldSpec("b_lut_p",     U16, 8),
    FieldSpec("b_lut_base",  U16, 9),
    FieldSpec("b_lut_delta", F32, 9),
])  # :contentReference[oaicite:11]{index=11}

chromatix_L_type = StructSpec("chromatix_L_type", [
    FieldSpec("linearization_enable",          I32),
    FieldSpec("linearization_control_enable",  I32),

    FieldSpec("control_linearization",         U8),
    FieldSpec("linearization_lowlight_trigger", trigger_point_type),

    FieldSpec("linear_A_trigger",              chromatix_CCT_trigger_type),
    FieldSpec("linear_D65_trigger",            chromatix_CCT_trigger_type),

    # a set of tables for different light sources and lighting conditions
    FieldSpec("linear_table_A_lowlight",       chromatix_linearization_type),
    FieldSpec("linear_table_A_normal",         chromatix_linearization_type),
    FieldSpec("linear_table_TL84_lowlight",    chromatix_linearization_type),
    FieldSpec("linear_table_TL84_normal",      chromatix_linearization_type),
    FieldSpec("linear_table_Day_lowlight",     chromatix_linearization_type),
    FieldSpec("linear_table_Day_normal",       chromatix_linearization_type),
])  # :contentReference[oaicite:12]{index=12}

# rolloff/light falloff tables:
mesh_rolloff_array_type = StructSpec("mesh_rolloff_array_type", [
    FieldSpec("mesh_rolloff_table_size", U16),
    FieldSpec("r_gain",   F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gr_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gb_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("b_gain",   F32, MESH_ROLLOFF_SIZE),
])  # :contentReference[oaicite:13]{index=13}

chromatix_rolloff_type = StructSpec("chromatix_rolloff_type", [
    # rolloff triggers and CCT triggers:
    FieldSpec("rolloff_A_trigger",    chromatix_CCT_trigger_type),
    FieldSpec("rolloff_D65_trigger",  chromatix_CCT_trigger_type),

    # LED / Strobe rolloff influence ranges (float):
    FieldSpec("rolloff_LED_start",    F32),
    FieldSpec("rolloff_LED_end",      F32),
    FieldSpec("rolloff_Strobe_start", F32),
    FieldSpec("rolloff_Strobe_end",   F32),

    # subgrid interpolation:
    FieldSpec("scale_cubic",          I32),
    FieldSpec("subgridh_offset",      I32),
    FieldSpec("subgridv_offset",      I32),

    # main grids rolloff:
    FieldSpec("mesh_rolloff_table",               mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_lowlight",      mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_golden_module", mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_LED",           mesh_rolloff_array_type),
    FieldSpec("mesh_rolloff_table_Strobe",        mesh_rolloff_array_type),
])  # :contentReference[oaicite:14]{index=14}

chromatix_LA_special_effects_type = StructSpec("chromatix_LA_special_effects_type", [
    FieldSpec("LA_LUT_backlit",    F32, 64),
    FieldSpec("LA_LUT_solarize",   F32, 64),
    FieldSpec("LA_LUT_posterize",  F32, 64),
    FieldSpec("LA_LUT_blackboard", F32, 64),
    FieldSpec("LA_LUT_whiteboard", F32, 64),
])  # :contentReference[oaicite:15]{index=15}

# block version/revision (0x0304 layout):
# 0304 doesn't have the full "chromatix_version_info" like 0310,
# but it does have the version/app_version/is_compressed/revision_number fields. :contentReference[oaicite:16]{index=16}
ChromatixVersionInfoType = StructSpec("ChromatixVersionInfoType_0304", [
    FieldSpec("chromatix_version",       U16),                 # chromatix_version_type
    FieldSpec("chromatix_app_version",   chromatix_app_version_type),
    FieldSpec("is_compressed",           U8),
    FieldSpec("revision_number",         U16),
])

# Top-level chromatix_VFE_common_type structure for version 0x0304. :contentReference[oaicite:17]{index=17}
chromatix_VFE_common_type = StructSpec("chromatix_VFE_common_type_0304", [
    FieldSpec("version_info",      ChromatixVersionInfoType),
    FieldSpec("pedestal_correction", chromatix_pedestalcorrection_type),
    FieldSpec("L",                   chromatix_L_type),
    FieldSpec("rolloff",             chromatix_rolloff_type),
    FieldSpec("LA_special_effects",  chromatix_LA_special_effects_type),
])

# ── Recursive traversal of the structure, assembling records ───────────────────────
def _walk_struct_entries(
    buf: bytes,
    base_abs_off: int, # absolute offset of this structure "in the file"
    struct_off: int, # offset of this structure in buf
    spec: StructSpec,
    prefix: str = ""
) -> List[Tuple[str, int, int]]:
    """
    Returns a list (full_field_name, abs_offset, length_bytes)
    for all "leaves" (primitives and arrays of primitives).
    We expand nested structures using dot notation and [i] indices.
    """
    out: List[Tuple[str, int, int]] = []

    layout = spec.calc_layout()
    for ent in layout['fields']:
        fs = ent['field']
        foff = ent['offset']
        elem_size = ent['size_each']
        field_abs_off = base_abs_off + foff

        # primitive?
        if isinstance(fs.type_spec, PrimType):
            prim = fs.type_spec

            if fs.count == 1:
                # single scalar → try to read and append the value to the name
                try:
                    raw_val = _safe_read_prim_scalar(buf, struct_off + foff, prim)
                except Exception:
                    raw_val = None

                full_name = prefix + fs.name
                full_name = _append_value_if_needed(full_name, raw_val, prim)
                out.append((full_name, field_abs_off, prim.size))

            else:
                # array of primitives — one entry for the entire array
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
    Assign an ID and collect CSV lines:
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

# ── public API ─ ...
def parse_chromatix_common(
    introdatabuffer: bytes,
    lc_off: int,
    base_off_in_buf: int = 0
) -> List[str]:
    """
    Collect lines ID_HEX,name,OFFSET_HEX,LENGTH_HEX.

    introdatabuffer — dump bytes (the entire .bin or a selected chunk).
    lc_off — "LCOFF" from the old pipeline (offset within a large ELF).
    base_off_in_buf — the offset where the introdatabuffer actually starts.
                      chromatix_VFE_common_type.

    If USEDUMPOFFSETINSTEAD == 1:
    absolute field offset = base_off_in_buf (i.e., raw in the dump)
    Otherwise:
    absolute field offset = lc_off + base_off_in_buf (old behavior).
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
    Compatible with your calling code:
    returns CSV strings for 0x0304.
    """
    return parse_chromatix_common(introdatabuffer, lc_off, base_off_in_buf)
