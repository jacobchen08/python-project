"""Questions for Animals, Politics and Computers from Wikidata, in the same style as
generators.py: several kinds of question per item, varied phrasing, close wrong answers."""

import re

from common import new_rng, pick, similar, year_options
from generators import adjective, candidate, load, quoted, text, true_or_false
from generators2 import strip_maker
from queries import QUERIES
from wikidata import query, usable_label, year

# The animal groups, checked against Wikidata's own labels. (Insects, molluscs and fish were
# tried too, but their queries time out on Wikidata's public service.)
ANIMAL_GROUPS = {"Q7377": ("mammal", "mammals"), "Q5113": ("bird", "birds"), "Q10811": ("reptile", "reptiles"),
                 "Q10908": ("amphibian", "amphibians")}
# for "What kind of animal is…?", any of these can be a wrong answer
ANIMAL_KINDS = ["mammal", "bird", "reptile", "amphibian", "fish", "insect"]
STATUS_ORDER = ["least concern", "near threatened", "vulnerable", "endangered", "critically endangered", "extinct"]


# ---------- animals (27) ----------

def animals():
    rng, out = new_rng("animals"), []
    group_of = {}
    for qid in ANIMAL_GROUPS:
        for row in query(f"animal_group_{qid}", QUERIES[f"animal_group_{qid}"]):
            group_of.setdefault(row["item"], qid)
    species = [s for s in load("animals") if s["qid"] in group_of]
    for s in species:
        names = sorted(s.get("common", ()), key=lambda n: (n.islower(), len(n)))
        s["common_name"] = names[0][:1].upper() + names[0][1:] if names else s["title"]
        s["group"] = ANIMAL_GROUPS[group_of[s["qid"]]]
    for s in species:
        name, (one, many) = s["common_name"], s["group"]
        others = [x["common_name"] for x in species if x["group"] != s["group"]]
        wrong = similar(name, others, rng)
        if wrong:
            out.append(candidate(27, s, pick(rng, f"Which of these animals is a {one}?" if one != "fish" else "Which of these animals is a fish?",
                                             f"Only one of these is a {one}. Which?"), name, wrong))
        kinds = [k for k in ANIMAL_KINDS if k != one]
        out.append(candidate(27, s, pick(rng, f"What kind of animal is the {name.lower() if name.islower() else name}?",
                                         f"The {name} is a…"), one.capitalize(), [k.capitalize() for k in rng.sample(kinds, 3)]))
        status = text(s, "statusLabel")
        # most well-known species are "least concern", so keep only some of those or it becomes the safe guess
        if status and status.lower() in STATUS_ORDER and (status.lower() != "least concern" or rng.random() < 0.25):
            right = status[:1].upper() + status[1:].lower()
            wrong_status = [w[:1].upper() + w[1:] for w in STATUS_ORDER if w != status.lower()]
            out.append(candidate(27, s, pick(rng, f"How does the IUCN Red List classify the {name}?",
                                             f"What is the conservation status of the {name}?"), right, rng.sample(wrong_status, 3)))
        scientific = s["title"]
        if scientific != name and re.fullmatch(r"[A-Z][a-z]+ [a-z]+", scientific):
            same_group = [x["title"] for x in species if x["group"] == s["group"] and re.fullmatch(r"[A-Z][a-z]+ [a-z]+", x["title"])]
            wrong = similar(scientific, same_group, rng)
            if wrong:
                out.append(candidate(27, s, pick(rng, f"What is the scientific name of the {name}?", f"Biologists call the {name} by which Latin name?"),
                                     scientific, wrong))
        other = rng.choice(kinds)
        out.append(true_or_false(27, s, rng, f"The {name} is a {one}.", f"The {name} is a {other}."))
    return out


# ---------- politics (24) ----------

def politics():
    rng, out = new_rng("politics"), []
    # Offices shared across several countries (a Commonwealth monarch, a governor-general)
    # would make "which country did … lead?" misleading
    leaders = [p for p in load("leaders")
               if not any(re.search(r"monarch of|governor-general|governor general", pos, re.I) for pos in p.get("positionLabel", ()))]
    countries = sorted({v for p in leaders for v in p.get("countryLabel", ()) if usable_label(v)})
    continent_of = {}
    for c in load("countries"):
        for name in c.get("continentLabel", ()):
            if name in ("Africa", "Asia", "Europe", "North America", "South America", "Oceania"):
                continent_of.setdefault(c["title"], name)
    party_country = {}
    for p in leaders:
        for party in p.get("partyLabel", ()):
            party_country.setdefault(party, text(p, "countryLabel"))
    holders = {}  # position -> [(start year, name)]
    for p in leaders:
        for position in p.get("positionLabel", ()):
            holders.setdefault(position, []).append((year(p, "start") or 0, p["title"]))
    parties = sorted({v for p in leaders for v in p.get("partyLabel", ()) if usable_label(v)})
    for p in leaders:
        name = p["title"]
        country = text(p, "countryLabel") if len(p.get("countryLabel", ())) == 1 else None
        position = text(p, "positionLabel") if len(p.get("positionLabel", ())) == 1 else None
        start, end = year(p, "start"), year(p, "end")
        if country:
            wrong = similar(country, countries, rng, closeness=lambda other: continent_of.get(other) != continent_of.get(country))
            if wrong:
                when = f" from {start} to {end}" if start and end and end >= start else f" from {start}" if start else ""
                out.append(candidate(24, p, pick(rng, f"{name} led which country{when}?", f"Which country did {name} lead{when}?",
                                                 f"As head of state or government{when}, {name} served which country?"), country, wrong))
        if position and start and end and end >= start:
            rivals = sorted({n for s, n in holders.get(position, []) if n != name}, key=lambda n: rng.random())
            if len(rivals) >= 3:
                q = (f"In {start}, who briefly served as {position}?" if start == end
                     else pick(rng, f"Who served as {position} from {start} to {end}?", f"From {start} until {end}, who was {position}?"))
                out.append(candidate(24, p, q, name, rivals[:3]))
        if position and start and start >= 1800:
            out.append(candidate(24, p, pick(rng, f"In what year did {name} become {position}?", f"{name} took office as {position} in which year?"),
                                 str(start), [str(v) for v in year_options(start, rng, spread=(1, 2, 3, 4, 5, 8))]))
        party = text(p, "partyLabel") if len(p.get("partyLabel", ())) == 1 else None
        if party:
            wrong = similar(party, parties, rng, closeness=lambda other: party_country.get(other) != country)
            if wrong:
                out.append(candidate(24, p, pick(rng, f"Which political party did {name} belong to?", f"{name} was a member of which party?"),
                                     party, wrong))
    return out


