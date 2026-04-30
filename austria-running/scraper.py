#!/usr/bin/env python3
"""
Scraper für österreichische Marathon- und Trailrun-Veranstaltungen.
Aktualisiert events.json täglich mit neuen Daten aus öffentlichen Quellen.
"""

import json
import re
import sys
import time
import logging
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path
from html.parser import HTMLParser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

EVENTS_FILE = Path(__file__).parent / "events.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AustriaRunCalendar/1.0; "
        "+https://github.com/nortschik/funscript)"
    ),
    "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CURATED_EVENTS = [
    {
        "id": 1,
        "name": "Oberbank Linz Donau Marathon",
        "type": "marathon",
        "date": "2026-04-12",
        "location": "Linz, Oberösterreich",
        "distances": ["5 km", "Halbmarathon", "Marathon", "Staffel"],
        "website": "https://www.linzmarathon.at",
        "description": (
            "Der 24. Oberbank Linz Donau Marathon entlang der Donau – "
            "Österreichs beliebtester Frühjahrslauf mit ~20.000 Läufern."
        ),
        "elevation_gain": None,
        "region": "Oberösterreich",
    },
    {
        "id": 2,
        "name": "Vienna City Marathon",
        "type": "marathon",
        "date": "2026-04-19",
        "location": "Wien",
        "distances": ["5 km", "10 km", "Halbmarathon", "Marathon", "Staffel"],
        "website": "https://www.vienna-marathon.com",
        "description": (
            "Österreichs größter Marathon durch die Weltstadt Wien – "
            "seit über 40 Jahren ein Fixpunkt im Laufkalender."
        ),
        "elevation_gain": None,
        "region": "Wien",
    },
    {
        "id": 3,
        "name": "Innsbruck Alpine Trailrun Festival",
        "type": "trail",
        "date": "2026-04-29",
        "date_end": "2026-05-02",
        "location": "Innsbruck, Tirol",
        "distances": ["7 km", "15 km", "30 km", "55 km", "80 km", "110 km"],
        "website": "https://www.innsbruckalpine.at",
        "description": (
            "Das größte Trailrun-Festival im deutschsprachigen Alpenraum – "
            "14 Bewerbe von 7 bis 113 km mit bis zu 5.600 Hm."
        ),
        "elevation_gain": 5600,
        "region": "Tirol",
    },
    {
        "id": 4,
        "name": "PUMA Salzburg Marathon",
        "type": "marathon",
        "date": "2026-05-17",
        "location": "Salzburg",
        "distances": ["5 km", "10 km", "Halbmarathon", "Marathon", "Staffel"],
        "website": "https://salzburg-marathon.at",
        "description": (
            "Die Lauffestspiele der Mozartstadt – ein Marathon durch das "
            "UNESCO-Weltkulturerbe Salzburg."
        ),
        "elevation_gain": None,
        "region": "Salzburg",
    },
    {
        "id": 5,
        "name": "Wörthersee Trail & Hike Festival",
        "type": "trail",
        "date": "2026-05-09",
        "location": "Pörtschach am Wörthersee, Kärnten",
        "distances": ["14 km", "28 km", "46 km", "65 km"],
        "website": "https://www.woerthersee-trail.at",
        "description": (
            "Trail- und Wanderfestival am schönsten See Österreichs mit "
            "spektakulären Ausblicken auf den Wörthersee."
        ),
        "elevation_gain": 2800,
        "region": "Kärnten",
    },
    {
        "id": 6,
        "name": "Stuiben Trailrun",
        "type": "trail",
        "date": "2026-05-14",
        "date_end": "2026-05-16",
        "location": "Umhausen, Ötztal, Tirol",
        "distances": ["10 km", "28 km", "55 km"],
        "website": "https://www.oetztal-trailrunning.at",
        "description": (
            "Spektakulärer Trailrun am Stuibenfall – dem größten Wasserfall "
            "Tirols (159 m). Inkl. 728 Treppenstufen!"
        ),
        "elevation_gain": 2200,
        "region": "Tirol",
    },
    {
        "id": 7,
        "name": "Semmering Trailrun",
        "type": "trail",
        "date": "2026-05-16",
        "location": "Semmering, Niederösterreich",
        "distances": ["8 km", "16 km", "28 km"],
        "website": "https://www.semmering.com",
        "description": (
            "Trailrun im UNESCO-Welterbe Semmeringbahn-Region mit "
            "herrlichem Panorama."
        ),
        "elevation_gain": 900,
        "region": "Niederösterreich",
    },
    {
        "id": 8,
        "name": "Tschirgant SkyRun",
        "type": "trail",
        "date": "2026-06-13",
        "location": "Imst, Tirol",
        "distances": ["12 km", "25 km"],
        "website": "https://www.tschirgant-skyrun.at",
        "description": (
            "Vertikalrennen und Skyrun am Tschirgant – einer der steilsten "
            "Berge Tirols mit einzigartiger Felswand."
        ),
        "elevation_gain": 1600,
        "region": "Tirol",
    },
    {
        "id": 9,
        "name": "Raiffeisen Montafon Arlberg Marathon",
        "type": "marathon",
        "date": "2026-06-27",
        "location": "Silbertal – St. Anton am Arlberg, Vorarlberg/Tirol",
        "distances": ["15 km Trail", "33 km Trail", "Marathon 42 km"],
        "website": "https://www.montafon.at/montafon-arlberg-marathon",
        "description": (
            "Bergmarathon von Silbertal bis St. Anton mit 1.500 Hm – "
            "spektakuläre Alpenlandschaft zwischen Vorarlberg und Tirol."
        ),
        "elevation_gain": 1500,
        "region": "Vorarlberg/Tirol",
    },
    {
        "id": 10,
        "name": "Grossglockner Mountain Run",
        "type": "trail",
        "date": "2026-07-05",
        "location": "Heiligenblut, Kärnten",
        "distances": ["13,3 km"],
        "website": "https://grossglockner-mountainrun.at",
        "description": (
            "Legendärer Berglauf von Heiligenblut (1.250 m) zur "
            "Kaiser-Franz-Josefs-Höhe (2.370 m) mit 1.300 Hm."
        ),
        "elevation_gain": 1300,
        "region": "Kärnten",
    },
    {
        "id": 11,
        "name": "The North Face Grossglockner Ultra-Trail",
        "type": "trail",
        "date": "2026-07-03",
        "date_end": "2026-07-05",
        "location": "Heiligenblut, Kärnten",
        "distances": ["50 km", "100 km", "UltraK"],
        "website": "https://www.ultratrail.at",
        "description": (
            "Ultra-Trail rund um Österreichs höchsten Berg – durch die "
            "beeindruckende Hochgebirgslandschaft des Großglockners."
        ),
        "elevation_gain": 4500,
        "region": "Kärnten",
    },
    {
        "id": 12,
        "name": "Pitz Alpine Glacier Trail",
        "type": "trail",
        "date": "2026-07-31",
        "date_end": "2026-08-02",
        "location": "St. Leonhard im Pitztal, Tirol",
        "distances": ["16 km", "36 km", "60 km", "80 km", "103 km"],
        "website": "https://www.oetztal-trailrunning.at/die-running-events/gletscher-trailrun",
        "description": (
            "Trail am Pitztaler Gletscher auf bis zu 3.000 m Höhe – sieben "
            "Distanzen durch eine der wildesten Hochgebirgslandschaften Tirols."
        ),
        "elevation_gain": 5500,
        "region": "Tirol",
    },
    {
        "id": 13,
        "name": "Kleine Zeitung Wörthersee Halbmarathon",
        "type": "marathon",
        "date": "2026-08-30",
        "location": "Klagenfurt, Kärnten",
        "distances": ["Halbmarathon"],
        "website": "https://www.kaerntenlaeuft.at",
        "description": (
            "Halbmarathon am Wörthersee im Sommer – perfekte Laufatmosphäre "
            "am schönsten See Kärntens."
        ),
        "elevation_gain": None,
        "region": "Kärnten",
    },
    {
        "id": 14,
        "name": "Ötztal Ultratrail",
        "type": "trail",
        "date": "2026-08-14",
        "date_end": "2026-08-16",
        "location": "Sölden, Ötztal, Tirol",
        "distances": ["25 km", "50 km", "100 km"],
        "website": "https://www.oetztal-trailrunning.at",
        "description": (
            "Ultra-Trail im Ötztal mit Distanzen bis 100 km durch die "
            "hochalpine Gletscherwelt."
        ),
        "elevation_gain": 5000,
        "region": "Tirol",
    },
    {
        "id": 15,
        "name": "Torlauf Dachstein",
        "type": "trail",
        "date": "2026-09-05",
        "location": "Ramsau am Dachstein, Steiermark",
        "distances": ["10 km", "Halbmarathon", "Marathon", "Ultra"],
        "website": "https://www.torlauf-dachstein.info",
        "description": (
            "10 Jahre Torlauf Dachstein! Jubiläumsausgabe mit neuem "
            "Ultra-Bewerb – spektakuläre Kulisse am Dachsteinmassiv."
        ),
        "elevation_gain": 2000,
        "region": "Steiermark",
    },
    {
        "id": 16,
        "name": "Wörthersee Marathon",
        "type": "marathon",
        "date": "2026-09-27",
        "location": "Klagenfurt am Wörthersee, Kärnten",
        "distances": ["Halbmarathon", "Marathon", "Staffel", "Walk the Lake"],
        "website": "https://woerthersee-marathon.at",
        "description": (
            "Premiere 2026! Ein See, eine Runde, ein Marathon – 42 km rund um "
            "den Wörthersee, organisiert von der VCM-Familie."
        ),
        "elevation_gain": None,
        "region": "Kärnten",
    },
    {
        "id": 17,
        "name": "Kleine Zeitung Graz Marathon",
        "type": "marathon",
        "date": "2026-10-11",
        "location": "Graz, Steiermark",
        "distances": ["5 km", "10 km", "Halbmarathon", "Marathon", "Staffel"],
        "website": "https://www.grazmarathon.at",
        "description": (
            "Der Stadtmarathon durch die Kulturhauptstadt Graz – flache "
            "Strecke durch die historische Altstadt."
        ),
        "elevation_gain": None,
        "region": "Steiermark",
    },
    {
        "id": 18,
        "name": "3-Länder Marathon Bregenz",
        "type": "marathon",
        "date": "2026-10-11",
        "location": "Bregenz, Vorarlberg",
        "distances": ["11 km", "Halbmarathon", "Marathon"],
        "website": "https://www.3-laender-marathon.at",
        "description": (
            "Einzigartiger Marathon über die Grenzen von Österreich, "
            "Deutschland und der Schweiz am Bodensee."
        ),
        "elevation_gain": None,
        "region": "Vorarlberg",
    },
    {
        "id": 19,
        "name": "Int. Wolfgangseelauf – Salzkammergut Marathon",
        "type": "marathon",
        "date": "2026-10-18",
        "location": "St. Wolfgang im Salzkammergut, Oberösterreich",
        "distances": ["5,2 km", "10 km", "27 km", "Marathon"],
        "website": "https://www.wolfgangseelauf.at",
        "description": (
            "Malerischer Marathon durch das Salzkammergut – seit 1972 ein "
            "fixer Herbstklassiker am Wolfgangsee."
        ),
        "elevation_gain": 400,
        "region": "Oberösterreich",
    },
    {
        "id": 20,
        "name": "Vienna City Marathon (Herbst)",
        "type": "marathon",
        "date": "2026-10-17",
        "date_end": "2026-10-18",
        "location": "Wien",
        "distances": ["5 km", "10 km", "Halbmarathon", "Marathon", "Staffel"],
        "website": "https://www.vienna-marathon.com",
        "description": (
            "Der Herbst-VCM 2026 – Österreichs traditionsreichster Marathon "
            "durch das Herz Wiens."
        ),
        "elevation_gain": None,
        "region": "Wien",
    },
]

