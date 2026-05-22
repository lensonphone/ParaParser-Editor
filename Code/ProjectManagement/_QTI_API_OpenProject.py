import os
import re
from typing import List, Sequence, Tuple, Union, Optional

# ──────────────────────────── USER KNOBS (for standalone launch) ──────────
ProjPath: str = "qti.QPPProj.QPPProj" # <- specify the path to .QPPProj here when launching standalone

# ── Qt (for relink/save dialogs) ──────────────────────────────────────────
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

# ── QPARParser Import (with fallback to local paths) ──────────────────────────
from Code.ProjectManagement._QTIProj_Co_De_mpressor import QPARParser


# ── Text Parsing Utilities rows ────────────────────────────────────────────
def _text_to_rows(text: str) -> List[List[str]]:
    rows: List[List[str]] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if "\t" in s:
            rows.append([c.strip() for c in s.split("\t")])
        elif "," in s:
            rows.append([c.strip() for c in s.split(",")])
        else:
            rows.append([s])
    return rows


def _is_supported_bin(path: str) -> bool:
    base = os.path.basename(path or "")
    name_l = base.lower()
    # Allow: com.qti.*.bin and libchromatix*.so
    if name_l.endswith(".bin") and base.startswith("com.qti."):
        return True
    if name_l.endswith(".so") and base.startswith("libchromatix"):
        return True
    return False


def _ensure_qapp():
    app = QApplication.instance()
    if app is None:
        QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
        app = QApplication([])
    return app


def _clean_str_path(p: str) -> str:
    # Remove quotes/spaces from edges, replace backslashes
    if not isinstance(p, str):
        try:
            p = p.decode("utf-8", "ignore")
        except Exception:
            p = str(p)
    p = p.strip().strip('"').strip("'")
    p = p.replace("\\", "/")
    return os.path.normpath(p)


def _normalize_embedded_path(embedded: Union[str, bytes, Sequence, None],
                             project_dir: str) -> str:
    """
    Converts the embedded path to a single string and attempts to make it absolute.
    Supports: str, bytes, [str], (str, ...), None.
    Returns "" if a valid path could not be obtained.
    """
    candidate: Optional[str] = None

    if embedded is None:
        candidate = ""
    elif isinstance(embedded, (list, tuple)):
        for item in embedded:
            if item:
                candidate = _clean_str_path(item if isinstance(item, str) else str(item))
                if candidate:
                    break
        if candidate is None:
            candidate = ""
    elif isinstance(embedded, (str, bytes)):
        candidate = _clean_str_path(embedded if isinstance(embedded, str) else embedded.decode("utf-8", "ignore"))
    else:
        candidate = _clean_str_path(str(embedded))

    if not candidate:
        return ""

    if not os.path.isabs(candidate):
        candidate = os.path.normpath(os.path.join(project_dir, candidate))

    candidate = os.path.expandvars(os.path.expanduser(candidate))
    return candidate


def _decompress_qpproj_to_text_and_path(project_path: str) -> Tuple[str, Union[str, Sequence, None]]:
    """
    Returns (text, embedded_path_raw).
    embedded_path_raw can be str / list / tuple / None — we'll normalize this later.
    """
    with open(project_path, "rb") as f:
        compressed = f.read()

    parser = QPARParser()
    out = parser.process_data(compressed)

    if isinstance(out, tuple):
        decompressed = out[0]
        embedded_path_raw = out[1] if len(out) > 1 else ""
    else:
        decompressed = out
        embedded_path_raw = ""

    text = decompressed.decode("utf-8", errors="ignore")
    return text, embedded_path_raw


def _offer_pick_lib(initial_dir: str = "") -> str:
    """
    .bin/.so selection dialog with a filter for supported names.
    Returns the selected path or "" if canceled.
    """
    dlg = QFileDialog(
        None,
        "Link QTI Library (.bin/.so)",
        initial_dir,
        "Chromatix Libraries (*.bin *.so);;QTI Library (*.bin);;libchromatix (*.so)"
    )
    dlg.setFileMode(QFileDialog.ExistingFile)

    while True:
        if not dlg.exec_():
            return ""
        paths = dlg.selectedFiles()
        if not paths:
            return ""
        path = paths[0]
        if _is_supported_bin(path):
            return path
        QMessageBox.warning(
            None, "Unsupported file",
            "Please select a QTI library: com.qti.*.bin or libchromatix*.so"
        )
        # repeat request in a loop


