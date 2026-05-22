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
        self.setWindowTitle("About QTI Parametr Parser")
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
<h3>Overview</h3>
<p><strong>API Parameter Parser</strong> is a creative lab for camera engineers.</p>
<p>It opens QTI/Chromatix libraries, reads them like a book, lays the driver out into clear chapters, and gives you tools to gently rewrite the plot: from choosing the right library and surgical patching to batch processing, dictionary-based parameter decoding, and plugins that can implement any workflow. Transparent, reproducible, and respectful to the hardware.</p>

<hr>

<h2>About the Project</h2>
<p><strong>Idea:</strong><br>
API Parameter Parser was born from a simple desire: to return full control of the camera to the user.</p>
<p>We carefully reveal what’s usually sealed deep inside Chromatix/drivers—parameters, tables, curves—and translate it into a clear language. From there it’s up to you: understand, adjust, extend, assemble back, and see how the camera behaves in a new way.</p>

<h3>What this opens?</h3>
<ul>
  <li><strong>Freedom of choice:</strong> open any library or a specific Chromatix driver; work surgically or in batches.</li>
  <li><strong>Structural insight:</strong> auto-formatted parameter trees turn a binary file into something human-readable; complex blocks stop being “magic.”</li>
  <li><strong>Gentle patching:</strong> change only what’s needed—with integrity checks.</li>
  <li><strong>Dictionaries & reproducibility:</strong> a shared parameter dictionary turns binary work into a craft—results are stable, diffs are clean.</li>
  <li><strong>Plugins without ceilings:</strong> the open API lets you add your own reader, transformer, or exporter—from quick hacks to serious modules.</li>
</ul>

<h3>Key capabilities</h3>
<ul>
  <li><strong>API Control</strong> — a unified control panel: select libraries, open and save processing projects.</li>
  <li><strong>Extractor/Replacer</strong> — precision parameter surgery: pull out, modify, and put back.</li>
  <li><strong>Dictionary & Dictionary Creator</strong> — the project’s common language: create and share dictionaries, lock field names and types.</li>
  <li><strong>Parser by Dictionary</strong> — deterministic parsing: one schema → the same readable results every time.</li>
  <li><strong>Hex + Context</strong> — a convenient “eye” into the binary: from bytes to meaning.</li>
  <li><strong>Autoformat Tree / Rows Export / Batch Export-Import</strong> — built-in plugins for humans and machines, including CSV/tabular data for research pipelines.</li>
</ul>

<h3>How people use it</h3>
<p>Pick a library/driver → Recognize structure with the parser → Analyze tables (LSC, AWB, noise, focus, etc.) → Modify the needed nodes (from curve points to whole blocks) → Rebuild with checksum verification → Test on the device.</p>

<h3>Who it’s for</h3>
<ul>
  <li>Developers and researchers of ISP/camera stacks;</li>
  <li>Enthusiasts of mobile optics and image tuning;</li>
  <li>Teams that value transparency and reproducibility.</li>
</ul>

<h3>What makes it special</h3>
<ul>
  <li><strong>Open architecture:</strong> plugin API (reader/transformer/writer/hooks)—add support for new formats, signatures, and exporters.</li>
  <li><strong>Project culture:</strong> we value care. Not “breaking,” but craft-level tuning.</li>
</ul>

<h3>Ethical note</h3>
<p>The project is intended for working with your own devices/libraries and within the bounds of the law. Respect licenses, copyrights, and vendor restrictions.</p>

<h3>Goal</h3>
<p><strong>API Parameter Parser</strong> is more than a tool—it’s a stage for ideas. Add your plugins, share dictionaries, propose export formats and new scenarios. The broader our shared knowledge, the more naturally the camera speaks to us—and the more beautiful the image becomes.</p>
""",

"Deutsch": """
<h3>Übersicht</h3>
<p><strong>API Parameter Parser</strong> ist ein kreatives Labor für Kameraingenieure.</p>
<p>Er öffnet QTI/Chromatix-Bibliotheken, liest sie wie ein Buch, legt den Treiber in klare Kapitel und bietet Werkzeuge, um die Handlung sanft umzuschreiben: von der Wahl der richtigen Bibliothek und gezieltem Patchen bis hin zur Stapelverarbeitung, Wörterbuch-basiertem Parameter-Decoding und Plugins für jeden Workflow. Transparent, reproduzierbar und respektvoll gegenüber der Hardware.</p>

<hr>

