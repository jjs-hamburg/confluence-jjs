# JJS KODI Confluence Custom

**Aktueller Release: 5.0.126**

JJS KODI Confluence Custom ist ein stark erweiterter Confluence-Skin für Kodi Omega. Er basiert auf dem ursprünglichen Confluence von Jezz_X / Team Kodi, bleibt aber als eigener Skin vollständig von `skin.confluence` getrennt.

Die technische Add-on-ID bleibt dauerhaft:

`skin.confluence.custom`

Dadurch bleibt der Skin updatefähig, ohne eine vorhandene originale Confluence-Installation zu überschreiben.

> Die unveränderte Referenzversion 5.0.125 bleibt in der Git-Historie als **Confluence Custom** erhalten. Seit 5.0.126 lautet der sichtbare Skin-Name **JJS KODI Confluence Custom**; die technische Add-on-ID bleibt unverändert.

## Herkunft und Lizenz

Basis ist Confluence von **Jezz_X / Team Kodi**. Die ursprüngliche Herkunft wird ausdrücklich beibehalten.

Lizenz:

**GNU General Public License version 2**

Das Repository enthält außerdem Schriftarten mit ihren jeweiligen mitgelieferten Lizenzdateien.

## Ziel des Projekts

Der Skin behält die direkte, übersichtliche Bedienphilosophie von Confluence bei, erweitert sie aber insbesondere für große Musikbibliotheken, Fernbedienungsbedienung und eine stark konfigurierbare Startseite.

Schwerpunkte sind:

- erweiterte Musik-Wiedergabeinformationen
- frei konfigurierbare Coverdarstellung
- Audio- und Zeit-Badges
- eigener Song-Popup mit Playlist, Credits und Lyrics
- eigener Haupt-/Untermenü-Editor
- konfigurierbare Startseiten-Darstellung
- umschaltbarer **Custom-** und **Standard-Confluence-Modus**
- Skin-Einstellungen sichern/wiederherstellen
- gemeinsame eigene Library-Node-Defaults
- portable Factory Defaults für Neuinstallationen

## Installation

Das installierbare Kodi-ZIP wird automatisch aus dem Quellstand dieses Repositories erzeugt und als **GitHub Release** veröffentlicht.

1. Auf der Repository-Seite **Releases** öffnen.
2. Den gewünschten Release auswählen.
3. Unter **Assets** direkt `skin.confluence.custom-<Version>.zip` herunterladen.
4. In Kodi **Add-ons → Aus ZIP-Datei installieren** wählen.
5. Genau dieses ZIP installieren.

Es wird bewusst **kein GitHub-Actions-Artifact** veröffentlicht. GitHub würde ein solches Artifact selbst noch einmal als ZIP verpacken und damit ein unnötiges Doppel-ZIP erzeugen.

## Update-Verhalten

Der Skin verwendet weiterhin die ID:

`skin.confluence.custom`

Ein neuer Release wird deshalb von Kodi als Update derselben Skin-Installation erkannt. Vorhandene Skin-Einstellungen und das Skin-Profil bleiben erhalten.

Factory Defaults werden ausschließlich bei einer echten Neuinstallation angewendet. Ein normales Update überschreibt vorhandene Einstellungen nicht.

## Übernahme bestehender Confluence-Einstellungen

Beim ersten Start kann der Skin vorhandene Einstellungen des ursprünglichen Confluence übernehmen.

Diese Übernahme ist als einmalige Migration ausgelegt. Das originale `skin.confluence` bleibt dabei unangetastet.

## Custom und Standard Confluence

Der Skin enthält zwei vollständige Sätze der zentralen Confluence-XML-Dateien:

- **Custom**
- **Standard Confluence**

Umschaltbar sind unter anderem:

- `Font.xml`
- `Home.xml`
- `Includes.xml`
- `IncludesBackgroundBuilding.xml`
- `IncludesHomeMenuItems.xml`
- `SkinSettings.xml`

Beim Umschalten werden die gewünschten Dateien zunächst vollständig vorbereitet und geprüft und danach ersetzt. Ein Reload des Skins aktiviert den neuen Modus.

Nach einem Skin-Update prüft der Startup-Service automatisch, ob der zuvor gewählte Modus noch aktiv ist, und stellt gegebenenfalls den richtigen XML-Satz wieder her.

Damit kann derselbe installierte Skin wahlweise als weitgehend klassisches Confluence oder mit den JJS-Custom-Erweiterungen betrieben werden.

## Eigener Menüeditor

Der Skin benötigt **kein Skin Shortcuts**.

Der integrierte Menüeditor verwendet normale Kodi-Dialoge und erlaubt die Konfiguration der Startseite direkt im Skin.

