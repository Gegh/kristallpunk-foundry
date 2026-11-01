import json
import os

def wrapper(key, extra):
    d = {
        "key": key, "colSpan": 1, "rowSpan": 1, "cssClass": "", "role": 0,
        "editRole": 0, "permission": 0, "tooltip": "", "visibilityFormula": "",
        "editableFormula": "", "escapeHTML": False,
    }
    d.update(extra)
    return d

def num(prop):
    # JS Script-Expression snippet: read a numeric prop safely. CSB stores
    # numberField values as strings, so bare access needs coercion (source
    # of the earlier "Pool 04" string-concatenation bug).
    return f"Number(props.{prop} ?? 0)"

def js_sum(*props):
    return " + ".join(num(p) for p in props)

def number_field(key, label, minv, maxv, allow_relative=False, tooltip=""):
    c = wrapper(key, {
        "type": "numberField", "size": "full-size", "label": label,
        "defaultValue": "" if allow_relative and str(maxv).startswith("$") else "0",
        "allowDecimal": False, "minVal": str(minv), "maxVal": str(maxv),
        "allowRelative": allow_relative, "showControls": True,
        "controlsStyle": "hover", "controlsCustomIncrements": "", "inputStyle": "text",
    })
    c["tooltip"] = tooltip
    return c

def static_label(key, text, tooltip=""):
    c = wrapper(key, {
        "type": "label", "size": "full-size", "icon": "", "value": text,
        "prefix": "", "suffix": "", "rollMessage": "", "altRollMessage": "",
        "rollMessageToChat": True, "altRollMessageToChat": True, "style": "label",
    })
    c["tooltip"] = tooltip
    return c

def text_field(key, label, default_value="", tooltip="", autocomplete=""):
    # CSB "textField" component (confirmed against the installed system's
    # own source, module/sheets/components/TextField.js: toJSON() emits
    # exactly charList/maxLength/autocomplete besides the shared
    # size/label/defaultValue fields already used by number_field()).
    # autocomplete is a plain comma-separated string, not a ${...}$ formula.
    c = wrapper(key, {
        "type": "textField", "size": "full-size", "label": label,
        "defaultValue": default_value, "charList": "", "maxLength": "",
        "autocomplete": autocomplete,
    })
    c["tooltip"] = tooltip
    return c

def computed_label(key, formula, prefix="", suffix="", tooltip="", roll_message="", roll_to_chat=False):
    # Plain live-computed display, e.g. for showing a calculated maximum
    # next to an editable current-value field. Optionally clickable: a
    # non-empty roll_message makes it behave like pool_button() (runs on
    # click), just without the "button" visual style.
    c = wrapper(key, {
        "type": "label", "size": "full-size", "icon": "",
        "value": f"${{{formula}}}$", "prefix": prefix, "suffix": suffix,
        "rollMessage": roll_message, "altRollMessage": "", "rollMessageToChat": roll_to_chat,
        "altRollMessageToChat": roll_to_chat, "style": "label",
    })
    c["tooltip"] = tooltip
    return c

