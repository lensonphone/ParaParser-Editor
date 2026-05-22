# -*- coding: utf-8 -*-
import sys, os, shutil, subprocess, platform
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QFileDialog, QMessageBox, QDialog, QVBoxLayout,
    QComboBox, QLabel, QDialogButtonBox
)
from PyQt5.QtCore import Qt

# ============== Debug ==============
AllowDebug = 0
def _dbg(*args):
    if AllowDebug:
        try:
            print("[ADB_API]", *args, flush=True)
        except Exception:
            pass

# ============== subprocess helpers ==============
def _quiet_subprocess_kwargs():
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        return {"startupinfo": si, "creationflags": subprocess.CREATE_NO_WINDOW}
    return {}

def run(cmd, capture=True, check=False, text=True):
    kw = {"text": text}
    if capture:
        kw["stdout"] = subprocess.PIPE
        kw["stderr"] = subprocess.PIPE
        kw["stdin"]  = subprocess.DEVNULL
    kw.update(_quiet_subprocess_kwargs())
    _dbg("RUN:", " ".join(cmd))
    p = subprocess.run(cmd, **kw)
    _dbg(" -> rc:", p.returncode)
    if capture:
        _dbg(" -> stdout:", (p.stdout or "").strip())
        _dbg(" -> stderr:", (p.stderr or "").strip())
    if check:
        p.check_returncode()
    return p

def run_su(adb, cmd: str):
    # Root command without mount-namespace tricks — like in your "working" version
    return run([adb, "shell", "su", "-c", cmd])

# ============== ADB locate / device ==============
def locate_adb():
    # 1) First, try PATH
    adb_name = "adb.exe" if os.name == "nt" else "adb"
    adb = shutil.which(adb_name)
    _dbg("locate_adb: which ->", adb)
    if adb:
        return adb

    # 2) Prepare base directories: current and parent
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.abspath(os.path.join(here, os.pardir))

    sysname = platform.system()  # "Windows" | "Darwin" | "Linux" ...
    # roots in which to look for adb subfolders
    roots = [
        os.path.join(here,   "Packages", "adb"),
        os.path.join(parent, "Packages", "adb"), # <-- one folder higher
    ]

    # 3) Select candidates for a specific OS
    candidates = []
    for root in roots:
        if sysname == "Darwin":
            candidates.append(os.path.join(root, "Mac", "adb"))
        elif sysname == "Windows":
            candidates.append(os.path.join(root, "win", "adb.exe"))
        else:
            candidates.append(os.path.join(root, "linux", "adb"))

    # 4) Check candidates one by one
    for cand in candidates:
        cand = os.path.normpath(cand)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            _dbg("locate_adb: found ->", cand)
            return cand

    _dbg("locate_adb: NOT FOUND in PATH or local/parent Packages")
    return None


def ensure_device_ready(adb, parent=None):
    s = run([adb, "get-state"])
    state = (s.stdout or "").strip()
    _dbg("ensure_device_ready: state =", state)
    if s.returncode != 0 or state not in ("device", "recovery", "bootloader"):
        QMessageBox.critical(parent, "ADB", "Device not detected by ADB.")
        return False
    pong = run([adb, "shell", "echo", "pong"])
    okpong = (pong.returncode == 0 and "pong" in (pong.stdout or ""))
    _dbg("ensure_device_ready: pong =", okpong)
    if not okpong:
        QMessageBox.critical(parent, "ADB", "ADB shell is not responding.")
        return False
    return True

def device_has_su(adb) -> bool:
    r = run([adb, "shell", "su", "-c", "id"])
    ok = (r.returncode == 0 and "uid=0" in (r.stdout or ""))
    _dbg("device_has_su:", ok)
    return ok

# ============== small utils ==============
def is_remote_file(adb, path: str) -> bool:
    r = run([adb, "shell", f"test -f \"{path}\"; echo $?"])
    ok = (r.stdout or "").strip().endswith("0")
    _dbg(f"is_remote_file('{path}') ->", ok)
    return ok