Unterstützt werden unter anderem:

- Hauptmenü-Bezeichnungen ändern
- Hauptmenü-Ziele ändern
- Position der vom Editor verwalteten Hauptmenüs nach links/rechts verschieben
- Untermenüs frei editieren
- bis zu sieben Untermenü-Einträge pro Gruppe
- Library-Nodes als Ziel
- Favoriten als Ziel
- Add-on-Einsprungpunkte als Ziel
- vorhandenen Kodi-Eintrag direkt als Menüpunkt übernehmen

Während der Zielauswahl erscheinen im Kodi-Kontextmenü die temporären Einträge:

- **Diesen Eintrag als Menüpunkt übernehmen**
- **JJS-Confluence-Menüauswahl abbrechen**

## Lange Texteingaben

Die Texteingabe in `DialogKeyboard.xml` ist seit 5.0.126 so ausgelegt, dass Kodis Edit-Control bei langen Texten den sichtbaren Ausschnitt mit dem Cursor verschiebt.

Damit kann bei langen Datei- und Ordnernamen bis zum Anfang und wieder bis zum Ende navigiert werden. Der Skin setzt **keine zusätzliche Zeichenbegrenzung**. Für die praktische Prüfung ist insbesondere eine Länge von mindestens 255 Zeichen vorgesehen.

## Startseiten-Darstellung

Die Startseite lässt sich weit über das ursprüngliche Confluence hinaus konfigurieren.

Dazu gehören insbesondere:

- Hauptmenü-Schriftfamilie und -größe
- Hauptmenü-Normal- und Aktivfarbe
- vertikale Position des Hauptmenüs
- Untermenü-Schriftfamilie und -größe
- Untermenü-Farben
- Covergröße
- Coverstil
- Schattenart
- Schattenbreite
- Schattenversatz
- Floor-/Spiegelungsdarstellung
- Front-/Back-Cover-Darstellung
- No-Cover-Stil
- Funktion des Exit-/Power-Buttons
- optionales Ausblenden von Wiedergabe-Steuerelementen oberhalb der Menüzeile

Als Hauptmenüschrift stehen unter anderem **Roboto Bold** und **Montserrat Black** zur Verfügung.

## Coverdarstellung

Die Musikdarstellung auf der Startseite besitzt eine eigene, detailliert konfigurierbare Coverlogik.

### Covergröße

Die Covergröße ist unabhängig von den übrigen Wiedergabeinformationen konfigurierbar.

### Vorder- und Rückseite

Bei vorhandenem Back-Cover kann per Fokus/Enter durch die Zustände geschaltet werden:

1. Vorderseite
2. Vorderseite + Rückseite
3. Kompakt unten
4. kein Cover
5. zurück zur Vorderseite

Wenn kein Back-Cover existiert, wird die nicht verfügbare Paaransicht übersprungen.

### Kompakt unten

In der kompakten Ansicht verschwindet das große Cover oberhalb des Hauptmenüs vollständig. Stattdessen steht das Cover unten links direkt vor den Wiedergabeinformationen.

**Nur die Höhe ist fest definiert:** 115 px, entsprechend der Höhe des gesamten Wiedergabeinformationsblocks. Die Breite wird aus der tatsächlichen Bildproportion berechnet. Ein quadratisches Cover bleibt quadratisch, eine schmale Longbox bleibt schmal; nicht-quadratische Cover werden weder beschnitten noch auf ein Quadrat gezwungen.

Albumtitel, Songtitel, Zeiten und Badges werden gemeinsam nach rechts verschoben, sodass sie unmittelbar hinter der tatsächlich benötigten Coverbreite beginnen.

### No-Cover

Für Alben ohne echtes Cover stehen unterschiedliche Darstellungen zur Verfügung, darunter:

- eigenes Jewel-Case-Bild
- Confluence-/Kodi-Standard
- frei gewähltes eigenes Bild

Die benötigten Standardtexturen werden so verwaltet, dass auch Kodis allgemeine Musik-Platzhalter konsistent dargestellt werden.

## Cover-Schatten

Die Schattengeometrie wurde gegenüber dem ursprünglichen Confluence vollständig neu aufgebaut.

Eigenschaften:

- **Hart** oder **Weich**
- Schattenbreite von 6 bis 38 px
- Schattenversatz von 0 bis 24 px
- korrekte Geometrie auch bei ungewöhnlichen Cover-Seitenverhältnissen
- exakte Ausrichtung an der tatsächlich von Kodi dargestellten Bildfläche
- weiche Schatten als eigene Blur-/Nine-Slice-Texturen
- keine sichtbaren Coverkopien als Schattenersatz

## Wiedergabeinformationen

