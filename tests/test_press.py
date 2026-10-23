"""Tri des titres de presse (veille/press.py) : catégorie, gravité, faux positifs connus.

Chaque cas correspond à une erreur réellement observée en production : ne pas supprimer un cas sans raison.
"""
import csv
from pathlib import Path

import pytest

from veille import press

GARDER = [
    ("Suicide bombing kills 12 at market in Mogadishu", "terrorism"),   # bug corrigé à l'audit v0.17
    ("Attentat-suicide contre une église à Damas", "terrorism"),
    ("Gunmen kill 5 in attack on village in Niger", "attack"),
    ("Earthquake of magnitude 6.2 strikes Turkey", "earthquake"),
    ("Protesters clash with police in Nairobi", "unrest"),
]
ECARTER = [
    "Assassinat de Johnnay à Champigny : la défense tente de torpiller l'enquête",   # procès, pas un attentat
    "Un adolescent se suicide après du harcèlement",                                   # drame privé
    "Football: PSG beat Marseille",
    "Bomberos apagan un incendio en Madrid",                                           # « bomb » ≠ « bomberos »
]


@pytest.mark.parametrize("titre,categorie", GARDER)
def test_titres_retenus(titre, categorie):
    cat, sev = press.classify(titre)
    assert cat == categorie
    assert 1 <= sev <= 4


@pytest.mark.parametrize("titre", ECARTER)
def test_titres_ecartes(titre):
    cat, _ = press.classify(titre)
    assert cat is None or press.not_incident(titre, cat)


def test_gravite_selon_bilan():
    _, sev = press.classify("Suicide bombing kills 60 at market in Mogadishu")
    assert sev == 4


def test_langue():
    assert press.guess_lang("Le gouvernement annonce des mesures") == "fr"
    assert press.guess_lang("The army said on Monday") == "en"


def test_jeu_etiquete_ne_regresse_pas():
    """Seuils minimaux sur tests/gold_tri.csv (voir tools/eval_tri.py). À relever quand le tri progresse."""
    rows = list(csv.DictReader(open(Path(__file__).parent / "gold_tri.csv", encoding="utf-8")))
    tp = fp = fn = 0
    for r in rows:
        want = r["garder"].strip() == "1"
        cat, _ = press.classify(r["titre"])
        got = press.is_event(r["titre"], cat)
        tp += want and got
        fp += got and not want
        fn += want and not got
    precision, rappel = tp / max(1, tp + fp), tp / max(1, tp + fn)
    assert precision >= 0.94, f"précision {precision:.0%}"   # v0.28 : 95 % sur 641 titres (v0.23 : 94 %, v0.22 : 51 %)
    assert rappel >= 0.98, f"rappel {rappel:.0%}"


# ------------------------------------------------------------------ contexte : Fil, pas carte (v0.23)
# Un « événement » doit pouvoir toucher physiquement un voyageur ou un site. Cas réels relevés en production.
CONTEXTE = [
    ("Detienen en Lerma a dos hombres y una menor por presunto secuestro y extorsión", "arrestation ou suites"),
    ("Saint-Louis. Menace d'attentat dans son lycée : l'élève de 16 ans a voulu faire une « blague »", "projet déjoué"),
    ("OIC, Arab states condemn drone attack on Saudi Arabia's Medina power station", "déclaration"),
    ("Saudi Arabia rejects Houthi claim of attack on Riyadh", "déclaration"),
    ("Seattle police chief resigns in wake of deadly food festival shooting: Mayor", "déclaration"),
    ("100 anni fa l'attentato a Mussolini a Bologna", "rétrospective ou démenti"),
    ("Pakistan Militant Attacks Hit 12-Year High in September", "analyse"),
    ("Attentato di Modena. Salim era sorvegliato? Scontro sugli 007", "analyse"),
    ("Ariana : 100 MD pour protéger les villes contre les inondations", "prévention, bilan ou suites"),
]
EVENEMENTS = [   # faux rejets corrigés en v0.23
    "Three people transported to hospital after downtown Las Vegas shooting, police say",   # victimes, pas une arrestation
    "The Sudanese Armed Forces (SAF) repelled an attack by the Rapid Support Forces (RSF)",    # « Support Forces »
    "Le Yémen affirme avoir mené des centaines de frappes contre les Houthis",               # annonce d'un fait
    "Ukraine latest: Kyiv bridge hit in Russian air strike as Moscow vows retaliation",
    "Ataque armado en la colonia 5 de Febrero deja un muerto y dos heridos en Culiacán",     # 1 + 2 victimes
    "Matan a juez de paz del municipio de Mazatepec, Morelos en ataque armado",              # cible publique
    "Reportan ataque armado en secundaria de Torreón",
    "Flash Floods Damage Section Of East-West Road, Delta Residents Seek Urgent Intervention",
    "Feuer unter Stromleitungen in Berlin - Anschlag?",                                     # question, mais feu constaté
    "Kathua shooting: CISF Head Constable kills 4 colleagues in Jammu and Kashmir",          # « kills 4 »
    "Israeli strike kills 2 Christian women, lecturer, her mother in new Gaza ceasefire breach",
]