def roll_script(display_name, pool_expr_js, ausdauer_field=None, ausdauer_label=None,
                 kompetenz_field=None):
    # JS Script-Expression: roll the pool once, show individual dice, count
    # 6er (Erfolge) and 1er (Einser), flag crit success/failure per Dreierpasch.
    # Component must be KEYLESS: keyed Labels run scripts synchronously, which
    # breaks "await" (CSB docs, Guides/Formula-System, Sync/Async section) and
    # produced an unrelated Roll-parse exception during this build.
    #
    # ausdauer_field: a Fertigkeitsprobe costs 1 point of the matching Ausdauer
    # (regelzusammenfassung-1-0.pdf, S. 4-5). Abgeleitete Werte cost none, so
    # derived-value pool buttons call this with ausdauer_field=None. Clamped
    # at 0: going below 0 isn't modeled (that's Anstrengung, not automated).
    #
    # kompetenz_field: Kompetenzen let the player reroll all 1er once per
    # probe, but only if a known competency actually covers the action in
    # that moment (proben-system.md, "Kompetenzen") - a judgment call, not
    # something a fixed formula can decide. So instead of a persistent
    # per-skill toggle, this asks via Dialog.confirm() right when a 1 comes
    # up, showing whatever the player entered in that skill's Kompetenzen
    # text field as a reminder. Foundry's Dialog is a plain global here (CSB
    # runs Script-Expressions through the AsyncFunction constructor with no
    # extra sandboxing, confirmed in the installed system's own
    # formulas/ComputablePhrase.js), so this await works the same way
    # await new Roll(...).evaluate() already does above.
    deduct = ""
    if ausdauer_field:
        deduct = (
            f"  const vorher = Number(props.{ausdauer_field} ?? 0);\n"
            f"  const nachher = Math.max(0, vorher - 1);\n"
            f"  entity.update({{\"system.props.{ausdauer_field}\": String(nachher)}});\n"
        )
    kosten_hinweis = (
        f"  text += `<br><em>-1 {ausdauer_label}-Ausdauer (jetzt ${{nachher}})</em>`;\n"
        if ausdauer_field else ""
    )
    kompetenz_block = ""
    kompetenz_hinweis = ""
    if kompetenz_field:
        kompetenz_block = (
            "  let kompetenzGenutzt = false;\n"
            "  let facesVorKompetenz = null;\n"
            "  if (einser > 0) {\n"
            f"    const kompetenzen = String(props.{kompetenz_field} ?? \"\").trim();\n"
            "    const hinweis = kompetenzen\n"
            "      ? `Bekannte Kompetenzen fuer diese Fertigkeit: <strong>${kompetenzen}</strong><br>Deckt eine davon diese Handlung ab?`\n"
            "      : `Deckt eine (ggf. noch nicht eingetragene) Kompetenz diese Handlung ab?`;\n"
            "    kompetenzGenutzt = await Dialog.confirm({\n"
            "      title: \"Kompetenz nutzen?\",\n"
            "      content: `<p>${hinweis}<br>Dann darfst du einmal alle gewuerfelten 1er wiederholen (zweites Ergebnis bindend).</p>`,\n"
            "    });\n"
            "    if (kompetenzGenutzt) {\n"
            "      facesVorKompetenz = faces.slice();\n"
            "      const rerollRoll = await new Roll(einser + \"d6\").evaluate();\n"
            "      const rerollFaces = rerollRoll.terms.at(0).results.map(r => r.result);\n"
            "      let ri = 0;\n"
            "      for (let i = 0; i < faces.length; i++) {\n"
            "        if (faces[i] === 1) { faces[i] = rerollFaces[ri]; ri++; }\n"
            "      }\n"
            "      faces.sort((a, b) => a - b);\n"
            "      sechser = faces.filter(f => f === 6).length;\n"
            "      einser = faces.filter(f => f === 1).length;\n"
            "    }\n"
            "  }\n"
        )
        kompetenz_hinweis = (
            "  if (kompetenzGenutzt) text += `<br><em>Kompetenz genutzt, 1er wiederholt "
            "(vorher: ${facesVorKompetenz.join(', ')})</em>`;\n"
        )
    return (
        "%{\n"
        "  const props = entity.system.props;\n"
        f"  const pool = {pool_expr_js};\n"
        f"  if (pool <= 0) return `<strong>{display_name}</strong>: Pool 0, kein Wurf möglich.`;\n"
        "  const roll = await new Roll(pool + \"d6\").evaluate();\n"
        "  const faces = roll.terms.at(0).results.map(r => r.result).sort((a,b) => a-b);\n"
        "  let sechser = faces.filter(f => f === 6).length;\n"
        "  let einser = faces.filter(f => f === 1).length;\n"
        f"{kompetenz_block}"
        f"{deduct}"
        f"  let text = `<strong>{display_name}</strong> (Pool ${{pool}}): (${{faces.join(', ')}})<br>"
        "Erfolge (6er): <strong>${sechser}</strong> &nbsp; Einser: <strong>${einser}</strong>`;\n"
        f"{kompetenz_hinweis}"
        "  if (einser >= 3) text += `<br>⚠️ Kritischer Misserfolg (3+ Einser)`;\n"
        "  if (sechser >= 3) text += `<br>✨ Kritischer Erfolg (3+ Sechser)`;\n"
        f"{kosten_hinweis}"
        "  return text;\n"
        "}%"
    )

