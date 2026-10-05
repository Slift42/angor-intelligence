"""Analyse légère des titres de presse, sans IA : thème, catégorie, gravité et lieu.

- Catégorie et gravité : dictionnaires de mots-clés en 21 langues (en, fr, es, pt, de, it, nl, pl, tr, ru, uk, ar,
  he, id, th, zh, fa, ur, bn, am, so).
- Lieu : pays cité (noms anglais/français) puis ville de ce pays (GeoNames, villes > 15 000 hab.,
  noms dans toutes les langues). Le dictionnaire GeoNames (licence CC BY 4.0) est téléchargé
  automatiquement une seule fois dans data/geonames/.

C'est volontairement prudent : en cas de doute, l'article reste dans le « Fil » sans être placé
sur la carte. L'étape IA prendra le relais pour le classement fin et le résumé en anglais.
"""
import io
import re
import unicodedata
import zipfile

from . import http
from .config import ROOT

GEONAMES_URL = "https://download.geonames.org/export/dump/cities15000.zip"
GEONAMES_DIR = ROOT / "data" / "geonames"

# ------------------------------------------------------------------ mots-clés
# Chaque entrée : racines de mots (début de mot), toutes langues confondues.
CATEGORY_WORDS = {
    "terrorism": ["terror", "jihad", "djihad", "yihad", "isis", "daech", "daesh", "al-qaida", "al qaeda", "al-qaeda",
                  "al-shabaab", "boko haram", "attentat", "suicide bomb", "kamikaze", "terör", "террор", "теракт",
                  "إرهاب", "انتحاري", "zamach terror", "anschlag"],
    "attack": ["attack", "attaque", "ataque", "atentado", "attacco", "angriff", "aanval", "atak", "saldırı", "напад",
               "нападение", "هجوم", "bomb", "bombs", "bombe$", "bombes$", "bombing", "bomba$", "bombas$", "explos", "blast", "gunm", "shooting", "fusillade", "tiroteo",
               "tiroteio", "sparatoria", "schießerei", "schiesserei", "strzelanin", "silahlı", "стрельб", "استهداف",
               "stabbing", "poignard", "kidnap", "enlèvement", "enleve", "secuestro", "sequestro", "rapimento",
               "entführ", "porwan", "kaçırıl", "похищ", "اختطاف", "hostage", "otage", "rehén", "refém", "ostaggi", "geisel",
               "assassin", "ied", "grenade", "arson", "incendie criminel", "pirates", "hijack", "hijacked", "hijacker"],
    "armed_conflict": ["airstrike", "air strike", "frappe", "bombard", "shelling", "artiller", "missile", "drone strike",
                       "drone strikes", "drone attack", "drone attacks", "attaque de drone", "attaques de drones", "frappe de drone",
                       "drones explosivos", "drones kamikazes", "drones kamikaze", "drones cargados", "drone-strike", "drones target", "drones hit",
                       "forces advance", "advance on", "advance in", "retake", "retakes", "recapture", "takes control",
                       "take control", "prend le controle", "toma el control", "rebels retreat", "clashes", "affrontement", "enfrentamiento", "confronto", "combat", "offensive",
                       "ofensiva", "gefecht", "kämpfe", "walki", "çatışma", "бой", "обстрел", "удар", "اشتباك",
                       "غارة", "قصف", "strikes kill", "strike kills", "strikes hit", "strikes on", "strike on", "strike hits", "strike hit", "deadly strike", "russian strike", "israeli strike", "missile strike", "hit by russian", "hit by israeli", "guided bomb", "frappes", "troops", "militants", "rebels", "rebelles", "rebeldes", "insurg", "ceasefire",
                       "cessez-le-feu", "alto el fuego", "invasion", "incursion", "militia", "milice", "milicia",
                       "war ", "guerre", "guerra", "krieg", "wojna", "savaş", "войн", "حرب"],
    "unrest": ["protest", "manifest", "demonstrat", "riot", "émeute", "emeute", "disturbio", "motim", "rivolta",
               "unruhen", "zamieszki", "ayaklanma", "бунт", "протест", "احتجاج", "مظاهر", "strike", "grève",
               "greve", "huelga", "sciopero", "streik", "staking", "strajk", "grev", "забастов", "إضراب",
               "blockade", "blocage", "bloqueo", "blocus", "heurts", "échauffourée", "echauffouree", "clashes with police", "curfew", "couvre-feu", "toque de queda", "coprifuoco",
               "ausgangssperre", "tear gas", "gaz lacrymogène", "lacrimógeno", "unrest", "troubles", "looting", "pillage", "saqueo"],
    "political": ["coup d'etat", "coup d etat", "coups d'etat", "coup attempt", "attempted coup", "failed coup", "military coup",
                  "tentative de coup", "coup militaire", "golpe de estado", "golpe militar", "intento de golpe", "golpe de estado",
                  "golpista", "golpistas", "colpo di stato", "staatsstreich", "militarputsch", "putsch", "darbe", "переворот", "انقلاب", "state of emergency", "état d'urgence",
                  "estado de emergencia", "stato di emergenza", "ausnahmezustand", "stan wyjątkowy", "olağanüstü hal",
                  "чрезвычайн", "حالة الطوارئ", "martial law", "loi martiale", "ley marcial", "impeach", "destitution",
                  ],
    "crime": ["cartel", "gang", "narco", "trafic de drogue", "drug traffick", "narcotráfico", "mafia", "robbery",
              "braquage", "atraco", "assalto", "rapina", "raub", "napad rabunkowy", "soygun", "ограблен", "سطو",
              "homicid", "homicide", "murder", "meurtre", "asesinato", "omicidio", "mord", "zabójstw", "cinayet",
              "убийств", "قتل", "piracy", "piraterie", "piratería", "extortion", "racket"],
    "cyber": ["cyber", "ransomware", "rançongiciel", "hack", "hacker", "hacked", "piratage", "data breach", "fuite de données",
              "ciberataque", "ataque informático", "attacco informatico", "hackerangriff", "atak hakerski",
              "siber saldırı", "кибератак", "хакер", "هجوم إلكتروني", "ddos", "malware", "phishing"],
    "infrastructure": ["blackout", "power outage", "panne d'électricité", "coupure", "apagón", "apagão", "blackout elettrico",
                       "stromausfall", "awaria prądu", "elektrik kesintisi", "отключени", "انقطاع الكهرباء",
                       "derail", "déraill", "descarril", "plane crash", "crash d'avion", "accidente aéreo",
                       "port closed", "airport closed", "aéroport fermé", "dam ", "barrage", "pipeline", "gazoduc",
                       "internet shutdown", "coupure d'internet", "collapse", "effondrement", "derrumbe"],
    "health": ["outbreak", "épidémie", "epidemia", "epidemie", "salgın", "эпидеми", "وباء", "cholera", "choléra",
               "cólera", "ebola", "marburg", "mpox", "measles", "rougeole", "sarampión", "dengue", "malaria",
               "paludisme", "avian flu", "grippe aviaire", "gripe aviar", "h5n1", "pandemic", "pandémie",
               "anthrax", "plague", "peste", "polio", "meningitis", "méningite", "lassa", "nipah", "yellow fever"],
    "earthquake": ["earthquake", "temblor", "enjambre sismico", "séisme", "seisme", "tremblement de terre", "sismo", "terremoto", "erdbeben",
                   "aardbeving", "trzęsienie", "deprem", "землетрясени", "زلزال", "tsunami", "magnitude"],
    "flood": ["flood", "inondation", "crue", "inundaci", "inundaç", "alluvion", "hochwasser", "überschwemm",
              "overstroming", "powódź", "sel ", "selde", "наводнени", "فيضان", "flash flood", "torrential"],
    "cyclone": ["cyclone", "hurricane", "ouragan", "huracán", "furacão", "uragano", "hurrikan", "typhoon", "typhon",
                "tifón", "tufão", "tifone", "taifun", "tajfun", "tayfun", "тайфун", "ураган", "إعصار", "tropical storm",
                "tempête tropicale", "tormenta tropical"],
    "storm": ["storm", "tempête", "tormenta", "tempestade", "tempesta", "sturm", "unwetter", "burza", "fırtına",
              "шторм", "буря", "عاصفة", "tornado", "blizzard", "hailstorm", "grêle", "granizo", "snowstorm"],
    "wildfire": ["wildfire", "forest fire", "bushfire", "feu de forêt", "incendie de forêt", "incendios forestales",
                 "incendio forestal", "incêndio florestal", "incendio boschivo", "waldbrand", "bosbrand",
                 "pożar lasu", "orman yangını", "лесной пожар", "حريق غابات"],
    "volcano": ["volcan", "volcano", "vulcão", "vulcano", "vulkan", "wulkan", "yanardağ", "вулкан", "بركان", "eruption", "éruption", "erupción"],
    "landslide": ["landslide", "glissement de terrain", "deslizamiento", "deslizamento", "frana", "erdrutsch",
                  "osuwisko", "heyelan", "оползень", "انهيار أرضي", "mudslide", "coulée de boue", "avalanche"],
    "extreme_temp": ["heatwave", "heat wave", "canicule", "ola de calor", "onda de calor", "ondata di calore",
                     "hitzewelle", "fala upałów", "sıcak hava dalgası", "жара", "موجة حر", "cold wave", "vague de froid"],
    "drought": ["drought", "sécheresse", "sequía", "seca", "siccità", "dürre", "susza", "kuraklık", "засух", "جفاف", "famine"],
}
# Langues ajoutées en v0.9 (presse des 25 pays) : hébreu, indonésien, thaï, chinois, persan, ourdou,
# bengali, amharique, somali. Listes volontairement courtes : les mots les moins ambigus.
EXTRA_WORDS = {
    "terrorism": ["טרור", "מחבל", "teroris", "terorisme", "bom bunuh diri", "ก่อการร้าย", "恐怖袭击", "恐怖襲擊", "恐袭",
                  "تروریست", "دہشت گرد", "دہشتگرد", "دہشت گردی", "জঙ্গি", "সন্ত্রাস", "አሸባሪ", "argagax"],
    "attack": ["פיגוע", "פיצוץ", "ירי", "חטיפה", "חטוף", "serangan", "ledakan", "penembakan", "penculikan", "sandera",
               "โจมตี", "ระเบิด", "ลอบยิง", "กราดยิง", "ลักพาตัว", "ตัวประกัน", "袭击", "襲擊", "爆炸", "枪击", "槍擊", "持刀",
               "砍人", "绑架", "綁架", "人质", "人質", "纵火", "縱火", "حمله", "تیراندازی", "گروگان", "حملہ", "دھماکہ",
               "دھماکا", "فائرنگ", "اغوا", "یرغمال", "হামলা", "বিস্ফোরণ", "গুলি", "অপহরণ", "ጥቃት", "ፍንዳታ", "እገታ",
               "weerar", "qarax", "toogasho", "afduub"],
    "armed_conflict": ["רקטות", "רקטה", "טילים", "יירוט", "אזעקות", "תקיפה", "bentrok", "kontak senjata", "kkb",
                       "ปะทะ", "สู้รบ", "ขีปนาวุธ", "交火", "空袭", "空襲", "导弹", "導彈", "军事冲突", "軍事衝突",
                       "درگیری", "پهپاد", "موشک", "بمباران", "جنگ", "جھڑپ", "ڈرون", "میزائل", "ውጊያ", "ግጭት",
                       "dagaal", "duqeyn"],
    "unrest": ["הפגנה", "הפגנות", "מהומות", "שביתה", "demonstrasi", "unjuk rasa", "kerusuhan", "mogok",
               "gas air mata", "ชุมนุม", "ประท้วง", "จลาจล", "นัดหยุดงาน", "แก๊สน้ำตา", "抗议", "抗議", "示威",
               "骚乱", "騷亂", "罢工", "罷工", "群体性事件", "催泪", "催淚", "اعتراض", "تجمع", "اعتصاب", "تظاهرات",
               "ناآرامی", "احتجاج", "مظاہرہ", "ہڑتال", "دھرنا", "বিক্ষোভ", "সংঘর্ষ", "হরতাল", "অবরোধ", "কারফিউ",
               "ተቃውሞ", "ሰልፍ", "banaanbax", "mudaaharaad"],
    "political": ["מצב חירום", "kudeta", "keadaan darurat", "รัฐประหาร", "ภาวะฉุกเฉิน",
                  "กฎอัยการศึก", "政变", "政變", "紧急状态", "緊急狀態", "戒严", "戒嚴",
                  "کودتا", "مارشل لاء", "ایمرجنسی", "জরুরি অবস্থা",
                  "አስቸኳይ ጊዜ", "xaalad degdeg"],
    "crime": ["רצח", "נרצח", "pembunuhan", "perampokan", "narkoba", "ฆาตกรรม", "ปล้น", "ยาเสพติด", "谋杀", "謀殺",
              "凶杀", "兇殺", "抢劫", "搶劫", "贩毒", "販毒", "黑帮", "黑幫", "سرقت", "قاچاق", "ڈکیتی", "منشیات",
              "হত্যা", "ডাকাতি", "মাদক", "ግድያ"],
    "cyber": ["סייבר", "peretasan", "serangan siber", "แฮก", "网络攻击", "網絡攻擊", "黑客", "勒索软件", "حمله سایبری", "هکر"],
    "infrastructure": ["pemadaman listrik", "ไฟดับ", "ตกราง", "停电", "停電", "脱轨", "出軌", "坍塌", "矿难", "礦難",
                       "قطعی برق", "خاموشی", "قطع اینترنت", "বিদ্যুৎ বিভ্রাট"],
    "health": ["מגפה", "wabah", "demam berdarah", "kolera", "โรคระบาด", "ไข้เลือดออก", "อหิวาต์", "疫情", "霍乱", "霍亂",
               "登革热", "登革熱", "禽流感", "شیوع", "وبا", "ڈینگی", "پولیو", "ہیضہ", "ডেঙ্গু", "কলেরা", "ወረርሽኝ",
               "ኮሌራ", "daacuun"],
    "earthquake": ["רעידת אדמה", "gempa", "แผ่นดินไหว", "地震", "زلزله", "زمین لرزه", "زلزلہ", "ভূমিকম্প",
                   "የመሬት መንቀጥቀጥ", "dhulgariir"],
    "flood": ["שיטפון", "שיטפונות", "banjir", "น้ำท่วม", "洪水", "洪灾", "洪災", "内涝", "سیل", "سیلاب", "বন্যা", "ጎርፍ",
              "fatahaad"],
    "cyclone": ["siklon", "ไต้ฝุ่น", "台风", "颱風", "ঘূর্ণিঝড়"],
    "storm": ["puting beliung", "พายุ", "龙卷风", "龍捲風", "冰雹", "暴风", "طوفان", "آندھی", "ঝড়"],
    "wildfire": ["kebakaran hutan", "karhutla", "ไฟป่า", "山火", "森林火灾", "森林火災", "آتش سوزی جنگل"],
    "volcano": ["erupsi", "gunung api", "ภูเขาไฟ", "火山"],
    "landslide": ["longsor", "ดินถล่ม", "山体滑坡", "山泥傾瀉", "泥石流", "رانش زمین", "لینڈ سلائیڈنگ", "ভূমিধস"],
    "extreme_temp": ["gelombang panas", "คลื่นความร้อน", "热浪", "熱浪", "寒潮", "موج گرما", "ہیٹ ویو", "তাপপ্রবাহ"],
    "drought": ["kekeringan", "ภัยแล้ง", "干旱", "乾旱", "خشکسالی", "খরা", "ድርቅ", "abaar"],
}
for _c, _ws in EXTRA_WORDS.items():
    CATEGORY_WORDS[_c] = CATEGORY_WORDS[_c] + _ws
