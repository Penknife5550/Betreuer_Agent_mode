"""
Custom template filters for number formatting.

de_money: Format a decimal as German currency string (75.000,00).
"""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def de_money(value):
    """
    Format a numeric value as a German-style decimal string with
    thousands separator (dot) and decimal comma.

    Examples:
        75000     → "75.000,00"
        1234.5    → "1.234,50"
        0         → "0,00"
        None      → ""
    """
    if value is None or value == "":
        return ""
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"))
        # Python's format with comma as thousands sep → "75,000.00" (English)
        formatted_en = f"{d:,.2f}"
        # Swap to German: "75,000.00" → "75.000,00"
        german = formatted_en.replace(",", "X").replace(".", ",").replace("X", ".")
        return german
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