def pool_button(display_name, pool_formula, pool_expr_js, tooltip, ausdauer_field=None, ausdauer_label=None,
                 kompetenz_field=None):
    # Keyless (key ""): nothing else references this component's value, and it
    # must be keyless for its async roll script to execute correctly.
    c = wrapper("", {
        "type": "label", "size": "full-size", "icon": "",
        "value": f"${{{pool_formula}}}$", "prefix": "Pool ", "suffix": " W6",
        "rollMessage": roll_script(display_name, pool_expr_js, ausdauer_field, ausdauer_label, kompetenz_field),
        "altRollMessage": "", "rollMessageToChat": True, "altRollMessageToChat": True,
        "style": "button",
    })
    c["tooltip"] = tooltip
    return c

def panel(key, title, flow, contents, collapsible=True):
    return wrapper(key, {
        "type": "panel", "flow": flow, "align": "center", "verticalAlign": "top",
        "collapsible": collapsible, "defaultCollapsed": False, "title": title,
        "titleStyle": "default", "contents": contents,
    })

def table(key, rows_cells, cols, layout):
    return wrapper(key, {
        "type": "table", "contents": rows_cells, "cols": cols,
        "rows": len(rows_cells), "layout": layout,
        # Custom class so our CSS (assets/kristallpunk-sheet.css) can override
        # Foundry's default zebra striping (body.game .app table tr:nth-child(even)),
        # which uses a translucent white overlay that looks patchy against the
        # scene background bleeding through the sheet window.
        "cssClass": "kristallpunk-table",
    })

# --- Status-Anzeiger: visueller, klickbarer Ausdauer/Wunden/Innenleben-Tracker ---
# Nachbau des physischen "Statusanzeiger"-Gadgets (Statusanzeiger-pdf-2026.pdf)
# und seiner Miro-Version (kristallpunk-spieltisch-miro): jede Zelle zeigt
# entweder ihre Zahl oder, wenn sie dem aktuellen Wert entspricht, einen
# Marker "●" (${...}$-Formel, math.js-Ternary). Zusaetzlich klickbar: ein
# Klick setzt das zugrundeliegende Feld direkt auf den Zellenwert, wie beim
# Verschieben des physischen Markers (Georg, 2026-09-13: "mach die zellen
# klickbar"). Keylos, damit ein moeglicher Roll-Message-Bug mit Keys (siehe
# roll_script()) gar nicht erst auftreten kann, auch wenn dieses Skript
# selbst kein await braucht.
def click_set_script(field, value, max_js=None):
    # Must declare "props" itself (matching roll_script()'s pattern): the
    # max_js guard expression references it via num()/js_sum(), and without
    # this line it throws "ReferenceError: props is not defined", caught
    # live via read_console_messages() on the first version of this script.
    guard = f'if ({value} > ({max_js})) return "";\n  ' if max_js is not None else ""
    return (
        "%{\n"
        "  const props = entity.system.props;\n"
        f"  {guard}entity.update({{\"system.props.{field}\": \"{value}\"}});\n"
        "  return \"\";\n"
        "}%"
    )

def track_cell(current_field, n, max_formula=None, max_js=None, show_plus=False):
    label = f"+{n}" if (show_plus and n > 0) else str(n)
    if max_formula is None:
        # Wund-Zelle oder Null-Pivot: fester Bereich, kein Maximum-Check noetig.
        formula = f'{current_field}=={n} ? "●" : {n}'
        click = click_set_script(current_field, n)
    else:
        # Ausdauer- oder Innenleben-Zelle: leer, wenn ausserhalb des fuer
        # diesen Charakter berechneten Maximums (z. B. Ausdauer 15 bei nur
        # 12 Punkten Max), sonst Zahl oder Marker. Klick auf eine leere
        # Zelle setzt entsprechend nichts (Guard im Klick-Skript).
        formula = f'{current_field}=={n} ? "●" : ({n} <= ({max_formula}) ? "{label}" : "")'
        click = click_set_script(current_field, n, max_js)
    return computed_label("", formula, tooltip="Klicken, um diesen Wert zu setzen.", roll_message=click)