# Diplomatie & politique (v0.9.2) : signaux sans menace physique directe, conservés dans une catégorie à part
# (hors note de risque) – élections, démissions, sanctions, expulsions de diplomates, rupture de relations.
CATEGORY_WORDS["diplomatic"] = [
    "election", "élection", "elección", "eleição", "elezion", "wahl", "wybor", "seçim", "выбор", "انتخاب", "בחירות",
    "pemilu", "เลือกตั้ง", "选举", "選舉", "انتخابات", "নির্বাচন", "ምርጫ", "doorasho", "referendum", "référendum",
    "resign", "démission", "demission", "dimisión", "renúncia", "dimissioni", "rücktritt", "dymisj", "istifa",
    "отставк", "استقال", "sanction", "sanciones", "sanções", "sanktion", "санкц", "عقوبات", "تحریم",
    "expel", "expulse", "expulsion", "persona non grata", "ambassador", "ambassadeur", "embajador", "embaixador",
    "ambasciatore", "botschafter", "посол", "سفير", "diplomat", "diplomatic ties", "relations diplomatiques",
    "relaciones diplomáticas", "rompt ses relations", "severs ties", "cuts ties", "motion de censure", "no-confidence",
    "no confidence", "remaniement", "reshuffle", "dissolution de l'assemblée", "government collapse", "chute du gouvernement"]
# ordre de priorité quand plusieurs catégories correspondent
PRIORITY = ["terrorism", "armed_conflict", "attack", "earthquake", "cyclone", "flood", "volcano", "wildfire",
            "landslide", "health", "political", "unrest", "cyber", "infrastructure", "crime", "storm",
            "extreme_temp", "drought", "diplomatic"]
# titres regroupés en un seul incident s'ils relèvent de la même famille, au même endroit, le même jour
FAMILY = {"terrorism": "violence", "attack": "violence", "armed_conflict": "violence", "crime": "violence",
          "unrest": "unrest", "political": "political", "diplomatic": "diplomatic"}
BASE_SEVERITY = {"terrorism": 3, "armed_conflict": 2, "attack": 2, "political": 1, "unrest": 1, "crime": 1,
                 "cyber": 1, "infrastructure": 1, "health": 2, "earthquake": 2, "cyclone": 2, "flood": 2,
                 "volcano": 2, "wildfire": 1, "landslide": 2, "storm": 1, "extreme_temp": 1, "drought": 1,
                 "diplomatic": 1}
ESCALATE = ["coup", "golpe", "putsch", "massacre", "masacre", "carnage", "mass shooting", "suicide bomb",
            "kamikaze", "state of emergency", "état d'urgence", "martial law", "loi martiale", "riot", "émeute"]
DEATH_RE = re.compile(r"(\d{1,5})\s*(?:people\s+|personnes\s+|personas\s+|pessoas\s+|persone\s+|menschen\s+)?"
                      r"(?:dead|killed|die[ds]?|morts?|tués?|muertos|fallecidos|mortos|morti|tote|todesopfer|"
                      r"zabitych|ofiar|ölü|hayatını|погиб|убит|قتيل|قتلى)", re.I)

KILLS_RE = re.compile(r"(?:kill(?:s|ed|ing)?|tue(?:nt)?|fait|deja|dejan|mata(?:m|n)?|uccide|t[öo]tet)\s+"
                      r"(?:at least\s+|au moins\s+|al menos\s+|pelo menos\s+|almeno\s+|mindestens\s+)?(\d{1,5})", re.I)

ECONOMY_WORDS = ["invest", "contrat", "contract", "contrato", "contratto", "vertrag", "umowa", "sözleşme", "контракт",
                 "عقد", "tender", "appel d'offres", "licitación", "licitação", "gara d'appalto", "ausschreibung",
                 "przetarg", "ihale", "тендер", "مناقصة", "privati", "acquisition", "acquiert", "adquisición",
                 "aquisição", "acquisizione", "übernahme", "przejęci", "satın al", "приобрет", "استحواذ", "factory",
                 "usine", "fábrica", "fabbrica", "fabrik", "fabryk", "fabrika", "завод", "مصنع", "export", "import",
                 "tariff", "droits de douane", "arancel", "tarifa", "dazi", "zölle", "cła", "gümrük", "пошлин",
                 "رسوم جمركية", "free trade", "libre-échange", "accord commercial", "trade deal", "gdp", "pib",
                 "inflation", "inflación", "inflação", "growth", "croissance", "crecimiento", "crescimento",
                 "concession", "mining", "minier", "minería", "mineração", "oil", "pétrole", "petróleo", "gas ",
                 "gaz ", "startup", "joint venture", "partenariat", "partnership", "sanction", "embargo", "ipo",
                 "bourse", "stock exchange", "central bank", "banque centrale", "banco central", "fdi", "ide "]

SPEECH_VERBS = ("says", "said", "warns", "warned", "accuses", "accused", "announces", "denies", "urges", "calls",
                "rejects", "dit", "affirme", "accuse", "annonce", "dénonce", "appelle", "rejette", "dice",
                "afirma", "acusa", "anuncia", "denuncia", "diz", "sagt", "warnt", "wirft", "говорит", "заявил")

LOC_PREP = {"in", "at", "near", "outside", "around", "a", "au", "aux", "en", "pres", "dans", "vers", "cerca", "de", "del", "em", "no", "na", "nel", "nella", "bei", "nahe", "im", "w", "we", "pod", "yakinlarinda",
            "в", "под", "у", "في", "قرب"}
PREP_LANGS = {"en", "fr", "es", "pt", "it", "de", "nl", ""}
NATURAL = {"earthquake", "flood", "cyclone", "storm", "wildfire", "volcano", "landslide", "extreme_temp", "drought"}

STOP_PLACES = {"nice", "mobile", "split", "bath", "reading", "van", "bar", "mary", "victoria", "florence",
               "police", "union", "independence", "liberty", "hope", "mercedes", "concord", "george", "orange",
               "marina", "patience", "trinidad", "valencia", "cordoba", "santiago", "san jose", "la paz", "grand",
               "de", "la", "le", "el", "san", "santa", "centre", "center", "city", "nord", "sud", "north", "south",
               "east", "west", "new", "port", "ville", "gaza city"}


