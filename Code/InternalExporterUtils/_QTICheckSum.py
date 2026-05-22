import struct
import zlib

# Default file for standalone execution (no arguments)
FilePathName = "com.qti.tuned.thor_semco_imx989_wide.bin"

# Address 0x1C contains an LE pointer (u32) to the CRC32 field in the file itself
CHECKSUM_ADDR_PTR_OFFSET = 0x1C

def _u32_le(b):
    return struct.unpack("<I", b)[0]


def _pack_u32_le(v):
    return struct.pack("<I", v & 0xFFFFFFFF)


def checksumfix(file_path=None):
    """
        1) Takes the file path (from the argument or the global FilePathName).
        2) Reads the CRC32 field address at 0x1C (LE u32).
        3) Calculates the CRC32 for the entire file EXCEPT these 4 bytes.
        4) If it matches the written value, 'Checksum is Correct'.
        If not, writes the correct CRC (LE) and returns 'Checksum is Fixed'.
        If the CRC address is outside the file / points to the end of the file,
        'Checksum not supported in this QTI Tuned Library'.
        If there are read/write errors, 'Error: ...'
    """
    path = file_path or FilePathName
    if not path:
        return "Error: FilePathName is not set"

    try:
        with open(path, "rb") as f:
            data = bytearray(f.read())
    except Exception as e:
        return "Error: failed to read file: %s" % e

    # Must be able to read 4 bytes of address at 0x1C
    if len(data) < CHECKSUM_ADDR_PTR_OFFSET + 4:
        return "Checksum not supported in this QTI Tuned Library"

    # Address of the CRC32 field (LE u32)
    checksum_addr = _u32_le(data[CHECKSUM_ADDR_PTR_OFFSET:CHECKSUM_ADDR_PTR_OFFSET + 4])

    #Address validity: must fit 4 bytes
    if checksum_addr < 0 or checksum_addr + 4 > len(data):
        return "Checksum not supported in this QTI Tuned Library"

    # Current CRC value in the file
    stored_crc = _u32_le(data[checksum_addr:checksum_addr + 4])

    # CRC32 of the entire file, excluding the 4 bytes of the CRC field
    crc = zlib.crc32(data[:checksum_addr])
    crc = zlib.crc32(data[checksum_addr + 4:], crc)
    calc_crc = crc & 0xFFFFFFFF

    if calc_crc == stored_crc:
        return "Checksum is Correct"

    # We repair and preserve
    try:
        data[checksum_addr:checksum_addr + 4] = _pack_u32_le(calc_crc)
        with open(path, "wb") as f:
            f.write(data)
    except Exception as e:
        return "Error: failed to write fixed checksum: %s" % e

    return "Checksum is Fixed"


if __name__ == "__main__":
    print(checksumfix())