<h2>Über das Projekt</h2>
<p><strong>Idee:</strong><br>
API Parameter Parser entstand aus dem einfachen Wunsch, dem Benutzer die volle Kontrolle über die Kamera zurückzugeben.</p>
<p>Wir legen offen, was normalerweise tief in Chromatix/Treibern versiegelt ist – Parameter, Tabellen, Kurven – und übersetzen es in eine klare Sprache. Ab da liegt es an Ihnen: verstehen, anpassen, erweitern, neu zusammensetzen und sehen, wie sich die Kamera anders verhält.</p>

<h3>Was eröffnet das?</h3>
<ul>
  <li><strong>Wahlfreiheit:</strong> Öffnen Sie jede Bibliothek oder einen bestimmten Chromatix-Treiber; arbeiten Sie gezielt oder in Stapeln.</li>
  <li><strong>Strukturelle Einsicht:</strong> Automatisch formatierte Parametertrees machen Binärdateien lesbar; komplexe Blöcke hören auf, „Magie“ zu sein.</li>
  <li><strong>Sanftes Patchen:</strong> Ändern Sie nur, was nötig ist – mit Integritätsprüfungen.</li>
  <li><strong>Wörterbücher & Reproduzierbarkeit:</strong> Ein gemeinsames Parameterwörterbuch macht Binärarbeit zu einem Handwerk – Ergebnisse sind stabil, Diffs sauber.</li>
  <li><strong>Plugins ohne Grenzen:</strong> Die offene API ermöglicht eigene Reader, Transformer oder Exporter – von schnellen Hacks bis zu komplexen Modulen.</li>
</ul>

<h3>Zentrale Funktionen</h3>
<ul>
  <li><strong>API Control</strong> — ein zentrales Bedienfeld: Bibliotheken auswählen, Projekte öffnen und speichern.</li>
  <li><strong>Extractor/Replacer</strong> — präzise Parameter-Chirurgie: herausziehen, ändern, zurückschreiben.</li>
  <li><strong>Dictionary & Dictionary Creator</strong> — die gemeinsame Sprache des Projekts: Wörterbücher erstellen und teilen, Feldnamen und Typen fixieren.</li>
  <li><strong>Parser nach Wörterbuch</strong> — deterministisches Parsing: ein Schema → jedes Mal dieselben lesbaren Ergebnisse.</li>
  <li><strong>Hex + Kontext</strong> — ein bequemes „Auge“ ins Binärfile: von Bytes zu Bedeutung.</li>
  <li><strong>Autoformat Tree / Rows Export / Batch Export-Import</strong> — eingebaute Plugins für Menschen und Maschinen, inkl. CSV/tabellarische Daten für Forschungspipelines.</li>
</ul>

<h3>Wie wird es genutzt</h3>
<p>Bibliothek/Treiber auswählen → Struktur mit Parser erkennen → Tabellen analysieren (LSC, AWB, Rauschen, Fokus usw.) → Benötigte Knoten ändern → Mit Checksummenprüfung neu aufbauen → Auf dem Gerät testen.</p>

<h3>Für wen?</h3>
<ul>
  <li>Entwickler und Forscher von ISP/Kamerastacks;</li>
  <li>Enthusiasten mobiler Optik und Bildabstimmung;</li>
  <li>Teams, die Transparenz und Reproduzierbarkeit schätzen.</li>
</ul>

<h3>Was macht es besonders</h3>
<ul>
  <li><strong>Offene Architektur:</strong> Plugin-API (Reader/Transformer/Writer/Hooks) – Unterstützung neuer Formate, Signaturen, Exporter.</li>
  <li><strong>Projektkultur:</strong> Wir legen Wert auf Sorgfalt. Kein „Zerstören“, sondern Handwerkskunst.</li>
</ul>

<h3>Ethischer Hinweis</h3>
<p>Das Projekt ist für die Arbeit mit eigenen Geräten/Bibliotheken und im Rahmen des Gesetzes gedacht. Respektieren Sie Lizenzen, Urheberrechte und Herstellerauflagen.</p>

<h3>Ziel</h3>
<p><strong>API Parameter Parser</strong> ist mehr als ein Werkzeug – es ist eine Bühne für Ideen. Fügen Sie Plugins hinzu, teilen Sie Wörterbücher, schlagen Sie Exportformate und neue Szenarien vor. Je größer unser gemeinsames Wissen, desto natürlicher spricht die Kamera – und desto schöner werden die Bilder.</p>
""",

"Français": """
<h3>Aperçu</h3>
<p><strong>API Parameter Parser</strong> est un laboratoire créatif pour les ingénieurs caméra.</p>
<p>Il ouvre les bibliothèques QTI/Chromatix, les lit comme un livre, divise le pilote en chapitres clairs et fournit des outils pour réécrire doucement l’histoire : du choix de la bonne bibliothèque et du patch chirurgical au traitement par lots, au décodage des paramètres basé sur un dictionnaire et aux plugins qui peuvent implémenter n’importe quel flux de travail. Transparent, reproductible et respectueux du matériel.</p>