SOURCES = [
    {"name": "Vienna City Marathon", "url": "https://www.vienna-marathon.com"},
    {"name": "Linz Marathon", "url": "https://www.linzmarathon.at"},
    {"name": "Salzburg Marathon", "url": "https://salzburg-marathon.at"},
    {"name": "Graz Marathon", "url": "https://www.grazmarathon.at"},
    {"name": "MaxFun Sports", "url": "https://www.maxfunsports.com"},
    {"name": "Innsbruck Alpine", "url": "https://www.innsbruckalpine.at"},
    {"name": "GoTrail.run Austria", "url": "https://gotrail.run/en/calendar/austria"},
    {"name": "ATRA – Trailrunning Verband Austria", "url": "https://www.atra.club"},
    {"name": "runme.at", "url": "https://www.runme.at/laufkalender/oesterreich/"},
    {
        "name": "Finishers.com Austria",
        "url": "https://www.finishers.com/en/destinations/europe/austria",
    },
]

SCRAPE_TARGETS = [
    {
        "url": "https://www.maxfunsports.com/laufkalender/oesterreich/",
        "name": "MaxFun Sports Laufkalender",
    },
    {
        "url": "https://www.atra.club/events",
        "name": "ATRA Trailrunning Events",
    },
]


class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip_tags = {"script", "style", "noscript", "head"}
        self._current_skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._current_skip += 1

    def handle_endtag(self, tag):
        if tag in self._skip_tags and self._current_skip > 0:
            self._current_skip -= 1

    def handle_data(self, data):
        if self._current_skip == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self):
        return " ".join(self.text_parts)


