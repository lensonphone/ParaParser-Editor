TRIKSMODULENAME = "Rows Export Tool"
UPDATE_ROWS = 0


import os, sys
from typing import Sequence, Optional
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

def _export_suggest_name(hint: Optional[str]) -> str:
    if not hint:
        return os.path.join(".", "rows.txt")
    if os.path.isdir(hint):
        return os.path.join(hint, "rows.txt")
    base = os.path.splitext(os.path.basename(hint))[0] or "rows"
    directory = os.path.dirname(hint)
    return os.path.join(directory if directory else ".", f"{base}.txt")

def _write_lines(path: str, rows: Sequence):
    content = "\n".join(str(r) for r in rows)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
        if not content.endswith("\n"):
            f.write("\n")

def run(file_path, rows: Sequence):
    """
    ALWAYS displays the 'Save As' dialog.
    file_path (if provided) is used as a name/folder hint.
    Always returns the original rows.
    """
    def _flow():
        _ensure_app()
        initial = _export_suggest_name(file_path if isinstance(file_path, str) else None)
        path, _ = QFileDialog.getSaveFileName(
            None, "Export Data to Text File", initial,
            "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return list(rows)
        if not path.lower().endswith(".txt"):
            path += ".txt"

        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            _write_lines(path, rows)
            QMessageBox.information(None, "Export Successful",
                                    f"Data successfully exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(None, "Export Error", f"Error during export:\n{e}")
        return list(rows)
    return _call_on_gui_thread(_flow)
