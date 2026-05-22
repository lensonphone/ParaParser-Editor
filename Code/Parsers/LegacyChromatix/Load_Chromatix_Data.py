import os
import sys
import struct
from typing import Optional, List, Dict, Tuple

# ============================================================
#  Global defaults / state
# ============================================================

LEGACY_CHROMATIX_LIB_PATH = "_SO/libchromatix_0310_common.so" # can be overridden via env
LOAD_CHROMATIX_VER: str = "" # version string like "0.3.10"
LCOFF: Optional[int] = None # found file offset CONTENT
LCLENGTH: Optional[int] = None # approximate length CONTENT

AllowDebug = 0 # 0 = quiet, 1 = print _dbg()


# ============================================================
#  Debug print
# ============================================================
def _dbg(*args, sep=" ", end="\n", file=sys.stdout, flush=False):
    if AllowDebug:
        print(*args, sep=sep, end=end, file=file, flush=flush)


# ============================================================
#  ELF constants / helpers
# ============================================================
ELF_MAGIC = b"\x7fELF"
ELFCLASS32, ELFCLASS64 = 1, 2
ELFDATA2LSB = 1
PT_LOAD = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_DYNSYM = 11

class ELFError(Exception):
    pass

def _read(f, off, size) -> bytes:
    f.seek(off)
    b = f.read(size)
    if len(b) != size:
        raise ELFError("Unexpected EOF")
    return b

def _u16(b: bytes) -> int:
    return struct.unpack('<H', b)[0]

def _u32(b: bytes) -> int:
    return struct.unpack('<I', b)[0]

def hexdump_context(blob: bytes, center_off: int, span: int = 0x40) -> str:
    """
    Returns a mini-hexdump +-span around the offset center_off.
    """
    start = max(0, center_off - span)
    end   = min(len(blob), center_off + span)
    view = blob[start:end]
    rel = center_off - start
    out_lines = []
    for i in range(0, len(view), 16):
        chunk = view[i:i+16]
        offs = start + i
        hexs = ' '.join(f"{bb:02X}" for bb in chunk)
        mark = '<' if i <= rel < i+16 else ' '
        out_lines.append(f"0x{offs:08X}{mark}  {hexs}")
    return "\n".join(out_lines)


# ============================================================
#  ELF parsing
# ============================================================
def parse_elf_headers(f) -> Dict:
    """
    Read the ELF header and return key fields.
    """
    e_ident = _read(f, 0, 16)
    if e_ident[:4] != ELF_MAGIC:
        raise ELFError("Not an ELF file")
    if e_ident[5] != ELFDATA2LSB:
        raise ELFError("Only little-endian ELF is supported")

    if e_ident[4] == ELFCLASS32:
        fmt = '<HHIIIIIHHHHHH'
        (e_type,e_machine,e_version,e_entry,e_phoff,e_shoff,
         e_flags,e_ehsize,e_phentsize,e_phnum,
         e_shentsize,e_shnum,e_shstrndx) = struct.unpack(
            fmt, _read(f,16,struct.calcsize(fmt))
        )
        bits = 32
    elif e_ident[4] == ELFCLASS64:
        fmt = '<HHIQQQIHHHHHH'
        (e_type,e_machine,e_version,e_entry,e_phoff,e_shoff,
         e_flags,e_ehsize,e_phentsize,e_phnum,
         e_shentsize,e_shnum,e_shstrndx) = struct.unpack(
            fmt, _read(f,16,struct.calcsize(fmt))
        )
        bits = 64
    else:
        raise ELFError("Unsupported ELF class")

    return {
        'bits': bits,
        'machine': e_machine,
        'e_phoff': e_phoff,
        'e_phentsize': e_phentsize,
        'e_phnum': e_phnum,
        'e_shoff': e_shoff,
        'e_shentsize': e_shentsize,
        'e_shnum': e_shnum,
        'e_shstrndx': e_shstrndx,
    }