def ausdauer_track(key, current_field, wound_field, track_max, max_formula, max_js):
    row = []
    for n in (3, 2, 1):
        row.append(track_cell(wound_field, n))
    row.append(track_cell(current_field, 0))
    for n in range(1, track_max + 1):
        row.append(track_cell(current_field, n, max_formula, max_js))
    return table(key, [row], len(row), "c" * len(row))

def innenleben_track(key, current_field):
    row = []
    for n in range(-3, 0):
        row.append(track_cell(current_field, n))
    row.append(track_cell(current_field, 0))
    for n in range(1, 4):
        row.append(track_cell(current_field, n, "3", "3", show_plus=True))
    return table(key, [row], len(row), "c" * len(row))

# --- Attributes ---
attr_koerper = panel("panel_attribute_koerper", "Attribute: Koerper", "grid-3", [
    number_field("kraft", "Kraft", 0, 6),
    number_field("geschick", "Geschick", 0, 6),
    number_field("sinne", "Sinne", 0, 6),
])
attr_geist = panel("panel_attribute_geist", "Attribute: Geist", "grid-3", [
    number_field("wille", "Wille", 0, 6),
    number_field("intelligenz", "Intelligenz", 0, 6),
    number_field("empathie", "Empathie", 0, 6),
])

# --- Status ---
koerper_ausdauer_tip = "Sinkt bei jeder koerperlichen Probe um 1. Bei 0: nur noch mit Anstrengung handlungsfaehig."
geist_ausdauer_tip = "Sinkt bei jeder geistigen Probe um 1. Bei 0: nur noch mit Anstrengung handlungsfaehig."

# Koerper- und Geist-Ausdauer haben ein Maximum, das sich live aus den drei
# zugehoerigen Attributen berechnet. Eigene Tabelle: Name | aktueller Wert
# (editierbar) | berechnetes Maximum (reine Anzeige, kein eigener Wert).
ausdauer_table = table("table_ausdauer", [
    [
        static_label("koerper_ausdauer_name", "Koerper-Ausdauer", koerper_ausdauer_tip),
        number_field("koerper_ausdauer", "", 0, "${kraft+geschick+sinne}$", True, koerper_ausdauer_tip),
        computed_label("koerper_ausdauer_max_anzeige", "kraft+geschick+sinne", "Max ", "",
                       "Berechnetes Maximum: Kraft + Geschick + Sinne."),
    ],
    [
        static_label("geist_ausdauer_name", "Geist-Ausdauer", geist_ausdauer_tip),
        number_field("geist_ausdauer", "", 0, "${wille+intelligenz+empathie}$", True, geist_ausdauer_tip),
        computed_label("geist_ausdauer_max_anzeige", "wille+intelligenz+empathie", "Max ", "",
                       "Berechnetes Maximum: Wille + Intelligenz + Empathie."),
    ],
], 3, "lcc")

innenleben_tip = ("Eine gemeinsame Skala von -3 (Zweifel) bis +3 (Zuversicht) ueber die neutrale 0 " +
                   "(Innenleben), siehe Statusanzeiger-Gadget. Ersetzt die getrennten 0-5-Zaehler " +
                   "aus dem Hauptregelwerk fuer diese digitale Umsetzung.")

