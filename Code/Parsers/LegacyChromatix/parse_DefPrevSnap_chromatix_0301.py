"""
Chromatix VFE common parser 0x0302 (early revision, chroma*_0302.h headers).

The top-level structure (chromatix_VFE_common_type) in this version is: :contentReference[oaicite:8]{index=8}
    chromatix_version            (unsigned short, u16)
    is_compressed                (unsigned char, u8)
    revision_number              (unsigned short, u16)

    chromatix_L                  (chromatix_L_type)
    chromatix_rolloff            (chromatix_rolloff_type)
    chromatix_LA_special_effects (chromatix_LA_special_effects_type)

Where:
chromatix_L_type includes: control_linearization (u8),
    linearization_lowlight_trigger (trigger_point_type),
    linear_A_trigger / linear_D65_trigger (chromatix_CCT_trigger_type),
    6 linear_table_*_* tables (chromatix_linearization_type). :contentReference[oaicite:9]{index=9}

chromatix_linearization_type contains for R/GR/GB/B:
    *_lut_p[8] (u16),
    *_lut_base[9] (u16),
    *_lut_delta[9] (float).
Delta is no longer present in newer versions, but it is still present in 0302. :contentReference[oaicite:10]{index=10}

  chromatix_rolloff_type:
    control_rolloff (u8),
    rolloff_lowlight_trigger (trigger_point_type),
    rolloff_A_trigger / rolloff_D65_trigger (chromatix_CCT_trigger_type),
    rolloff_LED_start / rolloff_LED_end / rolloff_Strobe_start / rolloff_Strobe_end (float),
    chromatix_mesh_rolloff_table[ROLLOFF_MAX_LIGHT],
    chromatix_mesh_rolloff_table_lowlight[ROLLOFF_MAX_LIGHT],
    chromatix_mesh_rolloff_table_golden_module[ROLLOFF_MAX_LIGHT],
    chromatix_mesh_rolloff_table_LED,
    chromatix_mesh_rolloff_table_Strobe.

  mesh_rolloff_array_type:
    mesh_rolloff_table_size (u16),
    r_gain[221], gr_gain[221], gb_gain[221], b_gain[221] (float each).
    221 = 17*13 (MESH_ROLLOFF_SIZE). :contentReference[oaicite:11]{index=11}

  chromatix_LA_special_effects_type:
    LA_LUT_backlit[64],
    LA_LUT_solarize[64],
    LA_LUT_posterize[64],
    LA_LUT_blackboard[64],
    LA_LUT_whiteboard[64]. :contentReference[oaicite:12]{index=12}

Flags:
REVERSE_INDEX → assign ID "from the end".
WRITEVALUETONAME → substitute scalar values ​​into the name (..._(28.8)).
USEDUMPOFFSETINSTEAD → calculate absolute offset from the dump, not from lc_off.
Compatible with your general framework.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional
import struct

# ── Indexing/Output Settings ─ ... ── Basic primitive types ───────────────────────────────────────────────────────
MODULE_VER              = "0301"
ID_START_NORMAL         = 0x0C00
ID_END_REVERSE          = 0x0CBF
REVERSE_INDEX = 1 # if 1 → IDs are added "from the tail"
WRITEVALUETONAME = 1 # if 1 → the scalar value is added to the name
USEDUMPOFFSETINSTEAD = 0 # if 1 → the absolute offset is calculated from the dump
AllowDebug              = 0

def _dbg(*args, **kwargs):
    if AllowDebug:
        print(*args, **kwargs)

def _align_up(off: int, align: int) -> int:
    if align <= 1:
        return off
    return (off + (align - 1)) & ~(align - 1)

# ── basic primitive types ────────────────────────────────────────────
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
    count: int = 1 # >1 → fixed-length array

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
        """Calculate field offsets inside the structure with padding for C-alignment."""
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
    """Read one primitive value to (if necessary) fit it into name."""
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
    We're inserting the value into the name (field_(123.4)).
    Which fields are we labeling:
      - gain_start / gain_end          (F32)
      - lux_index_start / lux_index_end (I32/U32)
      - CCT_start / CCT_end            (U32)
      - mesh_rolloff_table_size        (U16)
      - rolloff_LED_start / ..._end / rolloff_Strobe_start / ..._end (F32)
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
        "mesh_rolloff_table_size",
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

# ── constants for this version ───────────────────────────────────────────────────────────
MESH_ROLLOFF_SIZE = 17 * 13 # 221 float values ​​per rolloff grid channel. :contentReference[oaicite:13]{index=13}
ROLLOFF_MAX_LIGHT = 3 # TL84 / A / D65 (without H/Horizon yet). :contentReference[oaicite:14]{index=14}

# ── structures of 0302-headers ───────────────────────────────────────────────────────

# trigger_point_type:
#   float gain_start, gain_end;
#   long lux_index_start, lux_index_end; :contentReference[oaicite:15]{index=15}
trigger_point_type = StructSpec("trigger_point_type", [
    FieldSpec("gain_start",      F32),
    FieldSpec("gain_end",        F32),
    FieldSpec("lux_index_start", I32),
    FieldSpec("lux_index_end",   I32),
])

# chromatix_CCT_trigger_type:
#   unsigned long CCT_start;
#   unsigned long CCT_end; :contentReference[oaicite:16]{index=16}
chromatix_CCT_trigger_type = StructSpec("chromatix_CCT_trigger_type", [
    FieldSpec("CCT_start", U32),
    FieldSpec("CCT_end",   U32),
])

# chromatix_linearization_type (0302-style):
#   r_lut_p[8] (u16)
#   r_lut_base[9] (u16)
#   r_lut_delta[9] (float)
# ... for gr, gb, b. :contentReference[oaicite:17]{index=17}
chromatix_linearization_type = StructSpec("chromatix_linearization_type", [
    # R
    FieldSpec("r_lut_p",     U16, 8),
    FieldSpec("r_lut_base",  U16, 9),
    FieldSpec("r_lut_delta", F32, 9),

    # GR
    FieldSpec("gr_lut_p",     U16, 8),
    FieldSpec("gr_lut_base",  U16, 9),
    FieldSpec("gr_lut_delta", F32, 9),

    # GB
    FieldSpec("gb_lut_p",     U16, 8),
    FieldSpec("gb_lut_base",  U16, 9),
    FieldSpec("gb_lut_delta", F32, 9),

    # B
    FieldSpec("b_lut_p",     U16, 8),
    FieldSpec("b_lut_base",  U16, 9),
    FieldSpec("b_lut_delta", F32, 9),
])

# chromatix_L_type (0302-style):
#   tuning_control_type control_linearization; (u8)
#   trigger_point_type linearization_lowlight_trigger;
#   chromatix_CCT_trigger_type linear_A_trigger;
#   chromatix_CCT_trigger_type linear_D65_trigger;
# then six tables linear_table_*_* (chromatix_linearization_type). :contentReference[oaicite:18]{index=18}
chromatix_L_type = StructSpec("chromatix_L_type", [
    FieldSpec("control_linearization",              U8),
    FieldSpec("linearization_lowlight_trigger",     trigger_point_type),
    FieldSpec("linear_A_trigger",                   chromatix_CCT_trigger_type),
    FieldSpec("linear_D65_trigger",                 chromatix_CCT_trigger_type),

    FieldSpec("linear_table_A_lowlight",            chromatix_linearization_type),
    FieldSpec("linear_table_A_normal",              chromatix_linearization_type),
    FieldSpec("linear_table_TL84_lowlight",         chromatix_linearization_type),
    FieldSpec("linear_table_TL84_normal",           chromatix_linearization_type),
    FieldSpec("linear_table_Day_lowlight",          chromatix_linearization_type),
    FieldSpec("linear_table_Day_normal",            chromatix_linearization_type),
])

# mesh_rolloff_array_type (0302-style):
#   mesh_rolloff_table_size (u16),
#   r_gain[221], gr_gain[221], gb_gain[221], b_gain[221] (float). :contentReference[oaicite:19]{index=19}
mesh_rolloff_array_type = StructSpec("mesh_rolloff_array_type", [
    FieldSpec("mesh_rolloff_table_size", U16),
    FieldSpec("r_gain",   F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gr_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gb_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("b_gain",   F32, MESH_ROLLOFF_SIZE),
])

# chromatix_rolloff_type (0302-style):
#   tuning_control_type control_rolloff; (u8)
#   trigger_point_type rolloff_lowlight_trigger;
#   chromatix_CCT_trigger_type rolloff_A_trigger;
#   chromatix_CCT_trigger_type rolloff_D65_trigger;
#   float rolloff_LED_start, rolloff_LED_end, rolloff_Strobe_start, rolloff_Strobe_end;
# rolloff grid arrays:
# [ROLLOFF_MAX_LIGHT] for normal/lowlight/golden_module,
# and one LED/Strobe. :contentReference[oaicite:20]{index=20}
chromatix_rolloff_type = StructSpec("chromatix_rolloff_type", [
    FieldSpec("control_rolloff",             U8),
    FieldSpec("rolloff_lowlight_trigger",    trigger_point_type),
    FieldSpec("rolloff_A_trigger",           chromatix_CCT_trigger_type),
    FieldSpec("rolloff_D65_trigger",         chromatix_CCT_trigger_type),

    FieldSpec("rolloff_LED_start",           F32),
    FieldSpec("rolloff_LED_end",             F32),
    FieldSpec("rolloff_Strobe_start",        F32),
    FieldSpec("rolloff_Strobe_end",          F32),

    FieldSpec("mesh_rolloff_table", mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_lowlight", mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_golden_module", mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_LED", mesh_rolloff_array_type),
    FieldSpec("mesh_rolloff_table_Strobe", mesh_rolloff_array_type),
])

# chromatix_LA_special_effects_type:
# 5 LUTs of 64 floats each. :contentReference[oaicite:21]{index=21}
chromatix_LA_special_effects_type = StructSpec("chromatix_LA_special_effects_type", [
    FieldSpec("LA_LUT_backlit",    F32, 64),
    FieldSpec("LA_LUT_solarize",   F32, 64),
    FieldSpec("LA_LUT_posterize",  F32, 64),
    FieldSpec("LA_LUT_blackboard", F32, 64),
    FieldSpec("LA_LUT_whiteboard", F32, 64),
])

# chromatix_VFE_common_type (0302-style) top-level: :contentReference[oaicite:22]{index=22}
#   chromatix_version      (u16)
#   is_compressed          (u8)
#   revision_number        (u16)
#   chromatix_L            (chromatix_L_type)
#   chromatix_rolloff      (chromatix_rolloff_type)
#   chromatix_LA_special_effects (chromatix_LA_special_effects_type)
chromatix_VFE_common_type = StructSpec("chromatix_VFE_common_type_0302", [
    FieldSpec("chromatix_version",        U16),
    FieldSpec("is_compressed",            U8),
    FieldSpec("revision_number",          U16),
    FieldSpec("L",              chromatix_L_type),
    FieldSpec("rolloff",        chromatix_rolloff_type),
    FieldSpec("LA_special_effects", chromatix_LA_special_effects_type),
])

# ── Recursively traverse structure and collect strings ─────────────────────────────
def _walk_struct_entries(
    buf: bytes,
    base_abs_off: int, # absolute offset of this structure (in "file"/dump)
    struct_off: int, # offset of this structure within buf
    spec: StructSpec,
    prefix: str = ""
) -> List[Tuple[str, int, int]]:
    """
    Returns [(full_name, abs_offset, length_bytes), ...]
    for all leaf primitive fields.
    We expand nested structures recursively.
    We consider arrays of primitives to be a single block.
    We index arrays of structures using [...][i].
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
                # single scalar — we can append "(val)" to the name
                try:
                    raw_val = _safe_read_prim_scalar(buf, struct_off + foff, prim)
                except Exception:
                    raw_val = None

                full_name = prefix + fs.name
                full_name = _append_value_if_needed(full_name, raw_val, prim)
                out.append((full_name, field_abs_off, prim.size))
            else:
                # array of primitives → in one line
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
                    i_abs = field_abs_off + i * sub_size
                    i_buf = struct_off + foff + i * sub_size
                    out.extend(_walk_struct_entries(
                        buf,
                        base_abs_off=i_abs,
                        struct_off=i_buf,
                        spec=sub_spec,
                        prefix=prefix + f"{fs.name}[{i}]."
                    ))

    return out

def _finalize_rows(entries: List[Tuple[str, int, int]]) -> List[str]:
    """
    We assign an ID and generate strings:
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

# ── public functions ─ ... 446|1|base_off_in_buf — the offset from which the chromatix_VFE_common_type actually resides.
def parse_chromatix_common(
    introdatabuffer: bytes,
    lc_off: int,
    base_off_in_buf: int = 0
) -> List[str]:
    """
    Build CSV strings for chromatix_VFE_common_type (version 0302).

    introdatabuffer — your byte dump.
    lc_off — base LCOFF from ELF, if any.
    base_off_in_buf — offset where chromatix_VFE_common_type actually resides.

    If USEDUMPOFFSETINSTEAD == 1:
    absolute offset = base_off_in_buf + local_field_offset
    otherwise:
    absolute offset = lc_off + base_off_in_buf + local_field_offset
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
    Compatible with the common binding:
    returns [ "ID_HEX,name,OFFSET_HEX,LEN_HEX", ... ]
    for version 0302.
    """
    return parse_chromatix_common(introdatabuffer, lc_off, base_off_in_buf)
