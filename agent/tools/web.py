"""Outils web : recherche DuckDuckGo et récupération d'URL (anti-SSRF)."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "AgentAutonome/1.0 (+local; research bot; "
    "compatible; +https://localhost)"
)
FETCH_TIMEOUT = 15
FETCH_MAX_BYTES = 1_000_000
SEARCH_MAX_CHARS = 3000
FETCH_MAX_CHARS = 4000


def web_search(query: str, max_results: int = 5) -> str:
    """Recherche web via DuckDuckGo (package ``ddgs``).

    Args:
        query: Mots-clés.
        max_results: Nombre de résultats (1–10).

    Returns:
        Liste formatée titre / URL / snippet, ou message d'erreur.
    """
    q = (query or "").strip()
    if not q:
        return "ERREUR: query vide"

    try:
        n = int(max_results)
    except (TypeError, ValueError):
        n = 5
    n = max(1, min(n, 10))

    try:
        from ddgs import DDGS
    except ImportError:
        return "ERREUR: package ddgs manquant — pip install ddgs"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(q, max_results=n))
    except Exception as e:
        return f"ERREUR: recherche échouée: {e}"

    if not results:
        return "Aucun résultat"

    lines: list[str] = []
    for i, item in enumerate(results, 1):
        title = (item.get("title") or "").strip()
        href = (item.get("href") or item.get("link") or "").strip()
        body = (item.get("body") or item.get("snippet") or "").strip()
        lines.append(f"{i}. {title}\n   URL: {href}\n   {body}")

    text = "\n\n".join(lines)
    return text[:SEARCH_MAX_CHARS]


def _is_private_host(hostname: str) -> bool:
    """True si l'hôte résout vers une IP privée / loopback (blocage SSRF)."""
    host = hostname.strip("[]").lower()
    if host in {"localhost", "0.0.0.0"}:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def _validate_url(url: str) -> str | None:
    """Valide une URL publique http(s) ; renvoie un message d'erreur ou None."""
    raw = (url or "").strip()
    if not raw:
        return "ERREUR: url vide"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        return "ERREUR: schéma non autorisé (http/https uniquement)"
    if not parsed.hostname:
        return "ERREUR: hostname manquant"
    if _is_private_host(parsed.hostname):
        return "ERREUR: hôte privé / localhost interdit (SSRF)"
    return None


def _extract_html_text(html: str) -> str:
    """Extrait titre + texte visible d'une page HTML."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    for tag in soup.find_all(["nav", "footer", "header", "aside"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True) if main else ""
    # Collapse excessive blank lines
    lines = [ln for ln in (l.strip() for l in text.splitlines()) if ln]
    body = "\n".join(lines)

    if title:
        return f"Title: {title}\n\n{body}"
    return body


def fetch_url(url: str) -> str:
    """Télécharge une URL publique et renvoie le texte (HTML nettoyé ou brut).

    Protège contre SSRF (localhost / IP privées), timeout et taille max 1 Mo.
    """
    err = _validate_url(url)
    if err:
        return err

    try:
        with requests.get(
            url.strip(),
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            stream=True,
            allow_redirects=True,
        ) as resp:
            # Re-check final URL after redirects
            final_err = _validate_url(resp.url)
            if final_err:
                return final_err

            resp.raise_for_status()
            ctype = (resp.headers.get("Content-Type") or "").lower()
            encoding = resp.encoding or "utf-8"
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > FETCH_MAX_BYTES:
                    return "ERREUR: réponse trop volumineuse (>1 Mo)"
                chunks.append(chunk)
            raw = b"".join(chunks)

        try:
            text = raw.decode(encoding, errors="replace")
        except LookupError:
            text = raw.decode("utf-8", errors="replace")

        if "html" in ctype or text.lstrip().lower().startswith(
            ("<!doctype html", "<html")
        ):
            extracted = _extract_html_text(text)
            return extracted[:FETCH_MAX_CHARS] or "(page vide)"

        return text[:FETCH_MAX_CHARS] or "(contenu vide)"
    except requests.Timeout:
        return "ERREUR: timeout (15s)"
    except requests.RequestException as e:
        return f"ERREUR: fetch échoué: {e}"
