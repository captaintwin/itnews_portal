# utils/helpers.py
import hashlib
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; itnews-collector/1.0)"
REQUEST_TIMEOUT = 15  # seconds
IMG_EXT_WHITELIST = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def generate_id(url: str) -> str:
    """Детерминированный короткий ID на основе URL (10 символов)."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]


def _fetch_page(url: str):
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        r.raise_for_status()
        return r.text, r.url
    except Exception:
        return None, None


def fetch_main_image(page_url: str) -> str | None:
    """
    Возвращает URL главной картинки со страницы:
    1) og:image / rel=image_src
    2) эвристика по <img>
    """
    html, base_url = _fetch_page(page_url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")
    base = base_url or page_url

    # 1) OpenGraph
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return urljoin(base, og["content"])

    # 2) rel=image_src
    link_img = soup.find("link", rel="image_src")
    if link_img and link_img.get("href"):
        return urljoin(base, link_img["href"])

    # 3) эвристика по img
    best = None
    best_score = -10
    for i, img in enumerate(soup.find_all("img")):
        src = img.get("src") or img.get("data-src") or img.get("data-original")
        if not src or src.startswith("data:"):
            continue
        full = urljoin(base, src)

        score = 0
        # penalize логотипы/иконки/ads
        attrs = " ".join(map(str, [img.get("class"), img.get("id"), src])).lower()
        if any(k in attrs for k in ["logo", "icon", "sprite", "avatar", "advert", "ads"]):
            score -= 5
        # boost “hero/cover/main/featured”
        if any(k in attrs for k in ["hero", "cover", "main", "featured", "article", "post", "header"]):
            score += 5
        # чем раньше в документе — тем вероятнее
        score += max(0, 5 - i // 2)

        if score > best_score:
            best_score = score
            best = full

    return best


def _ext_from_url_or_ct(url: str, content_type: str | None) -> str:
    # по URL
    url_path = urlparse(url).path.lower()
    ext = os.path.splitext(url_path)[1]
    if ext in IMG_EXT_WHITELIST:
        return ext
    # по content-type
    if content_type:
        ct = content_type.lower()
        if "image/jpeg" in ct or "image/jpg" in ct:
            return ".jpg"
        if "image/png" in ct:
            return ".png"
        if "image/webp" in ct:
            return ".webp"
        if "image/gif" in ct:
            return ".gif"
    # дефолт
    return ".jpg"


def download_image(img_url: str, img_root: Path, news_id: str) -> str | None:
    """
    Качает изображение в img_root как preview_<id>.<ext>.
    Возвращает относительный путь (str) или None.
    """
    if not img_url:
        return None

    img_root.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(
            img_url,
            headers={"User-Agent": USER_AGENT, "Referer": img_url},
            timeout=REQUEST_TIMEOUT,
            stream=True,
        ) as r:
            r.raise_for_status()
            ext = _ext_from_url_or_ct(img_url, r.headers.get("Content-Type"))
            out_path = img_root / f"preview_{news_id}{ext}"
            tmp = out_path.with_suffix(out_path.suffix + ".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            tmp.rename(out_path)
            # вернем путь в виде "data/images/preview_<id>.ext"
            return str(out_path.as_posix())
    except Exception:
        return None
