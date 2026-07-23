# support.py
import sys
import base64
import webbrowser
import subprocess
import platform

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QDialog, QHBoxLayout, QLineEdit, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
import qrcode

# ──────────────────────────────────────────────────────────────────────────────
A93FEE5AAA3F38F8 = "v23n45p2m34cpm!!2mp834mp5mp347v5mp3452p3487n52cpv348m5"

def decrypt_link(enc_b64, key=A93FEE5AAA3F38F8):
    try:
        raw = base64.b64decode(enc_b64)
        out_bytes = bytes((b ^ ord(key[i % len(key)])) for i, b in enumerate(raw))
        try:
            s = out_bytes.decode('utf-8')
        except UnicodeDecodeError:
            s = out_bytes.decode('latin-1', errors='ignore')
        return s.strip().strip('\x00')
    except Exception:
        return None



def open_url_crossplatform(url: str):
    if not url:
        return
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", url], check=True)
        elif system == "Windows":
            subprocess.run(f'start {url}', shell=True, check=True)
        else:
            webbrowser.open(url)
    except Exception as e:
        print(f"[ERROR] open_url_crossplatform: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Local QR generation (no internet). Requires: pip install qrcode pillow
def qr_qpixmap(data: str, size: int = 320) -> QPixmap:
    if not data:
        return QPixmap()
    try:

        # матрица True/False
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=1,
            border=1,
        )
        qr.add_data(str(data))
        qr.make(fit=True)
        m = qr.get_matrix()
        h = len(m)
        w = len(m[0]) if h else 0
        if not w or not h:
            return QPixmap()

        # Рисуем RGB32 и затем масштабируем (без сглаживания)
        img = QImage(w, h, QImage.Format_RGB32)
        white = 0xFFFFFFFF
        black = 0xFF000000
        for y, row in enumerate(m):
            for x, v in enumerate(row):
                img.setPixel(x, y, black if v else white)

        img = img.scaled(size, size, Qt.KeepAspectRatio, Qt.FastTransformation)
        return QPixmap.fromImage(img)
    except Exception as e:
        print(f"[ERROR] qr_qpixmap: {e}")
        return QPixmap()

class QRDialog(QDialog):
    def __init__(self, data: str, title: str = "QR Code", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(360, 360)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        pix = qr_qpixmap(data, 320)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)
        if pix.isNull():
            lbl.setText("QR generation failed.\nCheck the link/address.")
        else:
            lbl.setPixmap(pix)
        v.addWidget(lbl)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        v.addWidget(close_btn, alignment=Qt.AlignCenter)


def show_qr_dialog(data: str, title: str):
    QRDialog(data, title).exec_()


# ──────────────────────────────────────────────────────────────────────────────
class SupportWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Support the Project")
        self.setFixedSize(680, 240)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Help Us Grow!")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("If you enjoyed our beta release, support us on one of the platforms and help shape the future of mobile cinematography. Your donation fuels a new vision and powerful tools that expand your creative freedom behind the lens:")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Encrypted links
        ENCRYPTED = {
            "345m9wityo87": b"HkZHHkcPXx0HVlgPHwNIVUtDE1deGwkfWwwEVhs=",  # Externallink
        }

        def get_final_url(name):
            return decrypt_link(ENCRYPTED.get(name, b""))

        # ── Jellonity row: [Support via Jellonity]  [QR Code]
        weblink_row = QHBoxLayout()
        weblink_btn = QPushButton("Open our donation link:")
        weblink_btn.clicked.connect(lambda: open_url_crossplatform(get_final_url("345m9wityo87")))
        weblink_row.addWidget(weblink_btn)

        weblink_qr_btn = QPushButton("QR Code")
        weblink_qr_btn.setFixedWidth(90)
        weblink_qr_btn.clicked.connect(lambda: show_qr_dialog(get_final_url("345m9wityo87"), "Jellonity QR"))
        weblink_row.addWidget(weblink_qr_btn)
        layout.addLayout(weblink_row)

 

        # ── Close
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SupportWindow()
    window.show()
    sys.exit(app.exec_())
