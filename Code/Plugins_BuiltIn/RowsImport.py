TRIKSMODULENAME = "Rows Import Tool"
UPDATE_ROWS = 1


import os, sys
from typing import List, Sequence, Optional
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox
from PyQt5.QtCore import QObject, QEventLoop, QMetaObject, Qt, pyqtSlot, QThread

def _ensure_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app

def _on_gui_thread() -> bool:
    app = QApplication.instance()
    return bool(app and (QThread.currentThread() is app.thread()))

def _call_on_gui_thread(fn, *args, **kwargs):
    app = _ensure_app()
    if _on_gui_thread():
        return fn(*args, **kwargs)

    result = {"v": None, "e": None}
    class _Invoker(QObject):
        @pyqtSlot()
        def go(self):
            try:
                result["v"] = fn(*args, **kwargs)
            except Exception as e:
                result["e"] = e
            finally:
                loop.quit()
    inv = _Invoker()
    inv.moveToThread(app.thread())
    loop = QEventLoop()
    QMetaObject.invokeMethod(inv, "go", Qt.QueuedConnection)
    loop.exec_()
    if result["e"] is not None:
        raise result["e"]
    return result["v"]

def _read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\r\n") for line in f]

def run(file_path, rows: Sequence):
    """
        ALWAYS displays the 'Open' dialog.
        file_path (if provided) is used as a starting directory hint.
        Reverts imported rows or original rows on cancel.
    """
    def _flow():
        _ensure_app()
        start_dir = ""
        if isinstance(file_path, str) and file_path.strip():
            start_dir = file_path if os.path.isdir(file_path) else os.path.dirname(file_path)
        path, _ = QFileDialog.getOpenFileName(
            None, "Import Data from Text File", start_dir,
            "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return list(rows)
        try:
            imported = _read_lines(path)
        except Exception as e:
            QMessageBox.critical(None, "Import Error", f"Error during import:\n{e}")
            return list(rows)

        confirm = QMessageBox.question(
            None, "Import Confirmation",
            f"Successfully loaded {len(imported)} rows from:\n{path}\n\nUse imported data?"
        )
        if confirm == QMessageBox.Yes:
            QMessageBox.information(None, "Import Successful",
                                    f"Data successfully imported!\n{len(imported)} rows loaded.")
            return imported
        return list(rows)
    return _call_on_gui_thread(_flow)
