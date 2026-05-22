# -*- coding: utf-8 -*-
import sys, re, struct
from typing import Optional, List, Tuple, Dict

from PyQt5.QtCore import Qt, QByteArray, QMimeData, QEvent, QRegExp
from PyQt5.QtGui import (
    QFont, QFontDatabase, QFontMetrics, QFontMetricsF,
    QGuiApplication, QClipboard, QKeySequence, QColor, QTextCursor, QTextCharFormat,
    QRegExpValidator
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QGroupBox, QFormLayout, QComboBox, QLabel, QSplitter, QMenu, QShortcut,
    QTabWidget, QToolTip, QPushButton, QFileDialog, QMessageBox, QInputDialog,
    QTextEdit, QDialog, QLineEdit, QDialogButtonBox
)

FIGURE_SPACE = '\u2007'  # U+2007
QTIDictionaryCreatorVer = "0.5"

# ---- Globals for run() ----
QTISelectedID = ""
QTISelectedIDRaw = ""
QTISelectedName = ""
QTISelectedHex = ""
QTISelectedFilePath = ""
QTISelectedOffset = 0
QTISelectedLength = 0
QTISelectedVersion = ""

# ---------------------- helpers ----------------------
TYPE_SIZES = {"u8": 1, "u16": 2, "f32": 4, "ascii": 1}
ALLOWED_TYPES = ("u8", "u16", "f32", "ascii")
TYPE_ORDER = {"u8": 0, "u16": 1, "f32": 2, "ascii": 3}


