TRIKSMODULENAME = "Plugin Input Logger"
"""
Diagnostic / educational plugin - AND a reference doc for the host's
plugin contract.

WHAT THIS PLUGIN DOES
----------------------
It shows (in a Qt5 dialog AND in stderr/debug console) everything that
the host passes into a plugin's run() call, so you can inspect the real
shape of the data before writing processing logic against it. Run this
once against whatever file/row you plan to target, read the dialog/log
output, then use that ground truth instead of guessing.

THE HOST'S PLUGIN CONTRACT (reverse-engineered, confirmed empirically)
------------------------------------------------------------------------
A plugin module is expected to define:

    run(file_path, rows) -> None

called by the host on the MAIN thread by default. Optional module-level
flags the host recognizes (declare them to opt in; leave unset for the
default False/off behavior):

    RUN_IN_WORKER  - run() on a background thread instead of main thread.
                     Leave unset/False if you open a Qt dialog (like this
                     plugin does) - Qt widgets must live on the main thread.
    HEADLESS       - plugin does not need any UI.
    NO_UI          - same idea; check the host's docs for the exact
                     distinction if both exist.
    UPDATE_ROWS    - 0 means "I only read data, don't refresh the
                     table/tree after I return." Set to 1 (or whatever the
                     host expects) if your plugin edits `rows` in place and
                     wants the host to redraw.

The host also fills in these module-level globals before calling run(),
if it declares them (declaring the name is what makes the host populate
it - see CURRENTSELECTED_ROW / CURRENT_CHROMATIX_VER below):

    CURRENTSELECTED_ROW   - see "ROW INDEXING" below.
    CURRENT_CHROMATIX_VER - a version string/identifier, when available.
    QTISelectedVersion    - NOT declared here on purpose; the host injects
                             it into the module's globals only sometimes,
                             so we read it defensively with a NameError
                             guard instead of declaring `= None` up front
                             (declaring it as None would shadow whatever
                             the host tries to inject).

ARGUMENTS TO run(file_path, rows)
------------------------------------
file_path : str | None
    Path to the file currently open in the host (the whole calibration/
    module file, not a specific sub-record). None/empty if nothing is
    open.

rows : list
    The ENTIRE table of rows for the currently open file - this is a
    symbol/module table listing EVERY module in the file (AEC, HDR, gain,
    CCT, revision info, etc.), not just the one row the user has
    selected or the one your plugin cares about. A real file can easily
    have 1000+ rows. Two consequences:
      1. Don't blindly loop over every row assuming they're all relevant
         to your plugin - filter by name, or better, only process the
         row(s) identified by CURRENTSELECTED_ROW.
      2. Each row is a plain CSV-formatted STRING, not raw bytes and not
         a tuple/dict:

             "ID,name,offset,size"

         e.g. "00000264,revision,00260BFC,00000002"
           -> ID     = 0x264   (row's own index/tag, hex without "0x")
              name   = "revision"
              offset = 0x260BFC   (absolute byte offset into file_path)
              size   = 0x2        (byte length of that module's data)

         All three numeric fields are hex digits WITHOUT a "0x" prefix -
         parse with int(field, 16). The row does NOT contain the actual
         module bytes; to get real data you open file_path yourself,
         seek(offset), and read(size).

ROW INDEXING (the sharp edge to get right)
---------------------------------------------
CURRENTSELECTED_ROW is 1-BASED, not a normal 0-based Python list index.
To find the matching entry in `rows`:

    idx0 = CURRENTSELECTED_ROW - 1     # INDEX_BASE = 1
    if rows is not None and 0 <= idx0 < len(rows):
        selected_row_string = rows[idx0]

Getting this off-by-one wrong silently reads the WRONG module - it won't
crash, it'll just quietly hand you a neighboring row's data instead of
the one the user actually selected. Always convert before indexing.

PUTTING IT TOGETHER: reading a module's real bytes
------------------------------------------------------
    idx0 = CURRENTSELECTED_ROW - 1
    row_str = rows[idx0]
    id_str, name, ofs_str, len_str = [p.strip() for p in row_str.split(",")]
    offset, size = int(ofs_str, 16), int(len_str, 16)
    with open(file_path, "rb") as f:
        f.seek(offset)
        payload = f.read(size)
    # `payload` is now the real bytes for that module - hand it to
    # struct.unpack(), numpy, etc. depending on what the module encodes.

WHY THIS FILE EXISTS
------------------------
Guessing any of the above from scratch (row shape, 1-based index, hex-
without-prefix fields) costs real debugging time and produces confusing
symptoms (off-by-one row selection, "could not parse" spam when a plugin
loops over unrelated rows, etc.). Run this Input Logger against a real
selection first, confirm the shapes above still hold for the current
host version, and only then write your plugin's real logic. The log also
dumps the first MAX_HEX_PREVIEW_BYTES bytes of the selected module (read
straight from file_path at its offset) as a hex string, so you can sanity
-check a real byte layout before writing a parser for it.
"""