def parse_program_headers(f, elf) -> List[Dict]:
    """
    Read the Program Header Table.
    """
    phs = []
    off = elf['e_phoff']
    for _ in range(elf['e_phnum']):
        if elf['bits'] == 32:
            fmt = '<IIIIIIII'
            (
                p_type,p_offset,p_vaddr,p_paddr,
                p_filesz,p_memsz,p_flags,p_align
            ) = struct.unpack(fmt, _read(f,off,struct.calcsize(fmt)))
        else:
            fmt = '<IIQQQQQQ'
            (
                p_type,p_flags,p_offset,p_vaddr,
                p_paddr,p_filesz,p_memsz,p_align
            ) = struct.unpack(fmt, _read(f,off,struct.calcsize(fmt)))
        phs.append({
            'p_type':   p_type,
            'p_offset': p_offset,
            'p_vaddr':  p_vaddr,
            'p_filesz': p_filesz,
            'p_memsz':  p_memsz,
            'p_flags':  p_flags
        })
        off += elf['e_phentsize']
    return phs

def va_to_file_off(va:int, phs:List[Dict]) -> Optional[int]:
    """
    Convert a virtual address to a file offset.
    """
    for ph in phs:
        if ph['p_type'] != PT_LOAD:
            continue
        v0 = ph['p_vaddr']
        v1 = v0 + ph['p_memsz']
        if v0 <= va < v1:
            return ph['p_offset'] + (va - v0)
    return None

def parse_section_headers(f, elf) -> List[Dict]:
    """
    Read the Section Header Table + section names.
    """
    shs = []
    off = elf['e_shoff']
    for _ in range(elf['e_shnum']):
        if elf['bits'] == 32:
            fmt = '<IIIIIIIIII'
            (
                sh_name,sh_type,sh_flags,sh_addr,
                sh_offset,sh_size,sh_link,sh_info,
                sh_addralign,sh_entsize
            ) = struct.unpack(fmt, _read(f,off,struct.calcsize(fmt)))
        else:
            fmt = '<IIQQQQIIQQ'
            (
                sh_name,sh_type,sh_flags,sh_addr,
                sh_offset,sh_size,sh_link,sh_info,
                sh_addralign,sh_entsize
            ) = struct.unpack(fmt, _read(f,off,struct.calcsize(fmt)))
        shs.append({
            'sh_name':sh_name,'sh_type':sh_type,'sh_flags':sh_flags,'sh_addr':sh_addr,
            'sh_offset':sh_offset,'sh_size':sh_size,'sh_link':sh_link,'sh_info':sh_info,
            'sh_addralign':sh_addralign,'sh_entsize':sh_entsize
        })
        off += elf['e_shentsize']

    # section with names
    if 0 <= elf['e_shstrndx'] < len(shs):
        shstr = shs[elf['e_shstrndx']]
        names = _read(f, shstr['sh_offset'], shstr['sh_size'])
    else:
        names = b''

    for i, sh in enumerate(shs):
        n = sh['sh_name']
        if n < len(names):
            end = names.find(b'\x00', n)
            sh['name'] = names[n:end].decode(errors='replace')
        else:
            sh['name'] = ''
        sh['index'] = i

    return shs

def load_strtab(f, sh) -> bytes:
    return _read(f, sh['sh_offset'], sh['sh_size'])

def read_symbols(f, elf, sh_sym, sh_str) -> List[Dict]:
    """
    Read the symbol table (dynsym/symtab).
    """
    strtab = load_strtab(f, sh_str)
    entsz = sh_sym['sh_entsize'] or (16 if elf['bits']==32 else 24)
    count = sh_sym['sh_size'] // entsz
    syms = []
    off = sh_sym['sh_offset']
    for _ in range(count):
        if elf['bits']==32:
            (
                st_name,st_value,st_size,
                st_info,st_other,st_shndx
            ) = struct.unpack('<IIIBBH', _read(f,off,entsz))
        else:
            (
                st_name,st_info,st_other,
                st_shndx,st_value,st_size
            ) = struct.unpack('<IBBHQQ', _read(f,off,entsz))

        name = ''
        if st_name < len(strtab):
            end = strtab.find(b'\x00', st_name)
            name = strtab[st_name:end].decode(errors='replace')
        syms.append({
            'name':name,
            'st_value':st_value,
            'st_size':st_size,
            'st_info':st_info,
            'st_other':st_other,
            'st_shndx':st_shndx
        })
        off += entsz
    return syms

