"""The Wikidata queries behind each category: which items a question can be about, and the
facts its clues are built from. Each returns one row per combination of facts; wikidata.group
gathers them per item. ?links (how many Wikipedias cover the item) measures how well known
it is, which sets the difficulty."""

EN = 'FILTER(LANG({}) = "en")'


def label(var):
    return f"{var} rdfs:label {var}Label . {EN.format(var + 'Label')}"


def optional_label(var, prop, subject="?item"):
    return f"OPTIONAL {{ {subject} wdt:{prop} {var} . {label(var)} }}"


def works(classes, min_links, facts, extra=""):
    """Items of the given classes with a label, how well known they are, and optional facts."""
    values = " ".join(f"wd:{c}" for c in classes)
    return f"""SELECT * WHERE {{
  VALUES ?class {{ {values} }}
  ?item wdt:P31 ?class ; wikibase:sitelinks ?links .
  FILTER(?links >= {min_links})
  {label('?item')}
  {extra}
  {facts}
}}"""


QUERIES = {
    # ---- tier 1 and 2 top-ups ----
    "books": works(["Q7725634", "Q8261", "Q571", "Q47461344"], 12,
        f"?item wdt:P50 ?author . {label('?author')} "
        "OPTIONAL { ?item wdt:P577 ?date } "
        "OPTIONAL { ?author wdt:P27 ?nation . ?nation wdt:P1549 ?nationality . FILTER(LANG(?nationality) = 'en') }"),
    "video_games": works(["Q7889"], 15,
        f"?item wdt:P178 ?developer . {label('?developer')} "
        "OPTIONAL { ?item wdt:P577 ?date } "
        + optional_label("?series", "P179") + optional_label("?publisher", "P123")),
    "battles": works(["Q178561"], 20,
        f"?item wdt:P361 ?war . ?war wdt:P31/wdt:P279* wd:Q198 . {label('?war')} "
        "OPTIONAL { ?item wdt:P585 ?date } "
        + optional_label("?country", "P17")),
    "wars": works(["Q198", "Q103495", "Q8465", "Q1361229"], 25,
        "?item wdt:P580 ?start . OPTIONAL { ?item wdt:P582 ?end } "
        + optional_label("?location", "P276")),
    "countries": works(["Q3624078"], 50,
        f"?item wdt:P36 ?capital . {label('?capital')} "
        + optional_label("?continent", "P30") + optional_label("?currency", "P38")
        + optional_label("?language", "P37")),
    "cities": works(["Q515", "Q1637706", "Q200250"], 40,
        f"?item wdt:P17 ?country . {label('?country')} "
        "OPTIONAL { ?item wdt:P1082 ?population } "
        + optional_label("?river", "P206")),
    "programming_languages": works(["Q9143", "Q28922885", "Q12772052"], 12,
        "OPTIONAL { ?item wdt:P571 ?date } "
        + optional_label("?designer", "P287") + optional_label("?developer", "P178")),
    "operating_systems": works(["Q9135", "Q14656"], 12,
        f"?item wdt:P178 ?developer . {label('?developer')} OPTIONAL {{ ?item wdt:P571 ?date }}"),
    "tech_companies": works(["Q4830453", "Q891723", "Q6881511"], 40,
        "?item wdt:P452 ?industry . VALUES ?industry { wd:Q11661 wd:Q880371 wd:Q638608 wd:Q1438053 wd:Q2283 } "
        "OPTIONAL { ?item wdt:P571 ?date } "
        + optional_label("?founder", "P112") + optional_label("?hq", "P159")),
    "software": works(["Q7397", "Q166142", "Q1639024", "Q35127"], 30,
        f"?item wdt:P178 ?developer . {label('?developer')} OPTIONAL {{ ?item wdt:P571 ?date }}"),
    "computer_scientists": """SELECT * WHERE {
  ?item wdt:P166 wd:Q185667 ; wikibase:sitelinks ?links .
  """ + label("?item") + """
  OPTIONAL { ?item p:P166 ?award . ?award ps:P166 wd:Q185667 ; pq:P585 ?date }
  OPTIONAL { ?item wdt:P27 ?nation . ?nation wdt:P1549 ?nationality . FILTER(LANG(?nationality) = 'en') }
}""",
    "anime": works(["Q63952888", "Q20650540", "Q1107"], 8,
        "OPTIONAL { ?item wdt:P580 ?date } OPTIONAL { ?item wdt:P577 ?date } "
        + optional_label("?studio", "P272") + optional_label("?director", "P57")
        + optional_label("?basedon", "P144")),
    "manga": works(["Q21198342", "Q8274"], 8,
        f"?item wdt:P50 ?author . {label('?author')} "
        "OPTIONAL { ?item wdt:P580 ?date } OPTIONAL { ?item wdt:P577 ?date } "
        + optional_label("?magazine", "P1433")),
    # Animals in two light steps (one heavy query times out): well-known species first...
    "animals": """SELECT * WHERE {
  ?item wdt:P105 wd:Q7432 ; wikibase:sitelinks ?links .
  FILTER(?links >= 60)
  ?item wdt:P1843 ?common . FILTER(LANG(?common) = "en")
  """ + label("?item") + """
  OPTIONAL { ?item wdt:P141 ?status . ?status rdfs:label ?statusLabel . FILTER(LANG(?statusLabel) = "en") }
}""",
    # ...then which big group (mammals, birds, reptiles…) each belongs to, one group at a time
    **{f"animal_group_{qid}": f"""SELECT ?item WHERE {{
  ?item wdt:P105 wd:Q7432 ; wikibase:sitelinks ?links .
  FILTER(?links >= 60)
  ?item wdt:P171+ wd:{qid} .
}}""" for qid in ["Q7377", "Q5113", "Q10811", "Q10908"]},  # mammals, birds, reptiles, amphibians
    # Computers: languages, systems, programs, file formats, companies and people
    "computer_software": works(["Q6368", "Q193564", "Q176165", "Q522972", "Q235557", "Q4182287", "Q3220391", "Q35127",
                                "Q7397", "Q166142", "Q1639024", "Q9135"], 20,
        "OPTIONAL { ?item wdt:P571 ?date } OPTIONAL { ?item wdt:P577 ?date } "
        + optional_label("?developer", "P178") + optional_label("?owner", "P127") + optional_label("?founder", "P112")),
    "tech_companies_all": """SELECT * WHERE {
  ?item wdt:P31/wdt:P279* wd:Q4830453 ; wdt:P452 ?industry ; wikibase:sitelinks ?links .
  FILTER(?links >= 35)
  ?industry rdfs:label ?industryLabel . FILTER(LANG(?industryLabel) = "en")
  FILTER(REGEX(?industryLabel, "software|computer|internet|semiconductor|information technology|video game|electronics|telecommunication", "i"))
  """ + label("?item") + """
  OPTIONAL { ?item wdt:P571 ?date }
  OPTIONAL { ?item wdt:P112 ?founder . ?founder rdfs:label ?founderLabel . FILTER(LANG(?founderLabel) = "en") }
  OPTIONAL { ?item wdt:P159 ?hq . ?hq rdfs:label ?hqLabel . FILTER(LANG(?hqLabel) = "en") }
}""",
    "computer_people": """SELECT * WHERE {
  VALUES ?job { wd:Q82594 wd:Q5482740 }  # computer scientist, programmer
  ?item wdt:P106 ?job ; wikibase:sitelinks ?links .
  FILTER(?links >= 30)
  """ + label("?item") + """
  ?item wdt:P800 ?work . ?work rdfs:label ?workLabel . FILTER(LANG(?workLabel) = "en")
  OPTIONAL { ?item wdt:P569 ?born }
  OPTIONAL { ?item wdt:P27 ?nation . ?nation wdt:P1549 ?nationality . FILTER(LANG(?nationality) = 'en') }
}""",
    # ---- tier 3 ----
    "deities": """SELECT * WHERE {
  ?item wdt:P31 ?class ; wikibase:sitelinks ?links .
  ?class wdt:P279* wd:Q178885 .
  FILTER(?links >= 8)
  """ + label("?item") + label("?class") + """
  OPTIONAL { ?item wdt:P2925 ?domain . ?domain rdfs:label ?domainLabel . FILTER(LANG(?domainLabel) = 'en') }
  OPTIONAL { ?item wdt:P22 ?father . ?father rdfs:label ?fatherLabel . FILTER(LANG(?fatherLabel) = 'en') }
  OPTIONAL { ?item wdt:P26 ?spouse . ?spouse rdfs:label ?spouseLabel . FILTER(LANG(?spouseLabel) = 'en') }
  OPTIONAL { ?item schema:description ?description . FILTER(LANG(?description) = 'en') }
}""",
    "paintings": works(["Q3305213"], 10,
        f"?item wdt:P170 ?artist . {label('?artist')} "
        "OPTIONAL { ?item wdt:P571 ?date } "
        + optional_label("?collection", "P195") + optional_label("?movement", "P135")
        + "OPTIONAL { ?artist wdt:P27 ?nation . ?nation wdt:P1549 ?nationality . FILTER(LANG(?nationality) = 'en') }"),
    # Heads of state and government, starting from the offices each country names as its own
    # (searching every kind of office times out)
    "leaders": """SELECT * WHERE {
  ?country wdt:P31 wd:Q6256 .
  { ?country wdt:P1906 ?position } UNION { ?country wdt:P1313 ?position }
  ?item p:P39 ?held ; wikibase:sitelinks ?links .
  ?held ps:P39 ?position .
  FILTER(?links >= 30)
  """ + label("?item") + label("?position") + label("?country") + """
  OPTIONAL { ?held pq:P580 ?start } OPTIONAL { ?held pq:P582 ?end }
  OPTIONAL { ?item wdt:P102 ?party . ?party rdfs:label ?partyLabel . FILTER(LANG(?partyLabel) = "en") }
}""",
    "mathematicians": """SELECT * WHERE {
  ?item wdt:P106 wd:Q170790 ; wikibase:sitelinks ?links .
  FILTER(?links >= 35)
  """ + label("?item") + """
  OPTIONAL { ?item wdt:P569 ?born }
  OPTIONAL { ?item wdt:P27 ?nation . ?nation wdt:P1549 ?nationality . FILTER(LANG(?nationality) = 'en') }
  OPTIONAL { ?item wdt:P800 ?work . ?work rdfs:label ?workLabel . FILTER(LANG(?workLabel) = 'en') }
}""",
    "cartoons": works(["Q581714", "Q117467246"], 8,
        "OPTIONAL { ?item wdt:P580 ?date } "
        + optional_label("?creator", "P170") + optional_label("?network", "P449")
        + optional_label("?studio", "P272")),
    "comics_characters": works(["Q1114461", "Q15773347", "Q188784"], 10,
        "OPTIONAL { ?item wdt:P170 ?creator . ?creator rdfs:label ?creatorLabel . FILTER(LANG(?creatorLabel) = 'en') } "
        + optional_label("?publisher", "P123")
        + optional_label("?alias", "P1080")),
    "comics_series": works(["Q14406742", "Q1004", "Q867335"], 10,
        "OPTIONAL { ?item wdt:P577 ?date } OPTIONAL { ?item wdt:P580 ?date } "
        + optional_label("?publisher", "P123") + optional_label("?creator", "P170")),
    "cars": works(["Q3231690", "Q1420"], 10,
        f"?item wdt:P176 ?maker . {label('?maker')} "
        "OPTIONAL { ?item wdt:P571 ?date } OPTIONAL { ?item wdt:P729 ?date } "
        "OPTIONAL { ?maker wdt:P17 ?makerCountry . ?makerCountry rdfs:label ?makerCountryLabel . FILTER(LANG(?makerCountryLabel) = 'en') }"),
    # ---- tier 4 ----
    "board_games": works(["Q131436", "Q142714", "Q11410"], 3,
        "OPTIONAL { ?item wdt:P577 ?date } "
        + optional_label("?designer", "P287") + optional_label("?publisher", "P123")
        + "OPTIONAL { ?item wdt:P1872 ?minPlayers } OPTIONAL { ?item wdt:P1873 ?maxPlayers }"),
    "musicals": works(["Q58483083", "Q2743", "Q1344"], 5,
        f"?item wdt:P86 ?composer . {label('?composer')} "
        "OPTIONAL { ?item wdt:P1191 ?date } OPTIONAL { ?item wdt:P577 ?date } "
        + optional_label("?lyricist", "P676") + optional_label("?basedon", "P144")),
    "gadgets": works(["Q19723451", "Q8076", "Q4931066", "Q155972", "Q15401633"], 6,
        f"?item wdt:P176 ?maker . {label('?maker')} "
        "OPTIONAL { ?item wdt:P577 ?date } OPTIONAL { ?item wdt:P571 ?date } "
        + optional_label("?os", "P306")),
}
