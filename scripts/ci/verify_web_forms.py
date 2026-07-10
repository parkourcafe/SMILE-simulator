"""Verify the public landing-form configuration without making network calls."""

from __future__ import annotations

import base64
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
HTML_PATH = ROOT / "web" / "index.html"
PROJECT_REF = "htclwrotnmhtbrdisqcu"


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_form: str | None = None
        self.fields: dict[str, dict[str, dict[str, str | None]]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "form":
            self.current_form = attributes.get("id")
            if self.current_form:
                self.fields[self.current_form] = {}
            return

        if self.current_form and tag in {"input", "select", "textarea"}:
            name = attributes.get("name")
            if name:
                self.fields[self.current_form][name] = attributes

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.current_form = None


def javascript_variable(html: str, name: str) -> str:
    match = re.search(rf'var {re.escape(name)} = "([^"]*)";', html)
    assert match, f"Missing JavaScript variable: {name}"
    return match.group(1)


def decode_jwt_payload(token: str) -> dict[str, object]:
    parts = token.split(".")
    assert len(parts) == 3, "Supabase anon key must be a JWT"
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))


def main() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")
    supabase_url = javascript_variable(html, "SUPABASE_URL")
    anon_key = javascript_variable(html, "SUPABASE_ANON_KEY")
    consent_version = javascript_variable(html, "CONSENT_VERSION")

    assert urlparse(supabase_url).hostname == f"{PROJECT_REF}.supabase.co"
    assert anon_key, "Supabase anon key must not be empty"
    assert not anon_key.startswith("sb_secret_"), "Secret key must never be in web/"
    assert consent_version.strip(), "Consent version must not be empty"

    claims = decode_jwt_payload(anon_key)
    assert claims.get("ref") == PROJECT_REF, "Anon key belongs to another project"
    assert claims.get("role") == "anon", "Only an anon key may be embedded in web/"
    assert int(claims.get("exp", 0)) > int(time.time()), "Supabase anon key is expired"

    parser = FormParser()
    parser.feed(html)
    expected_fields = {
        "form-user": {"name", "contact", "city", "interest", "comment", "consent"},
        "form-clinic": {
            "clinic_name",
            "city",
            "contact_person",
            "phone",
            "email",
            "flow",
            "interest",
            "message",
            "consent",
        },
    }
    for form_id, field_names in expected_fields.items():
        fields = parser.fields.get(form_id)
        assert fields is not None, f"Missing form: {form_id}"
        assert field_names <= fields.keys(), f"Missing fields in {form_id}"
        consent = fields["consent"]
        assert consent.get("type") == "checkbox"
        assert "required" in consent
        assert "checked" not in consent

    required_payload_fragments = {
        "locale: currentLang": 2,
        "consent_given: d.consent === 'on'": 2,
        "consent_version: CONSENT_VERSION": 2,
        "source: 'hero'": 2,
        "'Prefer': 'return=minimal'": 1,
    }
    for fragment, minimum_count in required_payload_fragments.items():
        assert html.count(fragment) >= minimum_count, (
            f"Missing form payload fragment: {fragment}"
        )

    print(
        "Landing forms use the expected public Supabase project and consent contract."
    )


if __name__ == "__main__":
    main()
