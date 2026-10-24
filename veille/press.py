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
import json
import re
import unicodedata
import zipfile

from . import http, langs
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
               "assassin", "ied", "grenade", "arson", "incendie criminel", "взрыв", "вибух", "patlama", "pirates", "hijack", "hijacked", "hijacker"],
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
# 35 langues supplémentaires (v0.25) : japonais, coréen, vietnamien, hindi, langues nordiques, d'Europe centrale,
# des Balkans, du Caucase, swahili, haoussa… (veille/langs.py)
for _c, _ws in langs.category_words().items():
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

LOC_PREP = {"in", "at", "on", "over", "near", "outside", "around", "a", "au", "aux", "en", "pres", "dans", "vers", "cerca", "de", "del", "em", "no", "na", "nel", "nella", "bei", "nahe", "im", "w", "we", "pod", "yakinlarinda",
            "в", "под", "у", "في", "قرب"}
PREP_LANGS = {"en", "fr", "es", "pt", "it", "de", "nl", ""}
NATURAL = {"earthquake", "flood", "cyclone", "storm", "wildfire", "volcano", "landslide", "extreme_temp", "drought"}

STOP_PLACES = {"nice", "mobile", "split", "bath", "reading", "van", "bar", "mary", "victoria", "florence",
               "police", "union", "independence", "liberty", "hope", "mercedes", "concord", "george", "orange",
               "marina", "patience", "trinidad", "valencia", "cordoba", "santiago", "san jose", "la paz", "grand",
               "de", "la", "le", "el", "san", "santa", "centre", "center", "city", "nord", "sud", "north", "south",
               "east", "west", "new", "port", "ville", "gaza city",
               # v0.28 : « White House » est un nom alternatif de Casablanca dans GeoNames
               "white house", "maison blanche", "casa blanca", "casa bianca", "weisses haus",
               # v0.28 (run 2) : « la ville », « les martyrs », « colons » (persan), prénom Vladimir
               "المدينة", "مدينة", "مدن", "الشهداء", "شهداء", "شهرک", "владимир", "владимира"}