status = panel("panel_status", "Status", "vertical", [
    ausdauer_table,
    panel("panel_status_rest", "", "grid-3", [
        number_field("leibwunden", "Leibwunden", 0, 3, True,
                     "Jede Leibwunde kostet Koerper-Proben +1 Ausdauer extra, bis hoechstens +3 (also 4 statt 1 Punkt bei drei Leibwunden). Vierte Leibwunde wird zu Nervenschock."),
        number_field("nervenschock", "Nervenschock", 0, 3, True,
                     "Jeder Nervenschock kostet Geist-Proben +1 Ausdauer extra, bis hoechstens +3. Vierter Nervenschock wird zu Leibwunde."),
        number_field("innenleben", "Innenleben", -3, 3, True, innenleben_tip),
    ], collapsible=False),
    panel("panel_statusanzeiger", "Status-Anzeiger", "vertical", [
        panel("panel_track_koerper_title", "Koerper: Leibwunde (3-1) | Ausdauer (0-18)", "vertical", [
            ausdauer_track("table_track_koerper", "koerper_ausdauer", "leibwunden", 18, "kraft+geschick+sinne", js_sum("kraft", "geschick", "sinne")),
        ], collapsible=False),
        panel("panel_track_geist_title", "Geist: Nervenschock (3-1) | Ausdauer (0-18)", "vertical", [
            ausdauer_track("table_track_geist", "geist_ausdauer", "nervenschock", 18, "wille+intelligenz+empathie", js_sum("wille", "intelligenz", "empathie")),
        ], collapsible=False),
        panel("panel_track_innenleben_title", "Innenleben: Zweifel (-3) .. Zuversicht (+3)", "vertical", [
            innenleben_track("table_track_innenleben", "innenleben"),
        ], collapsible=False),
    ], collapsible=False),
])

# --- Initiative: Wurf mit 1W6 (kein Erfolge-Pool), + manueller Bonus ---
# attribute-koerper-geist.md: "Wurf mit 1W6 zu Beginn jeder Szene, kostet
# keine Ausdauer... 6er oder hoeher zuerst, 1er zuletzt." Einige angeborene
# Eigenschaften/Kompetenzen veraendern den Wurf (z. B. Fechtstil
# polnisch/ungarisch +1, Blitzschnelle Reflexe addiert Ausweichen-Erfolge) -
# das sind Einzelfaelle mit eigener Mechanik, kein allgemeines Pool-Wuerfeln,
# deshalb hier nur ein manuelles Bonus-Feld statt eigener Automatisierung je
# Eigenschaft.
def initiative_script(bonus_field):
    return (
        "%{\n"
        "  const props = entity.system.props;\n"
        f"  const bonus = {num(bonus_field)};\n"
        "  const roll = await new Roll(\"1d6\").evaluate();\n"
        "  const wurf = roll.terms.at(0).results[0].result;\n"
        "  const gesamt = wurf + bonus;\n"
        "  let text = `<strong>Initiative</strong>: Wurf ${wurf} + Bonus ${bonus} = <strong>${gesamt}</strong><br>"
        "6 oder hoeher handelt zuerst, 1 zuletzt. Bei Gleichstand: SC vor NSC, "
        "SC untereinander neu entscheiden oder zusaetzlichen W6 wuerfeln.`;\n"
        "  return text;\n"
        "}%"
    )

def initiative_button(tooltip, bonus_field):
    c = wrapper("", {
        "type": "label", "size": "full-size", "icon": "",
        "value": "1W6 + Bonus", "prefix": "", "suffix": "",
        "rollMessage": initiative_script(bonus_field),
        "altRollMessage": "", "rollMessageToChat": True, "altRollMessageToChat": True,
        "style": "button",
    })
    c["tooltip"] = tooltip
    return c

initiative_tip = ("Wurf mit 1W6 zu Beginn jeder Szene, kostet keine Ausdauer. 6 oder hoeher handelt "
                   "zuerst, 1 zuletzt. Bei Gleichstand handeln SC vor NSC; SC untereinander entscheiden "
                   "neu oder wuerfeln einen zusaetzlichen W6. Manche angeborenen Eigenschaften und "
                   "Kompetenzen (z. B. Fechtstil polnisch/ungarisch, Blitzschnelle Reflexe) veraendern "
                   "den Wurf, trage sie hier als manuellen Bonus ein.")

