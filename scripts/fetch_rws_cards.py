"""Rebuild Moira's tracked Rider-Waite-Smith card assets from Wikimedia Commons.

The Commons API supplies every file URL; this script deliberately never constructs
thumbnail URLs.  It downloads the complete 78-file Geldard category, verifies the
mapping before replacing any local cards, then writes the tracked provenance
manifest.  Run it only when intentionally refreshing the deck.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "assets" / "cards"
CATEGORY = "Category:Rider-Waite-Smith_tarot_deck_(Geldard)"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "MoiraTarotAssetUpdater/1.0 (https://github.com/timoshinoleg-eng/moira)"
TARGET_SIZE = (350, 600)
REQUEST_DELAY_SECONDS = 1.1

sys.path.insert(0, str(ROOT))
from bot.tarot.deck import build_deck  # noqa: E402
from bot.visual.assets import card_image_path  # noqa: E402


def _request_json(params: dict[str, str]) -> dict:
    url = f"{COMMONS_API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                payload = response.read()
            # Keep the refresh polite: Wikimedia's API tells us the actual URL,
            # but the full deck still means 78 image requests.
            time.sleep(REQUEST_DELAY_SECONDS)
            return payload
        except HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 5:
                raise
            delay = int(exc.headers.get("Retry-After", "0") or 0) or (5 * attempt)
        except URLError:
            if attempt == 5:
                raise
            delay = 5 * attempt
        time.sleep(delay)
    raise RuntimeError("unreachable")


def _commons_title(card) -> str:
    """Return the exact Geldard filename for a Moira card."""
    name = card.name_en
    # The source category calls these two cards "One", while Moira's contract
    # correctly uses "Ace" for its display/content naming.
    if card.arcana == "minor" and card.rank == "ace" and card.suit in {"swords", "pentacles"}:
        name = f"One of {card.suit.title()}"
    return f"File:{name} (Rider-Waite Smith tarot deck).png"


def _target_name(card) -> str:
    path = card_image_path(card)
    if path is None:
        # card_image_path only returns None before an asset is present; rebuild
        # the same stable filename contract here without altering runtime code.
        from bot.visual.assets import RANK_NUM, SUIT_LETTER

        if card.arcana == "major":
            return f"m{int(card.id.split('_', 1)[1]):02d}.jpg"
        return f"{SUIT_LETTER[card.suit]}{RANK_NUM[card.rank]:02d}.jpg"
    return path.name


def _api_image_info(titles: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for start in range(0, len(titles), 40):
        data = _request_json(
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "titles": "|".join(titles[start : start + 40]),
                "prop": "imageinfo",
                "iiprop": "url|sha1|mime|size",
                "iiurlwidth": "750",
            }
        )
        for page in data["query"]["pages"]:
            if "missing" in page or not page.get("imageinfo"):
                raise RuntimeError(f"Commons metadata missing for {page['title']}")
            result[page["title"]] = page["imageinfo"][0]
    return result


def _fit_jpeg(source: bytes, destination: Path) -> None:
    with Image.open(io.BytesIO(source)) as original:
        rgba = original.convert("RGBA")
        # contain() scales only; it never crops the card border or artwork.
        fitted = ImageOps.contain(rgba, TARGET_SIZE, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", TARGET_SIZE, "white")
        x = (TARGET_SIZE[0] - fitted.width) // 2
        y = (TARGET_SIZE[1] - fitted.height) // 2
        canvas.paste(fitted, (x, y), fitted)
        canvas.save(destination, format="JPEG", quality=90, optimize=True, progressive=True)
    with Image.open(destination) as check:
        check.verify()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    deck = build_deck()
    if len(deck) != 78:
        raise RuntimeError(f"Expected a 78-card deck, got {len(deck)}")
    planned = {card.id: (_target_name(card), _commons_title(card)) for card in deck}
    if len({target for target, _source in planned.values()}) != 78:
        raise RuntimeError("Local card filename mapping is not one-to-one")

    category = _request_json(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "list": "categorymembers",
            "cmtitle": CATEGORY,
            "cmtype": "file",
            "cmlimit": "100",
        }
    )["query"]["categorymembers"]
    category_titles = {entry["title"] for entry in category}
    source_titles = {source for _target, source in planned.values()}
    if len(category_titles) != 78 or source_titles != category_titles:
        raise RuntimeError("Geldard category no longer matches the expected complete 78-card mapping")

    metadata = _api_image_info(sorted(source_titles))
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="moira-rws-") as tmp_name:
        temporary = Path(tmp_name)
        entries = []
        for card in deck:
            target_name, source_title = planned[card.id]
            info = metadata[source_title]
            thumb_url = info.get("thumburl")
            if not thumb_url:
                raise RuntimeError(f"Commons did not return an API thumbnail URL for {source_title}")
            target = temporary / target_name
            _fit_jpeg(_download(thumb_url), target)
            entries.append(
                {
                    "card_id": card.id,
                    "local_filename": target_name,
                    "commons_filename": source_title.removeprefix("File:"),
                    "commons_page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(source_title.replace(" ", "_")),
                    "source_url": info["url"],
                    "source_sha1": info["sha1"],
                    "sha256": _sha256(target),
                    "source_mime": info["mime"],
                    "source_dimensions": [info["width"], info["height"]],
                    "local_dimensions": list(TARGET_SIZE),
                }
            )

        if len({entry["sha256"] for entry in entries}) != 78:
            raise RuntimeError("Refusing to install duplicate local card artwork")

        for entry in entries:
            shutil.copy2(temporary / entry["local_filename"], CARDS_DIR / entry["local_filename"])

    manifest = {
        "deck": "Rider-Waite-Smith tarot deck (Geldard)",
        "category": "https://commons.wikimedia.org/wiki/Category:Rider-Waite-Smith_tarot_deck_(Geldard)",
        "license": "Public Domain Mark / PD-old, as represented on each Wikimedia Commons file page",
        "processing": "Commons API thumbnail URL -> Pillow contain resize with white padding -> JPEG 350x600; no crop",
        "cards": entries,
    }
    (CARDS_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    table = [
        "# Rider-Waite-Smith card provenance",
        "",
        "Moira bundles the complete 78-card **Rider-Waite-Smith tarot deck (Geldard)** from Wikimedia Commons. "
        "The Commons category lists 78 files; each file page represents the artwork as public domain. "
        "The local JPEGs are a proportional Pillow resize with white padding—no artwork or border is cropped.",
        "",
        "- Source category: <https://commons.wikimedia.org/wiki/Category:Rider-Waite-Smith_tarot_deck_(Geldard)>",
        "- License representation: Public Domain Mark / PD-old as shown by the corresponding Commons file page.",
        "- Rebuild: `python scripts/fetch_rws_cards.py` (Commons API URLs only; no hand-built thumbnail URL).",
        "- Machine-readable mapping, Commons original SHA-1, and local SHA-256: `manifest.json`.",
        "",
        "| Local file | Commons file | Local SHA-256 |",
        "|---|---|---|",
    ]
    table.extend(
        f"| `{entry['local_filename']}` | [{entry['commons_filename']}]({entry['commons_page']}) | `{entry['sha256']}` |"
        for entry in entries
    )
    (CARDS_DIR / "PROVENANCE.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    print(f"Installed and documented {len(entries)} RWS cards in {CARDS_DIR}")


if __name__ == "__main__":
    main()
