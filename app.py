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
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
PULSE_PATH = ROOT / "outputs" / "weekly_product_pulse.md"
FEE_PATH = ROOT / "outputs" / "fee_explainer.md"
APPROVE_SCRIPT = ROOT / "scripts" / "approve_outputs.py"


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


def main():
    st.set_page_config(page_title="Groww Feedback Intelligence", layout="wide")
    st.title("Groww Feedback Intelligence")
    st.write(
        "Review the Weekly Product Pulse and the Fee Explainer. "
        "Opening this page checks the existing drafts. "
        "It does not approve them, append a document, or send email."
    )
    st.info(
        "These drafts were generated from the dataset already in `data/`. "
        "Uploading a CSV does not regenerate them, does not replace that dataset, "
        "and is not saved."
    )

    st.header("Upload Groww reviews")
    uploaded = st.file_uploader(
        "Choose a Groww reviews CSV",
        type=["csv"],
        help="The file stays in this browser session. It is not written to data/.",
    )
    if uploaded is not None:
        summary = describe_upload(uploaded)
        if "error" in summary:
            st.error(summary["error"])
        else:
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

    pulse = read_draft(PULSE_PATH)
    fee = read_draft(FEE_PATH)
    st.header("Weekly Product Pulse")
    if pulse is None:
        st.error("Missing outputs/weekly_product_pulse.md.")
    else:
        st.markdown(pulse)
    st.header("Fee Explainer")
    if fee is None:
        st.error("Missing outputs/fee_explainer.md.")
    else:
        st.markdown(fee)

    st.header("Validation")
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

    st.header("Decision")
    st.write(
        "Activepieces is not connected. "
        "Approve and Request Revision call `scripts/approve_outputs.py`. "
        "That script writes `outputs/approval_record.md` only after a decision. "
        "It does not append a document, create an email draft, or send email."
    )
    warnings_present = bool(warnings) or exit_code == 2
    acknowledged = True
    if warnings_present and not blocked:
        acknowledged = st.checkbox(approve_outputs.ACK_LINE)
        if not acknowledged:
            st.info("Acknowledge the warning before approving or requesting revision.")
    reason = st.text_area(
        "Revision reason",
        placeholder="Required for Request Revision.",
    )
    approve_disabled = blocked or (warnings_present and not acknowledged)
    revise_disabled = approve_disabled or not reason.strip()
    approve_column, revise_column = st.columns(2)
    approve_clicked = approve_column.button("Approve", disabled=approve_disabled)
    revise_clicked = revise_column.button(
        "Request Revision", disabled=revise_disabled
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


main()
