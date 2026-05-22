import sys, os, re, shutil
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QBrush
from PyQt5.QtWidgets import QLayout 
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy, QLineEdit, QDialog,
    QCheckBox, QPlainTextEdit, QFileDialog, QMessageBox, QTabWidget,
    QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtWidgets import QAction, QActionGroup 
import importlib.util
import traceback
from functools import partial
import importlib.util
import importlib.machinery  
import shutil               
# --- helpers at module level ---
import sys, os, importlib.util, importlib.machinery
from PyQt5.QtCore import QObject, QThread
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtCore import QThread, QObject, QTimer, Qt, pyqtSignal
from PyQt5.QtWidgets import QProgressDialog
import importlib.util, importlib.machinery
from PyQt5.QtGui import QFont, QColor, QBrush, QKeySequence
from PyQt5.QtGui import QCloseEvent

import tempfile
import stat
import subprocess
import mmap, numpy as np

from pathlib import Path
import os, sys, re, stat, tempfile, shutil, subprocess, mmap, traceback
import importlib.util, importlib.machinery
from functools import partial

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject, QThread
from PyQt5.QtGui import QFont, QColor, QBrush, QKeySequence
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout,
    QLabel, QGroupBox, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy, QLineEdit, QDialog,
    QCheckBox, QPlainTextEdit, QFileDialog, QMessageBox, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QAction, QActionGroup
)


from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QFileDialog, QMessageBox



# --- Help+Support+About import  ----------------------------------------------
from Code.HelpAboutInfo.About_QTIPP import AboutDialog
from Code.HelpAboutInfo.Help_QTIParamExtractorReplacer import QTIHelpDialog
from Code.HelpAboutInfo.support import SupportWindow
# --- Help+Support+About import  ----------------------------------------------


# --- Icon import  ----------------------------------------------
from Resources.embedded_ParamEditor_ico import get_embedded_icon
# --- Icon import  ----------------------------------------------





# --- Custom import  ----------------------------------------------
import Code.Parsers.LegacyChromatix.Load_Chromatix_Data as LCAddrLenVer
from Code.ProjectManagement._QTIProj_Co_De_mpressor import QPARParser
import Code.Tools._QTIHex as QTIHex
import Code.Tools._QTIHexEdit as QTIHexEdit
import Code.InternalExporterUtils._QTICheckSum as ChkSum
import Code.Tools._QTIDictionaryCreator as QDCreate
import Code.Tools._QTIDictionaryParser as Qdict
import Code.Parsers.Importer._QTI_API_ImportLib as QTIAPIImportLib
import Code.ProjectManagement._QTI_API_OpenProject as QTIAPIOpenProj #getprojectopen
# --- Custom import  ----------------------------------------------

# --- Magisk import  ----------------------------------------------

import Code.InternalExporterUtils.magiskexport_qcom as MagiskExport
import Code.InternalExporterUtils.adb_export as ADBEX


# --- BuiltIn Plugins --- 

try:
    import Code.Plugins_BuiltIn.AutoformatTree2 as BuiltIn_AutoformatTree
    import Code.Plugins_BuiltIn.BatchExportImport as BuiltIn_BatchExportImport
    import Code.Plugins_BuiltIn.RowsExport as BuiltIn_RowsExport # ex RowsExportImportTool
    import Code.Plugins_BuiltIn.RowsImport as BuiltIn_RowsImport # ex RowsExportImportTool
except ImportError:
    import Plugins_BuiltIn.AutoformatTree2 as BuiltIn_AutoformatTree
    import Plugins_BuiltIn.BatchExportImport as BuiltIn_BatchExportImport
    import Plugins_BuiltIn.RowsExport as BuiltIn_RowsExport # ex RowsExportImportTool
    import Plugins_BuiltIn.RowsImport as BuiltIn_RowsImport # ex RowsExportImportTool

# --- BuiltIn Plugins --- 

APP_TITLE = "QTI Parameters Control - v0.0.1"

AllowDebug = 0

MOD = "Meta" if sys.platform == "darwin" else "Ctrl"

USETABLEINDEXASONE=1

TABLE_BATCH = 500      # how many lines per tick
TREE_BATCH  = 500      # how many lines per tick


CURRENT_CHROMATIX_VER: str = ""

def _dbg(msg: str) -> None:
    if AllowDebug:
        print(msg, file=sys.stderr)


        
def _safe_dir_of(path: str) -> str:
    try:
        d = os.path.dirname(path or '')
        return d if d else os.getcwd()
    except Exception:
        return os.getcwd()



# ─── CRC16/CCITT-FALSE (poly=0x1021, init=0xFFFF) ─────────────────────────

def checksum16_numpy(path: str, ones_complement: bool = False, little_endian=True) -> int:
    with open(path, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        b = memoryview(mm)
        # If the length is odd, we pad it with zero (as is usually done for 16-bit sums)
        odd = len(b) & 1
        if odd:
            b2 = np.empty(len(b)+1, dtype=np.uint8)
            b2[:-1] = np.frombuffer(b, dtype=np.uint8)
            b2[-1] = 0
            b = b2
        dtype = np.dtype('<u2' if little_endian else '>u2')
        arr = np.frombuffer(b, dtype=dtype)
        total = int(arr.sum(dtype=np.uint64))  # sum in 64-bit to avoid overflows
        if ones_complement:
            # reduce to 16 bits by adding carries (Internet checksum)
            total = (total & 0xFFFF) + (total >> 16)
            total = (total & 0xFFFF) + (total >> 16)
            return (~total) & 0xFFFF
        else:
            return total & 0xFFFF


def _file_sig16(path: str) -> tuple:
    return (os.path.getsize(path), checksum16_numpy(path))

def _files_differ(a: str, b: str) -> bool:
    if not (os.path.exists(a) and os.path.exists(b)):
        return True
    try:
        return _file_sig16(a) != _file_sig16(b)
    except Exception:
        # Fallback: If the signature couldn't be found, let's compare it byte by byte
        if os.path.getsize(a) != os.path.getsize(b):
            return True
        with open(a,'rb') as fa, open(b,'rb') as fb:
            while True:
                ba, bb = fa.read(1<<20), fb.read(1<<20)
                if not ba and not bb: break
                if ba != bb: return True
        return False

def _set_hidden_attr(path: str):
    try:
        if os.name == "nt":
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
        elif sys.platform == "darwin":
            # Don't rename it, leave *.bak next to it, just hide it with a flag
            subprocess.run(["chflags", "hidden", path], check=False)
        else:
            # On Linux, there is no concept of hidden as an attribute; we leave it as is
            pass
    except Exception:
        pass


def _clear_hidden_attr(path: str):
    """Remove the 'hidden' attribute from a file (Windows/macOS); on Linux, no-op."""
    try:
        if os.name == "nt":
            import ctypes, ctypes.wintypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
            GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
            SetFileAttributesW = ctypes.windll.kernel32.SetFileAttributesW
            GetFileAttributesW.restype = ctypes.wintypes.DWORD

            attrs = GetFileAttributesW(str(path))
            if attrs != INVALID_FILE_ATTRIBUTES and (attrs & FILE_ATTRIBUTE_HIDDEN):
                SetFileAttributesW(str(path), attrs & ~FILE_ATTRIBUTE_HIDDEN)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["chflags", "nohidden", path], check=False)
        else:
            # On Linux, there is no concept of hidden as an attribute; we leave it as is
            pass
    except Exception:
        pass




def _atomic_replace(src: str, dst: str):
    # Safely replace the dst file with the contents of src
    os.replace(src, dst)

def _atomic_write_bytes(path: str, data: bytes):
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try: os.remove(tmp)
        except FileNotFoundError: pass


# ─── CRC16/CCITT-FALSE (poly=0x1021, init=0xFFFF) ─────────────────────────







def app_base_dir():
    # where is the exe/bundle or script located
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def user_plugins_dir():
    d = os.path.join(app_base_dir(), "Plugins")
    _dbg(f"[Plugins looking at] = {d}")
    os.makedirs(d, exist_ok=True)
    # Windows: Allow access to dependent DLLs in this folder
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(d)
        except Exception:
            pass
    # Unix: sometimes it helps to load symbols globally
    if os.name == "posix" and hasattr(sys, "setdlopenflags"):
        try:
            import ctypes
            sys.setdlopenflags(sys.getdlopenflags() | ctypes.RTLD_GLOBAL)
        except Exception:
            pass
    return d



# --- helpers for plugins I/O -----------------------------------------------
def _normalize_rows_for_plugin(rows):
    """We always give the plugin a list of 'ID,Name,Offset,Length' strings.."""
    out = []
    for r in (rows or []):
        if isinstance(r, (list, tuple)):
            out.append(",".join(str(x) for x in r))
        else:
            out.append(str(r))
    return out
# ---------------------------------------------------------------------------





# -----------------------------------------------------------------------




# --- Custom Dictionary Parser lookup ----------------------------------------
def _candidate_custom_dict_paths():
    base = app_base_dir()
    search_dirs = [base, os.path.join(base, "ParaParser")]

    names = ["QTICustomDictionaryParser", "_QTICustomDictionaryParser"]
    exts = [".pyd"] if os.name == "nt" else [".so"]  # macOS/Linux: .so

    for d in search_dirs:
        # flat files
        for nm in names:
            for ext in exts:
                yield os.path.join(d, nm + ext)
        # nested options <dir>/<name>/<name>.ext
        for nm in names:
            dn = os.path.join(d, nm)
            if os.path.isdir(dn):
                for ext in exts:
                    yield os.path.join(dn, nm + ext)

def _find_custom_dict_module():
    for p in _candidate_custom_dict_paths():
        if os.path.exists(p):
            try:
                _dbg(f"[CustomDict] using: {p}")
                return load_plugin_from_file(p)
            except Exception as e:
                _dbg(f"[CustomDict] load error @ {p}: {e}")
    return None
# ---------------------------------------------------------------------------




# --- User Dictionary Creator lookup -----------------------------------------




def _candidate_user_creator_paths():
    base = app_base_dir()
    search_dirs = [base, os.path.join(base, "ParaParser")]  # only nearby and in ParaParser/

    #_dbg(f"search_dirs = {search_dirs}")
    # we support both names
    names = ["QTIDictionaryCreator", "_QTIDictionaryCreator"]
    # only binary extensions: .pyd (Windows) or .so (Linux/macOS CPython)
    exts = [".pyd"] if os.name == "nt" else [".so"]

    for d in search_dirs:
        # flat files: <dir>/QTIDictionaryCreator.so, <dir>/_QTIDictionaryCreator.so, etc.
        for nm in names:
            for ext in exts:
                yield os.path.join(d, nm + ext)

        # nested options: <dir>/QTIDictionaryCreator/QTIDictionaryCreator.so etc..
        for nm in names:
            dn = os.path.join(d, nm)
            if os.path.isdir(dn):
                for ext in exts:
                    yield os.path.join(dn, nm + ext)


def _find_user_dict_creator():
    for p in _candidate_user_creator_paths():
        if os.path.exists(p):
            try:
                _dbg(f"[UserDictCreator] using: {p}")
                return load_plugin_from_file(p)
            except Exception as e:
                _dbg(f"[UserDictCreator] load error @ {p}: {e}")
    return None

# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------




def load_plugin_from_file(fullpath: str):
    """
Loads a module from .py / .so / .pyd / .dylib / .dll
Module name = basename up to the first dot (must match PyInit_<name> for binaries)
    """
    base = os.path.basename(fullpath)
    modname = base.split('.')[0]
    ext = os.path.splitext(base)[1].lower()

    if ext in (".pyd", ".so", ".dylib", ".dll"):
        loader = importlib.machinery.ExtensionFileLoader(modname, fullpath)
    else:
        loader = importlib.machinery.SourceFileLoader(modname, fullpath)

    spec = importlib.util.spec_from_loader(modname, loader, origin=fullpath)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot create import spec for {fullpath}")

    module = importlib.util.module_from_spec(spec)
    # Important for .pyd/.so: register before exec_module,
    # so internal imports can find the module
    sys.modules[modname] = module
    spec.loader.exec_module(module)  # type: ignore
    return module
# --------------------------- importing custom modules ---------------------------



# --- worker only for parsing (background, so as not to freeze the UI) ---
class _ImportWorker(QThread):
    done = pyqtSignal(object, object) # rows, err (err=None if ok)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            # adapter as is
            rows = QTIAPIImportLib.getrowsfromlib(self.path)
            self.done.emit(rows, None)
        except Exception as e:
            self.done.emit(None, e)

