"""Tools the brain can call.

To add a capability:
  1. write a plain Python function that returns a short status string,
  2. add a schema describing it (so the LLM knows when/how to call it),
  3. register both in the TOOLS list at the bottom.
That's the entire extension story; both brains pick it up automatically.

SAFETY: every tool here only reads, opens, or plays. Nothing is destructive.
If you ever add something irreversible (delete, send, buy, overwrite), gate it
behind a spoken confirmation before doing the action. See README.
"""
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests

import config


# ── open a website ──────────────────────────────────────────────────
def open_website(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}"


# ── play something on YouTube ───────────────────────────────────────
def play_youtube(query: str) -> str:
    try:
        import pywhatkit                      # optional: plays the top result directly
        pywhatkit.playonyt(query)
        return f"Playing '{query}' on YouTube"
    except Exception:
        webbrowser.open("https://www.youtube.com/results?search_query=" + quote_plus(query))
        return f"Opened a YouTube search for '{query}'"


# ── walking folders without getting stuck ───────────────────────────
def _walk_files(dirs):
    """Yield files under `dirs`, skipping hidden and heavy folders (node_modules,
    .git, virtualenvs) and unreadable ones, up to MAX_FILES_SCANNED files."""
    seen = 0
    for root in dirs:
        if not root.exists():
            continue
        for current, subdirs, files in os.walk(root, onerror=lambda _e: None):
            subdirs[:] = [d for d in subdirs if not d.startswith(".") and d not in config.SKIP_DIRS]
            for name in files:
                seen += 1
                if seen > config.MAX_FILES_SCANNED:
                    return
                yield Path(current) / name


# ── play a local song/video ─────────────────────────────────────────
MEDIA_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".avi", ".mov", ".webm"}


def play_local_media(name: str) -> str:
    name_l = name.lower().strip()
    for path in _walk_files(config.MEDIA_DIRS):
        if path.suffix.lower() in MEDIA_EXTS and name_l in path.stem.lower():
            _open_with_default_app(path)
            return f"Playing {path.name}"
    return f"Couldn't find any local media matching '{name}'"


# ── search for a file ───────────────────────────────────────────────
def search_files(query: str) -> str:
    query_l = query.lower().strip()
    hits = []
    for path in _walk_files(config.FILE_SEARCH_DIRS):
        if query_l in path.name.lower():
            hits.append(str(path))
            if len(hits) >= 8:
                break
    if not hits:
        return f"No files matching '{query}'"
    return f"Found {len(hits)} file(s): " + "; ".join(hits)


def open_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.is_file():
        return f"That file doesn't exist: {path}"
    _open_with_default_app(p)
    return f"Opened {p.name}"


# ── date and time ───────────────────────────────────────────────────
def get_datetime() -> str:
    now = datetime.now()
    return now.strftime("It's %A %d %B %Y, %I:%M %p.").replace(" 0", " ")


# ── weather (Open-Meteo: free, no API key) ──────────────────────────
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "heavy rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with heavy hail",
}


def get_weather(city: str) -> str:
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": city, "count": 1}, timeout=10).json()
        if not geo.get("results"):
            return f"I couldn't find a place called {city}."
        place = geo["results"][0]
        now = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": place["latitude"], "longitude": place["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        }, timeout=10).json()["current"]
        sky = WEATHER_CODES.get(now["weather_code"], "unsettled weather")
        return (f"{place['name']}, {place.get('country', '')}: {sky}, {round(now['temperature_2m'])}°C "
                f"(feels like {round(now['apparent_temperature'])}°C), wind {round(now['wind_speed_10m'])} km/h.")
    except Exception as e:
        return f"Couldn't get the weather: {e}"


# ── news headlines ──────────────────────────────────────────────────
def get_news(topic: str = "") -> str:
    if not config.NEWSAPI_KEY:
        return "News isn't configured. Set a NEWSAPI_KEY environment variable to enable it."
    params = {"apiKey": config.NEWSAPI_KEY, "language": "en", "pageSize": 5}
    if topic:
        params["q"] = topic
        url = "https://newsapi.org/v2/everything"
    else:
        params["country"] = "us"
        url = "https://newsapi.org/v2/top-headlines"
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        if not articles:
            return "No headlines found."
        return "Top headlines: " + " | ".join(a["title"] for a in articles[:5])
    except Exception as e:
        return f"Couldn't fetch news: {e}"


# ── helper: open a path with the OS default application ──────────────
def _open_with_default_app(path: Path):
    if sys.platform.startswith("win"):
        os.startfile(str(path))            # Windows only
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ── registry: schema (for the LLM) + the callable ───────────────────
def _schema(name, description, properties=None, required=()):
    return {
        "name": name,
        "description": description,
        "input_schema": {"type": "object", "properties": properties or {}, "required": list(required)},
    }


TOOLS = [
    {"fn": open_website, "schema": _schema(
        "open_website", "Open a website in the default browser. Accepts a full URL or a bare domain.",
        {"url": {"type": "string", "description": "URL or domain, e.g. github.com"}}, ["url"])},
    {"fn": play_youtube, "schema": _schema(
        "play_youtube", "Search YouTube for a song or video and start playing it.",
        {"query": {"type": "string", "description": "What to play, e.g. 'lofi hip hop'"}}, ["query"])},
    {"fn": play_local_media, "schema": _schema(
        "play_local_media", "Find and play a song or video stored on this computer, matched by part of its file name.",
        {"name": {"type": "string", "description": "Part of the file name to match"}}, ["name"])},
    {"fn": search_files, "schema": _schema(
        "search_files", "Search the user's Documents, Desktop and Downloads for files whose name contains the query.",
        {"query": {"type": "string", "description": "Part of the file name"}}, ["query"])},
    {"fn": open_file, "schema": _schema(
        "open_file", "Open a specific file by its full path using the default application.",
        {"path": {"type": "string", "description": "Full path to the file"}}, ["path"])},
    {"fn": get_datetime, "schema": _schema(
        "get_datetime", "Get the current local date and time.")},
    {"fn": get_weather, "schema": _schema(
        "get_weather", "Get the current weather for a city.",
        {"city": {"type": "string", "description": "City name, e.g. Lahore"}}, ["city"])},
    {"fn": get_news, "schema": _schema(
        "get_news", "Get current top news headlines, optionally about a topic.",
        {"topic": {"type": "string", "description": "Optional topic, e.g. 'technology'"}})},
]

# Convenience lookups used by the brain.
TOOL_FNS = {t["schema"]["name"]: t["fn"] for t in TOOLS}
TOOL_SCHEMAS = [t["schema"] for t in TOOLS]