def find_symbol_va(f, elf, shs, target:str) -> Optional[int]:
    """
    Find the virtual address of the target symbol (e.g., load_chromatix).
    """
    dynsym = next((s for s in shs if s['name']=='.dynsym'), None)
    dynstr = next((s for s in shs if s['name']=='.dynstr'), None)
    if dynsym and dynstr:
        for s in read_symbols(f,elf,dynsym,dynstr):
            if s['name'] == target:
                return s['st_value']

    symtab = next((s for s in shs if s['name']=='.symtab'), None)
    strtab = next((s for s in shs if s['name']=='.strtab'), None)
    if symtab and strtab:
        for s in read_symbols(f,elf,symtab,strtab):
            if s['name'] == target:
                return s['st_value']

    return None


# ============================================================
#  Helpers for segments
# ============================================================
def rw_ptload_ranges(phs:List[Dict]) -> List[Tuple[int,int]]:
    """
    Returns a list (start_va, end_va) for RW segments (p_flags & 0x2).
    """
    out = []
    for p in phs:
        if p['p_type'] == PT_LOAD and (p['p_flags'] & 0x2):
            out.append((p['p_vaddr'], p['p_vaddr'] + p['p_memsz']))
    return out

def in_any_range(va:int, ranges:List[Tuple[int,int]]) -> bool:
    for a, b in ranges:
        if a <= va < b:
            return True
    return False

def get_text_section(shs):
    return next((s for s in shs if s.get('name') == '.text'), None)


# ============================================================
#  Thumb stub scan
# ============================================================
def scan_thumb_stubs_in_text(path: str, phs, shs) -> List[Dict]:
    """
    Find the Thumb pattern by .text:
        LDR r0,[PC,#imm8]; ADD r0,PC; BX LR
    This is a classic minimalistic loader that returns the block address.
    Returns a list of candidates {'stub_va','data_va','data_off','lit_va','method'}.
    """
    text = get_text_section(shs)
    if not text:
        return []
    start_va = text['sh_addr']
    start_off = va_to_file_off(start_va, phs)
    if start_off is None:
        return []

    rw_ranges = rw_ptload_ranges(phs)
    out = []

    with open(path, 'rb') as f:
        f.seek(start_off)
        blob = f.read(text['sh_size'])

    for i in range(0, len(blob) - 6, 2): # halfword step
        h0 = _u16(blob[i:i+2]) # expected 0x48??
        h1 = _u16(blob[i+2:i+4]) # expected 0x4478
        h2 = _u16(blob[i+4:i+6]) # expected 0x4770
        if (h0 & 0xF800) == 0x4800 and h1 == 0x4478 and h2 == 0x4770:
            # found LDR r0,[PC,#imm8]; ADD r0,PC; BX LR
            code_va = start_va + i
            imm8 = h0 & 0xFF
            lit_va = ((code_va + 4) & ~3) + (imm8 << 2)
            lit_off = va_to_file_off(lit_va, phs)
            if lit_off is None:
                continue
            with open(path, 'rb') as f2:
                f2.seek(lit_off)
                lit_word = _u32(f2.read(4))

            pc_for_add = (code_va + 2 + 4) # address(ADD)+4
            data_va = (lit_word + pc_for_add) & 0xFFFFFFFF
            if in_any_range(data_va, rw_ranges):
                out.append({
                    'stub_va': code_va | 1,
                    'data_va': data_va,
                    'data_off': va_to_file_off(data_va, phs),
                    'lit_va': lit_va,
                    'method': 'THUMB LDR+ADD.PC',
                })
    return out


