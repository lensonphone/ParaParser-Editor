# - Export: reads a map from *.qdict and writes typed XML (no hex inside fields).
#           If *.qdict is missing/empty — falls back to a single <entry> with hex.
# - Import: reads XML and patches ONLY the specified offsets on top of QTISelectedHex.
#           Returns bytes; trims/pads to QTISelectedLength if the host requires it.
#
# .qdict line format (robust to spaces):
#   offset | type | count | label
# where:
#   offset  — decimal or 0x..., module-relative (unless XML uses absolute mode),
#   type    — f32,f64,u8,u16,u32,u64,s8,s16,s32,s64,ascii,bytes
#             (aliases supported: float32,uint32,string,byte, ...),
#   count   — integer >= 1,
#   label   — text; nesting via "A > B > C".
#
# XML export/import understands:
#   <field label="..." offset="0x..." type="f32|u32|ascii|..." count="N">value(s)</field>
#   <array label="..." offset="0x..." type="..." count="N">v1, v2, v3, ...</array>
#   <entry label="..." offset="0x..." length="0x..." encoding="hex">AA BB CC ...</entry>  # fallback
#   <group label="...">...</group>
# Root options:
#   <qdict offset_mode="relative|absolute" base_offset="0x...">
#   In absolute mode we subtract QTISelectedOffset (if present) or base_offset.

from typing import Optional, List
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import xml.etree.ElementTree as ET
import struct, re

# ---- Filled by the host application ----
QTIDicStatus: str = ""                   # "Export" | "Import"
QTISelectedDicFilePath: str = ""         # path to *.qdict (map)
QTISelectedID: str = ""                  # pretty 0x...
QTISelectedIDRaw: str = ""               # raw id
QTISelectedName: str = ""
QTISelectedHex: str = ""                 # BASE for patching
QTISelectedFilePath: str = ""
QTISelectedOffset: int = 0               # absolute module offset in file (if known)
QTISelectedLength: int = 0               # required module length (host may enforce)
QTISelectedVersion: str = ""
QTISelectedBuffer: bytes = b""           # fallback buffer if Hex is missing




# ---- Behavior ----
TRIKSMODULENAME = "_QTIDictionary"
AllowExportData: int = 1
AllowPrint = 0


# ================= Buffer helpers =================

_HEX_CHARS = re.compile(r'[^0-9A-Fa-f]')

def _base_buffer() -> bytes:
    """Prefer QTISelectedHex as base; fallback to QTISelectedBuffer."""
    if isinstance(QTISelectedHex, str) and QTISelectedHex:
        s = _HEX_CHARS.sub("", QTISelectedHex)
        try:
            return bytes.fromhex(s)
        except Exception:
            pass
    if isinstance(QTISelectedBuffer, (bytes, bytearray)) and QTISelectedBuffer:
        return bytes(QTISelectedBuffer)
    return b""

def _ensure_len(buf: bytes, need_len: int) -> bytes:
    if not need_len or need_len <= 0:
        return buf
    if len(buf) == need_len:
        return buf
    return buf[:need_len] if len(buf) > need_len else buf + b"\x00"*(need_len-len(buf))

def _int_from_any(s: str) -> int:
    s = (s or "").strip()
    return int(s, 16) if s.lower().startswith("0x") else int(s or "0")

def _hex32(v: int) -> str:
    return f"0x{(int(v)&0xFFFFFFFF):08X}"

def _fit_bytes(b: bytes, n: int) -> bytes:
    """Trim/pad to n (useful for fixed-width ascii)."""
    if n <= 0:
        return b
    return b[:n] if len(b) >= n else b + b"\x00"*(n-len(b))

# ================= .QDICT parsing =================

_QDICT_SPLIT = re.compile(r"\s*\|\s*")

def _parse_qdict_line(line: str):
    """
    Format:
      off | type | count | label
    Allows comments (#,//,;). Unrecognized lines are ignored.
    """
    if not line.strip():
        return None
    ls = line.lstrip()
    if ls.startswith(("#","//",";")):
        return None
    parts = _QDICT_SPLIT.split(line.rstrip())
    if len(parts) < 4:
        return None
    off_s, typ, cnt_s, label = parts[:4]
    try:
        off = _int_from_any(off_s)
        cnt = int(cnt_s)
    except Exception:
        return None
    return {"offset": off, "type": _norm_type(typ), "count": cnt, "label": label.strip()}

def _load_qdict(path: str) -> List[dict]:
    items: List[dict] = []
    if not path:
        return items
    try:
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                rec = _parse_qdict_line(ln)
                if rec:
                    items.append(rec)
    except Exception:
        pass
    return items

