#!/usr/bin/env python3
"""Check the Milestone 5 Product Pulse and Fee Explainer drafts.

Run from the repository root:

    python3 scripts/validate_outputs.py

Word count: split the Product Pulse on whitespace. The title counts.
A quoted sentence must appear unchanged inside the matching CSV review.
It does not have to be the review's full text.

The script checks structure and citations. It does not prove that the
published fee amounts are correct, and it does not replace human approval.

Exit codes: 0 passed, 2 passed with review warnings, 1 failed.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PULSE_PATH = ROOT / "outputs" / "weekly_product_pulse.md"
FEE_PATH = ROOT / "outputs" / "fee_explainer.md"
CSV_PATH = ROOT / "data" / "groww_reviews_12_weeks.csv"
SOURCE_LIST_PATH = ROOT / "docs" / "source-list.md"

REVIEW_ID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
QUOTE = re.compile(r"[“\"](.+?)[”\"]")
GROWW_URL = re.compile(r"https://groww\.in/[^\s)>\]]+")
LAST_CHECKED = re.compile(
    r"Last checked:\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}"
)
NUMBERED_ITEM = re.compile(r"^\d+\.\s+\S")


def read_text(path):
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def section(text, heading):
    """Return the body under a Markdown heading, up to the next heading."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE
    )
    match = pattern.search(text)
    if match is None:
        return None
    rest = text[match.end():]
    next_heading = re.search(r"^##\s+", rest, re.MULTILINE)
    if next_heading:
        rest = rest[:next_heading.start()]
    return rest.strip()


def numbered_items(body):
    return [
        line.strip()
        for line in body.splitlines()
        if NUMBERED_ITEM.match(line.strip())
    ]


def load_reviews(path):
    reviews = {}
    duplicates = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "reviewId" not in reader.fieldnames:
            raise ValueError("CSV is missing the reviewId column.")
        if "content" not in reader.fieldnames:
            raise ValueError("CSV is missing the content column.")
        for row in reader:
            review_id = (row.get("reviewId") or "").strip()
            if not review_id:
                continue
            if review_id in reviews:
                duplicates.append(review_id)
            reviews[review_id] = row.get("content") or ""
    return reviews, duplicates


def official_urls(text):
    found = []
    for match in GROWW_URL.findall(text):
        cleaned = match.rstrip(".,;")
        if cleaned not in found:
            found.append(cleaned)
    return found


def fee_parts(text):
    marker = re.search(r"^##\s+Unresolved gaps\s*$", text, re.MULTILINE)
    if marker is None:
        return text, ""
    return text[:marker.start()], text[marker.end():]


class Report:
    def __init__(self):
        self.passes = []
        self.failures = []
        self.warnings = []

    def ok(self, message):
        self.passes.append(message)

    def fail(self, message):
        self.failures.append(message)

    def warn(self, message):
        self.warnings.append(message)


def check_pulse(report, text, reviews):
    if not text.lstrip().startswith("# "):
        report.fail("Product Pulse is missing its title.")
    word_count = len(text.split())
    if word_count <= 250:
        report.ok(
            f"Product Pulse word count is {word_count} "
            "(whitespace-separated words, title included; limit 250)."
        )
    else:
        report.fail(
            f"Product Pulse word count is {word_count}, above the 250 limit "
            "(whitespace-separated words, title included)."
        )

    themes = section(text, "Top three themes")
    if themes is None:
        report.fail("Product Pulse is missing the 'Top three themes' section.")
    else:
        items = numbered_items(themes)
        if len(items) == 3:
            report.ok("Product Pulse has exactly three themes.")
        else:
            report.fail(
                f"Product Pulse has {len(items)} themes; exactly three are required."
            )

    observation = section(text, "Key observation")
    if observation is None:
        report.fail("Product Pulse is missing the 'Key observation' section.")
    elif not observation.strip():
        report.fail("Product Pulse key observation is empty.")
    elif len(numbered_items(observation)) > 1:
        report.fail("Product Pulse has more than one key observation.")
    else:
        report.ok("Product Pulse has one key observation.")

    ideas = section(text, "Three product ideas")
    if ideas is None:
        report.fail("Product Pulse is missing the 'Three product ideas' section.")
    else:
        items = numbered_items(ideas)
        if len(items) == 3:
            report.ok("Product Pulse has exactly three product ideas.")
        else:
            report.fail(
                f"Product Pulse has {len(items)} product ideas; exactly three are required."
            )

    reviews_section = section(text, "Three reviews")
    if reviews_section is None:
        report.fail("Product Pulse is missing the 'Three reviews' section.")
        return

    entries = []
    for line in reviews_section.splitlines():
        id_match = REVIEW_ID.search(line)
        quote_match = QUOTE.search(line)
        if id_match is None and quote_match is None:
            continue
        if id_match is None or quote_match is None:
            report.fail(
                "A Product Pulse review line needs both a review ID and a quote: "
                + line.strip()
            )
            continue
        entries.append((id_match.group(0), quote_match.group(1)))

    if len(entries) == 3:
        report.ok("Product Pulse has exactly three quoted reviews.")
    else:
        report.fail(
            f"Product Pulse has {len(entries)} quoted reviews; exactly three are required."
        )

    for review_id, quote in entries:
        if review_id not in reviews:
            report.fail(f"Review ID {review_id} is not in the 12-week CSV.")
            continue
        if quote in reviews[review_id]:
            report.ok(
                f"Quote for {review_id} matches the CSV review text exactly."
            )
        else:
            report.fail(
                f"Quote for {review_id} is not an exact part of that CSV review."
            )


