"""CV anonymization: personal identifiers are replaced with placeholders before the text reaches the LLM or
the database. Runs locally (Presidio + spaCy), so the original never leaves the server.

Kept on purpose: companies, schools, titles, dates and skills, which the interview questions are built from."""

import re
import threading

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

PLACEHOLDERS = {
    "PERSON": "[NAME]", "EMAIL_ADDRESS": "[EMAIL]", "PHONE_NUMBER": "[PHONE]", "LOCAL_PHONE": "[PHONE]",
    "URL": "[LINK]", "PROFILE_HANDLE": "[LINK]", "LOCATION": "[LOCATION]", "STREET_ADDRESS": "[ADDRESS]", "NRP": "[PERSONAL]", "DOB": "[DOB]",
    "US_SSN": "[ID]", "US_PASSPORT": "[ID]", "IBAN_CODE": "[ID]", "CREDIT_CARD": "[ID]", "UK_NHS": "[ID]",
}
# tech words NER takes for names or links (e.g. "Jenkins" as a person, "ASP.NET" as a domain)
ALLOW = [
    "Jenkins", "Kafka", "Flask", "Django", "Ansible", "Grafana", "Kubernetes", "Terraform", "Redis", "Pandas",
    "Celery", "Selenium", "Jupyter", "Hadoop", "Spark", "Airflow", "Elixir", "Julia", "Ruby", "Rails", "Jest",
    "Helm", "Kibana", "Logstash", "Prometheus", "Docker", "Swift", "Kotlin", "Dart", "Flutter", "Vue",
    "ASP.NET", "VB.NET", ".NET", "socket.io", "Socket.IO", "Node.js", "Next.js", "Vue.js",
]
MIN_PHONE_DIGITS, MAX_PHONE_DIGITS = 9, 15  # 9+ digits: never a year range like "2019 - 2021"


class _LocalPhone(PatternRecognizer):
    """Phone numbers in any local format (Presidio's own recognizer only knows a few regions)."""

    def __init__(self):
        super().__init__("LOCAL_PHONE", patterns=[Pattern("phone", r"\+?\(?\d[\d\s().-]{7,}\d", 0.5)])

    def validate_result(self, pattern_text: str) -> bool:
        return MIN_PHONE_DIGITS <= sum(c.isdigit() for c in pattern_text) <= MAX_PHONE_DIGITS


_lock = threading.Lock()
_engines: tuple[AnalyzerEngine, AnonymizerEngine] | None = None


def _get() -> tuple[AnalyzerEngine, AnonymizerEngine]:
    global _engines
    with _lock:  # lazy: loading spaCy's large model takes a few seconds, once
        if _engines is None:
            analyzer = AnalyzerEngine()  # spaCy en_core_web_lg
            analyzer.registry.add_recognizer(_LocalPhone())
            analyzer.registry.add_recognizer(PatternRecognizer("DOB", patterns=[Pattern(
                "dob", r"(?i)\b(?:date of birth|d\.?o\.?b\.?|born(?: on)?)\s*[:\-]?\s*[\w ,./-]{0,20}\d{2,4}", 0.9,
            )]))
            analyzer.registry.add_recognizer(PatternRecognizer("STREET_ADDRESS", patterns=[Pattern(
                "street", r"\b\d{1,5}[A-Za-z]?,?\s+(?:[A-Z][\w'-]*\s+){1,4}(?:Road|Rd|Street|St|Avenue|Ave|Lane|Ln|"
                r"Boulevard|Blvd|Drive|Dr|Way|Court|Ct|Place|Pl|Marg|Path|Chowk)\b\.?", 0.6,
            )]))
            # profile ids written without a link: "GitHub: pbista", "LinkedIn - prashant-bista", "@pbista"
            analyzer.registry.add_recognizer(PatternRecognizer("PROFILE_HANDLE", patterns=[
                Pattern("labelled", r"(?i)\b(?:linked\s?in|git\s?hub|git\s?lab|twitter|x|stack\s?overflow|kaggle|"
                        r"leetcode|medium|behance|dribbble|hugging\s?face)(?:\s+(?:id|profile|handle|username))?"
                        r"\s*[:|/–-]\s*@?[\w][\w.-]*", 0.9),
                Pattern("at", r"(?<![\w.])@[A-Za-z0-9_][\w.-]{1,38}\b", 0.6),
            ]))
            _engines = analyzer, AnonymizerEngine()
        return _engines


def _header_name(text: str, contacts: list[str]) -> str | None:
    """A CV's first line is usually the name, often in capitals NER misses. Only trusted when one of its
    words is also in the email or a profile link, so a "Curriculum Vitae" or "Software Engineer" line isn't."""
    first = text.split("\n", 1)[0].strip()
    words = first.split()
    if not 2 <= len(words) <= 4 or not all(w.replace("-", "").replace("'", "").isalpha() for w in words):
        return None
    contact = " ".join(contacts).lower()
    return first if any(len(w) >= 3 and w.lower() in contact for w in words) else None


def anonymize_cv(text: str) -> str:
    analyzer, anonymizer = _get()
    results = analyzer.analyze(
        text, language="en", entities=list(PLACEHOLDERS), score_threshold=0.4, allow_list=ALLOW,
    )
    # every part of every detected name, wherever else it appears (headers, references, file footers)
    names = {text[r.start:r.end] for r in results if r.entity_type == "PERSON"}
    contacts = [text[r.start:r.end] for r in results if r.entity_type in ("EMAIL_ADDRESS", "URL")]
    if header := _header_name(text, contacts):
        names.add(header)
    out = anonymizer.anonymize(
        text, results, operators={k: OperatorConfig("replace", {"new_value": v}) for k, v in PLACEHOLDERS.items()},
    ).text
    tokens = {t for n in names for t in re.split(r"[\s.,]+", n) if len(t) >= 3}
    for t in sorted(tokens, key=len, reverse=True):  # case variants only: a name "Will" mustn't eat "will"
        variants = "|".join(re.escape(v) for v in {t, t.upper(), t.capitalize()})
        out = re.sub(rf"\b(?:{variants})\b", "[NAME]", out)
    return out