@pytest.mark.parametrize("titre,motif", CONTEXTE)
def test_titres_de_contexte(titre, motif):
    cat, _ = press.classify(titre)
    assert cat and press.context(titre, cat) == motif and not press.is_event(titre, cat)


@pytest.mark.parametrize("titre", EVENEMENTS)
def test_evenements_physiques_gardes(titre):
    cat, _ = press.classify(titre)
    assert press.is_event(titre, cat), (cat, press.not_incident(titre, cat), press.context(titre, cat) if cat else None)


def test_violence_electorale_n_est_pas_un_signal_diplomatique():
    t = "Elecciones 2026 bajo tensión: reportan DISPAROS y ánforas incendiadas en Loreto y Áncash"
    assert press.classify(t)[0] == "unrest" and press.is_event(t, "unrest")


def test_bilan_additionne_morts_et_blesses():
    assert press.casualty_toll(press.norm("deja un muerto y dos heridos")) == 3
    assert press.casualty_toll(press.norm("gunman kills 4 colleagues")) == 4
    assert press.casualty_toll(press.norm("attack in 2026 leaves people worried")) == 0


def test_gdelt_titre_reel_de_l_article():
    """GDELT : la catégorie vient d'un code, le titre réel de l'article dit souvent autre chose."""
    assert press.gdelt_noise("Megyn Kelly Melts Down at 'SVU' Star in Unhinged Rant") == "hors sujet"
    assert press.gdelt_noise("Explainer: Who are the Houthis, Iran") == "hors sujet"
    assert press.gdelt_noise("Retired Major Gen Golam Mohiuddin arrested over attack on New Gini Properties")
    assert press.gdelt_noise("Israeli forces shell village in southern Syria") is None
    assert press.gdelt_noise("Flames, Smoke Reported at Aramco Facility South of Saudi Capital") is None
    assert press.gdelt_noise("Russian attacks kill 6 in Ukraine and damage Kyiv's Northern Bridge") is None
    assert press.gdelt_noise("") is None


def test_contexte_dans_le_fil_pas_sur_la_carte():
    from datetime import datetime, timezone
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    items = [{"title": t, "url": f"https://x/{i}", "outlet": "X", "date": now, "country_hint": "MX", "lang": "es"}
             for i, t in enumerate(["Detienen en Lerma a dos hombres por presunto secuestro y extorsión en Toluca",
                                    "Ataque armado en Culiacán deja tres muertos"])]
    events, news, _ = press.build(items, [], {}, lambda m: None, now)
    assert len(news) == 2 and [n.get("context") for n in news] == ["arrestation ou suites", None]
    assert all("Detienen" not in e["title"] for e in events)


