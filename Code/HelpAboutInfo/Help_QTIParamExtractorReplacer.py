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
<h2>QTI Param Control — Quick Help</h2>

<h3>What this tool does</h3>
<p>Think of it as a <em>book reader</em> for camera libraries.  
Each library contains many small “chapters” (parameters, tables, curves).  
The program shows them clearly and lets you <strong>extract</strong>, <strong>replace</strong>, or <strong>interpret</strong> them.</p>

<hr>

<h3>Main Workflow</h3>
<ol>
  <li><strong>Open a library</strong><br>
      Load a QTI <code>.bin</code> / Chromatix file.<br>
      The table lists all parameters inside (ID, Name, Offset, Length).</li>
  <li><strong>Select a parameter</strong><br>
      Click any row in the table.<br>
      Its name and position in the file appear on the right side.</li>
  <li><strong>Extract or Replace</strong><br>
      <ul>
        <li><strong>Extract</strong> → Save the selected parameter as a binary file.</li>
        <li><strong>Replace</strong> → Insert your edited binary back into the library.</li>
      </ul>
  </li>
  <li><strong>Use Dictionaries (Optional)</strong><br>
      A dictionary (<code>.Qdict</code>) translates raw binary into human-readable values.<br>
      <ul>
        <li>Choose one from the dropdown, or let Autofind pick automatically.</li>
        <li>You can also Export or Import dictionaries to share with others.</li>
      </ul>
  </li>
  <li><strong>CheckSum Fix (Optional)</strong><br>
      After editing, some libraries need checksum correction.<br>
      Press <em>CheckSum Fix</em> so the system accepts your changes.</li>
</ol>

<hr>

<h3>Two Views</h3>
<ul>
  <li><strong>Table View:</strong> Classic list with IDs, names, offsets, lengths.</li>
  <li><strong>Tree View:</strong> Groups parameters by type/module for easier navigation.</li>
</ul>

<hr>

<h3>Typical Pipeline</h3>
<ol>
  <li>Load library</li>
  <li>Pick parameter</li>
  <li>Extract</li>
  <li>Edit externally</li>
  <li>Replace</li>
  <li>Fix checksum</li>
  <li>Save &amp; test on device</li>
</ol>

<hr>

<h3>Reminder</h3>
<blockquote>
  This tool does not <em>guess</em> how values affect the camera.  
  It only makes the hidden parameters visible and editable.  
  <br><br>
  <strong>Always keep a backup</strong> of your original library before replacing anything.
</blockquote>

<h3>Useful Links</h3>
<ul>
  <li><a href="https://lensonphone.com/lens-on-phone-suite-learn-more.html">Video guides</a></li>
  <li><a href="https://t.me/lensonphone">Telegram Community</a></li>
  <li><a href="https://lensonphone.com/">Website</a></li>
  <li><a href="https://www.instagram.com/reallensonphone/">Instagram</a></li>
  <li><a href="https://forms.gle/6Zt1sqStiWiPhRFJ7">Join us</a></li>
  <li><a href="https://forms.gle/3qz3mGowrjZbCH579">Report problem</a></li>
</ul>
""",

"Deutsch": """
<h2>QTI Param Control — Kurzanleitung</h2>

<h3>Was dieses Tool macht</h3>
<p>Stellen Sie es sich als <em>Buchleser</em> für Kamerabibliotheken vor.  
Jede Bibliothek enthält viele kleine „Kapitel“ (Parameter, Tabellen, Kurven).  
Das Programm zeigt sie klar an und ermöglicht es Ihnen, sie zu <strong>extrahieren</strong>, <strong>ersetzen</strong> oder <strong>interpretieren</strong>.</p>

<hr>

<h3>Hauptablauf</h3>
<ol>
  <li><strong>Bibliothek öffnen</strong><br>
      Laden Sie eine QTI <code>.bin</code> / Chromatix-Datei.<br>
      Die Tabelle listet alle Parameter auf (ID, Name, Offset, Länge).</li>
  <li><strong>Parameter auswählen</strong><br>
      Klicken Sie auf eine Zeile in der Tabelle.<br>
      Sein Name und seine Position in der Datei erscheinen rechts.</li>
  <li><strong>Extrahieren oder Ersetzen</strong><br>
      <ul>
        <li><strong>Extrahieren</strong> → Speichern Sie den ausgewählten Parameter als Binärdatei.</li>
        <li><strong>Ersetzen</strong> → Fügen Sie Ihre bearbeitete Binärdatei wieder in die Bibliothek ein.</li>
      </ul>
  </li>
  <li><strong>Wörterbücher verwenden (optional)</strong><br>
      Ein Wörterbuch (<code>.Qdict</code>) übersetzt rohe Binärdaten in lesbare Werte.<br>
      <ul>
        <li>Wählen Sie eines aus der Dropdown-Liste, oder lassen Sie Autofind automatisch wählen.</li>
        <li>Sie können auch Wörterbücher exportieren oder importieren, um sie zu teilen.</li>
      </ul>
  </li>
  <li><strong>CheckSum Fix (optional)</strong><br>
      Nach der Bearbeitung benötigen einige Bibliotheken eine Prüfsummen-Korrektur.<br>
      Drücken Sie <em>CheckSum Fix</em>, damit das System Ihre Änderungen akzeptiert.</li>
</ol>

<hr>

