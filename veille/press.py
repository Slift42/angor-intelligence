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
               "нападение", "هجوم", "bomb", "bombs", "bombe", "bombing", "bomba", "explos", "blast", "gunm", "shooting", "fusillade", "tiroteo",
               "tiroteio", "sparatoria", "schießerei", "schiesserei", "strzelanin", "silahlı", "стрельб", "استهداف",
               "stabbing", "poignard", "kidnap", "enlèvement", "enleve", "secuestro", "sequestro", "rapimento",
               "entführ", "porwan", "kaçırıl", "похищ", "اختطاف", "hostage", "otage", "rehén", "refém", "ostaggi", "geisel",
               "assassin", "ied", "grenade", "arson", "incendie criminel"],
    "armed_conflict": ["airstrike", "air strike", "frappe", "bombard", "shelling", "artiller", "missile", "drone strike",
                       "drones", "clashes", "affrontement", "enfrentamiento", "confronto", "combat", "offensive",
                       "ofensiva", "gefecht", "kämpfe", "walki", "çatışma", "бой", "обстрел", "удар", "اشتباك",
                       "غارة", "قصف", "strikes kill", "strike kills", "strikes hit", "strikes on", "strike on", "frappes", "troops", "militants", "rebels", "rebelles", "rebeldes", "insurg", "ceasefire",
                       "cessez-le-feu", "alto el fuego", "invasion", "incursion", "militia", "milice", "milicia",
                       "war ", "guerre", "guerra", "krieg", "wojna", "savaş", "войн", "حرب"],
    "unrest": ["protest", "manifest", "demonstrat", "riot", "émeute", "emeute", "disturbio", "motim", "rivolta",
               "unruhen", "zamieszki", "ayaklanma", "бунт", "протест", "احتجاج", "مظاهر", "strike", "grève",
               "greve", "huelga", "sciopero", "streik", "staking", "strajk", "grev", "забастов", "إضراب",
               "blockade", "blocage", "bloqueo", "curfew", "couvre-feu", "toque de queda", "coprifuoco",
               "ausgangssperre", "tear gas", "gaz lacrymogène", "lacrimógeno", "unrest", "troubles", "looting", "pillage", "saqueo"],
    "political": ["coup", "golpe", "putsch", "darbe", "переворот", "انقلاب", "state of emergency", "état d'urgence",
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
    "earthquake": ["earthquake", "séisme", "seisme", "tremblement de terre", "sismo", "terremoto", "erdbeben",
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
                 "pożar lasu", "orman yangını", "лесной пожар", "حريق غابات", "incendie"],
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
# ordre de priorité quand plusieurs catégories correspondent
PRIORITY = ["terrorism", "armed_conflict", "attack", "earthquake", "cyclone", "flood", "volcano", "wildfire",
            "landslide", "health", "political", "unrest", "cyber", "infrastructure", "crime", "storm",
            "extreme_temp", "drought"]
# titres regroupés en un seul incident s'ils relèvent de la même famille, au même endroit, le même jour
FAMILY = {"terrorism": "violence", "attack": "violence", "armed_conflict": "violence", "crime": "violence",
          "unrest": "unrest", "political": "political"}
BASE_SEVERITY = {"terrorism": 3, "armed_conflict": 2, "attack": 2, "political": 1, "unrest": 1, "crime": 1,
                 "cyber": 1, "infrastructure": 1, "health": 2, "earthquake": 2, "cyclone": 2, "flood": 2,
                 "volcano": 2, "wildfire": 1, "landslide": 2, "storm": 1, "extreme_temp": 1, "drought": 1}
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

LOC_PREP = {"in", "at", "near", "outside", "around", "a", "au", "aux", "en", "pres", "dans", "vers", "en",
            "cerca", "de", "del", "em", "no", "na", "nel", "nella", "bei", "nahe", "im", "w", "we", "pod", "yakinlarinda",
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
    return pre + re.escape(p) + (r"(?!\w)" if len(p) <= 4 else "")


def _word_re(words):
    """Racines longues : début de mot (« manifest » → manifestation). Mots courts : mot entier
    (« coup » ne doit pas trouver « coupure »). Voir _alt pour les écritures non latines."""
    parts = sorted({norm(w).strip() for w in words if norm(w).strip()}, key=len, reverse=True)
    return re.compile("|".join(_alt(p) for p in parts), re.I)


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
               "biopic", "novel", "roman ", "podcast", "quiz"]
_NOISE_RE = _word_re(NOISE_WORDS)

# Pas un incident pour une organisation ou un voyageur : procédure judiciaire (mise en examen, procès,
# condamnation…), sauf si le titre signale une mobilisation en cours (manifestation, émeute, blocage).
JUDICIAL_WORDS = ["mis en examen", "mise en examen", "mis en cause", "proces", "condamne", "condamnation", "jugement", "juge ",
                  "juges", "tribunal", "cour d'assises", "assises", "garde a vue", "verdict", "requisitoire", "requis",
                  "peine de", "prison ferme", "detention provisoire", "inculpe", "comparution", "comparait", "audience",
                  "relaxe", "plainte", "enquete ouverte", "ouvre une enquete", "parquet", "sentenced", "sentence",
                  "trial", "convicted", "conviction", "charged with", "indicted", "pleads guilty", "pleaded", "jury",
                  "court hears", "in court", "appeal court", "juicio", "condenado", "condena", "sentencia", "imputado",
                  "processo", "condannato", "condenado", "julgamento", "prozess", "verurteilt", "angeklagt", "vonnis",
                  "wyrok", "sad skazal", "mahkum", "hapis cezasi", "приговор", "осужден", "суд ", "حكم", "محاكمة",
                  "משפט", "נגזר", "vonis", "sidang", "divonis", "判决", "判處", "審判", "دادگاه", "حکم"]
_JUDICIAL_RE = _word_re(JUDICIAL_WORDS)
_MOBILISATION_RE = _word_re(CATEGORY_WORDS["unrest"])
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
                 "suicide", "suicid", "se suicide", "overdose", "noyade", "drowned", "noye"]