# ------------------------------------------------------------------ 35 langues supplémentaires (v0.25)
MULTI_GARDER = [
    ("Skottlossning i Malmö – två döda", "attack"),
    ("Skyderi i København: tre dræbte", "attack"),
    ("Lövöldözés Budapesten, két halott", "attack"),
    ("Explozie la un bloc din București: 3 morți și 10 răniți", "attack"),
    ("Poplave u Bosni: poginulo 5 osoba", "flood"),
    ("Σεισμός 5,2 Ρίχτερ στην Κρήτη", "earthquake"),
    ("Lũ lụt ở miền Trung, 12 người thiệt mạng", "flood"),
    ("地震 震度6強 死者5人", "earthquake"),
    ("भूकंप के झटके, 3 की मौत", "earthquake"),
    ("Shambulio la al-Shabaab laua watu 10 Mandera, wameuawa", "terrorism"),
    ("Взрыв в Белгороде: три человека погибли", "infrastructure"),
    ("Protest în Piața Victoriei", "unrest"),
    ("Coup d’État au Niger : la junte suspend la Constitution", "political"),   # apostrophe typographique
]
MULTI_ECARTER = [
    "Fotbal: Steaua câștigă meciul",
    "AFAD Duyurdu: Muğla Açıklarında Deprem Oldu!",      # « oldu » (turc) ≠ « öldü » (azéri)
    "Remont dróg w Krakowie",                             # « drog » n'est pas un mot de la drogue en polonais
    "Il sindaco di Roma: la vita in città",               # « vita » (vie) ≠ swahili « vita » (guerre)
    "Kun.uz: Toshkentda kuchli zilzila",                  # séisme sans magnitude ni dégâts : couvert par les capteurs
]


@pytest.mark.parametrize("titre,categorie", MULTI_GARDER)
def test_langues_ajoutees_retenues(titre, categorie):
    cat, _ = press.classify(titre)
    assert cat == categorie and press.is_event(titre, cat)


@pytest.mark.parametrize("titre", MULTI_ECARTER)
def test_langues_ajoutees_ecartees(titre):
    cat, _ = press.classify(titre)
    assert not press.is_event(titre, cat)


def test_requetes_et_editions_des_langues_ajoutees():
    from veille import langs
    from veille.connectors import gnews, outlets
    for lg in langs.LANGS:
        assert gnews.TERMS["security"][lg] and outlets.LANG_EDITION[lg] in gnews.EDITIONS, lg
    assert gnews.EDITIONS["ja-JP"] == ("ja", "JP", "JP:ja", "ja") and outlets.LANG_EDITION["sw"] == "en-US"


# ------------------------------------------------------------------ audit de la production (v0.28)
# 34 faux positifs relevés sur 7 jours d'angor.fr (octobre 2026) : chacun a donné une règle.
AUDIT_CONTEXTE = [
    ("Rains expected in Nairobi, across Kenya as Met warns of flash floods", "prévision"),
    ("Potensi Longsor dan Banjir Bandang di Kabupaten Bandung, 25 Kecamatan Masuk Kategori Menengah", "prévision"),
    ("Weather system over Bay of Bengal may intensify into cyclone, cross Odisha-Andhra coasts by Friday", "prévision"),
    ("Avant les pluies, Bizerte teste son dispositif contre les inondations", "prévention, bilan ou suites"),
    ("For Timure’s flood survivors, Dashain brings memories of the lives they lost", "prévention, bilan ou suites"),
    ("Ebola : le Nigeria renforce les contrôles sanitaires à l’aéroport de Lagos", "prévention, bilan ou suites"),
    ("Grenoble. Après les émeutes, l’incompréhension et l’inquiétude des sapeurs-pompiers", "prévention, bilan ou suites"),
    ("TÉMOIGNAGE. «La justice la présente comme une terroriste» : sa compagne, ex-professeure en Anjou, est détenue",
     "analyse"),
    ("Sri Lankan terrorism police summon Tamil National Cultural Council president in Jaffna", "arrestation ou suites"),
    ("Russia and Ukraine agreed to ceasefire in occupied Oleshky, White House says", "cessez-le-feu (annonce)"),
    ("Netanyahu Warns Iran Against Attack Ahead of Israeli Election", "déclaration"),
    ("Juanma Moreno tras el último ataque del narco: «Se repite día tras día en Andalucía; basta ya»", "déclaration"),
    ("حكومة السودان تنفي علاقة الجيش بقصف سوق النعام في أبيي", "déclaration"),
    ("NOW: Initial reports of a ballistic missile launch from Razavi Khorasan, Iran This is likely a test originating",
     "annonce militaire"),
]
AUDIT_BRUIT = [
    "Bénin : le Port de Cotonou généralise les opérations d’enlèvement sept jours sur sept",   # marchandises
    "Raw sewage floods this Durban main road",
    "Investigan tiroteo en el que estuvieron involucrados policías de Monterey Park",
    "Manhunt launched for Gauteng pastor over alleged rape, kidnapping and murder",
    "Haridwar News: नाबालिग के अपहरण, हत्या की धमकी के आरोप में रिपोर्ट दर्ज",
]
AUDIT_GARDER = [
    ("Worshippers killed in shooting at church in Jordan", "attack"),
    ("Gran Concepción: comunas reportan inundaciones y calles anegadas por intensas lluvias", "flood"),
    ("Russian forces attack gas station in Sumy, injuring two employees", "attack"),
    ("Taiwan shuts down as Typhoon Champi approaches", "cyclone"),
    ("Lycées piratés au Luxembourg: Les élèves sommés de changer leur mot de passe IAM", "cyber"),
    ("Grenoble : des affrontements lors du blocage d'un lycée, la police intervient", "unrest"),
    ("Kementerian PU: banjir rendam 3 kecamatan di Kota Padang, ribuan warga mengungsi", "flood"),
]


