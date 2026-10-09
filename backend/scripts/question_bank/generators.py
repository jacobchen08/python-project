"""Turning Wikidata facts into questions that don't read like a form.

Each generator returns candidate questions for one category. Every item can be asked about
in several ways (who made it, when, where, the reverse "which of these…", true or false),
each with a few phrasings, and clues combine two or three facts ("Rembrandt's 1642 painting
in the Rijksmuseum…") rather than asking one bare fact. Wrong answers come from the same
kind of thing, preferring close ones (same country, nearby years), so they're plausible.
How well known an item is (how many Wikipedias cover it) sets easy, medium or hard.
"""

import re

from common import decade_options, make_question, new_rng, pick, similar, year_options
from queries import QUERIES
from wikidata import group, one, query, usable_label, year

STANDARD_CONTINENTS = {"Africa", "Asia", "Europe", "North America", "South America", "Oceania", "Antarctica"}


# ---------- helpers ----------

def load(name):
    """The items of a query, each as a dict of facts, keeping only ones with a readable name."""
    items = []
    for qid, facts in group(query(name, QUERIES[name])).items():
        title = one(facts, "itemLabel")
        if not usable_label(title) or "�" in title:
            continue
        facts["qid"], facts["title"] = qid, title
        facts["fame"] = max(int(v) for v in facts.get("links", {"0"}))
        items.append(facts)
    return items


def text(facts, field):
    value = one(facts, field)
    return value if usable_label(value) and "�" not in value else None


# Wikidata's demonyms are sometimes nouns ("Briton"); these read as adjectives in a clue
DEMONYM_FIXES = {"Briton": "British", "Swede": "Swedish", "Dane": "Danish", "Pole": "Polish", "Finn": "Finnish",
                 "Spaniard": "Spanish", "Turk": "Turkish", "Scot": "Scottish", "Dutchman": "Dutch", "Englishman": "English",
                 "Irishman": "Irish", "Frenchman": "French", "Welshman": "Welsh", "Icelander": "Icelandic", "Swiss": "Swiss",
                 "Greek": "Greek", "Thai": "Thai", "Czech": "Czech", "Iraqi": "Iraqi", "Israeli": "Israeli", "Pakistani": "Pakistani"}
ADJECTIVE_ENDINGS = ("an", "ese", "ish", "ch", "ic", "i")


def adjective(facts, field="nationality"):
    """'American' rather than 'Americans', 'British' rather than 'Briton'; None if it won't read well."""
    for value in sorted(facts.get(field, ()), key=lambda v: (v.endswith("s"), len(v))):
        value = DEMONYM_FIXES.get(value, value)
        if value in DEMONYM_FIXES.values() or (value.endswith(ADJECTIVE_ENDINGS) and " " not in value):
            return value
    return None


NOT_AN_AUTHOR = {"various authors", "anonymous", "unknown", "anonymous work", "traditional"}


def candidate(category_id, item, question, correct, wrong, kind="multiple"):
    """A generated question, remembering which item it's about (to limit repeats per item)."""
    if kind == "multiple" and not wrong:
        return None
    q = make_question(category_id, question, correct, wrong, kind=kind)
    q["_item"], q["_fame"] = item["qid"], item["fame"]
    return q


def true_or_false(category_id, item, rng, statement_true, statement_false):
    """A true/false question, true or false at random, from two versions of the same claim."""
    if rng.random() < 0.5:
        return candidate(category_id, item, statement_true, "True", None, kind="boolean")
    return candidate(category_id, item, statement_false, "False", None, kind="boolean")


def quoted(title):
    return f"“{title}”"


# ---------- books (10) ----------