<h3>Zwei Ansichten</h3>
<ul>
  <li><strong>Tabellenansicht:</strong> Klassische Liste mit IDs, Namen, Offsets, Längen.</li>
  <li><strong>Baumansicht:</strong> Gruppiert Parameter nach Typ/Modul für einfachere Navigation.</li>
</ul>

<hr>

<h3>Typischer Ablauf</h3>
<ol>
  <li>Bibliothek laden</li>
  <li>Parameter auswählen</li>
  <li>Extrahieren</li>
  <li>Extern bearbeiten</li>
  <li>Ersetzen</li>
  <li>Prüfsumme korrigieren</li>
  <li>Speichern &amp; auf Gerät testen</li>
</ol>

<hr>

<h3>Erinnerung</h3>
<blockquote>
  Dieses Tool <em>errät</em> nicht, wie Werte die Kamera beeinflussen.  
  Es macht nur die versteckten Parameter sichtbar und bearbeitbar.  
  <br><br>
  <strong>Erstellen Sie immer ein Backup</strong> Ihrer Originalbibliothek, bevor Sie etwas ersetzen.
</blockquote>

<h3>Nützliche Links</h3>
<ul>
  <li><a href="https://lensonphone.com/lens-on-phone-suite-learn-more.html">Videoanleitungen</a></li>
  <li><a href="https://t.me/lensonphone">Telegram-Community</a></li>
  <li><a href="https://lensonphone.com/">Webseite</a></li>
  <li><a href="https://www.instagram.com/reallensonphone/">Instagram</a></li>
  <li><a href="https://forms.gle/6Zt1sqStiWiPhRFJ7">Mitmachen</a></li>
  <li><a href="https://forms.gle/3qz3mGowrjZbCH579">Problem melden</a></li>
</ul>
""",

"Français": """
<h2>QTI Param Control — Aide rapide</h2>

<h3>Ce que fait cet outil</h3>
<p>Pensez-y comme à un <em>lecteur de livre</em> pour bibliothèques de caméras.  
Chaque bibliothèque contient de petits « chapitres » (paramètres, tables, courbes).  
Le programme les affiche clairement et vous permet de les <strong>extraire</strong>, <strong>remplacer</strong> ou <strong>interpréter</strong>.</p>

<hr>

<h3>Flux de travail principal</h3>
<ol>
  <li><strong>Ouvrir une bibliothèque</strong><br>
      Charger un fichier QTI <code>.bin</code> / Chromatix.<br>
      Le tableau répertorie tous les paramètres (ID, Nom, Offset, Longueur).</li>
  <li><strong>Sélectionner un paramètre</strong><br>
      Cliquez sur une ligne du tableau.<br>
      Son nom et sa position apparaissent à droite.</li>
  <li><strong>Extraire ou Remplacer</strong><br>
      <ul>
        <li><strong>Extraire</strong> → Sauvegarder le paramètre sélectionné comme fichier binaire.</li>
        <li><strong>Remplacer</strong> → Insérer votre binaire modifié dans la bibliothèque.</li>
      </ul>
  </li>
  <li><strong>Utiliser des dictionnaires (optionnel)</strong><br>
      Un dictionnaire (<code>.Qdict</code>) traduit le binaire brut en valeurs lisibles.<br>
      <ul>
        <li>Choisissez-en un dans le menu déroulant, ou laissez Autofind choisir automatiquement.</li>
        <li>Vous pouvez aussi Exporter ou Importer des dictionnaires pour les partager.</li>
      </ul>
  </li>
  <li><strong>Correction de CheckSum (optionnel)</strong><br>
      Après modification, certaines bibliothèques nécessitent une correction de somme de contrôle.<br>
      Appuyez sur <em>CheckSum Fix</em> pour que le système accepte vos changements.</li>
</ol>

<hr>

<h3>Deux vues</h3>
<ul>
  <li><strong>Vue tableau :</strong> Liste classique avec IDs, noms, offsets, longueurs.</li>
  <li><strong>Vue arborescente :</strong> Regroupe les paramètres par type/module pour une navigation plus facile.</li>
</ul>

<hr>

<h3>Pipeline typique</h3>
<ol>
  <li>Charger la bibliothèque</li>
  <li>Choisir un paramètre</li>
  <li>Extraire</li>
  <li>Modifier en externe</li>
  <li>Remplacer</li>
  <li>Corriger la somme de contrôle</li>
  <li>Sauvegarder &amp; tester sur l’appareil</li>
</ol>

<hr>

<h3>Rappel</h3>
<blockquote>
  Cet outil ne <em>devine</em> pas comment les valeurs affectent la caméra.  
  Il rend seulement les paramètres cachés visibles et modifiables.  
  <br><br>
  <strong>Gardez toujours une copie de sauvegarde</strong> de votre bibliothèque originale avant de remplacer quoi que ce soit.
</blockquote>

<h3>Liens utiles</h3>
<ul>
  <li><a href="https://lensonphone.com/lens-on-phone-suite-learn-more.html">Guides vidéo</a></li>
  <li><a href="https://t.me/lensonphone">Communauté Telegram</a></li>
  <li><a href="https://lensonphone.com/">Site web</a></li>
  <li><a href="https://www.instagram.com/reallensonphone/">Instagram</a></li>
  <li><a href="https://forms.gle/6Zt1sqStiWiPhRFJ7">Nous rejoindre</a></li>
  <li><a href="https://forms.gle/3qz3mGowrjZbCH579">Signaler un problème</a></li>
</ul>
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
