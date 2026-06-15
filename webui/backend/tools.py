#!/usr/bin/env python3
"""GUA tools — the agent layer (real capabilities beyond chatting).

These give GUA *grounded* answers instead of fabricated ones (R6, truthfulness):

  web_search()  — a real DuckDuckGo search (no API key).
  fetch_url()   — fetch and read a real web page's text.

Both run on the user's own machine with their own internet. Intent detection is
keyword + pattern matching (typo-tolerant); a production agent would use the
model's native tool/function calling (qwen2.5 supports it).
"""
from __future__ import annotations

import re

SEARCH_TRIGGERS = [
    "search the web", "search online", "search for", "look up", "look it up",
    "google ", "find online", "find out", "latest news", "what's the latest",
    "whats the latest", "current price", "today's", "on the web", "browse",
    "open the website", "open the webpage", "open the page", "go to",
    # current real-world status -> must check live, not answer from stale memory
    "still online", "still up", "still around", "still exist", "still alive",
    "still working", "still works", "is it down", "is down", "currently",
    "right now", "as of today", "this year", "recently",
]

# Typo-tolerant "search" verb: search, serch, searc, seach, searcg, sarch, saerch …
_SEARCH_RE = re.compile(r"\bs[ae]?[ae]?r?c?h?g?\b", re.IGNORECASE)
_SEARCH_WORDS = re.compile(
    r"\b(searc\w*|serch\w*|seach\w*|sarch\w*|saerch\w*|look\s*up|google|browse)\b",
    re.IGNORECASE,
)

# A bare domain/URL mentioned in the message (pitlog.io, example.com, foo.ai …).
_DOMAIN_RE = re.compile(
    r"\b((?:https?://)?(?:www\.)?[a-z0-9][a-z0-9-]*\.(?:io|com|org|net|ai|co|dev|app|xyz|gg|me|info|tech))\b",
    re.IGNORECASE,
)

_STRIP = [
    r"can you ", r"could you ", r"would you ", r"please ", r"for me", r"in a browser",
    r"and tell me what (it|its|it's) (is|about)", r"and tell me what it is",
    r"and tell (me )?what (it|its) is about", r"tell me what (it|it's|its) is",
    r"and open the website", r"open the website", r"open the webpage", r"open the page",
    r"search the web for ", r"search online for ", r"search for ", r"search the web ",
    r"can you search again", r"search again", r"look it up", r"look up ", r"google ",
    r"find online ", r"find out (about )?", r"go to ", r"on the web", r"browse",
    r"what is ", r"what's ", r"whats ", r"\?",
]


# "is reddit down", "are the servers up", "is X offline/working/available"
_STATUS_RE = re.compile(
    r"\b(is|are|was|does)\b.{0,40}\b(down|online|offline|up|working|available|alive|active)\b",
    re.IGNORECASE,
)


def wants_search(message: str) -> bool:
    low = message.lower()
    if any(t in low for t in SEARCH_TRIGGERS):
        return True
    if _SEARCH_WORDS.search(low):
        return True
    if _STATUS_RE.search(low):     # liveness/status question -> check live
        return True
    if _DOMAIN_RE.search(low):     # any website mentioned -> look it up for real
        return True
    return False


def find_url(message: str) -> str | None:
    """If the message names a website/domain, return a fetchable https URL."""
    m = _DOMAIN_RE.search(message)
    if not m:
        return None
    dom = m.group(1)
    if not dom.lower().startswith("http"):
        dom = "https://" + dom
    return dom


def extract_query(message: str) -> str:
    q = message
    for pat in _STRIP:
        q = re.sub(pat, " ", q, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", q).strip(" .")


def fetch_url(url: str, max_chars: int = 3500) -> str | None:
    """Fetch a page and return readable text (tags stripped). None on failure.
    Runs on the user's machine with their internet — this is GUA actually
    reading the web, not guessing."""
    try:
        import requests
        r = requests.get(url, timeout=12,
                          headers={"User-Agent": "Mozilla/5.0 (GUA agent)"})
        r.raise_for_status()
        html = r.text
        html = re.sub(r"(?is)<(script|style|noscript|svg|head).*?</\1>", " ", html)
        # keep the title explicitly — it usually states what the site is
        title = ""
        tm = re.search(r"(?is)<title[^>]*>(.*?)</title>", r.text)
        if tm:
            title = re.sub(r"\s+", " ", tm.group(1)).strip()
        text = re.sub(r"(?s)<[^>]+>", " ", html)
        text = re.sub(r"&[a-z]+;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if title:
            text = f"PAGE TITLE: {title}\n\n{text}"
        return text[:max_chars] if text else None
    except Exception:
        return None


def web_search(query: str, max_results: int = 5) -> list | dict:
    """Return [{title, url, snippet}] or {'error': ...}."""
    try:
        try:
            from ddgs import DDGS            # newer package name
        except ImportError:
            from duckduckgo_search import DDGS  # older package name
        out = []
        with DDGS() as d:
            for r in d.text(query, max_results=max_results):
                out.append({"title": r.get("title", ""),
                            "url": r.get("href") or r.get("url", ""),
                            "snippet": r.get("body", "")})
        return out
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def format_results(query: str, results: list) -> str:
    lines = [f'Live web search results for "{query}":']
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}\n    {r['snippet']}\n    Source: {r['url']}")
    return "\n".join(lines)