# --------------------------- Sidebar (Right Column) ---------------------------
class ControlPanel(QWidget):
    # Signals to connect real logic later
    extractBinary = pyqtSignal()
    replaceBinary = pyqtSignal()
    extractParam = pyqtSignal(str)
    replaceParam = pyqtSignal(str)
    checksumFix = pyqtSignal()
    clickMe = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()



    def _boxed(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        return box

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        


        # File & parser header
        header = self._boxed("")
        hv = QVBoxLayout(header)
        self.titleLabel = QLabel("Open Library First...")
        self.titleLabel.setWordWrap(True)
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.titleLabel.setStyleSheet("font-weight:600;")
        hv.addWidget(self.titleLabel)
        self.versionLabel = QLabel("Parameter Parser Version:")
        self.versionLabel.setAlignment(Qt.AlignCenter)
        hv.addWidget(self.versionLabel)
        root.addWidget(header)

        # Selected parameter 
        box_sel = self._boxed("Selected Parameter")
        sv = QVBoxLayout(box_sel)

        self.selectedLabel = QLabel("Select Parameter First...")
        self.selectedLabel.setObjectName("selectedLabel")
        self.selectedLabel.setAlignment(Qt.AlignCenter)
        self.selectedLabel.setWordWrap(True)
      

        sv.addWidget(self.selectedLabel)
        root.addWidget(box_sel)

        # --- Extract/Replace as Binary ---
        box_bin = self._boxed("Extract/Replace As Binary")
        vb = QVBoxLayout(box_bin)
        hb = QHBoxLayout()
        btn_extract_bin = QPushButton("Extract")
        btn_replace_bin = QPushButton("Replace")
        btn_extract_bin.clicked.connect(self.extractBinary.emit)
        btn_replace_bin.clicked.connect(self.replaceBinary.emit)
        hb.addWidget(btn_extract_bin)
        hb.addWidget(btn_replace_bin)
        vb.addLayout(hb)
        root.addWidget(box_bin)




        # --- Dictionary Parser (Built-in) ---
        box_param = self._boxed("Dictionary Parser (Built-in)")
        self.grpDict = box_param

        pv = QVBoxLayout(box_param)
        line = QHBoxLayout()
        line.addWidget(QLabel("Dictionary:"))
        self.dictionary = QComboBox()
        self.dictionary.setEditable(False)
        self.dictionary.addItems(["Not selected", "Import *.Qdict"])
        self.dictionary.setCurrentIndex(0)
        self.dictionary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.addWidget(self.dictionary)
        pv.addLayout(line)

        # Autofind Dictionary checkbox
        self.autofindCheck = QCheckBox("Autofind Dictionary")
        self.autofindCheck.setChecked(False)
        pv.addWidget(self.autofindCheck)

        bh = QHBoxLayout()
        # rename them for clarity and save them as attributes:
        self.btnDicExport = QPushButton("Export")
        self.btnDicImport = QPushButton("Import")

        self.btnDicExport.clicked.connect(lambda: self.extractParam.emit(self.dictionary.currentText()))
        self.btnDicImport.clicked.connect(lambda: self.replaceParam.emit(self.dictionary.currentText()))
        bh.addWidget(self.btnDicExport)
        bh.addWidget(self.btnDicImport)

        # Initially disabled
        self.btnDicExport.setEnabled(False)
        self.btnDicImport.setEnabled(False)

        pv.addLayout(bh)
        root.addWidget(box_param)

        # Reaction to dictionary change — enable/disable buttons:
        self.dictionary.currentTextChanged.connect(self._on_dict_changed)
        # primary initialization
        self._on_dict_changed(self.dictionary.currentText())







        # Spacer
        spacer = QFrame()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(spacer)

        # Bottom buttons
        bottom = QHBoxLayout()
        self.btnClickMe = QPushButton("Find")
        self.btnDonate = QPushButton("Donate :)")        
        self.btnClose = QPushButton("Close")
        self.btnClickMe.clicked.connect(self.clickMe.emit)
        self.btnDonate.clicked.connect(self.support)
        bottom.addWidget(self.btnClickMe)
        bottom.addWidget(self.btnDonate)
        bottom.addWidget(self.btnClose)
        root.addLayout(bottom)


    def _on_dict_changed(self, text: str):
        bad = text in ("Not selected", "Import *.Qdict", None, "")
        self.btnDicExport.setEnabled(not bad)
        self.btnDicImport.setEnabled(not bad)




    def support(self):
        dlg = SupportWindow()
        dlg.exec_()

        
# ------------------------------ Hex Viewer Dialog ------------------------------
class HexViewerDialog(QDialog):
    def __init__(self, data_or_hex, parent=None, title: str = "Hex Viewer"):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QVBoxLayout(self)
        self.view = QPlainTextEdit(self)
        self.view.setReadOnly(True)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.Monospace)
        self.view.setFont(mono)
        # accept bytes or hex-string
        if isinstance(data_or_hex, (bytes, bytearray)):
            buf = bytes(data_or_hex)
        elif isinstance(data_or_hex, str) and len(data_or_hex) % 2 == 0:
            try:
                buf = bytes.fromhex(data_or_hex)
            except Exception:
                buf = data_or_hex.encode('utf-8', errors='ignore')
        else:
            buf = bytes()
        self.view.setPlainText(self._hexdump(buf))
        lay.addWidget(self.view)
        btn_row = QHBoxLayout()
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn, alignment=Qt.AlignRight)
        lay.addLayout(btn_row)

    def _hexdump(self, buf: bytes, width: int = 16) -> str:
        lines = []
        for off in range(0, len(buf), width):
            chunk = buf[off:off+width]
            hexpart = ' '.join(f"{b:02X}" for b in chunk)
            asciipart = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"{off:08X}  {hexpart:<{width*3}}  {asciipart}\n")
        return ''.join(lines)






class PluginWorker(QObject):
    finished = pyqtSignal(list)   # new_rows
    failed = pyqtSignal(str)      # traceback

    def __init__(self, fn, file_path, rows):
        super().__init__()
        self.fn = fn
        self.file_path = file_path
        self.rows = rows

    def run_old(self):
        try:
            res = self.fn(self.file_path, self.rows)
            # The plugin may return None/empty - we consider it "no changes"
            if isinstance(res, list):
                self.finished.emit(res)
            else:
                self.finished.emit([])
        except Exception:
            self.failed.emit(traceback.format_exc())


    def run(self):
        try:
            res = self.fn(self.file_path, self.rows)
            # Let's normalize the result:
            if res is None:
                out = []
            elif isinstance(res, str):
                out = [ln for ln in res.splitlines() if ln.strip()]
            elif isinstance(res, list):
                out = res
            else:
                out = []
            self.finished.emit(out)
        except Exception:
            self.failed.emit(traceback.format_exc())