Die Wiedergabeinformationen besitzen eine eigene Konfigurationssektion.

### Albumzeile

Der Albumtitel kann bei Überlänge wahlweise:

- abgeschnitten
- gescrollt
- auf zwei Zeilen umgebrochen

werden.

Beim Umbruch bleibt ein einzeiliger Titel exakt auf der historischen Albumposition. Nur ein tatsächlich zu langer Titel wächst nach oben.

Optional kann das Albumjahr angezeigt werden. Ungültige Kodi-Jahre wie `0` oder `0000` werden unterdrückt.

## Zeitangaben

Für die Wiedergabe können vier Zeitinformationen unabhängig aktiviert werden:

- aktuelle Songzeit
- verbleibende Songzeit
- aktuelle Albumzeit
- verbleibende Albumzeit

Die Zeiten können normal oder in eigenen **Zeit-Badges** dargestellt werden.

### Zeit-Badges

Zeit-Badges verwenden dieselbe optische Grundsprache wie das Audio-Badge.

Eigenschaften in 5.0.125:

- kompakte, inhaltsabhängige Breite
- ungefähr 10 px horizontaler Innenabstand
- Zeit-Schrift bleibt immer hell
- optional **alle Zeit-Badges gleich breit**
- bei Gleichbreite bestimmt die längste aktuell sichtbare Zeitangabe die gemeinsame Breite

## Audio-Badge

Codec und Kanalinformation können als gemeinsames Audio-Badge angezeigt werden.

Unterstützt werden unter anderem:

- Codec als Logo oder Text
- Kanalangaben wie 2.0, 5.1, 7.1 oder 5.1.4
- Größe von 80 bis 180 %
- Hintergrund Schwarz, Anthrazit, Confluence-Blau oder wie Untermenü
- Deckkraft 25–85 %
- 3D-Badge
- feste saubere Rundung
- dynamische Position rechts hinter den tatsächlich sichtbaren Zeitangaben

Codec- und Kanalinformationen bleiben dabei getrennt von Albumtitel und Albumjahr.

## Song-Popup

Der Skin besitzt einen eigenen, fernbedienungsfreundlichen Song-Popup für laufende Musikwiedergabe.

Die Ansichten bilden einen zyklischen Bereich aus:

- **Songliste**
- **Credits / Besetzung**
- **Lyrics**

Links und Rechts wechseln zyklisch zwischen den verfügbaren Seiten.

### Songliste

Die Songliste verwendet eine echte Kodi-Liste und kann den laufenden Titel automatisch nachführen.

Konfigurierbar sind unter anderem:

- Schriftfamilie
- Schriftgröße
- Normalfarbe
- Farbe des laufenden Songs
- Fokus-/Aktivfarbe
- Highlight-Farbe
- Tracknummern
- automatisches Öffnen
- Auswahl-/Fokus-/Highlight-Timeouts
- Hintergrunddarstellung

Seit 5.0.125 gilt:

- nach Ablauf des Highlight-Timeouts markiert der erste Hoch-/Runter-Druck zunächst den aktuellen Song
- das Highlight bleibt bis zum nächsten Timeout sichtbar
- erst der folgende Hoch-/Runter-Druck bewegt den Fokus zum Nachbartitel

### Credits / Besetzungsdaten

Der Popup kann die vom **JJS KODI Music Library Manager** bereitgestellten Credits/Besetzungsdaten anzeigen.

Die Credits sind als scrollbare, kompakte Zeilenansicht integriert und für Bedienung mit Fernbedienung ausgelegt.

## Lyrics

Der Song-Popup unterstützt Lyrics aus einer kompatiblen **CU LRC Lyrics**-Installation.

Unterstützt werden:

- normale Klartext-Lyrics
- LRC-Zeitmarken
- synchrones Nachführen
- manuelles Scrollen
- Enter/OK zum Umschalten zwischen synchronem und manuellem Modus
- konfigurierbare LRC-Sync-Verzögerung
- zentrierte oder normale Darstellung
- automatische Ausblendung der Lyrics-Seite, wenn definitiv kein Text vorhanden ist

Der Skin berücksichtigt dabei auch CU-LRC-Offset sowie eingebettete LRC-`[offset:]`-Tags.

## Library-Nodes

Der Skin liefert gemeinsame Library-Node-Defaults für Custom und Standard Confluence mit.

### Musik

Unter anderem:

- Zuletzt hinzugefügt – 50 Alben
- Zuletzt gehört – 50 tatsächlich gehörte Alben, nach letzter Wiedergabe
- Interpreten
- Dateien
- Genres
- Jahre
- Musikrollen / Contributors
- Boxsets
- Top 100
- Playlists
- Musikvideos