_PRIVATE_RE = _word_re(PRIVATE_WORDS)
# Criminalité retenue seulement si elle relève de l'ordre public ou menace des entreprises et des voyageurs.
PUBLIC_CRIME_WORDS = ["cartel", "gang", "narco", "trafic", "traffick", "mafia", "reglement de comptes", "reglements de comptes",
                      "fusillade", "shooting", "tiroteo", "sparatoria", "braquage", "attaque a main armee", "armed robbery",
                      "robo a mano armada", "car-jacking", "carjacking", "home-jacking", "extorsion", "extortion", "racket",
                      "piraterie", "piracy", "pirates", "enlevement", "kidnap", "secuestro", "rapt", "rancon", "ransom",
                      "pillage", "looting", "saqueo", "bandit", "banditisme", "hold-up", "narcotrafico", "sicario",
                      "coupeurs de route", "embuscade", "ambush", "crime organise", "organized crime", "criminal group"]
_PUBLIC_CRIME_RE = _word_re(PUBLIC_CRIME_WORDS)


def not_incident(title, cat=None):
    """Titre qui ne décrit pas un incident pouvant toucher une organisation ou un voyageur (motif), sinon None."""
    t = norm(title)
    if _JUDICIAL_RE.search(t) and not _MOBILISATION_RE.search(t):
        return "judiciaire"
    if _PRIVATE_RE.search(t) and not _PUBLIC_CRIME_RE.search(t):
        return "fait divers"
    if cat == "crime" and not _PUBLIC_CRIME_RE.search(t):
        return "fait divers"
    return None


def classify(title):
    """Renvoie (catégorie, gravité) ou (None, None) si le titre ne relève pas de la sûreté."""
    t = norm(title)
    if _NOISE_RE.search(t):
        return None, None
    found = [c for c in PRIORITY if _CAT_RE[c].search(t)]
    if not found:
        return None, None
    cat = found[0]
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


# ------------------------------------------------------------------ assemblage
def build(press_items, econ_items, countries, log, now, ai_results=None):
    """Transforme les titres collectés en : événements cartographiés, articles du Fil, veille économique."""
    import hashlib
    from datetime import timedelta
    from .model import make_event, to_iso

    gaz = None
    if press_items:
        try:
            gaz = Gazetteer(countries, log).load()
        except Exception as exc:
            log(f"  Presse : dictionnaire de villes indisponible ({exc}) – pas de géolocalisation")

    seen, news, groups = set(), [], {}
    for it in press_items:
        key = norm(it["title"])[:120]
        if key in seen:
            continue
        seen.add(key)
        ai = (ai_results or {}).get(it["title"])
        loc = None
        if ai is not None:
            # l'IA a lu le titre : on suit son avis (pertinence, catégorie, lieu)
            if not ai.get("relevant"):
                continue
            cat, sev = ai.get("category"), int(ai.get("severity") or 1)
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
            if gaz:
                loc = gaz.locate(it["title"], it.get("country_hint"), cat, it.get("lang", ""))
            elif it.get("country_hint"):
                loc = {"country": it["country_hint"]}
        uid = hashlib.sha1(key.encode()).hexdigest()[:12]
        news.append({"id": f"press-{uid}", "source": it["outlet"], "title": it["title"], "url": it["url"],
                     "summary_en": (ai or {}).get("summary_en", ""),
                     "date": to_iso(it["date"]), "lang": it.get("lang", ""), "category": cat, "severity": sev,
                     "country": (loc or {}).get("country"), "place": (loc or {}).get("place", "")})
        if loc and "lat" in loc:
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
            url=first["url"], place=g["loc"]["place"], precision="city", country=g["loc"]["country"],
            confidence="low" if g.get("social") and n < 2 else conf,
            tags=["auto-detected", "unverified", "press"] + (["ai"] if g.get("ai") else []) + (["social"] if g.get("social") else []))
        ev["sources"] = [{"name": x["outlet"], "url": x["url"], "title": x["title"], **({"site": x["site"]} if x.get("site") else {})}
                         for x in items[:8]]
        ev["headline"] = first["title"]
        if g.get("summary_fr"):
            ev["summary_fr"] = g["summary_fr"]
        if g.get("snippet"):
            ev["snippet"] = g["snippet"]
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
    log(f"  Presse : {len(news)} titres de sûreté, {len(events)} placés sur la carte, {len(econ)} titres économiques")
    return events, news, econ