def fetch_url(url: str, timeout: int = 15) -> str | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            return resp.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        log.warning("HTTP %s fetching %s", e.code, url)
    except urllib.error.URLError as e:
        log.warning("URL error fetching %s: %s", url, e.reason)
    except Exception as e:
        log.warning("Error fetching %s: %s", url, e)
    return None


def extract_events_from_html(html: str, source_url: str) -> list[dict]:
    """Heuristic extraction: look for date + running-related keywords near each other."""
    parser = SimpleHTMLTextExtractor()
    parser.feed(html)
    text = parser.get_text()

    DATE_RE = re.compile(
        r"\b(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\b"
        r"|\b(\d{4})-(\d{2})-(\d{2})\b"
    )
    TRAIL_KW = re.compile(
        r"trail|berglauf|skyrun|ultra|mountain run", re.IGNORECASE
    )
    MARATHON_KW = re.compile(
        r"marathon|halbmarathon|half marathon", re.IGNORECASE
    )
    AUSTRIA_CITIES = re.compile(
        r"Wien|Graz|Linz|Salzburg|Innsbruck|Klagenfurt|Bregenz|Wels|"
        r"Tirol|Steiermark|Kärnten|Vorarlberg|Niederösterreich|"
        r"Oberösterreich|Burgenland",
        re.IGNORECASE,
    )

    found = []
    sentences = re.split(r"[|\n]", text)
    for chunk in sentences:
        m = DATE_RE.search(chunk)
        if not m:
            continue
        if not (TRAIL_KW.search(chunk) or MARATHON_KW.search(chunk)):
            continue
        if not AUSTRIA_CITIES.search(chunk):
            continue

        try:
            if m.group(1):
                day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                year, month, day = int(m.group(4)), int(m.group(5)), int(m.group(6))
            ev_date = date(year, month, day).isoformat()
        except (ValueError, TypeError):
            continue

        ev_type = "trail" if TRAIL_KW.search(chunk) else "marathon"
        name = chunk[:80].strip()
        found.append(
            {
                "name": name,
                "type": ev_type,
                "date": ev_date,
                "location": "Österreich",
                "distances": [],
                "website": source_url,
                "description": chunk[:200].strip(),
                "elevation_gain": None,
                "region": "Österreich",
            }
        )

    return found