# ================= Type mapping =================

_FMT = {
    "u8":  ("<B", 1), "s8":  ("<b", 1),
    "u16": ("<H", 2), "s16": ("<h", 2),
    "u32": ("<I", 4), "s32": ("<i", 4),
    "u64": ("<Q", 8), "s64": ("<q", 8),
    "f32": ("<f", 4), "f64": ("<d", 8),
}

_TYPE_ALIASES = {
    "float32":"f32", "float":"f32", "f":"f32",
    "float64":"f64", "double":"f64",
    "uint8":"u8",  "byte":"u8", "bytes":"bytes",
    "int8":"s8",
    "uint16":"u16","int16":"s16",
    "uint32":"u32","int32":"s32",
    "uint64":"u64","int64":"s64",
    "char":"ascii", "string":"ascii", "str":"ascii",
}

def _norm_type(t: str) -> str:
    return _TYPE_ALIASES.get((t or "").strip().lower(), (t or "").strip().lower())

def _fmt_code(typ: str) -> str:
    """Return struct code (B/H/I/Q/f/d)."""
    fmt = _FMT[typ][0]
    return fmt[-1]

def _unpack_typed(buf: bytes, off: int, typ: str, count: int):
    typ = _norm_type(typ)
    n = max(0, int(count))
    if n == 0 or off < 0 or off >= len(buf):
        return [] if typ != "ascii" else ""

    if typ == "bytes":
        end = min(len(buf), off + n)
        return list(buf[off:end])

    if typ == "ascii":
        end = min(len(buf), off + n)
        return bytes(buf[off:end]).split(b"\x00", 1)[0].decode("latin-1", "replace")

    if typ in _FMT:
        _, sz = _FMT[typ]
        maxcnt = min(n, max(0, (len(buf) - off) // sz))
        if maxcnt <= 0:
            return []
        code = _fmt_code(typ)
        return list(struct.unpack_from(f"<{maxcnt}{code}", buf, off))

    # fallback
    end = min(len(buf), off + n)
    return list(buf[off:end])

def _pack_typed(val, typ: str) -> bytes:
    typ = _norm_type(typ)

    if typ == "bytes":
        if isinstance(val, (bytes, bytearray)):
            return bytes(val)
        return bytes(int(x) & 0xFF for x in (val or []))

    if typ == "ascii":
        if isinstance(val, str):
            return val.encode("latin-1", "replace")
        if isinstance(val, (bytes, bytearray)):
            return bytes(val)
        return bytes(int(x) & 0xFF for x in (val or []))

    if typ in _FMT:
        code = _fmt_code(typ)
        if isinstance(val, list):
            return struct.pack(f"<{len(val)}{code}", *[
                (float(x) if typ in ("f32","f64") else int(x)) for x in val
            ])
        return struct.pack(f"<{code}", (float(val) if typ in ("f32","f64") else int(val)))

    # fallback
    if isinstance(val, (bytes, bytearray)):
        return bytes(val)
    if isinstance(val, list):
        return bytes(int(x) & 0xFF for x in val)
    return bytes(val)

# ================= XML build =================

def _pretty_indent(elem: ET.Element, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            _pretty_indent(e, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def _mk_groups(root: ET.Element, label_path: List[str]) -> ET.Element:
    node = root
    for p in label_path:
        if not p:
            continue
        found = None
        for ch in node.findall("group"):
            if ch.attrib.get("label","") == p:
                found = ch; break
        if found is None:
            found = ET.SubElement(node, "group", {"label": p})
        node = found
    return node

def _as_clean_float(x: float) -> str:
    s = f"{float(x):.8f}"
    return s.rstrip("0").rstrip(".") if "." in s else s

def _build_xml_from_qdict(buf: bytes, qitems: List[dict]) -> ET.ElementTree:
    """Build typed XML using .qdict; arrays are formatted as 'v1, v2, v3' (comma-space)."""
    root = ET.Element("qdict", {
        "version": "2.0",
        "unit": "bytes",
        "offset_mode": "relative",
        "base_offset": _hex32(QTISelectedOffset or 0),
    })
    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "name").text = QTISelectedName or ""
    ET.SubElement(meta, "id", {"pretty": QTISelectedID or "", "raw": QTISelectedIDRaw or ""})
    ET.SubElement(meta, "length").text = str(len(buf))
    ET.SubElement(meta, "source").text = QTISelectedFilePath or ""

    for it in qitems:
        off, typ, cnt, label = it["offset"], it["type"], it["count"], it["label"]
        if off < 0 or off >= len(buf):
            continue  # skip invalid
        label_path = [s.strip() for s in label.split(">")]
        parent = _mk_groups(root, label_path[:-1])
        leaf = label_path[-1] if label_path else label

        if typ in ("ascii",) or cnt == 1:
            val = _unpack_typed(buf, off, typ, cnt)
            elem = ET.SubElement(parent, "field", {
                "label": leaf, "offset": _hex32(off), "type": typ, "count": str(cnt)
            })
            if typ in ("f32","f64"):
                v = val[0] if isinstance(val, list) else val
                elem.text = _as_clean_float(v)
            elif typ == "ascii":
                elem.text = val
            else:
                v = val[0] if isinstance(val, list) else val
                elem.text = str(int(v) if isinstance(v, (int, float)) else v)
        else:
            vals = _unpack_typed(buf, off, typ, cnt)
            arr = ET.SubElement(parent, "array", {
                "label": leaf, "offset": _hex32(off), "type": typ, "count": str(cnt)
            })
            line, out_lines = [], []
            for v in vals:
                token = _as_clean_float(v) if typ in ("f32","f64") else str(int(v))
                line.append(token)
                if len(line) >= 32:
                    out_lines.append(", ".join(line)); line = []
            if line: out_lines.append(", ".join(line))
            if out_lines:
                arr.text = "\n    " + "\n    ".join(out_lines) + "\n  "
    _pretty_indent(root)
    return ET.ElementTree(root)

def _build_xml_flat_hex(buf: bytes) -> ET.ElementTree:
    """Fallback: single hex entry."""
    root = ET.Element("qdict", {
        "version": "2.0", "unit": "bytes",
        "offset_mode": "relative",
        "base_offset": _hex32(QTISelectedOffset or 0),
    })
    meta = ET.SubElement(root, "meta")
    ET.SubElement(meta, "name").text = QTISelectedName or ""
    ET.SubElement(meta, "id", {"pretty": QTISelectedID or "", "raw": QTISelectedIDRaw or ""})
    ET.SubElement(meta, "length").text = str(len(buf))
    ET.SubElement(meta, "source").text = QTISelectedFilePath or ""
    entry = ET.SubElement(root, "entry", {
        "label": QTISelectedName or "module",
        "offset": "0x00000000",
        "length": _hex32(len(buf)),
        "encoding": "hex",
    })
    hx = buf.hex().upper()
    entry.text = " ".join(hx[i:i+2] for i in range(0,len(hx),2))
    _pretty_indent(root)
    return ET.ElementTree(root)

# ================= XML → patch =================

def _tok_list(text: str) -> List[str]:
    """Tokenize numbers; accepts 'v1, v2, v3' (comma-space) as well as any commas/whitespace."""
    return [t for t in re.split(r"[\s,]+", (text or "").strip()) if t]

def _apply_xml_patches(xml_path: str, src: bytes) -> bytes:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    offset_mode = (root.attrib.get("offset_mode") or "relative").strip().lower()
    base_offset = _int_from_any(root.attrib.get("base_offset","0"))
    out = bytearray(src)
    total = len(out)
    module_base = QTISelectedOffset or 0

    def rel(off: int) -> int:
        if offset_mode == "absolute":
            return off - (module_base if module_base else base_offset)
        return off

    def write(off_rel: int, data: bytes, label: str):
        end = off_rel + len(data)
        if off_rel < 0 or end > total:
            raise ValueError(f"Patch '{label}' out of bounds (off={off_rel}, size={len(data)}, total={total})")
        out[off_rel:end] = data

    def walk(node):
        tag = node.tag.lower()
        if tag == "field":
            off = rel(_int_from_any(node.attrib["offset"]))
            typ = _norm_type(node.attrib.get("type") or "u8")
            cnt = int(node.attrib.get("count","1"))
            label = node.attrib.get("label","field")
            txt = (node.text or "").strip()
            if typ == "ascii":
                data = _pack_typed(txt, typ)
                data = _fit_bytes(data, cnt) if cnt > 0 else data
                write(off, data, label)
            elif typ in ("f32","f64"):
                tokens = _tok_list(txt)
                if cnt <= 1:
                    val = float(tokens[0]) if tokens else 0.0
                    write(off, _pack_typed(val, typ), label)
                else:
                    vals = [float(t) for t in tokens]
                    if len(vals) != cnt:
                        vals = (vals + [0.0]*cnt)[:cnt]
                    write(off, _pack_typed(vals, typ), label)
            else:
                tokens = _tok_list(txt)
                if cnt <= 1:
                    val = int(tokens[0]) if tokens else 0
                    write(off, _pack_typed(val, typ), label)
                else:
                    vals = [int(t) for t in tokens]
                    if len(vals) != cnt:
                        vals = (vals + [0]*cnt)[:cnt]
                    write(off, _pack_typed(vals, typ), label)

        elif tag == "array":
            off = rel(_int_from_any(node.attrib["offset"]))
            typ = _norm_type(node.attrib.get("type") or "u8")
            cnt = int(node.attrib.get("count","0"))
            label = node.attrib.get("label","array")
            tokens = _tok_list(node.text)
            vals = [float(t) for t in tokens] if typ in ("f32","f64") else [int(t) for t in tokens]
            if cnt and len(vals) != cnt:
                vals = (vals + ([0.0] if typ in ("f32","f64") else [0])*cnt)[:cnt]
            write(off, _pack_typed(vals, typ), label)

        elif tag == "entry":
            off = rel(_int_from_any(node.attrib["offset"]))
            label = node.attrib.get("label","entry")
            data_text = node.attrib.get("data") or (node.text or "")
            hx = _HEX_CHARS.sub("", data_text)
            if len(hx) % 2 != 0:
                raise ValueError("Odd hex length in <entry>")
            blob = bytes.fromhex(hx)
            need_attr = node.attrib.get("length")
            if need_attr:
                need = _int_from_any(need_attr)
                blob = blob + b"\x00"*(need-len(blob)) if len(blob) < need else blob[:need]
            write(off, blob, label)

        for ch in list(node):
            walk(ch)

    walk(root)
    return bytes(out)

# ================= Save / Open =================

def _save_xml(buf: bytes, qitems: List[dict], parent=None):
    suggested = (QTISelectedName or "module").replace(" ","_")
    if QTISelectedIDRaw:
        suggested += f"_{QTISelectedIDRaw}"
    suggested += ".xml"
    path, _ = QFileDialog.getSaveFileName(parent, "Save XML", suggested, "XML files (*.xml)")
    if not path:
        return
    tree = _build_xml_from_qdict(buf, qitems) if qitems else _build_xml_flat_hex(buf)
    tree.write(path, encoding="utf-8", xml_declaration=True)

def _open_xml_and_patch(src: bytes, parent=None) -> Optional[bytes]:
    path, _ = QFileDialog.getOpenFileName(parent, "Open XML", "", "XML files (*.xml)")
    if not path:
        return None
    try:
        return _apply_xml_patches(path, src)
    except Exception as e:
        QMessageBox.critical(parent, "XML Import Error", str(e))
        return None

# ================= Public entry =================

def print_qt_variables_formatted():
    print("╔══════════════════════════════════════════════════════╗")
    print("║                    QTI VARIABLES                     ║")
    print("╠══════════════════════════════════════════════════════╣")
    
    max_length = 50
    vars_to_print = [
        ("Status", QTIDicStatus),
        ("Dictionary File", QTISelectedDicFilePath),
        ("ID", QTISelectedID),
        ("Raw ID", QTISelectedIDRaw),
        ("Name", QTISelectedName),
        ("Hex Dump", QTISelectedHex),
        ("File Path", QTISelectedFilePath),
        ("Offset", QTISelectedOffset),
        ("Length", QTISelectedLength),
        ("Version", QTISelectedVersion),
        ("Return Buffer", QTISelectedBuffer)
    ]
    
    for name, value in vars_to_print:
        print(f"║ {name:15}: {str(value):35} ║")
    
    print("╚══════════════════════════════════════════════════════╝")

def run(parent=None) -> Optional[bytes]:
    """
    No snapshot dialog.
    - Export: uses .qdict (if provided) to emit typed XML; otherwise a hex fallback.
    - Import: loads XML and patches only specified offsets on top of BASE (QTISelectedHex),
              returns bytes trimmed/padded to QTISelectedLength (if provided).
    """

    if AllowPrint == 1:
        print_qt_variables_formatted()
    
    buf = _base_buffer()
    qitems = _load_qdict(QTISelectedDicFilePath) if QTISelectedDicFilePath else []

    if QTIDicStatus == "Export":
        _save_xml(buf, qitems, parent=parent)
        return None

    if QTIDicStatus == "Import" and AllowExportData == 1:
        patched = _open_xml_and_patch(buf, parent=parent)
        if patched is None:
            return None
        return _ensure_len(patched, int(QTISelectedLength) if QTISelectedLength else 0)

    return None