class BookmarkDialog(QDialog):
    """Bookmark creation dialog: Label, Type, Indent (0..4). Count is calculated automatically."""
    def __init__(self, length: int, buf: bytes, parent=None,
                 default_type: str = "u8", default_label: str = "label",
                 default_indent: int = 0):
        super().__init__(parent)
        self.setWindowTitle("Add Bookmark")
        self._length = int(length)
        self._buf = bytes(buf)

        form = QFormLayout(self)

        # Label
        self.ed_label = QLineEdit(self)
        self.ed_label.setText(default_label)
        form.addRow("Label", self.ed_label)

        # Type options
        self.cb_type = QComboBox(self)
        self._ascii_ok = all(32 <= b <= 126 for b in self._buf) and self._length > 0

        options = ["u8"]
        if self._length % 2 == 0:
            options.append("u16")
        if self._length % 4 == 0:
            options.append("f32")
        if self._ascii_ok:
            options.append("ascii")

        start_type = default_type if default_type in options else ("ascii" if ("ascii" in options and self._ascii_ok) else options[0])
        for t in options:
            self.cb_type.addItem(t)
        self.cb_type.setCurrentText(start_type)
        form.addRow("Type", self.cb_type)

        # Indent 0..4
        self.cb_indent = QComboBox(self)
        for i in range(5):
            self.cb_indent.addItem(str(i), i)
        self.cb_indent.setCurrentIndex(max(0, min(default_indent, 4)))
        form.addRow("Indent", self.cb_indent)

        # Count (read-only)
        self.lbl_count = QLabel(self)
        form.addRow("Count", self.lbl_count)

        self.cb_type.currentTextChanged.connect(self._recalc_count)
        self._recalc_count()

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

        if parent and hasattr(parent, "text"):
            f = parent.text.font()
            self.setFont(f)

    def _recalc_count(self):
        t = self.cb_type.currentText()
        cnt = 1 if t == "ascii" else (self._length // TYPE_SIZES[t])
        self.lbl_count.setText(str(cnt))

    def result_values(self):
        t = self.cb_type.currentText()
        label = self.ed_label.text().strip() or "label"
        indent = int(self.cb_indent.currentData())
        count = 1 if t == "ascii" else (self._length // TYPE_SIZES[t])
        return {"type": t, "count": count, "label": label, "indent": indent}


class FindHexDialog(QDialog):
    """Search dialog: enter a HEX string (without length limit, except max_bytes).
    OK is active only if an integer number of bytes (an even number of digits) is entered and >0."""
    def __init__(self, max_bytes: int, initial: Optional[bytes] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find Hex")
        self._max = int(max_bytes)
        form = QFormLayout(self)

        self.ed_hex = QLineEdit(self)
        self.ed_hex.setPlaceholderText("DE AD BE EF")
        # Allow only HEX and spaces
        self.ed_hex.setValidator(QRegExpValidator(QRegExp(r"[0-9A-Fa-f\s]*")))
        if initial:
            self.ed_hex.setText(" ".join(f"{b:02X}" for b in initial))
        form.addRow("Hex bytes", self.ed_hex)

        self.lbl_info = QLabel(self)
        form.addRow("Bytes", self.lbl_info)

        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        self.btns.accepted.connect(self._on_accept)
        self.btns.rejected.connect(self.reject)
        form.addRow(self.btns)

        if parent and hasattr(parent, "text"):
            self.setFont(parent.text.font())

        self._bytes = b""
        self.ed_hex.textChanged.connect(self._on_changed)
        self._on_changed()

    def _on_changed(self):
        cleaned = re.sub(r"[^0-9A-Fa-f]", "", self.ed_hex.text())
        nibbles = len(cleaned)
        byte_count = nibbles // 2
        valid = (nibbles % 2 == 0) and (byte_count > 0) and (byte_count <= self._max)
        self.lbl_info.setText(f"{byte_count} / {self._max}")
        self.lbl_info.setStyleSheet("" if valid else "color:#c00;")
        self.btns.button(QDialogButtonBox.Ok).setEnabled(valid)
        try:
            self._bytes = bytes.fromhex(cleaned) if valid else b""
        except Exception:
            self._bytes = b""
            self.btns.button(QDialogButtonBox.Ok).setEnabled(False)

    def _on_accept(self):
        if not self._bytes:
            return
        self.accept()

    @property
    def pattern(self) -> bytes:
        return self._bytes


class MonoText(QPlainTextEdit):
    """Read-only monospaced widget with custom Copy and context menu."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setStyleHint(QFont.Monospace)
        mono.setFixedPitch(True)
        mono.setKerning(False)
        mono.setPointSize(12)
        self.setFont(mono)

        self.update_doc_margin()

        self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursorWidth(2)

        self._on_resized: Optional[callable] = None
        self._custom_copy_handler: Optional[callable] = None

        QShortcut(QKeySequence.Copy, self, activated=self._do_copy_raw)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._on_resized:
            self._on_resized()

    def _do_copy_raw(self):
        if self._custom_copy_handler and self.textCursor().hasSelection():
            self._custom_copy_handler()

    def copy(self):
        self._do_copy_raw()

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        act_copy = menu.addAction("Copy")
        act_copy.triggered.connect(self._do_copy_raw)
        menu.addSeparator()
        act_sel_all = menu.addAction("Select All")
        act_sel_all.triggered.connect(self.selectAll)
        menu.exec_(e.globalPos())

    def update_doc_margin(self):
        fm = QFontMetricsF(self.font())
        m = max(8.0, 1.5 * fm.horizontalAdvance('0'))
        self.document().setDocumentMargin(m)


def make_ro_editor(point_size: int) -> QPlainTextEdit:
    ed = QPlainTextEdit()
    ed.setReadOnly(True)
    ed.setLineWrapMode(QPlainTextEdit.NoWrap)
    f = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    f.setStyleHint(QFont.Monospace)
    f.setFixedPitch(True)
    f.setKerning(False)
    f.setPointSize(point_size)
    ed.setFont(f)
    fm = QFontMetricsF(f)
    ed.document().setDocumentMargin(max(8.0, 1.5 * fm.horizontalAdvance('0')))
    return ed


class HexDictionaryViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hex Dictionary Viewer")

        # state
        self.data: bytes = b""
        self.group_mode: str = "1"  # "1", "2", "4", "ASCII"

        # selection maps
        self._char2byte: List[Tuple[int, int]] = []
        self._byte2span: List[Tuple[int, int]] = []
        self._snap_guard: bool = False

        # qdict bookmarks
        self._marks: List[Dict] = []       # {offset,int,type,str,count,int,label,str,indent,int}
        self._qdict_dirty: bool = False
        self._qdict_path: Optional[str] = None

        # find state
        self._find_pattern: Optional[bytes] = None
        self._find_next_from: int = 0 # index from which to search next

        # ---------- layout ----------
        outer = QSplitter(Qt.Horizontal, self)

        duo = QWidget(self)
        duo_lyt = QHBoxLayout(duo); duo_lyt.setContentsMargins(0, 0, 0, 0); duo_lyt.setSpacing(0)

        self.tabs = QTabWidget(duo)
        self.text_formatter = make_ro_editor(12)
        self.text_qdict = make_ro_editor(12)
        self.tabs.addTab(self.text_formatter, "Formater")
        self.tabs.addTab(self.text_qdict, "Qdict")
        self.text_qdict.cursorPositionChanged.connect(self._on_qdict_cursor_moved)

        hex_holder = QWidget(duo)
        hex_lyt = QVBoxLayout(hex_holder); hex_lyt.setContentsMargins(0, 0, 0, 0)
        self.text = MonoText(hex_holder)
        self.text._on_resized = self._render
        self.text._custom_copy_handler = self._copy_raw_hex
        self.text.selectionChanged.connect(self._on_selection_changed)
        self.text.installEventFilter(self)
        hex_lyt.addWidget(self.text)

        duo_lyt.addWidget(self.tabs, 1)
        duo_lyt.addWidget(hex_holder, 1)

        right = QWidget(self)
        lyt_right = QVBoxLayout(right); lyt_right.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("Dictionary Controls", right)
        form = QFormLayout(grp); form.setLabelAlignment(Qt.AlignLeft); form.setFormAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.cmb_group = QComboBox(grp)
        self.cmb_group.addItems(["1", "2", "4", "ASCII"])
        self.cmb_group.setCurrentText("1")
        self.cmb_group.currentTextChanged.connect(self.on_group_changed)
        form.addRow(QLabel("Byte Grouping"), self.cmb_group)

        self.cmb_font = QComboBox(grp)
        self.cmb_font.addItems(["10", "12", "14", "16", "18"])
        self.cmb_font.setCurrentText(str(self.text.font().pointSize()))
        self.cmb_font.currentTextChanged.connect(self.on_font_changed)
        form.addRow(QLabel("Font Size"), self.cmb_font)

        self.btn_open = QPushButton("Open .Qdict", right)
        self.btn_open.clicked.connect(self._action_open_qdict)
        self.btn_saveas = QPushButton("Save As .Qdict", right)
        self.btn_saveas.clicked.connect(self._action_saveas_qdict)

        lyt_right.addWidget(grp)
        lyt_right.addStretch(1)
        lyt_right.addWidget(self.btn_open)
        lyt_right.addWidget(self.btn_saveas)

        outer.addWidget(duo)
        outer.addWidget(right)
        outer.setStretchFactor(0, 1)
        outer.setStretchFactor(1, 0)
        self.setCentralWidget(outer)

        QToolTip.setFont(self.text.font())

        # Shortcuts
        for seq in ("Ctrl+B", "Meta+B"):
            QShortcut(QKeySequence(seq), self, activated=self._bookmark_add)
        for seq in ("Ctrl+D", "Meta+D"):
            QShortcut(QKeySequence(seq), self, activated=self._bookmark_delete)
        for seq in ("Ctrl+F", "Meta+F"):
            QShortcut(QKeySequence(seq), self, activated=self._action_find_open)
        for seq in ("Ctrl+G", "Meta+G"):
            QShortcut(QKeySequence(seq), self, activated=self._action_find_next)

        self.status = self.statusBar()
        self._update_status(0, 0)

    # --------------------------- public API ---------------------------
    def set_hex(self, hex_text: str):
        cleaned = re.sub(r"[^0-9A-Fa-f]", "", hex_text or "")
        if len(cleaned) % 2 == 1:
            cleaned = cleaned[:-1]
        try:
            self.data = bytes.fromhex(cleaned) if cleaned else b""
        except ValueError:
            self.data = b""
        self._render()
        self._update_status(0, len(self.data))

    # ---------------------------- events -----------------------------
    def on_group_changed(self, text: str):
        self.group_mode = text
        self._render()
        self._update_status_from_selection()
        self._show_selection_tooltip()

    def on_font_changed(self, text: str):
        try:
            size = int(text)
        except ValueError:
            return
        f = self.text.font(); f.setPointSize(size); self.text.setFont(f); self.text.update_doc_margin()
        for ed in (self.text_formatter, self.text_qdict):
            ef = ed.font(); ef.setPointSize(size); ed.setFont(ef)
            fm = QFontMetricsF(ef); ed.document().setDocumentMargin(max(8.0, 1.5 * fm.horizontalAdvance('0')))
        self._render()
        self._update_status_from_selection()
        QToolTip.setFont(self.text.font())
        self._show_selection_tooltip()

    # ---------------------------- render -----------------------------
    def _bytes_per_line(self) -> int:
        if not self.data: return 1
        fm = QFontMetricsF(self.text.font())
        glyphs = "0123456789ABCDEF" + FIGURE_SPACE
        char_w = max(fm.horizontalAdvance(c) for c in glyphs)
        doc_m = float(self.text.document().documentMargin())
        fudge = max(2.0, char_w * 0.25)
        usable_px = max(1.0, self.text.viewport().width() - 2.0 * doc_m - fudge)
        cols = int(usable_px // char_w)
        if self.group_mode == "ASCII":
            return max(1, cols - 1)
        g = int(self.group_mode)
        token = 2 * g + 1
        groups = max(1, (cols + 1) // token)
        while groups > 1 and (groups * token - 1) > (cols - 1):
            groups -= 1
        return max(1, groups * g)

    def _render(self):
        if self.group_mode == "ASCII":
            text, c2b, b2s = self._build_ascii()
        else:
            g = int(self.group_mode)
            text, c2b, b2s = self._build_hex(g)
        self.text.blockSignals(True); self.text.setPlainText(text); self.text.blockSignals(False)
        self._char2byte, self._byte2span = c2b, b2s
        self._refresh_highlights()

    def _build_hex(self, group: int):
        data = self.data or b""
        bpl = self._bytes_per_line()
        out_chars: List[str] = []; c2b: List[Tuple[int, int]] = []
        b2s: List[Tuple[int, int]] = [(0, 0)] * len(data) if data else []
        pos = 0; idx = 0; n = len(data); i = 0
        while i < n:
            take = min(bpl, n - i); line = data[i:i + take]
            for j, byte in enumerate(line):
                hx = f"{byte:02X}"
                b2s[idx] = (pos, pos + 2)
                out_chars.append(hx[0]); c2b.append((idx, 0)); pos += 1
                out_chars.append(hx[1]); c2b.append((idx, 1)); pos += 1
                idx += 1
                if ((j + 1) % group == 0) and (j + 1 != take):
                    out_chars.append(FIGURE_SPACE); c2b.append((-1, -1)); pos += 1
            i += take
            if i < n:
                out_chars.append('\n'); c2b.append((-1, -1)); pos += 1
        return ("".join(out_chars), c2b, b2s)

    def _build_ascii(self):
        data = self.data or b""
        bpl = self._bytes_per_line()
        out_chars: List[str] = []; c2b: List[Tuple[int, int]] = []
        b2s: List[Tuple[int, int]] = [(0, 0)] * len(data) if data else []
        pos = 0; n = len(data)
        def tochr(b: int) -> str: return chr(b) if 32 <= b <= 126 else '.'
        i = 0
        while i < n:
            take = min(bpl, n - i)
            for j in range(take):
                bi = i + j; ch = tochr(data[bi])
                out_chars.append(ch); c2b.append((bi, 0)); b2s[bi] = (pos, pos + 1); pos += 1
            i += take
            if i < n:
                out_chars.append('\n'); c2b.append((-1, -1)); pos += 1
        return ("".join(out_chars), c2b, b2s)

    # ---------------- selection & tooltip -------------------
    def _on_selection_changed(self):
        if self._snap_guard: return
        self._snap_to_bytes()
        self._update_status_from_selection()
        self._show_selection_tooltip()

    def _find_selected_byte_range(self):
        if not self._char2byte or not self._byte2span:
            return (None, None)
        c = self.text.textCursor(); a, b = c.anchor(), c.position()
        if a == b: return (None, None)
        start, end = (a, b) if a <= b else (b, a)

        s_byte = None
        for i in range(start, end):
            bi, _ = self._char2byte[i] if i < len(self._char2byte) else (-1, -1)
            if bi >= 0: s_byte = bi; break
        if s_byte is None: return (None, None)

        e_byte = None
        for i in range(end - 1, start - 1, -1):
            bi, _ = self._char2byte[i] if i < len(self._char2byte) else (-1, -1)
            if bi >= 0: e_byte = bi; break
        if e_byte is None: return (None, None)
        if s_byte > e_byte: s_byte, e_byte = e_byte, s_byte
        return (s_byte, e_byte)

    def _snap_to_bytes(self):
        s_byte, e_byte = self._find_selected_byte_range()
        if s_byte is None: return
        s_ch = self._byte2span[s_byte][0]; e_ch = self._byte2span[e_byte][1]
        c = self.text.textCursor()
        self._snap_guard = True
        try:
            c.setPosition(s_ch); c.setPosition(e_ch, c.KeepAnchor); self.text.setTextCursor(c)
        finally:
            self._snap_guard = False

    def _selected_bytes(self) -> bytes:
        s_byte, e_byte = self._find_selected_byte_range()
        if s_byte is None: return b""
        return bytes(self.data[s_byte:e_byte + 1])

    def _ascii_str(self, buf: bytes) -> str:
        return "".join(chr(b) if 32 <= b <= 126 else '.' for b in buf)

    def _fmt_float(self, x: float) -> str:
        return f"{x:.6g}"

    def _tooltip_text_for(self, buf: bytes) -> Optional[str]:
        if not buf: return None
        n = len(buf)
        if n == 1:
            return f"u8: {buf[0]}, ASCII: '{self._ascii_str(buf)}'"
        if n == 2:
            return f"u16: {int.from_bytes(buf,'little')}, ASCII: '{self._ascii_str(buf)}'"
        if n == 4:
            return f"float32: {self._fmt_float(struct.unpack('<f', buf)[0])}, ASCII: '{self._ascii_str(buf)}'"
        MAX_SHOW = 64
        u8_seq = [str(b) for b in buf[:MAX_SHOW]] + (["…"] if len(buf) > MAX_SHOW else [])
        u16_seq, f32_seq = [], []
        for i in range(0, n - n % 2, 2):
            if len(u16_seq) >= MAX_SHOW: u16_seq.append("…"); break
            u16_seq.append(str(int.from_bytes(buf[i:i+2], "little")))
        for i in range(0, n - n % 4, 4):
            if len(f32_seq) >= MAX_SHOW: f32_seq.append("…"); break
            f32_seq.append(self._fmt_float(struct.unpack("<f", buf[i:i+4])[0]))
        asc = self._ascii_str(buf)
        parts = [
            "u8: " + ", ".join(u8_seq) if u8_seq else None,
            "u16: " + ", ".join(u16_seq) if u16_seq else None,
            "float32: " + ", ".join(f32_seq) if f32_seq else None,
            "ASCII: '" + asc + "'"
        ]
        return "\n".join(p for p in parts if p)

    def _show_selection_tooltip(self):
        buf = self._selected_bytes(); txt = self._tooltip_text_for(buf)
        if not txt: QToolTip.hideText(); return
        c = self.text.textCursor(); start = min(c.anchor(), c.position())
        c2 = self.text.textCursor(); c2.setPosition(start)
        rect = self.text.cursorRect(c2); base = self.text.viewport().mapToGlobal(rect.topLeft())
        fm = QFontMetricsF(QToolTip.font()); lines = txt.count("\n") + 1
        tip_h = int(lines * fm.height() + 12)
        above_y = base.y() - tip_h - 10
        screen = QGuiApplication.screenAt(base) or QGuiApplication.primaryScreen()
        top_bound = screen.availableGeometry().top()
        pos = base
        if above_y > top_bound:
            pos.setY(above_y)
        else:
            line_h = int(fm.height()); pos.setY(base.y() + line_h + 10)
        QToolTip.showText(pos, txt, self.text)

    # ---------------- keyboard: ←/→ by BYTES (+Shift) ----------------
    def eventFilter(self, obj, ev):
        if obj is self.text and ev.type() == QEvent.KeyPress:
            key = ev.key(); mods = ev.modifiers()
            if key in (Qt.Key_Left, Qt.Key_Right):
                if not self._byte2span: return False
                c = self.text.textCursor()
                anchor_ch = c.anchor(); pos_ch = c.position(); dir_right = (key == Qt.Key_Right)
                if mods & Qt.ShiftModifier:
                    a_byte = self._byte_from_char(anchor_ch, prefer_right=False)
                    p_byte = self._byte_from_char(pos_ch,    prefer_right=dir_right)
                    if a_byte is None and p_byte is None: return True
                    if a_byte is None: a_byte = p_byte
                    if p_byte is None: p_byte = a_byte
                    new_end = max(0, min(p_byte + (1 if dir_right else -1), len(self._byte2span) - 1))
                    s = min(a_byte, new_end); e = max(a_byte, new_end); e_ch = self._byte2span[e][1]
                    self._snap_guard = True
                    try:
                        c.setPosition(self._byte2span[a_byte][0]); c.setPosition(e_ch, c.KeepAnchor); self.text.setTextCursor(c)
                    finally:
                        self._snap_guard = False
                    self._show_selection_tooltip(); return True
                else:
                    cur_byte = self._byte_from_char(pos_ch, prefer_right=dir_right)
                    if cur_byte is None: return True
                    nxt = max(0, min(cur_byte + (1 if dir_right else -1), len(self._byte2span) - 1))
                    nxt_ch = self._byte2span[nxt][0]
                    self._snap_guard = True
                    try:
                        c.clearSelection(); c.setPosition(nxt_ch); self.text.setTextCursor(c)
                    finally:
                        self._snap_guard = False
                    QToolTip.hideText(); return True
        return super().eventFilter(obj, ev)

    def _byte_from_char(self, chpos: int, prefer_right=False) -> Optional[int]:
        if not self._char2byte: return None
        n = len(self._char2byte)
        def scan(start, stop, step):
            i = start
            while 0 <= i < n and (i != stop):
                bi, _ = self._char2byte[i]
                if bi >= 0: return bi
                i += step
            return None
        if 0 <= chpos < n:
            bi, _ = self._char2byte[chpos]
            if bi >= 0: return bi
        return scan(chpos, n, +1) or scan(chpos, -1, -1) if prefer_right else (scan(chpos, -1, -1) or scan(chpos, n, +1))

    # ------------------------ copy: RAW HEX --------------------------
    def _copy_raw_hex(self):
        buf = self._selected_bytes()
        if not buf: return
        hex_text = buf.hex().upper(); cb = QGuiApplication.clipboard()
        mime = QMimeData(); mime.setText(hex_text); mime.setData("application/octet-stream", QByteArray(buf))
        cb.setMimeData(mime, QClipboard.Clipboard)
        if hasattr(cb, "supportsSelection") and cb.supportsSelection():
            mime_sel = QMimeData(); mime_sel.setText(hex_text); mime_sel.setData("application/octet-stream", QByteArray(buf))
            cb.setMimeData(mime_sel, QClipboard.Selection)
        if hasattr(cb, "supportsFindBuffer") and cb.supportsFindBuffer():
            cb.setText(hex_text, QClipboard.FindBuffer)

    # --------------------------- status bar --------------------------
    def _update_status_from_selection(self):
        total = len(self.data)
        if total == 0: self._update_status(0, 0); return
        c = self.text.textCursor()
        if not c.hasSelection(): self._update_status(0, total); return
        sel_len = len(self._selected_bytes()); self._update_status(sel_len, total)

    def _update_status(self, sel_bytes: int, total_bytes: int):
        self.status.showMessage(f"0x{sel_bytes:X} out of 0x{total_bytes:X} bytes")

    # ====================== QDICT: bookmarks =========================
    def _bookmark_add(self):
        s_e = self._find_selected_byte_range()
        if s_e == (None, None): return
        s, e = s_e; length = e - s + 1
        buf = self.data[s:e+1]

        if length == 1:
            default_type = "u8"
        elif length == 2:
            default_type = "u16"
        elif length == 4:
            default_type = "f32"
        else:
            default_type = "ascii" if all(32 <= b <= 126 for b in buf) else "u8"

        dlg = BookmarkDialog(length=length, buf=buf, parent=self, default_type=default_type,
                             default_label="label", default_indent=0)
        if dlg.exec_() != QDialog.Accepted:
            return
        res = dlg.result_values()

        mark = dict(offset=int(s),
                    type=res["type"],
                    count=int(res["count"]),
                    label=str(res["label"]),
                    indent=int(res["indent"]))
        self._marks.append(mark)
        self._qdict_dirty = True
        self._rebuild_qdict_and_formatter(focus_mark=mark)
        self._refresh_highlights()

    def _bookmark_delete(self):
        if not self._marks: return
        if self.tabs.currentWidget() is self.text_qdict:
            line = self.text_qdict.textCursor().blockNumber()
            if 0 <= line < len(self._marks):
                if QMessageBox.question(self, "Delete Bookmark", "Delete selected Bookmark?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
                    del self._marks[line]
                    self._qdict_dirty = True
                    self._rebuild_qdict_and_formatter(focus_index=line)
                    self._refresh_highlights()
                return

    def _rebuild_qdict_and_formatter(self, focus_mark: Optional[dict] = None,
                                     focus_index: Optional[int] = None):
        # Always sort
        self._marks.sort(key=lambda m: (m['offset'],
                                        TYPE_ORDER.get(m['type'], 99),
                                        m['count'],
                                        m.get('label', '')))
        # Qdict text
        lines = []
        for m in self._marks:
            indent = ">" * int(m.get("indent", 0))
            lines.append(f"{m['offset']}|{m['type']}|{m['count']}|{m['label']}|{indent}|")
        self.text_qdict.blockSignals(True)
        self.text_qdict.setPlainText("\n".join(lines))
        self.text_qdict.blockSignals(False)

        # Formater text
        f_lines = []
        for m in self._marks:
            off = m["offset"]; typ = m["type"]; cnt = m["count"]; label = m["label"]
            size = TYPE_SIZES[typ]; end = min(len(self.data), off + size * cnt)
            buf = self.data[off:end]
            if typ == "u8":
                vals = [str(b) for b in buf]
                f_lines.append(f"{label} = " + ", ".join(vals))
            elif typ == "u16":
                vals = []
                for i in range(0, len(buf) - len(buf) % 2, 2):
                    vals.append(str(int.from_bytes(buf[i:i+2], "little")))
                f_lines.append(f"{label} = " + ", ".join(vals))
            elif typ == "f32":
                vals = []
                for i in range(0, len(buf) - len(buf) % 4, 4):
                    vals.append(f"{struct.unpack('<f', buf[i:i+4])[0]:.8f}")
                f_lines.append(f"{label} = " + ", ".join(vals))
            elif typ == "ascii":
                s = "".join(chr(b) if 32 <= b <= 126 else '.' for b in buf)
                f_lines.append(f"{label} = {s}")

        self.text_formatter.setPlainText("\n".join(f_lines))

        # Return cursor to line
        idx = None
        if focus_mark is not None:
            try:
                idx = self._marks.index(focus_mark)
            except ValueError:
                pass
        if idx is None and focus_index is not None and self._marks:
            idx = max(0, min(focus_index, len(self._marks) - 1))
        if idx is not None:
            cur = self.text_qdict.textCursor()
            blk = self.text_qdict.document().findBlockByNumber(idx)
            cur.setPosition(blk.position())
            self.text_qdict.setTextCursor(cur)

    def _refresh_highlights(self):
        """Highlight all bookmarks in HEX (yellow)."""
        sels = []
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(255, 255, 128))

        if not self._byte2span:
            self.text.setExtraSelections([])
            return

        for m in self._marks:
            off = m["offset"]
            size = TYPE_SIZES[m["type"]]
            count = m["count"]
            length = size * count

            s = off
            e = min(len(self._byte2span) - 1, off + length - 1)
            if s < 0 or e < s:
                continue

            s_ch = self._byte2span[s][0]
            e_ch = self._byte2span[e][1]

            sel = QTextEdit.ExtraSelection()
            cur = self.text.textCursor()
            cur.setPosition(s_ch)
            cur.setPosition(e_ch, QTextCursor.KeepAnchor)
            sel.cursor = cur
            sel.format = fmt
            sels.append(sel)

        self.text.setExtraSelections(sels)

    def _on_qdict_cursor_moved(self):
        """Synchronization: cursor in Qdict → selection in HEX."""
        if not self._marks: return
        line = self.text_qdict.textCursor().blockNumber()
        if not (0 <= line < len(self._marks)): return
        m = self._marks[line]
        off = m["offset"]; size = TYPE_SIZES[m["type"]]; length = size * m["count"]
        s = off; e = min(len(self._byte2span) - 1, off + length - 1)
        if not self._byte2span or s < 0 or e < s: return
        s_ch = self._byte2span[s][0]; e_ch = self._byte2span[e][1]
        c = self.text.textCursor(); self._snap_guard = True
        try:
            c.setPosition(s_ch); c.setPosition(e_ch, QTextCursor.KeepAnchor); self.text.setTextCursor(c)
            self.text.ensureCursorVisible()
        finally:
            self._snap_guard = False

    # ---------------------- FIND: Hex bytes ----------------------
    def _action_find_open(self):
        """Open the HEX search dialog. Saves the pattern and immediately searches for the first match."""
        max_bytes = len(self.data)
        dlg = FindHexDialog(max_bytes=max_bytes, initial=self._find_pattern, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        self._find_pattern = dlg.pattern
        self._find_next_from = 0
        self._action_find_next()

    def _select_range_by_bytes(self, start: int, length: int):
        """Select a range of bytes and scroll to it."""
        if not self._byte2span or start < 0 or length <= 0:
            return
        s = start
        e = min(len(self._byte2span) - 1, start + length - 1)
        s_ch = self._byte2span[s][0]
        e_ch = self._byte2span[e][1]
        c = self.text.textCursor()
        self._snap_guard = True
        try:
            c.setPosition(s_ch)
            c.setPosition(e_ch, QTextCursor.KeepAnchor)
            self.text.setTextCursor(c)
            self.text.ensureCursorVisible()
        finally:
            self._snap_guard = False
        self._update_status_from_selection()
        self._show_selection_tooltip()

    def _action_find_next(self):
        """Find the next match of the current pattern (going to the beginning)."""
        if not self._find_pattern:
            # if the pattern has not yet been defined, open the dialog
            self._action_find_open()
            return
        pat = self._find_pattern
        start = max(0, min(self._find_next_from, len(self.data)))
        idx = self.data.find(pat, start)
        if idx == -1 and start != 0:
            # go to the beginning
            idx = self.data.find(pat, 0)
        if idx == -1:
            QMessageBox.information(self, "Find Hex", "No matches found.")
            return
        self._select_range_by_bytes(idx, len(pat))
        # Next search - immediately after the found match
        self._find_next_from = idx + max(1, len(pat))

    # ---------------------- Qdict I/O ----------------------
    def _action_saveas_qdict(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save As .Qdict", "", "Qdict Files (*.qdict *.Qdict);;All Files (*)")
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            for m in self._marks:
                indent = ">" * int(m.get("indent", 0))
                f.write(f"{m['offset']}|{m['type']}|{m['count']}|{m['label']}|{indent}|\n")
        self._qdict_path = path; self._qdict_dirty = False

    def _action_open_qdict(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open .Qdict", "", "Qdict Files (*.qdict *.Qdict);;All Files (*)")
        if not path: return
        marks = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split("|")
                if len(parts) < 5: continue
                try:
                    offset = int(parts[0])
                    btype = parts[1].strip().lower()
                    count = int(parts[2])
                    label = parts[3]
                    indent = parts[4].count(">")
                    if btype not in ALLOWED_TYPES: continue
                    marks.append(dict(offset=offset, type=btype, count=count, label=label, indent=indent))
                except Exception:
                    continue
        self._marks = marks
        self._qdict_path = path; self._qdict_dirty = False
        self._rebuild_qdict_and_formatter()
        self._refresh_highlights()

    # ----------------------- close event -------------------
    def closeEvent(self, e):
        if self._marks and self._qdict_dirty:
            btn = QMessageBox.question(
                self, "Save Qdict?",
                "Save Qdict before exiting?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if btn == QMessageBox.Yes:
                self._action_saveas_qdict()
                if self._qdict_dirty and not self._qdict_path:
                    e.ignore(); return
            elif btn == QMessageBox.Cancel:
                e.ignore(); return
        super().closeEvent(e)

# ------------------------------ Runner -------------------------------
_LIVE_WINDOWS = []

def run(parent=None):
    app = QApplication.instance(); created = False
    if app is None:
        app = QApplication(sys.argv[:1]); created = True

    w = HexDictionaryViewer()
    if parent is not None:
        w.setParent(parent, Qt.Window)

    _LIVE_WINDOWS.append(w)
    w.setAttribute(Qt.WA_DeleteOnClose, True)

    title = globals().get('QTISelectedName', None)
    if title: w.setWindowTitle(str(title))
    src = globals().get('QTISelectedHex', '')
    w.set_hex(src)

    w.resize(1200, 720); w.show(); w.raise_(); w.activateWindow()

    if created:
        app.exec_()
    return w

if __name__ == "__main__":
    if not QTISelectedHex:
        QTISelectedName = "Demo"
        QTISelectedHex = (
            "00 00 80 3F 00 00 61 44 00 00 80 3F 00 00 48 43 00 "
            "00 40 41 00 00 80 42 00 00 00 00 00 00 80 40 00 C0 "
            "7F 44 00 00 E0 40 00 00 00 00 00 00 80 40 00 00 00 "
            "00 00 00 00 42 00 00 00 42 00 00 70 42 00 00 C0 41 "
            "00 00 00 41 00 00 00 00 00 00 00 00 00 00 68 43 00 "
            "00 20 41"
        )
    run()