initiative_row = table("table_initiative", [[
    static_label("initiative_label", "Initiative", initiative_tip),
    number_field("initiative_bonus", "Bonus", -5, 5, True, initiative_tip),
    initiative_button(initiative_tip + " Anklicken zum Wuerfeln.", "initiative_bonus"),
]], 3, "lcc")

# --- Abgeleitete Werte: Table (Name | Pool-Button) + Ruestung/Schutz separat ---
# Each entry: key, display name, CSB-formula (for the passive "Pool N" display),
# JS expression using entity.system.props (for the roll script), tooltip.
derived = [
    ("mut", "Mut", "kraft + wille",
     f"{num('kraft')} + {num('wille')}",
     "Kraft + Wille. Ueberwindet Angst erzeugende Gegner, kostet keinen Status."),
    ("kristall_echo", "Kristall-Echo", "sinne + empathie",
     f"{num('sinne')} + {num('empathie')}",
     "Sinne + Empathie. Fuehlt Resonanzmagie und aktivierte Kristalle."),
    ("erkennen", "Erkennen", "geschick + intelligenz",
     f"{num('geschick')} + {num('intelligenz')}",
     "Geschick + Intelligenz. Zusammenhaenge in der Realitaet begreifen."),
    ("haerte", "Haerte", "floor((kraft+geschick+sinne)/2)",
     f"Math.floor(({num('kraft')} + {num('geschick')} + {num('sinne')}) / 2)",
     "Koerper-Ausdauer-Maximum geteilt durch 2, abgerundet. Verteidigung, kostet keinen Status."),
    ("seelenhalt", "Seelenhalt", "floor((wille+intelligenz+empathie)/2)",
     f"Math.floor(({num('wille')} + {num('intelligenz')} + {num('empathie')}) / 2)",
     "Geist-Ausdauer-Maximum geteilt durch 2, abgerundet. Verteidigung, kostet keinen Status."),
]
derived_rows = []
for key, name, formula, pool_js, tip in derived:
    derived_rows.append([
        static_label(key + "_label", name, tip),
        pool_button(name, formula, pool_js, tip + " Anklicken zum Wuerfeln."),
    ])
derived_table = table("table_abgeleitet", derived_rows, 2, "lc")

abgeleitet = panel("panel_abgeleitet", "Abgeleitete Werte (v1.0, vorlaeufig) - anklicken zum Wuerfeln", "vertical", [
    initiative_row,
    derived_table,
    panel("panel_ruestung_schutz", "", "grid-2", [
        number_field("ruestung", "Ruestung", 0, 3, False,
                     "Koerperschutz 1-3 durch Ruestungsteile. Reduziert koerperlichen Ausdauerverlust, verhindert keine Leibwunden."),
        number_field("schutz", "Schutz", 0, 3, False,
                     "Geist-Schutz 1-3 durch Kristall-Amulette oder Resonanzzauber. Verhindert Nervenschock, verbraucht sich dabei."),
    ], collapsible=False),
])

