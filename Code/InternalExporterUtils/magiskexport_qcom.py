import os
import sys
import shutil
import zipfile
import tempfile
import traceback
from datetime import datetime
from typing import Optional, Sequence

from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QToolButton, QPushButton, QFileDialog, QMessageBox, QFrame
)

# -------- Global hook for external callers --------
FilePath = ""  # Can be set externally.

# Keep a strong ref to QApplication to avoid GC on macOS
_APP: Optional[QApplication] = None


# -------------------- Helpers --------------------
def _get_app() -> QApplication:
    global _APP
    app = QApplication.instance()
    if app is None:
        # use full argv so file dialogs have proper app name
        app = QApplication(sys.argv)
    _APP = app  # keep a global ref
    return app


def _pick_source_file(parent=None) -> str:
    _get_app()
    path, _ = QFileDialog.getOpenFileName(
        parent, "Select .so / .bin to package",
        "",
        "Shared/Tuned Files (*.so *.bin);;All Files (*)"
    )
    return path or ""


def _norm_abs_device_path(p: str) -> str:
    p = (p or "").strip()
    if not p:
        return ""
    return p if p.startswith("/") else ("/" + p)


def _resolve_source_path(src: str) -> str:
    """
    Try: as-given, CWD, script-dir. Return absolute existing path or "".
    """
    if not src:
        return ""
    if os.path.isfile(src):
        return os.path.abspath(src)
    cand = os.path.join(os.getcwd(), src)
    if os.path.isfile(cand):
        return os.path.abspath(cand)
    base = os.path.dirname(os.path.abspath(__file__))
    cand = os.path.join(base, src)
    if os.path.isfile(cand):
        return os.path.abspath(cand)
    return ""


def _write_text_lf(path: str, text: str, make_exec: bool = False) -> None:
    """
    Write text as UTF-8 (no BOM) with LF newlines on any OS.
    Normalizes CRLF/CR -> LF and optionally sets +x.
    """
    # Normalize any accidental CRLF/CR to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # newline="\n" forces LF on Windows too
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    if make_exec:
        try:
            os.chmod(path, 0o755)
        except Exception:
            pass


# -------------------- UI: Paths picker --------------------
class PathsPickerDialog(QDialog):
    """
    One required path (/system/vendor/lib64) + [+] to add second (/system/vendor/lib).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Magisk Export — Install Paths")
        self.paths = []
        self._second_exists = False

        self.setMinimumWidth(520)

        root = QVBoxLayout(self)

        info = QLabel("Confirm install path(s) on device (Magisk will overlay these):")
        info.setWordWrap(True)
        root.addWidget(info)

        # Row 1 (always present)
        self.row1 = self._make_path_row(default="/system/vendor/lib64", add_plus=True)
        root.addLayout(self.row1['layout'])

        # Placeholder for row2
        self.row2 = None

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_ok)
        btns.addWidget(self.btn_cancel)
        root.addLayout(btns)

    def _make_path_row(self, default: str, add_plus: bool):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        lab = QLabel("Path:")
        edit = QLineEdit(default)
        edit.setPlaceholderText("/system/vendor/lib64")
        edit.setMinimumWidth(360)

        layout.addWidget(lab)
        layout.addWidget(edit, 1)

        btn_plus = None
        btn_minus = None

        if add_plus:
            btn_plus = QToolButton()
            btn_plus.setText("+")
            btn_plus.setToolTip("Add another install path")
            btn_plus.clicked.connect(self._add_second_row)
            layout.addWidget(btn_plus)
        else:
            btn_minus = QToolButton()
            btn_minus.setText("−")
            btn_minus.setToolTip("Remove this install path")
            btn_minus.clicked.connect(self._remove_second_row)
            layout.addWidget(btn_minus)

        return {"layout": layout, "edit": edit, "plus": btn_plus, "minus": btn_minus}

    def _add_second_row(self):
        if self._second_exists:
            return
        # Disable '+' on row1
        if self.row1['plus'] is not None:
            self.row1['plus'].setEnabled(False)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        self.layout().insertWidget(2, sep)

        # Row 2
        self.row2 = self._make_path_row(default="/system/vendor/lib", add_plus=False)
        self.layout().insertLayout(3, self.row2['layout'])
        self._second_exists = True

    def _remove_second_row(self):
        if not self._second_exists or not self.row2:
            return
        for i in reversed(range(self.row2['layout'].count())):
            item = self.row2['layout'].itemAt(i)
            w = item.widget()
            if w:
                self.row2['layout'].removeWidget(w)
                w.deleteLater()
        self.layout().removeItem(self.row2['layout'])
        self.row2 = None
        self._second_exists = False
        if self.row1['plus'] is not None:
            self.row1['plus'].setEnabled(True)

    def accept(self):
        p1 = _norm_abs_device_path(self.row1['edit'].text())
        if not p1 or p1 == "/":
            QMessageBox.critical(self, "Magisk Export", "First path cannot be empty.")
            return

        paths = [p1]
        if self._second_exists and self.row2:
            p2 = _norm_abs_device_path(self.row2['edit'].text())
            if p2 and p2 != "/":
                if p2 == p1:
                    QMessageBox.critical(self, "Magisk Export", "Paths must be different.")
                    return
                paths.append(p2)

        self.paths = paths
        super().accept()


# -------------------- Core export logic --------------------
def export_magisk_module(file_path: str, target_paths: Sequence[str], parent=None) -> Optional[str]:
    """
    Build a Magisk module ZIP with file placed under each absolute path in 'target_paths'.
    Returns saved zip path or None if cancelled/failed.
    """
    _get_app()  # ensure QApplication exists before any dialogs

    file_path = _resolve_source_path((file_path or "").strip())
    if not file_path or not os.path.isfile(file_path):
        QMessageBox.critical(parent, "Magisk Export", "Source file not found:\n%s" % (file_path or "<empty>"))
        return None

    custom = os.path.basename(file_path)
    mod_name = os.path.splitext(custom)[0]

    tmp_root = tempfile.mkdtemp(prefix="MagiskTemp_")
    module_root = os.path.join(tmp_root, "%s_module" % mod_name)

    try:
        # Copy under each target path
        for dev_abs_path in target_paths:
            dev_abs_path = _norm_abs_device_path(dev_abs_path)
            if not dev_abs_path:
                continue
            rel_inside = dev_abs_path.lstrip("/")
            target_dir = os.path.join(module_root, rel_inside)
            os.makedirs(target_dir, exist_ok=True)
            tgt = os.path.join(target_dir, custom)
            shutil.copy2(file_path, tgt)
            try:
                os.chmod(tgt, 0o644)
            except Exception:
                pass

        # module.prop  (LF newlines, UTF-8 no BOM)
        _write_text_lf(
            os.path.join(module_root, "module.prop"),
            f"""id=lop_{mod_name.lower()}
