import sys
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
    QPushButton, QFileDialog, QTabWidget, QLabel, QMessageBox, QGridLayout, QInputDialog,  
    QDialog, QSlider, QLineEdit, QDialogButtonBox, QTextBrowser, QMenu
)
from PyQt5.QtGui import QImage, QFont, QPixmap, QColor
from PyQt5.QtCore import Qt


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Parametr Parser - Editor")
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
<p>An open-source toolkit for parsing and editing Qualcomm Chromatix camera libraries. The application supports working with existing parsers while also providing a powerful built-in environment for analyzing, editing, and managing library modules. Users can open and modify individual modules, save full projects, generate Magisk modules, export patched libraries, or send modified files directly to Android devices through ADB.</p><h3>Plugin System & Extensibility</h3> <p>One of the main advantages of the project is its flexible plugin system. Plugins can directly interact with loaded libraries and detected modules, allowing developers and researchers to extend functionality without modifying the core application.</p><h3>Internal Parser & Analysis Tools</h3> <p>The software also includes a partially developed internal parser/editor that allows manual module markup, structure coloring, and XML export for further analysis or reverse engineering workflows.</p><h3>Main Features</h3> <ul> <li><strong>Chromatix library parsing and editing</strong></li> <li><strong>Module extraction and replacement</strong></li> <li><strong>Project save/load system</strong></li> <li><strong>Direct ADB export to devices</strong></li> <li><strong>Magisk module generation</strong></li> <li><strong>Built-in and user plugin support</strong></li> <li><strong>Internal parser with manual structure markup</strong></li> <li><strong>XML export support</strong></li> <li><strong>Open-source and extensible architecture</strong></li> </ul><p>Designed for advanced camera tuning, reverse engineering, and Qualcomm imaging research workflows.</p>""",


"Deutsch": """
<p>Ein Open-Source-Toolkit zum Parsen und Bearbeiten von Qualcomm Chromatix-Kamerabibliotheken. Die Anwendung unterstützt die Arbeit mit vorhandenen Parsern und bietet gleichzeitig eine leistungsstarke integrierte Umgebung zum Analysieren, Bearbeiten und Verwalten von Bibliotheksmodulen. Benutzer können einzelne Module öffnen und ändern, vollständige Projekte speichern, Magisk-Module generieren, gepatchte Bibliotheken exportieren oder geänderte Dateien direkt über ADB an Android-Geräte senden.</p><h3>Plugin-System & Erweiterbarkeit</h3> <p>Einer der Hauptvorteile des Projekts ist sein flexibles Plugin-System. Plugins können direkt mit geladenen Bibliotheken und erkannten Modulen interagieren, sodass Entwickler und Forscher die Funktionalität erweitern können, ohne die Kernanwendung ändern zu müssen.</p><h3>Interner Parser & Analyse-Tools</h3> <p>Die Software enthält außerdem einen teilweise entwickelten internen Parser/Editor, der manuelle Modulauszeichnung, Strukturfarbgebung und XML-Export für weitere Analysen oder Reverse-Engineering-Workflows ermöglicht.</p><h3>Hauptfunktionen</h3> <ul> <li><strong>Parsen und Bearbeiten von Chromatix-Bibliotheken</strong></li> <li><strong>Extraktion und Austausch von Modulen</strong></li> <li><strong>Projekt speichern / laden</strong></li> <li><strong>Direkter ADB-Export auf Geräte</strong></li> <li><strong>Generierung von Magisk-Modulen</strong></li> <li><strong>Unterstützung für integrierte und benutzerdefinierte Plugins</strong></li> <li><strong>Interner Parser mit manueller Strukturmarkierung</strong></li> <li><strong>XML-Export-Unterstützung</strong></li> <li><strong>Open-Source und erweiterbare Architektur</strong></li> </ul><p>Entwickelt für fortgeschrittenes Camera-Tuning, Reverse Engineering und Qualcomm-Imaging-Forschungsworkflows.</p>
""",

"Français": """
<p>Une boîte à outils open-source pour analyser et éditer les bibliothèques caméra Qualcomm Chromatix. L'application prend en charge le travail avec les analyseurs existants tout en fournissant un environnement intégré puissant pour analyser, éditer et gérer les modules de la bibliothèque. Les utilisateurs peuvent ouvrir et modifier des modules individuels, enregistrer des projets complets, générer des modules Magisk, exporter des bibliothèques modifiées ou envoyer des fichiers modifiés directement vers des appareils Android via ADB.</p><h3>Système de plugins & extensibilité</h3> <p>L'un des principaux avantages du projet est son système de plugins flexible. Les plugins peuvent interagir directement avec les bibliothèques chargées et les modules détectés, permettant aux développeurs et aux chercheurs d'étendre les fonctionnalités sans modifier l'application principale.</p><h3>Analyseur interne & outils d'analyse</h3> <p>Le logiciel comprend également un analyseur/éditeur interne partiellement développé qui permet le balisage manuel des modules, le coloriage structurel et l'exportation XML pour des analyses plus approfondies ou des workflows de rétro-ingénierie.</p><h3>Fonctionnalités principales</h3> <ul> <li><strong>Analyse et édition de bibliothèques Chromatix</strong></li> <li><strong>Extraction et remplacement de modules</strong></li> <li><strong>Système d'enregistrement/chargement de projets</strong></li> <li><strong>Exportation directe vers les appareils via ADB</strong></li> <li><strong>Génération de modules Magisk</strong></li> <li><strong>Support des plugins intégrés et utilisateur</strong></li> <li><strong>Analyseur interne avec balisage manuel des structures</strong></li> <li><strong>Support d'exportation XML</strong></li> <li><strong>Architecture open-source et extensible</strong></li> </ul><p>Conçu pour le réglage avancé des caméras, la rétro-ingénierie et les workflows de recherche en imagerie Qualcomm.</p>
"""

        }

        self.lang_combo.setCurrentText("English")
        self.update_text("English")

    def update_text(self, lang):
        self.text.setHtml(self.help_texts.get(lang, ""))



if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = AboutDialog()
    win.show()
    sys.exit(app.exec_())