@pytest.mark.parametrize("titre,motif", AUDIT_CONTEXTE)
def test_audit_contexte(titre, motif):
    cat, _ = press.classify(titre)
    assert cat and not press.not_incident(titre, cat)
    assert press.context(titre, cat) == motif


@pytest.mark.parametrize("titre", AUDIT_BRUIT)
def test_audit_bruit(titre):
    cat, _ = press.classify(titre)
    assert cat is None or press.not_incident(titre, cat)


@pytest.mark.parametrize("titre,categorie", AUDIT_GARDER)
def test_audit_faits_gardes(titre, categorie):
    cat, _ = press.classify(titre)
    assert cat == categorie
    assert press.is_event(titre, cat)


def test_bruit_local_explicite():
    assert press.not_incident("Raw sewage floods this Durban main road", "flood") == "pollution locale"
    assert press.not_incident("Manhunt launched for Gauteng pastor over alleged rape", "crime") == "personne recherchée"


# ------------------------------------------------------------------ localisation (v0.28), avec le dictionnaire GeoNames
@pytest.fixture(scope="module")
def gaz():
    if not (press.GEONAMES_DIR / "cities15000.txt").exists():
        pytest.skip("dictionnaire GeoNames absent (téléchargé à la première collecte)")
    from veille import geo
    return press.Gazetteer(geo.Countries(), lambda *_: None).load()


@pytest.mark.parametrize("titre,indice,langue,pays,lieu", [
    ("One person killed in shooting near Paris, French Prime Minister says", "US", "en", "FR", "Paris"),   # flux US
    ("约旦河西岸发生袭击事件致2死5伤", "CN", "zh", "PS", None),               # Cisjordanie, pas la Chine
    ("水利部对4省份启动洪水防御Ⅳ级应急响应", "CN", "zh", "CN", None),          # pas un village homonyme au hasard
    ("Melania Trump 'secured ceasefire' in Ukrainian city of Oleshky: White House", "MA", "en", "UA", None),
    ("BBC, The New York Times, The Guardian and Al Jazeera report on settler violence", "US", "en", "US", None),
    ("Lycées piratés au Luxembourg: Les élèves sommés de changer leur mot de passe", "LU", "fr", "LU", "Luxembourg"),
])
def test_localisation_audit(gaz, titre, indice, langue, pays, lieu):
    cat, _ = press.classify(titre)
    loc = gaz.locate(titre, indice, cat, langue)
    assert loc["country"] == pays
    assert loc.get("place") == lieu


