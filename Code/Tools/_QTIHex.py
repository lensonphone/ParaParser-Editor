import sys, struct
from typing import List, Optional, Union
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QTextEdit, QSizePolicy, QWidget
)

AllowDebug = 0 

def dbg(msg: str):
    """Single logging point: print on DEBUG, buffer on LOGTOTXT."""
    if AllowDebug:
        print(msg)


QTIDicBin = "00001F430000274300002F430000364300003B4300003F43000041430000474300004D430000514300005843000059430000634300006C430000004300000043000000430000004300000043000000430000004300000043"

class HexViewerDialog(QDialog):
    def __init__(self, QTIDicBin: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hex Viewer")
        self.resize(400, 300)

        self.data = self._hex_to_bytes(QTIDicBin)
        dbg(f"QTIDicBin = {QTIDicBin}")
        self.group_bytes = 1
        self.decode_mode = False
        self.preview_on = False # two-state Preview
        self.ascii_mode = False # new Ascii mode
        self.font_pt = 14

        # --- top panel ---
        toolbar = QWidget(self)
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(40)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 6, 8, 6)
        tl.setSpacing(10)

        tl.addWidget(QLabel("Bytegrouping:", toolbar))
        self.combo_group = QComboBox(toolbar)
        # added Ascii item
        self.combo_group.addItems(["1", "2", "4", "Ascii"])
        self.combo_group.setCurrentText("1")
        self.combo_group.currentIndexChanged.connect(self._on_group_changed)
        tl.addWidget(self.combo_group)

        self.chk_decode = QCheckBox("Decode Data", toolbar)
        self.chk_decode.toggled.connect(self._on_decode_toggled)
        tl.addWidget(self.chk_decode)

        self.chk_preview = QCheckBox("Preview Data", toolbar)
        self.chk_preview.toggled.connect(self._on_preview_toggled)
        self.chk_preview.setEnabled(False) # only if group=4
        tl.addWidget(self.chk_preview)

        tl.addStretch(1)

        tl.addWidget(QLabel("Font:", toolbar))
        self.combo_font = QComboBox(toolbar)
        self.combo_font.addItems(["10", "12", "14", "16", "18"])
        self.combo_font.setCurrentText("12")
        self.combo_font.currentIndexChanged.connect(self._on_font_changed)
        tl.addWidget(self.combo_font)

        toolbar.setStyleSheet("#toolbar { background: #f4f4f4; border-bottom: 1px solid #ccc; }")

        # --- preview field ---
        self.view = QTextEdit(self)
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QTextEdit.NoWrap)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(self.font_pt)
        self.view.setFont(mono)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(toolbar)
        root.addWidget(self.view, 1)
        self.setLayout(root)

        self._refresh()

    # ---------- handlers ----------
    def _on_group_changed(self):
        text = self.combo_group.currentText()
        # ASCII mode: disable Decode/Preview and mark ascii_mode
        if text.lower() == "ascii":
            self.ascii_mode = True
            self.chk_decode.setEnabled(False)
            self.chk_decode.setChecked(False)
            self.decode_mode = False

            self.chk_preview.setEnabled(False)
            self.chk_preview.setChecked(False)
            self.preview_on = False
        else:
            self.ascii_mode = False
            self.group_bytes = int(text)
            self.chk_decode.setEnabled(True)
            # Preview is only available if group=4
            self.chk_preview.setEnabled(self.group_bytes == 4)
            if self.group_bytes != 4 and self.preview_on:
                self.preview_on = False
                self.chk_preview.setChecked(False)
        self._refresh()

    def _on_decode_toggled(self, checked: bool):
        # ignore in ASCII mode
        if self.ascii_mode:
            self.chk_decode.setChecked(False)
            self.decode_mode = False
            return
        self.decode_mode = checked
        if checked and self.preview_on:
            self.preview_on = False
            self.chk_preview.setChecked(False)
        self._refresh()

    def _on_preview_toggled(self, checked: bool):
        # ignore in ASCII mode
        if self.ascii_mode:
            self.chk_preview.setChecked(False)
            self.preview_on = False
            return
        self.preview_on = checked
        if checked and self.decode_mode:
            self.decode_mode = False
            self.chk_decode.setChecked(False)
        self._refresh()

    def _on_font_changed(self):
        self.font_pt = int(self.combo_font.currentText())
        mono = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        mono.setPointSize(self.font_pt)
        self.view.setFont(mono)
        self._refresh()

    # ---------- render ----------
    def _refresh(self):
        self.view.setHtml(self._build_html())

    def _build_html(self) -> str:
        css = (
            "pre {font-family: 'Courier New', monospace; "
            "font-size: " + str(self.font_pt) + "pt; line-height: 1.25; margin: 6px}"
        )
        if self.ascii_mode:
            body = self._render_ascii()
        else:
            body = self._render_decoded() if self.decode_mode else self._render_hex_with_optional_preview()
        return "<html><head><style>" + css + "</style></head><body><pre>" + body + "</pre></body></html>"

    # ---------- formats ----------
    def _render_hex_with_optional_preview(self) -> str:
        # Separator between groups — N spaces (N = group_bytes)
        sep = " " * self.group_bytes
        groups_per_line = max(1, 16 // self.group_bytes)
        out_lines: List[str] = []
        n = len(self.data); i = 0
        while i < n:
            row: List[str] = []
            for _ in range(groups_per_line):
                if i >= n: break
                chunk = self.data[i:i+self.group_bytes]
                # NO spaces within a group, only between groups
                if self.group_bytes == 1:
                    group_hex = f"{chunk[0]:02X}"
                else:
                    group_hex = "".join(f"{b:02X}" for b in chunk)

                style = ""
                # Gradient highlighting only works with group=4 and preview_on
                if self.group_bytes == 4 and self.preview_on and len(chunk) == 4:
                    val = struct.unpack("<f", bytes(chunk))[0]
                    gray = self._map_to_gray(val)
                    if gray is not None:
                        # text: white on dark, black on light
                        txt = "#fff" if gray < 96 else "#000"
                        style = "background: rgb({0},{0},{0}); color:{1};".format(gray, txt)

                row.append("<span style='" + style + "'>" + group_hex + "</span>" if style else group_hex)
                i += self.group_bytes
            out_lines.append(sep.join(row))
        return "\n".join(out_lines)

    def _render_decoded(self) -> str:
        sep = " " * self.group_bytes
        groups_per_line = max(1, 16 // self.group_bytes)
        out_lines: List[str] = []
        n = len(self.data); i = 0
        while i < n:
            row: List[str] = []
            for _ in range(groups_per_line):
                if i >= n: break
                chunk = self.data[i:i+self.group_bytes]
                if len(chunk) < self.group_bytes:
                    s = "".join(f"{b:02X}" for b in chunk) # incomplete group
                else:
                    if self.group_bytes == 1:
                        s = f"{chunk[0]:d}"
                    elif self.group_bytes == 2:
                        s = f"{struct.unpack('<H', bytes(chunk))[0]:d}"
                    else:  # 4
                        v = struct.unpack("<f", bytes(chunk))[0]
                        s = f"{v:.4f}".rstrip("0").rstrip(".")
                row.append(s); i += self.group_bytes
            out_lines.append(sep.join(row))
        return "\n".join(out_lines)

    def _render_ascii(self) -> str:
        """
        Show only ASCII: printable 0x20..0x7E and line feeds (0x0A).
        Remaining bytes are ignored.
        """
        chars: List[str] = []
        for b in self.data:
            if b == 0x0A: # LF -> newline
                chars.append("\n")
            elif 0x20 <= b <= 0x7E: # visible ASCII
                chars.append(chr(b))
            else:
                # ignore non-printable/non-ASCII
                pass
        return "".join(chars)

    # ---------- utils ----------
    @staticmethod
    def _hex_to_bytes(h: str) -> bytes:
        filtered = "".join(ch for ch in h if ch.upper() in "0123456789ABCDEF")
        if len(filtered) % 2: filtered = filtered[:-1]
        return bytes.fromhex(filtered)

    @staticmethod
    def _clamp(x: float, a: float, b: float) -> float:
        return a if x < a else (b if x > b else x)

    def _map_to_gray(self, val: float) -> Optional[int]:
        """
        Linear mapping to grayscale:
        0.5..10  -> 0..255
        20..4095 -> 0..255
        Returns an integer 0..255 or None (if outside both ranges).
        """
        if 0.5 <= val <= 10.0:
            t = (val - 0.5) / (10.0 - 0.5)
            gray = int(round(self._clamp(t, 0.0, 1.0) * 255))
            return gray
        if 20.0 <= val <= 4095.0:
            t = (val - 20.0) / (4095.0 - 20.0)
            gray = int(round(self._clamp(t, 0.0, 1.0) * 255))
            return gray
        return None

# --- demo ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    HexViewerDialog(QTIDicBin).exec_()