def _ask_relink_and_save(project_path: str, text: str, new_bin_path: str) -> bool:
    """
    Shows the dialog:
      [Relink & Save]  [Continue without Saving]  [Cancel]
    When Save is selected, overwrites the project with the new path via QPARParser().
    Returns True if not Cancel (any continuation of work), False if Cancel.
    """
    box = QMessageBox()
    box.setWindowTitle("Relink project?")
    box.setText("Relink the project with the selected QTI library and save?")
    save_btn = box.addButton("Relink && Save", QMessageBox.AcceptRole)
    cont_btn = box.addButton("Continue without Saving", QMessageBox.ActionRole)
    cancel_btn = box.addButton(QMessageBox.Cancel)
    box.setDefaultButton(save_btn)
    box.exec_()

    clicked = box.clickedButton()
    if clicked == cancel_btn:
        return False

    if clicked == save_btn:
        try:
            parser = QPARParser()
            out = parser.process_data(text.encode("utf-8", "ignore"), new_bin_path)
            compressed = out[0] if isinstance(out, tuple) else out
            with open(project_path, "wb") as f:
                f.write(compressed)
            QMessageBox.information(None, "Relinked", "Project relinked and saved:\n" + project_path)
        except Exception as e:
            QMessageBox.critical(None, "Relink save failed", str(e))
            # continue with the selected path even if saving failed
    return True


def getprojectopen(project_path: str) -> Tuple[str, List[List[str]]]:
    """
    Opens .QPPProj, returns (bin_path, rows).
    - If the built-in library path is missing / broken / path list,
    correctly normalizes it. If the file is not found, it prompts you to select a new
    .bin/.so and (as before) offers Relink & Save.
    - If you cancel the selection, it returns ("", rows).

    Project read/decode exceptions are raised.
    """
    if not project_path or not os.path.exists(project_path):
        raise FileNotFoundError(f"Project not found: {project_path!r}")

    _ensure_qapp()

    proj_dir = os.path.dirname(os.path.abspath(project_path))

    # 1) Decode the project
    text, embedded_raw = _decompress_qpproj_to_text_and_path(project_path)
    rows = _text_to_rows(text)

    # 2) Normalize any embedded_path format (str/list/tuple/bytes/None)
    bin_path = _normalize_embedded_path(embedded_raw, proj_dir)

    # 3) If the path exists and the file exists, return immediately
    if bin_path and os.path.exists(bin_path):
        return bin_path, rows

    # 4) Offer to select a library and optionally resave the project
    initial_dir = proj_dir
    picked = _offer_pick_lib(initial_dir)
    if not picked:
        # user canceled
        return "", rows

    # 5) Ask about relink & save
    proceeded = _ask_relink_and_save(project_path, text, picked)
    if not proceeded:
        # user clicked Cancel
        return "", rows

    return picked, rows


# ── Standalone launch without arguments ─────────────────────────────────────────
if __name__ == "__main__":
    # 1) Check that ProjPath is set
    if not ProjPath:
        print("Set ProjPath at the top of the script to your .QPPProj file.")
        raise SystemExit(1)

    print(f"[PROJECT] {ProjPath}")

    # 2) Open the project
    linked_path, rows = getprojectopen(ProjPath)

    # 3) Print the resulting library path
    print(f"[LIB PATH] {linked_path or '<none>'}")

    # 4) Print the first 30 lines
    n_show = min(30, len(rows))
    print(f"[ROWS PREVIEW] showing first {n_show} of {len(rows)}")
    for i in range(n_show):
        line = rows[i]
        # If this is a list, join them with commas; if it is a string, print as is
        if isinstance(line, list):
            print(f"{i:03d}: " + ", ".join(str(x) for x in line))
        else:
            print(f"{i:03d}: {str(line)}")
