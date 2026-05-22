import os, struct

# ---------- Defaults Variables ----------
QTI_LIBHEAD_FILE_NAME   = "com.qti.tuned.apollo_semco_s5khmx_wide20000.bin"
FILE_SIZE               = ""
CRC32                   = ""
VERSION                 = ""
BINARY_TAG              = ""
SECTBLOCK_OFFSET        = ""
SECTBLOCK_COUNT         = ""
# ---------- Secondary Variables ----------
ZEROS_DETECTED   = "0"
SYMBOL_OFFSET    = ""
SYMBOL_SIZE      = ""
DATA_OFFSET      = ""
DATA_SIZE        = ""
MODE_OFFSET      = ""
MODE_SIZE        = ""
IDLINK_OFFSET    = ""
IDLINK_SIZE      = ""
RESERVED_OFFSET  = ""
RESERVED_SIZE    = ""


def GetVariablesFromHeader():
    def _u32_le(buf: bytes, off: int):
        if off < 0 or off + 4 > len(buf): return None
        return struct.unpack_from("<I", buf, off)[0]

    def _be_hex_from_le_u32(v: int) -> str:
        return "0x" + struct.pack("<I", v)[::-1].hex().upper()

    def _read_cstr_window(buf: bytes, start: int, end: int) -> str:
        end = min(end, len(buf))
        i = start
        while i < end and buf[i] == 0: i += 1
        if i >= end: return ""
        j = i
        while j < end and buf[j] != 0: j += 1
        if j == i: return ""
        return buf[i:j].decode("ascii", errors="ignore")

    global FILE_SIZE, CRC32, VERSION, BINARY_TAG
    global SECTBLOCK_OFFSET, SECTBLOCK_COUNT
    global ZEROS_DETECTED, SYMBOL_OFFSET, SYMBOL_SIZE, DATA_OFFSET, DATA_SIZE
    global MODE_OFFSET, MODE_SIZE, IDLINK_OFFSET, IDLINK_SIZE, RESERVED_OFFSET, RESERVED_SIZE

    # reset
    FILE_SIZE = CRC32 = VERSION = BINARY_TAG = ""
    SECTBLOCK_OFFSET = SECTBLOCK_COUNT = ""
    ZEROS_DETECTED = "0"
    SYMBOL_OFFSET = SYMBOL_SIZE = DATA_OFFSET = DATA_SIZE = ""
    MODE_OFFSET = MODE_SIZE = IDLINK_OFFSET = IDLINK_SIZE = ""
    RESERVED_OFFSET = RESERVED_SIZE = ""

    if not os.path.isfile(QTI_LIBHEAD_FILE_NAME):
        return

    data = open(QTI_LIBHEAD_FILE_NAME, "rb").read()

    # ---------- Defaults ----------
    fs_val = _u32_le(data, 0x1C)
    if fs_val is not None:
        FILE_SIZE = _be_hex_from_le_u32(fs_val)
        if fs_val + 4 <= len(data):
            crc_val = _u32_le(data, fs_val)
            if crc_val is not None:
                CRC32 = _be_hex_from_le_u32(crc_val)

    probe = data[0x28: min(len(data), 0x28 + 64)]
    if probe.startswith(b"Chromatix"):
        VERSION = "1.0.0"
    elif probe.startswith(b"Parameter Parser V"):
        vpos = probe.find(b"V")
        if vpos != -1 and vpos + 6 <= len(probe):
            VERSION = probe[vpos+1:vpos+6].decode("ascii", errors="ignore")

    BINARY_TAG = _read_cstr_window(data, 0x50, 0x94)

    # ---- find the value of SECTBLOCK_OFFSET and ITS POSITION (locally) ----
    sectblock_hex = "0x00000000"
    sect_pos = -1
    start, end = 0x80, 0xC0
    last_i = min(end, len(data)) - 4
    for i in range(start, max(start, last_i + 1)):
        v = _u32_le(data, i)
        if v is None: break
        if 0x80 <= v <= 0xC0:
            sectblock_hex = _be_hex_from_le_u32(v)
            sect_pos = i
            break
    SECTBLOCK_OFFSET = sectblock_hex
    if sect_pos < 0:
        return

    # ---- we read COUNT immediately after the field ----
    cnt_val = _u32_le(data, sect_pos + 4)
    if cnt_val is None:
        return
    SECTBLOCK_COUNT = _be_hex_from_le_u32(cnt_val)

    # pointer to the first SECTBLOCK
    p0 = sect_pos + 8
    stride_A = 12
    stride_B = 24

    # format detector (sample format A)
    first_off_A = _u32_le(data, p0 + 4) if p0 + 12 <= len(data) else None
    if first_off_A is None:
        # fallback: a rare case - sections are actually at the address of the value
        try_base = int(SECTBLOCK_OFFSET, 16)
        if try_base is None or try_base < 0 or try_base + 8 > len(data):
            return
        cnt_val2 = _u32_le(data, try_base + 4)
        if cnt_val2:
            cnt_val = cnt_val2
            SECTBLOCK_COUNT = _be_hex_from_le_u32(cnt_val)
            p0 = try_base + 8
            first_off_A = _u32_le(data, p0 + 4) if p0 + 12 <= len(data) else None
        if first_off_A is None:
            return
    else:
        cnt_val = int(SECTBLOCK_COUNT, 16)

    need_bytes_A = p0 + stride_A * cnt_val
    need_bytes_B = p0 + stride_B * cnt_val

    parse_format = "A" if first_off_A != 0 else "B"
    if parse_format == "B" and need_bytes_B > len(data):
        parse_format = "A"
    if parse_format == "A" and need_bytes_A > len(data):
        return

    # ---- parsing ----
    p = p0
    if parse_format == "A":
        ZEROS_DETECTED = "0"
        for _ in range(cnt_val):
            sect_type = _u32_le(data, p);      p += 4
            sect_off  = _u32_le(data, p);      p += 4
            sect_len  = _u32_le(data, p);      p += 4
            if sect_type is None: break
            if sect_type == 0x00000000:
                SYMBOL_OFFSET, SYMBOL_SIZE = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000001:
                DATA_OFFSET,   DATA_SIZE   = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000002:
                MODE_OFFSET,   MODE_SIZE   = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000003:
                IDLINK_OFFSET, IDLINK_SIZE = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000004:
                RESERVED_OFFSET, RESERVED_SIZE = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
    else:
        ZEROS_DETECTED = "1"
        for _ in range(cnt_val):
            sect_type = _u32_le(data, p);      p += 4
            _pad1     = _u32_le(data, p);      p += 4
            sect_off  = _u32_le(data, p);      p += 4
            _pad2     = _u32_le(data, p);      p += 4
            sect_len  = _u32_le(data, p);      p += 4
            _pad3     = _u32_le(data, p);      p += 4
            if sect_type is None: break
            if sect_type == 0x00000000:
                SYMBOL_OFFSET, SYMBOL_SIZE = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000001:
                DATA_OFFSET,   DATA_SIZE   = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000002:
                MODE_OFFSET,   MODE_SIZE   = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000003:
                IDLINK_OFFSET, IDLINK_SIZE = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)
            elif sect_type == 0x00000004:
                RESERVED_OFFSET, RESERVED_SIZE = _be_hex_from_le_u32(sect_off), _be_hex_from_le_u32(sect_len)