def norm(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


# Écritures sans espace entre les mots (thaï, chinois, birman) ou à préfixes collés (éthiopien) :
# recherche en sous-chaîne. Hébreu et écriture arabe : préfixes courants autorisés (ה/ב/ו/ל…, و/ب/ال…).
_NOSPACE = re.compile(r"[\u0E00-\u0E7F\u3400-\u9FFF\uF900-\uFAFF\u1000-\u109F\u1200-\u139F]")
_HEBREW = re.compile(r"[\u0590-\u05FF]")
_ARABIC = re.compile(r"[\u0600-\u06FF]")


def _alt(p):
    if _NOSPACE.search(p):
        return re.escape(p)
    pre = r"(?<!\w)"
    if _HEBREW.search(p):
        pre += "(?:[הבולמשכ]{1,2})?"
    elif _ARABIC.search(p):
        pre += "(?:[وفبل])?(?:ال|لل)?"
    exact = p.endswith("$")  # « proces$ » : mot entier (sinon racine : « proces » trouverait « processus »)
    p = p.rstrip("$")
    return pre + re.escape(p) + (r"(?!\w)" if exact or len(p) <= 4 else "")


def _word_re(words):
    """Racines longues : début de mot (« manifest » → manifestation). Mots courts : mot entier
    (« coup » ne doit pas trouver « coupure »). Voir _alt pour les écritures non latines."""
    parts = sorted({norm(w).strip() for w in words if norm(w).strip()}, key=len, reverse=True)
    return re.compile("|".join(_alt(p) for p in parts), re.I)


# Variantes des racines courtes (≤ 4 lettres = mot entier) : « gunm » ne trouvait pas « gunmen ».
for _c, _ws in {"attack": ["gunmen", "gunman", "gunned down", "shot dead", "abduct", "tue par balle", "tues par balle",
                           "tuee par balle", "abattu", "abattus", "narchomicide", "ataku", "ataki", "enlevent", "enleves",
                           "enlevees", "rapt"],
                "unrest": ["riots", "rioting", "rioters"], "cyber": ["hacked", "hackers", "hacking"],
                "crime": ["gangs", "mordes", "raububerfall"], "flood": ["crues"], "diplomatic": ["wahlen"],
                "wildfire": ["feux de foret", "incendie de vegetation", "incendies de foret", "feu de broussailles",
                             "brush fire"]}.items():
    CATEGORY_WORDS[_c] = CATEGORY_WORDS[_c] + _ws
_CAT_RE = {c: _word_re(ws) for c, ws in CATEGORY_WORDS.items()}
_ESC_RE = _word_re(ESCALATE)
_ECO_RE = _word_re(ECONOMY_WORDS)


# Titres qui contiennent un mot-clé mais ne décrivent pas un incident réel (exercices, sport, culture…)
NOISE_WORDS = ["drill", "exercise", "exercice", "simulacro", "simulation", "tatbikat", "учени", "учебн", "übung",
               "esercitazione", "song", "chanson", "cancion", "album", "concert", "film", "movie", "series",
               "football", "soccer", "match ", "stadium", "stade", "estadio", "maracana", "league", "ligue",
               "anniversary", "anniversaire", "aniversario", "commemorat", "commémor", "hornet", "frelon", "wasp",
               "help desk", "helpdesk", "recipe", "horoscope", "museum", "musée", "exhibition", "exposition",
               "video game", "jeu vidéo", "acquit", "acquitte", "absuelto", "years ago", "il y a 10 ans",
               "biopic", "novel", "roman$", "podcast", "quiz", "bombay", "shooting stars", "npfl", "striker", "buteur",
               "goleador", "delantero", "attaquant", "offensive line", "theatre", "theater", "photo shoot", "shooting photo",
               "videoclip", "trailer", "bande-annonce", "attack on titan", "panic attack", "crise de panique",
               "heart attack", "crise cardiaque", "infarto", "herzinfarkt",
               "rinde protesta", "toma protesta", "tomo protesta", "manifestation culturelle", "manifestation sportive",
               "cinema", "journee mondiale", "memorializ", "fact check", "fact-check", "no muestra", "ne montre pas",
               "fausse video", "fake video", "punk", "runs riot", "octobre rose", "cf$", "fc$", "futbol", "partido de futbol",
               "debate", "pape", "pope", "papa leon", "offensive diplomatique", "diplomatic offensive", "charm offensive",
               "offensive de charme", "long combat", "combat pour", "combat contre", "fight against", "lucha contra",
               "analyst reveals", "opinion", "[opinia]", "editorial", "tribune libre", "interview", "entretien avec",
               "player ratings", "ratings", "debut", "debutto", "derby", "tournoi", "torneo", "tournament", "championship",
               "championnat", "asian games", "olympi", "medal", "medaille d'or", "documentary", "documentaire",
               "audience award", "explosive ordnance", "munitions cleared", "deminage", "demining",
               # v0.23 : sport, spectacle, faux sens (« enlèvent les vélos », « coup d'envoi »)
               "rugby", "basket", "nba", "tennis", "cricket", "golf", "handball", "volley", "cyclisme", "boxe", "boxing",
               "mma", "ufc", "lutte traditionnelle", "wrestling", "gala", "reality", "supervivientes", "festejos",
               "moros y cristianos", "carnaval", "desfile", "defile de mode", "fashion", "semi-marathon", "marathon",
               "course a pied", "aventurier", "stock exchange", "bourse", "verpflichtung", "fichaje", "mercato",
               "enlevent les", "enlever les", "enleve les", "crematorium", "crematorio", "coup d'envoi", "pelea",
               "rina", "rixe", "bagarre", "brawl", "scuffle", "alumnas", "hostel", "stages own", "own kidnapping",
               "simular", "left willingly", "playero", "motochorro", "habitante de calle", "centro de estetica",
               "siniestro", "picadas", "fiestas patronales", "training flight",
               "vol d'entrainement", "vuelo de entrenamiento", "risco de protesto", "protesto de", "zebrastreifen",
               "candidates", "candidats", "candidatos", "رزمایش", "مانور"]
_NOISE_RE = _word_re(NOISE_WORDS)

# Pas un incident pour une organisation ou un voyageur : procédure judiciaire (mise en examen, procès,
# condamnation…), sauf si le titre signale une mobilisation en cours (manifestation, émeute, blocage).
JUDICIAL_WORDS = ["mis en examen", "mise en examen", "mis en cause", "proces$", "condamne", "condamnation", "jugement", "juge ",
                  "juges", "tribunal", "cour d'assises", "assises", "garde a vue", "verdict", "requisitoire", "requis",
                  "peine de", "prison ferme", "detention provisoire", "inculpe", "comparution", "comparait", "audience",
                  "relaxe", "plainte", "enquete ouverte", "ouvre une enquete", "parquet", "sentenced", "sentence",
                  "trial", "convicted", "conviction", "charged with", "indicted", "pleads guilty", "pleaded", "jury",
                  "court hears", "in court", "appeal court", "juicio", "condenado", "condena", "sentencia", "imputado",
                  "processo", "condannato", "condenado", "julgamento", "prozess", "verurteilt", "angeklagt", "vonnis",
                  "wyrok", "sad skazal", "mahkum", "hapis cezasi", "приговор", "осужден", "суд ", "حكم", "محاكمة",
                  "משפט", "נגזר", "vonis", "sidang", "divonis", "判决", "判處", "審判", "دادگاه", "حکم", "سپریم کورٹ", "سزا یافتہ", "suma otro proceso", "proceso por"]
_JUDICIAL_RE = _word_re(JUDICIAL_WORDS)
_MOBILISATION_RE = _word_re(CATEGORY_WORDS["unrest"] + ["marcha", "marchas", "marche blanche", "affrontements avec",
                                                          "enfrentamientos con", "clashes with"])
# Fait divers : violence privée ou familiale, drame individuel. Aucun impact pour une organisation.
PRIVATE_WORDS = ["sa compagne", "son compagnon", "son epouse", "sa femme", "son mari", "son ex", "sa fille", "son fils",
                 "sa mere", "son pere", "ses enfants", "son bebe", "son voisin", "sa voisine", "conjugal", "conjugale",
                 "feminicide", "infanticide", "parricide", "violences intrafamiliales", "drame familial", "familial",
                 "septuagenaire", "octogenaire", "nonagenaire", "sexagenaire", "quinquagenaire", "quadragenaire",
                 "retraite ", "adolescent", "collegien", "lyceenne", "lyceen", "ecolier", "enfant de", "bebe", "a coups de",
                 "his wife", "her husband", "his girlfriend", "her boyfriend", "ex-wife", "ex-husband", "girlfriend",
                 "boyfriend", "domestic", "his mother", "his father", "her mother", "neighbour", "neighbor", "toddler",
                 "teenager", "teen ", "pensioner", "su esposa", "su pareja", "su marido", "feminicidio", "violencia de genero",
                 "sua mulher", "companheira", "moglie", "compagna", "ehefrau", "freundin", "partnerin", "femizid",
                 "suicide", "suicid", "se suicide", "overdose", "noyade", "drowned", "noye", "family members",
                 "membres d'une meme famille", "miembros de una familia", "familiares"]
_PRIVATE_RE = _word_re(PRIVATE_WORDS)
# « suicide » désigne ici un mode opératoire terroriste, pas un drame privé (corrigé lors de l'audit v0.17)
_SUICIDE_ATTACK_RE = re.compile(r"suicide[ -]?(bomb\w*|attack\w*|car|truck|vest|drone|blast|explosion)|(attentat|attaque)s?[ -]suicide|kamikaze|bombe humaine")
# Criminalité retenue seulement si elle relève de l'ordre public ou menace des entreprises et des voyageurs.
PUBLIC_CRIME_WORDS = ["cartel", "gang", "narco", "trafic", "traffick", "mafia", "reglement de comptes", "reglements de comptes",
                      "fusillade", "shooting", "tiroteo", "sparatoria", "braquage", "attaque a main armee", "armed robbery",
                      "robo a mano armada", "car-jacking", "carjacking", "home-jacking", "extorsion", "extortion", "racket",
                      "piraterie", "piracy", "pirates", "enlevement", "kidnap", "secuestro", "rapt", "rancon", "ransom",
                      "pillage", "looting", "saqueo", "bandit", "banditisme", "hold-up", "narcotrafico", "sicario",
                      "coupeurs de route", "embuscade", "ambush", "crime organise", "organized crime", "criminal group"]
_PUBLIC_CRIME_RE = _word_re(PUBLIC_CRIME_WORDS)

# ------------------------------------------------------------------ pertinence des « attaques » (v0.11)
# Les mots « attaque / ataque / attack / explosion » sont très ambigus : sport, politique, animaux, accidents
# domestiques, faits divers locaux. Une attaque n'est retenue que si elle est violente ET pertinente pour une
# organisation ou un voyageur : bilan lourd, lieu public ou cible institutionnelle, groupe armé, enlèvement.
GENERIC_ATTACK = ["attack", "attacks", "attacked", "attaque", "attaques", "attaqué", "ataque", "ataques", "atacan",
                  "atacado", "attacco", "angriff", "aanval", "atak", "saldırı", "saldiri", "saldırıya", "напад", "нападение",
                  "هجوم"]
EXPLOSION_WORDS = ["explos", "blast", "explosie", "patlama", "взрыв", "انفجار", "פיצוץ", "爆炸", "ระเบิด", "ledakan"]
INTENT_WORDS = ["bomb", "bombs", "bombe$", "bombes$", "bombing", "attentat", "atentado", "attentato", "anschlag", "terror", "ied",
                "engin explosif", "artefacto explosivo", "explosive device", "car bomb", "voiture piegee", "coche bomba",
                "grenade", "granada", "molotov", "drone", "missile", "rocket", "roquette", "suicide bomber", "kamikaze",
                "sabotage", "sabotaje", "attack", "attaque", "ataque", "angriff", "saldiri", "militant", "jihad",
                "insurg", "rebel", "rebelle", "gunmen", "hommes armes", "hombres armados", "shelling", "strike", "target", "targets",
                "targeted", "targeting", "visant", "vise", "cible", "ciblant", "contra ", "against"]
ACCIDENT_WORDS = ["gas", "gaz", "fuite", "leak", "combustiv", "combustible", "carburant", "fuel", "station-service",
                  "gas station", "gasolinera", "petrol", "tanker truck", "camion-citerne", "fuga", "vazamento", "pirotecnia", "cohete", "fireworks", "feu d'artifice",
                  "feux d'artifice", "petard", "boller", "transformador", "transformer", "transformateur", "chaudiere",
                  "boiler", "caldera", "cilindro", "bonbonne", "garrafa"]
FIREWORK_WORDS = ["pirotecnia", "cohete", "cohetes", "fireworks", "feu d'artifice", "feux d'artifice", "petard",
                  "petards", "boller", "polvora", "fogos"]
ANIMAL_WORDS = ["dog", "dogs", "chien", "chiens", "perro", "perros", "cachorro", "rottweiler", "pitbull", "pit bull",
                "kopek", "собак", "hund", "hunde", "elephant", "requin", "shark", "tiburon", "bear attack", "ours",
                "crocodile", "cocodrilo", "lion", "tigre", "tiger", "serpent", "snake", "loup", "wolf", "jaguar",
                "leopard", "cougar", "puma", "abeilles", "bees", "wasps"]
VIOLENCE_WORDS = ["kill", "killed", "killing", "kills", "dead", "death", "died", "dies", "mort", "morts", "tue", "tues", "tuee", "decede",
                  "muerto", "muertos", "muere", "murio", "fallecido", "morto", "mortos", "morre", "tot", "tote", "getotet",
                  "ermordet", "mata", "matan", "mato", "asesina", "asesinan", "asesinado", "asesinato", "assassin", "murder", "meurtre", "homicid", "muerte", "muertes", "morte", "mortes", "bala", "violent attack", "attaque violente", "olu", "oldu", "hayatini kaybetti", "убит", "погиб", "قتيل", "قتلى", "شهيد", "martyr",
                  "injur", "wound", "hurt", "blesse", "blesses", "herido", "heridos", "lesionad", "ferido", "feridos",
                  "verletzt", "yarali", "ранен", "جرحى", "مصاب", "casualt", "victim", "victime", "victima", "vitima",
                  "gunman", "gunmen", "gunfire", "gunshot", "shot", "shots", "disparo", "disparos", "balazo", "balazos",
                  "balacera", "a tiros", "tiros", "baleado", "arme", "armes", "arma", "armas", "armado", "armados",
                  "armed", "silahli", "knife", "couteau", "cuchillo", "faca", "messer", "machete", "stabb", "poignard",
                  "apunal", "esfaque", "niedergestochen", "erstochen", "bomb", "bombe$", "bomba$", "ied", "grenade", "granada", "explosive", "explosif",
                  "molotov", "drone", "missile", "rocket", "roquette", "mortar", "mortier", "hostage", "otage", "rehen",
                  "refem", "kidnap", "enlev", "secuestr", "sequestr", "entfuhr", "rapt", "arson", "incendiaire",
                  "incendiario", "sabotage", "sabotaje", "terror", "jihad", "militant", "insurg", "rebel", "bandit",
                  "gang", "cartel", "sicario", "massacre", "masacre", "tuerie", "chacina", "lynch", "fusillade",
                  "shooting", "tiroteo", "tiroteio", "sparatoria", "schiesserei", "strzelanin", "стрельб"]
MASS_WORDS = ["massacre", "masacre", "tuerie", "mass shooting", "chacina", "carnage", "bain de sang", "matanza",
              "strage", "blutbad", "katliam", "бойня", "مجزرة"]
PUBLIC_TARGET_WORDS = [
    # lieux publics et transports
    "school", "elementary", "secundaria", "preparatoria", "primaria", "juez", "jueza", "judge", "juge$", "magistrat", "funcionario", "funcionaria", "truck", "trucks", "lorry", "camion", "camiones", "caminhao", "driver", "drivers", "chauffeur", "chofer", "conductor", "transportista", "taxi", "mototaxi", "colectivo", "aid convoy", "aid truck", "aid trucks", "crew", "equipage", "tripulacion", "centro de salud", "health centre", "health center", "centre de sante", "educativa", "students", "estudiantes", "alumnos", "eleves", "etudiants", "estudantes", "ecole", "lycee", "college$", "university", "universite", "universidad", "universidade", "campus",
    "colegio", "escuela", "escola", "schule", "okul", "universitesi", "hospital$", "hospitals$", "hopital$", "hopitaux", "clinic$", "clinique$",
    "market", "marche", "mercado", "markt", "bazaar", "souk", "mall", "centre commercial", "shopping", "supermarket",
    "supermarche", "hotel", "restaurant", "cafe", "kahvehane", "bar", "nightclub", "discotheque", "boite de nuit",
    "discoteca", "festival", "bus", "autobus", "omnibus", "combi", "minibus", "train", "tren", "metro", "subway",
    "tram", "station", "gare", "estacion", "bahnhof", "hauptbahnhof", "airport", "aeroport", "aeropuerto", "aeroporto",
    "flughafen", "port ", "ferry", "highway", "autoroute", "carretera", "rodovia", "axe ",
    "church", "eglise", "iglesia", "igreja", "kirche", "mosque", "mosquee", "mezquita", "moschee", "synagog", "temple",
    "pagoda", "shrine", "pilgrim", "pelerin", "crowd", "foule", "multitud", "rassemblement", "parade", "defile",
    # cibles institutionnelles, économiques, humanitaires
    "embassy", "ambassade", "embajada", "consulat", "consulate", "police officer", "police officers", "policeman", "policemen", "police station", "police post", "police hq",
    "police headquarters", "police personnel", "police patrol", "cop", "cops", "officers", "law enforcement",
    "policier", "policiers", "commissariat", "gendarm", "policias", "agente", "agentes", "agent", "reten", "carabinero",
    "polizist", "polizisten", "polisi", "полицейск", "tavern", "taverne", "pub", "supplier", "defence", "defense company", "army", "armee", "ejercito", "exercito", "military",
    "militaire", "militar", "soldier", "soldat", "soldado", "troops", "checkpoint", "security post", "security forces",
    "forces de securite", "fuerzas de seguridad", "base ", "barracks", "caserne", "cuartel", "convoy", "convoi",
    "patrol", "patrouille", "government", "gouvernement", "gobierno", "ministry", "ministere", "ministerio",
    "parliament", "parlement", "congres", "town hall", "mairie", "prefecture", "court house", "palais de justice",
    "prison", "carcel", "company", "entreprise", "empresa", "factory", "usine", "fabrica", "plant", "mine ", "minas",
    "pipeline", "oleoduc", "gazoduc", "refinery", "raffinerie", "oil field", "power station", "centrale", "tanker",
    "ship", "navire", "buque", "vessel", "tourist", "touriste", "turista", "tourismus", "foreigner", "etranger",
    "extranjero", "expat", "aid worker", "humanitar", "ngo", "ong", "united nations", "onu", "peacekeep", "casque bleu",
    "journalist", "journaliste", "periodista", "jornalista", "reporter",
    # personnalités politiques
    "mayor", "maire", "alcalde", "exalcalde", "prefeito", "sindaco", "burgermeister", "politician", "politicien",
    "politico", "politiker", "candidate", "candidat", "candidato", "deputy", "depute", "diputado", "deputado", "mp ",
    "senator", "senateur", "senador", "minister", "ministre", "ministro", "governor", "gouverneur", "gobernador",
    "governador", "president", "leader", "chef de parti", "party", "parti$", "partido", "opposition", "activist",
    "militant politique", "elu ", "councillor", "conseiller", "concejal", "vereador", "official", "responsable",
    # lieux de sûreté spécifiques
    "business", "commerce", "commerçant", "comerciante", "negocio", "is yeri", "boutique", "shop ", "store ", "bank",
    "banque", "banco", "atm", "jewel", "bijouterie"]
ARMED_GROUP_WORDS = ["gang", "gangs", "cartel", "narco", "sicario", "sicarios", "bandit", "bandits", "bandidos",
                     "gunmen", "armed men", "hommes armes", "individus armes", "hombres armados", "homens armados",
                     "bewaffnete", "silahli kisi", "militant", "militants", "jihad", "terror", "insurg", "rebel",
                     "rebelle", "rebeldes", "russia", "point de deal", "narcotrafic", "narchomicide", "narcobandit", "trafic de drogue", "drug-related", "russian", "russians", "russe", "russes", "ruso", "rusos", "israeli", "israelien", "idf", "tsahal", "rsf", "wagner", "africa corps", "taliban", "pkk", "m23", "adf", "codeco", "janjaweed", "tatmadaw", "junta", "militia", "milice", "milicia", "isis", "isil", "daech", "daesh", "etat islamique",
                     "islamic state", "al-shabaab", "shabaab", "boko haram", "iswap", "jnim", "aqmi", "al-qaeda",
                     "al qaida", "hamas", "hezbollah", "houthi", "ttp", "bla ", "farc", "eln ", "clan del golfo",
                     "mara ", "maras", "ms-13", "barrio 18", "crime organise", "organized crime", "crimen organizado",
                     "silahli saldiri", "vooraad", "coupeurs de route", "con drones", "drones explosivos", "drone attack",
                     "fuerza publica", "fuerzas armadas", "force publique", "embuscade", "ambush", "emboscada",
                     "kidnap", "enlev", "secuestr", "sequestr", "entfuhr", "rapt", "hostage", "otage", "rehen", "ransom",
                     "rancon", "rescate", "piracy", "pirates", "piraterie", "extorsion", "extortion"]
AFTERMATH_WORDS = [
    "arrested", "arrests", "arrest ", "charged", "charges", "suspect identified", "identified", "arraign", "indictment",
    "accused", "accuse ", "accusee", "remand", "custody", "detains", "detained", "sentencing", "lawyer", "captured",
    "suspects named", "named as", "witnesses", "buried", "burial", "enterre", "sepultan", "identidad", "identity",
    "crime scene", "old video", "ancienne video", "allanamiento", "retienen", "pedido de secuestro", "la trama",
    "families of", "family of", "familles de", "familias de", "familia de", "justice march",
    "attorney", "interpelle", "interpelles", "interpellation", "arrete", "arretes", "interpellee", "avocat", "la defense",
    "l'enquete", "enqueteur", "enqueteurs", "temoin", "temoins", "appel a temoin", "instruction", "juge d'instruction",
    "capturan", "capturaron", "capturado", "detenido", "detenidos", "demoraron", "se entrega", "carcel para",
    "judicializado", "imputan", "formalizado", "prision preventiva", "preso", "presos", "suspeito foi", "gefasst",
    "festgenommen", "verhaftet", "opgepakt", "aangehouden", "voorgeleid", "tutuklandi", "gozalti", "yakalandi",
    "задержан", "арестован", "mourns", "mourned", "funeral", "obseques", "hommage", "tribute", "honors", "honoured",
    "honored", "medaille", "decore", "heroism", "hero", "heros", "what we know", "ce que l'on sait", "lo que se sabe",
    "o que se sabe", "was wir wissen", "asi fue", "nuevo video", "new video", "details emerge", "new details",
    "nowe informacje", "reacts", "reagit", "first lesson", "ilk ders", "son yolculuguna", "urges probe",
    "independent probe", "rights group", "survivors", "survivants", "sobrevivientes", "one year after", "un an apres",
    "a year after", "years after", "ans apres", "anos despues", "memorial", "gedenk", "vigil", "veillee",
    "trial", "proces$", "juicio", "prozess"]
EVACUATION_WORDS = ["evacuat", "evacu", "evacua", "shelter in place", "shelter-in-place", "lockdown", "confinement",
                    "bouclage", "perimetre de securite", "эвакуац", "tahliye", "raeumung", "räumung"]
SPECIFIC_ATTACK = ["atentado", "attentat", "attentato", "anschlag", "bombing", "bomb", "car bomb", "voiture piegee",
                   "coche bomba", "ied", "grenade", "suicide bomber", "kamikaze", "sabotage", "sabotaje", "terror",
                   "jihad", "hostage", "otage", "rehen", "refem", "kidnap", "enlev", "secuestr", "sequestr", "entfuhr",
                   "rapt", "ambush", "embuscade", "emboscada", "massacre", "masacre", "fusillade", "shooting",
                   "tiroteo", "tiroteio", "sparatoria", "stabbing", "arson", "incendie criminel"]
SECURITY_TARGET_WORDS = ["security post", "checkpoint", "police", "policier", "gendarm", "army", "armee", "military",
                         "militaire", "soldier", "soldat", "troops", "base$", "barracks", "caserne", "convoy", "convoi",
                         "patrol", "patrouille", "government", "gouvernement", "govt", "ministry", "ministere", "embassy",
                         "ambassade", "consulate", "consulat", "mosque", "mosquee", "church", "eglise", "synagog",
                         "temple", "shrine", "market", "marche", "bazaar", "souk", "bus$", "buses$", "school", "ecole",
                         "university", "universite", "mall", "hotel", "restaurant", "cafe", "stadium", "crowd", "foule",
                         "rally", "meeting", "embassy", "pipeline", "oleoduc", "gazoduc", "rail", "railway", "via ferrea",
                         "voie ferree", "bridge", "pont", "airport", "aeroport", "checkpoint", "office of", "headquarters",
                         "siege"]
THREAT_WORDS = ["threat", "threats", "menace", "menaces", "amenaza", "amenazas", "ameaca", "drohung", "tehdit", "угроз",
                "hoax", "canular", "alerte a la bombe", "bomb threat", "alerta de bomba", "fausse alerte"]
_GENERIC_ATTACK_RE = _word_re(GENERIC_ATTACK)
_EXPLOSION_RE = _word_re(EXPLOSION_WORDS)
_INTENT_RE = _word_re(INTENT_WORDS)
_ACCIDENT_RE = _word_re(ACCIDENT_WORDS)
_FIREWORK_RE = _word_re(FIREWORK_WORDS)
_ANIMAL_RE = _word_re(ANIMAL_WORDS)
_VIOLENCE_RE = _word_re(VIOLENCE_WORDS)
_MASS_RE = _word_re(MASS_WORDS)
_PUBLIC_TARGET_RE = _word_re(PUBLIC_TARGET_WORDS)
_ARMED_GROUP_RE = _word_re(ARMED_GROUP_WORDS)
_AFTERMATH_RE = _word_re(AFTERMATH_WORDS)
_THREAT_RE = _word_re(THREAT_WORDS)
_EVAC_RE = _word_re(EVACUATION_WORDS)
_SECURITY_TARGET_RE = _word_re(SECURITY_TARGET_WORDS)
_SPECIFIC_RE = _word_re(SPECIFIC_ATTACK)
_NONLATIN = re.compile(r"[\u0590-\u06FF\u0750-\u077F\u0E00-\u0E7F\u0980-\u09FF\u1200-\u139F\u3400-\u9FFF]")
_TOLL2_RE = re.compile(r"(?:toll|bilan|saldo|balance)\D{0,25}?(\d{1,4})", re.I)
_NUM_WORDS = {"one": 1, "un": 1, "una": 1, "uno": 1, "une": 1, "um": 1, "uma": 1, "two": 2, "deux": 2, "dos": 2, "duas": 2, "dois": 2, "due": 2, "zwei": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "dozen": 12,
              "dozens": 24, "trois": 3, "quatre": 4, "cinq": 5, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
              "dizaine": 10, "dizaines": 20, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
              "nueve": 9, "diez": 10, "decena": 10, "decenas": 20, "quatro": 4, "sete": 7, "oito": 8, "dez": 10,
              "tre": 3, "quattro": 4, "cinque": 5, "drei": 3, "vier": 4, "funf": 5, "sechs": 6, "zehn": 10}
_TOLL_RE = re.compile(r"(?<!\w)(\d{1,4}|" + "|".join(_NUM_WORDS) + r")(?!\w)"
                      r"(?!\s*-?\s*(?:year|yr|ans?\b|anos|ano\b|jahr|yas|month|mois|meses))(?:\W+\w+){0,3}?\W+"
                      r"(?:dead|killed|die|morts?|tues?|blesses?|muertos?|muertas?|muertes|fallecid[oa]s?|heridos?|heridas?|lesionad[oa]s?|mortos?|feridos?|"
                      r"morti|feriti|tote|verletzte|olu|yarali|people|personnes|personas|pessoas|persone|menschen|"
                      r"victims?|victimes?|victimas?|injured|wounded|casualties)", re.I)


_DEAD_TOLL_RE = re.compile(r"(?<!\w)(\d{1,4}|" + "|".join(_NUM_WORDS) + r")(?!\w)"
                           r"(?!\s*-?\s*(?:year|yr|ans?\b|anos|ano\b|jahr|yas|month|mois|meses))(?:\W+\w+){0,3}?\W+"
                           r"(?:dead|killed|die[ds]?|morts?|tues?|muertos?|muertas?|muertes|mueren|murieron|fallecid[oa]s|asesinad[oa]s|mortos?|morrem|"
                           r"morti|tote|olu|fallecidos)", re.I)


_BOTH_RE = re.compile(r"(?:muert[oa]s?|killed|dead|mort|tue)\W+(?:\w+\W+){0,2}?(?:herid[oa]s?|lesionad[oa]s?|injured|wounded|blesse)")


def casualty_toll(t, dead_only=False):
    """Plus grand bilan (morts, ou morts et blessés) lisible dans le titre normalisé, 0 sinon."""
    best = 0
    for m in _TOLL2_RE.finditer(t):
        n = int(m.group(1))
        best = max(best, 0 if 1900 <= n <= 2100 else n)
    for m in KILLS_RE.finditer(t):   # « kills 4 colleagues », « tue au moins 3 »
        if m.group(0).split()[0] not in ("fait", "deja", "dejan"):
            n = int(m.group(1))
            best = max(best, 0 if 1900 <= n <= 2100 else n)
    for m in (_DEAD_TOLL_RE if dead_only else _TOLL_RE).finditer(t):
        v = m.group(1)
        n = int(v) if v.isdigit() else _NUM_WORDS.get(v, 0)
        if 1900 <= n <= 2100:  # une année, pas un bilan
            continue
        best = max(best, n)
    if not dead_only:   # « un muerto y dos heridos » : morts et blessés s'additionnent
        best = max(best, sum(_NUM_WORDS.get(m.group(1), 0) if not m.group(1).isdigit() else
                             (0 if 1900 <= int(m.group(1)) <= 2100 else int(m.group(1))) for m in _TOLL_RE.finditer(t)))
        if _BOTH_RE.search(t):   # « deja muerto y mujer herida »
            best = max(best, 2)
    return best


def heavy_toll(t):
    """Bilan lourd : au moins 3 morts ou 5 victimes."""
    return casualty_toll(t, dead_only=True) >= 3 or casualty_toll(t) >= 5


def notable_toll(t):
    """Bilan notable pour une attaque armée de droit commun : au moins 2 morts ou 3 victimes (v0.23)."""
    return casualty_toll(t, dead_only=True) >= 2 or casualty_toll(t) >= 3


def attack_relevance(t):
    """Motif d'exclusion d'un titre classé « attaque » (texte normalisé), ou None s'il faut le garder."""
    if _ANIMAL_RE.search(t):
        return "animal"
    if _FIREWORK_RE.search(t):
        return "accident"
    if _THREAT_RE.search(t) and casualty_toll(t) == 0 and not _MASS_RE.search(t) and not _EVAC_RE.search(t) \
            and not _NONLATIN.search(t):
        return "menace"
    if _EXPLOSION_RE.search(t) and not _INTENT_RE.search(t) and not _GENERIC_ATTACK_RE.search(t):
        # explosion sans intention affichée : retenue comme attaque seulement si elle frappe une cible de sûreté
        return None if _SECURITY_TARGET_RE.search(t) and not _ACCIDENT_RE.search(t) else "accident"
    if _NONLATIN.search(t):
        return None  # mots-clés hébreu, arabe, thaï, chinois… déjà spécifiques (tir, enlèvement)
    if _ARMED_GROUP_RE.search(t) or _MASS_RE.search(t):
        return None
    if not _VIOLENCE_RE.search(t) and not _SPECIFIC_RE.search(t):
        return "hors sujet"  # « Google attaque… », « le maire attaque l'opposition », sport
    # « transporté à l'hôpital » : la victime, pas une attaque contre un hôpital
    tt = _HOSPITAL_RE.sub(" ", t)
    if heavy_toll(t) or notable_toll(t) or _PUBLIC_TARGET_RE.search(tt):
        return None
    return "fait divers"


RETRO_WORDS = ["obras", "project", "projet", "proyecto", "projeto", "delayed", "recensement", "how to protect",
               "como protegerse", "comment se proteger", "is ready for", "ready for the next", "prepared for", "simulazione",
               "simulacion", "iddia", "one year after", "un an apres", "a un ano", "a un trimestre", "years after",
               "ans apres", "balance con", "parti'de", "lessons from", "lecons", "retour sur", "look back", "recuerdan",
               "remember", "se souvenir", "study", "etude", "investigaciones", "research", "recherche", "report finds",
               "critica", "criticises", "criticizes", "podria", "could", "pourrait", "may face", "risk of", "climate change",
               "changement climatique", "cambio climatico", "work on", "works on", "travaux", "remise de", "donation", "don de",
               "malgre", "despite", "faits et informations", "facts and", "ce qui va changer", "face aux", "tanggul",
               "perbaikan", "salles rafraichies"]
_RETRO_RE = _word_re(RETRO_WORDS)
_MAG_RE = re.compile(r"(\d[.,]\d)\s*(?:m|sr)(?!\w)|(?:magnitud[eo]?|magnitudo|mag\.?|m|mw|ml|magnitude|sismo|seisme|earthquake|quake|terremoto|temblor|deprem)\s*(?:de\s*|of\s*|:\s*)?(\d(?:[.,]\d)?)(?!\d)"
                     r"|(\d(?:[.,]\d)?)\s*(?:de\s+|-)?(?:magnitud[eo]?|magnitude|buyuklugunde|درجات|richter|sr\b)", re.I)
QUAKE_IMPACT = ["dead", "killed", "died", "mort", "morts", "muerto", "muertos", "mortos", "olu", "injur", "blesse",
                "herido", "ferido", "yarali", "damage", "degats", "danos", "hasar", "collapse", "effondr", "derrumb",
                "desab", "tsunami", "victim", "victime", "evacu", "destroy", "detruit", "destruy", "houses", "maisons",
                "viviendas", "casas", "jolts", "strong", "powerful", "violent", "puissant", "fuerte", "forte", "guclu",
                "siddetli", "injuries"]
_QUAKE_IMPACT_RE = _word_re(QUAKE_IMPACT)
_CONFLICT_EVENT_RE = _word_re(["airstrike", "airstrikes", "air strike", "air strikes", "deadly", "retake", "retakes",
                               "recapture", "takes control", "toma el control", "prend le controle", "shell", "shells",
                               "strike", "strikes", "frappe", "clash", "clashes", "affrontement", "enfrentamiento", "attack",
                               "attaque", "ataque", "offensive", "ofensiva", "shelling", "bombard", "drone", "missile",
                               "captur", "seize", "seized", "advance", "avance", "fighting", "combats", "battle", "bataille",
                               "ambush", "embuscade", "raid", "incursion", "invasion", "ceasefire", "cessez-le-feu",
                               "enfrentamientos", "confrontos", "gefecht", "kampfe", "удар", "обстрел", "бой", "غارة", "قصف",
                               "اشتباك"])
_LOCAL_POLITICS_RE = _word_re(["municipal", "municipales", "maire", "mayor", "alcalde", "conseil municipal", "city council",
                               "mla", "state assembly", "assembly election", "election petition", "la justice annule",
                               "high court", "supreme court", "cour supreme", "cour d'appel"])
_INDUSTRIAL_RE = _word_re(["plant", "planta", "usine", "factory", "fabrica", "refinery", "raffinerie", "refineria", "mine$",
                           "pipeline", "gazoduc", "oleoduc", "depot", "entrepot", "warehouse", "chemical", "chimique",
                           "quimica", "port$", "terminal", "power station", "centrale"])
_INFRA_IMPACT_RE = _word_re(["blackout", "power outage", "panne", "coupure", "apagon", "apagao", "stromausfall", "closed",
                             "ferme", "cerrado", "shutdown", "derail", "deraill", "descarril", "plane crash", "crash d'avion",
                             "dam$", "barrage", "pipeline", "gazoduc", "internet", "traffic", "trafic", "disrupt", "perturb"])
_SMALL_ACCIDENT_RE = _word_re(["crane", "grue", "scaffold", "echafaudage", "construction site", "chantier", "balcon",
                               "balcony", "wall collapse", "mur$", "building site"])


def not_incident(title, cat=None):
    """Titre qui ne décrit pas un incident pouvant toucher une organisation ou un voyageur (motif), sinon None."""
    t = norm(title)
    if cat in ("earthquake", "flood", "cyclone", "storm", "wildfire", "landslide", "volcano", "drought", "extreme_temp") and _RETRO_RE.search(t):
        return "rétrospective ou projet"
    if cat == "armed_conflict" and not _VIOLENCE_RE.search(t) and not _CONFLICT_EVENT_RE.search(t):
        return "analyse (pas d'incident)"  # « Poutine intensifie l'effort de guerre », « la guerre dans les esprits »
    if cat == "diplomatic" and (_LOCAL_POLITICS_RE.search(t) or _JUDICIAL_RE.search(t)):
        return "politique locale ou judiciaire"
    if cat == "infrastructure" and _EXPLOSION_RE.search(t) and not (heavy_toll(t) or _INDUSTRIAL_RE.search(t)
                                                                     or _SECURITY_TARGET_RE.search(t)):
        return "accident domestique"
    if cat == "infrastructure" and not (heavy_toll(t) or _INFRA_IMPACT_RE.search(t)) and _SMALL_ACCIDENT_RE.search(t):
        return "accident de chantier"
    if cat == "earthquake":
        mags = [float(next(g for g in m.groups() if g).replace(",", ".")) for m in _MAG_RE.finditer(t)]
        if mags and max(mags) < 5:
            return "séisme faible (couvert par l'USGS)"
        if not mags and not _QUAKE_IMPACT_RE.search(t):
            return "séisme sans impact"
    if _JUDICIAL_RE.search(t) and not _MOBILISATION_RE.search(t):
        return "judiciaire"
    if cat not in ("armed_conflict", "terrorism") and _PRIVATE_RE.search(_SUICIDE_ATTACK_RE.sub(" ", t)) \
            and not _PUBLIC_CRIME_RE.search(t):
        return "fait divers"
    if cat == "crime" and not _PUBLIC_CRIME_RE.search(t):
        return "fait divers"
    if cat in ("attack", "crime", "terrorism") and _AFTERMATH_RE.search(t) \
            and not _MOBILISATION_RE.search(t):
        return "suites judiciaires ou hommage"
    if cat in ("attack", "crime"):
        return attack_relevance(t)
    return None


# ------------------------------------------------------------------ contexte, pas événement (v0.23)
# Un « événement » de la carte doit pouvoir toucher physiquement un voyageur ou un site. Les titres suivants parlent
# bien de sûreté, mais d'autre chose qu'un fait physique : arrestations et suites d'enquête, complots déjoués,
# déclarations et réactions, analyses, rétrospectives et démentis, travaux de prévention, annonces militaires,
# signaux diplomatiques. Ils restent dans le Fil (contexte) mais ne sont plus placés sur la carte.
VIOLENT_CATS = {"attack", "terrorism", "armed_conflict", "crime"}
ARREST_WORDS = ["arrest", "arrested", "arrests", "jailed", "jail", "detenido", "detenidos", "detenida", "detenidas",
                "detiene", "detienen", "detuvo", "detencion", "aprehend", "captura a", "capturan a", "capturo a",
                "capturados", "capturado", "cae alias", "cae en", "cayo", "caen alias", "desarticul", "interpelle",
                "interpelles", "interpellation", "interpellations", "arrete", "arretes", "arretee", "arrestation",
                "prende", "presos", "preso", "festgenommen", "festnahme", "arrestato", "arrestati", "ditangkap",
                "held for", "cops charge", "police charge", "charges filed", "localiza", "localizan", "localizada",
                "identifies", "ids", "identified as", "identifie", "identifica", "fundraiser", "cagnotte", "cleared in",
                "court told", "acusado", "acusados", "accuses", "relata", "relato", "denuncian falsas", "sigue alojado", "ubicaron",
                "sospechoso de", "ends in", "ended", "resolved", "liberado", "liberada", "liberee", "libere", "freed",
                "held in", "nuevo giro", "proceso contra", "in aula", "collectionn", "transported to", "were transported"]
_ARREST_RE = _word_re(ARREST_WORDS)
FRESH_WORDS = ["killed", "kills", "kill", "dead", "dies", "died", "wounded", "injured", "injures", "tue", "tues", "tuee",
               "tuees", "morts", "mort", "blesse", "blesses", "blessee", "muere", "murio", "mueren", "muertos", "muerto",
               "heridos", "herido", "asesinad", "mortos", "morto", "feridos", "ferito", "feriti", "morti", "tote",
               "verletzt", "verletzte", "olu", "yarali", "tewas", "luka"]
_FRESH_RE = _word_re(FRESH_WORDS)
FOILED_WORDS = ["dejoue", "dejouee", "dejoues", "foil", "foiled", "foils", "thwart", "thwarted", "thwarts", "frustra ",
                "frustran", "frustro", "frustrado", "frustrada", "neutraliza", "neutralizan", "neutralizo", "vereitelt",
                "vereiteln", "sventato", "sventata", "plot", "plots", "plotting", "plotted", "complot", "geplant",
                "planeaban", "planeado", "planned attack", "planning attack", "projetait", "menace d'attentat",
                "entging", "entgehen", "dismantled", "demantele", "desmantel", "متلاشی", "خنثی", "blague", "canular",
                "fausse alerte", "false alarm", "falsa alarma"]
_FOILED_RE = _word_re(FOILED_WORDS)
REACTION_WORDS = ["condemn", "condemns", "condemned", "condamne", "condena", "condenan", "deplore", "deplores", "deplora",
                  "denounce", "denounces", "denonce", "denoncent", "calls for", "call for", "appelle a", "pide", "piden",
                  "pidio", "exige", "exigen", "seeks", "lauds", "salue", "assures", "assure", "promet", "promises", "vows",
                  "says ready", "clarifies", "denies", "deny", "dement", "dementi", "desmiente", "rejects", "responds",
                  "reacts", "tribute", "hommage", "homenaje", "funeral", "funerailles", "obseques", "minute de silence",
                  "visit", "visite", "visita", "se rend", "talks", "summit", "sommet", "cumbre", "convoco", "convoca",
                  "anuncia medidas", "anuncio medidas", "announces", "annonce", "plans to", "to hold", "proposes",
                  "agreement", "accord", "acuerdo", "support for", "supports", "soutien", "appui", "appuyer", "respalda",
                  "blame game", "alleges", "allegue", "accuse", "acusa", "warned israel", "warns that", "official protest",
                  "publient", "publie une liste", "publishes", "anuncia", "anuncio", "comision para", "esclarecer",
                  "laws against", "law against", "loi contre", "ley contra", "legislation", "tackle", "approach is needed",
                  "tells villagers", "resigns", "resign", "demissionne", "dimite", "renuncia", "preoccupe", "preoccupee", "concerned", "preocupa", "preocupado", "ziyaret", "retour au calme", "accalmie", "calm returns", "regresa la calma", "vuelve la calma", "lull"]
_REACTION_RE = _word_re(REACTION_WORDS)
ANALYSIS_WORDS = ["revela", "revelan", "reveal", "reveals", "revealed", "ce que l'on sait",
                  "ce qu'on sait", "lo que se sabe", "explained", "explainer", "takeaways", "analysis", "analyse",
                  "analisis", "las claves", "les cles", "key points", "disminuyen", "en baisse", "drop in",
                  "guerra por el control", "volvio a disparar", "nomina esperto", "indikator", "bisa jadi", "מודיעין", "expert says", "experts say", "plongee", "decryptage", "la historia de", "la historia del",
                  "the story of", "spur fuhrt", "ermittler", "ermittlungen", "report finds", "informe revela",
                  "security vacuum", "sanctuary", "year high", "year low", "highest level", "plus haut niveau", "nivel mas alto", "cabos sueltos", "censors", "criminalis", "of gdp", "du pib", "own estimate", "distraction", "persistira", "never-ending", "politics of", "vive la"]
_ANALYSIS_RE = _word_re(ANALYSIS_WORDS)
_QUESTION_RE = re.compile(r"(?:^|[\s¿:,;—–-])(?:qui|quoi|pourquoi|comment|who|whom|why|how|what|quien|quienes|que hacia|"
                          r"por que|hasta cuando|cuando|wer|warum|wie|perche|apakah|mengapa|kenapa)\b[^?]*\?")
RETRO2_WORDS = ["years ago", "anni fa", "anos atras", "ans apres", "years after", "years since", "ans du", "anniversaire",
                "aniversario", "anniversario", "memorial", "souvenir", "se souvenir", "seconde guerre mondiale",
                "second world war", "world war", "segunda guerra mundial", "weltkrieg", "remains of", "restes de",
                "hoax", "hoaks", "fake", "faux", "fausse", "falso", "falsa", "not a houthi", "n'est pas", "no es un",
                "debunk", "misleading", "no factual basis", "unfounded", "sin fundamento", "infonde", "a year after", "year after the", "siecle", "siglo xx", "century", "il y a un an", "hace un ano", "un an apres",
                "menolak lupa", "dikorupsi", "korupsi", "corruption", "detournement", "quatre ans du", "four years since",
                "3 years of", "three years of", "years of war", "relance la", "ravive", "mur des noms", "not a ", "שנים עברו",
                "الذكرى", "ذكرى"]
_RETRO2_RE = _word_re(RETRO2_WORDS)
_YEARS_AGO_RE = re.compile(r"\bhace (?:mas de )?(?:un|\d+) anos?\b|\b(?:il y a|vor)\s+\d+\s+(?:ans|jahren)\b|\b\d+\s+(?:years|anni|ans)\s+(?:ago|fa|apres|after)\b")
PREVENTION_WORDS = ["prevenir", "prevention", "lutter contre", "protection contre", "proteger", "proteger de", "defensas",
                    "dragas", "obra reclamada", "sumideros", "sensores", "sensors", "alegaciones", "real decreto",
                    "plan especifico", "homologado", "tanque de tormentas", "ampliara", "construye", "construira",
                    "builds", "mitigation", "control works", "inspection", "inspects", "tests flood", "flood response",
                    "simulasi", "gladi", "edukasi", "bangun", "drainase", "perbaiki", "normalisasi", "relokasi",
                    "rekomendasikan", "sinkronkan", "penanganan", "upayakan", "cegah", "tinjau", "bersihkan",
                    "kolam retensi", "gorong", "bantuan", "salurkan", "pasca", "niedrigwasser", "kritisieren",
                    "hochwasserschutz", "testaufbau", "une solution", "s'engage", "assainir", "millions d'euros",
                    "milioni di euro", "interventi$", "completato", "farmers facing", "refinanciar", "deudas",
                    "fotos que muestran", "festival", "cri contre", "vulnerable", "lecons", "expose", "doble castigo",
                    "aprender a vivir", "el nino", "la nina", "command centre", "relief reaches", "repaired",
                    "aplican la fibe", "catastrar", "oficina", "desactiva", "desactivan", "respiran aliviados", "alivio",
                    "descenso de", "llaves", "nuevas casas", "reconstruccion", "reconstruction", "rebuild", "anticipar",
                    "inteligencia artificial", "ia con", "satelites", "y ninguno", "central team", "assesses",
                    "visits drought", "pidieron limpieza", "obligan a reorganizar" , "never again", "babi hutan",
                    "karangan bunga", "solution pour", "visite", "se rend", "en visite", "enquete nationale", "survey", "gueris", "guerie",
                    "gueries", "recovered", "discharged", "sortent", "quittent", "laboratoires mobiles",
                    "laboratorios moviles", "plan de preparation", "plan de reponse", "funding", "financement",
                    "transparency", "transparence", "mobilisent", "entravent", "transfere", "testing stepped up",
                    "concours", "abo)", "tackle", "approach is needed", "tells villagers", "signs of recovery", "relief appeal", "appeal for", "donates", "relief materials", "rolls out", "allocates", "ziyaret"]
_PREVENTION_RE = _word_re(PREVENTION_WORDS)
MILITARY_CONTEXT_WORDS = ["displayed", "acquired", "acquisition", "unveil", "devoile", "live firings", "firings",
                          "deployment", "deploiement", "despliegue", "redeploy", "withdraw", "retrait des troupes",
                          "procure", "purchase", "achat", "needs additional", "air defenses", "defense aerienne",
                          "budget", "drone show", "create giant", "spectacle de drones", "interdiction", "disent adieu",
                          "spy", "espion", "briefings", "shown to", "missile system", "live:", "sichtungssystem", "new system",
                          "nouveau systeme", "nuevo sistema", "live updates",
                          "ligne de front", "trasladan su gobierno", "infiltration", "plan cristo rey", "ofensiva urbana",
                          "invasiones de tierras", "zozobra", "convoca", "consejo de seguridad", "medidas de seguridad",
                          "refuerzan seguridad", "seguridad en barrios", "pide intervencion", "laboratorios"]
_MILITARY_CONTEXT_RE = _word_re(MILITARY_CONTEXT_WORDS)
_HOSPITAL_RE = re.compile(r"(?:taken|rushed|transported|airlifted|brought) to (?:the )?hospital|hospitali[sz]\w*|"
                          r"(?:trasladad|llevad)\w* al hospital|transporte\w* a l'hopital|evacue\w* vers l'hopital")
# réaction ou annonce qui décrit pourtant une attaque précise (« condamne l'attaque de drone contre la centrale de Médine »,
# « le Yémen affirme avoir mené des centaines de frappes ») : l'événement est là, il reste sur la carte… sauf démenti,
# condamnation ou sommet (l'attaque elle-même a son propre titre, que le regroupement par histoire rattache).
_CONCRETE_ATTACK_RE = re.compile(r"\b(?:attacks? (?:on|against|targeting)|strikes? (?:on|against)|frappes? (?:sur|contre)|"
                                 r"(?:centaines|dizaines) de frappes|attaques? contre|attentats? contre|ataques? (?:contra|a)\b|"
                                 r"offensive (?:contre|against|on)|ofensiva contra|repel\w*|repouss\w*|repel(?:en|ieron|io)|"
                                 r"launch\w* (?:an? )?(?:strike|attack|offensive)|terrorist attack targeting|"
                                 r"hit (?:in|by) (?:an? )?\w+ (?:air ?strike|strike|attack|missile|drone)|"
                                 r"retakes?|recaptures?|takes control|seizes?|prend le controle|toma el control)")
_DENIAL_RE = _word_re(["condemn", "condamne", "condena", "deplore", "denounce", "denonce", "denies", "deny", "denied", "rejects", "rejected", "dement", "dementi", "desmiente", "niega",
                       "clarifies", "assures", "no shooting", "aucune attaque", "talks", "summit", "sommet", "cumbre",
                       "to hold", "if attacked", "links to", "liens avec"])
# fait physique constaté (feu, explosion, tirs) : un titre interrogatif qui en parle reste un événement
_PHYSICAL_RE = _word_re(["fire", "fires", "feuer", "brand", "incendi", "explos", "detona", "blast", "explot", "disparos",
                         "shots fired", "tiroteo", "fusillade", "shooting", "gunfire", "coups de feu", "schusse"])
_ELECTION_VIOLENCE_RE = _word_re(["disparos", "shots fired", "gunfire", "coups de feu", "tiroteo", "fusillade", "incendiad",
                                  "incendie", "torched", "set on fire", "quemaron", "queman", "affrontements", "clashes",
                                  "enfrentamientos", "violence", "violencia", "violent", "killed", "muertos", "morts"])
_LIGHTNING_RE = _word_re(["foudre", "foudroye", "lightning", "rayo", "relampago", "fulmine", "blitz", "petir", "sambaran"])
_SEIZURE_RE = re.compile(r"secuestros? de (?:armas|droga|drogas|elementos|bienes|vehiculos|mercaderia|celulares|cocaina|"
                         r"marihuana|dinero|municiones|motos)|sequestro de (?:armas|drogas|bens)")


def context(title, cat):
    """Titre de sûreté qui n'est pas un fait physique (motif) : gardé dans le Fil, pas placé sur la carte. Sinon None."""
    if cat == "diplomatic":
        return "signal politique"
    t = norm(title)
    if _RETRO2_RE.search(t) or _YEARS_AGO_RE.search(t):
        return "rétrospective ou démenti"
    if (_QUESTION_RE.search(t) and cat != "unrest") or _ANALYSIS_RE.search(t) \
            or ("?" in t and cat in VIOLENT_CATS and not _FRESH_RE.search(t) and not _PHYSICAL_RE.search(t)):
        return "analyse"  # « à quoi s'attendre pour la manifestation ? » reste une information pratique
    mobil = _MOBILISATION_RE.search(t)
    if cat in NATURAL or cat == "health":
        if _PREVENTION_RE.search(t):
            return "prévention, bilan ou suites"
        return None
    if cat in VIOLENT_CATS or cat in ("political", "cyber"):
        if _FOILED_RE.search(t) and not _FRESH_RE.search(t) and not re.search(r"detona|explosion|explot|blast", t):
            return "projet déjoué"
        if _FOILED_RE.search(t) and cat == "terrorism":
            return "projet déjoué"
        if not mobil:
            th = _HOSPITAL_RE.sub(" ", t)   # « transported to hospital » : la victime, pas une arrestation
            first = " ".join(th.split()[:6])
            if _ARREST_RE.search(first) or (_ARREST_RE.search(th) and not _FRESH_RE.search(th)):
                return "arrestation ou suites"
        tr = t.replace("support forces", " ")   # Rapid Support Forces (Soudan), pas un « soutien »
        if _REACTION_RE.search(tr) and not casualty_toll(t) and not _FRESH_RE.search(t) \
                and (_DENIAL_RE.search(t) or not _CONCRETE_ATTACK_RE.search(t)):
            return "déclaration"
        if cat in ("armed_conflict", "terrorism") and _MILITARY_CONTEXT_RE.search(t) and not _FRESH_RE.search(t) \
                and not _CONCRETE_ATTACK_RE.search(t):
            return "annonce militaire"
        if cat == "attack" and _MILITARY_CONTEXT_RE.search(t) and not _FRESH_RE.search(t):
            return "annonce de sécurité"
    return None


def is_event(title, cat):
    """Titre classé (catégorie connue) qui décrit un fait physique à placer sur la carte."""
    return bool(cat) and not not_incident(title, cat) and not context(title, cat)


_GDELT_PHYSICAL_RE = _word_re(["teargas", "flames", "smoke", "shot at", "shoot down", "shot down", "hits", "hit by", "raid",
                               "raids", "crash", "crashes", "collapse", "stampede", "looted", "obstruct", "blocked", "fire"])
_GDELT_SOFT = {"judiciaire", "suites judiciaires ou hommage", "rétrospective ou projet", "analyse (pas d'incident)",
               "politique locale ou judiciaire", "séisme faible (couvert par l'USGS)"}


def gdelt_noise(headline):
    """GDELT code ses événements à partir d'articles : la catégorie vient de GDELT, mais le titre réel de l'article
    (headline) dit souvent autre chose (portrait, procès, tribune, people). Motif d'exclusion, ou None (v0.23).
    Plus indulgent que le tri de la presse : on n'écarte que ce qui n'a manifestement rien de physique."""
    h = (headline or "").strip()
    if not h:
        return None
    t = _SEIZURE_RE.sub("saisie", norm(h))
    found = [c for c in PRIORITY if _CAT_RE[c].search(t)]
    if not found:
        if _VIOLENCE_RE.search(t) or _CONFLICT_EVENT_RE.search(t) or _PHYSICAL_RE.search(t) or _GDELT_PHYSICAL_RE.search(t):
            return None
        return "hors sujet"
    if _NOISE_RE.search(t):
        return "hors sujet"
    cat = found[0]
    why = not_incident(h, cat)
    if why in _GDELT_SOFT:
        return why
    return context(h, cat)


def classify(title):
    """Renvoie (catégorie, gravité) ou (None, None) si le titre ne relève pas de la sûreté."""
    t = _SEIZURE_RE.sub("saisie", norm(title))
    if _NOISE_RE.search(t):
        return None, None
    found = [c for c in PRIORITY if _CAT_RE[c].search(t)]
    if _LIGHTNING_RE.search(t):
        found = ["storm"] + [c for c in found if c not in ("armed_conflict", "attack", "storm")]
    if not found:
        return None, None
    cat = found[0]
    if cat == "diplomatic" and _ELECTION_VIOLENCE_RE.search(t):
        cat = "unrest"   # « élections sous tension : tirs et urnes incendiées » : un fait physique
    if cat == "attack" and _EXPLOSION_RE.search(t) and not _INTENT_RE.search(t) and not _GENERIC_ATTACK_RE.search(t):
        # explosion sans intention affichée : volcan, accident industriel ou domestique, ou attaque contre une cible
        others = [c for c in found[1:] if c not in ("attack", "crime")]
        if _FIREWORK_RE.search(t):
            return None, None
        if others:
            cat = others[0]
        elif _SECURITY_TARGET_RE.search(t) and not _ACCIDENT_RE.search(t):
            pass  # attaque probable (poste de sécurité, marché, bus…)
        elif _VIOLENCE_RE.search(t) or casualty_toll(t) or _ACCIDENT_RE.search(t) or _INDUSTRIAL_RE.search(t):
            cat = "infrastructure"
        else:
            return None, None
    if not_incident(title, cat):
        return None, None
    sev = BASE_SEVERITY[cat]
    if _ESC_RE.search(t):
        sev += 1
    deaths = [int(m.group(1)) for m in DEATH_RE.finditer(title)] + \
             [int(m.group(1)) for m in KILLS_RE.finditer(title)]
    if deaths:
        d = max(deaths)
        sev = max(sev, 4 if d >= 50 else 3 if d >= 10 else 2)
    return cat, min(sev, 4)


def is_economic(title):
    return bool(_ECO_RE.search(norm(title)))


# ------------------------------------------------------------------ géographie
class Gazetteer:
    def __init__(self, countries, log=print, min_pop=15000):
        self.countries = countries
        self.log = log
        self.by_country = {}       # iso2 → {nom normalisé: (nom, lat, lon, population, capitale?)}
        self.country_names = []    # (regex, iso2)
        self.ready = False
        self.min_pop = min_pop
        self.big = {}              # grandes villes (> 1 M hab.) : nom → (ville, iso2)
        self.big_ambiguous = set()
        self.nospace = {}          # iso2 → [(nom en thaï/chinois/birman…, entrée)] : recherche en sous-chaîne

    def load(self):
        if self.ready:
            return self
        path = GEONAMES_DIR / "cities15000.txt"
        if not path.exists():
            GEONAMES_DIR.mkdir(parents=True, exist_ok=True)
            self.log("  Téléchargement du dictionnaire de villes GeoNames (une seule fois, ~3 Mo)…")
            raw = http.get(GEONAMES_URL, timeout=120).content
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                path.write_bytes(z.read("cities15000.txt"))
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                f = line.rstrip("\n").split("\t")
                if len(f) < 15:
                    continue
                try:
                    pop = int(f[14] or 0)
                except ValueError:
                    pop = 0
                if pop < self.min_pop:
                    continue
                iso, lat, lon, code = f[8], float(f[4]), float(f[5]), f[7]
                entry = (f[1], lat, lon, pop, code == "PPLC")
                names = {f[1], f[2]} | {a for a in f[3].split(",") if a}
                d = self.by_country.setdefault(iso, {})
                for n in names:
                    k = norm(n)
                    if _NOSPACE.search(k):
                        if len(k) >= 2 and pop >= 50000:
                            self.nospace.setdefault(iso, []).append((k, entry))
                        continue
                    if len(k) < 4 or k.isdigit() or k in STOP_PLACES or len(k.split()) > 4:
                        continue
                    if len(k) <= 3 and pop < 50000:
                        continue
                    if k not in d or d[k][3] < pop:
                        d[k] = entry
                    if pop >= 1000000:
                        prev = self.big.get(k)
                        if prev and prev[1] != iso:
                            self.big_ambiguous.add(k)
                        elif not prev or prev[0][3] < pop:
                            self.big[k] = (entry, iso)
        self.big_entries = {k: v[0] for k, v in self.big.items() if k not in self.big_ambiguous}
        self.big_iso = {v[0][0]: v[1] for k, v in self.big.items() if k not in self.big_ambiguous}
        for item in self.countries.items:
            for n in {item["name_en"], item["name_fr"]}:
                if n and len(n) > 3:
                    self.country_names.append((re.compile(r"(?<!\w)" + re.escape(norm(n)) + r"(?!\w)"), item["iso2"]))
        for alias, iso in _extra_country_aliases().items():
            self.country_names.append((re.compile(r"(?<!\w)" + re.escape(alias) + r"(?!\w)"), iso))
        self.ready = True
        return self

    def find_country(self, title):
        t = norm(title)
        best = None
        for rx, iso in self.country_names:
            m = rx.search(t)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), iso)
        return best[1] if best else None

    def find_city(self, title, iso, allow_capital_bare=False, lang=""):
        """Ville du pays citée dans le titre (la plus peuplée si plusieurs)."""
        d = self.by_country.get(iso)
        if not d:
            return None
        hit = self._match(title, d, allow_capital_bare, lang in PREP_LANGS)
        if hit or not _NOSPACE.search(title):
            return hit
        t = norm(title)  # titres en thaï, chinois… : nom de ville cherché dans le texte (le plus long, puis le plus peuplé)
        found = [(len(k), e[3], e) for k, e in self.nospace.get(iso, []) if k in t]
        if not found:
            return None
        e = max(found)[2]
        return {"place": e[0], "lat": e[1], "lon": e[2], "capital": e[4]}

    def geocode(self, place, iso):
        """Coordonnées d'un lieu nommé (par l'IA) dans un pays donné."""
        d = self.by_country.get(iso) or {}
        hit = d.get(norm(place)) or next((v for k, v in d.items() if k.startswith(norm(place) + " ")), None)
        return {"place": hit[0], "lat": hit[1], "lon": hit[2]} if hit else None

    def _match(self, title, d, allow_capital_bare, prep_langs=False):
        t = norm(title)
        tokens = re.findall(r"[\w-]+", t)
        raw_tokens = re.findall(r"[\w-]+", title)
        hits = []
        for size in (3, 2, 1):
            for i in range(len(tokens) - size + 1):
                key = " ".join(tokens[i:i + size])
                if key in d:
                    first = raw_tokens[i] if i < len(raw_tokens) else ""
                    if first[:1].isalpha() and first[:1].islower() and first[:1].upper() != first[:1]:
                        continue  # mot commun en minuscules (« nice day »)
                    nxt = tokens[i + size] if i + size < len(tokens) else ""
                    prev = tokens[i - 1] if i > 0 else ""
                    hits.append((d[key], nxt, prev))
        if not hits:
            return None
        # Une capitale désigne souvent le gouvernement (« Paris met en garde Moscou ») :
        # on ne la retient que précédée d'une préposition de lieu, ou pour une catastrophe naturelle.
        places = [h for h, nxt, prev in hits
                  if (not h[4] or (nxt not in SPEECH_VERBS and (allow_capital_bare or prev in LOC_PREP)))
                  # petite ville (< 150 000 hab.) : souvent un nom de personne ou un homonyme → préposition exigée
                  and not (prep_langs and not h[4] and h[3] < 150000 and prev not in LOC_PREP)]
        if not places:
            return None
        non_capital = [p for p in places if not p[4]]
        best = max(non_capital or places, key=lambda p: p[3])
        return {"place": best[0], "lat": best[1], "lon": best[2], "capital": best[4]}

    def locate(self, title, country_hint=None, category=None, lang=""):
        """Renvoie {country, place, lat, lon, precision} ou {country} ou None."""
        natural = category in NATURAL
        iso = self.find_country(title) or country_hint
        if not iso:
            # pas de pays cité : on tente les grandes villes au nom sans ambiguïté
            city = self._match(title, self.big_entries, natural, lang in PREP_LANGS)
            if not city:
                return None
            iso = self.big_iso[city["place"]]
            return {"country": iso, "place": city["place"], "lat": city["lat"], "lon": city["lon"],
                    "precision": "city"}
        city = self.find_city(title, iso, natural, lang)
        if city:
            return {"country": iso, "place": city["place"], "lat": city["lat"], "lon": city["lon"],
                    "precision": "city"}
        return {"country": iso}


