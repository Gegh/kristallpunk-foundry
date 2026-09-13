# Kristallpunk auf Foundry VTT

[Kristallpunk](https://kristallpunk.de) ist ein Fantasy-Pen-&-Paper-Rollenspiel in der Welt der Dunklen Romantik der 1820er Jahre. Dieses Repo enthält den Charakterbogen für [Foundry Virtual Tabletop](https://foundryvtt.com/), gebaut mit dem No-Code-System [Custom System Builder (CSB)](https://foundryvtt.com/packages/custom-system-builder), plus eine kleine Foundry-Modul, das ein paar Darstellungsfehler von Foundrys Standard-Tabellenstil korrigiert.

Kristallpunk hat kein eigenes, offizielles Foundry-System, weil es ein privates Homebrew-Regelwerk ist. Der Charakterbogen wird deshalb komplett per Custom System Builder nachgebaut, ohne eigenen Programmcode.

## Was hier drin ist

| Datei | Zweck |
|---|---|
| `character-template.json` | CSB-Template-Export des Charakterbogens (Attribute, Status, abgeleitete Werte, Fertigkeiten mit klickbaren Würfel-Pools) |
| `build_template.py` | Erzeugt `character-template.json` programmatisch. Änderungen am Bogen gehen hier rein, nicht per Hand in die JSON |
| `module.json`, `kristallpunk-sheet.css` | Ein winziges Foundry-Modul, das Foundrys Standard-Zebrastreifen bei Tabellenzeilen durch einen ruhigen, einheitlichen Hintergrund mit dünner Trennlinie ersetzt |

## Voraussetzungen

- Eine gekaufte [Foundry-VTT-Lizenz](https://foundryvtt.com/) (einmalig, aktuell 50 USD). Foundry selbst ist nicht Teil dieses Repos, kommerzielle Software.
- Das System [Custom System Builder](https://foundryvtt.com/packages/custom-system-builder), installierst du direkt in Foundry über den Paket-Browser oder das offizielle Manifest.
- Python 3, nur wenn du `build_template.py` änderst und neu erzeugen willst.

## Einrichtung

1. **Custom System Builder installieren** und eine Welt mit diesem System als Grundlage anlegen.
2. **Charakterbogen importieren:** In der Welt unter Einstellungen → Custom System Builder → *Import templates JSON* die Datei `character-template.json` auswählen.
3. **Style-Fix installieren:** Diesen Ordner (oder zumindest `module.json` und `kristallpunk-sheet.css`) nach `<FoundryDatenordner>/Data/modules/kristallpunk-foundry/` kopieren, dann in der Welt unter *Module verwalten* aktivieren. Läuft der Foundry-Server bereits, taucht das Modul erst nach einem Server-Neustart in der Liste auf (Foundry scannt `Data/modules/` nur beim Start neu ein). Danach unter Einstellungen → Custom System Builder das Feld "CSS Style file" leeren, sonst laden zwei identische Stylesheets parallel.

Damit rechnen Maximalwerte für Ausdauer live aus den Attributen, jede Fertigkeit zeigt ihren Würfel-Pool (Fertigkeit + zugehöriges Attribut) direkt daneben, anklickbar. Ein Klick würfelt die passende Anzahl W6 und zeigt im Chat die einzelnen Würfel, die Erfolge (6er) und die Einser getrennt, inklusive Markierung bei einem kritischen Erfolg oder Misserfolg nach der Dreierpasch-Regel.

Der Status-Bereich zeigt zusätzlich einen visuellen Status-Anzeiger: eine Zellenreihe je Körper-Ausdauer/Leibwunde, Geist-Ausdauer/Nervenschock und Innenleben, mit einem Marker "●" auf der Zelle des aktuellen Werts (Nachbau des physischen Statusanzeiger-Gadgets vom Spieltisch). Innenleben ist ein einziges Feld von -3 (Zweifel) bis +3 (Zuversicht) und ersetzt hier die getrennten Zuversicht/Zweifel-Zähler des Hauptregelwerks, siehe "Bekannte Lücken" unten.

## Bekannte Lücken

- Innenleben (-3 bis +3) ersetzt hier die getrennten Zuversicht/Zweifel-Zähler (je 0-5) aus dem Hauptregelwerk v0.93. Beide Zählweisen widersprechen sich, siehe die Innenleben-Klärung im KRISTALLPUNK-Wiki (`status-wunden-zuversicht.md`). Ein bereits ausgefüllter Charakterbogen mit alten Zuversicht/Zweifel-Werten übernimmt diese beim Re-Import nicht automatisch in das neue Innenleben-Feld.
- Nach einem Re-Import des Templates zeigen bereits angelegte Charaktere weiterhin den alten Bogen, bis man im Charakterblatt neben dem "Template"-Dropdown auf das Neuladen-Symbol klickt.
- Ausrüstungs- und Zauberkarten als eigene Item-Typen fehlen noch.
- Fertigkeiten zeigen nur den Grundwert, noch keine Kompetenzen.
- Automatischer Kompetenz-Reroll für Einser ("1er wiederholen") fehlt, braucht die Kompetenz-Felder als Voraussetzung.
- Das Regelwerk selbst ist an einigen Stellen noch nicht final (z. B. Attributsmaximum 6 vs. 7), einige Werte im Bogen sind entsprechend vorläufig.

## CSB-Formeln, Stolpersteine für die Zukunft

- Formeln müssen in `${ }$` eingeschlossen werden, sonst wird der Text nur wörtlich angezeigt statt berechnet.
- Ein Roll-Skript (`%{ ... }%`) in einer Komponente mit eigenem Key läuft synchron, `await` funktioniert darin nicht zuverlässig. Für einen Würfel-Wurf mit `await new Roll(...).evaluate()` muss die Komponente keylos sein (leeres Key-Feld).
- `${ }$`-Formeln unterstützen den mathjs-Ternary-Operator (`bedingung ? a : b`), live verifiziert im Status-Anzeiger-Tracker (`build_template.py`, `track_cell()`). Damit lassen sich bedingte Anzeigen (z. B. ein Marker auf genau einer Zelle) ohne Script-Expression bauen.
