import sys
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QFileDialog, QTabWidget, QLabel, QMessageBox, QGridLayout, QInputDialog,  
    QDialog, QSlider, QLineEdit, QDialogButtonBox, QTextBrowser, QMenu
)
from PyQt5.QtGui import QImage, QFont, QPixmap, QColor
from PyQt5.QtCore import Qt


class QTIHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help")
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # language selection drop-down
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Deutsch", "Français"])
        self.lang_combo.currentTextChanged.connect(self.update_text)
        layout.addWidget(self.lang_combo)

        # text with links and formatting
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(True)
        layout.addWidget(self.text, 1)

        # reference texts
        self.help_texts = {
"English": """
<h2>What This Program Does</h2>
<p>ParaParser-Editor is a desktop tool for parsing, inspecting, and editing binary parameters inside Qualcomm Chromatix camera tuning libraries (.bin / .so files). It provides a professional environment for camera tuning engineers and advanced modders.</p>

<hr>

<h3>Open & Parse Libraries</h3>
<p>Loads Qualcomm Chromatix camera libraries (.bin or .so) and extracts all parameters — their IDs, names, offsets, and sizes. The parser automatically detects the internal structure and builds a complete parameter map.</p>

<h3>Browse Parameters</h3>
<p>Displays parsed parameters in a searchable Table view or a hierarchical Tree view for easy navigation. You can sort columns, filter entries, and quickly jump between different parameter groups.</p>

<h3>Extract & Replace</h3>
<p>Lets you pull out any parameter as a binary blob and write a modified version back into the library file. This is useful for external hex editing or applying precomputed tuning values.</p>

<h3>Dictionary Support</h3>
<p>Uses .Qdict dictionary files to decode parameter values into human-readable form and import/export named presets. Dictionaries bridge the gap between raw binary data and meaningful camera settings.</p>

<h3>Hex Inspection</h3>
<p>Built-in hex viewer and hex editor let you inspect or patch raw bytes directly inside a selected parameter. Both read-only and editable modes are available with real-time updates.</p>

<h3>Magisk / ADB Export</h3>
<p>Packages the modified library as a ready-to-flash Magisk module or pushes it to a connected Android device over ADB. This streamlines deployment to rooted devices without manual file copying.</p>

<hr>

<h2>Window Structure</h2>
<p>The main window is split into two panels side by side. The left panel displays the parameter list, and the right panel provides all editing and export controls.</p>

<h3>Left Panel — Parameter List</h3>
<p>Contains two tabs you can switch between: Table (flat list with columns ID, Name, Offset, Length) and Tree (collapsible hierarchy by module/group). Click a row to select a parameter. Double‑click any row or node to open the Hex Viewer immediately.</p>

<h3>Right Panel — Controls</h3>
<p>Shows the currently selected parameter name and gives you all action buttons: Extract/Replace as binary, Dictionary Parser with Export/Import, and bottom utility buttons (Find, Donate, Close). Every action has a corresponding keyboard shortcut.</p>

<p><strong>Status Bar</strong> — at the very bottom of the window. Shows live feedback: current action, file name, search results, and any errors during parsing or replacement.</p>

<hr>

<h2>Menus Explained</h2>

<h3>File Menu</h3>
<p>Handles project files, library import, overwrite, export, Magisk/ADB deployment, and application exit. Projects save the full editing session including loaded dictionaries and last selected parameter.</p>

<ol>
    <li><strong>Project — Open (Ctrl+O)</strong><br>Opens a saved .QPPProj project file. Automatically loads the associated library and restores the previous editing session.</li>
    <li><strong>Project — Save (Ctrl+S)</strong><br>Saves the current session to the open project file. Only available after a project is loaded or saved for the first time.</li>
    <li><strong>Project — Save As… (Ctrl+Shift+S)</strong><br>Saves the session as a new .QPPProj file at a location you choose.</li>
    <li><strong>Library — Import (Ctrl+L)</strong><br>Opens a .bin or .so Chromatix camera library file, parses it in the background, and populates the parameter list.</li>
    <li><strong>Library — Overwrite</strong><br>Writes all current changes back into the original library file on disk. For .bin files, the checksum is recalculated automatically.</li>
    <li><strong>Library — Export As…</strong><br>Saves a copy of the modified library to a new file path without touching the original.</li>
    <li><strong>Library — Revert Changes</strong><br>Restores the library to the state it was in when it was last imported (from an automatic .bak backup). Useful for undoing all edits.</li>
    <li><strong>Export Library As Magisk (Ctrl+Shift+M)</strong><br>Packages the current library into a flashable Magisk module ZIP that can be installed on a rooted Android device.</li>
    <li><strong>Export Library via ADB (Ctrl+Shift+A)</strong><br>Pushes the modified library directly to a connected Android device using ADB (Android Debug Bridge).</li>
    <li><strong>Exit</strong><br>Closes the application. Will prompt to save unsaved changes if any are detected.</li>
</ol>

<h3>Edit Menu</h3>
<p>Provides search functionality across parameter names and raw binary content. The hex search scans the actual file bytes, not only the parameter list.</p>
<ol>
    <li><strong>Find Parameter (Ctrl+F)</strong><br>Opens the search dialog with two tabs — Search by Name (text search, Forward/Backward) and Search by Hex (raw byte pattern search inside the file).</li>
</ol>

<h3>View Menu</h3>
<p>Controls tree expansion, hex viewers, and sorting order of the parameter table. Sorting affects only the Table view; the Tree view follows the original structural hierarchy.</p>
<ol>
    <li><strong>Collapse or Expand Tree (Shift+C)</strong><br>Toggles all nodes in the Tree view between fully collapsed and fully expanded.</li>
    <li><strong>Show Hex Viewer (Ctrl+D)</strong><br>Opens a read-only hex dump window for the currently selected parameter. Shows offset, hex bytes, and ASCII side by side.</li>
    <li><strong>Show Hex Editor (Ctrl+Shift+D)</strong><br>Opens an editable hex window for the selected parameter, allowing you to modify raw bytes directly and write them back.</li>
    <li><strong>Sort → As Parsed</strong><br>Keeps parameters in the order they were found in the library file (default).</li>
    <li><strong>Sort → By ID</strong><br>Sorts parameters numerically by their internal ID.</li>
    <li><strong>Sort → By Offset</strong><br>Sorts parameters by their byte offset in the file — useful for sequential binary analysis.</li>
</ol>

<h3>Tools Menu</h3>
<p>Contains dictionary creation utilities. The built‑in creator works without external dependencies, while the user dictionary creator supports advanced workflows.</p>
<ol>
    <li><strong>Parser Dictionary Creator (Shift+D)</strong><br>Opens the built-in tool for building a new .Qdict dictionary from scratch — maps parameter IDs to human-readable names and value descriptions.</li>
    <li><strong>User Dictionary Creator (Ctrl+Shift+D)</strong><br>Appears only if a user-provided QTIDictionaryCreator binary module is installed. Launches the custom external dictionary creation tool.</li>
</ol>

<h3>Plugins Menu</h3>
<p>Lists built‑in automation tools and any third‑party plugins. Plugins extend the application without modifying its core code.</p>
<ol>
    <li><strong>Auto Tree Sorter V2</strong><br>Automatically reorganizes and formats the Tree view — groups parameters by module type and cleans up the hierarchy.</li>
    <li><strong>Batch Binary Export/Import Tool</strong><br>Export or import multiple selected parameters as binary files in a single operation — useful for bulk editing workflows.</li>
    <li><strong>Rows Export Tool</strong><br>Exports selected rows (parameters) to a text or data file for external review or sharing.</li>
    <li><strong>Rows Import Tool</strong><br>Imports a previously exported rows file and applies the values back into the current library.</li>
    <li><strong>User Plugins</strong><br>Lists any third-party plugins installed in the Plugins/ folder. Each appears as a menu item and can be run against the currently loaded library.</li>
    <li><strong>Install plugin…</strong><br>Opens a file picker to install a new user plugin (.py / .so / .pyd) into the Plugins directory without restarting the application.</li>
</ol>

<h3>More Menu</h3>
<p>Provides help, about information, and donation options. The built‑in help reference is context‑aware when a parameter is selected.</p>
<ol>
    <li><strong>About</strong><br>Shows the application version, author, and license information.</li>
    <li><strong>Help</strong><br>Opens the built-in help reference for QTI Parameter Extractor/Replacer functionality.</li>
    <li><strong>Donate</strong><br>Opens the support/donation window. Same as the Donate button in the right panel.</li>
</ol>

<hr>

<h2>Control Panel Buttons</h2>

<h3>Extract / Replace As Binary</h3>
<p><strong>Extract</strong> — saves the raw bytes of the selected parameter to a .bin file on disk.<br><strong>Replace</strong> — loads a .bin file you choose and writes its bytes back into the library at the parameter's position.<br>Shortcuts: Ctrl+E / Ctrl+R.</p>

<h3>Dictionary Parser (Built-in)</h3>
<p><strong>Dictionary dropdown</strong> — select a loaded .Qdict file (or choose "Import *.Qdict" to load one from disk). Defines how parameter values are decoded.<br><strong>Autofind Dictionary</strong> — checkbox. When checked, the dictionary list automatically filters to match the name of the currently selected parameter.<br><strong>Export</strong> — extracts the selected parameter's decoded data using the chosen dictionary.<br><strong>Import</strong> — writes decoded/edited data back into the parameter using the dictionary format.<br>Shortcuts: Ctrl+Shift+E / Ctrl+Shift+I.</p>

<h3>Bottom Buttons (Find, Donate, Close)</h3>
<p><strong>Find</strong> — opens the search dialog (same as Ctrl+F).<br><strong>Donate :)</strong> — opens the support window.<br><strong>Close</strong> — closes the application.</p>

<hr>

<h2>Search Dialog</h2>
<p>Opened via Edit → Find Parameter or Ctrl+F or the Find button. Contains two tabs for flexible searching across names and raw hex patterns.</p>

<h3>Tab 1 — Search "Name"</h3>
<p>Type part of a parameter name into the text field. Find Forward jumps to the next matching row below the current selection. Find Backward jumps to the previous matching row above. The search is case‑insensitive by default.</p>

<h3>Tab 2 — Search "Hex"</h3>
<p>Enter a raw byte sequence in hex (e.g. <code>01 02 0A 0B</code>). Find Forward/Backward scans the binary file for the byte pattern and selects the parameter that contains it. The dialog shows the byte count as you type, helping you validate the pattern length.</p>

<hr>

<h2>Keyboard Shortcuts</h2>
<p>All major actions have dedicated shortcuts for a fast, keyboard‑driven workflow. On macOS, use Cmd (⌘) instead of Ctrl.</p>
<ol>
    <li><strong>Ctrl+O</strong> — Open project</li>
    <li><strong>Ctrl+S</strong> — Save project</li>
    <li><strong>Ctrl+Shift+S</strong> — Save project as…</li>
    <li><strong>Ctrl+L</strong> — Import library file</li>
    <li><strong>Ctrl+F</strong> — Open search dialog</li>
    <li><strong>Ctrl+E</strong> — Extract selected param as binary</li>
    <li><strong>Ctrl+R</strong> — Replace selected param from binary</li>
    <li><strong>Ctrl+D</strong> — Open Hex Viewer</li>
    <li><strong>Ctrl+Shift+D</strong> — Open Hex Editor</li>
    <li><strong>Ctrl+Shift+E</strong> — Dictionary Export</li>
    <li><strong>Ctrl+Shift+I</strong> — Dictionary Import</li>
    <li><strong>Ctrl+Shift+C</strong> — Fix checksum</li>
    <li><strong>Ctrl+Shift+M</strong> — Export as Magisk module</li>
    <li><strong>Ctrl+Shift+A</strong> — Export via ADB</li>
    <li><strong>Shift+C</strong> — Collapse / expand tree</li>
    <li><strong>Shift+D</strong> — Parser Dictionary Creator</li>
</ol>
<p>macOS note: All Ctrl shortcuts use Cmd (⌘) instead. For example, Ctrl+S becomes Cmd+S.</p>

<hr>

<h2>Step-by-Step Example</h2>
<p>This typical workflow guides you from opening a library to deploying a modified version on an Android device.</p>
<ol>
    <li>Go to <strong>File → Library — Import</strong> (<code>Ctrl+L</code>) and open your .bin or .so camera library.</li>
    <li>Wait for parsing to finish. The Table will populate with all found parameters (IDs, names, offsets, and sizes).</li>
    <li>Use the <strong>Tree</strong> tab or press <code>Ctrl+F</code> to locate the parameter you want to edit.</li>
    <li>Click the row to select it. The right panel shows its name and enables the action buttons.</li>
    <li>Press <code>Ctrl+D</code> to inspect its raw bytes in the Hex Viewer, or <code>Ctrl+Shift+D</code> to edit them directly.</li>
    <li>Alternatively, use <strong>Extract</strong> (<code>Ctrl+E</code>) to save the parameter as a file, edit it externally, then <strong>Replace</strong> (<code>Ctrl+R</code>) to write it back.</li>
    <li>After all edits, go to <strong>File → Library — Overwrite</strong> to save changes to the library. Checksum is fixed automatically for .bin files.</li>
    <li>Use <strong>Export As Magisk</strong> (<code>Ctrl+Shift+M</code>) or <strong>Export via ADB</strong> (<code>Ctrl+Shift+A</code>) to deploy the result to your device.</li>
    <li>Save your session with <strong>File → Project — Save</strong> (<code>Ctrl+S</code>) so you can continue later.</li>
</ol>

<h3>Links</h3>
<ul>
  <li><a href="https://www.youtube.com/@Lensonphone">Video instructions</a></li>
  <li><a href="https://t.me/lensonphone">Telegram-Community</a></li>
  <li><a href="https://github.com/lensonphone">Github</a></li>
  <li><a href="https://www.instagram.com/reallensonphone/">Instagram</a></li>
  <li><a href="https://forms.gle/6Zt1sqStiWiPhRFJ7">Connect</a></li>
</ul>

""",

"Deutsch": """
<h2>Was dieses Programm tut</h2> <p>ParaParser-Editor ist ein Desktop-Tool zum Parsen, Inspizieren und Bearbeiten von Binärparametern in Qualcomm Chromatix Kamera-Tuning-Bibliotheken (.bin / .so-Dateien). Es bietet eine professionelle Umgebung für Kameratuning-Ingenieure und fortgeschrittene Modder.</p><hr><h3>Öffnen & Parsen von Bibliotheken</h3> <p>Lädt Qualcomm Chromatix Kamerabibliotheken (.bin oder .so) und extrahiert alle Parameter – deren IDs, Namen, Offsets und Größen. Der Parser erkennt automatisch die interne Struktur und erstellt eine vollständige Parametertabelle.</p><h3>Parameter durchsuchen</h3> <p>Zeigt die geparsten Parameter in einer durchsuchbaren Tabellenansicht oder einer hierarchischen Baumansicht zur einfachen Navigation an. Sie können Spalten sortieren, Einträge filtern und schnell zwischen verschiedenen Parametergruppen wechseln.</p><h3>Extrahieren & Ersetzen</h3> <p>Ermöglicht es, jeden Parameter als Binärblob zu extrahieren und eine modifizierte Version zurück in die Bibliotheksdatei zu schreiben. Dies ist nützlich für externes Hex-Editing oder das Anwenden von vorberechneten Tuning-Werten.</p><h3>Wörterbuchunterstützung</h3> <p>Verwendet .Qdict-Wörterbuchdateien, um Parameterwerte in eine menschenlesbare Form zu dekodieren und benannte Voreinstellungen zu importieren/exportieren. Wörterbücher überbrücken die Lücke zwischen rohen Binärdaten und verständlichen Kameraeinstellungen.</p><h3>Hex-Inspektion</h3> <p>Integrierter Hex-Betrachter und Hex-Editor ermöglichen es, rohe Bytes direkt innerhalb eines ausgewählten Parameters zu inspizieren oder zu patchen. Sowohl schreibgeschützte als auch bearbeitbare Modi sind mit Echtzeit-Updates verfügbar.</p><h3>Magisk / ADB Export</h3> <p>Verpackt die modifizierte Bibliothek als fertiges Magisk-Modul oder schiebt sie über ADB auf ein verbundenes Android-Gerät. Dies vereinfacht die Bereitstellung auf gerooteten Geräten ohne manuelles Dateikopieren.</p><hr><h2>Fensterstruktur</h2> <p>Das Hauptfenster ist in zwei nebeneinander liegende Bereiche aufgeteilt. Der linke Bereich zeigt die Parameterliste an, der rechte Bereich bietet alle Bearbeitungs- und Exportsteuerungen.</p><h3>Linker Bereich — Parameterliste</h3> <p>Enthält zwei Registerkarten, zwischen denen Sie wechseln können: Tabelle (flache Liste mit Spalten ID, Name, Offset, Länge) und Baum (einklappbare Hierarchie nach Modul/Gruppe). Klicken Sie auf eine Zeile, um einen Parameter auszuwählen. Doppelklicken Sie auf eine beliebige Zeile oder einen Knoten, um sofort den Hex-Betrachter zu öffnen.</p><h3>Rechter Bereich — Steuerungen</h3> <p>Zeigt den aktuell ausgewählten Parameternamen und gibt Ihnen alle Aktionsschaltflächen: Extrahieren/Ersetzen als Binärdatei, Wörterbuch-Parser mit Export/Import und untere Dienstprogrammschaltflächen (Suchen, Spenden, Schließen). Jede Aktion hat eine entsprechende Tastenkombination.</p><p><strong>Statusleiste</strong> — ganz unten im Fenster. Zeigt Live-Feedback: aktuelle Aktion, Dateiname, Suchergebnisse und eventuelle Fehler während des Parsens oder Ersetzens.</p><hr><h2>Menüs erklärt</h2><h3>Datei-Menü</h3> <p>Verwaltet Projektdateien, Bibliotheksimport, Überschreiben, Export, Magisk/ADB-Bereitstellung und Beenden der Anwendung. Projekte speichern die gesamte Bearbeitungssitzung einschließlich geladener Wörterbücher und des zuletzt ausgewählten Parameters.</p><ol> <li><strong>Projekt — Öffnen (Strg+O)</strong><br>Öffnet eine gespeicherte .QPPProj-Projektdatei. Lädt automatisch die zugehörige Bibliothek und stellt die vorherige Bearbeitungssitzung wieder her.</li> <li><strong>Projekt — Speichern (Strg+S)</strong><br>Speichert die aktuelle Sitzung in der geöffneten Projektdatei. Nur verfügbar, nachdem ein Projekt geladen oder zum ersten Mal gespeichert wurde.</li> <li><strong>Projekt — Speichern unter… (Strg+Umschalt+S)</strong><br>Speichert die Sitzung als neue .QPPProj-Datei an einem von Ihnen gewählten Ort.</li> <li><strong>Bibliothek — Importieren (Strg+L)</strong><br>Öffnet eine .bin- oder .so-Chromatix-Kamerabibliotheksdatei, parst sie im Hintergrund und füllt die Parameterliste.</li> <li><strong>Bibliothek — Überschreiben</strong><br>Schreibt alle aktuellen Änderungen zurück in die ursprüngliche Bibliotheksdatei auf der Festplatte. Bei .bin-Dateien wird die Prüfsumme automatisch neu berechnet.</li> <li><strong>Bibliothek — Exportieren als…</strong><br>Speichert eine Kopie der modifizierten Bibliothek in einem neuen Dateipfad, ohne das Original zu berühren.</li> <li><strong>Bibliothek — Änderungen rückgängig machen</strong><br>Stellt die Bibliothek auf den Zustand beim letzten Import wieder her (aus einem automatischen .bak-Backup). Nützlich, um alle Bearbeitungen rückgängig zu machen.</li> <li><strong>Bibliothek als Magisk exportieren (Strg+Umschalt+M)</strong><br>Verpackt die aktuelle Bibliothek in ein flashbares Magisk-Modul-ZIP, das auf einem gerooteten Android-Gerät installiert werden kann.</li> <li><strong>Bibliothek über ADB exportieren (Strg+Umschalt+A)</strong><br>Schiebt die modifizierte Bibliothek direkt auf ein verbundenes Android-Gerät mit ADB (Android Debug Bridge).</li> <li><strong>Beenden</strong><br>Schließt die Anwendung. Fordert zum Speichern ungespeicherter Änderungen auf, falls solche erkannt werden.</li> </ol><h3>Bearbeiten-Menü</h3> <p>Bietet Suchfunktionalität über Parameternamen und rohe Binärinhalte. Die Hex-Suche durchsucht die tatsächlichen Dateibytes, nicht nur die Parameterliste.</p> <ol> <li><strong>Parameter suchen (Strg+F)</strong><br>Öffnet den Suchdialog mit zwei Registerkarten — Suche nach Namen (Textsuche, Vorwärts/Rückwärts) und Suche nach Hex (Suche nach rohem Bytemuster in der Datei).</li> </ol><h3>Ansicht-Menü</h3> <p>Steuert Baumausklappung, Hex-Betrachter und Sortierreihenfolge der Parametertabelle. Die Sortierung betrifft nur die Tabellenansicht; die Baumansicht folgt der ursprünglichen strukturellen Hierarchie.</p> <ol> <li><strong>Baum ein-/ausklappen (Umschalt+C)</strong><br>Schaltet alle Knoten in der Baumansicht zwischen vollständig eingeklappt und vollständig ausgeklappt um.</li> <li><strong>Hex-Betrachter anzeigen (Strg+D)</strong><br>Öffnet ein schreibgeschütztes Hex-Dump-Fenster für den aktuell ausgewählten Parameter. Zeigt Offset, Hex-Bytes und ASCII nebeneinander an.</li> <li><strong>Hex-Editor anzeigen (Strg+Umschalt+D)</strong><br>Öffnet ein bearbeitbares Hex-Fenster für den ausgewählten Parameter, sodass Sie rohe Bytes direkt ändern und zurückschreiben können.</li> <li><strong>Sortieren → Wie geparst</strong><br>Behält die Reihenfolge der Parameter bei, in der sie in der Bibliotheksdatei gefunden wurden (Standard).</li> <li><strong>Sortieren → Nach ID</strong><br>Sortiert Parameter numerisch nach ihrer internen ID.</li> <li><strong>Sortieren → Nach Offset</strong><br>Sortiert Parameter nach ihrem Byte-Offset in der Datei – nützlich für sequentielle Binäranalyse.</li> </ol><h3>Extras-Menü</h3> <p>Enthält Dienstprogramme zur Wörterbucherstellung. Der integrierte Creator funktioniert ohne externe Abhängigkeiten, während der Benutzer-Wörterbuch-Creator erweiterte Workflows unterstützt.</p> <ol> <li><strong>Parser-Wörterbuch-Creator (Umschalt+D)</strong><br>Öffnet das integrierte Tool zum Erstellen eines neuen .Qdict-Wörterbuchs – ordnet Parameter-IDs menschenlesbaren Namen und Wertbeschreibungen zu.</li> <li><strong>Benutzer-Wörterbuch-Creator (Strg+Umschalt+D)</strong><br>Erscheint nur, wenn ein benutzerbereitgestelltes QTIDictionaryCreator-Binärmodul installiert ist. Startet das externe benutzerdefinierte Wörterbucherstellungstool.</li> </ol><h3>Plugins-Menü</h3> <p>Listet integrierte Automatisierungstools und alle Drittanbieter-Plugins auf. Plugins erweitern die Anwendung, ohne ihren Kerncode zu ändern.</p> <ol> <li><strong>Auto Tree Sorter V2</strong><br>Ordnet die Baumansicht automatisch neu und formatiert sie – gruppiert Parameter nach Modultyp und bereinigt die Hierarchie.</li> <li><strong>Batch-Binär-Export/Import-Tool</strong><br>Exportiert oder importiert mehrere ausgewählte Parameter als Binärdateien in einem einzigen Vorgang – nützlich für Massenbearbeitungsworkflows.</li> <li><strong>Rows Export Tool</strong><br>Exportiert ausgewählte Zeilen (Parameter) in eine Text- oder Datendatei zur externen Überprüfung oder Weitergabe.</li> <li><strong>Rows Import Tool</strong><br>Importiert eine zuvor exportierte Zeilendatei und wendet die Werte zurück in die aktuelle Bibliothek an.</li> <li><strong>Benutzer-Plugins</strong><br>Listet alle im Plugins/-Ordner installierten Drittanbieter-Plugins auf. Jedes erscheint als Menüpunkt und kann gegen die aktuell geladene Bibliothek ausgeführt werden.</li> <li><strong>Plugin installieren…</strong><br>Öffnet einen Dateiauswahl-Dialog, um ein neues Benutzer-Plugin (.py / .so / .pyd) in das Plugins-Verzeichnis zu installieren, ohne die Anwendung neu zu starten.</li> </ol><h3>Weitere Menüs</h3> <p>Bietet Hilfe, Info und Spendenoptionen. Die integrierte Hilfereferenz ist kontextabhängig, wenn ein Parameter ausgewählt ist.</p> <ol> <li><strong>Info</strong><br>Zeigt Anwendungsversion, Autor und Lizenzinformationen an.</li> <li><strong>Hilfe</strong><br>Öffnet die integrierte Hilfereferenz für die QTI Parameter Extractor/Replacer-Funktionalität.</li> <li><strong>Spenden</strong><br>Öffnet das Unterstützungs-/Spendenfenster. Wie die Spenden-Schaltfläche im rechten Bereich.</li> </ol><hr><h2>Schaltflächen des Steuerungsbereichs</h2><h3>Extrahieren / Ersetzen als Binärdatei</h3> <p><strong>Extrahieren</strong> — speichert die rohen Bytes des ausgewählten Parameters in einer .bin-Datei auf der Festplatte.<br><strong>Ersetzen</strong> — lädt eine von Ihnen gewählte .bin-Datei und schreibt deren Bytes an der Position des Parameters zurück in die Bibliothek.<br>Tastenkürzel: Strg+E / Strg+R.</p><h3>Wörterbuch-Parser (integriert)</h3> <p><strong>Wörterbuch-Dropdown</strong> — wählen Sie eine geladene .Qdict-Datei (oder "Import *.Qdict", um eine von der Festplatte zu laden). Definiert, wie Parameterwerte dekodiert werden.<br><strong>Wörterbuch automatisch finden</strong> — Kontrollkästchen. Wenn aktiviert, wird die Wörterbuchliste automatisch gefiltert, um dem Namen des aktuell ausgewählten Parameters zu entsprechen.<br><strong>Export</strong> — extrahiert die dekodierten Daten des ausgewählten Parameters mit dem gewählten Wörterbuch.<br><strong>Import</strong> — schreibt bearbeitete/dekodierte Daten mit dem Wörterbuchformat zurück in den Parameter.<br>Tastenkürzel: Strg+Umschalt+E / Strg+Umschalt+I.</p><h3>Untere Schaltflächen (Suchen, Spenden, Schließen)</h3> <p><strong>Suchen</strong> — öffnet den Suchdialog (wie Strg+F).<br><strong>Spenden :)</strong> — öffnet das Spendenfenster.<br><strong>Schließen</strong> — schließt die Anwendung.</p><hr><h2>Suchdialog</h2> <p>Geöffnet über Bearbeiten → Parameter suchen oder Strg+F oder die Suchen-Schaltfläche. Enthält zwei Registerkarten für flexible Suche über Namen und rohe Hex-Muster.</p><h3>Registerkarte 1 — Suche "Name"</h3> <p>Geben Sie einen Teil eines Parameternamens in das Textfeld ein. Vorwärts suchen springt zur nächsten übereinstimmenden Zeile unterhalb der aktuellen Auswahl. Rückwärts suchen springt zur vorherigen übereinstimmenden Zeile oberhalb. Die Suche ist standardmäßig nicht case-sensitiv.</p><h3>Registerkarte 2 — Suche "Hex"</h3> <p>Geben Sie eine rohe Bytesequenz in Hex ein (z.B. <code>01 02 0A 0B</code>). Vorwärts/Rückwärts durchsucht die Binärdatei nach dem Bytemuster und wählt den Parameter aus, der es enthält. Der Dialog zeigt die Byteanzahl während der Eingabe an, um die Musterlänge zu validieren.</p><hr><h2>Tastaturkürzel</h2> <p>Alle Hauptaktionen haben spezielle Kürzel für einen schnellen, tastaturgesteuerten Workflow. Auf macOS verwenden Sie Cmd (⌘) anstelle von Strg.</p> <ol> <li><strong>Strg+O</strong> — Projekt öffnen</li> <li><strong>Strg+S</strong> — Projekt speichern</li> <li><strong>Strg+Umschalt+S</strong> — Projekt speichern unter…</li> <li><strong>Strg+L</strong> — Bibliotheksdatei importieren</li> <li><strong>Strg+F</strong> — Suchdialog öffnen</li> <li><strong>Strg+E</strong> — Ausgewählten Parameter als Binärdatei extrahieren</li> <li><strong>Strg+R</strong> — Ausgewählten Parameter aus Binärdatei ersetzen</li> <li><strong>Strg+D</strong> — Hex-Betrachter öffnen</li> <li><strong>Strg+Umschalt+D</strong> — Hex-Editor öffnen</li> <li><strong>Strg+Umschalt+E</strong> — Wörterbuch-Export</li> <li><strong>Strg+Umschalt+I</strong> — Wörterbuch-Import</li> <li><strong>Strg+Umschalt+C</strong> — Prüfsumme reparieren</li> <li><strong>Strg+Umschalt+M</strong> — Als Magisk-Modul exportieren</li> <li><strong>Strg+Umschalt+A</strong> — Über ADB exportieren</li> <li><strong>Umschalt+C</strong> — Baum ein-/ausklappen</li> <li><strong>Umschalt+D</strong> — Parser-Wörterbuch-Creator</li> </ol> <p>macOS-Hinweis: Alle Strg-Kürzel verwenden Cmd (⌘) stattdessen. Zum Beispiel wird Strg+S zu Cmd+S.</p><hr><h2>Schritt-für-Schritt-Beispiel</h2> <p>Dieser typische Workflow führt Sie vom Öffnen einer Bibliothek bis zur Bereitstellung einer modifizierten Version auf einem Android-Gerät.</p> <ol> <li>Gehen Sie zu <strong>Datei → Bibliothek — Importieren</strong> (<code>Strg+L</code>) und öffnen Sie Ihre .bin- oder .so-Kamerabibliothek.</li> <li>Warten Sie, bis das Parsen abgeschlossen ist. Die Tabelle wird mit allen gefundenen Parametern (IDs, Namen, Offsets und Größen) gefüllt.</li> <li>Verwenden Sie die <strong>Baum</strong>-Registerkarte oder drücken Sie <code>Strg+F</code>, um den zu bearbeitenden Parameter zu finden.</li> <li>Klicken Sie auf die Zeile, um sie auszuwählen. Der rechte Bereich zeigt seinen Namen und aktiviert die Aktionsschaltflächen.</li> <li>Drücken Sie <code>Strg+D</code>, um seine rohen Bytes im Hex-Betrachter zu inspizieren, oder <code>Strg+Umschalt+D</code>, um sie direkt zu bearbeiten.</li> <li>Alternativ verwenden Sie <strong>Extrahieren</strong> (<code>Strg+E</code>), um den Parameter als Datei zu speichern, extern zu bearbeiten, dann <strong>Ersetzen</strong> (<code>Strg+R</code>), um ihn zurückzuschreiben.</li> <li>Nach allen Bearbeitungen gehen Sie zu <strong>Datei → Bibliothek — Überschreiben</strong>, um Änderungen in der Bibliothek zu speichern. Die Prüfsumme wird bei .bin-Dateien automatisch korrigiert.</li> <li>Verwenden Sie <strong>Als Magisk exportieren</strong> (<code>Strg+Umschalt+M</code>) oder <strong>Über ADB exportieren</strong> (<code>Strg+Umschalt+A</code>), um das Ergebnis auf Ihrem Gerät bereitzustellen.</li> <li>Speichern Sie Ihre Sitzung mit <strong>Datei → Projekt — Speichern</strong> (<code>Strg+S</code>), um später fortzufahren.</li> </ol><h3>Links</h3> <ul> <li><a href="https://www.youtube.com/@Lensonphone">Videoanleitungen</a></li> <li><a href="https://t.me/lensonphone">Telegram-Community</a></li> <li><a href="https://github.com/lensonphone">Github</a></li> <li><a href="https://www.instagram.com/reallensonphone/">Instagram</a></li> <li><a href="https://forms.gle/6Zt1sqStiWiPhRFJ7">Kontakt</a></li> </ul>
""",

"Français": """
<h2>Ce que fait ce programme</h2> <p>ParaParser-Editor est un outil de bureau pour analyser, inspecter et modifier des paramètres binaires dans les bibliothèques de réglage d'appareil photo Qualcomm Chromatix (fichiers .bin / .so). Il offre un environnement professionnel pour les ingénieurs en réglage d'appareil photo et les moddeurs avancés.</p><hr><h3>Ouverture et analyse des bibliothèques</h3> <p>Charge les bibliothèques d'appareil photo Qualcomm Chromatix (.bin ou .so) et extrait tous les paramètres — leurs ID, noms, décalages et tailles. L'analyseur détecte automatiquement la structure interne et construit une carte complète des paramètres.</p><h3>Navigation dans les paramètres</h3> <p>Affiche les paramètres analysés dans une vue tableau consultable ou une vue arborescente hiérarchique pour une navigation facile. Vous pouvez trier les colonnes, filtrer les entrées et passer rapidement entre différents groupes de paramètres.</p><h3>Extraction et remplacement</h3> <p>Permet d'extraire n'importe quel paramètre sous forme de blob binaire et de réécrire une version modifiée dans le fichier de bibliothèque. Utile pour l'édition hexadécimale externe ou l'application de valeurs de réglage précalculées.</p><h3>Support des dictionnaires</h3> <p>Utilise des fichiers de dictionnaire .Qdict pour décoder les valeurs des paramètres sous une forme lisible par l'homme et importer/exporter des préréglages nommés. Les dictionnaires comblent le fossé entre les données binaires brutes et les paramètres significatifs de l'appareil photo.</p><h3>Inspection hexadécimale</h3> <p>Visualiseur hexadécimal et éditeur hexadécimal intégrés vous permettent d'inspecter ou de modifier directement les octets bruts à l'intérieur d'un paramètre sélectionné. Les modes lecture seule et édition sont disponibles avec des mises à jour en temps réel.</p><h3>Export Magisk / ADB</h3> <p>Emballer la bibliothèque modifiée sous forme de module Magisk prêt à être flashé ou l'envoie à un appareil Android connecté via ADB. Cela simplifie le déploiement sur les appareils rootés sans copie manuelle des fichiers.</p><hr><h2>Structure de la fenêtre</h2> <p>La fenêtre principale est divisée en deux panneaux côte à côte. Le panneau gauche affiche la liste des paramètres et le panneau droit fournit toutes les commandes d'édition et d'export.</p><h3>Panneau gauche — Liste des paramètres</h3> <p>Contient deux onglets entre lesquels vous pouvez basculer : Tableau (liste plate avec colonnes ID, Nom, Décalage, Longueur) et Arborescence (hiérarchie pliable par module/groupe). Cliquez sur une ligne pour sélectionner un paramètre. Double-cliquez sur n'importe quelle ligne ou nœud pour ouvrir immédiatement le visualiseur hexadécimal.</p><h3>Panneau droit — Commandes</h3> <p>Affiche le nom du paramètre actuellement sélectionné et vous donne tous les boutons d'action : Extraire/Remplacer en binaire, Analyseur de dictionnaire avec Export/Import, et les boutons d'outils en bas (Rechercher, Faire un don, Fermer). Chaque action a un raccourci clavier correspondant.</p><p><strong>Barre d'état</strong> — tout en bas de la fenêtre. Affiche des commentaires en direct : action en cours, nom du fichier, résultats de recherche et toute erreur lors de l'analyse ou du remplacement.</p><hr><h2>Explication des menus</h2><h3>Menu Fichier</h3> <p>Gère les fichiers de projet, l'importation de bibliothèque, l'écrasement, l'exportation, le déploiement Magisk/ADB et la fermeture de l'application. Les projets sauvegardent toute la session d'édition, y compris les dictionnaires chargés et le dernier paramètre sélectionné.</p><ol> <li><strong>Projet — Ouvrir (Ctrl+O)</strong><br>Ouvre un fichier de projet .QPPProj enregistré. Charge automatiquement la bibliothèque associée et restaure la session d'édition précédente.</li> <li><strong>Projet — Enregistrer (Ctrl+S)</strong><br>Sauvegarde la session en cours dans le fichier de projet ouvert. Disponible uniquement après qu'un projet a été chargé ou sauvegardé pour la première fois.</li> <li><strong>Projet — Enregistrer sous… (Ctrl+Maj+S)</strong><br>Sauvegarde la session sous un nouveau fichier .QPPProj à un emplacement de votre choix.</li> <li><strong>Bibliothèque — Importer (Ctrl+L)</strong><br>Ouvre un fichier de bibliothèque d'appareil photo .bin ou .so Chromatix, l'analyse en arrière-plan et remplit la liste des paramètres.</li> <li><strong>Bibliothèque — Écraser</strong><br>Écrit toutes les modifications actuelles dans le fichier de bibliothèque d'origine sur le disque. Pour les fichiers .bin, la somme de contrôle est recalculée automatiquement.</li> <li><strong>Bibliothèque — Exporter sous…</strong><br>Sauvegarde une copie de la bibliothèque modifiée vers un nouveau chemin de fichier sans toucher à l'original.</li> <li><strong>Bibliothèque — Annuler les modifications</strong><br>Restaure la bibliothèque à l'état où elle était lors du dernier import (à partir d'une sauvegarde .bak automatique). Utile pour annuler toutes les modifications.</li> <li><strong>Exporter la bibliothèque en tant que Magisk (Ctrl+Maj+M)</strong><br>Emballer la bibliothèque actuelle dans un ZIP de module Magisk flashable qui peut être installé sur un appareil Android rooté.</li> <li><strong>Exporter la bibliothèque via ADB (Ctrl+Maj+A)</strong><br>Envoie la bibliothèque modifiée directement à un appareil Android connecté en utilisant ADB (Android Debug Bridge).</li> <li><strong>Quitter</strong><br>Ferme l'application. Invite à enregistrer les modifications non sauvegardées si elles sont détectées.</li> </ol><h3>Menu Édition</h3> <p>Fournit une fonctionnalité de recherche dans les noms de paramètres et le contenu binaire brut. La recherche hexadécimale analyse les octets réels du fichier, pas seulement la liste des paramètres.</p> <ol> <li><strong>Rechercher un paramètre (Ctrl+F)</strong><br>Ouvre la boîte de dialogue de recherche avec deux onglets — Recherche par nom (recherche textuelle, Avant/Arrière) et Recherche par hexadécimal (recherche de motif d'octets bruts dans le fichier).</li> </ol><h3>Menu Affichage</h3> <p>Contrôle le développement de l'arborescence, les visualiseurs hexadécimaux et l'ordre de tri du tableau des paramètres. Le tri n'affecte que la vue Tableau ; la vue Arborescence suit la hiérarchie structurelle d'origine.</p> <ol> <li><strong>Réduire ou développer l'arborescence (Maj+C)</strong><br>Bascule tous les nœuds de la vue arborescente entre complètement réduit et complètement développé.</li> <li><strong>Afficher le visualiseur hexadécimal (Ctrl+D)</strong><br>Ouvre une fenêtre de dump hexadécimal en lecture seule pour le paramètre actuellement sélectionné. Affiche le décalage, les octets hexadécimaux et l'ASCII côte à côte.</li> <li><strong>Afficher l'éditeur hexadécimal (Ctrl+Maj+D)</strong><br>Ouvre une fenêtre hexadécimale modifiable pour le paramètre sélectionné, permettant de modifier directement les octets bruts et de les réécrire.</li> <li><strong>Trier → Comme analysé</strong><br>Conserve les paramètres dans l'ordre dans lequel ils ont été trouvés dans le fichier de bibliothèque (par défaut).</li> <li><strong>Trier → Par ID</strong><br>Trie les paramètres numériquement par leur ID interne.</li> <li><strong>Trier → Par décalage</strong><br>Trie les paramètres par leur décalage d'octets dans le fichier — utile pour l'analyse binaire séquentielle.</li> </ol><h3>Menu Outils</h3> <p>Contient des utilitaires de création de dictionnaires. Le créateur intégré fonctionne sans dépendances externes, tandis que le créateur de dictionnaire utilisateur prend en charge les flux de travail avancés.</p> <ol> <li><strong>Créateur de dictionnaire d'analyse (Maj+D)</strong><br>Ouvre l'outil intégré pour construire un nouveau dictionnaire .Qdict — mappe les ID de paramètres à des noms lisibles et des descriptions de valeurs.</li> <li><strong>Créateur de dictionnaire utilisateur (Ctrl+Maj+D)</strong><br>Apparaît uniquement si un module binaire QTIDictionaryCreator fourni par l'utilisateur est installé. Lance l'outil externe de création de dictionnaire personnalisé.</li> </ol><h3>Menu Plugins</h3> <p>Liste les outils d'automatisation intégrés et tous les plugins tiers. Les plugins étendent l'application sans modifier son code de base.</p> <ol> <li><strong>Auto Tree Sorter V2</strong><br>Réorganise et formate automatiquement la vue arborescente — regroupe les paramètres par type de module et nettoie la hiérarchie.</li> <li><strong>Outil d'exportation/importation par lots binaires</strong><br>Exporte ou importe plusieurs paramètres sélectionnés sous forme de fichiers binaires en une seule opération — utile pour les flux de travail de modification en masse.</li> <li><strong>Outil d'exportation de lignes</strong><br>Exporte les lignes sélectionnées (paramètres) vers un fichier texte ou de données pour examen externe ou partage.</li> <li><strong>Outil d'importation de lignes</strong><br>Importe un fichier de lignes précédemment exporté et applique les valeurs dans la bibliothèque actuelle.</li> <li><strong>Plugins utilisateur</strong><br>Liste tous les plugins tiers installés dans le dossier Plugins/. Chacun apparaît comme un élément de menu et peut être exécuté sur la bibliothèque actuellement chargée.</li> <li><strong>Installer un plugin…</strong><br>Ouvre un sélecteur de fichiers pour installer un nouveau plugin utilisateur (.py / .so / .pyd) dans le répertoire Plugins sans redémarrer l'application.</li> </ol><h3>Menu Plus</h3> <p>Fournit de l'aide, des informations sur le logiciel et des options de don. La référence d'aide intégrée est contextuelle lorsqu'un paramètre est sélectionné.</p> <ol> <li><strong>À propos</strong><br>Affiche la version de l'application, l'auteur et les informations de licence.</li> <li><strong>Aide</strong><br>Ouvre la référence d'aide intégrée pour la fonctionnalité d'extraction/remplacement de paramètres QTI.</li> <li><strong>Faire un don</strong><br>Ouvre la fenêtre de soutien/don. Identique au bouton Faire un don dans le panneau droit.</li> </ol><hr><h2>Boutons du panneau de contrôle</h2><h3>Extraire / Remplacer en tant que binaire</h3> <p><strong>Extraire</strong> — sauvegarde les octets bruts du paramètre sélectionné dans un fichier .bin sur le disque.<br><strong>Remplacer</strong> — charge un fichier .bin de votre choix et écrit ses octets dans la bibliothèque à la position du paramètre.<br>Raccourcis : Ctrl+E / Ctrl+R.</p><h3>Analyseur de dictionnaire (intégré)</h3> <p><strong>Liste déroulante des dictionnaires</strong> — sélectionnez un fichier .Qdict chargé (ou choisissez "Importer *.Qdict" pour en charger un depuis le disque). Définit comment les valeurs des paramètres sont décodées.<br><strong>Trouver automatiquement le dictionnaire</strong> — case à cocher. Lorsqu'elle est cochée, la liste des dictionnaires se filtre automatiquement pour correspondre au nom du paramètre actuellement sélectionné.<br><strong>Exporter</strong> — extrait les données décodées du paramètre sélectionné en utilisant le dictionnaire choisi.<br><strong>Importer</strong> — écrit les données décodées/modifiées dans le paramètre en utilisant le format du dictionnaire.<br>Raccourcis : Ctrl+Maj+E / Ctrl+Maj+I.</p><h3>Boutons du bas (Rechercher, Faire un don, Fermer)</h3> <p><strong>Rechercher</strong> — ouvre la boîte de dialogue de recherche (comme Ctrl+F).<br><strong>Faire un don :)</strong> — ouvre la fenêtre de don.<br><strong>Fermer</strong> — ferme l'application.</p><hr><h2>Boîte de dialogue de recherche</h2> <p>Ouverte via Édition → Rechercher un paramètre ou Ctrl+F ou le bouton Rechercher. Contient deux onglets pour une recherche flexible sur les noms et les motifs hexadécimaux bruts.</p><h3>Onglet 1 — Recherche "Nom"</h3> <p>Saisissez une partie d'un nom de paramètre dans le champ de texte. Rechercher vers l'avant saute à la ligne correspondante suivante en dessous de la sélection actuelle. Rechercher vers l'arrière saute à la ligne correspondante précédente au-dessus. La recherche ne tient pas compte de la casse par défaut.</p><h3>Onglet 2 — Recherche "Hexadécimal"</h3> <p>Entrez une séquence d'octets bruts en hexadécimal (par exemple <code>01 02 0A 0B</code>). Avant/Arrière analyse le fichier binaire à la recherche du motif d'octets et sélectionne le paramètre qui le contient. La boîte de dialogue affiche le nombre d'octets pendant que vous tapez, vous aidant à valider la longueur du motif.</p><hr><h2>Raccourcis clavier</h2> <p>Toutes les actions principales ont des raccourcis dédiés pour un flux de travail rapide axé sur le clavier. Sur macOS, utilisez Cmd (⌘) au lieu de Ctrl.</p> <ol> <li><strong>Ctrl+O</strong> — Ouvrir un projet</li> <li><strong>Ctrl+S</strong> — Enregistrer le projet</li> <li><strong>Ctrl+Maj+S</strong> — Enregistrer le projet sous…</li> <li><strong>Ctrl+L</strong> — Importer un fichier de bibliothèque</li> <li><strong>Ctrl+F</strong> — Ouvrir la boîte de dialogue de recherche</li> <li><strong>Ctrl+E</strong> — Extraire le paramètre sélectionné en binaire</li> <li><strong>Ctrl+R</strong> — Remplacer le paramètre sélectionné à partir d'un binaire</li> <li><strong>Ctrl+D</strong> — Ouvrir le visualiseur hexadécimal</li> <li><strong>Ctrl+Maj+D</strong> — Ouvrir l'éditeur hexadécimal</li> <li><strong>Ctrl+Maj+E</strong> — Exportation du dictionnaire</li> <li><strong>Ctrl+Maj+I</strong> — Importation du dictionnaire</li> <li><strong>Ctrl+Maj+C</strong> — Corriger la somme de contrôle</li> <li><strong>Ctrl+Maj+M</strong> — Exporter en tant que module Magisk</li> <li><strong>Ctrl+Maj+A</strong> — Exporter via ADB</li> <li><strong>Maj+C</strong> — Réduire / développer l'arborescence</li> <li><strong>Maj+D</strong> — Créateur de dictionnaire d'analyse</li> </ol> <p>Note macOS : Tous les raccourcis Ctrl utilisent Cmd (⌘) à la place. Par exemple, Ctrl+S devient Cmd+S.</p><hr><h2>Exemple étape par étape</h2> <p>Ce flux de travail typique vous guide depuis l'ouverture d'une bibliothèque jusqu'au déploiement d'une version modifiée sur un appareil Android.</p> <ol> <li>Allez dans <strong>Fichier → Bibliothèque — Importer</strong> (<code>Ctrl+L</code>) et ouvrez votre bibliothèque d'appareil photo .bin ou .so.</li> <li>Attendez la fin de l'analyse. Le tableau se remplira avec tous les paramètres trouvés (IDs, noms, décalages et tailles).</li> <li>Utilisez l'onglet <strong>Arborescence</strong> ou appuyez sur <code>Ctrl+F</code> pour localiser le paramètre que vous souhaitez modifier.</li> <li>Cliquez sur la ligne pour la sélectionner. Le panneau droit affiche son nom et active les boutons d'action.</li> <li>Appuyez sur <code>Ctrl+D</code> pour inspecter ses octets bruts dans le visualiseur hexadécimal, ou <code>Ctrl+Maj+D</code> pour les modifier directement.</li> <li>Alternativement, utilisez <strong>Extraire</strong> (<code>Ctrl+E</code>) pour sauvegarder le paramètre sous forme de fichier, modifiez-le en externe, puis <strong>Remplacer</strong> (<code>Ctrl+R</code>) pour le réécrire.</li> <li>Après toutes les modifications, allez dans <strong>Fichier → Bibliothèque — Écraser</strong> pour enregistrer les changements dans la bibliothèque. La somme de contrôle est corrigée automatiquement pour les fichiers .bin.</li> <li>Utilisez <strong>Exporter en tant que Magisk</strong> (<code>Ctrl+Maj+M</code>) ou <strong>Exporter via ADB</strong> (<code>Ctrl+Maj+A</code>) pour déployer le résultat sur votre appareil.</li> <li>Sauvegardez votre session avec <strong>Fichier → Projet — Enregistrer</strong> (<code>Ctrl+S</code>) afin de pouvoir continuer plus tard.</li> </ol><h3>Liens</h3> <ul> <li><a href="https://www.youtube.com/@Lensonphone">Instructions vidéo</a></li> <li><a href="https://t.me/lensonphone">Communauté Telegram</a></li> <li><a href="https://github.com/lensonphone">Github</a></li> <li><a href="https://www.instagram.com/reallensonphone/">Instagram</a></li> <li><a href="https://forms.gle/6Zt1sqStiWiPhRFJ7">Contact</a></li> </ul>
"""

        }

        self.lang_combo.setCurrentText("English")
        self.update_text("English")

    def update_text(self, lang):
        self.text.setHtml(self.help_texts.get(lang, ""))



if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = QTIHelpDialog()
    win.show()
    sys.exit(app.exec_())