# ------------------------------- Main Window ---------------------------------
class MainWindow(QMainWindow):

    #inside the MainWindow class (at the top where the other attributes are)
    _TABLE_CHUNK = 800      # How many rows per tick should be added to the table?
    _TREE_CHUNK  = 400      # How many elements per tick should be added to the tree?


    
    def __init__(self, file_path: str = None, rows: list = None, project_path: str = ""):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 680)

        self._syncing_selection = False # loop protection
        self.rows_model = [] # row model with metadata
        self.id_to_row_index = {} # id_raw -> row index (table)
        self.id_to_tree_item = {} # id_raw -> QTreeWidgetItem

        self.project_path = project_path or "" # <— save as an attribute
        self._rows_raw = None # we'll put the original rows here

        self._build_ui() # first, create the panel/widgets
        self._build_menu() # now You can create a menu; it uses self.panel
        self._update_project_actions()
        self._sync_actions_enabled() # if the menu already exists

        self._user_dict_creator_mod = None

        self._sort_mode = "As Parsed"
        self.view_order = [] # list of MODEL indexes in display order
        self.model_to_view = {} # reverse map: model index -> table index
        
        #_dbg(f"[project_path] = {self.project_path}")        
        

       

        # custom dictionary parser, if any
        self._custom_dict_mod = _find_custom_dict_module()
        self._update_dict_panel_title()



        # Startup modes
        if rows is not None and file_path:
            self.set_file(file_path, rows=rows)



        self._plugin_update_policy = None   # UPDATE_ROWS from the current plugin
        self._plugin_name = None            # name of the current plugin (for messages)


        # ── Find/Hex state ───────────────────────────────────────────────
       
        self._last_find = ""           # text search by Name
        self._last_find_hex = ""       # latest HEX template (cleaned)
        self._last_hex_pos = None      # the last offset found in the file (int) or None





    # ----------------------------- UI build --------------------------------
    def _build_ui(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.setCentralWidget(splitter)

        # Left: TABS -> Table & Tree
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        # ---- Table tab
        self.table = QTableWidget(0, 4)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Offset", "Length"])
        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.Fixed)   # ID
        hh.setSectionResizeMode(1, QHeaderView.Stretch) # Name
        hh.setSectionResizeMode(2, QHeaderView.Fixed)   # Offset
        hh.setSectionResizeMode(3, QHeaderView.Fixed)   # Length
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        # fonts
        tfont = self.table.font()
        tfont.setPointSize(12)
        self.table.setFont(tfont)
        hfont = self.table.horizontalHeader().font()
        hfont.setPointSize(10)
        self.table.horizontalHeader().setFont(hfont)
        self.table.verticalHeader().setFont(hfont)
        fm = self.table.fontMetrics()
        self.table.verticalHeader().setDefaultSectionSize(int(fm.height() * 1.3))
        # signals
        self.table.itemDoubleClicked.connect(self._on_table_item_double_clicked)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.tabs.addTab(self.table, "Table")

        # ---- Tree tab
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(False)
        self.tree.setHeaderLabels(["Name (ID)"])
        tf = self.tree.font()
        tf.setPointSize(12)
        self.tree.setFont(tf)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self.tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.tabs.addTab(self.tree, "Tree")
    
        self.tree.setUniformRowHeights(True)


        # Right: control panel
        self.panel = ControlPanel()
        self.panel.btnClose.clicked.connect(self.close)
        self.panel.clickMe.connect(self.open_find_dialog)
        self.panel.extractBinary.connect(self.on_extract_binary)
        self.panel.replaceBinary.connect(self.on_replace_binary)
        self.panel.extractParam.connect(self.on_extract_param)
        self.panel.replaceParam.connect(self.on_replace_param)
        self.panel.autofindCheck.toggled.connect(self._on_autofind_toggled)
        self.panel.dictionary.activated[str].connect(self._on_dictionary_activated)
        self.panel.dictionary.currentTextChanged.connect(lambda _=None: self._sync_actions_enabled())

        self.panel.checksumFix.connect(self.on_checksum_fix)
        splitter.addWidget(self.panel)

        splitter.setSizes([800, 300])

        # Status bar
        self.statusBar().showMessage("Ready")



    def _build_menu(self):
        mb = self.menuBar()

        # File
        self.menuFile = mb.addMenu("File")


        self.actOpenProj = QAction("Project - Open", self)
        self.actOpenProj.setShortcut(QKeySequence(f"Ctrl+O"))          # Cmd/Ctrl+S
        self.actOpenProj.triggered.connect(self.openProj)
        self.menuFile.addAction(self.actOpenProj)
        
        self.actSave = QAction("Project - Save", self)
        self.actSave.setShortcut(QKeySequence(f"Ctrl+S"))          # Cmd/Ctrl+S
        self.actSave.triggered.connect(self.on_project_save)
        
        self.menuFile.addAction(self.actSave)

        self.actSaveAs = QAction("Project - Save As...", self)
        self.actSaveAs.setShortcut(QKeySequence(f"Ctrl+Shift+S"))  # Cmd/Ctrl+Shift+S
        self.actSaveAs.triggered.connect(self.on_project_save_as)
        self.menuFile.addAction(self.actSaveAs)



        # --- Library block (separator) ---
        self.menuFile.addSeparator()



        self.actImportLibrary = QAction("Library - Import", self)
        self.actImportLibrary.setShortcut(QKeySequence(f"Ctrl+L"))
        self.actImportLibrary.triggered.connect(self.Import_library)
        self.menuFile.addAction(self.actImportLibrary)


        self.actOverwriteLibrary = QAction("Library - Overwrite", self)
        self.actOverwriteLibrary.triggered.connect(self.on_overwrite_library)
        self.menuFile.addAction(self.actOverwriteLibrary)

        self.actSaveAsLibrary = QAction("Library - Export  As...", self)
        self.actSaveAsLibrary.triggered.connect(self.on_saveas_library)
        self.menuFile.addAction(self.actSaveAsLibrary)

        self.actRevertLibrary = QAction("Library - Revert Changes", self)
        self.actRevertLibrary.triggered.connect(self.revert_library)
        self.menuFile.addAction(self.actRevertLibrary)


        # --- Magisk block (separator) ---
        self.menuFile.addSeparator()
        
        self.actExportLibasMagisk = QAction("Export Library As Magisk", self)
        self.actExportLibasMagisk.triggered.connect(self.createmagiskmodule)
        self.actExportLibasMagisk.setShortcut(QKeySequence(f"Ctrl+Shift+M"))  # Cmd/Ctrl+Shift+S
        self.menuFile.addAction(self.actExportLibasMagisk)

        self.actExportADB = QAction("Export Library via ADB", self)
        self.actExportADB.triggered.connect(self.sendviaADB)
        self.actExportADB.setShortcut(QKeySequence(f"Ctrl+Shift+A"))  # Cmd/Ctrl+Shift+S
        self.menuFile.addAction(self.actExportADB)






        # --- End block (separator) ---
        self.menuFile.addSeparator()
        actExit = QAction("Exit", self)
        actExit.triggered.connect(self.close)
        self.menuFile.addAction(actExit)

        # Edit
        self.menuEdit  = mb.addMenu("Edit")
        aFind  = QAction("Find Parameter", self)
        aFind.setShortcut(QKeySequence(f"Ctrl+F"))                 # Cmd/Ctrl+F
        self.menuEdit.addAction(aFind)
        aFind.triggered.connect(self.open_find_dialog)

        # View
        self.menuView = mb.addMenu("View")

        self.actToggleTree = QAction("Collapse or Expand Tree", self)
        self.actToggleTree.setShortcut(QKeySequence("Shift+C"))
        self.actToggleTree.triggered.connect(self.on_view_toggle_tree)
        self.menuView.addAction(self.actToggleTree)

        # Show Hex
        self.actShowHex = QAction("Show Hex Viewer", self)
        self.actShowHex.setShortcut(QKeySequence(f"Ctrl+D"))
        self.actShowHex.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.actShowHex.triggered.connect(self._show_hex_shortcut)
        self.menuView.addAction(self.actShowHex)


        # Show HexEdit
        self.actShowHexEdit = QAction("Show Hex Editor", self)
        self.actShowHexEdit.setShortcut(QKeySequence(f"Ctrl+Shift+D"))
        self.actShowHexEdit.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.actShowHexEdit.triggered.connect(self._show_hexEdit_shortcut)
        self.menuView.addAction(self.actShowHexEdit)



        # --- Sort As submenu with mutually exclusive items ---
        sort_menu = self.menuView.addMenu("Sort")

        self.sortGroup = QActionGroup(self)       # the group makes the points mutually exclusive
        self.sortGroup.setExclusive(True)

        self.actSortVar1 = QAction("As Parsed", self, checkable=True)
        self.actSortVar2 = QAction("By ID", self, checkable=True)
        self.actSortVar3 = QAction("By Offset", self, checkable=True)

        #by default we enable Var1
        self.actSortVar1.setChecked(True)

        # put actions in a group
        for act in (self.actSortVar1, self.actSortVar2, self.actSortVar3):
            self.sortGroup.addAction(act)
            sort_menu.addAction(act)

        # sort mode change handler
        self.sortGroup.triggered.connect(self._on_sort_mode_changed)
             


        # Tools
        self.menuTools = mb.addMenu("Tools")

        self.actDictCreator = QAction("Parser Dictionary Creator", self)
        self.actDictCreator.setShortcut(QKeySequence(f"Shift+D"))  # Cmd/Ctrl+Shift+D
        self.actDictCreator.triggered.connect(self.on_tools_dict_creator)
        self.menuTools.addAction(self.actDictCreator)
        
        # after self.actDictCreator:
        self.menuTools.addSeparator()
        self.actUserDictCreator = QAction("User Dictionary Creator", self)
        self.actUserDictCreator.setShortcut(QKeySequence(f"Ctrl+Shift+D"))  # Cmd/Ctrl+Shift+D
        self.actUserDictCreator.setVisible(False)
        self.actUserDictCreator.triggered.connect(self._launch_user_dict_creator)
        self.menuTools.addAction(self.actUserDictCreator)

        # so that the item appears/disappears when the menu is opened
        self.menuTools.aboutToShow.connect(self._refresh_user_dict_creator_menu)
        self._refresh_user_dict_creator_menu()




        # Plugins (Plugins)
        self.menuPlugins = mb.addMenu("Plugins")
        self.builtinplug = self.menuPlugins.addMenu("Built-In Plugins")
        self.plugitem1 = QAction("Auto Tree Sorter V2", self)
        self.plugitem2 = QAction("Batch Binary Export/Import Tool", self)
        self.plugitem3 = QAction("Rows Export Tool", self)
        self.plugitem4 = QAction("Rows Import Tool", self)       

        self.plugitem1.triggered.connect(self.run_AutoformatTree2)
        self.plugitem2.triggered.connect(self.run_BatchExportImport)
        self.plugitem3.triggered.connect(self.run_RowsExport)
        self.plugitem4.triggered.connect(self.run_RowsImport)

        self.builtinplug.addAction(self.plugitem1)
        self.builtinplug.addAction(self.plugitem2)
        self.builtinplug.addAction(self.plugitem3)
        self.builtinplug.addAction(self.plugitem4)
        
        # User
        self.userplug = self.menuPlugins.addMenu("User Plugins")
        self._populate_user_plugins_menu(self.userplug)

        self.menuPlugins.addSeparator()
        actInstall = QAction("Install plugin…", self)
        actInstall.triggered.connect(self._install_user_plugin)
        self.menuPlugins.addAction(actInstall)







        # About
        self.menuAbout = mb.addMenu("More")

        aAboutpp  = QAction("About", self)
        aHelp     = QAction("Help", self)
        aDonate   = QAction("Donate", self)

        if sys.platform == "darwin":
            aAboutpp.setMenuRole(QAction.NoRole)

        # Lambda functions calling methods
        aAboutpp.triggered.connect(lambda: self.show_about())
        aHelp.triggered.connect(lambda: self.show_help())
        aDonate.triggered.connect(lambda: self.support())

        self.menuAbout.addAction(aAboutpp)
        self.menuAbout.addAction(aHelp)
        self.menuAbout.addAction(aDonate)


        # === Global shortcuts (panel actions) ===
        # === Global shortcuts (panel actions) ===
        # Binary Extract / Replace
        self.actBinExtract = QAction("Binary: Extract", self)
        self.actBinExtract.setShortcut(QKeySequence(f"Ctrl+E"))
        self.actBinExtract.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.actBinExtract.triggered.connect(lambda _checked=False: self.panel.extractBinary.emit())
        self.addAction(self.actBinExtract)

        self.actBinReplace = QAction("Binary: Replace", self)
        self.actBinReplace.setShortcut(QKeySequence(f"Ctrl+R"))
        self.actBinReplace.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.actBinReplace.triggered.connect(lambda _checked=False: self.panel.replaceBinary.emit())
        self.addAction(self.actBinReplace)

        # Dictionary Parser: Export / Import
        self.actDicExport = QAction("Dictionary: Export", self)
        self.actDicExport.setShortcut(QKeySequence(f"Ctrl+Shift+E"))
        self.actDicExport.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.actDicExport.triggered.connect(
            lambda _checked=False: self.panel.extractParam.emit(self.panel.dictionary.currentText())
        )
        self.addAction(self.actDicExport)

        self.actDicImport = QAction("Dictionary: Import", self)
        self.actDicImport.setShortcut(QKeySequence(f"Ctrl+Shift+I"))
        self.actDicImport.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.actDicImport.triggered.connect(
            lambda _checked=False: self.panel.replaceParam.emit(self.panel.dictionary.currentText())
        )
        self.addAction(self.actDicImport)

        # Checksum Fix
        self.actChecksumFix = QAction("Checksum Fix", self)
        self.actChecksumFix.setShortcut(QKeySequence(f"Ctrl+Shift+C"))
        self.actChecksumFix.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.actChecksumFix.triggered.connect(lambda _checked=False: self.panel.checksumFix.emit())
        self.addAction(self.actChecksumFix)
        # === /Global shortcuts ===













    def _update_project_actions(self):
        # Save is active only if project_path exists
        self.actSave.setEnabled(bool(self.project_path))



    def openProj(self):
        """Open .QPPProj, load the library, make a backup, import rows,
        fill the project_path, and enable Save."""
        proj_path, _ = QFileDialog.getOpenFileName(
        self, "Open project (.QPPProj)", "", "QPPProj (*.QPPProj *.qppproj)"
        )
        if not proj_path:
            return

        try:
            # 1) We get rows and the path to the library from the project
            library_path, rows = QTIAPIOpenProj.getprojectopen(proj_path)
            
            if library_path or os.path.isfile(library_path):
                _evt = QCloseEvent()
                self.closeEvent(_evt)
                if not _evt.isAccepted():
                    return
            # 2) If the path to the library is empty/broken, we will ask you to select it manually.
            if not library_path or not os.path.isfile(library_path):
                QMessageBox.information(
                    self, "Library not found",
                    "The project does not contain a valid path to the camera library.\n"
                    "Please select the corresponding .bin/.so file."
                )
                start_dir = _safe_dir_of(getattr(self, 'file_path', ''))
                lib_path_new, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select Chromatix Library (.bin/.so)",
                    start_dir,
                    "Chromatix Libraries (*.bin *.so);;QTI Libraries (*.bin);;Shared objects (*.so)"
                )
                if not lib_path_new:
                    return
                library_path = lib_path_new

            # 3) Open the library and populate the UI/model
            # set_file will automatically update the version, dictionaries, etc.; if rows are passed, it uses them.
            self.set_file(library_path, rows=rows if rows else None)

            #4) We guarantee to create a backup (if it doesn’t exist yet)
            try:
                bak = self._backup_path()
                if not os.path.exists(bak):
                    self._make_backup()
            except Exception:
                # not critical - just show the status
                self.statusBar().showMessage("Backup creation skipped (non-fatal).", 4000)

            # 5) Remember the project path and activate Save
            self.project_path = proj_path
            self._update_project_actions()   # includes self.actSave depending on project_path
            self._sync_actions_enabled()

            self.statusBar().showMessage(
                f"Project loaded: {os.path.basename(proj_path)} — {os.path.basename(library_path)}",
                5000
            )

        except Exception as e:
            QMessageBox.critical(self, "Open Project failed", str(e))




    # --- your button/slot ---
    def Import_library(self):
        """Open *.bin/*.so, parse the strings and load them into the UI."""
        start_dir = _safe_dir_of(getattr(self, 'file_path', ''))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Chromatix Library (.bin/.so)",
            start_dir,
            "Chromatix Libraries (*.bin *.so);;QTI Libraries (*.bin);;Shared objects (*.so)"
        )

        if path:
            _evt = QCloseEvent()
            self.closeEvent(_evt)
            if not _evt.isAccepted():
                return

        if not path:
            return

        # run in the background
        self.Import_library_helper(path)

    def Import_library_helper(self, path: str):
        # You can show the indicator if you wish; here's a link to the stream
        self._import_thread = _ImportWorker(path, self)
        self._import_thread.done.connect(lambda rows, err: self._import_finished(path, rows, err))
        self._import_thread.start()

    def _import_finished(self, path: str, rows, err):
        if err is not None:
            QMessageBox.critical(self, "Import failed", str(err))
            return
        if not rows:
            QMessageBox.information(self, "Import", "No parameters were extracted from the library.")
            return
        # show file and fill in the models
        self.set_file(path, rows=rows)





    def revert_library(self):
        """Restore the original library from .bak after confirmation."""
        bak = self._backup_path()
        if not os.path.exists(bak):
            QMessageBox.information(self, "Revert", "Backup file not found.")
            return
        ans = QMessageBox.question(
            self, "Revert library",
            "Do you want to restore the camera library version that was used since the last overwrite?\n"
            "Yes — restore from backup\nNo — cancel",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if ans != QMessageBox.Yes:
            return
        if self._restore_backup():
            # After a successful recovery, we will update and recreate the backup from the restored original.
            self._make_backup()
            self._update_version_and_checksum()
            QMessageBox.information(self, "Revert", "Library restored from backup.")

    def on_overwrite_library(self):
        """
        Overwrite the backup with the current version of the file.
        Before copying — if it's a .bin file — run ChkSum.checksumfix().
        """
        src = getattr(self, 'file_path', None)
        if not src or not os.path.isfile(src):
            QMessageBox.warning(self, "Save Library", "Open a library first.")
            return

        ext = os.path.splitext(src)[1].lower()
        try:
            if ext == ".bin":
                # «calculates the checksum if supported in this file»
                ChkSum.FilePathName = src
                _ = ChkSum.checksumfix()
            # Overwrite the .bak file with the updated version.
            if self._make_backup():
                QMessageBox.information(self, "Save Library", "Backup overwritten with the current file.")
        except Exception as e:
            QMessageBox.critical(self, "Save Library", f"Failed: {e}")

            
    def on_saveas_library(self):
        """
        Save Library As...
        - Take the currently open file (self.file_path).
        - Make a temporary copy.
        - If it's a .bin file, run ChkSum.checksumfix() on the COPY.
        - Save the copy to the selected path.
        The original file remains unchanged.
        """
        # 1) source
        src = getattr(self, "file_path", None)
        if not src or not os.path.isfile(src):
            QMessageBox.warning(self, "Save Library As", "Open a library first (com.qti.*.bin or .so).")
            return

        # 2) select a destination
        base = os.path.basename(src)
        dst, _ = QFileDialog.getSaveFileName(
            self, "Save Library As...", base,
            "Libraries (*.bin *.so);;BIN files (*.bin);;Shared objects (*.so);;All files (*)"
        )
        if not dst:
            return

        # 3) temporary copy of the source
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp(prefix="qti_saveas_")
        tmp_copy = os.path.join(tmpdir, os.path.basename(src))
        try:
            shutil.copy2(src, tmp_copy)

            # 4) If it's BIN, we fix the checksum on COPY
            ext = os.path.splitext(tmp_copy)[1].lower()
            if ext == ".bin":
                try:
                    # ChkSum expects the path in ChkSum.FilePathName and edits the file in place.
                    ChkSum.FilePathName = tmp_copy
                    _ = ChkSum.checksumfix()  # You can save the text to your status if needed.
                except Exception as e:
                    QMessageBox.warning(
                        self, "Checksum",
                        f"Checksum fix failed: {e}\nFile will be saved without checksum fix."
                    )

            # 5) writing the final file
            # If dst exists, we'll ask for confirmation.
            if os.path.exists(dst):
                ans = QMessageBox.question(
                    self, "Overwrite file?",
                    f"File already exists:\n{dst}\nReplace it?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if ans != QMessageBox.Yes:
                    return

            shutil.copy2(tmp_copy, dst)
            QMessageBox.information(self, "Save Library As", f"Saved:\n{dst}")

        except Exception as e:
            QMessageBox.critical(self, "Save Library As", str(e))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)




    def on_project_save(self):
        if not self.project_path:
            return self.on_project_save_as()
        rows = self._rows_raw or []
        try:
            self._save_rows_to_path(self.project_path, rows)
            QMessageBox.information(self, "Save Project", "Saved to: " + self.project_path)
        except Exception as e:
            QMessageBox.critical(self, "Save Project", "Save failed: " + str(e))

    def on_project_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save project as", "", "QPPProj (*.QPPProj)")
        if not path:
            return

        clean = re.sub(r'(?i)\.qppproj$', '', path.strip().rstrip('. '))
        path = str(Path(clean).with_suffix(".QPPProj"))

        rows = self._rows_raw or []
        try:
            self._save_rows_to_path(path, rows)
            self.project_path = path
            self._update_project_actions()
            self._sync_actions_enabled()
            QMessageBox.information(self, "Save Project", "Saved to: " + path)
        except Exception as e:
            QMessageBox.critical(self, "Save Project", "Save failed: " + str(e))



    def createmagiskmodule(self):
        """
            Builds the Magisk module from the current .so/.bin:
            • source copy -> temp
            • applies self._patches to the copy (if any)
            • MagiskExport.FilePath = temp_copy; MagiskExport.run()
            • clears temp after completion
            This assumes that MagiskExport is already imported at the module level.
        """
        # ---- 1) Source ----
        src = None
        for cand in (getattr(self, "_driver_path", None), getattr(self, "file_path", None)):
            if cand and os.path.isfile(cand):
                src = cand
                break
        if not src:
            src, _ = QFileDialog.getOpenFileName(
                self, "Select driver/library (.so or .bin)", "",
                "Libraries/Binaries (*.so *.bin);;Shared Objects (*.so);;BIN files (*.bin);;All files (*)"
            )
            if not src:
                return

        patches = getattr(self, "_patches", []) or []

        # ---- 2) Temporary copy ----
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp(prefix="qti_magisk_")
        base_name = os.path.basename(src)
        temp_so_path = os.path.join(tmpdir, base_name)

        try:
            shutil.copy2(src, temp_so_path)

            # ---- 3) Patches to the copy (optional) ----
            if patches:
                with open(temp_so_path, "r+b") as f:
                    for p in patches:
                        try:
                            off = int(p.get("offset", -1))
                            dat = p.get("data", None)
                            if off >= 0 and isinstance(dat, (bytes, bytearray)):
                                f.seek(off); f.write(dat)
                        except Exception:
                            continue


            # ---- 3.5) If it's .bin, fix the checksum for the temporary copy (in-place)
            if os.path.splitext(temp_so_path)[1].lower() == ".bin":
                try:
                    ChkSum.FilePathName = temp_so_path
                    ChkSum.checksumfix()       # edits the file in place
                except Exception as e:
                    try:
                        QMessageBox.warning(
                            self, "Checksum",
                            f"Checksum fix failed: {e}\nModule will be built without checksum fix."
                        )
                    except Exception:
                        print(f"[Checksum] fix failed for {temp_so_path}: {e}")


            # ---- 4) Launching the exporter ----
            if not hasattr(MagiskExport, "run"):
                QMessageBox.warning(self, "Magisk Export", "MagiskExport.run() is not available.")
                return

            prev_fp = getattr(MagiskExport, "FilePath", None)
            try:
                MagiskExport.FilePath = temp_so_path  # exactly a COPY in the temporary folder
                MagiskExport.run()                    # The exporter will show the paths window and build the ZIP
            finally:
                try:
                    MagiskExport.FilePath = prev_fp
                except Exception:
                    pass

            # ---- 5) Completion ----
            #QMessageBox.information(self, "Magisk Module", "Magisk module successfully built.")
            try:
                if hasattr(self, "_patches"):
                    self._patches.clear()  # patches were applied only to the copy
            except Exception:
                pass

        except Exception as e:
            QMessageBox.critical(self, "Magisk Export Failed", str(e))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)






























































    def sendviaADB(self):
        """
        Sending a library to the device via ADB with protection against the "wrong" library.
        Logic:
        • If the current file is open: library_local_path = self.file_path.
        • If the same local path has already been sent, use the saved adb_remote_path.
        • If the path is different, adb_remote_path = None (let ADB_API ask/decide for itself).
        • After ADB_API, save both winners in self._adb_last_local/self._adb_last_remote.
        """
        cur = getattr(self, "file_path", None)
        if not cur or not os.path.isfile(cur):
            # Allow manual selection
            cur, _ = QFileDialog.getOpenFileName(
                self, "Select library to export via ADB", "",
                "Libraries/Binaries (*.so *.bin);;All files (*)"
            )
            if not cur:
                return

        # Restore a previously known pair
        last_local  = getattr(self, "_adb_last_local", None)
        last_remote = getattr(self, "_adb_last_remote", None)

        # Substitute the remote path only if the local one is an exact match
        adb_remote_path = last_remote if (last_local and os.path.abspath(last_local) == os.path.abspath(cur)) else None

        # >>> INSERT: Fix checksum for .bin (in-place)
        if os.path.splitext(cur)[1].lower() == ".bin":
            try:
                ChkSum.FilePathName = cur
                ChkSum.checksumfix() # Fixes the file in-place
            except Exception as e:
                QMessageBox.warning(self, "Checksum",
                                    f"Checksum fix failed: {e}\nFile will be sent without checksum fix.")

        try:
            ADBRETURN = ADBEX.ADB_API(cur, adb_remote_path, parent=self)
            # Expect a tuple (local, remote), but try to be flexible
            if isinstance(ADBRETURN, (list, tuple)) and len(ADBRETURN) >= 2:
                library_local_path, adb_remote_path = ADBRETURN[0], ADBRETURN[1]
            else:
                # Fallback: if the API returned only the remote path
                library_local_path, adb_remote_path = cur, ADBRETURN if isinstance(ADBRETURN, str) else None

            # Save "memory" for the next call
            self._adb_last_local  = library_local_path
            self._adb_last_remote = adb_remote_path

            if adb_remote_path:
                self.statusBar().showMessage(f"ADB: exported to {adb_remote_path}", 5000)
            else:
                self.statusBar().showMessage("ADB: export completed.", 4000)

            # Bonus: If the same file that was open was exported, consider the path confirmed
            if hasattr(self, "file_path") and os.path.abspath(self.file_path) == os.path.abspath(library_local_path):
                # Everything is ok, the "correct" path is confirmed
                pass

        except Exception as e:
            QMessageBox.critical(self, "ADB Export", f"Failed:\n{e}")



    # --------------------------- Close Event --------------------------------

    def closeEvent(self, e):
        # If there is no file or no backup — Close immediately
        src = getattr(self, 'file_path', None)
        bak = self._backup_path()
        if not (src and os.path.isfile(src) and os.path.exists(bak)):
            e.accept()
            return

        try:
            different = _files_differ(src, bak)
        except Exception:
            different = True

        if not different:
            # Nothing has changed - you can delete the backup or keep it (it's your choice).
            # I suggest keeping the .bak file - it will come in handy between sessions.
            self._delete_backup()
            e.accept()
            return

        # There are changes - ask.
        # Buttons: Keep (keep the working library), Revert (discard changes), Cancel
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Unsaved changes in library")
        msg.setText(
            "The working library differs from the backup.\n\n"
            "Do you want to keep the modified library, revert to the original, or cancel?"
        )
        keep_btn   = msg.addButton("Keep changes (overwrite backup)", QMessageBox.YesRole)
        revert_btn = msg.addButton("Revert changes (restore backup)", QMessageBox.NoRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.setDefaultButton(cancel_btn)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked is keep_btn:
            # "Overwrite the working library" as you described = leave as is, delete the backup, and close.
            # (if you want to keep a new backup, replace it with self._make_backup())
            self._delete_backup()
            e.accept()
        elif clicked is revert_btn:
            # Restore .bak → original and delete the backup; close
            if self._restore_backup():
                self._delete_backup()
                e.accept()
            else:
                e.ignore()
        else:
            # Cancel
            e.ignore()










    def _save_rows_to_path(self, path: str, rows: list):
        txt = self.rows_to_text(rows)
        
        parser = QPARParser()

        raw = txt.encode("utf-8", errors="ignore")
        src_bin = getattr(self, 'file_path', "") or "" # path to an open .bin file, if any

        # support both versions of process_data:
        # - new: returns (compressed_bytes, bin_path)
        # - old: returns compressed_bytes
        try:
            result = parser.process_data(raw, src_bin) # new signature
        except TypeError:
            # old signature without the second argument
            result = parser.process_data(raw)

        if isinstance(result, tuple) and len(result) == 2:
            data_out, embedded_bin_path = result
            # optional: you can show which path was embedded in the status
            self.statusBar().showMessage(f"Project saved (bin: {embedded_bin_path})", 3000)
        else:
            data_out = result

        with open(path, "wb") as f:
            f.write(data_out)


    def rows_to_text(self, rows: list) -> str:
        """Converting source rows to text for packing:
        if the element is a list/tuple => concatenate, separated by commas; otherwise, take as yes."""
        out = []
        for r in rows or []:
            if isinstance(r, (list, tuple)):
                out.append(",".join(str(x) for x in r))
            else:
                out.append(str(r))
        return "\n".join(out)


    # ----------------------------- Sort Data --------------------------------
    def _on_sort_mode_changed(self, action: QAction):
        mode = action.text()
        self._apply_sort_mode(mode)
        self._populate_table_from_model()



    def _apply_sort_mode(self, mode: str = None):
        if mode:
            self._sort_mode = mode
        n = len(self.rows_model)
        if n == 0:
            self.view_order = []
            self.model_to_view = {}
            return

        if self._sort_mode == "By ID":
            # None moved to the end via a tuple key
            self.view_order = sorted(
                range(n),
                key=lambda i: ((self.rows_model[i]["id_num"] is None),
                               self.rows_model[i]["id_num"] if self.rows_model[i]["id_num"] is not None else 0,
                            self.rows_model[i]["orig_index"]) # stability based on the original order
            )
        elif self._sort_mode == "By Offset":
            self.view_order = sorted(
                range(n),
                key=lambda i: ((self.rows_model[i]["offset"] is None),
                               self.rows_model[i]["offset"] if self.rows_model[i]["offset"] is not None else 0,
                               self.rows_model[i]["orig_index"])
            )
        else:  # "As Parsed"
            self.view_order = sorted(range(n), key=lambda i: self.rows_model[i]["orig_index"])

        # Reverse map for quick transition model -> view
        self.model_to_view = {m_idx: v_idx for v_idx, m_idx in enumerate(self.view_order)}

    def _view_to_model_index(self, view_row: int) -> int:
        if 0 <= view_row < len(self.view_order):
            return self.view_order[view_row]
        return view_row # fallback

    def _model_to_view_index(self, model_row: int) -> int:
        return self.model_to_view.get(model_row, model_row)


    # ----------------------------- Built In Plugins --------------------------------

    def run_AutoformatTree2(self):
        self.on_trick_triggered(BuiltIn_AutoformatTree)

    def run_BatchExportImport(self):
        self.on_trick_triggered(BuiltIn_BatchExportImport)
        
    def run_RowsExport(self):
        self.on_trick_triggered(BuiltIn_RowsExport)

    def run_RowsImport(self):
        self.on_trick_triggered(BuiltIn_RowsImport)        
        
    # ----------------------------- Hex Viewer and Editor --------------------------------



    def _show_hex_shortcut(self):
        entry = self._get_current_entry()
        if entry:
            self._open_hex_for_entry(entry)


    def _show_hexEdit_shortcut(self):
        entry = self._get_current_entry()
        if entry:
            self._open_hexedit_for_entry(entry)


    # ----------------------------- Built In Plugins --------------------------------


    def _sync_actions_enabled(self):
        # Save — as before, based on the presence of project_path
        self.actSave.setEnabled(bool(self.project_path))

        # Dictionary Export/Import — like buttons
        bad = self.panel.dictionary.currentText() in ("Not selected", "Import *.Qdict", None, "")
        self.actDicExport.setEnabled(not bad)
        self.actDicImport.setEnabled(not bad)






    # --------------------------------------------- Qdict for Export/Import --------------------------------


    def _get_dict_module(self):
        """Returns the active dictionary module: custom or built-in Qdict."""
        return getattr(self, "_custom_dict_mod", None) or Qdict

    def _update_dict_panel_title(self):
        try:
            title = "Dictionary Parser (Custom)" if getattr(self, "_custom_dict_mod", None) \
                    else "Dictionary Parser (Built-in)"
            if hasattr(self.panel, "grpDict"):
                self.panel.grpDict.setTitle(title)
        except Exception:
            pass



    def _get_selected_dict_path(self, dict_name: str):
        if not dict_name or dict_name in ("Not selected", "Import *.Qdict"):
            return None
        dd = self._dict_dir()
        candidate = os.path.join(dd, dict_name)
        return candidate if os.path.exists(candidate) else None

    def _coerce_to_bytes(self, ret):
        """Trying to convert the result of Qdict.run() to bytes."""
        if ret is None:
            return None
        if isinstance(ret, (bytes, bytearray)):
            return bytes(ret)
        if isinstance(ret, str):
            s = ret.strip()
            # First, try hex → bytes
            try:
                return bytes.fromhex(s)
            except Exception:
                # If this isn't hex, consider it invalid for binary
                return None
        if isinstance(ret, list) and all(isinstance(x, int) and 0 <= x <= 255 for x in ret):
            return bytes(ret)
        return None

    def _prepare_dict_context(self, mod, status: str, dict_path: str, entry: dict, data: bytes, hex_str: str):
        """Fill in the expected fields in the selected dictionary module (custom or built-in) + legacy bridge in _QTIHex."""
        try:
            # main fields of the dictionary itself
            setattr(mod, "QTIDicStatus",           status)
            setattr(mod, "QTISelectedDicFilePath", dict_path or "")
            setattr(mod, "QTISelectedID",          entry.get("id_disp", ""))
            setattr(mod, "QTISelectedIDRaw",       entry.get("id_raw", ""))
            setattr(mod, "QTISelectedName",        entry.get("name", ""))
            setattr(mod, "QTISelectedHex",         hex_str or "")
            setattr(mod, "QTISelectedFilePath",    getattr(self, 'file_path', "") or "")
            setattr(mod, "QTISelectedOffset",      entry.get("offset", 0) or 0)
            setattr(mod, "QTISelectedLength",      entry.get("length", 0) or 0)
            setattr(mod, "QTISelectedVersion",     getattr(self, "ver_txt", ""))

            try:
                setattr(mod, "QTISelectedBuffer", data)
            except Exception:
                pass

            # Legacy bridge — in case the module looks in _QTIHex
            try:
                QTIHex.QTIDicBin           = data
                QTIHex.QTIDicHex           = hex_str
                QTIHex.QTISelectedID       = entry.get("id_disp", "")
                QTIHex.QTISelectedIDRaw    = entry.get("id_raw", "")
                QTIHex.QTISelectedName     = entry.get("name", "")
                QTIHex.QTISelectedFilePath = getattr(self, 'file_path', "") or ""
                QTIHex.QTISelectedOffset   = entry.get("offset", 0) or 0
                QTIHex.QTISelectedLength   = entry.get("length", 0) or 0
                QTIHex.QTISelectedVersion  = getattr(self, "ver_txt", "")
            except Exception:
                pass
        except Exception:
            pass

    def _run_dict(self, mod):
        """Running the selected dictionary module."""
        if hasattr(mod, "run") and callable(mod.run):
            return mod.run(parent=self)
        if hasattr(mod, "launch") and callable(mod.launch):
            return mod.launch(parent=self)
        QMessageBox.information(self, "Dictionary Parser", "Dictionary module loaded, but no run()/launch() found.")
        return None




    # --------------------------------------------- Qdict for Export/Import --------------------------------




    # ----------------------------- User Plugins --------------------------------

    def _populate_user_plugins_menu(self, menu):
        menu.clear()
        d = user_plugins_dir()
        entries = []
        try:
            entries = sorted(os.listdir(d))
        except Exception:
            pass

        any_found = False
        for fname in entries:
            if fname.startswith("_"):
                continue
            low = fname.lower()
            if not low.endswith((".py", ".pyd", ".so", ".dylib", ".dll")):
                continue
            any_found = True

            full = os.path.join(d, fname)
            base = fname.split('.')[0]

            # Protect against name conflicts with built-in
            if base in ("AutoformatTree2", "BatchExportImport", "RowsExport", "RowsImport"):
                act = QAction(f"{fname} (conflict with built-in)", self)
                act.setEnabled(False)
                menu.addAction(act)
                continue

            try:
                mod = load_plugin_from_file(full)
                title = getattr(mod, "TRIKSMODULENAME", base)
                act = QAction(title, self)
                act.triggered.connect(lambda _=False, m=mod: self.on_trick_triggered(m))
                menu.addAction(act)
            except Exception as e:
                act = QAction(f"{fname} (error)", self)
                act.setEnabled(False)
                act.setToolTip(str(e))
                menu.addAction(act)

        if not any_found:
            a = QAction("(no user plugins)", self)
            a.setEnabled(False)
            menu.addAction(a)

    def _install_user_plugin(self):
        d = user_plugins_dir()
        src, _ = QFileDialog.getOpenFileName(
            self, "Install plugin", "",
            "Plugins (*.pyd *.so *.dylib *.dll *.py)"
        )
        if not src:
            return
        dst = os.path.join(d, os.path.basename(src))
        if os.path.exists(dst):
            if QMessageBox.question(
                self, "Overwrite?",
                f"{os.path.basename(dst)} exists. Replace?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            ) != QMessageBox.Yes:
                return
        try:
            shutil.copy2(src, dst)
            self._populate_user_plugins_menu(self.userplug)
            QMessageBox.information(self, "Install plugin", f"Installed to:\n{dst}")
        except Exception as e:
            QMessageBox.critical(self, "Install plugin", str(e))


    # ----------------------------- User Plugins --------------------------------



    def _normalize_plugin_result(self, res):
        if res is None:
            return []
        if isinstance(res, str):
            return [ln for ln in res.splitlines() if ln.strip()]
        if isinstance(res, list):
            return res
        return []

    # inside MainWindow
    def _get_selected_orig_row_index(self) -> int:
        """Returns the row index in the ORIGINAL rows list (_rows_raw),
        corresponding to the current selection in the table or tree.
        If nothing is selected, returns -1.
        """
        # if the table is active, navigate view->model and get the orig_index
        if self.tabs.currentWidget() is self.table:
            vrow = self.table.currentRow()
            if 0 <= vrow < len(self.view_order):
                mrow = self._view_to_model_index(vrow)
                return self.rows_model[mrow].get("orig_index", -1)

        # if the tree tab is active, the model index is already stored there
        if self.tabs.currentWidget() is self.tree:
            item = self.tree.currentItem()
            if item:
                mrow = item.data(0, Qt.UserRole + 1) # model index
                if mrow is not None and 0 <= mrow < len(self.rows_model):
                    return self.rows_model[mrow].get("orig_index", -1)

        # fallback — try the current table row regardless of the active tab
        vrow = self.table.currentRow()
        if 0 <= vrow < len(self.view_order):
            mrow = self._view_to_model_index(vrow)
            return self.rows_model[mrow].get("orig_index", -1)

        return -1



    def on_trick_triggered(self, mod):
        run_fn = getattr(mod, "run", None)
        if not callable(run_fn):
            QMessageBox.warning(self, "Plugins", f"Module '{mod.__name__}' has no run(file_path, rows)")
            return

        self._set_plugins_enabled(False)
        self.statusBar().showMessage("Running plugin…")

        run_in_worker = bool(
            getattr(mod, "RUN_IN_WORKER", False) or
            getattr(mod, "HEADLESS", False) or
            getattr(mod, "NO_UI", False)
        )

        self._plugin_update_policy = getattr(mod, 'UPDATE_ROWS', None)
        self._plugin_name = getattr(mod, 'TRIKSMODULENAME', mod.__name__)

        safe_rows = _normalize_rows_for_plugin(self._rows_raw or [])
        file_path = getattr(self, 'file_path', "")

        # >>> NEW: pass the index of the selected ORIGINAL row, if the plugin supports it
        if hasattr(mod, "CURRENTSELECTED_ROW"):
            try:
                sel_idx0 = self._get_selected_orig_row_index() # 0-based or -1 (no selection)
                sel_idx1 = (sel_idx0 + 1) if sel_idx0 >= 0 else 0 # 1-based or 0 (no choice)
                sel_idx  = sel_idx1 if USETABLEINDEXASONE else sel_idx0
                setattr(mod, "CURRENTSELECTED_ROW", int(sel_idx))
            except Exception as e:
                # don't interfere with launch if something goes wrong
                pass
        # <<< NEW


        # >>> Chromaticix version for plugins
        try:
            # Take from self.ver_txt with a fallback to the global one
            cur_ver = getattr(self, "ver_txt", None) or CURRENT_CHROMATIX_VER or ""
            # Strictly ASCII
            try:
                cur_ver = cur_ver.encode("ascii", errors="ignore").decode("ascii").strip()
            except Exception:
                cur_ver = str(cur_ver).strip()

            # If the plugin explicitly supports CURRENT_CHROMATIX_VER, pass it through
            if hasattr(mod, "CURRENT_CHROMATIX_VER"):
                setattr(mod, "CURRENT_CHROMATIX_VER", cur_ver)

            # Just in case, duplicate it in already used fields (often more convenient for plugins)
            setattr(mod, "QTISelectedVersion", cur_ver) # many of your modules already read this
        except Exception:
            pass
        # <<< Chromaticix version for Plugins




        if not run_in_worker:
            try:
                res = run_fn(file_path, safe_rows)
                out = self._normalize_plugin_result(res)
                self._on_plugin_finished(out)
            except Exception:
                self._on_plugin_failed(traceback.format_exc())
            finally:
                self._set_plugins_enabled(True)
            return

        # === BACKGROUND RUN (headless only) ===
        self._plugin_progress = QProgressDialog("Running plugin…", None, 0, 0, self)
        self._plugin_progress.setCancelButton(None)
        self._plugin_progress.setWindowModality(Qt.WindowModal)
        self._plugin_progress.setMinimumDuration(0)
        self._plugin_progress.show()

        self._plugin_thread = QThread(self)
        self._plugin_worker = PluginWorker(run_fn, file_path, safe_rows)
        self._plugin_worker.moveToThread(self._plugin_thread)

        self._plugin_thread.started.connect(self._plugin_worker.run)
        self._plugin_worker.finished.connect(self._on_plugin_finished)
        self._plugin_worker.failed.connect(self._on_plugin_failed)

        self._plugin_worker.finished.connect(self._plugin_thread.quit)
        self._plugin_worker.failed.connect(self._plugin_thread.quit)
        self._plugin_worker.finished.connect(self._plugin_worker.deleteLater)
        self._plugin_worker.failed.connect(self._plugin_worker.deleteLater)
        self._plugin_thread.finished.connect(self._plugin_thread.deleteLater)

        self._plugin_thread.start()




    def _on_plugin_finished(self, new_rows: list):
        try:
            if self._plugin_progress:
                self._plugin_progress.close()
        except Exception:
            pass
        self._set_plugins_enabled(True)

        flag = getattr(self, '_plugin_update_policy', None)

        # "as before" — apply only if a NON-EMPTY list is returned
        def behave_as_before():
            if isinstance(new_rows, list) and len(new_rows) > 0:
                self._rows_raw = new_rows
                self._populate_from_rows(new_rows)
                QMessageBox.information(self, "Plugin", "Applied.")
            else:
                self.statusBar().showMessage("Plugin finished — no changes.", 4000)

        try:
            if flag == 0:
                # Plugin asks not to update views
                self.statusBar().showMessage("Plugin finished — update suppressed by plugin (UPDATE_ROWS=0).", 5000)
            else:
                # flag is None (missing) OR flag == 1 → behave "as before"
                behave_as_before()
        finally:
            # clear state
            self._plugin_update_policy = None
            self._plugin_name = None


    def _on_plugin_failed(self, err_text: str):
        try:
            if self._plugin_progress:
                self._plugin_progress.close()
        except Exception:
            pass
        self._set_plugins_enabled(True)
        QMessageBox.critical(self, "Plugin", "Error:\n" + err_text)
        self._plugin_update_policy = None
        self._plugin_name = None


    def _set_plugins_enabled(self, enabled: bool):
        try:
            self.menuPlugins.setEnabled(enabled)
        except Exception:
            pass



    # ───────────────────────── Backup helpers ─────────────────────────────
    def _backup_path(self) -> str:
        return (getattr(self, 'file_path', '') or '') + ".bak"

    def _make_backup(self) -> bool:
        """Creates/overwrites .bak from the current file and marks it as hidden (where possible)."""
        src = getattr(self, 'file_path', None)
        if not src or not os.path.isfile(src):
            return False
        bak = self._backup_path()
        try:
            shutil.copy2(src, bak)
            _set_hidden_attr(bak)
            return True
        except Exception as e:
            self.statusBar().showMessage("Backup failed: " + str(e), 6000)
            return False



    def _restore_backup(self) -> bool:
        """Overwrites the working library with the contents of .bak without transferring attributes."""
        src = self._backup_path() # .bak (hidden)
        dst = getattr(self, 'file_path', None) # working file
        if not (dst and os.path.exists(src)):
            return False
        try:
            # read bytes from .bak
            with open(src, "rb") as f:
                data = f.read()

            # carefully write to the working file through a temporary one (the 'hidden' attribute is not will move)
            _atomic_write_bytes(dst, data)

            # guaranteed to remove hidden from the working file (in case it's stuck somewhere)
            _clear_hidden_attr(dst)

            return True
        except Exception as e:
            QMessageBox.critical(self, "Restore", "Restore failed: " + str(e))
            return False


    def _delete_backup(self):
        bak = self._backup_path()
        try:
            if os.path.exists(bak):
                os.chmod(bak, stat.S_IWRITE | stat.S_IREAD)
                os.remove(bak)
        except Exception:
            pass




    # --------------------------- File / Data logic -------------------------


    def _load_modules_from_bin(self):
        """
        If the file is open, try to get rows from it (universal for .bin and .so)
        via QTIAPIImportLib.getrowsfromlib(self.file_path).
        """
        path = getattr(self, 'file_path', None)
        if not path or not os.path.isfile(path):
            return
        try:
            rows = QTIAPIImportLib.getrowsfromlib(path)
            if rows:
                self._populate_from_rows(rows)
                self._rows_raw = rows
            else:
                self.statusBar().showMessage("No parameters parsed from the library.", 4000)
        except Exception as e:
            self.statusBar().showMessage("Parse failed: " + str(e), 6000)

    def set_file(self, path: str, rows: list = None):
        self.file_path = path
        stem = os.path.splitext(os.path.basename(path))[0]
        self.panel.titleLabel.setText(stem)
        self._update_version_and_checksum()
        if rows is not None:
            self._populate_from_rows(rows)
        else:
            self._load_modules_from_bin()
        self._reload_dictionary_list()
        # ← AFTER loading and filling
        self.check_onloading()



    def check_onloading(self):
        """If the .bak already exists, we'll ask what to do (it might have closed incorrectly last time)."""
        bak = self._backup_path()
        if os.path.exists(bak):
            ans = QMessageBox.question(
                self, "Previous backup detected",
                "It looks like the app didn’t close properly last time.\n"
                "Do you want to restore the original version (from backup) or continue with the current edit?\n\n"
                "Yes — Restore original from backup (keep previous backup)\n"
                "No — Continue with current file (remove old backup and create a new one)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if ans == QMessageBox.Yes:
                # Use the old .bak as a "reference" and DO NOT overwrite it
                # Don't touch the original, just continue working and leave the .bak in place
                self.statusBar().showMessage("Backup kept. You can revert anytime via File → Revert Changes.", 5000)
            else:
                # Delete the old one and create a new backup based on the current file state
                self._delete_backup()
                if self._make_backup():
                    self.statusBar().showMessage("New backup created.", 4000)
        else:
            # No backup - create one
            if self._make_backup():
                self.statusBar().showMessage("Backup created.", 3000)




    # ----------------------------- Model & parsing --------------------------



# ----------------------------- Populate views (ASYNC) ---------------------------

    def _cancel_async_build(self):
        self._build_epoch = getattr(self, "_build_epoch", 0) + 1
        # Stop any past timers/progress
        for name in ("_table_timer", "_tree_timer"):
            t = getattr(self, name, None)
            if t:
                t.stop()
        for name in ("_table_progress", "_tree_progress"):
            d = getattr(self, name, None)
            if d:
                try: d.close()
                except Exception: pass

    def _populate_table_from_model(self):
        self._building_table = True
        self._build_epoch = getattr(self, "_build_epoch", 0) + 1
        epoch = self._build_epoch

        self.table.blockSignals(True)
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)
        self.table.clearContents()

        total = len(self.rows_model)
        self.table.setRowCount(total)
        self._tbl_idx = 0

        def add_chunk():
            if epoch != self._build_epoch:
                return
            start = self._tbl_idx
            end = min(start + self._TABLE_CHUNK, total)
            for vrow in range(start, end):
                mrow = self.view_order[vrow] # MODEL index
                entry = self.rows_model[mrow]

                id_item = QTableWidgetItem(entry["id_disp"])
                id_item.setData(Qt.UserRole, entry["id_raw"])
                id_item.setData(Qt.UserRole + 10, mrow) # save Model index

                name_item = QTableWidgetItem(entry["name"])
                name_item.setData(Qt.UserRole, entry["id_raw"])
                name_item.setData(Qt.UserRole + 1, entry["tags"].get("namemark", ""))
                name_item.setData(Qt.UserRole + 2, entry["tags"].get("data", ""))
                name_item.setData(Qt.UserRole + 10, mrow)

                off_item = QTableWidgetItem(entry["offset_str"])
                off_item.setData(Qt.UserRole, entry["id_raw"])
                off_item.setData(Qt.UserRole + 10, mrow)

                len_item = QTableWidgetItem(self._fmt_hex_min(entry["length_str"]))
                len_item.setData(Qt.UserRole, entry["id_raw"])
                len_item.setData(Qt.UserRole + 10, mrow)

                self.table.setItem(vrow, 0, id_item)
                self.table.setItem(vrow, 1, name_item)
                self.table.setItem(vrow, 2, off_item)
                self.table.setItem(vrow, 3, len_item)

                col = entry["tags"].get("namecol")
                if isinstance(col, QColor) and col.isValid():
                    br = QBrush(col)
                    for c in range(4):
                        it = self.table.item(vrow, c)
                        if it: it.setForeground(br)

            self._tbl_idx = end
            if end < total:
                self.statusBar().showMessage(f"Building table… {end}/{total}")
                QTimer.singleShot(0, add_chunk)
            else:
                self.table.blockSignals(False)
                self.table.setSortingEnabled(False)
                self.table.setUpdatesEnabled(True)
                self._building_table = False
                if total:
                    # select the first row in the current order
                    self.table.selectRow(0)
                    self._update_selected_label()
                QTimer.singleShot(0, self._populate_tree_from_model)
                self.statusBar().showMessage("Table ready", 1500)

        QTimer.singleShot(0, add_chunk)



    def _populate_tree_from_model(self):
        self.row_to_tree_item = {}
        self._build_epoch = getattr(self, "_build_epoch", 0) + 1
        epoch = self._build_epoch

        self.tree.blockSignals(True)
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        self.id_to_tree_item.clear()

        total = len(self.rows_model)
        self._tree_idx = 0
        self._tree_current_parent = None

        def add_chunk():
            if epoch != self._build_epoch:
                return
            start = self._tree_idx
            end = min(start + self._TREE_CHUNK, total)

            for vrow in range(start, end):
                mrow = self.view_order[vrow]
                entry = self.rows_model[mrow]
                label = f'{entry["name"]} ({entry["id_disp"]})'
                item = QTreeWidgetItem([label])
                item.setData(0, Qt.UserRole, entry["id_raw"])
                item.setData(0, Qt.UserRole + 1, mrow) # IMPORTANT: Model index

                col = entry["tags"].get("namecol")
                if isinstance(col, QColor) and col.isValid():
                    item.setForeground(0, QBrush(col))

                if entry["tags"].get("dictionary", False):
                    self.tree.addTopLevelItem(item)
                    self._tree_current_parent = item
                elif entry["tags"].get("parent", False) and self._tree_current_parent is not None:
                    self._tree_current_parent.addChild(item)
                else:
                    self.tree.addTopLevelItem(item)

                self.id_to_tree_item[entry["id_raw"]] = item
                self.row_to_tree_item[mrow] = item # map MODEL -> item

            self._tree_idx = end
            if end < total:
                self.statusBar().showMessage(f"Building tree… {end}/{total}")
                QTimer.singleShot(0, add_chunk)
            else:
                self.tree.expandToDepth(0)
                self.tree.blockSignals(False)
                self.tree.setUpdatesEnabled(True)
                self.statusBar().showMessage("Tree ready", 1500)

        QTimer.singleShot(0, add_chunk)








    
    def _populate_from_rows(self, rows):
        self._cancel_async_build() # ← add
        """
        Fills the model and both views (table + tree).
        Row/record format: 4 columns: ID, Name (with tags), Offset, Length.
        Tags are at the beginning of the Name field.
        """
        parsed, skipped = [], 0
        for line in rows or []:
            rec, too_many = self._parse_row(line)
            if rec is None:
                if too_many:
                    skipped += 1
                continue
            parsed.append(rec)

        # Build the model
        self._build_rows_model(parsed)

        # Populate the table and tree
        self._populate_table_from_model()
        # self._populate_tree_from_model() # REMOVE

        self._rows_raw = rows # save the original rows for saving/trixes
        
        if skipped:
            QMessageBox.information(
                self, "Experimental notice",
                "This is an experimental tool; some parameters could not be loaded. "
                "Please contact the community and share your library sample."
            )

    def _parse_row(self, line):
        # returns ((id_str, name, offset_str, length_str), too_many_flag)
        if isinstance(line, (list, tuple)):
            cols = [str(c).strip() for c in line]
        else:
            cols = re.split(r'[,;\t]+', str(line).strip())
        if len(cols) > 4:
            return None, True
        if len(cols) < 4:
            return None, False
        mid, name, off, length = cols[0].strip(), cols[1].strip(), cols[2].strip(), cols[3].strip()
        return (mid, name, off, length), False

    def _build_rows_model(self, items):
        self.rows_model.clear()
        self.id_to_row_index.clear()
        self.id_to_tree_item.clear()

        for idx, (mid, name_field, off, length) in enumerate(items):
            clean_name, tags = self._parse_name_and_tags(name_field)
            id_num = self._parse_int(mid)
            off_num = self._parse_int(off)

            entry = {
                "orig_index": idx,
                "id_raw": str(mid).strip(),
                "id_disp": self._fmt_hex_min(mid),
                "id_num": id_num,
                "name": clean_name,
                "offset_str": str(off).strip(),
                "length_str": str(length).strip(),
                "offset": off_num,
                "length": self._parse_int(length),
                "tags": tags,
            }
            self.rows_model.append(entry)
            if entry["id_raw"] not in self.id_to_row_index:
                self.id_to_row_index[entry["id_raw"]] = idx

        # ← here, ONCE
        self._apply_sort_mode()



    def _parse_name_and_tags(self, name_field: str):
        """
        Parsing the tag prefix at the beginning of the Name field and returning (clean_name, tags_dict).
        Supported tags:
          [dictionary]  -> tags['dictionary']=True
          [parent]      -> tags['parent']=True
          [namecol=#a36864] -> tags['namecol']=QColor(...)
          [namemark="..."]  -> tags['namemark']="..."
          [data="..."]      -> tags['data']="..."
        All other tags are ignored. The tags themselves are excluded from display.
        """
        s = name_field if isinstance(name_field, str) else str(name_field)
        # strip prefixes like "[...][...]" (any number)
        prefix_match = re.match(r'^\s*(?:\[[^\]]*\]\s*)*', s)
        prefix = prefix_match.group(0) if prefix_match else ""
        rest = s[len(prefix):].strip()

        tags_list = re.findall(r'\[([^\]]*)\]', prefix)
        tags = {
            "dictionary": False,
            "parent": False,
            "namecol": None,   # QColor or None
            "namemark": "",
            "data": ""
        }

        for t in tags_list:
            t_str = t.strip()
            low = t_str.lower()

            if low == "dictionary":
                tags["dictionary"] = True
                continue
            if low == "parent":
                tags["parent"] = True
                continue

            # namecol
            m_col = re.match(r'(?i)^namecol\s*=\s*(#[0-9A-Fa-f]{3,8})\s*$', t_str)
            if m_col:
                try:
                    color = QColor(m_col.group(1))
                    if color.isValid():
                        tags["namecol"] = color
                except Exception:
                    pass
                continue

            # namemark="..."`
            m_mark = re.match(r'(?i)^namemark\s*=\s*"(.*)"\s*$', t_str)
            if m_mark:
                tags["namemark"] = m_mark.group(1)
                continue

            # data="..."`
            m_data = re.match(r'(?i)^data\s*=\s*"(.*)"\s*$', t_str)
            if m_data:
                tags["data"] = m_data.group(1)
                continue

            # ignore other tags

        return rest, tags

    # ----------------------------- Populate views ---------------------------
  

    # ------------------------------- Helpers --------------------------------
    def _fmt_hex_min(self, s: str) -> str:
        """
        Returns a string like 0x... without leading zeros if the original value
        was HEX (e.g. '00000020' or '0x00000020').
        Otherwise, returns the original string.
        """
        if not isinstance(s, str):
            s = str(s)
        ss = s.strip()
        if ss.lower().startswith('0x'):
            try:
                return f"0x{int(ss, 16):X}"
            except Exception:
                return ss
        if re.fullmatch(r'[0-9A-Fa-f]+', ss) and ss.startswith('0'):
            try:
                return f"0x{int(ss, 16):X}"
            except Exception:
                return ss
        return ss

    def _parse_int(self, text):
        s = str(text).strip()
        try:
            return int(s, 0)  # supports '0x..' or decimal
        except Exception:
            try:
                return int(s, 16)
            except Exception:
                return None

    def _update_selected_label(self):
        row = self.table.currentRow()
        name = "{thenameofselectedrow}" if row < 0 else (
            self.table.item(row, 1).text() if self.table.item(row, 1) else "?"
        )

        s = (name or "").strip()
        cols = 32 # target line length (you can return 38)
        max_lines = 3
        seps = "._/-"

        lines = []
        i, n = 0, len(s)

        while i < n and len(lines) < max_lines:
            # if the remainder already fits on one line, just add and exit
            rem = n - i
            if rem <= cols:
                lines.append(s[i:n])
                i = n
                break

            # overflow: try to wrap on the separator within the cols window
            hard_end = i + cols
            window = s[i:hard_end]

            cut = -1
            # look for the closest separator to the end of the window
            for k in range(len(window) - 1, -1, -1):
                if window[k] in seps:
                    cut = i + k + 1 # wrap AFTER the separator
                    break

            if cut == -1:
                # you can "look ahead" a little, but only when there is already overflow
                look_end = min(hard_end + 12, n)
                for k in range(hard_end, look_end):
                    if s[k] in seps:
                        cut = k + 1
                        break

            if cut == -1:
                cut = hard_end # no separators - hard wrap

            lines.append(s[i:cut])
            i = cut

        # if it doesn't fit completely, add an ellipsis to the last visible line
        if i < n and lines:
            lines[-1] = lines[-1].rstrip() + "…"

        txt = "\n".join(lines) if lines else s
        self.panel.selectedLabel.setWordWrap(True)
        self.panel.selectedLabel.setText(txt)





    # --------------------------- Selection sync -----------------------------
    def _on_table_selection_changed(self, *args):
        if self._syncing_selection or getattr(self, "_building_table", False):
            return
        vrow = self.table.currentRow()
        self._syncing_selection = True
        try:
            if vrow is not None and vrow >= 0:
                mrow = self._view_to_model_index(vrow)
                item = getattr(self, "row_to_tree_item", {}).get(mrow)
                if item:
                    self.tree.blockSignals(True)
                    self.tree.setCurrentItem(item)
                    self.tree.blockSignals(False)
            self._update_selected_label()
        finally:
            self._syncing_selection = False

    def _on_tree_selection_changed(self):
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            item = self.tree.currentItem()
            if not item:
                return
            mrow = item.data(0, Qt.UserRole + 1) # model index
            if mrow is not None and 0 <= mrow < len(self.rows_model):
                vrow = self._model_to_view_index(mrow)
                self.table.blockSignals(True)
                self.table.selectRow(vrow)
                self.table.blockSignals(False)
                self._update_selected_label()
        finally:
            self._syncing_selection = False




    # ------------------------------ Double-click ----------------------------
    def _on_table_item_double_clicked(self, item):
        self._open_hex_for_current_table_row()

    def _on_tree_item_double_clicked(self, item, column):
        if not getattr(self, 'file_path', None):
            return
        row = item.data(0, Qt.UserRole + 1) # model string index
        if row is None or row < 0 or row >= len(self.rows_model):
            return
        entry = self.rows_model[row]
        self._open_hex_for_entry(entry)


    # ------------------------------ Open HexViewer ----------------------------
    def _open_hex_for_entry(self, entry):
        name = entry["name"]
        off = entry["offset"]
        ln  = entry["length"]
        if off is None or ln is None:
            QMessageBox.warning(self, "Parse error", "Offset or length could not be parsed.")
            return
        try:
            with open(self.file_path, 'rb') as f:
                f.seek(off)
                data = f.read(ln)
        except Exception as e:
            QMessageBox.critical(self, "Read failed", str(e))
            return

        hex_str = data.hex().upper()
        title = f"Hex Viewer — {name} @ 0x{off:X} (+{ln} bytes)"

        # Attempt to pass QTIHex to an external HexViewer (if available)
        try:
            QTIHex.QTIDicBin = hex_str
            if hasattr(QTIHex, "HexViewerDialog"):
                dlg = QTIHex.HexViewerDialog(hex_str)
                dlg.exec_()
                return
        except Exception:
            pass

        # Fallback to the built-in viewer
        dlg = HexViewerDialog(hex_str, self, title=title)
        dlg.exec_()




    def _open_hex_for_current_table_row(self):
        if not getattr(self, 'file_path', None):
            return
        vrow = self.table.currentRow()
        if vrow < 0:
            return
        entry = self.rows_model[self._view_to_model_index(vrow)]
        self._open_hex_for_entry(entry)



    # ------------------------------ Open HexEditor ----------------------------


    def _open_hexedit_for_entry(self, entry: dict):
        """
        Opens the external editor _QTIHexEdit, passing the file path, offset, and length.
        Global variable contract inside _QTIHexEdit:
          - _QTIHexEditFilePath
          - _QTIHexEditLibraryOffset
          - _QTIHexEditLibraryLength
        """
        # 1) sanity-check
        if not getattr(self, 'file_path', None):
            QMessageBox.warning(self, "No file", "Open a 'com.qti.*.bin' file first.")
            return

        off = entry.get("offset")
        ln  = entry.get("length")
        if off is None or ln is None:
            QMessageBox.warning(self, "Parse error", "Offset or length could not be parsed.")
            return

        # 2) Fill in the expected global variables in the _QTIHexEdit module
        try:
            # You specified these names as used by the _QTIHexEdit module itself
            setattr(QTIHexEdit, "_QTIHexEditFilePath",       self.file_path)
            setattr(QTIHexEdit, "_QTIHexEditLibraryOffset",  int(off))
            setattr(QTIHexEdit, "_QTIHexEditLibraryLength",  int(ln))
        except Exception as e:
            QMessageBox.critical(self, "Hex Editor", f"Cannot set _QTIHexEdit globals:\n{e}")
            return

        # 3) Try launching the editor in different ways – flexible, like with _QTIHex
        try:
            # Option A: Dialog class
            if hasattr(QTIHexEdit, "HexEditorDialog"):
                dlg = QTIHexEdit.HexEditorDialog(parent=self)
                dlg.exec_()
                return

            # Option B: Window
            if hasattr(QTIHexEdit, "MainWindow"):
                wnd = QTIHexEdit.MainWindow(parent=self)
                wnd.show()
                # To prevent the window from being garbage collected, you can save a reference
                self._hexedit_window = wnd
                return

            # Option C: Procedural launch
            if hasattr(QTIHexEdit, "run") and callable(QTIHexEdit.run):
                # Try to pass parent, if supported
                try:
                    QTIHexEdit.run(parent=self)
                except TypeError:
                    QTIHexEdit.run()
                return

            if hasattr(QTIHexEdit, "launch") and callable(QTIHexEdit.launch):
                try:
                    QTIHexEdit.launch(parent=self)
                except TypeError:
                    QTIHexEdit.launch()
                return

            # If none of the known inputs are found
            QMessageBox.information(
                self, "Hex Editor",
                "Module _QTIHexEdit is loaded, but no HexEditorDialog/MainWindow/run()/launch() was found."
            )

        except Exception as e:
            QMessageBox.critical(self, "Hex Editor error", repr(e))



    # ------------------------------- Actions --------------------------------
    def on_extract_binary(self):
        if not getattr(self, 'file_path', None):
            QMessageBox.warning(self, "No file", "Open a 'com.qti.*.bin' file first.")
            return

        entry = self._get_current_entry()
        if not entry:
            return

        name, off, ln = entry["name"], entry["offset"], entry["length"]
        if off is None or ln is None:
            QMessageBox.warning(self, "Parse error", "Offset or length could not be parsed.")
            return

        default_path = os.path.join(os.path.dirname(self.file_path), f"{name}.bin")
        out_path, _ = QFileDialog.getSaveFileName(self, "Save parameter as .bin", default_path, "BIN files (*.bin)")
        if not out_path:
            return

        try:
            with open(self.file_path, 'rb') as f:
                f.seek(off)
                data = f.read(ln)
            with open(out_path, 'wb') as w:
                w.write(data)
            self.statusBar().showMessage(f"Extracted '{name}' → {os.path.basename(out_path)}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Extract failed", str(e))


    def on_extract_param(self, dict_name: str):
        # EXPORT → Qdict (without returning data)
        if not getattr(self, 'file_path', None):
            QMessageBox.warning(self, "No file", "Open a 'com.qti.*.bin' file first.")
            return

        dict_path = self._get_selected_dict_path(dict_name)
        if not dict_path:
            QMessageBox.warning(self, "Dictionary not selected", "Please load a Parser Dictionary first.")
            return

        entry = self._get_current_entry()
        if not entry:
            return

        name, off, ln = entry["name"], entry["offset"], entry["length"]
        if off is None or ln is None:
            QMessageBox.warning(self, "Parse error", "Offset or length could not be parsed.")
            return

        try:
            with open(self.file_path, 'rb') as f:
                f.seek(off)
                data = f.read(ln)
        except Exception as e:
            QMessageBox.critical(self, "Read failed", str(e))
            return

        hex_str = data.hex().upper()

        # Preparing the context and launch the selected dictionary
        mod = self._get_dict_module()
        self._prepare_dict_context(mod, "Export", dict_path, entry, data, hex_str)

        try:
            self._run_dict(mod)
            self.statusBar().showMessage("Dictionary export completed.", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Dictionary export failed", str(e))

                
    def on_replace_param(self, dict_name: str):
        # IMPORT → Qdict (expect a binary of the same length and write it to a file)
        if not getattr(self, 'file_path', None):
            QMessageBox.warning(self, "No file", "Open a 'com.qti.*.bin' file first.")
            return

        dict_path = self._get_selected_dict_path(dict_name)
        if not dict_path:
            QMessageBox.warning(self, "Dictionary not selected", "Please load a Parser Dictionary first.")
            return

        entry = self._get_current_entry()
        if not entry:
            return

        name, off, ln = entry["name"], entry["offset"], entry["length"]
        if off is None or ln is None:
            QMessageBox.warning(self, "Parse error", "Offset or length could not be parsed.")
            return

        try:
            with open(self.file_path, 'rb') as f:
                f.seek(off)
                data = f.read(ln)
        except Exception as e:
            QMessageBox.critical(self, "Read failed", str(e))
            return

        hex_str = data.hex().upper()

        mod = self._get_dict_module()
        self._prepare_dict_context(mod, "Import", dict_path, entry, data, hex_str)

        try:
            ret = self._run_dict(mod)
        except Exception as e:
            QMessageBox.critical(self, "Dictionary import failed", str(e))
            return

        new_data = self._coerce_to_bytes(ret)
        if not new_data:
            QMessageBox.critical(self, "Import Error",
                                 "No data returned by the dictionary module. Try a different approach.")
            return
        if len(new_data) != ln:
            QMessageBox.critical(self, "Import Error",
                                 f"The returned buffer size ({len(new_data)}) doesn't match the module size ({ln}).")
            return

        try:
            with open(self.file_path, 'r+b') as w:
                w.seek(off)
                w.write(new_data)
            self.statusBar().showMessage("Dictionary import completed.", 4000)
            self._update_version_and_checksum()
        except Exception as e:
            QMessageBox.critical(self, "Write failed", str(e))


    def on_replace_binary(self):
        if not getattr(self, 'file_path', None):
            QMessageBox.warning(self, "No file", "Open a 'com.qti.*.bin' file first.")
            return

        entry = self._get_current_entry()
        if not entry:
            return

        name, off, ln = entry["name"], entry["offset"], entry["length"]
        if off is None or ln is None:
            QMessageBox.warning(self, "Parse error", "Offset or length could not be parsed.")
            return

        in_path, _ = QFileDialog.getOpenFileName(self, f"Choose replacement for '{name}'", "", "BIN files (*.bin)")
        if not in_path:
            return

        try:
            size = os.path.getsize(in_path)
            if size != ln:
                QMessageBox.warning(self, "Length mismatch",
                                    f"Replacement file size ({size}) does not match parameter length ({ln}).")
                return

            with open(in_path, 'rb') as r, open(self.file_path, 'r+b') as w:
                w.seek(off)
                w.write(r.read())

            self.statusBar().showMessage(f"Replaced '{name}' from {os.path.basename(in_path)}", 4000)
            self._update_version_and_checksum()
        except Exception as e:
            QMessageBox.critical(self, "Replace failed", str(e))


    def on_checksum_fix(self):
        if not getattr(self, 'file_path', None):
            return

        try:
            ChkSum.FilePathName = self.file_path
            res = ChkSum.checksumfix()
            self.statusBar().showMessage(f"{res}", 4000)
            self._update_version_and_checksum()
        except Exception as e:
            QMessageBox.critical(self, "Checksum Error", str(e))

    def _get_current_entry(self):
        if self.tabs.currentWidget() is self.table:
            vrow = self.table.currentRow()
            if 0 <= vrow < len(self.view_order):
                return self.rows_model[self._view_to_model_index(vrow)]

        if self.tabs.currentWidget() is self.tree:
            item = self.tree.currentItem()
            if item:
                mrow = item.data(0, Qt.UserRole + 1)
                if mrow is not None and 0 <= mrow < len(self.rows_model):
                    return self.rows_model[mrow]

        vrow = self.table.currentRow()
        if 0 <= vrow < len(self.view_order):
            return self.rows_model[self._view_to_model_index(vrow)]
        return None



    def on_view_toggle_tree(self):
        """If there is at least one expanded element, collapse everything; otherwise, expand everything."""
        if not hasattr(self, "tree") or self.tree.topLevelItemCount() == 0:
            return

        def any_expanded(item):
            if item.isExpanded():
                return True
            for i in range(item.childCount()):
                if any_expanded(item.child(i)):
                    return True
            return False

        expanded_found = False
        for i in range(self.tree.topLevelItemCount()):
            if any_expanded(self.tree.topLevelItem(i)):
                expanded_found = True
                break

        if expanded_found:
            self.tree.collapseAll()
        else:
            self.tree.expandAll()

    def on_tools_dict_creator(self):
        # built-in Creator from ParaParser._QTIDictionaryCreator (yours is already imported as QDCreate)
        self._launch_dict_creator_module(QDCreate)



    def _refresh_user_dict_creator_menu(self):
        """Check for a custom Creator and update the menu item."""
        mod = _find_user_dict_creator()
        self._user_qdc_mod = mod
        visible = mod is not None
        self.actUserDictCreator.setVisible(visible)
        if visible:
            title = getattr(mod, "TRIKSMODULENAME", "User Dictionary Creator")
            self.actUserDictCreator.setText(title)
            self.actUserDictCreator.setToolTip("")
        else:
            self.actUserDictCreator.setText("User Dictionary Creator (not installed)")
            self.actUserDictCreator.setToolTip(
                "Place QTIDictionaryCreator(.pyd/.so) into app folder or ParaParser/"
            )



    def _launch_user_dict_creator(self):
        """Open the custom Dictionary Creator if found."""
        mod = getattr(self, "_user_qdc_mod", None) or _find_user_dict_creator()
        if not mod:
            QMessageBox.information(self, "User Dictionary Creator", "No user creator module found.")
            return
        self._launch_dict_creator_module(mod)


    def _launch_dict_creator_module(self, mod):
        entry = self._get_current_entry()
        if not entry:
            QMessageBox.information(self, "Tools", "Select a module first.")
            return

        off = entry.get("offset"); ln = entry.get("length")
        if off is None or ln is None:
            QMessageBox.warning(self, "Tools", "Offset/Length parse error for selected module.")
            return

        try:
            with open(self.file_path, "rb") as f:
                f.seek(off)
                data = f.read(ln)
            hex_str = data.hex().upper()
        except Exception as e:
            QMessageBox.critical(self, "Tools", "Read failed: " + str(e))
            return

        # === LEGACY BRIDGE for built-in _QTIDictionaryCreator (expects _QTIHex globals) ===
        try:
            # many old tools read bytes from here
            QTIHex.QTIDicBin = data # RAW BYTES (important!)
            # if anyone needs text hex, we'll put it separately
            QTIHex.QTIDicHex        = hex_str

            QTIHex.QTISelectedID    = entry.get("id_disp")
            QTIHex.QTISelectedIDRaw = entry.get("id_raw")
            QTIHex.QTISelectedName  = entry.get("name")
            QTIHex.QTISelectedFilePath = self.file_path
            QTIHex.QTISelectedOffset   = off
            QTIHex.QTISelectedLength   = ln
            QTIHex.QTISelectedVersion  = getattr(self, "ver_txt", "")
        except Exception:
            pass
        # === /LEGACY BRIDGE ===

        # at the same time, we preserve the modern schema via the attributes of the dict itself module
        try:
            setattr(mod, "QTISelectedID",        entry.get("id_disp"))
            setattr(mod, "QTISelectedIDRaw",     entry.get("id_raw"))
            setattr(mod, "QTISelectedName",      entry.get("name"))
            setattr(mod, "QTISelectedHex",       hex_str)
            setattr(mod, "QTISelectedBuffer", data) # just in case
            setattr(mod, "QTISelectedFilePath",  self.file_path)
            setattr(mod, "QTISelectedOffset",    off)
            setattr(mod, "QTISelectedLength",    ln)
            setattr(mod, "QTISelectedVersion",   getattr(self, "ver_txt", ""))
        except Exception:
            pass

        try:
            if hasattr(mod, "run") and callable(mod.run):
                # trying to be flexible: some plugins accept kwargs
                try:
                    mod.run(parent=self, data=data, hex_str=hex_str,
                            file_path=self.file_path, offset=off, length=ln,
                            id=entry.get("id_raw"), name=entry.get("name"),
                            version=getattr(self, "ver_txt", ""))
                except TypeError:
                    mod.run(parent=self)
            elif hasattr(mod, "launch") and callable(mod.launch):
                mod.launch(parent=self)
            elif hasattr(mod, "MainDialog"):
                dlg = mod.MainDialog(parent=self); dlg.exec_()
            elif hasattr(mod, "MainWindow"):
                wnd = mod.MainWindow(parent=self); wnd.show()
            else:
                QMessageBox.information(
                    self, "Tools",
                    "Dictionary Creator loaded, but no run()/launch()/MainDialog/MainWindow found."
                )
        except Exception as e:
            QMessageBox.critical(self, "Tools", "Creator error:\n" + repr(e))


    # --------------------------- Dictionary helpers -------------------------
    def _dict_dir(self):
        base_dir = os.path.dirname(self.file_path) if getattr(self, 'file_path', None) else os.getcwd()
        return os.path.join(base_dir, 'Dictionaries')

    def _reload_dictionary_list(self, filter_text: str = None):
        combo = self.panel.dictionary
        combo.blockSignals(True)
        combo.clear()
        items = []
        dd = self._dict_dir()
        files = []
        if os.path.isdir(dd):
            try:
                files = [f for f in os.listdir(dd) if f.lower().endswith('.qdict')]
            except Exception:
                files = []
        if filter_text and self.panel.autofindCheck.isChecked() and files:
            ft = filter_text.lower()
            files = [f for f in files if ft in f.lower()]
        files.sort()
        if not files:
            items = ["Not selected", "Import *.Qdict"]
        else:
            items = files + ["Import *.Qdict"]
        combo.addItems(items)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)
        # Update the Export/Import button activity to reflect the current selection.
        try:
            self.panel._on_dict_changed(self.panel.dictionary.currentText())
        except Exception:
            pass
        self._sync_actions_enabled()


    def _on_autofind_toggled(self, checked: bool):
        row = self.table.currentRow()
        name = self.table.item(row,1).text() if (checked and row >=0 and self.table.item(row,1)) else None
        self._reload_dictionary_list(filter_text=name)

    def _on_dictionary_activated(self, text: str):
        if text == "Import *.Qdict":
            self._import_qdict()

    def _import_qdict(self):
        src, _ = QFileDialog.getOpenFileName(self, "Import *.Qdict", "", "Qdict files (*.Qdict)")
        if not src:
            return
        dd = self._dict_dir()
        os.makedirs(dd, exist_ok=True)
        dst = os.path.join(dd, os.path.basename(src))
        if os.path.exists(dst):
            ans = QMessageBox.question(self, "Replace file?", f"{os.path.basename(dst)} already exists. Replace it?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ans != QMessageBox.Yes:
                return
        try:
            shutil.copy2(src, dst)
            self._reload_dictionary_list()
            idx = self.panel.dictionary.findText(os.path.basename(dst))
            if idx >= 0:
                self.panel.dictionary.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))



    def _update_version_and_checksum(self):
        """
        Updates the version and state of the CheckSum Fix button.
        - For *.bin: old logic (read ASCII from 0x3A and compare the length from 0x1C).
        - For *.so: the version is requested from the LegacyChromatix loader.
                    *.so does not have a checksum—disable the button.
        """
        if not getattr(self, 'file_path', None):
            return

        try:
            ext = os.path.splitext(self.file_path)[1].lower()

            # ───────────────────────────────── SO/ELF branch ─────────────────────────────────
            if ext == ".so":
                # Path to .so as LEGACY_CHROMATIX_LIB_PATH
                LEGACY_CHROMATIX_LIB_PATH = self.file_path
                try:
                    ver_txt = LCAddrLenVer.load_chromatix_version(LEGACY_CHROMATIX_LIB_PATH)
                    # Normalize the string versions
                    if not isinstance(ver_txt, str):
                        ver_txt = ""
                    ver_txt = ver_txt.strip()
                    if not ver_txt:
                        ver_txt = "?.?." # fallback
                except Exception as e:
                    ver_txt = "?.?.?"
                    self.statusBar().showMessage("Failed to read .so version: " + str(e), 6000)

                self.ver_txt = ver_txt
                CURRENT_CHROMATIX_VER = ver_txt
                self.panel.versionLabel.setText("Parameter Parser Version: " + ver_txt)
                

                # No checksum for .so - disable the button
                self._sync_actions_enabled()
               
                return

            # ──────────────────────────────── BIN branch (old style) ────────────────────────────────
            size_fs = os.path.getsize(self.file_path)
            with open(self.file_path, 'rb') as f:
                # 1) Version at 0x3A (5 bytes) ASCII)
                f.seek(0x3A)
                ver = f.read(5)
                ver_txt = ver.decode('ascii', errors='ignore').replace('\x00', '').strip()
                if '.' not in ver_txt:
                    ver_txt = '1.0.0'
                self.ver_txt = ver_txt
                CURRENT_CHROMATIX_VER = ver_txt
                self.panel.versionLabel.setText("Parameter Parser Version: " + ver_txt)
                

                # 2) Image length by 0x1C (4 LE bytes) — compare with actual size
                f.seek(0x1C)
                raw = f.read(4)
                if len(raw) == 4:
                    file_len_le = int.from_bytes(raw, 'little')
                    self._sync_actions_enabled()


        except Exception as e:
            # If any error occurs, gently disable the button and report the status
            self.statusBar().showMessage("Version/Checksum read failed: " + str(e), 6000)






    # ——— HEX helpers ———
    def _clean_hex_text(self, s: str) -> str:
        """
        Removes everything except 0-9, A-F, a-f. Removes spaces/line feeds/separators.
        Returns raw, continuous HEX without the 0x prefix.
        """
        return re.sub(r'[^0-9A-Fa-f]', '', s or '')

    def _find_bytes_in_file(self, pattern: bytes, direction: int, wrap: bool = True) -> int or None:
        try:
            size_fs = os.path.getsize(self.file_path)
            with open(self.file_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            QMessageBox.critical(self, "HEX Search", f"Cannot read file:\n{e}")
            return None

        if not pattern:
            return None

        if self._last_hex_pos is None:
            start = 0 if direction > 0 else size_fs
        else:
            start = self._last_hex_pos + (1 if direction > 0 else 0)

        if direction > 0:
            pos = data.find(pattern, max(0, start))
            if pos == -1 and wrap:
                pos = data.find(pattern, 0)  # wrap to BOF
        else:
            end_lim = max(0, start)
            pos = data.rfind(pattern, 0, end_lim)
            if pos == -1 and wrap:
                pos = data.rfind(pattern, 0, size_fs)  # wrap to EOF

        return pos if pos != -1 else None


    def _select_param_by_file_offset(self, file_ofs: int) -> bool:
        """
        Finds the model record whose [offset, offset+length) contains file_ofs.
        Selects such a row in the table/tree, scrolls to it, and writes the status.
        Returns True if the parameter is found.
        """
        # Find the model index
        mrow = None
        for idx, entry in enumerate(self.rows_model):
            off = entry.get("offset")
            ln  = entry.get("length")
            if off is None or ln is None: 
                continue
            if off <= file_ofs < (off + ln):
                mrow = idx
                break

        if mrow is None:
            return False

        # Convert to display index
        vrow = self._model_to_view_index(mrow)
        if 0 <= vrow < self.table.rowCount():
            self.tabs.setCurrentWidget(self.table)
            self.table.blockSignals(True)
            self.table.selectRow(vrow)
            self.table.scrollToItem(self.table.item(vrow, 0))
            self.table.blockSignals(False)
            self._update_selected_label()

        entry = self.rows_model[mrow]
        name = entry.get("name", "?"); idd = entry.get("id_disp", "?")
        off  = entry.get("offset", 0); ln = entry.get("length", 0)
        rel  = file_ofs - off
        self.statusBar().showMessage(
            f'Match → "{name}" ({idd}) @ 0x{off:X} [+0x{rel:X} of 0x{ln:X}]', 6000
        )
        return True


    # --------------------------- Find dialog --------------------------------

    def open_find_dialog(self):
        if not getattr(self, 'file_path', None):
            QMessageBox.warning(self, "No file", "Open a 'com.qti.*.bin' file first.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Find Param")
        dlg.setMinimumSize(350, 150) # Minimum window size
        dlg.setMaximumSize(500, 300) # Minimum window size
        dlg.resize(350, 150) # Initial size
        
        # Enable resizing
        dlg.setSizeGripEnabled(True)
        
        root = QVBoxLayout(dlg)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        tabs = QTabWidget(dlg)
        root.addWidget(tabs)

        # ========= TAB 1: Search "Name" =========
        tab_name = QWidget()
        lay1 = QVBoxLayout(tab_name)
        lay1.setContentsMargins(10, 10, 10, 10)
        lay1.setSpacing(8)

        lay1.addWidget(QLabel('Find text in "Name":'))
        name_edit = QLineEdit(tab_name)
        name_edit.setText(getattr(self, "_last_find", ""))
        lay1.addWidget(name_edit)

        row1 = QHBoxLayout()
        b_back_txt = QPushButton("Find Backward", tab_name)
        b_fwd_txt  = QPushButton("Find Forward", tab_name)
        b_close_1  = QPushButton("Close", tab_name)
        row1.addWidget(b_back_txt)
        row1.addWidget(b_fwd_txt)
        row1.addWidget(b_close_1)
        lay1.addLayout(row1)

        tabs.addTab(tab_name, 'Search "Name"')

        # ========= TAB 2: Search "Hex" =========
        tab_hex = QWidget()
        lay2 = QVBoxLayout(tab_hex)
        lay2.setContentsMargins(10, 10, 10, 10)
        lay2.setSpacing(8)

        lay2.addWidget(QLabel('Find HEX sequence (max 32 KiB):'))

        hex_edit = QPlainTextEdit(tab_hex)
        hex_edit.setPlainText(self._last_find_hex)
        mono = QFont("Courier New")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(12) # Reduce font size for better display
        hex_edit.setFont(mono)
        hex_edit.setPlaceholderText("Example: 01 02 0A 0B 0C 0D ...")
        
        # HEX SETTINGS FOR BETTER DISPLAY
        hex_edit.setLineWrapMode(QPlainTextEdit.WidgetWidth) # Wrap by width Widget
        hex_edit.setWordWrapMode(True) # Enable word wrap
        
        # Enable scrollbars
        hex_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        hex_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        lay2.addWidget(hex_edit)

        hex_info = QLabel("", tab_hex)
        lay2.addWidget(hex_info)

        row2 = QHBoxLayout()
        b_back_hex = QPushButton("Find Backward", tab_hex)
        b_fwd_hex  = QPushButton("Find Forward", tab_hex)
        b_close_2  = QPushButton("Close", tab_hex)
        row2.addWidget(b_back_hex)
        row2.addWidget(b_fwd_hex)
        row2.addWidget(b_close_2)
        lay2.addLayout(row2)

        tabs.addTab(tab_hex, 'Search "Hex"')

        # Function for formatting HEX text with hyphens
        def format_hex_with_wrap(text):
            """Splits long HEX strings into pieces for better display"""
            # First, strip all non-HEX characters
            cleaned = self._clean_hex_text(text)
            if not cleaned:
                return ""
            
            # Split into groups of 32 characters (16 bytes) for readability
            chunk_size = 48
            chunks = [cleaned[i:i+chunk_size] for i in range(0, len(cleaned), chunk_size)]
            
            # Combine with line breaks
            return '\n'.join(chunks)

        # Function for updating HEX information and text formatting
        def _clean_hex_info_text():
            raw = hex_edit.toPlainText()
            cleaned = self._clean_hex_text(raw)
            max_hex_chars = 32768 * 2
            if len(cleaned) > max_hex_chars:
                cleaned = cleaned[:max_hex_chars]
                cursor = hex_edit.textCursor()
                pos = cursor.position()
                hex_edit.blockSignals(True)
                hex_edit.setPlainText(cleaned)
                cursor.setPosition(min(pos, len(cleaned)))
                hex_edit.setTextCursor(cursor)
                hex_edit.blockSignals(False)
            byte_len = len(cleaned) // 2
            hex_info.setText(f"Clean length: {len(cleaned)} hex chars (~{byte_len} bytes).")

    
        # ========== Name search logic ==========
        def do_fwd_txt():
            self._last_find = name_edit.text()
            self._do_find(self._last_find, +1)

        def do_back_txt():
            self._last_find = name_edit.text()
            self._do_find(self._last_find, -1)

        b_fwd_txt.clicked.connect(do_fwd_txt)
        b_back_txt.clicked.connect(do_back_txt)
        b_close_1.clicked.connect(dlg.close)

        # ========== HEX search logic ==========
        def do_hex(direction: int):
            raw = hex_edit.toPlainText()
            cleaned = self._clean_hex_text(raw)
            if len(cleaned) == 0:
                QMessageBox.information(self, "HEX Search", "Enter hex bytes to search.")
                return
            if len(cleaned) % 2 != 0:
                QMessageBox.warning(self, "HEX Search", "HEX string must have even length.")
                return
            if len(cleaned) > 65536:
                QMessageBox.warning(self, "HEX Search", "HEX pattern exceeds 32 KiB limit.")
                return
            try:
                pat = bytes.fromhex(cleaned)
                # reset if template has changed
                if not hasattr(self, "_last_hex_pat") or self._last_hex_pat != pat:
                    self._last_hex_pos = None
                self._last_hex_pat = pat

            except Exception:
                QMessageBox.critical(self, "HEX Search", "HEX string contains invalid characters.")
                return

            self._last_find_hex = cleaned
            
            ofs = self._find_bytes_in_file(pat, direction, wrap=True)

            if ofs is None:
                self.statusBar().showMessage("No more matches.", 3000)
                return
            self._last_hex_pos = ofs
            if not self._select_param_by_file_offset(ofs):
                self.statusBar().showMessage(f"Match at file offset 0x{ofs:X} (not inside any known module).", 6000)
                QMessageBox.information(self, "HEX Search", f"Match at file offset: 0x{ofs:X}")

        hex_edit.textChanged.connect(_clean_hex_info_text)
        
        # format initial text on opening
        if self._last_find_hex:
            formatted_initial = format_hex_with_wrap(self._last_find_hex)
            hex_edit.setPlainText(formatted_initial)
        _clean_hex_info_text()

        b_fwd_hex.clicked.connect(lambda: do_hex(+1))
        b_back_hex.clicked.connect(lambda: do_hex(-1))
        b_close_2.clicked.connect(dlg.close)

        # FUNCTION FOR CHANGING SIZE WHEN SWITCHING TABs
        def on_tab_changed(index):
            if index == 0:  # Search Name tab
                dlg.setMinimumHeight(150)
                dlg.setMaximumHeight(300)
                dlg.resize(350, 150)
            else:  # Search Hex tab
                dlg.setMinimumHeight(250)
                dlg.setMaximumHeight(300)
                dlg.resize(350, 250)
        
        # Connecting the tab change handler
        tabs.currentChanged.connect(on_tab_changed)

        # Configuring space distribution for stretching
        root.setStretchFactor(tabs, 1)
        
        # Set the size policy for tab content
        for tab in [tab_name, tab_hex]:
            tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Especially for hex_edit - so it stretches with the window
        hex_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Modeless
        dlg.setModal(False)
        dlg.show()

        # keeping links
        self._find_dialog = dlg
        self._find_name_edit = name_edit
        self._find_hex_edit = hex_edit
        self._find_tabs = tabs




    def _do_find(self, text: str, direction: int):
        if not text:
            self.statusBar().showMessage("Enter text to find.", 2000)
            return
        n = self.table.rowCount()
        if n == 0:
            return
        cur = self.table.currentRow()
        if cur < 0:
            idx = 0 if direction > 0 else n - 1
        else:
            idx = cur + direction
        while 0 <= idx < n:
            item = self.table.item(idx, 1)  # Name column
            if item and text.lower() in item.text().lower():
                self.table.selectRow(idx)
                self.table.scrollToItem(item)
                self._update_selected_label()
                if getattr(self.panel, 'autofindCheck', None) and self.panel.autofindCheck.isChecked():
                    self._reload_dictionary_list(filter_text=item.text())
                self.statusBar().showMessage(f"Found: {item.text()} (row {idx+1})", 2000)
                return
            idx += direction
        self.statusBar().showMessage("No further matches.", 2000)


    # --------------------------- Adds --------------------------------


    def _log(self, msg: str):
        self.statusBar().showMessage(msg, 2500)
        _dbg(msg)



    def show_about(self):
        dlg = AboutDialog(self)
        dlg.exec_()



    def show_help(self):
        dlg = QTIHelpDialog(self)
        dlg.exec_()


    def support(self):
        dlg = SupportWindow()
        dlg.exec_()




# --------------------------------- Entrypoint --------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)


    icon = get_embedded_icon()
    app.setWindowIcon(icon)

    
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