# ------------------------- test function -------------------------
def ParseQTIHeader():
    # test function
    GetVariablesFromHeader()
    # print all variables
    print(f'QTI_LIBHEAD_FILE_NAME = "{QTI_LIBHEAD_FILE_NAME}"')
    print(f'FILE_SIZE = "{FILE_SIZE}"')
    print(f'CRC32     = "{CRC32}"')
    print(f'VERSION   = "{VERSION}"')
    print(f'BINARY_TAG = "{BINARY_TAG}"')
    print(f'SECTBLOCK_OFFSET = "{SECTBLOCK_OFFSET}"')
    print(f'SECTBLOCK_COUNT  = "{SECTBLOCK_COUNT}"')

    print(f'ZEROS_DETECTED = "{ZEROS_DETECTED}"')

    print(f'SYMBOL_OFFSET = "{SYMBOL_OFFSET}"')
    print(f'SYMBOL_SIZE   = "{SYMBOL_SIZE}"')

    print(f'DATA_OFFSET   = "{DATA_OFFSET}"')
    print(f'DATA_SIZE     = "{DATA_SIZE}"')

    print(f'MODE_OFFSET   = "{MODE_OFFSET}"')
    print(f'MODE_SIZE     = "{MODE_SIZE}"')

    print(f'IDLINK_OFFSET = "{IDLINK_OFFSET}"')
    print(f'IDLINK_SIZE   = "{IDLINK_SIZE}"')

    print(f'RESERVED_OFFSET = "{RESERVED_OFFSET}"')
    print(f'RESERVED_SIZE   = "{RESERVED_SIZE}"')


# ------------------------- external API functions -------------------------

def QTIHead2Base(path):
    global QTI_LIBHEAD_FILE_NAME
    QTI_LIBHEAD_FILE_NAME = path
    GetVariablesFromHeader()
    return DATA_OFFSET

def GetModeDataOffsetSize(path):
    global QTI_LIBHEAD_FILE_NAME
    QTI_LIBHEAD_FILE_NAME = path
    GetVariablesFromHeader()
    return MODE_OFFSET, MODE_SIZE


if __name__ == "__main__":
    ParseQTIHeader()

