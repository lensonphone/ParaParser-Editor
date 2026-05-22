# Test dictionary for checking Export/Import binding from the application.
# Shows all input variables in the dialog and, if AllowExportData == 1
# and status == "Import", returns binary data of the required length.

from typing import Optional
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QPlainTextEdit, QHBoxLayout, QPushButton, QLabel
)
from PyQt5.QtCore import Qt

# ====== PUBLIC GLOBALS (filled by the application) ===========================
QTIDicStatus: str = ""                   # "Export" or "Import"
QTISelectedDicFilePath: str = ""         # path to *.Qdict (if any)
QTISelectedID: str = ""                  # "0x.." (pretty)
QTISelectedIDRaw: str = ""               # raw ID as in table data
QTISelectedName: str = ""                # module name
QTISelectedHex: str = ""                 # HEX string (no spaces)
QTISelectedFilePath: str = ""            # path to bin
QTISelectedOffset: int = 0               # module offset
QTISelectedLength: int = 0               # module length
QTISelectedVersion: str = ""             # parser version
QTISelectedBuffer: bytes = b""           # raw bytes of the module (if passed)



# ====== CONFIGURING MODULE BEHAVIOR ===========================================
# If 1 and status = "Import", the module will return binary data (bytes).
# If 0 - will not return (None).

AllowExportData: int = 1

# Display name (optional)
TRIKSMODULENAME = "_QTIDictionary"


# =================================================================================
# INTERNAL HELPERS
# ===============================================================================

def _first_nonempty_buffer() -> bytes:
    """Return the input buffer preferably from QTISelectedBuffer,
    otherwise from QTIDicBin, otherwise parse QTISelectedHex, otherwise b''."""
    if isinstance(globals().get("QTISelectedBuffer"), (bytes, bytearray)) and QTISelectedBuffer:
        return bytes(QTISelectedBuffer)
    if isinstance(globals().get("QTIDicBin"), (bytes, bytearray)) and QTIDicBin:
        return bytes(QTIDicBin)
    if isinstance(globals().get("QTISelectedHex"), str) and QTISelectedHex:
        s = QTISelectedHex.strip().replace(" ", "")
        try:
            return bytes.fromhex(s)
        except Exception:
            return b""
    return b""


def _ensure_len(buf: bytes, need_len: int) -> bytes:
    """We adjust the length: if it is longer, we cut it off, if it is shorter, we add 0x00."""
    if need_len is None or need_len <= 0:
        return buf
    if len(buf) == need_len:
        return buf
    if len(buf) > need_len:
        return buf[:need_len]
    return buf + b"\x00" * (need_len - len(buf))


def _vars_dump_text() -> str:
    """We generate text with all available variables for display in the dialog."""
    def safe(v):
        try:
            return str(v)
        except Exception:
            return "<unrepr>"

    # show the first N bytes as hex so as not to spam the window
    def hex_preview(b: bytes, n: int = 64) -> str:
        if not b:
            return "(empty)"
        chunk = b[:n]
        return chunk.hex(" ").upper() + (" ..." if len(b) > n else "")

    src_buf = _first_nonempty_buffer()
    lines = [
        f"TRIKSMODULENAME     = {TRIKSMODULENAME}",
        f"AllowExportData     = {AllowExportData}",
        "",
        f"QTIDicStatus        = {safe(QTIDicStatus)}",
        f"QTISelectedDicFilePath = {safe(QTISelectedDicFilePath)}",
        f"QTISelectedID       = {safe(QTISelectedID)}",
        f"QTISelectedIDRaw    = {safe(QTISelectedIDRaw)}",
        f"QTISelectedName     = {safe(QTISelectedName)}",
        f"QTISelectedFilePath = {safe(QTISelectedFilePath)}",
        f"QTISelectedOffset   = {safe(QTISelectedOffset)}",
        f"QTISelectedLength   = {safe(QTISelectedLength)}",
        f"QTISelectedVersion  = {safe(QTISelectedVersion)}",
        f"QTISelectedHex(len) = {len(QTISelectedHex) if isinstance(QTISelectedHex, str) else 'N/A'}",
        f"QTISelectedBuffer   = {len(QTISelectedBuffer) if isinstance(QTISelectedBuffer, (bytes, bytearray)) else 0} bytes",
        "",
        f"Chosen input buffer = {_src_label()}",
        f"Input length        = {len(src_buf)}",
        f"Preview (<=64B)     = {hex_preview(src_buf)}",
        "",
        f"Would return bytes? = { 'YES' if (QTIDicStatus=='Import' and AllowExportData==1) else 'NO' }",
        f"Target length       = {QTISelectedLength}",
    ]
    return "\n".join(lines)


def _src_label() -> str:
    if QTISelectedBuffer:
        return "QTISelectedBuffer"
    if QTIDicBin:
        return "QTIDicBin"
    if QTISelectedHex:
        return "QTISelectedHex"
    return "(empty)"


class _VarsDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Qdict test — vars snapshot")
        self.resize(760, 520)

        lay = QVBoxLayout(self)
        info = QLabel("Below are all variables as seen by _QTIDictionary.py")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.view = QPlainTextEdit(self)
        self.view.setReadOnly(True)
        self.view.setPlainText(text)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.view.setMinimumHeight(420)
        lay.addWidget(self.view)

        btns = QHBoxLayout()
        self.btnOk = QPushButton("OK")
        self.btnOk.clicked.connect(self.accept)
        btns.addStretch(1)
        btns.addWidget(self.btnOk)
        lay.addLayout(btns)


# ===============================================================================
# PUBLIC ENTRY POINTS
# ==============================================================================

def run(parent=None) -> Optional[bytes]:
    """
    Main entry point:
    - Always shows the window with variables.
    - If QTIDicStatus == 'Import' and AllowExportData == 1,
    returns binary data of length QTISelectedLength.
    - Otherwise returns None.
    """
    dlg = _VarsDialog(_vars_dump_text(), parent=parent)
    dlg.exec_()

    if QTIDicStatus == "Import" and AllowExportData == 1:
        buf = _first_nonempty_buffer()
        # We'll adjust the length to the expected one - so that the main program doesn't complain.
        buf = _ensure_len(buf, int(QTISelectedLength) if QTISelectedLength else 0)
        return buf

    return None


