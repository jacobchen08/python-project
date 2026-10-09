"""Questions for the tier 3 and 4 categories that come from Wikidata: cartoons, comics,
vehicles, board games, musicals and theatre, gadgets, and the people side of mathematics.
Same approach as generators.py: several kinds of question per item, varied phrasing, clues
that combine facts, and close wrong answers."""

import re

from common import decade_options, new_rng, pick, similar, year_options
from generators import adjective, candidate, load, quoted, text, true_or_false
from wikidata import usable_label, year


def strip_maker(model, maker):
    """'Toyota RAV4 EV' made by 'Toyota' -> 'RAV4 EV', so the question doesn't give the answer away."""
    words = [w for w in re.split(r"[\s-]+", maker) if len(w) >= 3 and w.lower() not in {"inc.", "inc", "corporation", "company", "group", "motor", "motors", "electronics", "ltd", "ltd."}]
    trimmed = model
    for word in words:
        trimmed = re.sub(rf"\b{re.escape(word)}\b", "", trimmed, flags=re.I)
    trimmed = re.sub(r"\s+", " ", trimmed).strip(" -")
    return trimmed if len(trimmed) >= 2 and trimmed != model else model


# ---------- cartoons (32) ----------

def cartoons():
    rng, out = new_rng("cartoons"), []
    shows = load("cartoons")
    creators = sorted({v for s in shows for v in s.get("creatorLabel", ()) if usable_label(v)})
    networks = sorted({v for s in shows for v in s.get("networkLabel", ()) if usable_label(v)})
    studios = sorted({v for s in shows for v in s.get("studioLabel", ()) if usable_label(v)})
    for s in shows:
        title, y = quoted(s["title"]), year(s, "date")
        creator = text(s, "creatorLabel") if len(s.get("creatorLabel", ())) == 1 else None
        network = text(s, "networkLabel") if len(s.get("networkLabel", ())) == 1 else None
        studio = text(s, "studioLabel") if len(s.get("studioLabel", ())) == 1 else None
        when = f" ({y})" if y else ""
        if creator:
            wrong = similar(creator, creators, rng)
            if wrong:
                clue = f", first shown on {network}" if network else ""
                out.append(candidate(32, s, pick(rng, f"Who created the animated series {title}{when}{clue}?",
                                                 f"{title}{when} was dreamed up by which creator?"), creator, wrong))
        if network:
            wrong = similar(network, networks, rng)
            if wrong:
                out.append(candidate(32, s, pick(rng, f"Which channel first aired {title}{when}?",
                                                 f"{title}{when} premiered on which network?"), network, wrong))
        if studio:
            wrong = similar(studio, studios, rng)
            if wrong:
                out.append(candidate(32, s, pick(rng, f"Which studio produced the cartoon {title}{when}?",
                                                 f"{title} came out of which animation studio?"), studio, wrong))
        if y and y >= 1930:
            right, wrong = decade_options(y, rng)
            out.append(candidate(32, s, pick(rng, f"In which decade did {title} first air?", f"{title} debuted in which decade?"), right, wrong))
    return out


# ---------- comics (29) ----------

COMICS_UNIVERSE = re.compile(r"marvel|earth-|dc universe|dc comics|image|dark horse|archie|valiant|wildstorm|vertigo|teenage mutant|tmnt", re.I)


