"""Traduction du classeur de revue des risques (tools/build_risk_workbook.py --lang en).

Le classeur est construit en français (langue de référence), puis traduit cellule par cellule à partir de la table
tools/risk_workbook_en.json (clé = texte français, valeur = texte anglais). Sont aussi traduits : noms d'onglets
(y compris dans les formules et les liens), textes entre guillemets des formules, listes déroulantes, mises en forme
conditionnelles. Les nombres variables (dates, effectifs) sont remplacés par {0}, {1}… dans les clés, ce qui permet
à une phrase comme « 131 sources déclarées » de rester traduite quand le nombre change.

Ne sont jamais traduits (colonnes « protégées ») : identifiants, noms de médias, domaines, mots-clés, titres de
presse du jeu de test, noms de villes. Les noms de pays viennent de docs/data/countries.js (name_en).

Texte absent de la table : laissé en français et listé (python tools/build_risk_workbook.py --lang en --missing
écrit la liste dans revue/traductions_manquantes.json, à traduire puis à ajouter à la table).
"""
import re

NUM = re.compile(r"\d+(?:[.,]\d+)?")
QUOTED = re.compile(r'"([^"]*)"')
NAVY = "0E1B2C"

# Par onglet (nom français) et par titre de colonne : protect = jamais traduit ; country = nom de pays ;
# soft = traduit si la table le connaît, sinon laissé tel quel sans être signalé (noms propres).
COLUMNS = {
    "Médias": {"protect": ["Pays", "Média", "Domaine", "Langue", "Lettre actuelle"], "country": ["Nom du pays"]},
    "Sources": {"protect": ["Identifiant", "Type"], "soft": ["Nom"]},
    "Mots-clés": {"protect": ["Mot-clé (racine)"]},
    "Jeu de test": {"protect": ["Titre", "Pays", "Catégorie (Claude)"]},
    "Villes": {"protect": ["Pays", "Ville", "Niveau"], "country": ["Nom du pays"]},
    "Santé": {"protect": ["Pays"], "country": ["Nom"]},
    "Catégories": {"protect": ["Clé technique", "Libellé FR", "Libellé EN"]},
}


def norm(text):
    """Texte → (clé avec {0}, {1}…, nombres trouvés)."""
    nums = NUM.findall(text)
    i = iter(range(len(nums)))
    return NUM.sub(lambda m: "{%d}" % next(i), text), nums


class Translator:
    def __init__(self, table, countries=None):
        self.table = {k: v for k, v in table.items() if not k.startswith("_")}
        self.keep = set(table.get("_keep", []))   # identiques dans les deux langues (noms propres, codes)
        self.countries = countries or {}
        self.missing = set()
        self.sheet = None          # onglet en cours (pour savoir où manque une traduction)
        self.missing_in = {}       # onglet → textes sans traduction

    def text(self, s, report=True):
        """Traduit un texte ; renvoie l'original (et le note comme manquant) si la table ne le connaît pas."""
        if not isinstance(s, str) or not re.search(r"[A-Za-zÀ-ÿ]", s):
            return s
        if s in self.table:
            return self.table[s]
        if s in self.keep:
            return s
        key, nums = norm(s)
        if key in self.table:
            out = self.table[key]
            for i, n in enumerate(nums):
                out = out.replace("{%d}" % i, n)
            return out
        if report:
            self.missing.add(key)
            self.missing_in.setdefault(self.sheet, set()).add(key)
        return s

    def formula(self, f, sheet_names):
        def lit(m):
            return '"' + self.text(m.group(1)) + '"'
        f = QUOTED.sub(lit, f)
        for fr, en in sheet_names.items():
            f = f.replace(f"'{fr}'!", f"'{en}'!").replace(f"{fr}!", f"'{en}'!")
        return f

    def dv_list(self, f1):
        if f1 and f1.startswith('"') and f1.endswith('"'):
            return '"' + ",".join(self.text(v) for v in f1[1:-1].split(",")) + '"'
        return f1


def _rules_for_rows(ws, rules):
    """Pour chaque ligne : {colonne: règle} selon le dernier en-tête (cellules sur fond bleu nuit) rencontré."""
    current, out = {}, {}
    for row in ws.iter_rows():
        heads = {c.column: c.value for c in row if isinstance(c.value, str) and c.fill and c.fill.fgColor
                 and str(c.fill.fgColor.rgb).endswith(NAVY)}
        if heads:
            current = {}
            for col, h in heads.items():
                for kind, names in rules.items():
                    if h in names:
                        current[col] = kind
            out[row[0].row] = {}
            continue
        if row:
            out[row[0].row] = current
    return out


def translate_workbook(wb, tr):
    """Traduit le classeur en place."""
    sheet_names = {ws.title: tr.text(ws.title) for ws in wb.worksheets}
    for ws in wb.worksheets:
        tr.sheet = ws.title
        rows = _rules_for_rows(ws, COLUMNS.get(ws.title, {}))
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if c.hyperlink is not None and c.hyperlink.location:
                    c.hyperlink.location = tr.formula(c.hyperlink.location, sheet_names)
                if not isinstance(v, str) or type(c).__name__ == "MergedCell":
                    continue
                if v.startswith("="):
                    c.value = tr.formula(v, sheet_names)
                    continue
                kind = rows.get(c.row, {}).get(c.column)
                if kind == "protect":
                    continue
                if kind == "country":
                    c.value = tr.countries.get(v, v)
                elif kind == "soft":
                    c.value = tr.text(v, report=False)
                else:
                    c.value = tr.text(v)
        for dv in ws.data_validations.dataValidation:
            if dv.formula1 and dv.formula1.startswith('"'):
                dv.formula1 = tr.dv_list(dv.formula1)
            elif dv.formula1:
                dv.formula1 = tr.formula(dv.formula1, sheet_names)
            if dv.prompt:
                dv.prompt = tr.text(dv.prompt)
            if dv.promptTitle:
                dv.promptTitle = tr.text(dv.promptTitle)
        for cf in ws.conditional_formatting:
            for rule in cf.rules:
                rule.formula = [tr.formula(x, sheet_names) for x in (rule.formula or [])]
    for ws in wb.worksheets:
        ws.title = sheet_names[ws.title]
    return wb