def _extra_country_aliases():
    return {"usa": "US", "etats-unis": "US", "uk": "GB", "royaume-uni": "GB",
            "britain": "GB", "rdc": "CD", "drc": "CD", "dr congo": "CD", "congo-kinshasa": "CD",
            "cote d'ivoire": "CI", "ivory coast": "CI", "burma": "MM", "birmanie": "MM", "gaza": "PS",
            "cisjordanie": "PS", "west bank": "PS", "turkiye": "TR", "russie": "RU", "ukraine": "UA",
            "centrafrique": "CF", "soudan du sud": "SS", "coree du nord": "KP", "north korea": "KP",
            "south korea": "KR", "coree du sud": "KR", "taiwan": "TW", "kosovo": "XK"}


_GAZ = {}


def gazetteer(countries, log=print):
    """Dictionnaire de villes partagé par la collecte (chargé une fois), ou None s'il est indisponible."""
    if "g" not in _GAZ:
        try:
            _GAZ["g"] = Gazetteer(countries, log).load()
        except Exception as exc:
            log(f"  Presse : dictionnaire de villes indisponible ({exc}) – pas de géolocalisation")
            _GAZ["g"] = None
    return _GAZ["g"]


def refine_regional(events, countries, log):
    """Incidents placés au niveau d'une région (GDELT, provinces) : si le titre de l'article cite une ville du pays,
    proche du point actuel (< 400 km), on la retient (précision « ville »)."""
    from .geo import haversine_km
    gaz = None
    moved = 0
    for ev in events:
        if ev.get("precision") not in ("region", "country") or not ev.get("country"):
            continue
        text = " ".join(x for x in (ev.get("headline"), ev.get("title") if ev.get("source") == "Press" else "") if x)
        if not text:
            continue
        gaz = gaz or gazetteer(countries, log)
        if not gaz:
            return 0
        city = gaz.find_city(text, ev["country"], False, ev.get("lang", ""))
        if city and (ev.get("lat") is None or haversine_km(ev["lat"], ev["lon"], city["lat"], city["lon"]) < 400):
            ev.update(lat=city["lat"], lon=city["lon"], place=city["place"], precision="city")
            moved += 1
    if moved:
        log(f"  Géolocalisation : {moved} incident(s) précisé(s) au niveau de la ville grâce au titre de l'article")
    return moved


