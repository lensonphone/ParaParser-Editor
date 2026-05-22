# -*- coding: utf-8 -*-
"""
Chromatix VFE common parser 0x0308.

Based on structures from chromatix_common_0308.h and chromatix_0308.h:
- chromatix_VFE_common_type (version 0x308) contains:
    chromatix_version                (u16)
    chromatix_app_version            (4 x u8: major/minor/revision/build)
    is_compressed                    (u8)
    revision_number                  (u16)
    chromatix_pedestal_correction    (pedestalcorrection_enable/... pctable[2])
    chromatix_L (linearization_enable,... lowlight/normal tables)
    Chromatix_BLSS_data              (BLSS_enable,... black_level_* c offset-only)
    chromatix_rolloff                (rolloff_*_trigger, LED/Strobe, mesh_rolloff_table[*])
    chromatix_LA_special_effects     (LA_LUT_*[64])
See definition of CHROMATIX_VFE_COMMON_VERSION 0x308. :contentReference[oaicite:5]{index=5}

Differences from 0x0305:
- ROLLOFF_MAX_LIGHT now includes ROLLOFF_H_LIGHT, i.e. 4 grid sets. :contentReference[oaicite:6]{index=6}
- Rolloff triggers now have rolloff_H_trigger in addition to A and D65. :contentReference[oaicite:7]{index=7}
- Chromatix_BLSS_type now stores only black_level_offset (u16), without scale. :contentReference[oaicite:8]{index=8}

Function output:
List of strings of the form
    ID_HEX,name,ABS_OFFSET_HEX,LENGTH_HEX

Global flags:
REVERSE_INDEX = 1 → IDs are numbered from the tail (ID_END_REVERSE ..)
WRITEVALUETONAME = 1 → The scalar value is appended to the name (..._(28.8))
USEDUMPOFFSETINSTEAD = 1 → The absolute offset is calculated from the dump, not lc_off

Main API:
  intro_row_parser(data: bytes, lc_off: int, base_off_in_buf: int = 0) -> List[str]
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional
import struct

# ── Indexing/output settings ─────────────────────────────────────────────
MODULE_VER              = "0308"
ID_START_NORMAL         = 0x0C00
ID_END_REVERSE          = 0x0CBF
REVERSE_INDEX = 1 # count IDs "from the end"
WRITEVALUETONAME = 1 # embed values ​​into the name
USEDUMPOFFSETINSTEAD = 0 # absolute offset = offset in the dump
AllowDebug              = 0

def _dbg(*args, **kwargs):
    if AllowDebug:
        print(*args, **kwargs)

def _align_up(off: int, align: int) -> int:
    if align <= 1:
        return off
    return (off + (align - 1)) & ~(align - 1)

# ── basic primitive types ─ ... >1 → fixed-length array
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
    count: int = 1  # =1 → single field; >1 → fixed-length array

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
        """Calculate field offsets within the structure, taking alignment into account."""
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
    """Read a scalar (u16/u32/f32/...) at the absolute offset off in buf.
    If the offset is beyond the end of the buffer, throw an exception, and we won't insert the value into the name.
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
    If the field is known as a "trigger" (gain_start, lux_index_start, CCT_start,
    mesh_pedestal_table_size, etc.), substitute _(value) into the name.
    This preserves readability: e.g., rolloff_LED_start_(1.5). :contentReference[oaicite:9]{index=9}
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
        # can be added "mesh_rolloff_table_size" if you want to see the rolloff grid size in the name
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

# ── array size constants for 0x0308 ──────────────────────────────────
MESH_PEDESTALTABLE_SIZE = 13 * 10 # 130 U16 points per pedestal channel (HDR tables) :contentReference[oaicite:10]{index=10}
MESH_ROLLOFF_SIZE = 17 * 13 # 221 F32 points per channel rolloff grids (17x13) :contentReference[oaicite:11]{index=11}
ROLLOFF_MAX_LIGHT = 4 # TL84, A, D65, H (Horizon) → 4 sets of tables :contentReference[oaicite:12]{index=12}

# ── 0308 header-style structure declarations ──────────────────────────────
# chromatix_app_version_type: 4 bytes major/minor/revision/build (unsigned char). :contentReference[oaicite:13]{index=13}
chromatix_app_version_type = StructSpec("chromatix_app_version_type", [
    FieldSpec("major",    U8),
    FieldSpec("minor",    U8),
    FieldSpec("revision", U8),
    FieldSpec("build",    U8),
])