def books():
    rng, out = new_rng("books"), []
    items = [i for i in load("books") if text(i, "authorLabel") and text(i, "authorLabel").casefold() not in NOT_AN_AUTHOR]
    authors = sorted({text(i, "authorLabel") for i in items})
    profile = {}  # author -> (nationality, a year they published)
    for i in items:
        profile.setdefault(text(i, "authorLabel"), (adjective(i), year(i, "date")))
    for b in items:
        title, author, y, nat = quoted(b["title"]), text(b, "authorLabel"), year(b, "date"), adjective(b)
        others = similar(author, authors, rng, closeness=lambda a: (
            profile[a][0] != nat, abs((profile[a][1] or 1900) - (y or 1900)) // 25))
        if not others:
            continue
        if y and nat:
            q = pick(rng, f"Which {nat} writer published {title} in {y}?",
                     f"{title} first appeared in {y}. Which {nat} author wrote it?",
                     f"Name the {nat} author behind {title} ({y}).")
        elif y:
            q = pick(rng, f"Who wrote {title}, first published in {y}?", f"{title} ({y}) is the work of which writer?")
        else:
            q = pick(rng, f"Who is the author of {title}?", f"{title} was written by whom?")
        out.append(candidate(10, b, q, author, others))
        if y and y >= 1500:
            right, wrong = decade_options(y, rng)
            out.append(candidate(10, b, pick(rng, f"In which decade was {author}'s {title} first published?",
                                             f"{author} published {title} in which decade?"), right, wrong))
        not_by = [i["title"] for i in items if text(i, "authorLabel") != author]
        wrong_books = similar(b["title"], not_by, rng)
        if wrong_books:
            out.append(candidate(10, b, pick(rng, f"Which of these books did {author} write?",
                                             f"{author} is the author of which of these?"), quoted(b["title"]),
                                 [quoted(w) for w in wrong_books]))
    return out


# ---------- video games (15) ----------

def video_games():
    rng, out = new_rng("video_games"), []
    items = [i for i in load("video_games") if text(i, "developerLabel")]
    developers = sorted({text(i, "developerLabel") for i in items})
    active = {}  # developer -> a year they released something
    for i in items:
        active.setdefault(text(i, "developerLabel"), year(i, "date"))
    for g in items:
        title, dev, y = quoted(g["title"]), text(g, "developerLabel"), year(g, "date")
        series, publisher = text(g, "seriesLabel"), text(g, "publisherLabel")
        wrong_devs = similar(dev, developers, rng, closeness=lambda d: abs((active[d] or 2000) - (y or 2000)) // 5)
        if wrong_devs:
            if y and publisher and publisher != dev:
                q = pick(rng, f"Published by {publisher} in {y}, {title} was developed by which studio?",
                         f"Which studio developed {title}, released in {y} by {publisher}?")
            elif y:
                q = pick(rng, f"Which studio developed {title}, released in {y}?", f"{title} ({y}) came out of which development studio?")
            else:
                q = f"Which studio developed {title}?"
            out.append(candidate(15, g, q, dev, wrong_devs))
        if y:
            out.append(candidate(15, g, pick(rng, f"In what year was {title} first released?", f"{title} first came out in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng, spread=(1, 2, 3, 4, 5))]))
        if series and series.casefold() not in g["title"].casefold():
            all_series = sorted({text(i, "seriesLabel") for i in items if text(i, "seriesLabel")})
            wrong_series = similar(series, all_series, rng)
            if wrong_series:
                out.append(candidate(15, g, pick(rng, f"{title} is part of which game series?",
                                                 f"Which franchise does {title} belong to?"), series, wrong_series))
        others = [i["title"] for i in items if text(i, "developerLabel") != dev]
        wrong_games = similar(g["title"], others, rng)
        if wrong_games:
            out.append(candidate(15, g, pick(rng, f"Which of these games was developed by {dev}?",
                                             f"{dev} made which of these games?"), quoted(g["title"]), [quoted(w) for w in wrong_games]))
    return out


# ---------- history (23) ----------

def history():
    rng, out = new_rng("history"), []
    battles = [i for i in load("battles") if text(i, "warLabel")]
    wars = [i for i in load("wars") if year(i, "start")]
    war_names = sorted({text(i, "warLabel") for i in battles} | {i["title"] for i in wars})
    for b in battles:
        war, y, place = text(b, "warLabel"), year(b, "date"), text(b, "countryLabel")
        if war.casefold() in b["title"].casefold():
            continue
        wrong = similar(war, war_names, rng)
        if wrong:
            where = f" in {'the ' if place.startswith(('Kingdom', 'Republic', 'Empire', 'United', 'Duchy', 'Grand')) else ''}{place}" if place else ""
            when = f" in {y}" if y else ""
            q = pick(rng, f"The {b['title']}, fought{when}{where}, was part of which war?",
                     f"Which conflict included the {b['title']}{when}?")
            out.append(candidate(23, b, q, war, wrong))
        if y and y > 0:
            out.append(candidate(23, b, pick(rng, f"In what year was the {b['title']} fought?", f"The {b['title']} took place in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng)]))
    for w in wars:
        start, end, place = year(w, "start"), year(w, "end"), text(w, "locationLabel")
        if start and start > 0:
            if end and end >= start:
                out.append(candidate(23, w, pick(rng, f"The {w['title']} ended in {end}. In which year did it begin?",
                                                 f"Which year saw the start of the {w['title']}, which lasted until {end}?"),
                                     str(start), [str(v) for v in year_options(start, rng)]))
            else:
                right, wrong = decade_options(start, rng) if start >= 1000 else (None, None)
                if right:
                    out.append(candidate(23, w, f"In which decade did the {w['title']} begin?", right, wrong))
        if end and start and end > start and end - start < 40:
            claim = end - start
            fake = claim + rng.choice([-3, -2, 2, 3, 5])
            if fake > 0:
                out.append(true_or_false(23, w, rng, f"The {w['title']} lasted about {claim} years, from {start} to {end}.",
                                         f"The {w['title']} lasted about {fake} years, from {start} to {start + fake}."))
    return out


# ---------- geography (22) ----------

def geography():
    rng, out = new_rng("geography"), []
    countries = [c for c in load("countries") if text(c, "capitalLabel")]
    capitals = sorted({text(c, "capitalLabel") for c in countries})
    names = sorted({c["title"] for c in countries})
    for c in countries:
        name, capital = c["title"], text(c, "capitalLabel")
        continent = next((v for v in sorted(c.get("continentLabel", ())) if v in STANDARD_CONTINENTS), None)
        same_continent = lambda other: 0 if continent and continent in {
            v for x in countries if x["title"] == other for v in x.get("continentLabel", ())} else 1
        wrong = similar(capital, capitals, rng, closeness=lambda cap: same_continent(
            next((x["title"] for x in countries if text(x, "capitalLabel") == cap), "")))
        if wrong and capital.casefold() not in name.casefold():
            out.append(candidate(22, c, pick(rng, f"What is the capital of {name}?", f"Which city is the capital of {name}?",
                                             f"If you flew to the capital of {name}, where would you land?"), capital, wrong))
            out.append(candidate(22, c, pick(rng, f"{capital} is the capital of which country?",
                                             f"Which country is governed from {capital}?"), name,
                                 similar(name, names, rng, closeness=same_continent)))
        currency = text(c, "currencyLabel")
        currency = currency[0].upper() + currency[1:] if currency else None
        if currency and name.split()[0].casefold() not in currency.casefold():
            currencies = sorted({text(x, "currencyLabel")[0].upper() + text(x, "currencyLabel")[1:]
                                 for x in countries if text(x, "currencyLabel")})
            wrong_cur = similar(currency, currencies, rng)
            if wrong_cur:
                out.append(candidate(22, c, pick(rng, f"Which currency would you spend in {name}?",
                                                 f"What is the official currency of {name}?"), currency, wrong_cur))
        if continent and continent != "Antarctica":
            others = sorted(STANDARD_CONTINENTS - {continent, "Antarctica"})
            out.append(candidate(22, c, pick(rng, f"On which continent is {name}?", f"{name} lies on which continent?"),
                                 continent, rng.sample(others, 3)))
    cities = [c for c in load("cities") if text(c, "countryLabel")]
    city_countries = sorted({text(c, "countryLabel") for c in cities})
    continent_of = {c["title"]: next((v for v in sorted(c.get("continentLabel", ())) if v in STANDARD_CONTINENTS), None)
                    for c in countries}
    for city in cities:
        country, people = text(city, "countryLabel"), one(city, "population")
        if country.casefold() in city["title"].casefold():
            continue
        home = continent_of.get(country)
        wrong = similar(country, city_countries, rng, closeness=lambda other: continent_of.get(other) != home)
        if not wrong:
            continue
        river = text(city, "riverLabel")
        if river:
            q = pick(rng, f"The city of {city['title']}, on the {river}, is in which country?",
                     f"In which country would you find {city['title']}, which sits on the {river}?")
        elif people and people.isdigit() and int(people) >= 100000:
            q = pick(rng, f"{city['title']}, home to about {round(int(people), -4 if int(people) >= 1e6 else -3):,} people, is in which country?",
                     f"Which country is the city of {city['title']} in?")
        else:
            q = pick(rng, f"In which country is the city of {city['title']}?", f"{city['title']} is a city in which country?")
        out.append(candidate(22, city, q, country, wrong))
    return out


# ---------- anime and manga (31) ----------

def anime_manga():
    rng, out = new_rng("anime"), []
    shows = load("anime")
    studios = sorted({v for s in shows for v in s.get("studioLabel", ()) if usable_label(v)})
    directors = sorted({v for s in shows for v in s.get("directorLabel", ()) if usable_label(v)})
    for s in shows:
        title, y, studio, director = quoted(s["title"]), year(s, "date"), text(s, "studioLabel"), text(s, "directorLabel")
        if studio and len(s.get("studioLabel", ())) == 1:
            wrong = similar(studio, studios, rng)
            if wrong:
                clue = f" directed by {director}" if director else ""
                when = f" ({y})" if y else ""
                out.append(candidate(31, s, pick(rng, f"Which studio animated {title}{when}{clue}?",
                                                 f"{title}{when} was produced by which animation studio?"), studio, wrong))
        if director and len(s.get("directorLabel", ())) == 1:
            wrong = similar(director, directors, rng)
            if wrong:
                out.append(candidate(31, s, pick(rng, f"Who directed the anime {title}?", f"{title} was directed by whom?"), director, wrong))
        if y and y >= 1960:
            out.append(candidate(31, s, pick(rng, f"In what year did {title} first air or premiere?", f"{title} debuted in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng, spread=(1, 2, 3, 4, 6))]))
    mangas = [m for m in load("manga") if text(m, "authorLabel")]
    authors = sorted({text(m, "authorLabel") for m in mangas})
    magazines = sorted({text(m, "magazineLabel") for m in mangas if text(m, "magazineLabel")})
    for m in mangas:
        title, author, y, magazine = quoted(m["title"]), text(m, "authorLabel"), year(m, "date"), text(m, "magazineLabel")
        wrong = similar(author, authors, rng)
        if wrong:
            if magazine and y:
                q = pick(rng, f"Which manga artist created {title}, first serialised in {magazine} in {y}?",
                         f"{title} began in {magazine} in {y}. Who created it?")
            elif y:
                q = pick(rng, f"Who created the manga {title}, which began in {y}?", f"{title} ({y}) is the work of which mangaka?")
            else:
                q = f"Who is the creator of the manga {title}?"
            out.append(candidate(31, m, q, author, wrong))
        if magazine and magazine.casefold() not in m["title"].casefold():
            wrong_mag = similar(magazine, magazines, rng)
            if wrong_mag:
                out.append(candidate(31, m, pick(rng, f"In which magazine was {author}'s {title} serialised?",
                                                 f"{title} by {author} ran in which manga magazine?"), magazine, wrong_mag))
    return out


# ---------- mythology (20) ----------

MYTH_WORDS = re.compile(r"\s*\b(deity|deities|god|goddess|gods|divinity|spirit|primordial|chthonic|solar|lunar|sea|sky|war|death|love|fertility|mother|creator|water|fire|thunder|underworld|tutelary|household)\b", re.I)


MYTHOLOGIES = {"Greek", "Roman", "Norse", "Egyptian", "Hindu", "Celtic", "Irish", "Welsh", "Slavic", "Aztec", "Maya",
               "Mayan", "Inca", "Japanese", "Chinese", "Mesopotamian", "Sumerian", "Babylonian", "Akkadian", "Hittite",
               "Canaanite", "Etruscan", "Yoruba", "Polynesian", "Hawaiian", "Māori", "Finnish", "Baltic", "Lithuanian",
               "Latvian", "Germanic", "Anglo-Saxon", "Persian", "Zoroastrian", "Shinto", "Buddhist", "Taoist", "Korean",
               "Vietnamese", "Philippine", "Armenian", "Georgian", "Gaulish", "Lusitanian", "Phoenician", "Ugaritic", "Hurrian"}


def mythology_name(class_label):
    """'Norse deity' -> 'Norse', 'Ancient Egyptian deity' -> 'Egyptian'; None unless it's a known mythology."""
    culture = MYTH_WORDS.sub("", class_label).strip(" -")
    culture = re.sub(r"^(Ancient|ancient|Old|Classical)\s+", "", culture)
    return culture if culture in MYTHOLOGIES else None


GENERIC_DESCRIPTION = re.compile(r"\b(mythology|mythological|religion|character|figure)\b", re.I)
ROLE_WORDS = {"god", "goddess", "deity", "personification", "king", "queen", "titan", "titaness", "spirit", "nymph",
              "lord", "mother", "father"}


def mythology():
    rng, out = new_rng("mythology"), []
    gods = load("deities")
    for g in gods:
        cultures = {mythology_name(c) for c in g.get("classLabel", ())} - {None}
        g["culture"] = min(cultures) if len(cultures) == 1 else None
    by_culture = {}
    for g in gods:
        if g["culture"]:
            by_culture.setdefault(g["culture"], []).append(g)
    cultures = sorted(c for c, members in by_culture.items() if len(members) >= 4)
    for g in gods:
        culture, name = g["culture"], g["title"]
        if culture not in cultures:
            continue
        same = [x["title"] for x in by_culture[culture]]
        description = text(g, "description")
        domain = text(g, "domainLabel")
        if domain and domain.casefold() not in name.casefold():
            wrong = similar(name, same, rng)
            if wrong:
                out.append(candidate(20, g, pick(rng, f"In {culture} mythology, who is the deity of {domain}?",
                                                 f"Which {culture} deity is associated with {domain}?"), name, wrong))
        # "Greek goddess of the hunt" -> "In Greek mythology, who is the goddess of the hunt?"
        if description and " of " in description and not GENERIC_DESCRIPTION.search(description):
            role = re.sub(rf"^(the |a |an )?((ancient )?{culture} )?", "", description.rstrip("."), flags=re.I)
            role = role[:1].lower() + role[1:]
            if name.casefold() not in role.casefold() and 8 <= len(role) <= 70 and role.split()[0] in ROLE_WORDS:
                wrong = similar(name, same, rng)
                if wrong:
                    out.append(candidate(20, g, pick(rng, f"In {culture} mythology, who is the {role}?",
                                                     f"Which {culture} deity is the {role}?",
                                                     f"Name the {role} in {culture} mythology."), name, wrong))
        father = text(g, "fatherLabel")
        if father:
            fathers = sorted(({text(x, "fatherLabel") for x in by_culture[culture] if text(x, "fatherLabel")} | set(same)) - {name})
            wrong = similar(father, fathers, rng)
            if wrong:
                out.append(candidate(20, g, pick(rng, f"In {culture} mythology, who is the father of {name}?",
                                                 f"{name} is the child of which {culture} figure?"), father, wrong))
        outsiders = [x["title"] for x in gods if x["culture"] and x["culture"] != culture]
        wrong_gods = similar(name, outsiders, rng)
        if wrong_gods:
            out.append(candidate(20, g, pick(rng, f"Which of these figures comes from {culture} mythology?",
                                             f"Only one of these belongs to {culture} mythology. Which?"), name, wrong_gods))
        other = rng.choice([c for c in cultures if c != culture])
        out.append(true_or_false(20, g, rng, f"{name} is a figure from {culture} mythology.",
                                 f"{name} is a figure from {other} mythology."))
        wrong_cultures = similar(culture, cultures, rng)
        if wrong_cultures and culture.casefold() not in (description or "").casefold():
            out.append(candidate(20, g, pick(rng, f"{name} belongs to which mythology?", f"Which culture's myths include {name}?"),
                                 culture, wrong_cultures))
    return out


# ---------- art (25) ----------

def art():
    rng, out = new_rng("art"), []
    paintings = [p for p in load("paintings") if text(p, "artistLabel")]
    artists = sorted({text(p, "artistLabel") for p in paintings})
    museums = sorted({text(p, "collectionLabel") for p in paintings if text(p, "collectionLabel")})
    movements = sorted({text(p, "movementLabel") for p in paintings if text(p, "movementLabel")})
    for p in paintings:
        title, artist, y = quoted(p["title"]), text(p, "artistLabel"), year(p, "date")
        museum, movement, nat = text(p, "collectionLabel"), text(p, "movementLabel"), adjective(p)
        if artist.casefold() in p["title"].casefold():
            continue
        wrong = similar(artist, artists, rng)
        if wrong:
            if museum and y:
                q = pick(rng, f"Which artist painted {title} ({y}), now in the {museum}?",
                         f"{title}, painted in {y}, hangs in the {museum}. Who painted it?")
            elif y and nat:
                q = f"Which {nat} artist painted {title} in {y}?"
            else:
                q = pick(rng, f"Who painted {title}?", f"{title} is the work of which painter?")
            out.append(candidate(25, p, q, artist, wrong))
        if museum:
            wrong_m = similar(museum, museums, rng)
            if wrong_m:
                out.append(candidate(25, p, pick(rng, f"Where can you see {artist}'s {title}?",
                                                 f"{artist}'s {title} belongs to which collection?"), museum, wrong_m))
        if movement and movement.casefold() not in p["title"].casefold():
            wrong_mv = similar(movement, movements, rng)
            if wrong_mv:
                out.append(candidate(25, p, pick(rng, f"{artist}'s {title} belongs to which art movement?",
                                                 f"Which movement is {title} by {artist} part of?"), movement, wrong_mv))
        if y and y >= 1300:
            right, wrong_d = decade_options(y, rng)
            out.append(candidate(25, p, f"In which decade did {artist} paint {title}?", right, wrong_d))
    return out


GENERATORS = {10: books, 15: video_games, 23: history, 22: geography, 31: anime_manga, 20: mythology, 25: art}