def comics():
    rng, out = new_rng("comics"), []
    characters = [c for c in load("comics_characters")
                  if any(COMICS_UNIVERSE.search(u) for u in c.get("aliasLabel", ())) or c.get("publisherLabel")]
    creators = sorted({v for c in characters for v in c.get("creatorLabel", ()) if usable_label(v)})
    publishers = sorted({v for c in characters for v in c.get("publisherLabel", ()) if usable_label(v)})
    for c in characters:
        name = c["title"]
        made_by = sorted(v for v in c.get("creatorLabel", ()) if usable_label(v))
        universe = next((u for u in sorted(c.get("aliasLabel", ())) if COMICS_UNIVERSE.search(u)), None)
        house = "Marvel" if universe and re.search(r"marvel|earth-", universe, re.I) else "DC" if universe and re.search(r"\bdc\b", universe, re.I) else None
        publisher = text(c, "publisherLabel") or house
        if made_by:
            pool = [x for x in creators if x not in made_by]
            wrong = similar(made_by[0], pool, rng)
            if wrong:
                if len(made_by) == 2:
                    q = pick(rng, f"{name} was created by {made_by[1]} and which other comics creator?",
                             f"Alongside {made_by[1]}, who co-created {name}?")
                elif publisher:
                    q = pick(rng, f"Which creator introduced the {publisher} character {name}?", f"Who created {name} for {publisher}?")
                else:
                    q = f"Who created the comics character {name}?"
                out.append(candidate(29, c, q, made_by[0], wrong))
        if made_by:
            not_theirs = [x["title"] for x in characters if made_by[0] not in x.get("creatorLabel", ())]
            wrong = similar(name, not_theirs, rng)
            if wrong:
                out.append(candidate(29, c, pick(rng, f"Which of these characters did {made_by[0]} create or co-create?",
                                                 f"{made_by[0]} had a hand in creating which of these characters?"), name, wrong))
        if house:
            other = "DC" if house == "Marvel" else "Marvel"
            out.append(true_or_false(29, c, rng, f"{name} is a {house} Comics character.", f"{name} is a {other} Comics character."))
        if text(c, "publisherLabel"):
            wrong = similar(text(c, "publisherLabel"), publishers, rng)
            if wrong:
                out.append(candidate(29, c, pick(rng, f"Which publisher's comics feature {name}?", f"{name} first appeared in comics from which publisher?"),
                                     text(c, "publisherLabel"), wrong))
    series = load("comics_series")
    series_publishers = sorted({v for s in series for v in s.get("publisherLabel", ()) if usable_label(v)} | set(publishers))
    for s in series:
        title, y, publisher = quoted(s["title"]), year(s, "date"), text(s, "publisherLabel")
        if publisher:
            wrong = similar(publisher, series_publishers, rng)
            if wrong:
                when = f", which began in {y}" if y else ""
                out.append(candidate(29, s, f"Which publisher brought out the comic {title}{when}?", publisher, wrong))
        if y and y >= 1900:
            out.append(candidate(29, s, pick(rng, f"In what year did the comic {title} begin?", f"{title} first appeared in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng)]))
    return out


# ---------- vehicles (28) ----------

def vehicles():
    rng, out = new_rng("vehicles"), []
    cars = [c for c in load("cars") if text(c, "makerLabel")]
    makers = sorted({text(c, "makerLabel") for c in cars})
    maker_country = {text(c, "makerLabel"): text(c, "makerCountryLabel") for c in cars if text(c, "makerCountryLabel")}
    countries = sorted(set(maker_country.values()))
    for c in cars:
        maker, y = text(c, "makerLabel"), year(c, "date")
        model = strip_maker(c["title"], maker)
        if model != c["title"]:
            wrong = similar(maker, makers, rng, closeness=lambda m: maker_country.get(m) != maker_country.get(maker))
            if wrong:
                when = f", launched in {y}," if y else ""
                out.append(candidate(28, c, pick(rng, f"Which company makes the {model}?",
                                                 f"The {model}{when} is built by which manufacturer?",
                                                 f"You're behind the wheel of the {model}. Which brand is it?"), maker, wrong))
        country = maker_country.get(maker)
        if country:
            wrong = similar(country, countries, rng)
            if wrong:
                out.append(candidate(28, c, pick(rng, f"The {c['title']} comes from a carmaker based in which country?",
                                                 f"{maker}, maker of the {model}, is based in which country?"), country, wrong))
        if y and y >= 1900:
            out.append(candidate(28, c, pick(rng, f"In what year did the {c['title']} first go on sale?",
                                             f"The {c['title']} was introduced in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng, spread=(1, 2, 3, 4, 5, 7))]))
    return out


# ---------- board games (16) ----------

def board_games():
    rng, out = new_rng("board_games"), []
    games = [g for g in load("board_games") if "Q11410" not in g.get("class", ()) or g.get("designerLabel")]
    designers = sorted({v for g in games for v in g.get("designerLabel", ()) if usable_label(v)})
    publishers = sorted({v for g in games for v in g.get("publisherLabel", ()) if usable_label(v)})
    for g in games:
        title, y = quoted(g["title"]), year(g, "date")
        designer = text(g, "designerLabel") if len(g.get("designerLabel", ())) == 1 else None
        publisher = text(g, "publisherLabel") if len(g.get("publisherLabel", ())) == 1 else None
        kind = "card game" if "Q142714" in g.get("class", ()) else "board game"
        if designer:
            wrong = similar(designer, designers, rng)
            if wrong:
                when = f" ({y})" if y else ""
                out.append(candidate(16, g, pick(rng, f"Who designed the {kind} {title}{when}?", f"{title}{when} is the work of which game designer?"),
                                     designer, wrong))
        if publisher:
            wrong = similar(publisher, publishers, rng)
            if wrong:
                out.append(candidate(16, g, pick(rng, f"Which company publishes {title}?", f"{title} is published by which games company?"),
                                     publisher, wrong))
        for maker, field, verb in ((designer, "designerLabel", "designed"), (publisher, "publisherLabel", "published")):
            if maker:
                others = [x["title"] for x in games if maker not in x.get(field, ())]
                wrong = similar(g["title"], others, rng)
                if wrong:
                    out.append(candidate(16, g, f"Which of these games did {maker} {'design' if verb == 'designed' else 'publish'}?",
                                         title, [quoted(x) for x in wrong]))
        if y and y >= 1800:
            right, wrong = decade_options(y, rng)
            out.append(candidate(16, g, pick(rng, f"In which decade was {title} first published?", f"{title} first hit the shelves in which decade?"),
                                 right, wrong))
        low, high = (one_int(g, "minPlayers"), one_int(g, "maxPlayers"))
        if low and high and 1 <= low < high <= 12:
            fake = high + rng.choice([2, 3, 4])
            out.append(true_or_false(16, g, rng, f"{title} can be played by up to {high} players.", f"{title} can be played by up to {fake} players."))
    return out


def one_int(facts, field):
    values = [v for v in facts.get(field, ()) if v.split(".")[0].isdigit()]
    return int(float(min(values))) if values else None


# ---------- musicals and theatre (13) ----------

def musicals():
    rng, out = new_rng("musicals"), []
    works = load("musicals")
    composers = sorted({text(w, "composerLabel") for w in works if text(w, "composerLabel")})
    lyricists = sorted({v for w in works for v in w.get("lyricistLabel", ()) if usable_label(v)})
    for w in works:
        title, y, composer = quoted(w["title"]), year(w, "date"), text(w, "composerLabel")
        kind = "musical" if "Q2743" in w.get("class", ()) else "opera" if "Q1344" in w.get("class", ()) else "stage work"
        based = text(w, "basedonLabel")
        if composer and len(w.get("composerLabel", ())) == 1 and composer.split()[-1].casefold() not in w["title"].casefold():
            wrong = similar(composer, composers, rng)
            if wrong:
                if y and based and based.casefold() != w["title"].casefold():
                    q = f"Which composer wrote the {y} {kind} {title}, based on {quoted(based)}?"
                elif y:
                    q = pick(rng, f"Who composed the {kind} {title}, which premiered in {y}?", f"{title} ({y}) has music by which composer?")
                else:
                    q = pick(rng, f"Who wrote the music for the {kind} {title}?", f"The {kind} {title} was composed by whom?")
                out.append(candidate(13, w, q, composer, wrong))
        lyricist = text(w, "lyricistLabel") if len(w.get("lyricistLabel", ())) == 1 else None
        if lyricist and lyricist != composer:
            wrong = similar(lyricist, lyricists, rng)
            if wrong:
                out.append(candidate(13, w, pick(rng, f"Who wrote the words for {composer}'s {kind} {title}?",
                                                 f"{composer} set {title} to music. Who wrote its libretto or lyrics?"), lyricist, wrong))
        if y and y >= 1600:
            right, wrong = decade_options(y, rng)
            out.append(candidate(13, w, pick(rng, f"In which decade did {composer}'s {title} premiere?", f"{title} by {composer} was first staged in which decade?"),
                                 right, wrong))
    return out


# ---------- gadgets (30) ----------

def gadgets():
    rng, out = new_rng("gadgets"), []
    devices = [d for d in load("gadgets") if text(d, "makerLabel")]
    makers = sorted({text(d, "makerLabel") for d in devices})
    systems = sorted({v for d in devices for v in d.get("osLabel", ()) if usable_label(v)})
    kinds = {"Q19723451": "phone", "Q8076": "games console", "Q4931066": "tablet", "Q155972": "laptop", "Q15401633": "camera"}
    for d in devices:
        maker, y = text(d, "makerLabel"), year(d, "date")
        model = strip_maker(d["title"], maker)
        kind = next((k for q, k in kinds.items() if q in d.get("class", ())), "device")
        if model != d["title"] or maker.split()[0].casefold() not in d["title"].casefold():
            wrong = similar(maker, makers, rng)
            if wrong:
                when = f" released in {y}" if y else ""
                out.append(candidate(30, d, pick(rng, f"Which company made the {model} {kind}{when}?", f"The {model} is a {kind} from which maker?"),
                                     maker, wrong))
        others = [x["title"] for x in devices if text(x, "makerLabel") != maker]
        wrong = similar(d["title"], others, rng)
        if wrong:
            out.append(candidate(30, d, pick(rng, f"Which of these devices is made by {maker}?", f"{maker} makes which of these?"),
                                 d["title"], wrong))
        if y and y >= 1970:
            out.append(candidate(30, d, pick(rng, f"In what year was the {d['title']} released?", f"The {d['title']} first went on sale in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng, spread=(1, 2, 3, 4))]))
        system = text(d, "osLabel") if len(d.get("osLabel", ())) == 1 else None
        if system:
            wrong = similar(system, systems, rng)
            if wrong:
                out.append(candidate(30, d, pick(rng, f"Which operating system did the {d['title']} launch with?",
                                                 f"Out of the box, the {d['title']} ran which software?"), system, wrong))
    return out


# ---------- mathematicians (19, with mathematics.py for the numbers) ----------

def mathematicians():
    rng, out = new_rng("mathematicians"), []
    people = load("mathematicians")
    names = sorted(p["title"] for p in people)
    born_in = {p["title"]: year(p, "born") or 1800 for p in people}
    for p in people:
        name, born, nat = p["title"], year(p, "born"), adjective(p)
        surname_bits = {w.casefold() for w in re.split(r"\W+", name) if len(w) >= 4}
        works = sorted(w for w in p.get("workLabel", ()) if usable_label(w)
                       and not any(bit in w.casefold() for bit in surname_bits))
        if works:
            who = f"{nat} mathematician" if nat else "mathematician"
            when = f", born in {born}," if born and born > 0 else ""
            wrong = similar(name, names, rng, closeness=lambda other: abs(born_in[other] - (born or 1800)) // 40)
            if wrong:
                work = works[0] if works[0].lower().startswith("the ") else f"the {works[0]}"
                out.append(candidate(19, p, pick(rng, f"Which {who}{when} is known for {work}?",
                                                 f"Which {who} gave us {work}?"), name, wrong))
        if born and born > 0:
            century = (born - 1) // 100 + 1
            options = [c for c in range(max(1, century - 3), century + 4) if c != century and c <= 20]
            if len(options) >= 3:
                fmt = lambda c: f"{c}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(c % 10 if c not in (11, 12, 13) else 0, 'th') } century"
                out.append(candidate(19, p, pick(rng, f"In which century was the mathematician {name} born?",
                                                 f"{name} was born in which century?"), fmt(century), [fmt(c) for c in rng.sample(options, 3)]))
    return out


GENERATORS2 = {32: cartoons, 29: comics, 28: vehicles, 16: board_games, 13: musicals, 30: gadgets}