_APOS = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bb": "'", "\u02bc": "'", "`": "'", "\u00b4": "'"})


def norm(text):
    """Minuscules, sans accents ni signes diacritiques, apostrophes typographiques ramenées à « ' » (v0.25 : « coup d’État »
    comme « coup d'État », ouzbek « o‘g‘irlash »)."""
    text = unicodedata.normalize("NFKD", (text or "").translate(_APOS))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.lower()).strip()


# Écritures sans espace entre les mots (thaï, chinois, birman) ou à préfixes collés (éthiopien) :
# recherche en sous-chaîne. Hébreu et écriture arabe : préfixes courants autorisés (ה/ב/ו/ל…, و/ب/ال…).
_NOSPACE = re.compile(r"[\u0E00-\u0E7F\u3400-\u9FFF\uF900-\uFAFF\u1000-\u109F\u1200-\u139F\u3040-\u30FF\uAC00-\uD7AF\u1780-\u17FF]")
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
NOISE_WORDS += langs.words("noise")
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
JUDICIAL_WORDS += langs.words("judicial")
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
VIOLENCE_WORDS += langs.words("dead")
_VIOLENCE_RE = _word_re(VIOLENCE_WORDS)
_MASS_RE = _word_re(MASS_WORDS)
_PUBLIC_TARGET_RE = _word_re(PUBLIC_TARGET_WORDS)
ARMED_GROUP_WORDS += ["gängen", "gängkonflikt", "bandekonflikt", "'yan bindiga", "waasi", "magaidi", "banditi"]
_ARMED_GROUP_RE = _word_re(ARMED_GROUP_WORDS)
_AFTERMATH_RE = _word_re(AFTERMATH_WORDS)
_THREAT_RE = _word_re(THREAT_WORDS)
_EVAC_RE = _word_re(EVACUATION_WORDS)
_SECURITY_TARGET_RE = _word_re(SECURITY_TARGET_WORDS)
_SPECIFIC_RE = _word_re(SPECIFIC_ATTACK)
_NONLATIN = re.compile(r"[\u0590-\u06FF\u0750-\u077F\u0E00-\u0E7F\u0980-\u09FF\u1200-\u139F\u3400-\u9FFF"
                       r"\u0370-\u03FF\u0530-\u058F\u0900-\u097F\u0B80-\u0BFF\u10A0-\u10FF\u1000-\u109F\u1780-\u17FF"
                       r"\u3040-\u30FF\uAC00-\uD7AF]")   # + grec, arménien, dévanagari, tamoul, géorgien, birman, khmer, kana, hangul
_TOLL2_RE = re.compile(r"(?:toll|bilan|saldo|balance)\D{0,25}?(\d{1,4})", re.I)
_NUM_WORDS = {"två": 2, "fyra": 4, "fem": 5, "két": 2, "három": 3, "négy": 4, "dva": 2, "dvije": 2,
              "tri": 3, "doi": 2, "două": 2, "trei": 3, "patru": 4, "cinci": 5, "δύο": 2, "τρεις": 3, "τέσσερις": 4,
              "два": 2, "двое": 2, "три": 3, "трое": 3, "четыре": 4, "пять": 5, "пятеро": 5, "десять": 10,
              "one": 1, "un": 1, "una": 1, "uno": 1, "une": 1, "um": 1, "uma": 1, "two": 2, "deux": 2, "dos": 2, "duas": 2, "dois": 2, "due": 2, "zwei": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "dozen": 12,
              "dozens": 24, "trois": 3, "quatre": 4, "cinq": 5, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
              "dizaine": 10, "dizaines": 20, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
              "nueve": 9, "diez": 10, "decena": 10, "decenas": 20, "quatro": 4, "sete": 7, "oito": 8, "dez": 10,
              "tre": 3, "quattro": 4, "cinque": 5, "drei": 3, "vier": 4, "funf": 5, "sechs": 6, "zehn": 10}
_NUM_NORM = {norm(k): v for k, v in _NUM_WORDS.items()}
# morts et blessés des langues ajoutées en v0.25 (« 5 dræbte », « 3 morți », « 10 halott »…), écritures alphabétiques
_RU_DEAD = ["погибли", "погибло", "погибших", "погиб", "убиты", "убитых", "ранены", "раненых", "пострадали", "пострадавших",
            "загинули", "загиблих", "поранені", "поранених", "постраждали"]
_LANG_DEAD = "|".join(sorted({re.escape(norm(w)) for w in langs.words("dead") + _RU_DEAD if not _NONLATIN.search(w)},
                             key=len, reverse=True))
_TOLL_RE = re.compile(r"(?<!\w)(\d{1,4}|" + "|".join(norm(w) for w in _NUM_WORDS) + r")(?!\w)"
                      r"(?!\s*-?\s*(?:year|yr|ans?\b|anos|ano\b|jahr|yas|month|mois|meses))(?:\W+\w+){0,3}?\W+"
                      r"(?:dead|killed|die|morts?|tues?|blesses?|muertos?|muertas?|muertes|fallecid[oa]s?|heridos?|heridas?|lesionad[oa]s?|mortos?|feridos?|"
                      r"morti|feriti|tote|verletzte|olu|yarali|people|personnes|personas|pessoas|persone|menschen|"
                      r"victims?|victimes?|victimas?|injured|wounded|casualties|" + _LANG_DEAD + ")", re.I)


_DEAD_TOLL_RE = re.compile(r"(?<!\w)(\d{1,4}|" + "|".join(norm(w) for w in _NUM_WORDS) + r")(?!\w)"
                           r"(?!\s*-?\s*(?:year|yr|ans?\b|anos|ano\b|jahr|yas|month|mois|meses))(?:\W+\w+){0,3}?\W+"
                           r"(?:dead|killed|die[ds]?|morts?|tues?|muertos?|muertas?|muertes|mueren|murieron|fallecid[oa]s|asesinad[oa]s|mortos?|morrem|"
                           r"morti|tote|olu|fallecidos|" + _LANG_DEAD + ")", re.I)


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
        n = int(v) if v.isdigit() else _NUM_NORM.get(v, 0)
        if 1900 <= n <= 2100:  # une année, pas un bilan
            continue
        best = max(best, n)
    if not dead_only:   # « un muerto y dos heridos » : morts et blessés s'additionnent
        best = max(best, sum(_NUM_NORM.get(m.group(1), 0) if not m.group(1).isdigit() else
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
_MAG_RE = re.compile(r"(\d[.,]\d)\s*(?:m|sr|richter|ριχτερ|рихтер|balla|балла|баллов|bal)(?!\w)|(?:magnitud[eo]?|magnitudo|mag\.?|m|mw|ml|magnitude|sismo|seisme|earthquake|quake|terremoto|temblor|deprem)\s*(?:de\s*|of\s*|:\s*)?(\d(?:[.,]\d)?)(?!\d)"
                     r"|(\d(?:[.,]\d)?)\s*(?:de\s+|-)?(?:magnitud[eo]?|magnitude|buyuklugunde|درجات|richter|sr\b)", re.I)
QUAKE_IMPACT = ["dead", "killed", "died", "mort", "morts", "muerto", "muertos", "mortos", "olu", "injur", "blesse",
                "herido", "ferido", "yarali", "damage", "degats", "danos", "hasar", "collapse", "effondr", "derrumb",
                "desab", "tsunami", "victim", "victime", "evacu", "destroy", "detruit", "destruy", "houses", "maisons",
                "viviendas", "casas", "jolts", "strong", "powerful", "violent", "puissant", "fuerte", "forte", "guclu",
                "siddetli", "injuries"]
QUAKE_IMPACT += langs.words("dead") + ["震度", "津波", "被害", "cunami", "tsunami"]
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
    why = audit_noise(t, cat)
    if why:
        return why
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
ARREST_WORDS += langs.words("arrest")
_ARREST_RE = _word_re(ARREST_WORDS)
FRESH_WORDS = ["killed", "kills", "kill", "dead", "dies", "died", "wounded", "injured", "injures", "tue", "tues", "tuee",
               "tuees", "morts", "mort", "blesse", "blesses", "blessee", "muere", "murio", "mueren", "muertos", "muerto",
               "heridos", "herido", "asesinad", "mortos", "morto", "feridos", "ferito", "feriti", "morti", "tote",
               "verletzt", "verletzte", "olu", "yarali", "tewas", "luka"]
FRESH_WORDS += langs.words("dead")
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
    why = audit_context(t, cat)
    if why:
        return why
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


# ------------------------------------------------------------------ v0.28 : audit de la production (octobre 2026)
# 178 événements réels de la carte relus un par un : 34 n'étaient pas des incidents. Chaque motif ci-dessous vient d'un
# cas réel (tests/gold_tri.csv, commentaire « prod 2026-10 »).
FORECAST_WORDS = ["may intensify", "likely to intensify", "could intensify", "expected to intensify", "set to intensify",
                  "may hit", "could hit", "likely to hit", "set to hit", "expected to hit", "to make landfall", "forecast",
                  "prevision", "previsions", "pronostico", "pronostica", "rains expected", "rain expected",
                  "heavy rain expected", "se esperan lluvias", "lluvias esperadas", "pluies attendues", "warns of possible",
                  "met warns", "met office warns", "met department warns", "weather office warns", "warns of flash",
                  "warns of heavy", "potensi", "berpotensi", "prakiraan", "waspada banjir", "imbau warga", "disiagakan",
                  "antisipasi", "risiko", "petakan", "pemetaan", "mitigasi", "kategori menengah", "pourrait toucher",
                  "risque de crues", "alerta por posibles", "posibles inundaciones", "podria afectar", "risk map",
                  "เตือนภัย", "เฝ้าระวัง", "预警", "预报", "पूर्वानुमान", "चेतावनी", "پیش‌بینی", "توقعات"]
_FORECAST_RE = _word_re(FORECAST_WORDS)
_IMPACT_RE = _word_re(["shuts", "shut down", "closed", "closes", "closure", "cancel", "cancels", "cancelled", "canceled",
                       "suspend", "suspended", "suspends", "stranded", "ferme", "fermees", "annule", "annules", "cerrad",
                       "suspendid", "evacu", "evakuasi", "damage", "damaged", "destroy", "missing", "swept", "rendam",
                       "terendam", "tewas", "hilang", "inundated", "inondee", "inondees", "submerg", "cut off", "isoles"])
AFTERCARE_WORDS = ["teste son dispositif", "dispositif contre", "avant les pluies", "avant l'hiver", "renforce les controles",
                   "controles sanitaires", "controle sanitaire", "screening", "depistage", "tangani dampak", "kembali terlayani",
                   "kembali normal", "green policing", "lingkungan bersih", "wujudkan", "indemnisation", "indemnisations",
                   "compensation claims", "เยียวยา", "carencias", "dejan al descubierto", "saneamiento", "leave quarantine",
                   "leaves quarantine", "quitte la quarantaine", "sale de cuarentena", "released from quarantine",
                   "controverse", "controversy", "polemique", "polemica", "memories", "souvenirs", "recuerdos",
                   "brings memories", "survivors recall", "lives they lost"]
_AFTERCARE_RE = _word_re(AFTERCARE_WORDS)
_CEASEFIRE_RE = _word_re(["ceasefire", "cease-fire", "cessez-le-feu", "cese al fuego", "alto el fuego", "tregua", "truce",
                          "treve", "waffenruhe", "waffenstillstand", "перемир", "припинення вогню", "هدنة", "وقف إطلاق النار",
                          "آتش‌بس", "停火", "休战"])
_VIOLATION_RE = _word_re(["violat", "breach", "violation", "viole", "violent", "rompe", "rupture", "despite ceasefire",
                          "malgre le cessez-le-feu", "pese a la tregua", "collapse", "collapses", "s'effondre"])
_WARNS_AGAINST_RE = re.compile(r"\bwarns?\b(?:\s+\S+){0,3}\s+against\b|\bwarns? of\b|\bmet(?:tent)? en garde\b|"
                               r"\bmise en garde\b|\badviert\w*\b|\bwarnt\b|\bpreviene contra\b")
SUMMON_WORDS = ["summon", "summons", "summoned", "convoque", "convoquee", "convoques", "citado a declarar", "citada a declarar",
                "interroge", "interrogee", "questioned", "questioning", "detenu", "detenue", "detenus", "detenues",
                "incarcere", "incarceree", "emprisonne", "emprisonnee", "encarcelad", "envian a la carcel", "a la carcel",
                "procesados", "procesado", "declarados culpables", "declarado culpable", "declarada culpable",
                "declaradas culpables", "found guilty", "reconnu coupable", "reconnus coupables", "dihukum",
                "रिपोर्ट दर्ज", "मुकदमा दर्ज", "केस दर्ज", "गिरफ्तार", "گرفتار"]
_SUMMON_RE = _word_re(SUMMON_WORDS)
_TESTIMONY_RE = _word_re(["temoignage", "testimony", "testimonio", "portrait", "reportage", "report on", "reports on",
                          "on the daily", "op-ed", "column", "chronique"])
_STATEMENT_RE = _word_re(["basta ya", "se repite", "tras el ultimo", "after the latest", "apres la derniere",
                          "apres le dernier", "secured ceasefire",
                          "تنفي", "ينفي", "نفى", "نفت", "تدين", "يدين", "می‌گوید", "میگوید", "اعلام کرد"])
_MISSILE_TEST_RE = _word_re(["likely a test", "missile test", "test launch", "test-fire", "test fire", "test-fired",
                             "test fired", "essai de missile", "tir d'essai", "prueba de misil", "ensayo de misil"])
_AFTER_RIOTS_RE = re.compile(r"^(?:\w+\W+){0,2}(?:apres|after|tras|despues de|nach)\s+(?:les |the |los |las |la |den |der )?"
                             r"(?:emeutes|riots|disturbios|violences|unruhen|manifestations|protests|affrontements)")
_LOGISTICS_RE = re.compile(r"operations? d'enlevement|enlevement (?:des |de )?(?:conteneurs|marchandises|colis|ordures|"
                           r"dechets|vehicules|epaves|bagages|encombrants|cargaisons)")
_SEWAGE_RE = _word_re(["raw sewage", "eaux usees", "aguas residuales", "aguas negras", "sewage spill", "egouts debordent"])
_POLICE_INVOLVED_RE = re.compile(r"officer-involved|police-involved|involucrad\w* (?:\w+ )?polic|"
                                 r"policiers? implique|policias? involucrad")
_MANHUNT_RE = re.compile(r"\bmanhunt (?:launched |under way |underway )?for\b|\bwanted for\b|\bavis de recherche\b|"
                         r"\bse busca a\b|\bchasse a l'homme (?:pour|contre)\b")
_ALLEGED_RE = _word_re(["alleged", "allegedly", "accused", "presume", "presumed", "presunto", "presunta", "suspected of"])
_LOCAL_DESK_RE = re.compile(r"^[\w .'-]{2,30}\s(?:news|samachar|समाचार)\s*[:|]", re.I)
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_SOUTH_ASIA_CRIME_RE = _word_re(["मुठभेड़", "बदमाश", "आरोपी", "चोर", "लूट", "ڈاکو", "ملزم", "مقابلے", "پولیس مقابلہ"])
CYBER_HINTS = ["mot de passe", "mots de passe", "password", "passwords", "piratage", "pirates informatiques", "rancongiciel",
               "ransomware", "data breach", "fuite de donnees", "ddos", "phishing", "hameconnage", "malware",
               "cyberattaque", "cyberattack", "hackers", "hacked"]
_CYBER_HINT_RE = _word_re(CYBER_HINTS)
_PROTEST_RE = _word_re(["protest", "protests", "protesters", "manifest", "manifestation", "manifestants", "protesta",
                        "manifestantes", "demonstration", "demonstrators", "प्रदर्शन", "आंसू गैस", "tear gas", "teargas",
                        "gaz lacrymogene", "gases lacrimogenos", "احتجاج", "تظاهرات"])
_CIVIL_UNREST_RE = _word_re(["blocus", "blocage", "blocages", "lycees", "lyceens", "etudiants", "students", "estudiantes",
                             "mobilisation", "manifest", "protest", "protesta", "gaz lacrymogene", "tear gas", "teargas",
                             "huelga", "greve", "strike action", "saqueos", "pillages", "looting"])
_MILITARY_RE = _word_re(["army", "troops", "soldiers", "military", "militants", "rebels", "insurgents", "jihadist",
                         "airstrike", "air strike", "drone", "missile", "artillery", "shelling", "armee", "soldats",
                         "rebelles", "ejercito", "militares", "guerrilla", "disidencias", "सेना", "उग्रवादी", "आतंकी"])


# ------------------------------------------------------------------ v0.28, run 2 : second audit (931 titres du 23 octobre)
# 277 faux positifs sur 931 titres de presse de la carte : suites d'un fait (hommages, témoignages, procès, enquête),
# prévention et préparation (crues, épidémies), menaces et projets de frappe, sujets militaires sans incident,
# métaphores (« protesters flood Belgrade »), faits divers locaux, interventions de police, sport. Cas réels :
# tests/gold_tri.csv, commentaire « prod 2026-10-23 ».
THREAT_WORDS = ["pourraient frapper", "pourrait frapper", "prevoient de nouvelles frappes", "prevoit de frapper",
                "planning new strikes", "plan new strikes", "plans new strikes", "planning strikes", "could strike",
                "may strike", "might strike", "threatens", "threatened", "threat to", "menace de", "menacent de",
                "amenaza con", "amenazan con", "droht", "drohen", "vows to", "vow to", "will treat", "legitimate targets",
                "won't be the last", "will not be the last", "nicht der letzte", "ne sera pas la derniere",
                "fears offensive", "fears an offensive", "fears israeli", "fears attack", "craint une offensive",
                "teme una ofensiva", "warned germany", "warned that", "يتوعد", "يتوعّد", "توعد", "هشدار داد", "هشدار",
                "تهدد", "يهدد", "loi anti-emeutes", "anti-riot laws", "approves tougher", "toughens security laws"]
_THREAT_RE = _word_re(THREAT_WORDS)
STATEMENT2_WORDS = ["blames", "blamed", "'no change'", "no change in", "zelensky says", "putin says", "defends", "defend",
                    "appeal for calm", "appeals for calm", "appelle la population", "appelle au calme", "ecrit au",
                    "writes to", "urges", "insta a", "presses", "heads to", "ready to help", "pret a aider",
                    "expresses sympathy", "تعرب عن", "يعرب عن", "يطمئن", "يوجه نداء", "نداء", "has no link", "no link with",
                    "explains why", "explique pourquoi", "summarizes", "summarises", "resume l'operation",
                    "safe and stable", "آمنة ومستقرة", "s'insurgent", "favorable a", "je suis favorable", "favorable al",
                    "deplore", "denuncia el trabajo", "asks minister", "pide al ministro",
                    "commemor", "conmemor", "rinde homenaje", "recompensa", "ofrece recompensa", "reward",
                    "sympathy", "solidarity", "solidarite", "solidaridad", "satisfait", "satisfecho", "pedem que", "pede que",
                    "piden que", "pide que", "falam em", "hablan de", "parlent de", "البيت الأبيض", "البيت الابيض", "وزير الخارجية", "وزیر خارجه", "foreign minister",
                    "ministre des affaires etrangeres", "canciller", "谴责", "批评", "declares", "declare le", "declara la"]
_STATEMENT2_RE = _word_re(STATEMENT2_WORDS)
FOLLOWUP_WORDS = ["remembered", "remember", "victims include", "laid to rest", "awaits answers", "await answers",
                  "recounts", "recount", "survivor battles", "birthday gift", "suspect id'd", "id'd", "ids suspect",
                  "checking in on", "security after the", "dan de alta", "dado de alta", "rescued alive", "resume search",
                  "resumes search", "resumes operation", "resume operation", "agradece", "thanks officer", "sobreseyeron",
                  "sobresee", "dictan presidio", "presidio perpetuo", "life term", "double life", "iddianame",
                  "adliyeye sevk", "осудили", "осужден", "завели дело", "возбудили дело", "geklart", "aufgeklart",
                  "procesan", "procesa a", "case registered", "report au", "renvoye au", "relieved amid",
                  "flood control probe", "arastirma onergesi", "mystery", "معمہ", "still unsolved", "victim battles",
                  "battles impaired", "laid to", "un mes despues", "one month after",
                  "dit avoir ete frappe", "resigns after", "cleared by", "tested negative", "teste negatif",
                  "testado negativo", "negativo para", "dio negativo", "secuestro virtual", "virtual kidnapping",
                  "most wanted", "playing dead", "pretending to be dead", "juzgar a", "propone juzgar", "capturamos", "on ramasse",
                  "police reagit", "promisiuni", "dupa protest", "死因", "身元", "rassurer", "reassure", "tranquilizar",
                  "descarta", "rules out", "ruled out", "ecarte la piste", "exclut la piste", "s'est senti",
                  "se sont sentis", "announce safety", "safety changes", "safety measures", "to prevent attacks",
                  "prevent attacks", "seek residents"]
_FOLLOWUP_RE = _word_re(FOLLOWUP_WORDS)
# suites probables, sauf si le titre décrit aussi le fait lui-même (morts, feu, heurts)
FOLLOWUP_SOFT_WORDS = ["survivor", "survivors", "survived", "reabre", "reopens", "on ramasse", "au lendemain",
                       "suite a l'emeute", "apres les emeutes", "apres l'emeute", "apres les affrontements",
                       "apres les violences", "ne veulent pas revivre", "ne veulent pas que les affrontements",
                       "ne veulent pas que", "troops rescue", "rescue kidnapped", "rescued kidnapped", "rescue victim",
                       "rescues victim", "funeral", "mourn", "mourns",
                       "funerailles", "velorio", "sepelio", "entierro", "despiden", "pleure", "lloran", "says he was",
                       "dit avoir ete", "blanchi"]
_FOLLOWUP_SOFT_RE = _word_re(FOLLOWUP_SOFT_WORDS)
# arrestations : en tête de titre seulement (« Capturamos a un sujeto… », pas « …, la police a interpellé 3 personnes »)
_ARREST_LEAD_RE = _word_re(["capturamos", "capturadas", "capturados", "capturan", "hideout busted", "police dock", "docked",
                            "detain", "detains", "detained", "يعتقل", "اعتقال", "συλληψεις", "ταυτοποιηθηκαν"])
_PHYSICAL2_RE = _word_re(["affrontements", "clashes", "enfrentamientos", "emeutes", "riots", "pillages", "incendi", "ravage",
                          "fire", "fires", "explos", "blast", "shooting", "fusillade", "tiroteo", "disparos", "barricades",
                          "feu", "brule", "brulent", "combats", "fighting", "combates", "kampfe"])
ANALYSIS2_WORDS = ["what sparked", "what that means", "what it means", "how they could", "struggles to contain",
                   "fallout from", "likened to", "quelles differences", "interactive map", "carte interactive",
                   "volunteer summary", "war update", "что происходит", "comment la manifestation", "a degenere",
                   "a bascule", "swept across", "increasingly targeting",
                   "acled", "cocktail", "analysts say", "unlikely to have", "reabren la herida", "reopens the wound",
                   "ravive", "la ruta oscura", "ruta oscura", "inside chicago's battle", "battle against",
                   "lutte contre", "bras de fer", "interminable", "the story", "l'histoire", "la historia", "uzman",
                   "olacak mi", "expert", "experts", "archives du", "archives", "il y a", "years on", "ans apres",
                   "anos despues", "rebellion rocks", "rocks france", "refuses to yield", "refuse de ceder",
                   "explainer", "faq", "everything we know", "font craindre", "fait craindre", "hinungdan", "tout savoir", "lo que sabemos", "testimonio",
                   "racontent", "raconte", "relatan", "relata", "residents recount",
                   "leur ville cramer", "ciudad del miedo", "pourquoi", "why ", "warum", "por que", "por qué"]
_ANALYSIS2_RE = _word_re(ANALYSIS2_WORDS)
MILITARY_NEWS_WORDS = ["kjoper", "kjop", "kauft", "acquires", "buys", "to buy", "achete", "compra de", "adquiere",
                       "over-the-horizon radar", "building a radar", "radar", "unexploded", "non explose", "sin explotar",
                       "defense minister", "defence minister", "ministre de la defense", "ministro de defensa",
                       "new defense", "nuevo ministro", "armored vehicles", "vehicules blindes", "بکتر بند", "scrambles",
                       "scrambled", "decolle", "fait decoller", "exercise", "exercice militaire", "drill", "תרגיל",
                       "military parade", "compensation", "indemnisation", "war crimes victims",
                       "1,100 militants killed in past year", "rs14bn", "spent to counter", "counterterrorism record",
                       "record antiterroriste", "named vivaldi", "offensive was named", "ballistic missile movement",
                       "movement recorded", "tunnel", "postpones", "aplaza", "davos", "commander explains"]
MILITARY_NEWS_WORDS += ["kjøper", "kjøp"]
_MILITARY_NEWS_RE = _word_re(MILITARY_NEWS_WORDS)
# résumés et bulletins : jamais un fait daté et localisé
_ANALYSIS_STRICT_RE = _word_re(["comment la manifestation", "a degenere", "a bascule", "swept across", "quelles differences",
                                "pourquoi", "what sparked", "what that means", "what it means", "je suis favorable",
                                "favorable a l'etat", "ready to help", "pret a aider", "how they could"])
_DIGEST_RE = _word_re(["volunteer summary", "war update", "interactive map", "carte interactive", "daily brief", "что происходит",
                       "lo que sabemos", "ce que l'on sait"])
_GENRE_RE = re.compile(r"^\W*(?:temoignage|portrait|entretien|interview|opinion|opinie|opinion|op-ed|tribune|edito|"
                       r"editorial|chronique|columna|analisis|analyse|decryptage|explainer)\b")
_QUOTE_SAYS_RE = re.compile(r"""^\W*(?:[\w .-]{2,20}:\s*)?['"‘“«].{3,80}['"’”»]\s*,?\s*(?:says|said|dit|affirme|dice|afirma)\b|,\s*(?:[\w'’.-]+\s){0,4}says$""")
_CULTURE_RE = _word_re(["lleva a la pantalla", "pelicula", "documental", "documentary", "film sur", "movie", "libro sobre",
                        "book on", "novela", "exposicion", "exhibition", "narcocorrid", "artistas senalados", "concierto"])
_SEIZURE2_RE = re.compile(r"seiz\w* \d[\d,.]* ?(?:kilograms|kilos|kg|tonnes|tons)|saisie de \d|decomis\w* \d|incaut\w* \d")
_FAMILY_RE = re.compile(r"\b(?:dispute|querelle|rina|pelea|disputa) (?:entre|familiale|conjugale|de pareja)|entre (?:deux )?freres|"
                        r"\bson (?:frere|cadet|aine|epouse)\b|\bsa (?:femme|compagne|mere|fille)\b")
_BR_CONFRONTO_RE = re.compile(r"\bconfronto\b")
_BR_POLICE_RE = re.compile(r"\b(?:pm|policia\w*|policiais|suspeito|investigado|bandido)s?\b")
_TERROR_METAPHOR_RE = _word_re(["terrorises", "terrorisees", "terrorise", "terrorised", "terrorized", "terror psicologico",
                                "terreur psychologique", "psychological terror"])
_PLAN_PROTEST_RE = re.compile(r"\bplans? (?:\w+ ){0,3}protest|\bappellent a manifester|\bconvocan (?:una )?marcha")
PREPARE_WORDS = ["recomendaciones", "prevencion de", "fondos", "invertira", "invierte", "inversion", "se prepara",
                 "se preparan", "preparativos", "preparacion", "advierte", "advierten", "riesgo de", "eleva riesgo",
                 "zonas expuestas", "zonas mas expuestas", "protocolo", "instala barreras", "laboratorio de innovacion",
                 "necesita", "millones para", "red de pluviales", "refuerza la proteccion", "despliegue de motobombas",
                 "motobombas", "activan plan", "apoyar a habitantes", "exhortan", "piden declarar", "declarar en emergencia",
                 "mision a europa", "no se reportan", "fallos judiciales", "vigilancia por", "sel riskine",
                 "kalici cozum", "toplanti", "sel destegi", "milyon lira", "altyapi", "cozum", "rustet", "rustet sich",
                 "erwartet", "lutte contre les inondations", "dispositif de recasement", "booste sa capacite",
                 "annonce le renforcement", "renforcement du", "gare aux", "prepa", "braces for heavy", "braces for rain",
                 "braces for flood", "prepares for", "se prepare", "resilience", "inaugur", "resmikan", "perkuat",
                 "koordinasi", "survei", "upaya atasi", "bahas banjir", "imbau masyarakat", "terjun ke titik", "risks along",
                 "loss raises", "threatens to shut", "asks minister", "to face floods", "se gesta", "storm will",
                 "flood guard", "flood rakshak", "फ्लड रक्षक", "राशन किट", "राहत सामग्री", "बजट", "सीएम", "निपटने", "तैयारी", "मुआवजा", "डूबी फसलों", "करोड़ों",
                 "vaccin", "vaccine", "vaccination", "vacunacion", "vacuna", "essai clinique", "clinical trial",
                 "preventive measures", "mesures preventives", "medidas preventivas", "surveillance", "deploys nurses",
                 "hotlines", "hotline", "preparedness", "supplies", "training", "health promot", "refuerza controles",
                 "controles contra", "urge virtual", "campaign", "campagne", "campana de", "fermeture", "prevoit de fermer",
                 "fermer le", "simulado", "simulacro", "sekolah lapang", "protesis", "tras el terremoto", "家屋被害",
                 "intensifican la entrega", "emergency operations centre", "operations center", "activates emergency",
                 "intervenidas", "plan marina", "donne", "tang ", "xuong cuu ho", "relieved", "probe", "inquiry",
                 "meclis", "budget", "งบ", "ฟื้นฟู", "เยียวยา", "ลงทะเบียน", "รับเงิน", "ปิดศูนย์", "เตรียมแผน",
                 "estas son las alertas", "solution", "soluciones", "permanent", "kalici", "mangrove", "dumping waste", "shut sites", "nuevo sistema",
                 "novy system", "pripravu", "secondary disaster", "二次災害", "reopen", "community support",
                 "farms destroy", "insurance", "seguro", "aid falls short", "winter aid", "without safe shelter",
                 "aprovecha", "cash in", "windfall"]
_PREPARE_RE = _word_re(PREPARE_WORDS)
_NAT_IMPACT2_RE = _word_re(["holiday", "conge", "feriado", "evacuated", "evacues", "evacuados", "tombee", "collapsed",
                            "effondre", "derrumbe", "missing", "disparus", "desaparecidos"])
# exercices et prévention : même avec « blessés » dans le texte (« séisme simulé : blessés, routes coupées »)
_PREPARE_STRICT_RE = _word_re(["simulado", "simulacro", "sismo simulado", "drill", "sekolah lapang", "vaccin", "vacuna",
                               "essai clinique", "clinical trial", "recomendaciones", "invertira", "fondos", "kalici cozum",
                               "toplanti", "resmikan", "inaugur", "preparedness", "protesis"])
_FLOOD_METAPHOR_RE = re.compile(r"\b(?:posters|banners|visitors|tourists|fans|crowds|thousands|hundreds|students|protesters|"
                                r"demonstrators|migrants|drugs|orders|calls|messages|tributes|complaints|wave|applications|"
                                r"people|supporters|shoppers)\b(?:\W+(?!amid|after|from|by|in|as|due)[\w']+)?\W+flood(?:s|ed|ing)?\b"
                                r"(?! victims| waters| warning| alert)|"
                                r"\bflooding (?:the )?(?:us|u\.s\.|market|streets|country|internet)\b|"
                                r"\bflood (?:\w+ )?(?:streets|music|award)")
_PROTESTERS_RE = _word_re(["protesters", "demonstrators", "students", "protest", "rally", "march", "manifestants"])
_WEAK_QUAKE_JA_RE = re.compile(r"最大震度[：:]?\s*[1-3](?![0-9])|震度[1-3]の地震")
_JA_NOISE_RE = re.compile(r"破産|負債|使用しないで|販売の恐れ|混入")
_SPORT2_RE = _word_re(["الزمالك", "الأهلي", "بيراميدز", "سيراميكا", "بتروجت", "الدوري", "مباراة", "المنتخب", "يقودان هجوم",
                       "homenaje a messi", "golazo", "goleador", "delantero", "el 10 de", "judo", "जूडो", "खिलाड़ी"])
_ANIMAL_RE = _word_re(["stray dogs", "dog attack", "dog bites", "mordeduras", "perros", "chiens", "कुत्तों", "कुत्ते",
                       "मधुमक्खि", "bees", "abejas", "elephant", "elefante", "poultry", "volailles", "newcastle disease",
                       "fusarium", "meteorit", "meteorite", "caruta", "carut"])
_POLICE_CLASH_RE = re.compile(r"(?:morre|morreu|morrem|mortos?|baleado|ferido)\w* (?:\w+ ){0,3}(?:apos |em )?confronto com "
                              r"(?:a |os |as )?(?:pm|policia|policiais|guardas|brigada)|confronto com (?:a |os )?(?:pm\b|policia)|"
                              r"(?:murio|muere|mueren|murieron|abatido|abatidos) en (?:un )?enfrentamiento con (?:la )?(?:policia|"
                              r"guardia|agentes)|fatal shooting of (?:\w+ )?(?:alleged|suspected)|"
                              r"shooting involving (?:at least )?(?:\w+ ){0,3}(?:deputy|deputies|officer|officers|trooper)|"
                              r"\bindecom\b|enfrentamiento entre policias e|tiroteo con (?:la )?policia")
_VERBAL_CLASH_RE = re.compile(r"\bclash(?:es|ed)? with (?:the )?(?:lawyer|secretary|minister|governor|president|chief|party|"
                              r"leader|judge|journalist|pti|apc|pdp|opposition)|clashes with \w+ (?:over|on) |"
                              r"\bs'en prend (?:a|au)\b")
_FACTCHECK_RE = re.compile(r"\bson de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|"
                           r"diciembre)\b|\bno de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|"
                           r"noviembre|diciembre)\b|fact[- ]check|verificacion|desinformacion|imagenes antiguas|old video")
_URDU_RE = re.compile(r"[ٹڈڑںھہے]")
_URDU_SECURITY_RE = _word_re(["دہشت", "دھماک", "بم", "خودکش", "مسلح افراد", "عسکریت", "حملہ آور", "پولیس پارٹی",
                              "ایف سی", "سیکیورٹی فورسز", "فتنۃ", "فتنہ", "اغوا"])
_HINDI_SECURITY_RE = _word_re(["आतंक", "उग्रवाद", "नक्सल", "बम", "विस्फोट", "ब्लास्ट", "दंगा", "दंगे", "सांप्रदायिक",
                               "आंसू गैस", "प्रदर्शन", "ड्रोन", "मिसाइल", "सेना"])
_PROTEST_MINE_RE = _word_re(["minerii", "minerilor", "mineri", "mina", "minei", "exploatarea", "subteran", "protest",
                             "refuza", "salarii"])
_LANDSLIDE_VICTORY_RE = _word_re(["landslide victory", "landslide win", "landslide majority", "predicts landslide",
                                  "victoire ecrasante", "victoria aplastante"])
_UNREST_HINT_RE = _word_re(["disturbios", "cargas policiales", "carga policial", "contra la policia", "contre la police",
                            "forces de l'ordre", "antifascist", "jeunes", "migrants",
                            "migrantes", "altercados", "bengalas", "mitin", "carabineros", "riot", "riots", "emeute",
                            "emeutes", "lacrymo", "indigenas", "violences urbaines", "17 octobre", "ultra-droite",
                            "ultradroite", "manifestation", "manifestations", "mobilisation", "marcha", "protesters",
                            "street medic", "pillages", "barricades"])
_STRIKE_MILITARY_RE = re.compile(r"\b(?:forces|drone|drones|missile|missiles|shahed|russian|ukrainian|israeli|air)\s+"
                                 r"(?:\w+\s+)?strikes?\b|\bstrikes? (?:hit|on|against|kill)")

# ------------------------------------------------------------------ v0.29 (run 4) : contrôle hors échantillon
# Mesure sur 559 titres jamais vus (carte du 24 octobre, règles v0.28 en ligne) : 257 faux positifs (46 %). Les règles
# ajoutées sont volontairement générales (familles de motifs plutôt que phrases) : sport, annonces et interdictions de
# manifester, alertes météo sans dégâts, brèves locales, procédures judiciaires, déclarations, nouvelles militaires.
SPORT3_WORDS = ["penalty", "penalties", "penaltis", "penales", "goal", "goals", "goles", "gol$", "golazo", "goalie",
                "goalkeeper", "portero", "gardien de but", "squad", "la liga", "premier league", "serie a", "bundesliga",
                "ligue 1", "champions league", "europa league", "cup final", "final place", "semi-final", "semifinal",
                "quarter-final", "matchday", "fixture", "fixtures", "clasico", "partido", "jornada", "por la fecha",
                "camogie", "hurling", "gaelic", "wnbl", "nfl", "mlb", "nhl", "punters", "jockey", "racecourse",
                "sha tin", "yesil sahalar", "stormsteg", "stormers", "lightning stakes", "adelaide lightning", "knockout",
                "head coach", "entrenador", "hat-trick", "hat trick", "red card", "carton rouge",
                "tarjeta roja", "ibrox", "vallecas", "stade de france", "camp nou", "bernabeu",
                "transfer window", "verpflichtet", "secures point", "secure point", "earns point", "victory over",
                "win over", "beats", "sink", "sinks", "draw with", "bulls against", "rayo vs", "vs.", "frente a frente", "historial de",
                "to victory", "real madrid", "atletico madrid", "psg", "juventus", "bayern munich", "manchester united",
                "manchester city", "ac milan", "inter milan", "olympique de marseille", "olympique lyonnais"]
_SPORT3_RE = _word_re(SPORT3_WORDS)
_SCORE_RE = re.compile(r"\b\d{1,2}\s*[-–:]\s*\d{1,2}\b(?!\s*(?:h|heures|ans|km|octobre|october|oct))")
ANNOUNCE_WORDS = ["interdit", "interdite", "interdits", "interdites", "interdiction", "interdictions", "aucune manifestation",
                  "n'est autorisee", "ne sera autorisee", "prefecture", "parcours", "trace de la manifestation", "attendue",
                  "attendues", "attendus", "prevue", "prevues", "a quoi s'attendre", "ce qu'il faut savoir",
                  "quelles mesures", "y aura-t-il", "perturbations attendues", "appelle a manifester", "appellent a",
                  "convoca", "convocan", "scheduled", "to take place", "will take place", "planned protest",
                  "plan to protest", "se organizan", "preparan", "aprovam novos", "redoutent", "redoute", "crainte",
                  "inquiet", "inquietude", "couvre-feu sera", "sera instaure", "dispositif", "securite renforcee",
                  "haute securite", "ultra-securise", "barricaded for possible", "for possible unrest", "renfort",
                  "renforts", "recours", "mesures exceptionnelles", "nouveau parcours", "suivez", "en prevision",
                  "a la veille", "ahead of", "avant la manifestation", "demain", "tomorrow", "samedi prochain",
                  "ce samedi", "ce week-end", "this weekend", "este sabado", "am sonntag", "le prefet", "faut-il"]
_ANNOUNCE_RE = _word_re(ANNOUNCE_WORDS)
_DESPITE_RE = _word_re(["malgre", "despite", "pese a", "a pesar", "brave", "bravent", "ont brave", "defy", "defient"])
# signes qu'une manifestation a bien eu lieu (ou se déroule) : l'annonce n'est alors qu'un détail du récit
_CALL_RE = _word_re(["appelle a", "appellent a", "calls for", "convoca", "convocan", "llama a"])
_PLOT_RE = _word_re(["se organizan para", "para provocar", "plan to provoke", "prevoient de", "planean"])
# citation en tête à la première personne (« J'avais la boule au ventre… ») : témoignage
_LEADING_QUOTE_RE = re.compile(r'^\W{0,3}[«"“„][^»"”“]*\b(?:je|j\'|on|nous|i|we|my|mon|ma|yo|nos)\b[^»"”“]*[»"”“]')
_ANALYSIS3_RE = _word_re(["qui sont", "immersion au", "en immersion", "doivent-elles", "doit-on", "faut-il", "outlets framed", "profiles",
                          "como se ha", "vers un bain", "revele", "revelo", "detalla", "ofensiva mediatica",
                          "offensive mediatique", "media offensive", "awareness", "world polio day", "end polio",
                          "journee de l", "participe a la manifestation", "certificacion", "celebran", "se plantea",
                          "declarar emergencia", "siapkan", "strategi$", "shirya", "incorpora", "para enfrentar",
                          "en campana", "asks officials", "resilient", "plan de riesgos", "estudo clinico",
                          "vacina", "dispositif de detection", "prolonge", "prolongation", "extended until",
                          "compensate"])
_LAUNCH_RE = _word_re(["launches", "launch", "lance", "a lance", "lancement", "sensibilisation", "awareness", "inaugur",
                       "caravane", "campagne", "campaign"])
_HEALTH_NOISE_RE = _word_re(["no confirmed case", "aucun cas confirme", "ningun caso", "negative", "negatif", "negativo",
                             "no outbreak", "clarifies", "en greve", "grevistes", "strike for", "primes", "menacent de suspendre"])
_HAPPENED_RE = _word_re(["blocking", "bloquean", "bloqueando", "occupent", "occupy", "occupying", "ont ", "se sont", "a eu lieu", "ont eu lieu", "took place", "marched", "rallied", "gathered",
                         "protested", "blocked", "bloque", "bloquent", "defilent", "ont defile", "manifestent",
                         "protestan", "protestam", "protestano", "protestieren", "rassemblement a", "rassemblent",
                         "cortege", "en cours", "sous tension", "tensions", "flood", "throng", "fill the streets",
                         "descend on", "took to the streets", "descendent dans la rue", "investissent", "disturbios",
                         "saqueos", "quema", "scontri", "heurts", "echauffourees", "lacrymo", "projectiles", "casse",
                         "degradations", "brises", "affrontements", "clashes", "enfrentamientos", "pillages", "interpell",
                         "detenidos", "arrested", "arrestations", "blesses", "injured", "heridos"])
_TURNOUT_RE = re.compile(r"\d[\d\s .]*\s*(?:manifestants|personnes|people|protesters|manifestantes|demonstrators|"
                         r"persone|menschen|pessoas)\b|\b(?:thousands|hundreds|milliers|centaines|miles|cientos|milhares|"
                         r"tausende|hunderte)\b")
WARNING2_WORDS = ["expected", "predicted", "forecast", "likely by", "likely to", "brewing", "brace for", "braces for",
                  "threatens", "ameaca", "amenaza", "se espera", "se esperan", "a que hora llegan", "registraran",
                  "sigue alerta", "alerta amarilla", "alerta naranja", "alerta verde", "yellow warning", "amber warning",
                  "orange warning", "red warning", "warning in effect", "warning issued", "warnings issued",
                  "alerts issued", "warning for", "flood warning", "flood alert", "uyarisi", "uyari", "upozorava",
                  "предупреждение", "livsfara", "varning", "warnung", "se forma", "low pressure", "depression",
                  "basse pression", "내일", "approaching", "s'approche", "se acerca", "se aproxima", "en camino",
                  "risco de", "riesgo de", "dikkat", "attendues", "attendus", "prevues", "iniciara", "week-end noir",
                  "que pasara", "pourrait", "podria", "could bring"]
_WARNING2_RE = _word_re(WARNING2_WORDS)
_IMPACT2_RE = _word_re(["hits", "hit by", "batters", "battered", "lash", "lashes", "slams", "slam", "sweep", "sweeps",
                        "closes", "closed", "close roads", "cancel", "cancels", "cancelled", "disruption", "disrupts",
                        "prives d'electricite", "coupures", "power cut", "without power", "blackout", "stranded",
                        "flooded", "inundad", "anegad", "plough", "injured", "blesses", "degats", "damage", "destroyed", "derrumb",
                        "collapsed", "arrastrad", "evacu", "kills", "killed", "dead", "muertos", "morts", "rescued",
                        "submerg", "affected", "afectad", "touched down", "made landfall", "toque tierra", "landfall",
                        "brings heavy", "apporte", "trae fuertes", "scrapped", "annule", "annulee", "suspendu", "provoc"])
DIGEST2_RE = re.compile(r"\b(?:en vivo|en direct|live|minute par minute|minuto a minuto|recap|morning recap|итоги дня)\b"
                        r".{0,80}\b(?:hoy|today|aujourd'hui|cette semaine|this week|\d{1,2} de (?:octubre|noviembre)|"
                        r"seguridad|clima|bloqueos|top stories|other top)", re.I)
JUDICIAL2_WORDS = ["judge rules", "judge says", "juge", "jugee", "juge a", "juzgar", "juicio", "court orders", "court rules",
                   "court order", "panel to hear", "to hear evidence", "suit over", "lawsuit", "sues", "demanda a",
                   "apologie", "apologia", "inculpe", "mis en examen", "procesan", "denuncian en", "privados de libertad",
                   "nab", "nabs", "nabbed", "presentes au", "presentados", "aprehenden", "perquisizioni", "perquisitions",
                   "allanamientos", "fauteurs de troubles presentes", "case after", "changes stance", "igpn",
                   "enquete de l'igpn", "enquete ouverte", "probe launched", "launch probe", "launches probe", "توقيف",
                   "القبض على", "judge says", "judge orders", "must have new manager"]
_JUDICIAL2_RE = _word_re(JUDICIAL2_WORDS)
# verbes de réaction souvent attachés au récit d'un vrai fait (« denuncian secuestro », « exigen paz ») volontairement
# absents : ils ne suffisent pas à faire d'un titre une simple déclaration
STATEMENT3_WORDS = ["calls on", "llama a", "reaffirme", "reaffirms", "insiste", "distances itself", "se desmarca",
                    "issues warning", "harsh warning", "sounds alarm", "alerte lancee", "lance l'alerte", "alleges",
                    "says ex", "former u.s. envoy", "ex-us envoy", "envoy says", "minister says", "commissioner says",
                    "president issues", "offers to", "has offered", "affirme que", "furieux", "furious", "criticise",
                    "criticize", "seeks to portray", "عون:", "گفت", "کارشناس", "تشديد الإجراءات", "إجراءات أمنية",
                    "tightens security", "tightening security", "heightened security", "renforce la securite",
                    "threatening", "fears that", "fear that", "may attack", "procureur", "prosecutor", "fiscal general", "falam em"]
_STATEMENT3_RE = _word_re(STATEMENT3_WORDS)
# suites certaines, même si le titre rappelle le bilan (« body of Bangladeshi killed in Riyadh attack arrives in Dhaka »)
_AFTERMATH_STRICT_RE = _word_re(["vigil$", "vigils", "candlelight", "vigile$", "veillee", "condolence", "condoleances", "عزاء",
                                 "blood donation", "التبرع بالدم", "discharged", "dado de alta", "body of", "repatri",
                                 "played dead", "playing dead", "hablo el hombre", "le recit", "recit glacant", "retour sur",
                                 "bilan mitige", "studi kasus", "perdieron todo", "que cultivos", "habilitada", "reopened",
                                 "fin de la greve", "end hunger strike", "agrees to end", "au obtinut", "promisiuni",
                                 "orders checks", "after years", "years after", "historia de", "la dramatica historia",
                                 "perdidas aseguradas", "insured losses", "ayuda federal", "federal aid", "provides",
                                 "donates", "sediakan", "relawan", "يتفقد", "inspects", "inspect", "readiness",
                                 "rescue kidnap", "rescues kidnap", "rescued kidnap", "kidnap victim", "evitaron",
                                 "evitan", "frustraron", "plans for", "discussed plans"])
AFTERMATH3_WORDS = ["arrives in", "historial", "recit", "tras los disturbios", "apres la liberation", "after the release",
                    "un an apres", "a year after", "year after", "penyebab", "drama de los", "se han perdido", "reabierta",
                    "back to normal", "retour a la normale", "ends hunger strike", "ont obtenu"]
_AFTERMATH3_RE = _word_re(AFTERMATH3_WORDS)
MILITARY3_WORDS = ["improves", "mass-produces", "mass produces", "veut produire", "produire", "to produce", "production",
                   "recruiting", "recruit", "recrute", "arming", "delays approval", "approval of", "patriot missiles",
                   "missile defense", "missile defence", "spent", "deploys", "deploy", "sends troops", "unit base",
                   "sets up", "lessons", "trains its", "training", "drills", "exercise", "manoeuvres", "maniobras"]
_MILITARY3_RE = _word_re(MILITARY3_WORDS)
_ECONOMY2_RE = _word_re(["oil price", "prix du petrole", "barrel", "baril", "precio del petroleo", "stocks", "markets",
                         "marches financiers", "exports", "export", "eksport", "trade deal", "inflation", "tariff"])
CULTURE2_WORDS = ["cartelera", "cine", "cinema", "festival", "fest$", "cortometrajes", "horror", "terror se toma",
                  "game", "jeu video", "satire", "satira", "mural", "lan-party", "lan party",
                  "vulkanlan", "celebs", "celebrity", "selebriti", "seleb$", "speak up", "ex-miss", "miss universe", "concierto",
                  "concert",
                  "tiger shroff", "bollywood", "series", "netflix", "museum", "exhibition", "mostra", "zoo"]
_CULTURE2_RE = _word_re(CULTURE2_WORDS)
_MISC_NOISE_RE = re.compile(r"\bbird strike\b|\bhacked to death\b|\bkalp krizi\b|\bcrime epidemic\b|\bepidemic of\b|"
                            r"\bcrocodile\b|\bcrocodil|\bjadwal\b|\bpemadaman\b|"
                            r"\bcoupures? d'electricite annoncees\b|\bmanifesto\b|\bmanifeste electoral|"
                            r"\bscam\b|\bonline fraud\b|\bescroquerie\b|\bfraude en ligne\b|\bcyberlibel\b|\bcaravane\b|"
                            r"\bprejudices de la cybercriminalite\b|\bmiddelalder|\bmedieval\b|\bmoyen age\b|"
                            r"\bstate of emergency\b.{0,40}\b(?:youth|services|children)|\btrau\b|\bbuffalo\b|"
                            r"\bworld \w+ day\b|\b(?:janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|"
                            r"novembre|decembre) dernier\b|\beksport\b")
_HINDI_PROTEST_RE = _word_re(["धरना", "विरोध प्रदर्शन", "आंदोलन", "लाठीचार्ज", "आंसू गैस", "बंद", "हड़ताल", "पथराव"])
_HINDI_DESK_RE = re.compile(r"^[\w .'-]{2,30}\s(?:news|samachar|समाचार)\s*[:|]", re.I)


def audit3_noise(t, cat):
    """Bruit (v0.29) : sport, culture, faux sens, brèves locales en hindi."""
    if _SPORT3_RE.search(t) and not _VIOLENCE_RE.search(t.replace("strike", "")) and cat not in NATURAL - {"storm"}:
        return "sport"
    if _SCORE_RE.search(t) and re.search(r"\bvs?\.?\b|\bcontre\b|\bcontra\b|\bagainst\b|\bfecha\b|\bliga\b", t) \
            and not _FRESH_RE.search(t):
        return "sport"
    if _CULTURE2_RE.search(t) and not heavy_toll(t) and not _PHYSICAL2_RE.search(t):
        return "hors sujet (culture)"
    if _MISC_NOISE_RE.search(t):
        return "hors sujet"
    if cat in ("cyber", "infrastructure") and _LAUNCH_RE.search(t) and not _FRESH_RE.search(t) \
            and not _PHYSICAL2_RE.search(t):
        return "annonce"
    if _DEVANAGARI.search(t) and not heavy_toll(t) and (
            _HINDI_DESK_RE.search(t) or (cat == "unrest" and not _HINDI_PROTEST_RE.search(t))):
        return "fait divers local"
    if cat in ("armed_conflict", "attack", "unrest") and _ECONOMY2_RE.search(t) and not _FRESH_RE.search(t):
        return "économie"
    return None


def audit3_context(t, cat, fresh, physical):
    """Contexte (v0.29) : annonces, alertes sans dégâts, résumés, procédures, déclarations, suites, militaire."""
    if DIGEST2_RE.search(t):
        return "analyse"
    if _AFTERMATH_STRICT_RE.search(t):
        return "prévention, bilan ou suites" if cat in NATURAL or cat == "health" else "suites (enquête, hommage, témoignage)"
    if _ANALYSIS3_RE.search(t) or (_LEADING_QUOTE_RE.search(t) and not physical and cat in VIOLENT_CATS | {"unrest"}):
        return "analyse"
    if _JUDICIAL2_RE.search(t) and cat in NATURAL:
        return "arrestation ou suites"
    if cat in NATURAL or cat == "health":
        if _WARNING2_RE.search(t) and not _IMPACT2_RE.search(t) and not fresh:
            return "prévision"
        if cat == "health" and _HEALTH_NOISE_RE.search(t):
            return "prévention, bilan ou suites"
        if _AFTERMATH3_RE.search(t) or (_STATEMENT3_RE.search(t) and not fresh):
            return "prévention, bilan ou suites"
        return None
    if cat == "unrest" and ((_ANNOUNCE_RE.search(t) and not physical and not _TURNOUT_RE.search(t)
                             and not _HAPPENED_RE.search(t) and (not _DESPITE_RE.search(t) or _CALL_RE.search(t)))
                            or _PLOT_RE.search(t)):
        return "annonce"
    if _JUDICIAL2_RE.search(t) and not (physical and cat == "unrest"):
        return "arrestation ou suites"
    if _AFTERMATH3_RE.search(t) and not fresh:
        return "suites (enquête, hommage, témoignage)"
    if _STATEMENT3_RE.search(t) and not physical:
        return "déclaration"
    if cat in VIOLENT_CATS and _MILITARY3_RE.search(t) and not fresh and not _CONCRETE_ATTACK_RE.search(t):
        return "annonce militaire"
    return None

def audit_noise(t, cat):
    """Non-incidents relevés en production (v0.28), texte normalisé : motif d'exclusion, ou None."""
    why = audit3_noise(t, cat)
    if why:
        return why
    if cat in ("attack", "crime") and _LOGISTICS_RE.search(t):
        return "hors sujet (enlèvement de marchandises)"
    if cat == "flood" and _SEWAGE_RE.search(t) and not heavy_toll(t):
        return "pollution locale"
    if cat in ("attack", "crime") and _POLICE_INVOLVED_RE.search(t) and not heavy_toll(t):
        return "intervention policière"
    if cat in ("attack", "crime", "terrorism") and _MANHUNT_RE.search(t) and _ALLEGED_RE.search(t):
        return "personne recherchée"
    if cat in ("attack", "crime") and not heavy_toll(t) and (
            (_DEVANAGARI.search(t) and _LOCAL_DESK_RE.search(t)) or _SOUTH_ASIA_CRIME_RE.search(t)):
        return "fait divers local"
    # v0.28, run 2
    if cat in ("attack", "crime") and not heavy_toll(t) and (
            (_DEVANAGARI.search(t) and not _HINDI_SECURITY_RE.search(t)) or
            (_URDU_RE.search(t) and not _URDU_SECURITY_RE.search(t))):
        return "fait divers local"   # brèves régionales en hindi et en ourdou : querelles, vols, règlements de comptes
    if cat in VIOLENT_CATS and _POLICE_CLASH_RE.search(t) and not heavy_toll(t):
        return "intervention policière"
    if cat in VIOLENT_CATS and _VERBAL_CLASH_RE.search(t) and not _FRESH_RE.search(t):
        return "politique (joute verbale)"
    if _SPORT2_RE.search(t):
        return "sport"
    if _ANIMAL_RE.search(t) and not heavy_toll(t):
        return "hors sujet (animaux)"
    if _FACTCHECK_RE.search(t):
        return "rétrospective ou démenti"
    if cat == "earthquake" and _WEAK_QUAKE_JA_RE.search(t):
        return "séisme faible (couvert par l'USGS)"
    if _JA_NOISE_RE.search(t):
        return "hors sujet"
    if _CULTURE_RE.search(t):
        return "hors sujet (culture)"
    if cat in VIOLENT_CATS and _SEIZURE2_RE.search(t) and not _FRESH_RE.search(t):
        return "saisie"
    if cat in ("attack", "crime") and _FAMILY_RE.search(t):
        return "fait divers"
    if cat in VIOLENT_CATS and _BR_CONFRONTO_RE.search(t) and _BR_POLICE_RE.search(t) and not heavy_toll(t):
        return "intervention policière"
    return None


def audit_context(t, cat):
    """Titres de sûreté qui ne décrivent pas un fait physique (v0.28) : motif, ou None. Texte normalisé."""
    fresh = bool(_FRESH_RE.search(t))   # casualty_toll lirait « 53 personel » (indonésien) comme un bilan
    if cat in NATURAL or cat == "health":
        if _FORECAST_RE.search(t) and not _IMPACT_RE.search(t) and not fresh:
            return "prévision"
        if _AFTERCARE_RE.search(t):
            return "prévention, bilan ou suites"
        return audit_context2(t, cat, fresh)
    if _TESTIMONY_RE.search(t) and not fresh and not _PHYSICAL2_RE.search(t):
        return "analyse"
    if _SUMMON_RE.search(t) and not (fresh and not _SUMMON_RE.search(" ".join(t.split()[:8]))):
        return "arrestation ou suites"
    if cat in ("armed_conflict", "terrorism", "attack") and _CEASEFIRE_RE.search(t) and not _VIOLATION_RE.search(t) \
            and not fresh and not _CONCRETE_ATTACK_RE.search(t):
        return "cessez-le-feu (annonce)"
    if cat in VIOLENT_CATS and _WARNS_AGAINST_RE.search(t) and not fresh:
        return "déclaration"
    if cat in VIOLENT_CATS and _STATEMENT_RE.search(t) and not fresh and not _CONCRETE_ATTACK_RE.search(t):
        return "déclaration"
    if cat in ("armed_conflict", "terrorism") and _MISSILE_TEST_RE.search(t) and not fresh:
        return "annonce militaire"
    if cat == "unrest" and _AFTER_RIOTS_RE.search(t) and not fresh:
        return "prévention, bilan ou suites"
    if cat in ("health",) and _AFTERCARE_RE.search(t):
        return "prévention, bilan ou suites"
    return audit_context2(t, cat, fresh)


def audit_context2(t, cat, fresh):
    """Second audit de la production (v0.28, run 2) : suites, menaces, analyses, sujets militaires, prévention."""
    soft = _FOLLOWUP_SOFT_RE.search(t)
    # « après les émeutes » : le mot « émeutes » de la formule ne compte pas comme un fait décrit
    rest = (t[:soft.start()] + " " + t[soft.end():]) if soft else t
    rest = rest.replace("couvre-feu", " ").replace("toque de queda", " ")
    physical = bool(_FRESH_RE.search(rest)) or bool(_PHYSICAL2_RE.search(rest))
    if _DIGEST_RE.search(t) or _GENRE_RE.search(t) or _ANALYSIS_STRICT_RE.search(t):
        return "analyse"
    why = audit3_context(t, cat, fresh, physical)   # v0.29 (run 4)
    if why:
        return why
    if cat in NATURAL or cat == "health":
        if _PREPARE_RE.search(t) and not (fresh and not _FOLLOWUP_RE.search(t)):
            return "prévention, bilan ou suites"
        if _PREPARE_STRICT_RE.search(t):
            return "prévention, bilan ou suites"
        if _PLAN_PROTEST_RE.search(t) or (_QUOTE_SAYS_RE.search(t) and not fresh):
            return "déclaration"
        if _FOLLOWUP_RE.search(t) or _ANALYSIS_STRICT_RE.search(t) or (
                (_ANALYSIS2_RE.search(t) or _STATEMENT2_RE.search(t) or _FOLLOWUP_SOFT_RE.search(t))
                and not fresh and not _IMPACT_RE.search(t) and not _NAT_IMPACT2_RE.search(t)):
            return "prévention, bilan ou suites"
        return None
    if _FOLLOWUP_RE.search(t) or (soft and not physical) or \
            _ARREST_LEAD_RE.search(" ".join(t.split()[:8])):
        return "suites (enquête, hommage, témoignage)"
    if _ANALYSIS2_RE.search(t) and not physical:
        return "analyse"
    if cat in VIOLENT_CATS | {"unrest", "political"} and _THREAT_RE.search(t) and not fresh:
        return "déclaration"
    if _STATEMENT2_RE.search(t) and not physical:
        return "déclaration"
    if cat in VIOLENT_CATS and (_MILITARY_NEWS_RE.search(" ".join(t.split()[:8])) or
                                (_MILITARY_NEWS_RE.search(t) and not fresh)):
        return "annonce militaire"
    if _QUOTE_SAYS_RE.search(t) and not physical:
        return "déclaration"
    if cat in ("unrest", "health", "political") and _PLAN_PROTEST_RE.search(t):
        return "annonce"
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
    t = re.sub(r"\bpeste (?=(?:o |un |una |\d))", "plus de ", t)   # roumain « peste 90 » = plus de 90 (pas la peste)
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
    if cat in ("attack", "crime") and _CYBER_HINT_RE.search(t) and not _VIOLENCE_RE.search(t):
        cat = "cyber"   # « lycées piratés : les élèves doivent changer leur mot de passe » (v0.28)
    if cat == "armed_conflict" and (("unrest" in found and _PROTEST_RE.search(t)) or _CIVIL_UNREST_RE.search(t)) \
            and not _MILITARY_RE.search(t) and not _ARMED_GROUP_RE.search(t):
        cat = "unrest"  # manifestation dispersée au gaz lacrymogène, heurts avec la police (v0.28)
    # v0.28, run 2
    if cat == "flood" and _FLOOD_METAPHOR_RE.search(t):
        if not (_PROTESTERS_RE.search(t) and "unrest" in _CAT_RE):
            return None, None   # « posters flood Kaduna », « synthetic drugs flooding the US »
        cat = "unrest"          # « Thousands flood Athens streets in education protest »
    if cat == "volcano" and _PROTEST_MINE_RE.search(t):
        return ("unrest", BASE_SEVERITY["unrest"]) if _word_re(["protest", "refuza"]).search(t) else (None, None)
    if cat == "landslide" and _LANDSLIDE_VICTORY_RE.search(t):
        return None, None
    if cat == "terrorism" and _TERROR_METAPHOR_RE.search(t):
        rest = [c for c in found if c != "terrorism" and _CAT_RE[c].search(_TERROR_METAPHOR_RE.sub(" ", t))]
        if not rest:
            return None, None
        cat = rest[0]           # « système d'artillerie qui terrorisait Kherson » : conflit armé, pas terrorisme
    if cat == "unrest" and _STRIKE_MILITARY_RE.search(t) and not _PROTEST_RE.search(t):
        cat = "armed_conflict"  # « Russian forces strike energy facility » n'est pas une grève
    if cat == "armed_conflict" and _UNREST_HINT_RE.search(t) and not _MILITARY_RE.search(t) \
            and not _ARMED_GROUP_RE.search(t) and not _STRIKE_MILITARY_RE.search(t):
        cat = "unrest"          # heurts avec la police, émeutes urbaines du 17 octobre
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
        self.nospace_countries = []  # (nom de pays en chinois, japonais, thaï…, iso2) : recherche en sous-chaîne (v0.28)

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
                        # chinois, thaï… : un nom de 2 caractères est trop ambigu (« 河西 » dans « 约旦河西岸 », la
                        # Cisjordanie, donnait Genhe en Mongolie-Intérieure) sauf pour les très grandes villes (v0.28)
                        if (len(k) >= 3 and pop >= 50000) or (len(k) >= 2 and pop >= 1000000):
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
        names = {}
        for item in self.countries.items:
            for n in {item["name_en"], item["name_fr"]}:
                k = norm(n or "")
                if len(k) > 3 and k not in AMBIGUOUS_COUNTRY_NAMES:
                    names[k] = item["iso2"]
        names.update(_extra_country_aliases())
        for alias, iso in SCRIPT_COUNTRY_ALIASES.items():
            k = norm(alias)
            if _NOSPACE.search(k):
                self.nospace_countries.append((k, iso))
            else:   # arabe, persan, hébreu, cyrillique, devanagari : mot entier (« إسرائيلية » n'est pas « إسرائيل »)
                names[k] = iso
        for k, iso in _cldr_country_names().items():   # 28 langues (v0.28 : « França », « Ucrânia », « Arnavutluk »)
            names.setdefault(k, iso)
        self.country_index = names
        self.country_max_words = max(len(k.split()) for k in names)
        self.ready = True
        return self

    def country_mentions(self, title):
        """Pays cités dans le titre, dans l'ordre : [(position, iso2, acteur ?, entre guillemets ?)] (v0.28)."""
        t = strip_media(norm(title))
        quoted = [m.span() for m in _QUOTED_RE.finditer(t)]
        found = []
        toks = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"[\w'’-]+", t)]
        idx = self.country_index
        for i in range(len(toks)):
            for n in range(min(self.country_max_words, len(toks) - i), 0, -1):
                key = " ".join(x[2] for x in toks[i:i + n])
                iso = idx.get(key)
                if not iso and n == 1:
                    for strip in _script_prefix_variants(key):
                        iso = idx.get(strip)
                        if iso:
                            break
                if iso:
                    found.append((toks[i][0], toks[i + n - 1][1], iso))
                    break
        for k, iso in self.nospace_countries:
            i = t.find(k)
            while i >= 0:
                found.append((i, i + len(k), iso))
                i = t.find(k, i + len(k))
        found.sort(key=lambda x: (x[0], -x[1]))
        out = []
        for start, end, iso in found:
            if out and start < out[-1][4]:
                continue   # « soudan du sud » contient « soudan »
            after = t[end:end + 40]
            actor = bool(_ACTOR_AFTER_RE.match(after)) or (bool(_NOSPACE.search(t[start:end])) and
                                                           any(after.startswith(x) for x in CJK_ACTOR_SUFFIX))
            inq = any(a <= start < b for a, b in quoted)
            out.append((start, iso, actor, inq, end))
        return [x[:4] for x in out]

    def find_country(self, title, with_actor=False):
        """Pays où se passe le fait : premier pays cité hors guillemets qui n'est pas l'auteur d'une frappe
        (« Russia hits central Kyiv » : la Russie est l'acteur), sinon le premier cité."""
        ms = self.country_mentions(title)
        if not ms:
            return (None, False, -1) if with_actor else None
        outside = [m for m in ms if not m[3]] or ms
        place = [m for m in outside if not m[2]]
        best = place[0] if place else outside[0]
        return (best[1], best[2], best[0]) if with_actor else best[1]

    def find_city(self, title, iso, allow_capital_bare=False, lang=""):
        """Ville du pays citée dans le titre (la plus peuplée si plusieurs)."""
        d = self.by_country.get(iso)
        if not d:
            return None
        title = strip_media(title)
        hit = self._match(title, d, allow_capital_bare, lang in PREP_LANGS)
        if hit or not _NOSPACE.search(title):
            return hit
        t = norm(title)  # titres en thaï, chinois… : nom de ville cherché dans le texte (le plus long, puis le plus peuplé)
        found = [(len(k), e[3], e) for k, e in self.nospace.get(iso, []) if k in t]
        if not found:
            return None
        e = max(found)[2]
        return {"place": e[0], "lat": e[1], "lon": e[2], "capital": e[4], "pop": e[3]}

    def geocode(self, place, iso):
        """Coordonnées d'un lieu nommé (par l'IA) dans un pays donné."""
        d = self.by_country.get(iso) or {}
        hit = d.get(norm(place)) or next((v for k, v in d.items() if k.startswith(norm(place) + " ")), None)
        return {"place": hit[0], "lat": hit[1], "lon": hit[2]} if hit else None

    def _match(self, title, d, allow_capital_bare, prep_langs=False):
        t = norm(title)
        tokens = re.findall(r"[\w-]+", t)
        raw_tokens = re.findall(r"[\w-]+", title)
        hits, keys = [], []
        for size in (3, 2, 1):
            for i in range(len(tokens) - size + 1):
                key = " ".join(tokens[i:i + size])
                if key in d:
                    first = raw_tokens[i] if i < len(raw_tokens) else ""
                    if first[:1].isalpha() and first[:1].islower() and first[:1].upper() != first[:1]:
                        continue  # mot commun en minuscules (« nice day »)
                    nxt = tokens[i + size] if i + size < len(tokens) else ""
                    if nxt in PLACE_SUFFIX:
                        continue  # « Monterey Park » (Californie) n'est pas Monterrey (Mexique) (v0.28)
                    prev = tokens[i - 1] if i > 0 else ""
                    hits.append((d[key], nxt, prev))
                    keys.append(key)
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
        key, nxt, prev = next((k, n, pr) for (h, n, pr), k in zip(hits, keys) if h is best)
        return {"place": best[0], "lat": best[1], "lon": best[2], "capital": best[4], "key": key, "prev": prev,
                "pop": best[3]}

    def locate(self, title, country_hint=None, category=None, lang=""):
        """Renvoie {country, place, lat, lon, precision} ou {country} ou None."""
        natural = category in NATURAL
        title = strip_media(title)
        cited, actor, cited_pos = self.find_country(title, with_actor=True)
        cited = cited or demonym_place(title)
        iso = cited or country_hint
        if iso:
            # pays déduit de l'édition du flux (Google News États-Unis, Chine…) ou seulement auteur d'une frappe : une
            # grande ville étrangère citée l'emporte sur un homonyme local (« near Paris » n'est pas Paris, Texas ni
            # Parys en Afrique du Sud) ou sur une ville d'origine (« Hyderabad man killed in Riyadh airport attack ») (v0.28)
            big = self._match(title, self.big_entries, natural or actor, lang in PREP_LANGS)
            if big and self.big_iso.get(big["place"]) and self.big_iso[big["place"]] != iso:
                local = self.find_city(title, iso, natural, lang)
                strong = big["prev"] in LOC_PREP_STRONG and not (local and local.get("prev") in LOC_PREP_STRONG)
                # même mot : la ville locale ne porte ce nom qu'en variante (« Paris » pour Parys, Afrique du Sud) ou est
                # un petit homonyme (Paris, Texas : 25 000 habitants contre 2 millions)
                same_word = bool(local) and local.get("key") == big["key"] and (
                    norm(local["place"]) != big["key"] or big.get("pop", 0) >= 20 * (local.get("pop") or 1))
                # pays cité (non auteur) : la grande ville l'emporte seulement si elle est citée avant lui, après « in »
                # (« strikes reported in Kyiv… Russia »), pas « attaque contre l'Ukraine… négociations à Saint-Pétersbourg »
                before = 0 <= norm(strip_media(title)).find(big["key"]) < cited_pos if cited_pos >= 0 else True
                if (cited and (actor or (strong and before))) or (not cited and (not local or same_word or strong)):
                    return {"country": self.big_iso[big["place"]], "place": big["place"], "lat": big["lat"],
                            "lon": big["lon"], "precision": "city"}
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


# Pays « auteur » d'un fait (v0.28) : « Russia hits Kyiv », « Israel strikes… », « 法国外长谴责… »
_ACTOR_AFTER_RE = re.compile(r"^(?:'s)?\s*(?:\w+\s+){0,1}(?:hits?|strikes?|struck|bombs?|bombed|attacks?|attacked|shells?|pounds?|"
                             r"launch(?:es|ed)?|fires?|fired|targets?|targeted|frappe\w*|bombarde\w*|attaque\w*|ataca\w*|"
                             r"bombardea\w*|golpea\w*|forces? (?:attack|strike|hit|launch|shell))\b")
CJK_ACTOR_SUFFIX = ("外长", "外交部", "总统", "总理", "政府", "军方", "国防部", "外相", "首相", "大統領", "政府は")
LOC_PREP_STRONG = {"in", "at", "on", "over", "near", "outside", "en", "a", "au", "dans", "pres", "em", "no", "na", "cerca", "im",
                   "bei", "nel", "nella", "в", "في", "قرب"}
_QUOTED_RE = re.compile(r'"[^"]{3,200}"|“[^”]{3,200}”|«[^»]{3,200}»|„[^“”]{3,200}[“”]')
def _script_prefix_variants(tok):
    """Préfixes collés de l'arabe (و، ف، ب، ل + ال) et de l'hébreu (ה، ב، ו، ל، מ، ש، כ) retirés : « والأردن » → « الأردن »."""
    out = []
    if _ARABIC.search(tok):
        for p in ("و", "ف", "ب", "ل"):
            if tok.startswith(p) and len(tok) > 4:
                out.append(tok[1:])
        if tok.startswith("لل"):
            out.append("ال" + tok[2:])
    elif _HEBREW.search(tok):
        for k in (1, 2):
            if len(tok) > k + 2 and all(c in "הבולמשכ" for c in tok[:k]):
                out.append(tok[k:])
    return out
# noms de pays ambigus en anglais ou en français : « Salvador » (Bahia), « Georgia » (État américain), « Jordan » (prénom)
AMBIGUOUS_COUNTRY_NAMES = {"salvador", "georgia", "georgie"}
US_STATES = ["alabama", "alaska", "arizona", "arkansas", "california", "californie", "colorado", "connecticut", "delaware",
             "florida", "floride", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
             "louisiane", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
             "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "nouveau-mexique",
             "north carolina", "caroline du nord", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
             "pennsylvanie", "rhode island", "south carolina", "caroline du sud", "south dakota", "tennessee", "texas",
             "utah", "vermont", "virginia", "virginie", "west virginia", "wisconsin", "wyoming", "carolina del norte",
             "carolina del sur", "luisiana", "pensilvania", "nuevo mexico", "virginia occidental"]
_CLDR = {}


def _cldr_country_names():
    """Noms de pays en 28 langues (config/country_names.json, généré par tools/build_country_names.py)."""
    if "n" not in _CLDR:
        try:
            raw = json.loads((ROOT / "config" / "country_names.json").read_text(encoding="utf-8"))["names"]
        except (OSError, ValueError, KeyError):
            raw = {}
        _CLDR["n"] = {norm(k): v for k, v in raw.items()
                      if norm(k) not in AMBIGUOUS_COUNTRY_NAMES and norm(k) not in DEMONYMS}
    return _CLDR["n"]


# Noms de pays et territoires dans d'autres écritures (v0.28) : un titre chinois sur la Cisjordanie ne doit pas être
# placé en Chine parce que le flux vient de l'édition chinoise de Google News. Pays « acteurs » fréquents (Israël,
# Russie, États-Unis) volontairement absents des écritures sans espaces : le premier pays cité serait souvent l'auteur
# de la frappe, pas le lieu.
SCRIPT_COUNTRY_ALIASES = {
    # chinois
    "约旦河西岸": "PS", "加沙": "PS", "黎巴嫩": "LB", "叙利亚": "SY", "也门": "YE", "苏丹": "SD", "南苏丹": "SS",
    "缅甸": "MM", "乌克兰": "UA", "阿富汗": "AF", "巴基斯坦": "PK", "伊拉克": "IQ", "索马里": "SO", "海地": "HT",
    "刚果": "CD", "马里": "ML", "尼日尔": "NE", "尼日利亚": "NG", "利比亚": "LY", "埃塞俄比亚": "ET", "菲律宾": "PH",
    "印度尼西亚": "ID", "印尼": "ID", "泰国": "TH", "越南": "VN", "日本": "JP", "韩国": "KR", "朝鲜": "KP", "台湾": "TW",
    "香港": "HK", "澳门": "MO", "墨西哥": "MX", "巴西": "BR", "法国": "FR", "德国": "DE", "英国": "GB", "意大利": "IT",
    "西班牙": "ES", "土耳其": "TR", "印度": "IN", "孟加拉": "BD", "尼泊尔": "NP", "斯里兰卡": "LK", "马来西亚": "MY",
    "柬埔寨": "KH", "老挝": "LA", "新加坡": "SG", "澳大利亚": "AU", "新西兰": "NZ", "埃及": "EG", "沙特": "SA",
    "约旦": "JO", "伊朗": "IR",
    # japonais
    "ヨルダン川西岸": "PS", "ガザ": "PS", "レバノン": "LB", "シリア": "SY", "イエメン": "YE", "ウクライナ": "UA",
    "ミャンマー": "MM", "アフガニスタン": "AF", "フィリピン": "PH", "インドネシア": "ID", "韓国": "KR",
    # thaï
    "เมียนมา": "MM", "พม่า": "MM", "กัมพูชา": "KH", "ลาว": "LA", "มาเลเซีย": "MY", "ฟิลิปปินส์": "PH",
    "อินโดนีเซีย": "ID", "เวียดนาม": "VN", "ญี่ปุ่น": "JP", "จีน": "CN", "ยูเครน": "UA", "กาซา": "PS",
    # arabe (mot entier)
    "فلسطين": "PS", "غزة": "PS", "الضفة الغربية": "PS", "لبنان": "LB", "سوريا": "SY", "العراق": "IQ", "اليمن": "YE",
    "السودان": "SD", "مصر": "EG", "ليبيا": "LY", "تونس": "TN", "الجزائر": "DZ", "المغرب": "MA", "الأردن": "JO",
    "السعودية": "SA", "الكويت": "KW", "قطر": "QA", "البحرين": "BH", "الإمارات": "AE", "الصومال": "SO",
    "مالي": "ML", "النيجر": "NE", "تشاد": "TD", "نيجيريا": "NG", "أفغانستان": "AF", "باكستان": "PK", "أوكرانيا": "UA",
    "إيران": "IR", "تركيا": "TR", "أبيي": "SD",
    # gentilés arabes (« وزير الداخلية الأردني ») ; israélien volontairement absent (souvent l'auteur de la frappe)
    "الأردني": "JO", "الأردنية": "JO", "السوري": "SY", "السورية": "SY", "العراقي": "IQ", "العراقية": "IQ",
    "اللبناني": "LB", "اللبنانية": "LB", "اليمني": "YE", "اليمنية": "YE", "السوداني": "SD", "السودانية": "SD",
    "المصري": "EG", "المصرية": "EG", "الليبي": "LY", "الليبية": "LY", "الفلسطيني": "PS", "الفلسطينية": "PS",
    "الصومالي": "SO", "الصومالية": "SO", "التونسي": "TN", "التونسية": "TN", "الجزائري": "DZ", "الجزائرية": "DZ",
    "المغربي": "MA", "المغربية": "MA", "الكويتي": "KW", "القطري": "QA", "الأفغاني": "AF", "الباكستاني": "PK",
    # persan et ourdou (mot entier ; « آذربایجان » volontairement absent : province iranienne)
    "افغانستان": "AF", "پاکستان": "PK", "عراق": "IQ", "سوریه": "SY", "یمن": "YE", "اوکراین": "UA", "ایران": "IR",
    "ترکیه": "TR", "هند": "IN", "بھارت": "IN",
    # hébreu
    "לבנון": "LB", "סוריה": "SY", "עזה": "PS", "תימן": "YE", "איראן": "IR", "עיראק": "IQ",
    # devanagari (hindi, népali)
    "पाकिस्तान": "PK", "नेपाल": "NP", "बांग्लादेश": "BD", "अफगानिस्तान": "AF", "श्रीलंका": "LK", "भारत": "IN",
}
PLACE_SUFFIX = {"park", "beach", "heights", "springs", "hills", "valley", "county", "township", "falls", "creek",
                "harbor", "harbour", "gardens", "grove", "ridge", "bluffs", "shores"}
MEDIA_NAMES = ["new york times", "new york post", "new york daily news", "washington post", "los angeles times",
               "la times", "chicago tribune", "boston globe", "times of israel", "jerusalem post", "times of india",
               "hindustan times", "economic times", "khaleej times", "gulf times", "tehran times", "moscow times",
               "kyiv independent", "kyiv post", "the guardian", "al jazeera", "bbc", "cnn", "france 24", "le parisien",
               "ouest-france", "la depeche", "le dauphine", "le progres", "dallas morning news", "houston chronicle",
               "miami herald", "seattle times", "irish times", "straits times", "bangkok post", "jakarta post",
               "manila times", "japan times", "korea times", "china daily", "global times", "south china morning post",
               "arab news", "jordan times", "egypt independent", "daily nation", "sydney morning herald", "the hindu",
               "dawn", "the nation", "punch", "vanguard", "premium times"]
_MEDIA_RE = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(n) for n in sorted(MEDIA_NAMES, key=len, reverse=True)) + r")(?!\w)", re.I)


DEMONYMS = {"ukrainian": "UA", "russian": "RU", "israeli": "IL", "palestinian": "PS", "lebanese": "LB", "syrian": "SY",
            "iraqi": "IQ", "iranian": "IR", "yemeni": "YE", "sudanese": "SD", "nigerian": "NG", "malian": "ML",
            "burkinabe": "BF", "somali": "SO", "kenyan": "KE", "ethiopian": "ET", "congolese": "CD", "pakistani": "PK",
            "afghan": "AF", "indian": "IN", "french": "FR", "german": "DE", "british": "GB", "spanish": "ES",
            "italian": "IT", "mexican": "MX", "colombian": "CO", "brazilian": "BR", "haitian": "HT", "venezuelan": "VE",
            "turkish": "TR", "saudi": "SA", "egyptian": "EG", "libyan": "LY", "burmese": "MM", "filipino": "PH",
            "thai": "TH", "chinese": "CN", "japanese": "JP", "ecuadorian": "EC", "peruvian": "PE", "chilean": "CL",
            "argentine": "AR", "cameroonian": "CM", "chadian": "TD", "nigerien": "NE", "mozambican": "MZ",
            "ukrainienne": "UA", "russe": "RU", "israelienne": "IL", "libanaise": "LB", "syrienne": "SY",
            "irakienne": "IQ", "malienne": "ML", "nigeriane": "NG", "congolaise": "CD", "mexicaine": "MX"}
_DEMONYM_PLACE_RE = re.compile(r"\b(" + "|".join(DEMONYMS) + r")\s+(?:city|town|village|region|province|oblast|state|capital|port|"
                               r"border town|district)\b|\b(?:ville|region|province|localite|capitale) (" + "|".join(DEMONYMS) + r")\b")


def demonym_place(title):
    """« Ukrainian city of Oleshky », « la ville ukrainienne de… » : pays du lieu (v0.28)."""
    m = _DEMONYM_PLACE_RE.search(norm(title))
    return DEMONYMS.get(m.group(1) or m.group(2)) if m else None


def strip_media(text):
    """Retire les noms de médias (« New York Times », « Times of Israel », « 京都新聞 », « جريدة المدينة ») avant la
    géolocalisation (v0.28)."""
    return _MEDIA_SCRIPT_RE.sub(" ", _MEDIA_RE.sub(" ", text or ""))


_MEDIA_SCRIPT_RE = re.compile(r"[\u4e00-\u9fff]{1,4}(?:新聞|新闻|日報|日报|時報|时报)|（[^）]{0,30}(?:NEWS|新聞|ニュース)[^）]{0,30}）|"
                              r"(?:جريدة|صحيفة|موقع|قناة)\s+\S+")


def _extra_country_aliases():
    return {"usa": "US", "etats-unis": "US", "uk": "GB", "royaume-uni": "GB",
            "britain": "GB", "rdc": "CD", "drc": "CD", "dr congo": "CD", "congo-kinshasa": "CD",
            "cote d'ivoire": "CI", "ivory coast": "CI", "burma": "MM", "birmanie": "MM", "gaza": "PS",
            "cisjordanie": "PS", "west bank": "PS", "turkiye": "TR", "russie": "RU", "ukraine": "UA",
            "centrafrique": "CF", "soudan du sud": "SS", "coree du nord": "KP", "north korea": "KP",
            "south korea": "KR", "coree du sud": "KR", "taiwan": "TW", "kosovo": "XK",
            **{s: "US" for s in US_STATES}}


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