# ------------------------------------------------------------------ géolocalisation complémentaire
def refine_location(loc, it, gaz, countries, log=None):
    """Titre sans ville reconnue : on cherche une ville dans le chapeau, puis une province (titre + chapeau)."""
    if loc and "lat" in loc:
        return loc
    iso = (loc or {}).get("country") or it.get("country_hint")
    if not iso:
        return loc
    snippet = it.get("snippet") or ""
    if gaz and snippet:
        city = gaz.find_city(snippet, iso, False, it.get("lang", ""))
        if city:
            return {"country": iso, "place": city["place"], "lat": city["lat"], "lon": city["lon"], "precision": "city"}
    from . import admin1
    reg = admin1.find(f"{it.get('title', '')} {snippet}", iso, countries, log)
    if reg:
        return dict(reg, country=iso)
    return loc


# ------------------------------------------------------------------ langue
_STOP = {
    "fr": " le la les des du une un et est dans pour sur avec par pas qui que aux au ont sont été après contre selon près "
          "morts mort blessés trois deux plusieurs lors cette ces ",
    "en": " the of and to a for on with is at by from after as are was has have over amid police say says said killed "
          "kill people dead injured near two three after ",
    "es": " el los las del y en un una por con para que se tras según contra muertos heridos dos tres ",
    "pt": " o os do da dos das e em um uma por com para que no na após contra mortos feridos dois três ",
    "de": " der die das und den von zu mit im nach bei auf ist ein eine für gegen tote verletzte zwei drei ",
    "it": " il lo gli di del della e un una per con che dopo contro nel morti feriti due tre ",
    "nl": " het een en van op met voor bij na tegen doden gewonden twee drie ",
    "tr": " ve bir bu ile için olarak sonra karşı ölü yaralı ",
    "id": " dan di yang ke dari untuk dengan pada ini itu tewas ",
    "pl": " i w na z do się nie że po dla przez ",
}
_STOPSETS = {k: set(v.split()) for k, v in _STOP.items()}
_CHAR_HINTS = {"fr": "éèêëçàùâîôœ", "es": "ñ¿¡áíóú", "pt": "ãõçáâêô", "de": "ßäöü", "tr": "ığşçöü", "pl": "ąęłńśźż"}


