import os, sys, struct
from typing import List, Optional, Union
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase, QKeySequence, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSizePolicy, QWidget, QMessageBox, QPushButton, QPlainTextEdit,
    QShortcut
)

# ── Global variables set by an external program (_QTIHexEdit) ──
_QTIHexEditFilePath       = "/Volumes/PROJ SCRATCH/___Codding_CameraTools/QTIParParserUI_v10/com.qti.tuned.sharp_imx506.bin"
_QTIHexEditLibraryOffset = "0x4B706A" # can be int or string in hex/decimal
_QTIHexEditLibraryLength = "0x3E0" # can be int or string in hex/decimal


# ========= Overwrite editor based on QPlainTextEdit ==========
class HexPlainEdit(QPlainTextEdit):
    """
    Full overwrite mode by nibbles:
    • Accepts only HEX (0–9, A–F), letters → UPPERCASE
    • Space/Tab/Enter are ignored (do not change the markup)
    • Print/Paste Rewrites nibbles from left to right
    • Backspace/Delete don't delete, but set '0' in the corresponding nibble
    • Buffer length never changes
    • Undo/Redo supported (replacements are made via QTextCursor)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setOverwriteMode(True)
        self.setCursorWidth(2)
        self.setUndoRedoEnabled(True)

    # ---- auxiliary ----
    @staticmethod
    def _is_hex_char(ch: str) -> bool:
        return ch.upper() in "0123456789ABCDEF"

    def _doc_text(self) -> str:
        return self.toPlainText()

    def _hex_positions(self) -> list:
        s = self._doc_text()
        return [i for i, ch in enumerate(s) if self._is_hex_char(ch)]

    def _cursor_doc_pos(self) -> int:
        return self.textCursor().position()

    def _set_cursor_doc_pos(self, pos: int):
        cur = self.textCursor()
        pos = max(0, min(pos, len(self._doc_text())))
        cur.setPosition(pos)
        self.setTextCursor(cur)

    def nibble_index_at_cursor(self) -> int:
        """How many HEX characters are to the left of the cursor."""
        s = self._doc_text()
        pos = self._cursor_doc_pos()
        return sum(1 for i in range(pos) if self._is_hex_char(s[i]))

    def goto_nibble(self, nib_idx: int):
        positions = self._hex_positions()
        if not positions:
            return
        if nib_idx < 0:
            nib_idx = 0
        if nib_idx >= len(positions):
            nib_idx = len(positions) - 1
        self._set_cursor_doc_pos(positions[nib_idx])

    def _replace_char_at(self, pos: int, ch: str):
        """Replace the character at position `pos` with `ch` via QTextCursor (Undo-friendly)."""
        cur = self.textCursor()
        cur.setPosition(pos)
        cur.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 1)
        cur.insertText(ch)
        self.setTextCursor(cur)

    def _overwrite_one_nibble(self, ch_upper: str):
        if not self._is_hex_char(ch_upper):
            return
        s = self._doc_text()
        pos = self._cursor_doc_pos()
        positions = self._hex_positions()
        # Find the first editable character to the right (including the current position)
        next_pos = None
        for p in positions:
            if p >= pos:
                next_pos = p
                break
        if next_pos is None:
            return
        self._replace_char_at(next_pos, ch_upper)
        # Cursor -> next nibble
        # The positions list is up-to-date in length (has not changed), the index can be recalculated:
        positions = self._hex_positions()
        idx = positions.index(next_pos) + 1
        self.goto_nibble(idx)

    def _backspace_overwrite(self):
        positions = self._hex_positions()
        if not positions:
            return
        pos = self._cursor_doc_pos()
        prev_pos = None
        for p in reversed(positions):
            if p < pos:
                prev_pos = p
                break
        if prev_pos is None:
            return
        self._replace_char_at(prev_pos, "0")
        self._set_cursor_doc_pos(prev_pos)

    def _delete_overwrite(self):
        positions = self._hex_positions()
        if not positions:
            return
        pos = self._cursor_doc_pos()
        target = None
        for p in positions:
            if p >= pos:
                target = p
                break
        if target is None:
            return
        self._replace_char_at(target, "0")
        positions = self._hex_positions()
        idx = positions.index(target) + 1
        self.goto_nibble(idx)

    # ---- input/insert ----
    def keyPressEvent(self, e):
        key = e.key()
        text = e.text().upper() if e.text() else ""

        # system Shortcuts and navigation — leave it to the base (Undo/Redo, etc.)
        if (e.modifiers() & (Qt.ControlModifier | Qt.MetaModifier)) or \
           key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down,
                   Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown):
            return super().keyPressEvent(e)

        if key == Qt.Key_Backspace:
            self._backspace_overwrite()
            return
        if key == Qt.Key_Delete:
            self._delete_overwrite()
            return

        # Ignore spaces/line breaks (delimiters are fixed)
        if text in (" ", "\t", "\r", "\n"):
            return

        if text and text[0] in "0123456789ABCDEF":
            self._overwrite_one_nibble(text[0])
            return

        # Ignore other items
        return

    def insertFromMimeData(self, source):
        t = source.text() if source and source.hasText() else ""
        if not t:
            return
        hex_only = "".join(ch for ch in t.upper() if ch in "0123456789ABCDEF")
        if not hex_only:
            return
        # Group into one undo step
        cur = self.textCursor()
        cur.beginEditBlock()
        self.setTextCursor(cur)
        for ch in hex_only:
            self._overwrite_one_nibble(ch)
        cur = self.textCursor()
        cur.endEditBlock()
        self.setTextCursor(cur)


# ====================== HexEditorDialog ======================
class HexEditorDialog(QDialog):
    def __init__(self, parent=None,
                 file_path: Optional[str] = None,
                 offset: Optional[Union[int, str]] = None,
                 length: Optional[Union[int, str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Hex Editor")
        self.resize(920, 600)

        # ── Load data from file ──
        self.file_path, self.off, self.expected_len, self.data = self._load_data(
            file_path, offset, length
        )

        # ── View states ──
        self.group_bytes    = 1           # 1 / 2 / 4
        self.ascii_mode = False # ASCII output mode
        self.decode_mode = False # Show numbers instead of hex
        self.font_pt        = 14
        self.bytes_per_line = 16 # Width (16/24/32/48/64)

        # --- Top panel ---
        toolbar = QWidget(self)
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(40)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 6, 8, 6)
        tl.setSpacing(10)

        tl.addWidget(QLabel("Bytegrouping:", toolbar))
        self.combo_group = QComboBox(toolbar)
        self.combo_group.addItems(["1", "2", "4", "Ascii"])
        self.combo_group.setCurrentText("1")
        self.combo_group.currentIndexChanged.connect(self._on_group_changed)
        tl.addWidget(self.combo_group)

        self.chk_decode = QCheckBox("Decode Data", toolbar)
        self.chk_decode.toggled.connect(self._on_decode_toggled)
        tl.addWidget(self.chk_decode)

        tl.addStretch(1)

        tl.addWidget(QLabel("Width:", toolbar))
        self.combo_width = QComboBox(toolbar)
        self.combo_width.addItems(["16", "24", "32", "48", "64"])
        self.combo_width.setCurrentText(str(self.bytes_per_line))
        self.combo_width.currentIndexChanged.connect(self._on_width_changed)
        tl.addWidget(self.combo_width)

        tl.addWidget(QLabel("Font:", toolbar))
        self.combo_font = QComboBox(toolbar)
        self.combo_font.addItems(["10", "12", "14", "16", "18"])
        self.combo_font.setCurrentText(str(self.font_pt))
        self.combo_font.currentIndexChanged.connect(self._on_font_changed)
        tl.addWidget(self.combo_font)

        # Buttons Undo/Redo
        self.btn_undo = QPushButton("Undo", toolbar)
        self.btn_redo = QPushButton("Redo", toolbar)
        tl.addWidget(self.btn_undo)
        tl.addWidget(self.btn_redo)

        # Save button — strictly override
        self.btn_save = QPushButton("Save buffer to file", toolbar)
        tl.addWidget(self.btn_save)

        toolbar.setStyleSheet("#toolbar { background: #f4f4f4; border-bottom: 1px solid #ccc; }")

        # --- Edit field (overwrite) ---
        self.view = HexPlainEdit(self)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(self.font_pt)
        self.view.setFont(mono)

        # Button and shortcut bindings
        self.btn_undo.clicked.connect(self.view.undo)
        self.btn_redo.clicked.connect(self.view.redo)
        self.btn_save.clicked.connect(self._on_save_to_file)

        # Hotkeys Ctrl+Z / Ctrl+Shift+Z (in addition to system keys)
        QShortcut(QKeySequence("Ctrl+Z"),        self, self.view.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"),  self, self.view.redo)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(toolbar)
        root.addWidget(self.view, 1)
        self.setLayout(root)

        self._refresh()

    # ========================= Loading data =========================
    def _load_data(self,
                   file_path: Optional[str],
                   offset: Optional[Union[int, str]],
                   length: Optional[Union[int, str]]):
        file_path = file_path if file_path not in (None, "") else _QTIHexEditFilePath
        offset    = offset    if offset    not in (None, "") else _QTIHexEditLibraryOffset
        length    = length    if length    not in (None, "") else _QTIHexEditLibraryLength

        off = self._parse_int(offset)
        ln  = self._parse_int(length)

        if not file_path or off is None or ln is None or off < 0 or ln <= 0:
            QMessageBox.critical(self, "Hex Editor", "Invalid file path / offset / length.")
            return file_path or "", off or 0, 0, b""

        if not os.path.isfile(file_path):
            QMessageBox.critical(self, "Hex Editor", f"File not found:\n{file_path}")
            return file_path, off, 0, b""

        try:
            fsize = os.path.getsize(file_path)
            if off > fsize:
                QMessageBox.critical(self, "Hex Editor", "Offset is beyond file end.")
                return file_path, off, 0, b""
            ln_eff = min(ln, max(0, fsize - off))
            if ln_eff != ln:
                QMessageBox.warning(self, "Hex Editor",
                                    f"Requested length goes beyond EOF.\nClipped to {ln_eff} bytes.")

            with open(file_path, "rb") as f:
                f.seek(off)
                data = f.read(ln_eff)
            return file_path, off, ln_eff, data

        except Exception as e:
            QMessageBox.critical(self, "Hex Editor", f"Read error:\n{e}")
            return file_path, off, 0, b""

    @staticmethod
    def _parse_int(v: Optional[Union[int, str]]) -> Optional[int]:
        if v is None:
            return None
        if isinstance(v, int):
            return v
        s = str(v).strip()
        try:
            return int(s, 0)
        except Exception:
            try:
                return int(s, 16)
            except Exception:
                return None

    # ====================== handlers ======================
    def _on_group_changed(self):
        text = self.combo_group.currentText()
        if text.lower() == "ascii":
            self.ascii_mode = True
            self.decode_mode = False
            self.chk_decode.setChecked(False)
        else:
            self.ascii_mode = False
            self.group_bytes = int(text)
        self._refresh()

    def _on_decode_toggled(self, checked: bool):
        if self.ascii_mode:
            self.chk_decode.setChecked(False)
            self.decode_mode = False
            return
        self.decode_mode = checked
        self._refresh()

    def _on_font_changed(self):
        self.font_pt = int(self.combo_font.currentText())
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(self.font_pt)
        self.view.setFont(mono)
        self._refresh()

    def _on_width_changed(self):
        self.bytes_per_line = int(self.combo_width.currentText())
        self._refresh()

    # == ... nibble
    def _hex_edit_mode(self) -> bool:
        return (not self.ascii_mode) and (not self.decode_mode)

    def _update_save_enabled(self):
        ok = self._hex_edit_mode() and self.expected_len > 0 and bool(self.file_path)
        self.btn_save.setEnabled(ok)
        # You can only edit in HEX mode.
        self.view.setReadOnly(not self._hex_edit_mode())

    def _on_save_to_file(self):
        if not self._hex_edit_mode():
            QMessageBox.information(self, "Hex Editor",
                "Editing is allowed only in HEX mode (group 1/2/4, no Decode, no ASCII).")
            return
        if self.expected_len <= 0 or not self.file_path:
            QMessageBox.critical(self, "Hex Editor", "Nothing to save: empty buffer or invalid file.")
            return

        text = self.view.toPlainText()
        cleaned = "".join(ch for ch in text if ch.upper() in "0123456789ABCDEF")
        need_hex_chars = self.expected_len * 2
        if len(cleaned) != need_hex_chars:
            QMessageBox.critical(self, "Save error",
                f"Buffer length mismatch.\nExpected {need_hex_chars} hex chars "
                f"({self.expected_len} bytes), got {len(cleaned)}.")
            return
        try:
            new_bytes = bytes.fromhex(cleaned)
        except Exception as e:
            QMessageBox.critical(self, "Save error", f"Invalid HEX data:\n{e}")
            return

        try:
            with open(self.file_path, "r+b") as f:
                f.seek(self.off)
                f.write(new_bytes)
            self.data = new_bytes
            QMessageBox.information(self, "Saved",
                f"Wrote {self.expected_len} bytes @ offset 0x{self.off:X}.")
        except Exception as e:
            QMessageBox.critical(self, "Save error", f"Write failed:\n{e}")

    # ====================== render ======================
    def _refresh(self):
        # save the nibble cursor position
        nib_idx = self.view.nibble_index_at_cursor()

        if self._hex_edit_mode():
            self.view.setPlainText(self._render_hex_plain())
        elif self.ascii_mode:
            self.view.setPlainText(self._render_ascii())
        else:
            self.view.setPlainText(self._render_decoded_or_hex_readonly())

        # return the cursor to the previous nibble
        self.view.goto_nibble(nib_idx)
        self._update_save_enabled()

    def _render_hex_plain(self) -> str:
        gb = self.group_bytes
        sep = " " * gb
        groups_per_line = max(1, self.bytes_per_line // gb)
        out_lines: List[str] = []
        n = len(self.data); i = 0
        while i < n:
            row: List[str] = []
            for _ in range(groups_per_line):
                if i >= n: break
                chunk = self.data[i:i+gb]
                row.append("".join(f"{b:02X}" for b in chunk))
                i += gb
            out_lines.append(sep.join(row))
        return "\n".join(out_lines)

    def _render_decoded_or_hex_readonly(self) -> str:
        if self.decode_mode:
            return self._render_decoded()
        gb = self.group_bytes
        sep = " " * gb
        groups_per_line = max(1, self.bytes_per_line // gb)
        out_lines: List[str] = []
        n = len(self.data); i = 0
        while i < n:
            row: List[str] = []
            for _ in range(groups_per_line):
                if i >= n: break
                chunk = self.data[i:i+gb]
                row.append("".join(f"{b:02X}" for b in chunk))
                i += gb
            out_lines.append(sep.join(row))
        return "\n".join(out_lines)

    def _render_decoded(self) -> str:
        gb = self.group_bytes
        sep = " " * gb
        groups_per_line = max(1, self.bytes_per_line // gb)
        out_lines: List[str] = []
        n = len(self.data); i = 0
        while i < n:
            row: List[str] = []
            for _ in range(groups_per_line):
                if i >= n: break
                chunk = self.data[i:i+gb]
                if len(chunk) < gb:
                    s = "".join(f"{b:02X}" for b in chunk)
                else:
                    if gb == 1:
                        s = f"{chunk[0]:d}"
                    elif gb == 2:
                        s = f"{struct.unpack('<H', bytes(chunk))[0]:d}"
                    else:  # 4
                        try:
                            v = struct.unpack("<f", bytes(chunk))[0]
                            s = f"{v:.4f}".rstrip("0").rstrip(".")
                        except Exception:
                            s = "NaN"
                row.append(s); i += gb
            out_lines.append(sep.join(row))
        return "\n".join(out_lines)

    def _render_ascii(self) -> str:
        chars: List[str] = []
        for b in self.data:
            if b == 0x0A:
                chars.append("\n")
            elif 0x20 <= b <= 0x7E:
                chars.append(chr(b))
        return "".join(chars)


# --- demo ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dlg = HexEditorDialog()
    dlg.exec_()