# Declaring these makes the host fill them in before calling run().
CURRENTSELECTED_ROW = None    # 1-based index into `rows` - see ROW INDEXING above
CURRENT_CHROMATIX_VER = None

# This plugin only inspects/reports data - it never changes the rows,
# so we tell the host not to touch the table/tree after we finish.
UPDATE_ROWS = 0

# Runs on the MAIN thread (default) - required, since we open a Qt dialog.
# RUN_IN_WORKER / HEADLESS / NO_UI are intentionally left unset/False.

MAX_ROWS_TO_SHOW = 10  # if more rows than this, the full list is not printed
MAX_HEX_PREVIEW_BYTES = 100  # how many bytes of the selected module to dump as hex


import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton


def _format_rows_block(rows):
    """Return a display string for `rows`, truncated if too long."""
    total = len(rows)
    if total <= MAX_ROWS_TO_SHOW:
        lines = [f"  [{i}] {r}" for i, r in enumerate(rows)]
        return f"rows ({total} total):\n" + ("\n".join(lines) if lines else "  (empty)")

    # More than MAX_ROWS_TO_SHOW -> show a head/tail preview only.
    head_n = 5
    tail_n = 5
    head = [f"  [{i}] {r}" for i, r in enumerate(rows[:head_n])]
    tail = [f"  [{total - tail_n + j}] {r}" for j, r in enumerate(rows[-tail_n:])]
    hidden = total - head_n - tail_n
    middle = [f"  ... {hidden} more row(s) not shown ..."]
    body = "\n".join(head + middle + tail)
    return f"rows ({total} total, showing first {head_n} and last {tail_n}):\n{body}"


HEX_DUMP_BYTES_PER_LINE = 16  # classic hexdump width - keeps lines short enough to read without scrolling


def _format_hex_block(data, bytes_per_line=HEX_DUMP_BYTES_PER_LINE, indent="     "):
    """Splits `data` into fixed-width hex lines, each prefixed with its
    starting byte offset within `data` (not the file), e.g.:
        +0000: 0000803F00C00F45F9DB264011E19DBF1D5BBFB
        +0010: EBCB3AEBE5210D43F478DA1BEA6B6143DA0A775B
    Keeps every line short and readable in both the Qt dialog and a plain
    terminal, regardless of wrap settings.
    """
    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        lines.append(f"{indent}+{i:04X}: {chunk.hex().upper()}")
    return "\n".join(lines)


def _read_hex_preview(file_path, offset, size, max_bytes=MAX_HEX_PREVIEW_BYTES):
    """
    Reads up to `max_bytes` bytes starting at `offset` from `file_path` and
    returns them as a multi-line hex dump (fixed-width lines, see
    _format_hex_block) instead of one long unbroken string, so it's
    readable without horizontal scrolling in either the dialog or the
    console. Never raises - any failure is reported inline instead.

    NOTE: if the module's own `size` is smaller than `max_bytes` (very
    common - plenty of modules are a handful of bytes), this shows the
    module's ENTIRE content, not a 100-byte preview - there's simply
    nothing more to show. The line always states plainly whether you're
    looking at the whole module or a truncated slice of a bigger one.
    """
    header = f"  -> hex dump @ offset=0x{offset:X}, module size=0x{size:X} ({size} bytes)"

    if not file_path or not os.path.exists(file_path):
        return f"{header}: (file_path unavailable, can't read)"
    if size <= 0:
        return f"{header}: (module size is 0, nothing to read)"

    n = min(size, max_bytes)
    try:
        with open(file_path, "rb") as f:
            f.seek(offset)
            data = f.read(n)
    except Exception as e:
        return f"{header}: (read failed: {e})"

    if not data:
        return f"{header}: (read returned no data)"

    if size <= max_bytes:
        scope = f"ALL {len(data)} bytes (whole module - smaller than the {max_bytes}-byte cap)"
    else:
        scope = f"first {len(data)} of {size} bytes (module is larger than the {max_bytes}-byte cap)"
    short_read_note = "" if len(data) == n else f" [short read: only {len(data)} of {n} requested]"

    return f"{header}\n  -> {scope}:{short_read_note}\n{_format_hex_block(data)}"