# trigger_point_type: gain_start/gain_end (float), lux_index_start/lux_index_end (long→32bit). :contentReference[oaicite:14]{index=14}
trigger_point_type = StructSpec("trigger_point_type", [
    FieldSpec("gain_start",      F32),
    FieldSpec("gain_end",        F32),
    FieldSpec("lux_index_start", I32),
    FieldSpec("lux_index_end",   I32),
])

# chromatix_CCT_trigger_type: CCT_start / CCT_end (unsigned long → u32). :contentReference[oaicite:15]{index=15}
chromatix_CCT_trigger_type = StructSpec("chromatix_CCT_trigger_type", [
    FieldSpec("CCT_start", U32),
    FieldSpec("CCT_end",   U32),
])

# pedestalcorrection_table: grid size + 4 channels of 130 U16 values ​​each. :contentReference[oaicite:16]{index=16}
pedestalcorrection_table = StructSpec("pedestalcorrection_table", [
    FieldSpec("mesh_pedestal_table_size", U16),
    FieldSpec("channel_black_level_r",    U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gr",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gb",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_b",    U16, MESH_PEDESTALTABLE_SIZE),
])

# chromatix_pedestalcorrection_type: enable, control_enable, pctable[2] for HDR. :contentReference[oaicite:17]{index=17}
chromatix_pedestalcorrection_type = StructSpec("chromatix_pedestalcorrection_type", [
    FieldSpec("pedestalcorrection_enable",         I32),
    FieldSpec("pedestalcorrection_control_enable", I32),
    FieldSpec("pctable", pedestalcorrection_table, 2),
])

# chromatix_linearization_type in 0x0308:
# same fields as in 0x0305 (essentially lut_p[8], lut_base[9] for R/GR/GB/B;
# *_lut_delta[] arrays are commented out and are no longer in the binary). :contentReference[oaicite:18]{index=18}
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

# chromatix_L_type (linearization block):
# linearization_enable / linearization_control_enable (int),
# control_linearization (tuning_control_type = unsigned char),
# linearization_lowlight_trigger (trigger_point_type),
# lowlight/normal tables without separate A/TL84/D65. :contentReference[oaicite:19]{index=19}
chromatix_L_type = StructSpec("chromatix_L_type", [
    FieldSpec("linearization_enable",          I32),
    FieldSpec("linearization_control_enable",  I32),

    FieldSpec("control_linearization",         U8),
    FieldSpec("linearization_lowlight_trigger", trigger_point_type),

    FieldSpec("linear_table_lowlight",         chromatix_linearization_type),
    FieldSpec("linear_table_normal",           chromatix_linearization_type),
])

# Chromatix_BLSS_type in 0x0308:
# only offset (u16). This is different from 0x0305, which had offset+scale. :contentReference[oaicite:20]{index=20}
Chromatix_BLSS_type = StructSpec("Chromatix_BLSS_type", [
    FieldSpec("black_level_offset", U16),
])

# Chromatix_blk_subtract_scale_type:
# BLSS_enable / BLSS_control_enable (int),
# control_BLSS (tuning_control_type = u8),
# BLSS_low_light_trigger (trigger_point_type),
# black_level_lowlight / black_level_normal (Chromatix_BLSS_type). :contentReference[oaicite:21]{index=21}
Chromatix_blk_subtract_scale_type = StructSpec("Chromatix_blk_subtract_scale_type", [
    FieldSpec("BLSS_enable",         I32),
    FieldSpec("BLSS_control_enable", I32),

    FieldSpec("control_BLSS",        U8),
    FieldSpec("BLSS_low_light_trigger", trigger_point_type),

    FieldSpec("black_level_lowlight", Chromatix_BLSS_type),
    FieldSpec("black_level_normal",   Chromatix_BLSS_type),
])

# mesh_rolloff_array_type:
# mesh_rolloff_table_size (u16), then 221 floats for r/gr/gb/b. :contentReference[oaicite:22]{index=22}
mesh_rolloff_array_type = StructSpec("mesh_rolloff_array_type", [
    FieldSpec("mesh_rolloff_table_size", U16),
    FieldSpec("r_gain",   F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gr_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gb_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("b_gain",   F32, MESH_ROLLOFF_SIZE),
])

# chromatix_rolloff_type at 0x0308:
# rolloff_H_trigger + rolloff_A_trigger + rolloff_D65_trigger,
# rolloff_LED_start/end, rolloff_Strobe_start/end,
# scale_cubic/subgridh_offset/subgridv_offset,
# and then grid arrays for ROLLOFF_MAX_LIGHT (=4) + LED/Strobe. :contentReference[oaicite:23]{index=23}
chromatix_rolloff_type = StructSpec("chromatix_rolloff_type", [
    FieldSpec("rolloff_H_trigger",   chromatix_CCT_trigger_type),
    FieldSpec("rolloff_A_trigger",   chromatix_CCT_trigger_type),
    FieldSpec("rolloff_D65_trigger", chromatix_CCT_trigger_type),

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

# chromatix_LA_special_effects_type:
# five LUTs of 64 floats each. :contentReference[oaicite:24]{index=24}
chromatix_LA_special_effects_type = StructSpec("chromatix_LA_special_effects_type", [
    FieldSpec("LA_LUT_backlit",    F32, 64),
    FieldSpec("LA_LUT_solarize",   F32, 64),
    FieldSpec("LA_LUT_posterize",  F32, 64),
    FieldSpec("LA_LUT_blackboard", F32, 64),
    FieldSpec("LA_LUT_whiteboard", F32, 64),
])

# Top-level chromatix_VFE_common_type structure for 0x0308:
# the order and field names exactly match common header 0x0308. :contentReference[oaicite:25]{index=25}
chromatix_VFE_common_type = StructSpec("chromatix_VFE_common_type_0308", [
    FieldSpec("chromatix_version",      U16),
    FieldSpec("chromatix_app_version",  chromatix_app_version_type),
    FieldSpec("is_compressed",          U8),
    FieldSpec("revision_number",        U16),

    FieldSpec("pedestal_correction", chromatix_pedestalcorrection_type),

    FieldSpec("L",                    chromatix_L_type),

    FieldSpec("BLSS_data",            Chromatix_blk_subtract_scale_type),

    FieldSpec("rolloff",              chromatix_rolloff_type),

    FieldSpec("LA_special_effects",   chromatix_LA_special_effects_type),
])

# ── recursive traversal of the structure and field assembly ─────────────────────────
def _walk_struct_entries(
    buf: bytes,
    base_abs_off: int, # absolute offset of this structure "in the file"/dump
    struct_off: int, # offset of this structure within buf
    spec: StructSpec,
    prefix: str = ""
) -> List[Tuple[str, int, int]]:
    """
    Returns a list (full_field_name, abs_offset, length_bytes)
    for all leaf fields (primitive or array of primitives).
    Nested structures are expanded using dot notation and [i] indices.
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
                # single scalar → attempt to substitute the value _(val)
                try:
                    raw_val = _safe_read_prim_scalar(buf, struct_off + foff, prim)
                except Exception:
                    raw_val = None

                full_name = prefix + fs.name
                full_name = _append_value_if_needed(full_name, raw_val, prim)
                out.append((full_name, field_abs_off, prim.size))
            else:
                # array of simple types → one row for the entire array
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
    Assign an ID and collect the rows:
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

# ── public functions ─ ... 454|1|base_off_in_buf — the offset at which chromatix_VFE_common_type actually
def parse_chromatix_common(
    introdatabuffer: bytes,
    lc_off: int,
    base_off_in_buf: int = 0
) -> List[str]:
    """
    Assembles the final CSV (as a list of strings) for the chromatix_VFE_common_type (0x0308) structure.

    introdatabuffer — dump bytes (entire bin or selected fragment).
    lc_off — "LCOFF" from ELF (if any).
    base_off_in_buf — the offset in the introdatabuffer where the actual
    starts in the introdatabuffer.

    If USEDUMPOFFSETINSTEAD == 1:
    absolute offset = base_off_in_buf + field_offset
    (i.e., we calculate purely from the dump).
    Otherwise:
    absolute offset = lc_off + base_off_in_buf + field_offset
    (old ELF behavior).
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
    Wrapper for your general call.
    Returns a list of strings ID_HEX, name, OFFSET_HEX, LENGTH_HEX
    for version 0x0308.
    """
    return parse_chromatix_common(introdatabuffer, lc_off, base_off_in_buf)
