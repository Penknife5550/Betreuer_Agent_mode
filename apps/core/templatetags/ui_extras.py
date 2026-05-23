"""
UI-Helfer fuer die App-Shell.

initials: Erzeugt zweistellige Initialen aus User (Vor-/Nachname bevorzugt,
          sonst die ersten zwei Zeichen des usernames). Wird im Template
          nur fuer eingeloggte User aufgerufen.
"""

from django import template

register = template.Library()


@register.filter
def initials(user):
    """Zweistellige Initialen fuer den Avatar im User-Dropdown."""
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()

    if first and last:
        return (first[0] + last[0]).upper()
    if first:
        return first[:2].upper()
    if last:
        return last[:2].upper()
    return (user.username[:2] or "?").upper()