def is_remote_dir(adb, path: str) -> bool:
    r = run([adb, "shell", f"test -d \"{path}\"; echo $?"])
    ok = (r.stdout or "").strip().endswith("0")
    _dbg(f"is_remote_dir('{path}') ->", ok)
    return ok

# ============== dialogs ==============
class RemotePathDialog(QDialog):
    """Input: base directory or full path (if it ends with '/', add the file name)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Target on device")
        v = QVBoxLayout(self)
        v.addWidget(QLabel(
            "Choose/edit a base directory, or type a full absolute path (including file name).\n"
            "If the text ends with '/', it is treated as a directory."
        ))
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.addItems([
            "/system/vendor/lib64",
            "/system/vendor/lib",
            "/system/lib64",
            "/system/lib",
        ])
        v.addWidget(self.combo)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

    def value(self) -> str:
        return (self.combo.currentText() or "").strip()

def normalize_remote_input_to_file_path(adb, typed: str, basename: str) -> str:
    _dbg("normalize: typed =", typed, "basename =", basename)
    if not typed:
        return ""
    if not typed.startswith("/"):
        typed = "/" + typed
    if typed.endswith("/"):
        path = typed.rstrip("/") + "/" + basename
        _dbg("normalize: endswith('/') ->", path)
        return path
    if is_remote_dir(adb, typed):
        path = typed.rstrip("/") + "/" + basename
        _dbg("normalize: is dir on device ->", path)
        return path
    _dbg("normalize: treat as file path ->", typed)
    return typed

# ============== backup (file only) ==============
def backup_remote_file(adb, remote_path, local_path, parent=None):
    """
    Place the backup next to local_path:
      <dirname(local_path)>/adb_backups/<YYYYMMDD_HHMMSS>/<basename(remote_path)>
    Returns the path to the local backup or None on failure/absence file on the device.
    """
    if not is_remote_file(adb, remote_path):
        _dbg("backup_remote_file: skip (not a file)", remote_path)
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    local_dir = os.path.dirname(os.path.abspath(local_path)) if local_path else os.getcwd()
    backup_root = os.path.join(local_dir, "adb_backups", ts)
    os.makedirs(backup_root, exist_ok=True)

    dst = os.path.join(backup_root, os.path.basename(remote_path))
    _dbg("backup_remote_file: pull ->", remote_path, "->", dst)
    pull = run([adb, "pull", remote_path, dst])
    if pull.returncode != 0:
        QMessageBox.warning(parent, "ADB Backup",
                            f"Failed to backup remote file:\n{remote_path}\n\n{(pull.stderr or '').strip()}")
        return None
    return dst


# =============== remount (like yours) ===============
def remount_system_rw(adb) -> bool:
    """Trying the standard and alternative /system remount to rw."""
    _dbg("remount_system_rw: try standard")
    r1 = run_su(adb, "mount -o rw,remount /system")
    if r1.returncode == 0:
        _dbg("remount_system_rw: standard ok")
        return True
    _dbg("remount_system_rw: try alternative by blockdevice")
    r2 = run_su(adb, "mount -o rw,remount /dev/block/bootdevice/by-name/system /system")
    ok = (r2.returncode == 0)
    _dbg("remount_system_rw: alternative =", ok)
    return ok

# ============== replacement (cp → chmod) ==============
def replace_remote_file(adb, local_path, remote_path, parent=None) -> bool:
    if not os.path.isfile(local_path):
        QMessageBox.critical(parent, "ADB Replace", f"Local file not found:\n{local_path}")
        return False
    if not is_remote_file(adb, remote_path):
        QMessageBox.critical(parent, "ADB Replace",
                             f"Target file does not exist on device:\n{remote_path}\n"
                             f"Replacement is not possible.")
        return False
    if not device_has_su(adb):
        QMessageBox.critical(parent, "ADB Replace",
                             "Root (su) is required to write into /system or /vendor.")
        return False

    # Confirmation
    if QMessageBox.question(
        parent, "Confirm replace",
        f"Replace on device:\n{remote_path}\n\nwith local file:\n{local_path}?",
        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
    ) != QMessageBox.Yes:
        _dbg("replace: user canceled")
        return False

    # Backup of an existing file (file only)
    #backup_remote_file(adb, remote_path, parent)
    backup_remote_file(adb, remote_path, local_path, parent)

    # Remount /system rw
    remount_system_rw(adb) # like your working version - try it, don't panic

    # Push to /sdcard
    tmp_remote = f"/sdcard/{os.path.basename(local_path)}"
    p = run([adb, "push", local_path, tmp_remote])
    if p.returncode != 0:
        QMessageBox.critical(parent, "ADB Replace", f"Failed to push file:\n{(p.stderr or '').strip()}")
        return False

    # Copy to root with 644 permissions, delete tmp
    try:
        c1 = run_su(adb, f"cp \"{tmp_remote}\" \"{remote_path}\"")
        c2 = run_su(adb, f"chmod 644 \"{remote_path}\"") if c1.returncode == 0 else c1
        c3 = run_su(adb, f"rm \"{tmp_remote}\"")
        if c1.returncode != 0 or c2.returncode != 0:
            raise RuntimeError(f"cp/chmod failed rc1={c1.returncode} rc2={c2.returncode}")
    except Exception as e:
        QMessageBox.warning(parent, "ADB Replace", f"Error replacing file:\n{e}")
        return False

    QMessageBox.information(parent, "ADB Replace",
                            f"Successfully replaced:\n{remote_path}\nPermissions set to 644.")
    return True

# ============== PUBLIC API ==============
def ADB_API(local_path=None, remote_path=None, parent: QWidget = None):
    """
    Returns:
    - (local_path, remote_path) on success
    - None on cancel/error
    """
    adb = locate_adb()
    if not adb:
        QMessageBox.critical(parent, "ADB", "ADB not found.\nAdd to PATH or place in Packages/adb/(Mac|win|linux).")
        return None
    if not ensure_device_ready(adb, parent=parent):
        return None

    # 1) local_path
    if not local_path:
        dlg_parent = parent if parent is not None else QWidget()
        if parent is None:
            dlg_parent.setWindowFlags(Qt.Tool)
        fname, _ = QFileDialog.getOpenFileName(dlg_parent, "Choose local file", "", "All Files (*)")
        if not fname:
            _dbg("ADB_API: local_path canceled")
            return None
        local_path = fname
    _dbg("ADB_API: local_path =", local_path)

    # 2) remote_path
    if not remote_path:
        d = RemotePathDialog(parent)
        if d.exec_() != QDialog.Accepted:
            _dbg("ADB_API: remote dialog canceled")
            return None
        typed = d.value()
        if not typed:
            QMessageBox.warning(parent, "ADB", "No remote input provided.")
            return None
        remote_path = normalize_remote_input_to_file_path(locate_adb(), typed, os.path.basename(local_path))
    else:
        remote_path = normalize_remote_input_to_file_path(locate_adb(), remote_path, os.path.basename(local_path))

    _dbg("ADB_API: remote_path(final) =", remote_path)

    # 3) strict file existence check
    if not is_remote_file(adb, remote_path):
        if is_remote_dir(adb, remote_path.rstrip("/")):
            QMessageBox.critical(parent, "ADB Replace",
                                 "The selected target on device is a directory.\n"
                                 "Replacement requires an existing file path.")
        else:
            QMessageBox.critical(parent, "ADB Replace",
                                 f"Target file not found on device:\n{remote_path}\n"
                                 f"Replacement is not possible.")
        return None

    # 4) replace
    ok = replace_remote_file(adb, local_path, remote_path, parent=parent)
    if not ok:
        return None

    # success → return both paths
    return (local_path, remote_path)

# ============== standalone ==============
def main():
    app = QApplication(sys.argv)
    res = ADB_API(None, None, parent=None) # individual launch → empty arguments
    if AllowDebug:
        print("ADB_API returned:", res)
    sys.exit(0 if res else 1)

if __name__ == "__main__":
    main()