# --- Fertigkeiten: Table (Name | Wert | Pool-Button) ---
skills_koerper = [
    ("athletik", "Athletik", "kraft", "Kraft", "Grobe Bewegungen und koerperliche Ausdauer."),
    ("aufmerksamkeit", "Aufmerksamkeit", "sinne", "Sinne", "Wie der Charakter die Umwelt wahrnimmt."),
    ("ausweichen", "Ausweichen", "sinne", "Sinne", "Reaktion des Koerpers, Schnelligkeit und Praezision der Bewegung."),
    ("fernkampf", "Fernkampf", "geschick", "Geschick", "Werfen und Schiessen, vom Stein bis zur Kanone."),
    ("handwerk", "Handwerk", "geschick", "Geschick", "Herstellung, Reparatur, Instandhaltung, feinmotorische Handlungen."),
    ("heimlichkeit", "Heimlichkeit", "geschick", "Geschick", "Taschenspielertricks und Taschendiebstahl, auch Schloesser oeffnen."),
    ("nahkampf", "Nahkampf", "kraft", "Kraft", "Vom Faustkampf bis zum eleganten Degen."),
    ("orientierung", "Orientierung", "sinne", "Sinne", "Wegfindung, Navigation, Spuren lesen, Fahrzeuge fahren."),
]
skills_geist = [
    ("autoritaet", "Autoritaet", "wille", "Wille", "Durchsetzungsvermoegen, Verhoere, aggressive Sprache."),
    ("bildung", "Bildung", "intelligenz", "Intelligenz", "Mass der Ausbildung, gesellschaftliches und politisches Wissen."),
    ("inspiration", "Inspiration", "empathie", "Empathie", "Einfallsreichtum und Kreativitaet, Kunst, Musik, Improvisation."),
    ("medizin", "Medizin", "intelligenz", "Intelligenz", "Verletzte heilen, Krankheiten behandeln, Wunden versorgen."),
    ("prismenresonanz", "Prismenresonanz", "wille", "Wille", "Die Kunst zu zaubern, siehe Kristallmagie-Uebersicht."),
    ("redekunst", "Redekunst", "empathie", "Empathie", "Ueberreden, feilschen, ueberzeugen, beruhigen."),
    ("schauspiel", "Schauspiel", "empathie", "Empathie", "Jemand anderen darstellen oder nachahmen, sich verstellen."),
    ("wissenschaft", "Wissenschaft", "intelligenz", "Intelligenz", "Naturwissenschaften und andere Wissenschaften, theoretisches Wissen."),
]

# Kompetenz-Katalog je Fertigkeit, Namen aus fertigkeiten-und-kompetenzen.md
# (Charaktererschaffung v1.0, Schritt 3b), nur fuer die Autocomplete-Liste
# des jeweiligen Kompetenzen-Textfelds - keine erzwungene Auswahl, der
# Spieler kann trotzdem jeden Text eintragen (z. B. eigene abgesprochene
# Kompetenzen, siehe proben-system.md).
KOMPETENZEN_KATALOG = {
    "athletik": "Klettern, Reiten, Dauerlauf, Schwimmen",
    "aufmerksamkeit": "Dazwischenwerfen, Schreckhaft, Wachtposten, Ueberwachen, Durchschauen, Entdecken",
    "ausweichen": "Asiatischer Kampf, Blitzschnelle Reflexe, Tanzen, Wie ein Blatt im Wind",
    "fernkampf": "Artillerist, Duellant, Scharfschuetze, Kristallschuss, Ladedrill, Lieblingswaffe, Meisterschuetze, Schuss vom Pferderuecken",
    "handwerk": "Erlerntes Handwerk, Reparieren, Schloesser oeffnen, Galvanistische Kristallapparaturen, Nutztierkunde, Wildtierkunde, Gaertnerei",
    "heimlichkeit": "Auf der Lauer liegen, Gauklertricks, Gaunerzinken, Gluecksspiel-Schummler, Informationen und Geruechte, Schlossknacker, Schleichen, Taschendiebstahl, Verbergen & verstecken",
    "nahkampf": "Kampf zu Pferd, Landwehr, Lieblingswaffe, Strassenkampf, Waffenmeister, Parade-Riposte, Fechtstil venezianisch, Fechtstil polnisch/ungarisch, Fechtstil japanisch, Nahkampfstil Boxkampf, Nahkampfstil Ringkampf, Nahkampfstil asiatisches Kun Fu",
    "orientierung": "Kutschen & Fuhrwerke, Navigation, Spuren lesen urban, Spuren lesen Natur, Truebnisgebiete, Ueberleben-Natur, Wegfindung, Wildtierkunde",
    "autoritaet": "Bedrohen, Einschuechtern, Kommandieren, Standhaftigkeit, Verhoertechniken",
    "bildung": "Antike Sprachen, Bibliotheksstruktur, Buchfuehrung und Verwaltung, Enormes Allgemeinwissen, Etikette, Fachwissen-Profession, Gesetz, Fremdsprachen",
    "inspiration": "Achtsamkeit, Bildhauerei, Faelschung, Gluecks-Spieler(in), Malerei, Musik, Dichtung",
    "medizin": "Abgestumpft, Chirurgie, Feldarzt, Forensik, Internist, Kraeutermedizin, Kunst des toten Lebens, Pathologie, Psychologie, Truebnispathologe, Tiere",
    "prismenresonanz": "Buchzauberei, Resonanzkompetenz, Rituale",
    "redekunst": "Befragen, Feilschen, Fuersorge, Geplauder, Luegen, Ueberzeugen, Verhandlungsexperte",
    "schauspiel": "Darstellung, Etikette, Taeuschen & Verkleiden",
    "wissenschaft": "Archeologie, Antike Sprachen, Biologie, Okkultismus, Pharmazie & Chemie, Philosophie & Geschichte, Politik, Naturwissenschaften",
}