def deduplicate(events: list[dict]) -> list[dict]:
    seen = {}
    for ev in events:
        key = (ev["name"].lower()[:30], ev["date"])
        if key not in seen:
            seen[key] = ev
    result = list(seen.values())
    for i, ev in enumerate(result, start=1):
        ev["id"] = i
    return result


def load_existing() -> list[dict]:
    if EVENTS_FILE.exists():
        with open(EVENTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("events", [])
    return []


def save(events: list[dict]) -> None:
    today = date.today().isoformat()
    payload = {
        "last_updated": today,
        "events": events,
        "sources": SOURCES,
    }
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("Saved %d events to %s", len(events), EVENTS_FILE)


def scrape_additional() -> list[dict]:
    additional = []
    for target in SCRAPE_TARGETS:
        log.info("Scraping %s …", target["name"])
        html = fetch_url(target["url"])
        if html:
            found = extract_events_from_html(html, target["url"])
            log.info("  → %d potential events found", len(found))
            additional.extend(found)
        time.sleep(2)
    return additional


def merge_events(base: list[dict], scraped: list[dict]) -> list[dict]:
    existing_keys = {(e["name"].lower()[:30], e["date"]) for e in base}
    new_events = []
    for ev in scraped:
        key = (ev["name"].lower()[:30], ev["date"])
        if key not in existing_keys:
            new_events.append(ev)
            existing_keys.add(key)
    merged = base + new_events
    return deduplicate(merged)


def main():
    log.info("=== Austria Running Events Scraper ===")
    log.info("Date: %s", date.today().isoformat())

    # Start with curated base data
    base_events = CURATED_EVENTS.copy()

    # Try to incorporate any existing scraped events
    existing = load_existing()
    if existing:
        # Keep scraped events not in curated list
        curated_keys = {(e["name"].lower()[:30], e["date"]) for e in base_events}
        for ev in existing:
            key = (ev["name"].lower()[:30], ev["date"])
            if key not in curated_keys:
                base_events.append(ev)
        log.info("Loaded %d existing events", len(existing))

    # Scrape additional sources
    scraped = scrape_additional()
    merged = merge_events(base_events, scraped)

    # Sort by date
    merged.sort(key=lambda e: e["date"])

    log.info("Total events after merge: %d", len(merged))
    save(merged)
    log.info("Done.")


if __name__ == "__main__":
    main()