def test_noms_de_medias_et_demonymes():
    assert "york" not in press.strip_media("The New York Times reports").lower()
    assert press.demonym_place("in Ukrainian city of Oleshky") == "UA"


# ------------------------------------------------------------------ second audit de la production (v0.28, run 2)
# 931 titres de la carte du 23 octobre 2026 : 277 faux positifs (30 %), ramenés à 7. Un cas par règle.
AUDIT2_CONTEXTE = [
    "Oregon elementary school shooting victims remembered",                                          # hommage
    "A shattered community awaits answers, motive in Bend school shooting",
    "Gun used in Oregon elementary school shooting was birthday gift from shooter's mom, sources say",
    "El juez propone juzgar a otros cuatro exjefes de ETA por el atentado mortal de Santa Pola de 2002",
    "#ÚLTIMAHORA | Por el secuestro y el asesinato del hijo del expresidente capturamos a sujeto en La Ceiba",
    "Les États-Unis pourraient frapper l'Iran dès ce week-end, avance un diplomate américain",       # menace
    "Comment la manifestation a dégénéré en émeutes urbaines dans le centre-ville de Chambéry",       # analyse
    "What sparked the fiery protests in France – and how they could spread across Europe",
    "Strikes on Civilian Infrastructure in Ukraine and Russia: Oct. 14-15, 2026 CIT Volunteer Summary",
    "Iran has a new defense minister. Mehrdad Akhlaghi was confirmed Sunday with 237 votes, replacing Aziz Nasirzadeh, killed in February's opening strike on Tehran.",
    "Danmark kjøper langtrekkende JSM-missiler fra Kongsberg",                                        # militaire
    "Recomendaciones del Acueducto para evitar inundaciones en Bogotá",                               # prévention
    "Alanya kırsalında sel riskine karşı dört bölgede çalışma",
    "Nach Rekordhochwasser 2024: Wien rüstet Wienfluss auch für 5.000-jährige Hochwasser",
    "Nigeria: Ebola - Kano, Niger, Kaduna, Plateau, Kogi, Nasarawa Adopt Preventive Measures",
    "Nord-Kivu : Beni lance la vaccination contre Ebola avec le vaccin Ervebo",
    "Ante un sismo simulado, Manizales evaluó cómo responder a viviendas colapsadas, heridos y vías bloqueadas",
    "Kenya: 'No Ebola Billionaires' Says Duale",
    "Gobierno de Canadá descarta atentado terrorista tras incendio en zona de entrenamiento militar de Alberta",
]
AUDIT2_BRUIT = [
    "2027: Posters, banners flood Kaduna as residents lament economic hardship",                    # métaphore
    "Inside Chicago's battle against the synthetic drugs flooding the US",
    "JSP predicts landslide victory in Srikakulam mayoral poll",
    "بحبح وبدر موسى يقودان هجوم السويس بتروجت أمام سيراميكا",                                      # football
    "Investigado por homicídio e tráfico de drogas morre após confronto em Itabaiana",              # police
    "À Montpellier, la dispute entre deux frères de 60 et 63 ans dégénère : l'aîné poignarde le cadet",
    "Ariel Gutiérrez lleva a la pantalla el secuestro de su madre",                                  # culture
    "神奈川県で最大震度1の地震 神奈川県・小田原市",                                                  # séisme faible
    "Videos de lluvias e inundaciones en la región peruana de Piura son de febrero de 2026, no de octubre",
    "Hunedoara: Minerii de la Vulcan au obținut primele promisiuni după protest",
    "Iran will treat American and Israeli targets as legitimate if Trump backs any attack Netanyahu launches against the country, a senior Iranian official told Lebanon's Al…",
]
AUDIT2_GARDER = [
    ("Thousands flood Athens streets in education protest", "unrest"),
    ("Protest la Mina Vulcan din Valea Jiului: zeci de mineri nemulțumiți de salarii au refuzat să iasă", "unrest"),
    ("Russian forces strike energy facility in Ternopil region", "armed_conflict"),
    ("Vito Quiles en Zaragoza: cargas policiales, disturbios y enfrentamientos en el Campus San Francisco", "unrest"),
    ("Burnt-out wreck: Ukraine destroys Smerch rocket artillery system that terrorised Kherson", "armed_conflict"),
    ("Thousands evacuated amid Bangkok floods", "flood"),
    ("Masisi : l'AFC/M23 reprend Remeka et attaque les positions des FARDC à Kaleta", "attack"),
    ("Blocage des lycées : deux départs de feu dans un établissement à Poitiers, le rectorat appelle au calme", "unrest"),
    ("Troops kill two suspected kidnappers, rescue victim, recover ransom in Kano – Official", "armed_conflict"),
    ("Japan Earthquake LIVE Updates: 5.8 Magnitude Earthquake Jolts Japan, Injuries Reported", "earthquake"),
]