# ---------- computers (18) ----------

def computers():
    rng, out = new_rng("computers"), []
    # Programming languages: who designed them, and when they appeared
    languages = load("programming_languages")
    designers = sorted({v for l in languages for v in l.get("designerLabel", ()) if usable_label(v)})
    for l in languages:
        designer = text(l, "designerLabel") if len(l.get("designerLabel", ())) == 1 else None
        y = year(l, "date")
        if designer:
            wrong = similar(designer, designers, rng)
            if wrong:
                when = f", which first appeared in {y}" if y else ""
                out.append(candidate(18, l, pick(rng, f"Who designed the programming language {l['title']}{when}?",
                                                 f"{l['title']}{when} was created by whom?"), designer, wrong))
        if y and y >= 1945:
            out.append(candidate(18, l, pick(rng, f"In what year did the programming language {l['title']} first appear?",
                                             f"{l['title']} was released in which year?"), str(y), [str(v) for v in year_options(y, rng, spread=(1, 2, 3, 5, 7))]))
    # Software and systems: who makes them
    software = load("computer_software") + load("operating_systems")
    makers = sorted({v for s in software for v in s.get("developerLabel", ()) if usable_label(v)})
    for s in software:
        maker = text(s, "developerLabel") if len(s.get("developerLabel", ())) == 1 else None
        y = year(s, "date")
        if maker:
            shown = strip_maker(s["title"], maker)
            wrong = similar(maker, makers, rng)
            if wrong:
                when = f", first released in {y}," if y else ""
                out.append(candidate(18, s, pick(rng, f"Which company or group develops {shown}{when.rstrip(',')}?", f"{shown}{when} comes from which developer?"),
                                     maker, wrong))
        if y and y >= 1960:
            out.append(candidate(18, s, pick(rng, f"In what year was {s['title']} first released?", f"{s['title']} first came out in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng, spread=(1, 2, 3, 4, 6))]))
        owner = text(s, "ownerLabel")
        if owner and owner != maker:
            owners = sorted({text(x, "ownerLabel") for x in software if text(x, "ownerLabel")})
            wrong = similar(owner, owners, rng)
            if wrong:
                out.append(candidate(18, s, pick(rng, f"Which company owns {s['title']}?", f"{s['title']} belongs to which company?"), owner, wrong))
    # Companies: founders, headquarters, founding year
    companies = load("tech_companies_all") + load("tech_companies")
    founders = sorted({v for c in companies for v in c.get("founderLabel", ()) if usable_label(v)})
    cities = sorted({v for c in companies for v in c.get("hqLabel", ()) if usable_label(v)})
    for c in companies:
        founder = sorted(v for v in c.get("founderLabel", ()) if usable_label(v))
        if founder:
            wrong = similar(founder[0], [f for f in founders if f not in founder], rng)
            if wrong:
                q = (f"{c['title']} was founded by {founder[1]} and which co-founder?" if len(founder) == 2
                     else pick(rng, f"Who founded {c['title']}?", f"{c['title']} was started by whom?"))
                out.append(candidate(18, c, q, founder[0], wrong))
        hq = text(c, "hqLabel") if len(c.get("hqLabel", ())) == 1 else None
        if hq:
            wrong = similar(hq, cities, rng)
            if wrong:
                out.append(candidate(18, c, pick(rng, f"Where is {c['title']} headquartered?", f"{c['title']} has its headquarters in which city?"), hq, wrong))
        y = year(c, "date")
        if y and y >= 1900:
            out.append(candidate(18, c, pick(rng, f"In what year was {c['title']} founded?", f"{c['title']} was founded in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng)]))
    # People: what they're known for, and Turing Awards
    people = load("computer_people")
    names = sorted({p["title"] for p in people})
    for p in people:
        name, nat = p["title"], adjective(p)
        bits = {w.casefold() for w in re.split(r"\W+", name) if len(w) >= 4}
        works = sorted(w for w in p.get("workLabel", ()) if usable_label(w) and not any(b in w.casefold() for b in bits))
        if works:
            wrong = similar(name, names, rng)
            if wrong:
                who = f"{nat} computer scientist" if nat else "computer scientist"
                out.append(candidate(18, p, pick(rng, f"Which {who} is known for {works[0]}?", f"{works[0]} is the work of which {who}?"), name, wrong))
    for p in load("computer_scientists"):
        y = year(p, "date")
        if y:
            out.append(candidate(18, p, pick(rng, f"In which year did {p['title']} receive the Turing Award?", f"{p['title']} won the Turing Award in which year?"),
                                 str(y), [str(v) for v in year_options(y, rng, spread=(1, 2, 3, 4, 6))]))
    return out


GENERATORS3 = {27: [animals], 24: [politics], 18: [computers]}