### Video

Eigene Standard-Nodes werden auch für Filme und Serien geliefert.

Bei einer echten Neuinstallation werden nur fehlende Profil-Nodes angelegt. Vorhandene Node-Dateien werden nicht ungefragt überschrieben.

Mit **Library-Nodes auf Skin-Standard zurücksetzen** können die mitgelieferten Musik-/Video-Node-Bäume bewusst vollständig wiederhergestellt werden.

## Factory Defaults

Für eine echte Neuinstallation enthält der Skin einen portablen, getesteten Grundeinstellungsstand.

Wichtige Eigenschaften:

- nur bei echter Neuinstallation
- vorhandene Installationen werden bei Updates nicht überschrieben
- portables Default-Wallpaper über `special://skin/...`
- Pending-/Skip-Marker schützen vor halb abgeschlossener Initialisierung
- die Defaults können gezielt aus den Skin-Einstellungen heraus zurückgesetzt werden

## Skin-Einstellungen sichern und wiederherstellen

Alle aktiven **skin-spezifischen** Bool-/String-Einstellungen können als JSON gesichert und wiederhergestellt werden.

Die Sicherung enthält ausschließlich Einstellungen von `skin.confluence.custom`. Allgemeine Kodi-Einstellungen werden absichtlich nicht verändert.

Der Ziel- bzw. Quellpfad wird über Kodis Dateibrowser gewählt; dadurch sind auch über Kodi erreichbare SMB-/VFS-Ziele nutzbar.

Restore ist ein echter Snapshot-Restore und nicht nur ein Merge:

- Einstellungen aus der Sicherung werden gesetzt
- aktuelle Skin-Einstellungen, die in der Sicherung nicht vorhanden waren, werden zurückgesetzt
- allgemeine Kodi-Einstellungen bleiben unangetastet

## Skin-Service

Der Skin enthält einen eigenen Python-Service, der beim Kodi-Login gestartet wird.

Er übernimmt unter anderem Laufzeitaufgaben für:

- Song-Popup
- Zeit-/Albumzeitberechnung
- Highlight- und Fokuslogik
- Lyrics-Synchronisation
- Credits-Anzeige
- dynamische Zeit-Badge-Breiten
- lange Albumtitel / zweizeilige Darstellung
- Wiedergabezustände

## Projektstruktur

Der installierbare Skin liegt vollständig unter:

`skin.confluence.custom/`

Wichtige Bereiche:

- `addon.xml` – Add-on-ID, Version, Skin-/Service-/Kontextmenü-Registrierung
- `1080p/` – aktiver XML-Satz des Skins
- `resources/skin_modes/custom/` – Custom-XML-Satz
- `resources/skin_modes/standard/` – Standard-Confluence-XML-Satz
- `resources/lib/` – Menüeditor, Startup, Skin-Service, Settings-/Factory-/Node-Verwaltung
- `resources/library_nodes/` – mitgelieferte Musik-/Video-Nodes
- `resources/factory-default-settings.json` – Defaults für echte Neuinstallationen
- `media/` – Skin-Grafiken, Badges, Schatten und Codec-Logos
- `backgrounds/` – Standardhintergründe
- `fonts/` – mitgelieferte Schriften und Lizenzinformationen
- `language/` – Confluence-Sprachressourcen
- `changelog.txt` – fortlaufende Entwicklungshistorie
- `TEST-NOTES-*.txt` – konkrete Testhinweise der jeweiligen Entwicklungsstände
- `README-CONFLUENCE-CUSTOM.txt` – historische Projektbeschreibung

## Build und Release

Der GitHub-Workflow prüft vor dem Paketieren:

- gültiges `addon.xml`
- Add-on-ID `skin.confluence.custom`
- vorhandene Versionsnummer
- Skin-Extension `xbmc.gui.skin`
- Python-Syntax der Skin-Service-/Hilfsskripte
- Vorhandensein der Custom- und Standard-XML-Sätze
- Vorhandensein zentraler Skin-Dateien
- genau einen Skin-Root im ZIP
- ZIP-Integrität

Das Release-Asset heißt:

`skin.confluence.custom-<Version>.zip`

und ist direkt in Kodi installierbar.

## Versionsbasis

Der zuerst in dieses Repository übernommene, unveränderte und getestete Referenzstand ist:

**5.0.125 – timebadges-popup-highlight**

Der Original-Import wird anhand seiner SHA256-Prüfsumme verifiziert, bevor er als Quellstand übernommen wird.

Aktueller Release:

**5.0.126 – JJS-Namensgebung, lange Texteingaben, verschiebbare Hauptmenüs und proportionale kompakte Coveransicht**
