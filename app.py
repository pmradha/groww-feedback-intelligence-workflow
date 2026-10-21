"""Groww Feedback Intelligence review page.

Run from the repository root:

    pip install -r requirements-ui.txt
    streamlit run app.py

Opening the page runs scripts/validate_outputs.py and shows the existing
drafts. It does not approve them. Approve and Request Revision call
scripts/approve_outputs.py, which writes the local approval record.
The page does not append a document, create an email draft, or send email.
"""

import csv
import importlib.util
import io
import re
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
PULSE_PATH = ROOT / "outputs" / "weekly_product_pulse.md"
FEE_PATH = ROOT / "outputs" / "fee_explainer.md"
APPROVE_SCRIPT = ROOT / "scripts" / "approve_outputs.py"
REVIEW_CSV = ROOT / "data" / "groww_reviews_12_weeks.csv"

PAGE_STYLE = """
<style>
.gfi-header {
  background: #0b1f3a;
  color: #f7f9fc;
  border-radius: 12px;
  padding: 0.85rem 1.05rem 0.8rem;
  margin: 0 0 0.85rem 0;
}
.gfi-header h1 {
  color: #f7f9fc;
  font-size: 1.35rem;
  font-weight: 650;
  line-height: 1.25;
  margin: 0 0 0.15rem 0;
}
.gfi-header p {
  color: #d5deea;
  font-size: 0.92rem;
  line-height: 1.4;
  margin: 0;
}
div[data-testid="stMarkdown"] h2 {
  font-size: 1.05rem;
  font-weight: 650;
  line-height: 1.35;
  margin: 0.85rem 0 0.35rem 0;
}
div[data-testid="stHeading"] h3 {
  font-size: 1.02rem;
  font-weight: 650;
  line-height: 1.35;
}
section.main > div.block-container {
  padding-top: 1.25rem;
  padding-bottom: 2rem;
}
@media (max-width: 700px) {
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
}
</style>
"""

HEADER_HTML = """
<div class="gfi-header">
  <h1>Groww Feedback Intelligence</h1>
  <p>Customer feedback · Weekly review</p>
</div>
"""


def load_approval_script():
    spec = importlib.util.spec_from_file_location("approve_outputs", APPROVE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


approve_outputs = load_approval_script()


def read_draft(path):
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def without_document_h1(text):
    """Drop a draft's opening Markdown H1. The page header is the only title."""
    lines = text.splitlines()
    removed = False
    kept = []
    for line in lines:
        if not removed and line.startswith("# ") and not line.startswith("## "):
            removed = True
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def section_body(text, heading):
    match = re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text)
    if match is None:
        return None
    rest = text[match.end() :]
    nxt = re.search(r"(?m)^##\s+", rest)
    if nxt:
        rest = rest[: nxt.start()]
    return rest


def saved_review_rows():
    """Count rows in the existing 12-week CSV. Nothing is written."""
    with REVIEW_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def summary_figures(pulse):
    if not pulse:
        return "Unavailable", "Unavailable"
    count_match = re.search(r"([\d,]+)\s+English Google Play reviews", pulse)
    if count_match:
        reviews = count_match.group(1)
    else:
        reviews = f"{saved_review_rows():,}"
    themes_body = section_body(pulse, "Top three themes")
    if themes_body is None:
        themes = "Unavailable"
    else:
        themes = str(len(re.findall(r"(?m)^\d+\.\s+\S", themes_body)))
    return reviews, themes


def approval_status():
    """Read the approval record when it already exists. Do not create it."""
    record_path = approve_outputs.DEFAULT_RECORD
    if not record_path.is_file():
        return "Pending"
    text = record_path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^-\s+Decision:\s*(\S+)\s*$", text)
    if match is None:
        return "Pending"
    decision = match.group(1)
    if decision == "approved":
        return "Approved"
    if decision == "revision_requested":
        return "Revision requested"
    return decision


def describe_upload(uploaded):
    """Summarise an in-memory CSV. The bytes are not written to disk."""
    raw = uploaded.getvalue()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"error": "This file is not UTF-8 text. It was not saved."}
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        header = []
    row_count = sum(1 for _ in reader)
    return {
        "name": uploaded.name,
        "bytes": len(raw),
        "columns": [column.strip() for column in header],
        "rows": row_count,
    }


def validation_blocks(exit_code, failures):
    return exit_code == 1 or bool(failures) or exit_code not in (0, 2)


def run_displayed_validation():
    return approve_outputs.run_validator(approve_outputs.VALIDATOR)


def submit_decision(decision, reason, acknowledged):
    """Delegate the decision to scripts/approve_outputs.py.

    Returns a status and the script output. This function does not write
    the approval record itself.
    """
    exit_code, validation_output = run_displayed_validation()
    _passes, warnings, failures = approve_outputs.classified_lines(validation_output)
    if validation_blocks(exit_code, failures):
        return "blocked", validation_output
    warnings_present = bool(warnings) or exit_code == 2
    if warnings_present and not acknowledged:
        return "acknowledgement_required", validation_output
    if decision not in ("approve", "revise"):
        return "blocked", validation_output

    lines = []
    if warnings_present:
        lines.append(approve_outputs.ACK_LINE)
    lines.append(decision)
    if decision == "revise":
        cleaned = (reason or "").strip()
        if not cleaned:
            return "reason_required", validation_output
        lines.append(cleaned)

    completed = subprocess.run(
        [sys.executable, str(APPROVE_SCRIPT)],
        cwd=ROOT,
        input="\n".join(lines) + "\n",
        capture_output=True,
        text=True,
    )
    output = completed.stdout
    if completed.stderr.strip():
        output = output + ("\n" if output else "") + completed.stderr
    status = "recorded" if completed.returncode == 0 else "rejected"
    return status, output


