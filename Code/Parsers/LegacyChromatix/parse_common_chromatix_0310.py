from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Union, Optional
import struct

MODULE_VER        = "0310"
ID_START_NORMAL   = 0x0C00
ID_END_REVERSE    = 0x0CBF
REVERSE_INDEX     = 1          
WRITEVALUETONAME  = 1          
USEDUMPOFFSETINSTEAD = 0
AllowDebug        = 0




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
    count: int = 1  

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

    if not WRITEVALUETONAME or val is None:
        return field_path

    tail = field_path.split(".")[-1]

    NEED_FLOAT = {
        "gain_start", "gain_end",
        "rolloff_LED_start", "rolloff_LED_end",
    }
    NEED_U32 = {
        "lux_index_start", "lux_index_end",
        "CCT_start", "CCT_end",
    }
    NEED_U16 = {
        "mesh_pedestal_table_size",
        "black_level_offset",
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

# ── constants taken from headers/reverse ─────────────────────────────
NUM_BLK_REGIONS          = 6           
MESH_PEDESTALTABLE_SIZE  = 13 * 10     
MESH_ROLLOFF_SIZE        = 17 * 13     
ROLLOFF_MAX_LIGHT        = 4

# ── small structures ───────────────────────────────────────────────────

chromatix_app_version_type = StructSpec("chromatix_app_version_type", [
    FieldSpec("major",    U8),
    FieldSpec("minor",    U8),
    FieldSpec("revision", U8),
    FieldSpec("build",    U8),
])

trigger_point_type = StructSpec("trigger_point_type", [
    FieldSpec("gain_start",       F32),
    FieldSpec("gain_end",         F32),
    FieldSpec("lux_index_start",  I32),
    FieldSpec("lux_index_end",    I32),
])

chromatix_CCT_trigger_type = StructSpec("chromatix_CCT_trigger_type", [
    FieldSpec("CCT_start", U32),
    FieldSpec("CCT_end",   U32),
])

pedestalcorrection_table = StructSpec("pedestalcorrection_table", [
    FieldSpec("mesh_pedestal_table_size", U16),
    FieldSpec("channel_black_level_r",    U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gr",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_gb",   U16, MESH_PEDESTALTABLE_SIZE),
    FieldSpec("channel_black_level_b",    U16, MESH_PEDESTALTABLE_SIZE),
])

chromatix_linearization_type = StructSpec("chromatix_linearization_type", [
    FieldSpec("r_lut_p",      U16, 8),
    FieldSpec("r_lut_base",   U16, 9),
    FieldSpec("gr_lut_p",     U16, 8),
    FieldSpec("gr_lut_base",  U16, 9),
    FieldSpec("gb_lut_p",     U16, 8),
    FieldSpec("gb_lut_base",  U16, 9),
    FieldSpec("b_lut_p",      U16, 8),
    FieldSpec("b_lut_base",   U16, 9),
])

chromatix_linearization_v2_type = StructSpec("chromatix_linearization_v2_type", [
    FieldSpec("linearization_v2_trigger", trigger_point_type),
    FieldSpec("r_lut_p",      U16, 8),
    FieldSpec("r_lut_base",   U16, 9),
    FieldSpec("gr_lut_p",     U16, 8),
    FieldSpec("gr_lut_base",  U16, 9),
    FieldSpec("gb_lut_p",     U16, 8),
    FieldSpec("gb_lut_base",  U16, 9),
    FieldSpec("b_lut_p",      U16, 8),
    FieldSpec("b_lut_base",   U16, 9),
])

Chromatix_BLSS_type = StructSpec("Chromatix_BLSS_type", [
    FieldSpec("black_level_offset", U16),
])

Chromatix_BLSS_v2_type = StructSpec("Chromatix_BLSS_v2_type", [
    FieldSpec("blss_v2_trigger",   trigger_point_type),
    FieldSpec("black_level_offset", U16),
])

mesh_rolloff_array_type = StructSpec("mesh_rolloff_array_type", [
    FieldSpec("mesh_rolloff_table_size", U16),
    FieldSpec("r_gain",   F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gr_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("gb_gain",  F32, MESH_ROLLOFF_SIZE),
    FieldSpec("b_gain",   F32, MESH_ROLLOFF_SIZE),
])

chromatix_LA_special_effects_type = StructSpec("chromatix_LA_special_effects_type", [
    FieldSpec("LA_LUT_backlit",    F32, 64),
    FieldSpec("LA_LUT_solarize",   F32, 64),
    FieldSpec("LA_LUT_posterize",  F32, 64),
    FieldSpec("LA_LUT_blackboard", F32, 64),
    FieldSpec("LA_LUT_whiteboard", F32, 64),
])

# ── middle blocks ──────────────────────────────────────────────────────

ChromatixVersionInfoType = StructSpec("ChromatixVersionInfoType", [
    FieldSpec("chromatix_version",        U16),
    FieldSpec("revision_number",          U16),
    FieldSpec("chromatix_app_version",    chromatix_app_version_type),
    FieldSpec("chromatix_header_type",    I32),
    FieldSpec("is_compressed",            U8),
    FieldSpec("is_mono",                  U8),
    FieldSpec("is_video",                 U8),
    FieldSpec("reserved_align",           U8),
    FieldSpec("chromatix_mode",           I32),
    FieldSpec("target_id",                U32),
    FieldSpec("chromatix_id",             U32),
    FieldSpec("reserved",                 U32, 4),
])

chromatix_pedestalcorrection_type = StructSpec("chromatix_pedestalcorrection_type", [
    FieldSpec("pedestalcorrection_enable",          I32),
    FieldSpec("pedestalcorrection_control_enable",  I32),
    FieldSpec("control_pedestal",                   U8),
    FieldSpec("pedestal_lowlight_trigger",          trigger_point_type),
    FieldSpec("pctable",                            pedestalcorrection_table, 2),
    FieldSpec("pctable_lowlight",                   pedestalcorrection_table, 2),
])

chromatix_L_type = StructSpec("chromatix_L_type", [
    FieldSpec("linearization_enable",               I32),
    FieldSpec("linearization_control_enable",       I32),
    FieldSpec("last_region_unity_slope_enable",     I32),
    FieldSpec("control_linearization",              U8),
    FieldSpec("linearization_lowlight_trigger",     trigger_point_type),
    FieldSpec("linear_table_lowlight",              chromatix_linearization_type),
    FieldSpec("linear_table_normal",                chromatix_linearization_type),
])

chromatix_L_v2_type = StructSpec("chromatix_L_v2_type", [
    FieldSpec("linearization_v2_enable",            I32),
    FieldSpec("linearization_v2_control_enable",    I32),
    FieldSpec("last_region_unity_slope_enable",     I32),
    FieldSpec("control_linearization",              U8),
    FieldSpec("linear_table_data",                  chromatix_linearization_v2_type, NUM_BLK_REGIONS),
])

Chromatix_blk_subtract_scale_type = StructSpec("Chromatix_blk_subtract_scale_type", [
    FieldSpec("BLSS_enable",                I32),
    FieldSpec("BLSS_control_enable",        I32),
    FieldSpec("control_BLSS",               U8),
    FieldSpec("BLSS_low_light_trigger",     trigger_point_type),
    FieldSpec("black_level_lowlight",       Chromatix_BLSS_type),
    FieldSpec("black_level_normal",         Chromatix_BLSS_type),
])

Chromatix_blk_subtract_scale_v2_type = StructSpec("Chromatix_blk_subtract_scale_v2_type", [
    FieldSpec("BLSS_v2_enable",             I32),
    FieldSpec("BLSS_v2_control_enable",     I32),
    FieldSpec("control_BLSS",               U8),
    FieldSpec("black_level_data",           Chromatix_BLSS_v2_type, NUM_BLK_REGIONS),
])

chromatix_rolloff_type = StructSpec("chromatix_rolloff_type", [
    FieldSpec("rolloff_H_trigger",                      chromatix_CCT_trigger_type),
    FieldSpec("rolloff_A_trigger",                      chromatix_CCT_trigger_type),
    FieldSpec("rolloff_D65_trigger",                    chromatix_CCT_trigger_type),

    FieldSpec("rolloff_LED_start",                      F32),
    FieldSpec("rolloff_LED_end",                        F32),

    FieldSpec("scale_cubic",                            I32),
    FieldSpec("subgridh_offset",                        I32),
    FieldSpec("subgridv_offset",                        I32),

    FieldSpec("mesh_rolloff_table",           mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_lowlight",  mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_golden_module", mesh_rolloff_array_type, ROLLOFF_MAX_LIGHT),
    FieldSpec("mesh_rolloff_table_LED",       mesh_rolloff_array_type),
    FieldSpec("mesh_rolloff_table_LED2",      mesh_rolloff_array_type),
])

chromatix_VFE_common_type = StructSpec("chromatix_VFE_common_type", [
    FieldSpec("version_info",        ChromatixVersionInfoType),
    FieldSpec("pedestal_correction", chromatix_pedestalcorrection_type),
    FieldSpec("L",                   chromatix_L_type),
    FieldSpec("L_v2_data",           chromatix_L_v2_type),
    FieldSpec("BLSS_data",           Chromatix_blk_subtract_scale_type),
    FieldSpec("BLSS_v2_data",        Chromatix_blk_subtract_scale_v2_type),
    FieldSpec("rolloff",             chromatix_rolloff_type),
    FieldSpec("LA_special_effects",  chromatix_LA_special_effects_type),
])

# ── recursive traversal of a structure ────────────────────────────────────────

def _walk_struct_entries(
    buf: bytes,
    base_abs_off: int,    # absolute offset of the structure in the file
    struct_off: int,      # offset of the structure inside buf (usually the same)
    spec: StructSpec,
    prefix: str = ""
) -> List[Tuple[str, int, int]]:
    """Collect (field_name, absolute_offset, length_in_bytes) for all leaves."""
    out: List[Tuple[str, int, int]] = []

    layout = spec.calc_layout()
    for ent in layout['fields']:
        fs = ent['field']
        foff = ent['offset']
        elem_size = ent['size_each']
        total_size = ent['size_total']
        field_abs_off = base_abs_off + (foff)


        if isinstance(fs.type_spec, PrimType):
            prim = fs.type_spec
            if fs.count == 1:
                # single scalar -> read (if it fits) to mix the value into the name
                try:
                    raw_val = _safe_read_prim_scalar(buf, struct_off + foff, prim)
                except Exception:
                    raw_val = None
                full_name = prefix + fs.name
                full_name = _append_value_if_needed(full_name, raw_val, prim)
                out.append((full_name, field_abs_off, prim.size))
            else:
                # array of primitives -> one entry for the entire array
                full_name = prefix + fs.name
                out.append((full_name, field_abs_off, prim.size * fs.count))

        # nested structure?
        else:
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
    """Assigning IDs and generating CSV lines."""
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

# ── public functions ─────────────────────────────────────────────────

def parse_chromatix_common(
    introdatabuffer: bytes,
    lc_off: int,
    base_off_in_buf: int = 0
) -> List[str]:
    """
    We collect the strings ID_HEX, name, OFFSET_HEX, and LEN_HEX.

    introdatabuffer — the bytes of your dump.
    lc_off — the original "LCOFF" (block offset within a large file),
    relevant if we're parsing directly from the .so file.
    base_off_in_buf — the offset within the introdatabuffer where
    the chromatix structure actually begins.

    USEDUMPOFFSETINSTEAD:
    =1 → the absolute offset is calculated as base_off_in_buf
    (that is, "offsets are exactly as in the dump").
    =0 → the absolute offset is calculated as lc_off + base_off_in_buf
    (as your old code did).
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
    # compatibility with your old calling system
    return parse_chromatix_common(introdatabuffer, lc_off, base_off_in_buf)
