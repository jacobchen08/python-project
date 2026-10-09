"""Reading facts from Wikidata (https://www.wikidata.org), whose data is public domain (CC0).

Every query's result is kept in backend/data/sources/wikidata/<name>.json, so rebuilding the
bank doesn't ask Wikidata again. Delete a file to fetch it fresh.
"""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "QuizzrQuestionBank/1.0 (open-source trivia game; builds questions once, results cached)"
CACHE = Path(__file__).resolve().parents[2] / "data" / "sources" / "wikidata"
PREFIXES = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX schema: <http://schema.org/>
PREFIX bd: <http://www.bigdata.com/rdf#>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
"""
QID = re.compile(r"^Q\d+$")


def query(name, sparql, retries=3):
    """Rows of a SELECT query as dicts of plain strings, cached under `name`."""
    path = CACHE / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": PREFIXES + sparql, "format": "json"})
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            data = json.load(urllib.request.urlopen(request, timeout=120))
            break
        except Exception as e:  # timeouts and "too many requests": wait and try again
            if attempt == retries - 1:
                raise RuntimeError(f"Wikidata query {name!r} failed: {e}") from e
            time.sleep(15 * (attempt + 1))
    rows = [
        {key: cell["value"].rsplit("/", 1)[-1] if cell["value"].startswith("http://www.wikidata.org/entity/") else cell["value"]
         for key, cell in row.items()}
        for row in data["results"]["bindings"]
    ]
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    time.sleep(2)  # be gentle with the public endpoint
    return rows


def usable_label(text):
    """A label a player can read: not a bare item id, not empty, not absurdly long."""
    return bool(text) and not QID.match(text) and len(text) <= 80


def group(rows, key="item"):
    """Rows (one per fact combination) gathered per item: {item: {field: set(values)}}."""
    items = {}
    for row in rows:
        entry = items.setdefault(row[key], {})
        for field, value in row.items():
            if field != key and value:
                entry.setdefault(field, set()).add(value)
    return items


def one(entry, field):
    """A single value of a field (the alphabetically first, so builds are repeatable), or None."""
    values = entry.get(field)
    return min(values) if values else None


def year(entry, field):
    value = one(entry, field)
    return int(value[:4]) if value and value[:4].isdigit() and not value.startswith("-") else None