def guess_lang(text):
    """Langue probable d'un titre (écriture, puis mots-outils et accents) ; "" si incertain."""
    t = text or ""
    if re.search(r"[\u0590-\u05FF]", t):
        return "he"
    if re.search(r"[\u0600-\u06FF]", t):
        return "ur" if re.search(r"[ٹڈڑںےۓ]", t) else "fa" if re.search(r"[پچژگکی]", t) else "ar"
    if re.search(r"[\u0400-\u04FF]", t):
        return "uk" if re.search(r"[іїєґ]", t.lower()) else "ru"
    if re.search(r"[\u0E00-\u0E7F]", t):
        return "th"
    if re.search(r"[\u3040-\u30FF]", t):
        return "ja"
    if re.search(r"[\uAC00-\uD7AF]", t):
        return "ko"
    if re.search(r"[\u4E00-\u9FFF]", t):
        return "zh"
    if re.search(r"[\u1200-\u137F]", t):
        return "am"
    if re.search(r"[\u0980-\u09FF]", t):
        return "bn"
    if re.search(r"[\u0900-\u097F]", t):
        return "hi"
    low = t.lower()
    words = re.findall(r"[a-zà-ÿğışçöüñãõąęłńśźżœ]+", low)
    if len(words) < 3:
        return ""
    scores = {k: sum(2 if len(w) > 3 else 1 for w in words if w in st) for k, st in _STOPSETS.items()}
    for k, chars in _CHAR_HINTS.items():
        scores[k] += 2 * min(2, sum(1 for c in low if c in chars))
    best = max(scores, key=scores.get)
    ranked = sorted(scores.values(), reverse=True)
    return best if ranked[0] >= 2 and ranked[0] > ranked[1] else ""


