"""Tests fuer den ``initials``-Template-Filter."""

from types import SimpleNamespace

from apps.core.templatetags.ui_extras import initials


def _user(first="", last="", username=""):
    return SimpleNamespace(first_name=first, last_name=last, username=username)


class TestInitials:
    def test_first_and_last_takes_first_letter_of_each(self):
        assert initials(_user("Max", "Meier")) == "MM"

    def test_only_first_takes_two_letters(self):
        assert initials(_user("Anna", "")) == "AN"

    def test_only_last_takes_two_letters(self):
        assert initials(_user("", "Schmidt")) == "SC"

    def test_only_username(self):
        assert initials(_user(username="admin")) == "AD"

    def test_one_char_username(self):
        assert initials(_user(username="a")) == "A"

    def test_empty_user_falls_back_to_question_mark(self):
        assert initials(_user()) == "?"

    def test_uppercase_on_lowercase_input(self):
        assert initials(_user("max", "meier")) == "MM"

    def test_strips_whitespace(self):
        assert initials(_user("  Max  ", "  Meier  ")) == "MM"

    def test_unicode_umlauts(self):
        assert initials(_user("Übung", "Ärger")) == "ÜÄ"

    def test_none_fields_do_not_crash(self):
        # Legacy-DB-Rows koennen first_name=None haben
        u = SimpleNamespace(first_name=None, last_name=None, username="bob")
        assert initials(u) == "BO"