def render_upload():
    with st.container(border=True):
        st.markdown(
            "Uploading a CSV does not currently regenerate the outputs, "
            "does not replace `data/`, and is not saved."
        )
        uploaded = st.file_uploader(
            "Upload a reviews CSV",
            type=["csv"],
            help="The file stays in this browser session. It is not written to data/.",
            key="review_csv",
        )
        if uploaded is None:
            return
        summary = describe_upload(uploaded)
        if "error" in summary:
            st.error(summary["error"])
            return
        st.write(
            f"In memory only: `{summary['name']}`, "
            f"{summary['rows']} data rows, {summary['bytes']} bytes."
        )
        st.write("Columns: " + ", ".join(summary["columns"]))
        needed = {"reviewId", "content"}
        missing = needed.difference(summary["columns"])
        if missing:
            st.warning(
                "This upload is missing "
                + ", ".join(sorted(missing))
                + ". The drafts below still come from the saved dataset."
            )
        else:
            st.success(
                "The upload has reviewId and content. "
                "The drafts below were not regenerated from it."
            )


def render_draft(path_label, text):
    if text is None:
        st.error(f"Missing {path_label}.")
        return
    with st.container(border=True):
        st.markdown(without_document_h1(text))


def render_approval():
    st.subheader("Approval status")
    st.write(approval_status())
    st.markdown(
        "Opening this page does not write an approval record. "
        "Activepieces is not connected. "
        "Email is never sent. "
        "No document is appended and no email draft is created."
    )

    st.subheader("Validation")
    st.write(
        "Results come from `scripts/validate_outputs.py`. "
        "A warning is not proof that the fee amounts are correct."
    )
    exit_code, validation_output = run_displayed_validation()
    passes, warnings, failures = approve_outputs.classified_lines(validation_output)
    blocked = validation_blocks(exit_code, failures)
    if passes:
        with st.expander(f"{len(passes)} passed checks"):
            for item in passes:
                st.write(item)
    for item in warnings:
        st.warning(item)
    for item in failures:
        st.error(item)
    if any("2.5%" in item or "not reconciled" in item.lower() for item in warnings):
        st.warning(
            "Unresolved brokerage minimum-charge discrepancy: "
            "a ₹5 minimum versus the lower of ₹5 or 2.5% of trade value. "
            "Those wordings are not reconciled, and this is not a pass on the fee facts."
        )
    if blocked:
        st.error(
            f"Validation failed (exit code {exit_code}). "
            "Approval is blocked until the failed checks are fixed."
        )
    elif not warnings and exit_code == 0:
        st.success("Validation passed with no warnings.")

    st.subheader("Decision")
    st.markdown(
        "Approve and Request Revision call `scripts/approve_outputs.py`. "
        "That script writes `outputs/approval_record.md` only after a decision. "
        "It does not append a document, create an email draft, or send email."
    )
    warnings_present = bool(warnings) or exit_code == 2
    acknowledged = True
    if warnings_present and not blocked:
        acknowledged = st.checkbox(approve_outputs.ACK_LINE, key="ack_warnings")
        if not acknowledged:
            st.info("Acknowledge the warning before approving or requesting revision.")
    reason = st.text_area(
        "Revision reason",
        placeholder="Required for Request Revision.",
        key="revision_reason",
    )
    approve_disabled = blocked or (warnings_present and not acknowledged)
    revise_disabled = approve_disabled or not reason.strip()
    approve_column, revise_column = st.columns(2)
    approve_clicked = approve_column.button(
        "Approve",
        type="primary",
        disabled=approve_disabled,
        key="approve_outputs",
    )
    revise_clicked = revise_column.button(
        "Request Revision",
        disabled=revise_disabled,
        key="request_revision",
    )
    if not reason.strip():
        st.caption("Request Revision stays unavailable until a reason is entered.")

    status = None
    decision_output = ""
    if approve_clicked:
        status, decision_output = submit_decision("approve", "", acknowledged)
    elif revise_clicked:
        status, decision_output = submit_decision("revise", reason, acknowledged)

    if status == "recorded":
        st.success("The approval script recorded the decision. No email was sent.")
        record_path = approve_outputs.DEFAULT_RECORD
        if record_path.is_file():
            st.markdown(record_path.read_text(encoding="utf-8"))
    elif status == "blocked":
        st.error("The approval script was not run because validation failed.")
    elif status == "acknowledgement_required":
        st.error("The approval script was not run. The warning was not acknowledged.")
    elif status == "reason_required":
        st.error("The approval script was not run. A revision request needs a reason.")
    elif status == "rejected":
        st.error("The approval script rejected the decision. No record was written.")
    if decision_output:
        st.subheader("Approval script output")
        st.code(decision_output)


def main():
    st.set_page_config(page_title="Groww Feedback Intelligence", layout="centered")
    st.markdown(PAGE_STYLE, unsafe_allow_html=True)
    st.markdown(HEADER_HTML, unsafe_allow_html=True)

    pulse = read_draft(PULSE_PATH)
    fee = read_draft(FEE_PATH)
    reviews, themes = summary_figures(pulse)
    left, middle, right = st.columns(3, gap="small")
    left.metric("Reviews analysed", reviews, border=True)
    middle.metric("Top themes", themes, border=True)
    right.metric("Review status", approval_status(), border=True)

    render_upload()

    pulse_tab, fee_tab, approval_tab = st.tabs(
        ["Product Pulse", "Fee Explainer", "Approval"]
    )
    with pulse_tab:
        render_draft("outputs/weekly_product_pulse.md", pulse)
    with fee_tab:
        render_draft("outputs/fee_explainer.md", fee)
    with approval_tab:
        render_approval()


main()