def item_lang(it):
    """Langue d'un titre : celle du flux, corrigée quand l'écriture ou les mots-outils la contredisent."""
    declared = (it.get("lang") or "")[:2].lower()
    g = guess_lang(it.get("title", ""))
    if g and (not declared or (g != declared and (g in ("he", "ar", "fa", "ur", "ru", "uk", "th", "zh", "ja", "ko", "am", "bn", "hi")
                                                  or declared == "en"))):
        return g
    return declared or g


# ------------------------------------------------------------------ assemblage
def build(press_items, econ_items, countries, log, now, ai_results=None):
    """Transforme les titres collectés en : événements cartographiés, articles du Fil, veille économique."""
    import hashlib
    from .model import make_event, to_iso

    gaz = gazetteer(countries, log) if press_items else None

    seen, news, groups = set(), [], {}
    for it in press_items:
        key = norm(it["title"])[:120]
        if key in seen:
            continue
        seen.add(key)
        ai = (ai_results or {}).get(it["title"])
        loc, ctx = None, None
        if ai is not None:
            # l'IA a lu le titre : on suit son avis (pertinence, catégorie, lieu)
            if not ai.get("relevant"):
                continue
            cat, sev = ai.get("category"), int(ai.get("severity") or 1)
            # fait physique ? avis de l'IA ; à défaut (ancienne fiche en cache), règles par mots-clés
            if ai.get("physical") is False:
                ctx = "contexte (IA)"
            elif ai.get("physical") is None and cat:
                ctx = context(it["title"], cat)
            iso = ai.get("country") or it.get("country_hint")
            if iso:
                loc = {"country": iso}
                if gaz and ai.get("place"):
                    g = gaz.geocode(ai["place"], iso)
                    if g:
                        loc.update(g, precision="city")
        else:
            cat, sev = classify(it["title"])
            if not cat:
                continue
            ctx = context(it["title"], cat)   # arrestation, déclaration, analyse… : dans le Fil, pas sur la carte
            if gaz:
                loc = gaz.locate(it["title"], it.get("country_hint"), cat, it.get("lang", ""))
            elif it.get("country_hint"):
                loc = {"country": it["country_hint"]}
        it["lang"] = item_lang(it)
        loc = refine_location(loc, it, gaz, countries, log)
        uid = hashlib.sha1(key.encode()).hexdigest()[:12]
        if ai:  # titres traduits par l'IA (affichés dans la langue de la plateforme)
            it["_tfr"], it["_ten"] = ai.get("title_fr") or "", ai.get("title_en") or ""
        news.append({"id": f"press-{uid}", "source": it["outlet"], "title": it["title"], "url": it["url"],
                     **({"title_fr": it["_tfr"]} if it.get("_tfr") else {}), **({"title_en": it["_ten"]} if it.get("_ten") else {}),
                     "summary_en": (ai or {}).get("summary_en", ""),
                     "date": to_iso(it["date"]), "lang": it.get("lang", ""), "category": cat, "severity": sev,
                     "country": (loc or {}).get("country"), "place": (loc or {}).get("place", ""),
                     **({"context": ctx} if ctx else {})})
        if loc and "lat" in loc and not ctx:
            family = FAMILY.get(cat, cat)
            gkey = f"{loc['country']}-{norm(loc['place'])}-{family}-{it['date']:%Y%m%d}"
            g = groups.setdefault(gkey, {"loc": loc, "cat": cat, "sev": sev, "items": [], "outlets": set()})
            if PRIORITY.index(cat) < PRIORITY.index(g["cat"]):
                g["cat"] = cat
            g["sev"] = max(g["sev"], sev)
            g["items"].append(it)
            g["outlets"].add(it["outlet"])
            g["social"] = g.get("social") or bool(it.get("social"))
            if ai and ai.get("summary_en") and not g.get("summary"):
                g["summary"] = ai["summary_en"]
                g["summary_fr"] = ai.get("summary_fr") or ""
            if it.get("snippet") and not g.get("snippet"):
                g["snippet"] = it["snippet"]
            g["ai"] = g.get("ai") or ai is not None
            if ai and ai.get("physical") is True:
                g["physical"] = True   # l'IA a confirmé un fait physique (contrôle d'entrée, veille/triage.py)

    events = []
    for gkey, g in groups.items():
        items = sorted(g["items"], key=lambda x: x["date"])
        n = len(g["outlets"])
        conf = "high" if n >= 4 else "medium" if n >= 2 else "low"
        first, last = items[0], items[-1]
        uid = hashlib.sha1(gkey.encode()).hexdigest()[:14]
        ev = make_event(
            id=f"press-{uid}", source="Press", category=g["cat"], severity=g["sev"],
            title=first["title"], summary=g.get("summary") or f"Detected in local and international press ({n} outlet(s)). "
                                         f"Location and category inferred automatically from headlines.",
            date=to_iso(last["date"]), start=to_iso(first["date"]), lat=g["loc"]["lat"], lon=g["loc"]["lon"],
            url=first["url"], place=g["loc"]["place"], precision=g["loc"].get("precision", "city"), country=g["loc"]["country"],
            confidence="low" if g.get("social") and n < 2 else conf,
            tags=["auto-detected", "unverified", "press"] + (["ai"] if g.get("ai") else []) + (["social"] if g.get("social") else []))
        ev["sources"] = [{"name": x["outlet"], "url": x["url"], "title": x["title"], **({"site": x["site"]} if x.get("site") else {})}
                         for x in items[:8]]
        ev["headline"] = first["title"]
        if first.get("lang"):
            ev["lang"] = first["lang"][:2]
        for k, f in (("title_fr", "_tfr"), ("title_en", "_ten")):
            if first.get(f):
                ev[k] = first[f]
        if g.get("summary_fr"):
            ev["summary_fr"] = g["summary_fr"]
        if g.get("snippet"):
            ev["snippet"] = g["snippet"]
        if g.get("physical"):
            ev["physical"] = True
        events.append(ev)

    econ, eseen = [], set()
    for it in econ_items:
        key = norm(it["title"])[:120]
        if key in eseen:
            continue
        eseen.add(key)
        iso = it.get("country_hint")
        if gaz and not iso:
            iso = gaz.find_country(it["title"])
        if not iso:
            continue
        econ.append({"id": it["id"], "country": iso, "title": it["title"], "url": it["url"],
                     "source": it["outlet"], "date": to_iso(it["date"]), "lang": it.get("lang", "")})
    nctx = sum(1 for n in news if n.get("context"))
    log(f"  Presse : {len(news)} titres de sûreté ({nctx} de contexte, Fil seulement), {len(events)} placés sur la carte, "
        f"{len(econ)} titres économiques")
    return events, news, econ