def skill_table(key, skills, ausdauer_field, ausdauer_label):
    rows = []
    for skey, sname, akey, aname, tip in skills:
        full_tip = f"{aname}. {tip}"
        pool_js = f"{num(skey)} + {num(akey)}"
        kompetenz_field = skey + "_kompetenzen"
        katalog = KOMPETENZEN_KATALOG.get(skey, "")
        kompetenz_tip = (f"Bekannte Kompetenzen fuer {sname} (frei eintragbar, z. B. eigene mit der SL "
                          f"abgesprochene). Bekannte Faelle laut Regelwerk: {katalog}. Deckt eine davon "
                          "eine Probe ab, fragt der Wuerfel-Button bei Einsern automatisch, ob alle "
                          "einmal wiederholt werden sollen (zweites Ergebnis bindend).")
        rows.append([
            static_label(skey + "_label", f"{sname} ({aname})", full_tip),
            number_field(skey, "", 0, 9, False, full_tip),
            text_field(kompetenz_field, "", "", kompetenz_tip, katalog),
            pool_button(sname, f"{skey} + {akey}", pool_js,
                        full_tip + " Anklicken zum Wuerfeln, zieht 1 " + ausdauer_label + "-Ausdauer ab.",
                        ausdauer_field, ausdauer_label, kompetenz_field),
        ])
    return table(key, rows, 4, "lclc")

fertigkeiten_koerper = panel("panel_fertigkeiten_koerper", "Fertigkeiten: Koerperlich - Pool anklicken zum Wuerfeln (zieht 1 Koerper-Ausdauer ab), Kompetenzen eintragen fuer automatische Nachfrage beim Einser-Wiederholen", "vertical", [
    skill_table("table_fertigkeiten_koerper", skills_koerper, "koerper_ausdauer", "Koerper"),
])
fertigkeiten_geist = panel("panel_fertigkeiten_geist", "Fertigkeiten: Geist - Pool anklicken zum Wuerfeln (zieht 1 Geist-Ausdauer ab), Kompetenzen eintragen fuer automatische Nachfrage beim Einser-Wiederholen", "vertical", [
    skill_table("table_fertigkeiten_geist", skills_geist, "geist_ausdauer", "Geist"),
])

body_contents = [attr_koerper, attr_geist, status, abgeleitet, fertigkeiten_koerper, fertigkeiten_geist]

template = {
    "isCustomSystemExport": True,
    "actors": [{
        "id": "ZvQE8Tx1ulL1D2qb",
        "type": "_template",
        "name": "Kristallpunk Charakter",
        "data": {
            "body": {"contents": body_contents, "key": "custom_body", "type": "panel"},
            "display": {"width": 900, "height": 900, "fix_size": False, "pp_width": 64, "pp_height": 64},
            "header": {"contents": [], "key": "custom_header", "type": "panel"},
            "hidden": [],
            "attributeBar": {},
            "templateSystemUniqueVersion": 3,
        },
        "flags": {"custom-system-builder": {"version": "6.0.2"}},
    }],
    "items": [],
}

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "character-template.json")
with open(out_path, "w") as f:
    json.dump(template, f, ensure_ascii=False, indent=1)

print("geschrieben:", out_path)