def _describe_selected_row(file_path, rows):
    """
    Resolves CURRENTSELECTED_ROW (1-based) against `rows` and, if it looks
    like the host's "ID,name,offset,size" CSV format, breaks it down field
    by field and dumps a hex preview of the module's actual bytes (read
    from file_path at that offset). Returns a display string; never
    raises - any parsing/read hiccup is reported inline instead of
    crashing the whole logger.
    """
    if CURRENTSELECTED_ROW is None:
        return "CURRENTSELECTED_ROW: (not set by host)"
    if not isinstance(CURRENTSELECTED_ROW, int):
        return f"CURRENTSELECTED_ROW: {CURRENTSELECTED_ROW!r} (unexpected type, not an int)"

    idx0 = CURRENTSELECTED_ROW - 1  # INDEX_BASE = 1
    lines = [f"CURRENTSELECTED_ROW: {CURRENTSELECTED_ROW!r} (1-based) -> index {idx0} (0-based)"]

    if not rows or not (0 <= idx0 < len(rows)):
        lines.append(f"  -> out of range for {len(rows) if rows else 0} row(s)")
        return "\n".join(lines)

    row_str = rows[idx0]
    lines.append(f"  -> rows[{idx0}] = {row_str!r}")

    if isinstance(row_str, str):
        parts = [p.strip() for p in row_str.split(",")]
        if len(parts) == 4:
            id_str, name, ofs_str, len_str = parts
            try:
                offset = int(ofs_str, 16)
                size = int(len_str, 16)
                lines.append(
                    f"  -> parsed as CSV: id=0x{int(id_str, 16):X} name={name!r} "
                    f"offset=0x{offset:X} size=0x{size:X}"
                )
                lines.append(_read_hex_preview(file_path, offset, size))
            except ValueError:
                lines.append("  -> looked like 4 CSV fields but one wasn't valid hex")
        else:
            lines.append(f"  -> not the usual 4-field CSV format ({len(parts)} field(s))")

    return "\n".join(lines)


def run(file_path, rows):
    rows = rows or []

    lines = []
    lines.append("=== Plugin Input Logger ===")
    lines.append(f"file_path: {file_path!r}" if file_path else "file_path: (empty - no file open)")
    lines.append(_describe_selected_row(file_path, rows))
    lines.append(f"CURRENT_CHROMATIX_VER: {CURRENT_CHROMATIX_VER!r}")
    try:
        lines.append(f"QTISelectedVersion: {QTISelectedVersion!r}")  # noqa: F821 (set by host at runtime)
    except NameError:
        lines.append("QTISelectedVersion: (not set by host)")
    lines.append("")
    lines.append(_format_rows_block(rows))

    log_text = "\n".join(lines)

    # Always mirror the log to stderr / debug console too.
    print(log_text)

    # Show it in a small Qt5 dialog as well.
    dlg = QDialog()
    dlg.setWindowTitle(TRIKSMODULENAME)
    dlg.resize(640, 420)

    layout = QVBoxLayout(dlg)

    text = QPlainTextEdit(dlg)
    text.setReadOnly(True)
    text.setPlainText(log_text)
    text.setLineWrapMode(QPlainTextEdit.NoWrap)
    layout.addWidget(text)

    close_btn = QPushButton("Close", dlg)
    close_btn.clicked.connect(dlg.accept)
    layout.addWidget(close_btn, alignment=Qt.AlignRight)

    dlg.exec_()

    # No changes to apply - UPDATE_ROWS = 0 anyway, but return None to be explicit.
    return None