@pytest.mark.parametrize("titre", AUDIT2_CONTEXTE)
def test_audit2_contexte(titre):
    cat, _ = press.classify(titre)
    assert cat and not press.not_incident(titre, cat) and press.context(titre, cat), (cat, titre)


@pytest.mark.parametrize("titre", AUDIT2_BRUIT)
def test_audit2_bruit(titre):
    cat, _ = press.classify(titre)
    assert cat is None or press.not_incident(titre, cat) or press.context(titre, cat)


@pytest.mark.parametrize("titre,categorie", AUDIT2_GARDER)
def test_audit2_faits_gardes(titre, categorie):
    cat, _ = press.classify(titre)
    assert cat == categorie and press.is_event(titre, cat), (cat, titre)


@pytest.mark.parametrize("titre,indice,pays,lieu", [
    ("França investiga tiroteio em Paris como ataque terrorista", "BR", "FR", "Paris"),      # noms de pays en portugais
    ("A capital da Ucrânia foi alvo de um novo ataque com mísseis esta noite", "BR", "UA", None),
    ("One killed, four injured in drive-by shooting near Paris", "ZA", "FR", "Paris"),       # pas Parys
    ("Russia Hits Central Kyiv With Cluster Missile", "RU", "UA", "Kyiv"),                    # pays auteur
    ("Hyderabad man killed in Riyadh airport attack, two sons injured", "IN", "SA", "Riyadh"),  # ville d'origine
    ("Houthi attack on Riyadh airport disrupts 134 flights from Dhaka", "BD", "SA", "Riyadh"),
    ('"We\'re trying to do it like in France." In Albania, clashes with police for the fifth day', "FR", "AL", None),
    ("2 employees killed, 1 hurt in workplace shooting in Virginia; suspect dead", "ZA", "US", None),   # État américain
    ("Dois homens morreram após confronto, no bairro de Mata Escura, em Salvador", "BR", "BR", "Salvador"),
    ("وزير الداخلية الأردني مازن الفراية: ما حدث في الكرك عملية إرهابية", "ID", "JO", None),        # gentilé arabe
    ("法国外长谴责以色列定居者在约旦河西岸袭击法国官员", "CN", "PS", None),
    ("زلزال بقوة 5 درجات يضرب جنوب بنما - جريدة المدينة", "SA", "PA", None),                     # nom de journal
    ("Romania Blames Russia for Drone Strike That Sank Black Sea Ship", "RO", "RO", None),
])
def test_localisation_audit2(gaz, titre, indice, pays, lieu):
    cat, _ = press.classify(titre)
    loc = gaz.locate(titre, indice, cat or "attack", press.guess_lang(titre))
    assert loc["country"] == pays
    if lieu:
        assert loc.get("place") == lieu


def test_noms_de_pays_multilingues():
    names = press._cldr_country_names()
    assert names["ucrania"] == "UA" and names["arnavutluk"] == "AL" and names["frankreich"] == "FR"
    for ambigu in ("island", "indie", "mali", "peru", "salvador", "israeli", "somali"):   # mots courants, gentilés
        assert ambigu not in names