# ============================================================
#  CONTENT size inference
# ============================================================
def infer_content_size(path: str, phs: List[Dict], content_va: int) -> Optional[int]:
    """
    Attempt to treat first u32 as length.
    If it looks plausible and fits into the segment, then ok.
    """
    rw_seg = None
    for ph in phs:
        if ph['p_type'] == PT_LOAD and (ph['p_flags'] & 0x2):
            v0, v1 = ph['p_vaddr'], ph['p_vaddr'] + ph['p_memsz']
            if v0 <= content_va < v1:
                rw_seg = ph
                break
    if not rw_seg:
        return None

    content_off = va_to_file_off(content_va, phs)
    if content_off is None:
        return None

    with open(path, 'rb') as f:
        f.seek(content_off)
        raw = f.read(4)
    if len(raw) != 4:
        return None

    sz = struct.unpack('<I', raw)[0]
    if sz == 0 or (sz % 4) != 0:
        return None

    max_len = (rw_seg['p_vaddr'] + rw_seg['p_memsz']) - content_va
    if sz > max_len:
        return None

    return sz

def segment_remaining_size(phs: List[Dict], content_va: int, content_off: int) -> Optional[int]:
    """
    Fallback: how many bytes remain in the RW segment starting from this point.
    """
    seg = None
    for p in phs:
        if p['p_type'] == PT_LOAD and (p['p_flags'] & 0x2):
            v0, v1 = p['p_vaddr'], p['p_vaddr'] + p['p_memsz']
            if v0 <= content_va < v1:
                seg = p
                break
    if not seg:
        return None

    file_tail = (seg['p_offset'] + seg['p_filesz']) - content_off
    if file_tail < 0:
        return None
    mem_tail  = (seg['p_vaddr'] + seg['p_memsz']) - content_va
    if mem_tail < 0:
        return None

    return min(file_tail, mem_tail)


# ============================================================
#  Header / rescue logic
# ============================================================

# We support versions 0.3.01 .. 0.3.10.
# In different libraries, the first u32 can look like either "0x00000309" or "0x09060304", etc.
# Therefore, we put here both known pure words and any exotic ones we come across. 417|1|0x09060304, # variant encountered in 0.3.04
HDR_WORDS = {
    0x00000300,
    0x00000301,
    0x00000302,
    0x00000303,
    0x00000304,
    0x09060304,  # variant at 0.3.04
    0x00000305,
    0x00000306,
    0x00000307,
    0x00000308,
    0x00000309,
    0x00000310,
    0x00000103, # early permutations
    0x00001003,
}

END_MARKERS = [
    b"\x00GCC", b"GCC\x00",
    b"\x00\x00\x00aeabi", b"aeabi\x00",
    bytes.fromhex("0000000900000004000000474E55"),  # ...GNU
    b"\x00GNU", b"GNU\x00",
]

def _looks_like_header_bytes(hdr: bytes) -> bool:
    """
    Heuristic "Is this the beginning of a large Chromatix calibration block?"
    Works for 0.3.01 .. 0.3.10 (0301 .. 0310, including 0302 .. 0309).
    """
    if len(hdr) < 8:
        return False

    w0 = _u32(hdr[:4])
    if w0 in HDR_WORDS:
        return True

    # Generalized check:
    # byte0 = patch (usually 0x01 .. 0x10),
    # byte1 = 0x03 (minor=3),
    # The following are service words, which do not have to be zero.
    patch = hdr[0]
    minor = hdr[1]

    if minor == 0x03 and 1 <= patch <= 0x20:
        return True

    return False

def _valid_header_at(path: str, off: int) -> bool:
    """
    Check if there's something resembling a Chromatix header at offset off.
    """
    try:
        with open(path, 'rb') as f:
            f.seek(off)
            hdr = f.read(16)
        return _looks_like_header_bytes(hdr)
    except Exception:
        return False