<hr>

<h2>À propos du projet</h2>
<p><strong>Idée :</strong><br>
API Parameter Parser est né d’un désir simple : redonner à l’utilisateur le contrôle total de la caméra.</p>
<p>Nous révélons soigneusement ce qui est habituellement scellé dans Chromatix/pilotes — paramètres, tables, courbes — et le traduisons dans un langage clair. Ensuite, c’est à vous : comprendre, ajuster, étendre, réassembler et voir comment la caméra se comporte différemment.</p>

<h3>Ce que cela ouvre ?</h3>
<ul>
  <li><strong>Liberté de choix :</strong> ouvrir n’importe quelle bibliothèque ou un pilote Chromatix spécifique ; travailler chirurgicalement ou en lots.</li>
  <li><strong>Vision structurelle :</strong> des arbres de paramètres auto-formatés rendent un fichier binaire lisible ; les blocs complexes cessent d’être de la « magie ».</li>
  <li><strong>Patch doux :</strong> ne changez que ce qui est nécessaire — avec des contrôles d’intégrité.</li>
  <li><strong>Dictionnaires & reproductibilité :</strong> un dictionnaire partagé transforme le travail binaire en artisanat — résultats stables, diffs propres.</li>
  <li><strong>Plugins sans limite :</strong> l’API ouverte permet d’ajouter vos propres lecteurs, transformateurs ou exportateurs — des hacks rapides aux modules sérieux.</li>
</ul>

<h3>Fonctionnalités clés</h3>
<ul>
  <li><strong>API Control</strong> — un panneau de contrôle unifié : sélectionner des bibliothèques, ouvrir et sauvegarder des projets.</li>
  <li><strong>Extractor/Replacer</strong> — chirurgie de paramètre de précision : extraire, modifier, réinsérer.</li>
  <li><strong>Dictionnaire & Créateur</strong> — langage commun du projet : créer et partager des dictionnaires, verrouiller les noms et types de champs.</li>
  <li><strong>Parser par Dictionnaire</strong> — analyse déterministe : un schéma → mêmes résultats lisibles à chaque fois.</li>
  <li><strong>Hex + Contexte</strong> — un « œil » pratique dans le binaire : des octets au sens.</li>
  <li><strong>Arborescence auto-formatée / Export lignes / Export-Import par lot</strong> — plugins intégrés pour humains et machines, y compris CSV/données tabulaires pour pipelines de recherche.</li>
</ul>

<h3>Comment les gens l’utilisent</h3>
<p>Choisir une bibliothèque/pilote → Reconnaître la structure avec le parseur → Analyser les tables (LSC, AWB, bruit, focus, etc.) → Modifier les nœuds nécessaires → Reconstruire avec vérification de checksum → Tester sur l’appareil.</p>

<h3>Pour qui ?</h3>
<ul>
  <li>Développeurs et chercheurs en ISP/stacks caméra ;</li>
  <li>Passionnés d’optique mobile et de tuning d’image ;</li>
  <li>Équipes qui valorisent transparence et reproductibilité.</li>
</ul>

<h3>Ce qui le rend spécial</h3>
<ul>
  <li><strong>Architecture ouverte :</strong> API de plugin (lecteur/transformateur/écrivain/hooks) — prise en charge de nouveaux formats, signatures et exportateurs.</li>
  <li><strong>Culture de projet :</strong> nous valorisons le soin. Pas de « cassage », mais un tuning artisanal.</li>
</ul>

<h3>Note éthique</h3>
<p>Le projet est destiné à être utilisé avec vos propres appareils/bibliothèques et dans le respect de la loi. Respectez licences, droits d’auteur et restrictions des fournisseurs.</p>

<h3>Objectif</h3>
<p><strong>API Parameter Parser</strong> est plus qu’un outil — c’est une scène pour les idées. Ajoutez vos plugins, partagez des dictionnaires, proposez des formats d’export et de nouveaux scénarios. Plus notre savoir partagé est large, plus la caméra s’exprime naturellement — et plus belles seront les images.</p>
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
