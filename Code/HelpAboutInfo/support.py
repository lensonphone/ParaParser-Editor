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
B3458C37AFAEFDFAB43CA = "v23n45p2m34cpm!!2mp834mp5mp347v5mp3452p3487n52cpv348m52348n5"




def decrypt_link(enc_b64, key=B3458C37AFAEFDFAB43CA):
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

        # True/False matrix
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

        # Draw RGB32 and then scale (no anti-aliasing)
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
            "cn014bm10934nv": b"HkZHHkcPXx0aRENNAAxYUVMBXltcWUIUWgMRR1EIFEAeGV1RRkFNVlBPVhxRVQYfGFpAQS1SX1JdVEBWGV8=",  # PayPal
            "3457mnnq2bnv4577": b"FFtHDVtcHggPUAUSQlhTSUQUF1ZYDA5AQR0ERV9HGFQUE1YHAAYDVU5TQV1DAlBGAUoLVQhGQVJTXVNxGVxSGlE=",  # Bitcoin
        }

        def get_final_url(name):
            return decrypt_link(ENCRYPTED.get(name, b""))


        # ── PayPal row: [Donate via PayPal]  [QR Code]
        paypal_row = QHBoxLayout()
        paypal_btn = QPushButton("Donate via PayPal")
        paypal_btn.clicked.connect(lambda: open_url_crossplatform(get_final_url("cn014bm10934nv")))
        paypal_row.addWidget(paypal_btn)

        paypal_qr_btn = QPushButton("QR Code")
        paypal_qr_btn.setFixedWidth(90)
        paypal_qr_btn.clicked.connect(lambda: show_qr_dialog(get_final_url("cn014bm10934nv"), "PayPal QR"))
        paypal_row.addWidget(paypal_qr_btn)
        layout.addLayout(paypal_row)

        # ── Bitcoin row:  "Bitcoin (BTC)"  [readonly address]  [QR Code]
        bitcoin_url = get_final_url("3457mnnq2bnv4577")

        btc_row = QHBoxLayout()
        btc_row.setContentsMargins(0, 0, 0, 0)
        btc_row.setSpacing(8)

        btc_label = QLabel("Bitcoin (BTC)")
        btc_row.addWidget(btc_label)

        btc_line = QLineEdit()
        btc_line.setReadOnly(True) # can be selected and copied
        btc_line.setFrame(False) # no frame
        btc_line.setText(bitcoin_url or "")
        btc_line.setCursorPosition(0)
        # remove setFocusPolicy(Qt.NoFocus)
        btc_line.setStyleSheet("QLineEdit { border: none; background: transparent; }")
        btc_row.addWidget(btc_line, 1)

        btc_qr_btn = QPushButton("QR Code")
        btc_qr_btn.setFixedWidth(90)
        btc_qr_btn.clicked.connect(lambda: show_qr_dialog(bitcoin_url, "Bitcoin QR"))
        btc_row.addWidget(btc_qr_btn)

        layout.addLayout(btc_row)


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