def _size_by_end_markers(path: str, start_off: int) -> Optional[int]:
    """
    Look for the nearest marker like 'GCC', 'aeabi', 'GNU' to estimate the end of the block.
    """
    with open(path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        fsz = f.tell()
        f.seek(start_off)
        blob = f.read(fsz - start_off)

    best = None
    for m in END_MARKERS:
        j = blob.find(m)
        if j != -1:
            pos = start_off + j
            if best is None or pos < best:
                best = pos

    if best is None or best <= start_off:
        return None
    return best - start_off

def _rescue_locate(path: str, phs: List[Dict], tried_off: Optional[int]) -> Optional[Tuple[int,int]]:
    """
    Rescue mode:
    - try historical offset 0x3004,
    - otherwise, scan the entire file word by word (4-byte increments),
    look for something resembling a Chromatix header (0.3.xx),
    estimate the size by markers / by the tail of the RW segment.
    """
    def size_from(off:int) -> Optional[int]:
        # First, try markers ('GCC', 'aeabi', 'GNU').
        sz = _size_by_end_markers(path, off)
        if sz and sz > 0:
            return sz

        # If no markers are found, count to the end of the RW segment.
        va_guess = None
        for p in phs:
            if p['p_type']==PT_LOAD and (p['p_flags'] & 0x2):
                base  = p['p_offset']
                vbase = p['p_vaddr']
                if base <= off < base + p['p_filesz']:
                    va_guess = vbase + (off - base)
                    file_tail = (p['p_offset'] + p['p_filesz']) - off
                    mem_tail  = (p['p_vaddr']  + p['p_memsz']) - va_guess
                    if file_tail > 0 and mem_tail > 0:
                        return min(file_tail, mem_tail)
        return None

    # A) Hard historical offset 0x3004
    off_3004 = 0x3004
    if tried_off != off_3004 and off_3004 >= 0 and _valid_header_at(path, off_3004):
        sz = size_from(off_3004)
        if sz:
            return (off_3004, sz)

    # B) Full brute force on the file in 4-byte increments
    with open(path, 'rb') as f:
        blob = f.read()

    for i in range(0, len(blob) - 16, 4):
        if _looks_like_header_bytes(blob[i:i+16]):
            sz = size_from(i)
            if sz:
                return (i, sz)

    return None


# ============================================================
#  Version helpers
# ============================================================
def _bcd_to_int(x: int) -> int:
    """
    Interpret the low-order byte of the version as BCD:
    0x10 -> 10, 0x09 -> 9, etc.
    """
    return (x >> 4) * 10 + (x & 0x0F)

def _u16_le(buf: bytes) -> int:
    return struct.unpack('<H', buf)[0]

def _format_ver_ascii(u16_le: int) -> str:
    """
    Convert the first two bytes of the block to a string like "0.3.10".
    u16 little-endian:
    Hi = minor (e.g. 0x03 -> 3)
      Lo = patch (BCD: 0x10 -> 10).
    Examples:
      0x0301 -> "0.3.1"
      0x0304 -> "0.3.4"
      0x0309 -> "0.3.9"
      0x0310 -> "0.3.10"
    """
    minor = (u16_le >> 8) & 0xFF
    patch_bcd = u16_le & 0xFF
    patch = _bcd_to_int(patch_bcd)
    return f"0.{minor}.{patch}"


# ============================================================
#  Core logic
# ============================================================
def load_chromatix_offsets(path: str) -> Optional[Tuple[int,int]]:
    """
    Finds CONTENT:
    1) looks for the load_chromatix symbol (if not removed),
    tries to calculate the block address directly OR via a Thumb stub,
    validates the header.
    2) if that fails, scans .text for Thumb stubs,
    try all candidates.
    3) if still unsuccessful — rescue: global brute force on the file.
    Returns (file_off, size) or None.
    """
    global LEGACY_CHROMATIX_LIB_PATH, LCOFF, LCLENGTH
    LEGACY_CHROMATIX_LIB_PATH = path

    with open(path, 'rb') as f:
        elf = parse_elf_headers(f)
        phs = parse_program_headers(f, elf)
        shs = parse_section_headers(f, elf)

        # helper: final code for the content_va address
        def finalize(content_va: int) -> Optional[Tuple[int,int]]:
            content_off = va_to_file_off(content_va, phs)
            if content_off is None:
                return None
            size_hdr = infer_content_size(path, phs, content_va) or 0
            size_seg = segment_remaining_size(phs, content_va, content_off) or 0

            # prefer_seg = True if the segment starts exactly at content_va
            prefer_seg = False
            for p in phs:
                if (
                    p['p_type'] == PT_LOAD and
                    (p['p_flags'] & 0x2) and
                    p['p_vaddr'] == content_va
                ):
                    prefer_seg = True
                    break

            chosen = size_seg if (prefer_seg and size_seg) else (size_seg or size_hdr or 0)
            return (content_off, chosen)

        # ----------------------------------------------------
        # 1) Path via the 'load_chromatix' symbol
        # ----------------------------------------------------
        load_va = find_symbol_va(f, elf, shs, 'load_chromatix')
        if load_va is not None:
            # Attempt to interpret this as a Thumb stub
            code_va = load_va & ~1
            off = va_to_file_off(code_va, phs)
            candidate_pairs = []

            if off is not None:
                try:
                    code = _read(f, off, 6)
                except ELFError:
                    code = b''

                if len(code) >= 6:
                    h0 = _u16(code[0:2])
                    h1 = _u16(code[2:4])
                    h2 = _u16(code[4:6])

                    # classic LDR+ADD+BX
                    if (h0 & 0xF800) == 0x4800 and h1 == 0x4478 and h2 == 0x4770:
                        imm8 = h0 & 0xFF
                        lit_va = ((code_va + 4) & ~3) + (imm8 << 2)
                        lit_off = va_to_file_off(lit_va, phs)
                        if lit_off is not None:
                            with open(path, 'rb') as f2:
                                f2.seek(lit_off)
                                lit_word = _u32(f2.read(4))
                            pc_for_add = (code_va + 2 + 4)
                            data_va = (lit_word + pc_for_add) & 0xFFFFFFFF
                            candidate_pairs.append(data_va)

                    # alternative: the compiler could have simply returned the address of a global variable.
                    # Then load_va is already a function, which is essentially "return &data_xxxx".
                    # We can't reliably decode this without a disassembler,
                    # but the function itself is often located next to the RW data.
                    # This is a heuristic fallback: if load_va itself falls into the RW segment,
                    # then we consider load_va as content_va.
                    if in_any_range(load_va, rw_ptload_ranges(phs)):
                        candidate_pairs.append(load_va)

            # Check all candidates from this step
            for cand_va in candidate_pairs:
                res = finalize(cand_va)
                if res:
                    foff_tmp, size_tmp = res
                    if _valid_header_at(path, foff_tmp):
                        # bingo
                        LCOFF, LCLENGTH = foff_tmp, size_tmp
                        return (foff_tmp, size_tmp)
                    else:
                        _dbg(f"[candidate_rejected_sym] off=0x{foff_tmp:X} size=0x{size_tmp:X}")

        # ----------------------------------------------------
        # 2) Stripped: manually search for Thumb stubs in .text
        # ----------------------------------------------------
        cands = scan_thumb_stubs_in_text(path, phs, shs)
        for c in cands:
            if c['data_off'] is None:
                continue
            res = finalize(c['data_va'])
            if res:
                foff_tmp, size_tmp = res
                if _valid_header_at(path, foff_tmp):
                    LCOFF, LCLENGTH = foff_tmp, size_tmp
                    return (foff_tmp, size_tmp)
                else:
                    _dbg(f"[candidate_rejected_stub] off=0x{foff_tmp:X} size=0x{size_tmp:X}")

    # --------------------------------------------------------
    # 3) RESCUE: brute force on file, '`GCC`/`aeabi`/`GNU`' markers
    # --------------------------------------------------------
    with open(path, 'rb') as f:
        elf_r = parse_elf_headers(f)
        phs_r = parse_program_headers(f, elf_r)

    r = _rescue_locate(path, phs_r, tried_off=None)
    if r:
        foff, size = r
        LCOFF, LCLENGTH = foff, size
        return (foff, size)

    return None


def load_chromatix_version(path_ver: str) -> Optional[str]:
    """
    Returns a version string like '0.3.10', '0.3.4', ...
    Algorithm:
    - ensures that LCOFF/LCLENGTH are filled in via load_chromatix_offsets
    - reads the first 2 bytes of the block as u16 LE
    - converts to "0.minor.patch"
    Also updates the global LOAD_CHROMATIX_VER.
    """
    global LEGACY_CHROMATIX_LIB_PATH, LCOFF, LCLENGTH, LOAD_CHROMATIX_VER

    if not path_ver or not os.path.isfile(path_ver):
        _dbg(f"[load_chromatix_version] File not found or empty path: {path_ver}", file=sys.stderr)
        return None

    need_find = (LCOFF is None) or (LEGACY_CHROMATIX_LIB_PATH != path_ver)
    if need_find:
        res = load_chromatix_offsets(path_ver)
        if not res:
            _dbg("[load_chromatix_version] Failed to locate CONTENT offset.", file=sys.stderr)
            return None
        foff, size = res
        LEGACY_CHROMATIX_LIB_PATH = path_ver
        LCOFF, LCLENGTH = foff, size

    if LCOFF is None:
        _dbg("[load_chromatix_version] LCOFF is None after offset search.", file=sys.stderr)
        return None

    try:
        with open(path_ver, 'rb') as f:
            f.seek(LCOFF)
            header2 = f.read(2)
        if len(header2) != 2:
            _dbg("[load_chromatix_version] Could not read 2 bytes at LCOFF.", file=sys.stderr)
            return None

        ver_u16_le = _u16_le(header2)
        ver_ascii = _format_ver_ascii(ver_u16_le)

        LOAD_CHROMATIX_VER = ver_ascii
        _dbg(f"[load_chromatix_version] RAW=0x{ver_u16_le:04X} -> '{ver_ascii}'")

        return ver_ascii

    except Exception as e:
        _dbg(f"[load_chromatix_version] IO error: {e}", file=sys.stderr)
        return None


# ============================================================
#  Verbose report / CLI
# ============================================================
def run_verbose(path: str, prefound: Optional[Tuple[int,int]] = None):
    """
    Prints debug info:
    - ELF segments
    - FOUND_FOFF / FOUND_SIZE
    - mini-hexdump around CONTENT
    """
    with open(path, 'rb') as f:
        elf = parse_elf_headers(f)
        phs = parse_program_headers(f, elf)
        shs = parse_section_headers(f, elf)

        _dbg(f"File: {path}")
        _dbg(f"Bits: {elf['bits']}, PH num: {elf['e_phnum']}, SH num: {elf['e_shnum']}\n")
        _dbg("PT_LOAD segments (for VA → FOFF mapping):")
        for ph in phs:
            if ph['p_type'] == PT_LOAD:
                _dbg(
                    f"  VBase=0x{ph['p_vaddr']:X}  FBase=0x{ph['p_offset']:X}  "
                    f"VEnd=0x{ph['p_vaddr']+ph['p_memsz']:X}  FileSz=0x{ph['p_filesz']:X}"
                )
        _dbg()

    if prefound is None:
        res = load_chromatix_offsets(path)
        if not res:
            _dbg("Failed to locate CONTENT.")
            return
        foff, size = res
    else:
        foff, size = prefound

    _dbg(f"FOUND_FOFF=0x{foff:X}")
    _dbg(f"FOUND_SIZE=0x{size:X}")

    with open(path, 'rb') as f0:
        blob = f0.read()
    _dbg("\nHex context around CONTENT FOFF:")
    _dbg(hexdump_context(blob, foff))


def main():
    """
    CLI:
    - reads path from env LEGACY_CHROMATIX_LIB_PATH or from global
    - finds CONTENT
    - prints flags
    """
    path = os.environ.get("LEGACY_CHROMATIX_LIB_PATH", LEGACY_CHROMATIX_LIB_PATH)
    if not path or not isinstance(path, str):
        _dbg("LEGACY_CHROMATIX_LIB_PATH is empty. Set env var or edit LEGACY_CHROMATIX_LIB_PATH default.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(path):
        _dbg(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    res = load_chromatix_offsets(path)
    if not res:
        _dbg("FOUND_FOFF=<none>")
        _dbg("FOUND_SIZE=<unknown>")
        if AllowDebug:
            run_verbose(path, prefound=None)
        return

    foff, size = res
    _dbg(f"FOUND_FOFF=0x{foff:X}")
    _dbg(f"FOUND_SIZE=0x{size:X}")

    if AllowDebug:
        run_verbose(path, prefound=(foff, size))

    # Let's try to read the version right away
    ver = load_chromatix_version(path)
    if ver is not None:
        _dbg(f"LOAD_CHROMATIX_VER={ver}")


if __name__ == '__main__':
    main()
