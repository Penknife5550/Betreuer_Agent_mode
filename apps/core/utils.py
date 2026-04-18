"""
Gemeinsame Utilities, die app-uebergreifend genutzt werden.
"""

from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings

from weasyprint import default_url_fetcher
from weasyprint.urls import URLFetchingError


def safe_get_by_id(model, pk):
    """
    Sucht einen Model-Eintrag per Primary-Key und liefert ``None``,
    wenn der PK ungueltig ist (``ValueError``) oder das Objekt nicht
    existiert. Einziger Usecase: HTMX-Lookup-Views, die bei fehlenden
    oder ungueltigen Parametern stillschweigend ein Leer-Template rendern
    sollen (kein 404, sondern Partial ohne Daten).
    """
    if pk in (None, ""):
        return None
    try:
        return model.objects.get(pk=pk)
    except (model.DoesNotExist, ValueError, TypeError):
        return None


def _resolve_allowed_roots():
    """Erlaubte File-System-Roots fuer WeasyPrint-Ressourcen."""
    return [
        Path(settings.BASE_DIR / "static").resolve(),
        Path(settings.STATIC_ROOT).resolve() if settings.STATIC_ROOT else None,
        Path(settings.MEDIA_ROOT).resolve() if settings.MEDIA_ROOT else None,
    ]


def safe_url_fetcher(url):
    """
    WeasyPrint-URL-Fetcher mit SSRF-Schutz.

    Erlaubt:
        - Relative Pfade (kein Schema) -- reicht WeasyPrint an den Default durch.
        - ``file://``-URLs innerhalb von ``BASE_DIR/static``, ``STATIC_ROOT``
          oder ``MEDIA_ROOT``.

    Blockiert:
        - ``http(s)://`` (verhindert SSRF auf interne Metadaten-Dienste).
        - ``file://`` ausserhalb der erlaubten Roots (Path-Traversal).
        - Alle anderen Schemata (``ftp://``, ``gopher://``, ``data:`` ausgenommen).

    WeasyPrint loest ``data:``-URIs intern selbst auf, daher werden sie hier
    normal durchgereicht.
    """
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    # Kein Schema -> relativer Pfad (WeasyPrint resolved gegen base_url).
    # data:-URIs werden direkt von WeasyPrint geparst.
    if scheme in ("", "data"):
        return default_url_fetcher(url)

    if scheme in ("http", "https"):
        raise URLFetchingError(
            f"Externe URLs sind aus Sicherheitsgruenden nicht erlaubt: {url}"
        )

    if scheme == "file":
        # Normalisiere den Pfad, dann prueffe Allowlist.
        raw_path = unquote(parsed.path or "")
        try:
            resolved = Path(raw_path).resolve()
        except (OSError, RuntimeError) as exc:
            raise URLFetchingError(
                f"Datei-URL konnte nicht aufgeloest werden: {url}"
            ) from exc

        allowed_roots = [root for root in _resolve_allowed_roots() if root is not None]
        for root in allowed_roots:
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            return default_url_fetcher(url)

        raise URLFetchingError(
            f"Datei-URL ausserhalb erlaubter Verzeichnisse: {url}"
        )

    raise URLFetchingError(
        f"URL-Schema '{scheme}' wird nicht unterstuetzt: {url}"
    )
