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

def computed_label(key, formula, prefix="", suffix="", tooltip=""):
    # Plain (non-rollable) live-computed display, e.g. for showing a
    # calculated maximum next to an editable current-value field.
    c = wrapper(key, {
        "type": "label", "size": "full-size", "icon": "",
        "value": f"${{{formula}}}$", "prefix": prefix, "suffix": suffix,
        "rollMessage": "", "altRollMessage": "", "rollMessageToChat": True,
        "altRollMessageToChat": True, "style": "label",
    })
    c["tooltip"] = tooltip
    return c

def roll_script(display_name, pool_expr_js):
    # JS Script-Expression: roll the pool once, show individual dice, count
    # 6er (Erfolge) and 1er (Einser), flag crit success/failure per Dreierpasch.
    # Component must be KEYLESS: keyed Labels run scripts synchronously, which
    # breaks "await" (CSB docs, Guides/Formula-System, Sync/Async section) and
    # produced an unrelated Roll-parse exception during this build.
    return (
        "%{\n"
        "  const props = entity.system.props;\n"
        f"  const pool = {pool_expr_js};\n"
        f"  if (pool <= 0) return `<strong>{display_name}</strong>: Pool 0, kein Wurf möglich.`;\n"
        "  const roll = await new Roll(pool + \"d6\").evaluate();\n"
        "  const faces = roll.terms.at(0).results.map(r => r.result).sort((a,b) => a-b);\n"
        "  const sechser = faces.filter(f => f === 6).length;\n"
        "  const einser = faces.filter(f => f === 1).length;\n"
        f"  let text = `<strong>{display_name}</strong> (Pool ${{pool}}): (${{faces.join(', ')}})<br>"
        "Erfolge (6er): <strong>${sechser}</strong> &nbsp; Einser: <strong>${einser}</strong>`;\n"
        "  if (einser >= 3) text += `<br>⚠️ Kritischer Misserfolg (3+ Einser)`;\n"
        "  if (sechser >= 3) text += `<br>✨ Kritischer Erfolg (3+ Sechser)`;\n"
        "  return text;\n"
        "}%"
    )

def pool_button(display_name, pool_formula, pool_expr_js, tooltip):
    # Keyless (key ""): nothing else references this component's value, and it
    # must be keyless for its async roll script to execute correctly.
    c = wrapper("", {
        "type": "label", "size": "full-size", "icon": "",
        "value": f"${{{pool_formula}}}$", "prefix": "Pool ", "suffix": " W6",
        "rollMessage": roll_script(display_name, pool_expr_js),
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

status = panel("panel_status", "Status", "vertical", [
    ausdauer_table,
    panel("panel_status_rest", "", "grid-4", [
        number_field("leibwunden", "Leibwunden", 0, 3, True,
                     "-1 auf koerperliche Proben pro Leibwunde, kumulativ bis -3. Vierte Leibwunde wird zu Nervenschock."),
        number_field("nervenschock", "Nervenschock", 0, 3, True,
                     "-1 auf geistige Proben pro Nervenschock, kumulativ bis -3. Vierter Nervenschock wird zu Leibwunde."),
        number_field("zuversicht", "Zuversicht", 0, 5, True,
                     "Startwert nach Alter, siehe Charaktererstellung. Max 5, ein sechster Punkt gilt als automatischer Erfolg."),
        number_field("zweifel", "Zweifel", 0, 5, True,
                     "Max 5, ein sechster Punkt gibt der SL Kontrolle oder eine Truebnismutation."),
    ], collapsible=False),
])

def num(prop):
    return f"Number(props.{prop} ?? 0)"

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

def skill_table(key, skills):
    rows = []
    for skey, sname, akey, aname, tip in skills:
        full_tip = f"{aname}. {tip}"
        pool_js = f"{num(skey)} + {num(akey)}"
        rows.append([
            static_label(skey + "_label", f"{sname} ({aname})", full_tip),
            number_field(skey, "", 0, 9, False, full_tip),
            pool_button(sname, f"{skey} + {akey}", pool_js, full_tip + " Anklicken zum Wuerfeln."),
        ])
    return table(key, rows, 3, "lcc")

fertigkeiten_koerper = panel("panel_fertigkeiten_koerper", "Fertigkeiten: Koerperlich - Pool anklicken zum Wuerfeln", "vertical", [
    skill_table("table_fertigkeiten_koerper", skills_koerper),
])
fertigkeiten_geist = panel("panel_fertigkeiten_geist", "Fertigkeiten: Geist - Pool anklicken zum Wuerfeln", "vertical", [
    skill_table("table_fertigkeiten_geist", skills_geist),
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