name=LOP Module: {mod_name}
version=1.0
versionCode=1
author=Lens On Phone - Suite
description=Magisk module for {custom}
"""
        )

        # customize.sh
        _write_text_lf(
            os.path.join(module_root, "customize.sh"),
"""# Magisk module - general settings
SKIPUNZIP=0
ASH_STANDALONE=0
REPLACE=""

# set permissions recursively: dirs 0755, files 0644
set_perm_recursive $MODPATH 0 0 0755 0644
""",
            make_exec=True
        )

        # Hooks
        hook_content = "#!/system/bin/sh\nMODDIR=${0%/*}\n"
        for hook in ("post-fs-data.sh", "service.sh"):
            _write_text_lf(os.path.join(module_root, hook), hook_content, make_exec=True)

        # META-INF
        updater = os.path.join(module_root, "META-INF", "com", "google", "android")
        os.makedirs(updater, exist_ok=True)
        _write_text_lf(os.path.join(updater, "updater-script"), "#MAGISK\n")
        _write_text_lf(
            os.path.join(updater, "update-binary"),
            """#!/sbin/sh
umask 022
ui_print() { echo "$1"; }
require_new_magisk() {
  ui_print "*******************************"
  ui_print " Please install Magisk v20.4+! "
  ui_print "*******************************"
  exit 1
}
OUTFD=$2
ZIPFILE=$3
mount /data 2>/dev/null
[ -f /data/adb/magisk/util_functions.sh ] || require_new_magisk
. /data/adb/magisk/util_functions.sh
[ $MAGISK_VER_CODE -lt 20400 ] && require_new_magisk
install_module
exit 0
""",
            make_exec=True
        )

        # Zip (stored)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_basename = f"LOP_{mod_name}_{ts}.zip"
        zip_tmp = os.path.join(tmp_root, zip_basename)
        with zipfile.ZipFile(zip_tmp, "w", compression=zipfile.ZIP_STORED) as z:
            for root, _, files in os.walk(module_root):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, module_root).replace(os.sep, "/")
                    z.write(full, rel)

        # Save As
        _get_app()
        save_path, _ = QFileDialog.getSaveFileName(
            parent, "Save Magisk Module As", zip_basename, "Magisk Module (*.zip)"
        )
        if not save_path:
            QMessageBox.warning(parent, "Magisk Export", "Save cancelled, module discarded.")
            return None

        shutil.move(zip_tmp, save_path)
        QMessageBox.information(parent, "Magisk Export", "Module saved to:\n%s" % save_path)
        return save_path

    except Exception as e:
        traceback.print_exc()
        _get_app()
        QMessageBox.critical(parent, "Magisk Export", "Failed to build module:\n%s" % e)
        return None

    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


# -------------------- High-level runner --------------------
def run(file_path: Optional[str] = None) -> Optional[str]:
    """
    1) Determine file_path (arg > global FilePath > file dialog; with smart path resolving)
    2) PathsPickerDialog (default /system/vendor/lib64; [+] adds /system/vendor/lib)
    3) Build & Save
    """
    _get_app()

    # 1) Source file
    src = (file_path or FilePath or "").strip()
    src = _resolve_source_path(src)
    if not src:
        src = _pick_source_file()
        if not src:
            return None
    if not os.path.isfile(src):
        QMessageBox.critical(None, "Magisk Export", "Source file not found:\n%s" % src)
        return None

    # 2) Pick install paths
    dlg = PathsPickerDialog()
    if dlg.exec_() != QDialog.Accepted:
        return None

    # 3) Export
    return export_magisk_module(src, dlg.paths, parent=None)


# -------------------- CLI entry --------------------
if __name__ == "__main__":
    # Prefer CLI arg; else use global FilePath; else prompt
    cli_fp = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    if cli_fp:
        FilePath = cli_fp

    app = _get_app()
    saved = run(FilePath)
    if saved:
        print(saved)