def check_fee(report, text, source_list):
    bullets_text, gaps_text = fee_parts(text)
    bullets = [
        line.strip()
        for line in bullets_text.splitlines()
        if line.strip().startswith("- ")
    ]
    if not bullets:
        report.fail("Fee Explainer has no factual bullets.")
    elif len(bullets) <= 6:
        report.ok(f"Fee Explainer has {len(bullets)} factual bullets (limit 6).")
    else:
        report.fail(
            f"Fee Explainer has {len(bullets)} factual bullets, above the limit of 6."
        )

    if LAST_CHECKED.search(text):
        report.ok("Fee Explainer includes a last-checked date.")
    else:
        report.fail(
            "Fee Explainer is missing a 'Last checked: D Month YYYY' date."
        )

    explainer_urls = official_urls(text)
    listed_urls = set(official_urls(source_list))
    official = [url for url in explainer_urls if url in listed_urls]
    missing = [url for url in explainer_urls if url not in listed_urls]
    if len(official) >= 2:
        report.ok(
            f"Fee Explainer cites {len(official)} distinct Groww URLs "
            "that are listed in docs/source-list.md."
        )
    else:
        report.fail(
            "Fee Explainer needs at least two distinct groww.in URLs "
            "that are also listed in docs/source-list.md. "
            f"Found {len(official)}."
        )
    for url in missing:
        report.fail(
            f"Fee Explainer URL is not in docs/source-list.md: {url}"
        )

    minimum_five = re.search(r"minimum of ₹5|₹5 minimum|minimum is ₹5", bullets_text)
    alternate_minimum = re.search(r"lower of ₹5 or 2\.5%", bullets_text)
    if minimum_five and alternate_minimum:
        report.fail(
            "Fee bullets state both the ₹5 minimum and the lower-of-₹5-or-2.5% "
            "minimum as settled facts. Those wordings are not reconciled."
        )

    if re.search(r"were reconciled|has been reconciled|wordings agree", text, re.I):
        report.fail(
            "Fee Explainer presents conflicting minimum wording as reconciled."
        )
    elif re.search(r"not reconciled", gaps_text, re.I):
        report.warn(
            "Unresolved fee wording remains open: the ₹5 minimum and the "
            "lower-of-₹5-or-2.5% wording are not reconciled. "
            "This is a review warning, not a pass on the fee facts."
        )
    elif "2.5%" in gaps_text:
        report.warn(
            "Fee Explainer leaves a 2.5% charge wording unresolved. "
            "This is a review warning, not a pass on the fee facts."
        )


def main():
    report = Report()
    pulse = read_text(PULSE_PATH)
    fee = read_text(FEE_PATH)
    source_list = read_text(SOURCE_LIST_PATH)

    if pulse is None:
        report.fail(f"Missing file: {PULSE_PATH.relative_to(ROOT)}")
    if fee is None:
        report.fail(f"Missing file: {FEE_PATH.relative_to(ROOT)}")
    if source_list is None:
        report.fail(f"Missing file: {SOURCE_LIST_PATH.relative_to(ROOT)}")
    if not CSV_PATH.is_file():
        report.fail(f"Missing file: {CSV_PATH.relative_to(ROOT)}")
        reviews = {}
    else:
        try:
            reviews, duplicates = load_reviews(CSV_PATH)
        except ValueError as exc:
            report.fail(str(exc))
            reviews = {}
            duplicates = []
        else:
            if duplicates:
                report.fail(
                    "12-week CSV has duplicate review IDs: "
                    + ", ".join(duplicates[:5])
                )
            else:
                report.ok(
                    f"12-week CSV loaded with {len(reviews)} unique review IDs."
                )

    if pulse is not None and reviews:
        check_pulse(report, pulse, reviews)
    if fee is not None and source_list is not None:
        check_fee(report, fee, source_list)

    for message in report.passes:
        print(f"PASS: {message}")
    for message in report.warnings:
        print(f"WARNING: {message}")
    for message in report.failures:
        print(f"FAIL: {message}")

    def count_label(count, singular, plural):
        word = singular if count == 1 else plural
        return f"{count} {word}"

    print(
        "\nSummary: "
        f"{count_label(len(report.passes), 'pass', 'passes')}, "
        f"{count_label(len(report.warnings), 'warning', 'warnings')}, "
        f"{count_label(len(report.failures), 'failure', 'failures')}."
    )
    print(
        "This check does not prove that the fee amounts themselves are correct."
    )
    if report.failures:
        return 1
    if report.warnings:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
