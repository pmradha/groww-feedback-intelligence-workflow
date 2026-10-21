"""Groww Feedback Intelligence review page.

Run from the repository root:

    pip install -r requirements-ui.txt
    streamlit run app.py

Opening the page runs scripts/validate_outputs.py and shows the existing
drafts. It does not approve them. Approve and Request Revision call
scripts/approve_outputs.py, which writes the local approval record.
Request Revision stays on this computer. Approve sends a signed webhook
only after that script exits successfully. HTTP success is not proof that
Notion or Gmail ran. The page does not send email.
"""

import csv
import hashlib
import hmac
import http.client
import importlib.util
import io
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
PULSE_PATH = ROOT / "outputs" / "weekly_product_pulse.md"
FEE_PATH = ROOT / "outputs" / "fee_explainer.md"
APPROVE_SCRIPT = ROOT / "scripts" / "approve_outputs.py"
REVIEW_CSV = ROOT / "data" / "groww_reviews_12_weeks.csv"
SUBMISSION_MARKER = ROOT / "outputs" / "activepieces_submission.json"
WEBHOOK_BODY = json.dumps(
    {"reporting_period": "M5"},
    separators=(",", ":"),
    ensure_ascii=True,
).encode("utf-8")
WEBHOOK_TIMEOUT_SECONDS = 10

PAGE_STYLE = """
<style>
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"] {
  background: #ffffff;
}
[data-testid="stMarkdown"] p,
[data-testid="stMarkdown"] li {
  color: #1c1c1c;
}
.gfi-title {
  margin: 0 0 1.35rem 0;
}
.gfi-title h1 {
  color: #1c1c1c !important;
  font-size: 1.45rem;
  font-weight: 650;
  line-height: 1.25;
  margin: 0 0 0.25rem 0;
}
.gfi-title p {
  color: #5f6b76 !important;
  font-size: 0.95rem;
  line-height: 1.4;
  margin: 0;
}
div[data-testid="stMarkdown"] h2,
div[data-testid="stHeading"] h3 {
  color: #1c1c1c !important;
  font-size: 1.05rem;
  font-weight: 650;
  line-height: 1.35;
}
div[data-testid="stCaptionContainer"] {
  color: #5f6b76;
}
[data-testid="stMarkdown"] a {
  color: #067a5a !important;
}
[data-testid="stMarkdown"] a:hover {
  color: #056348 !important;
}
[data-testid="stMetric"] {
  background: #f7f8f8;
  border: 1px solid #e6e8eb;
  border-radius: 8px;
  padding: 0.7rem 0.9rem 0.55rem;
}
[data-testid="stMetricLabel"] {
  color: #5f6b76;
}
[data-testid="stMetricValue"] {
  color: #1c1c1c;
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: #e6e8eb;
  border-radius: 8px;
  background: #ffffff;
}
[data-testid="stTab"][aria-selected="true"] p {
  color: #1c1c1c !important;
}
[data-testid="stTab"][aria-selected="false"] p {
  color: #5f6b76 !important;
}
.react-aria-SelectionIndicator {
  background-color: #00d09c !important;
}
[data-testid="stBaseButton-primary"] {
  background-color: #00d09c !important;
  border: 1px solid #00d09c !important;
}
[data-testid="stBaseButton-primary"] p {
  color: #14221c !important;
}
[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
  background-color: #00c492 !important;
  border-color: #00c492 !important;
}
[data-testid="stBaseButton-primary"]:disabled {
  background-color: #eef1f0 !important;
  border-color: #e4e7e6 !important;
}
[data-testid="stBaseButton-primary"]:disabled p {
  color: #8a928f !important;
}
input[type="checkbox"] {
  accent-color: #00d09c;
}
[data-testid="stCheckbox"] label[data-selected="true"] > div:first-of-type {
  background-color: #00d09c !important;
  border-color: #00d09c !important;
}
[data-testid="stCheckbox"] label[data-selected="true"] polyline {
  stroke: #14221c !important;
}
.block-container {
  padding-top: 2rem;
  padding-bottom: 2.75rem;
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
<div class="gfi-title">
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


def configured_secret(name):
    """Return a stripped secret string, or None. Never log the value."""
    try:
        value = st.secrets[name]
    except Exception:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def webhook_url_is_usable(url):
    if any(character in url for character in "\r\n\t "):
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https", "http"):
        return False
    if not parsed.hostname:
        return False
    if parsed.username or parsed.password:
        return False
    return True


def draft_content_hash():
    digest = hashlib.sha256()
    for path in (PULSE_PATH, FEE_PATH):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def load_submission_marker():
    if not SUBMISSION_MARKER.is_file():
        return None
    try:
        data = json.loads(SUBMISSION_MARKER.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"unreadable": True}
    if not isinstance(data, dict):
        return {"unreadable": True}
    return data


def save_submission_marker(marker):
    SUBMISSION_MARKER.parent.mkdir(parents=True, exist_ok=True)
    temporary = SUBMISSION_MARKER.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(marker, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, SUBMISSION_MARKER)


def accepted_by_hash(marker):
    if not isinstance(marker, dict) or marker.get("unreadable"):
        return {}
    raw = marker.get("accepted_by_hash")
    if not isinstance(raw, dict):
        return {}
    accepted = {}
    for key, value in raw.items():
        if isinstance(key, str) and (isinstance(value, int) or value is None):
            accepted[key] = value
    return accepted


def remember_submission(draft_hash, outcome, http_status, error_category=None):
    """Persist webhook state beside the approval record.

    scripts/approve_outputs.py rewrites outputs/approval_record.md from
    scratch, so the marker cannot live in that file without a breaking
    format change. Only an HTTP 2xx records the draft hash as accepted.
    """
    current = load_submission_marker()
    accepted = accepted_by_hash(current)
    if outcome == "accepted":
        accepted[draft_hash] = http_status
    if error_category not in FAILURE_CATEGORIES:
        error_category = None
    marker = {
        "accepted_by_hash": accepted,
        "last_draft_sha256": draft_hash,
        "last_http_status": http_status,
        "last_outcome": outcome,
        "last_error_category": error_category,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_submission_marker(marker)
    return marker


def outcome_for_status(code):
    if isinstance(code, int) and 200 <= code <= 299:
        return "accepted"
    return "failed"


FAILURE_CATEGORIES = frozenset({
    "timeout",
    "connection_refused",
    "dns",
    "tls",
    "connection_error",
})


def connection_failure_category(exc):
    """Map a connection failure to a fixed category. Never return exception text."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, ssl.SSLError):
        return "tls"
    if isinstance(exc, ConnectionRefusedError):
        return "connection_refused"
    if isinstance(exc, socket.gaierror):
        return "dns"
    return "connection_error"


def post_signed_webhook(url, secret, body, timeout):
    """POST the exact body bytes. Return outcome and status only.

    Timeout and connection errors are unknown: the server may have accepted
    the request. This function does not retry and does not read a body.
    """
    parsed = urllib.parse.urlparse(url)
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    path = parsed.path or "/"
    if parsed.query:
        path = path + "?" + parsed.query
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "x-signature": signature,
    }
    if parsed.scheme == "https":
        connection_class = http.client.HTTPSConnection
    else:
        connection_class = http.client.HTTPConnection
    connection = connection_class(parsed.hostname, port=parsed.port, timeout=timeout)
    try:
        connection.request("POST", path, body=body, headers=headers)
        response = connection.getresponse()
        code = response.status
        try:
            response.close()
        except OSError:
            pass
        return {"outcome": outcome_for_status(code), "http_status": code}
    except (TimeoutError, socket.timeout, http.client.HTTPException, OSError) as exc:
        return {
            "outcome": "unknown",
            "http_status": None,
            "error_category": connection_failure_category(exc),
        }
    finally:
        try:
            connection.close()
        except OSError:
            pass


def submit_activepieces():
    """Send the approved-draft webhook, or skip it when this hash already succeeded."""
    try:
        draft_hash = draft_content_hash()
    except OSError:
        return {
            "outcome": "failed",
            "http_status": None,
            "reason": "drafts_unreadable",
        }

    marker = load_submission_marker()
    if marker and marker.get("unreadable"):
        return {
            "outcome": "unknown",
            "http_status": None,
            "reason": "marker_unreadable",
        }
    prior = accepted_by_hash(marker)
    if draft_hash in prior:
        return {
            "outcome": "already_accepted",
            "http_status": prior.get(draft_hash),
            "reason": "duplicate",
        }

    url = configured_secret("ACTIVEPIECES_WEBHOOK_URL")
    secret = configured_secret("ACTIVEPIECES_HMAC_SECRET")
    missing = []
    if url is None or not webhook_url_is_usable(url):
        missing.append("ACTIVEPIECES_WEBHOOK_URL")
    if secret is None:
        missing.append("ACTIVEPIECES_HMAC_SECRET")
    if missing:
        try:
            remember_submission(draft_hash, "not_configured", None)
        except OSError:
            pass
        return {
            "outcome": "not_configured",
            "http_status": None,
            "reason": "secrets",
            "missing": missing,
        }

    result = post_signed_webhook(url, secret, WEBHOOK_BODY, WEBHOOK_TIMEOUT_SECONDS)
    marker_saved = True
    try:
        remember_submission(
            draft_hash,
            result["outcome"],
            result.get("http_status"),
            result.get("error_category"),
        )
    except OSError:
        marker_saved = False
    recorded = {
        "outcome": result["outcome"],
        "http_status": result.get("http_status"),
        "reason": "response",
        "marker_saved": marker_saved,
    }
    if result.get("error_category") in FAILURE_CATEGORIES:
        recorded["error_category"] = result["error_category"]
    return recorded


def webhook_feedback(webhook):
    """Map a webhook result to a level and a message with no secret values."""
    outcome = webhook.get("outcome")
    code = webhook.get("http_status")
    if outcome == "accepted":
        shown = code if isinstance(code, int) else "2xx"
        return (
            "accepted",
            "Local approval is recorded. "
            f"Webhook submission accepted (HTTP {shown}). "
            "This only means the Activepieces trigger accepted the request. "
            "It does not mean Notion was updated or a Gmail draft was created. "
            "Verify the Activepieces run. "
            "This page will not send these same drafts again. "
            "A marker on this computer does not stop another browser or user from submitting them. "
            "Activepieces-side idempotency is not documented."
            + (
                " The local duplicate guard could not be saved, so verify the run before approving again."
                if webhook.get("marker_saved") is False
                else ""
            ),
        )
    if outcome == "already_accepted":
        shown = f" (HTTP {code})" if isinstance(code, int) else ""
        return (
            "accepted",
            "Local approval is recorded. "
            f"Webhook submission was already accepted for these drafts{shown}, so the webhook was not called again. "
            "That earlier acceptance does not mean Notion or Gmail succeeded. "
            "Verify the Activepieces run. "
            "A marker on this computer does not stop another browser or user from submitting them. "
            "Activepieces-side idempotency is not documented.",
        )
    if outcome == "unknown" and webhook.get("reason") == "marker_unreadable":
        return (
            "unknown",
            "Local approval is recorded. "
            "The submission marker could not be read, so the webhook was not called. "
            "Webhook outcome unknown; verify the Activepieces run before retrying. "
            "No automatic retry was made.",
        )
    if outcome == "unknown":
        category = webhook.get("error_category")
        category_note = ""
        if category in FAILURE_CATEGORIES:
            category_note = f" Failure category: {category}."
        return (
            "unknown",
            "Local approval is recorded. "
            "Webhook outcome unknown; verify the Activepieces run before retrying. "
            "The request may have been accepted even though this page did not receive a response. "
            "No automatic retry was made."
            + category_note,
        )
    if outcome == "failed" and webhook.get("reason") == "drafts_unreadable":
        return (
            "failed",
            "Local approval is recorded. "
            "Webhook submission failed because the draft files could not be read. "
            "The external submission still needs attention. "
            "Notion and Gmail were not confirmed.",
        )
    if outcome == "not_configured":
        missing = [name for name in (webhook.get("missing") or []) if isinstance(name, str)]
        if len(missing) == 1:
            detail = f"because {missing[0]} is missing or not usable. "
        elif missing:
            detail = f"because {' and '.join(missing)} are missing or not usable. "
        else:
            detail = (
                "because ACTIVEPIECES_WEBHOOK_URL or "
                "ACTIVEPIECES_HMAC_SECRET is missing or not usable. "
            )
        return (
            "failed",
            "Local approval is recorded. "
            f"Webhook submission failed {detail}"
            "The external submission still needs attention. "
            "Notion and Gmail were not confirmed.",
        )
    if outcome == "failed" and isinstance(code, int):
        return (
            "failed",
            "Local approval is recorded. "
            f"Webhook submission failed (HTTP {code}). "
            "The external submission still needs attention. "
            "Notion and Gmail were not confirmed.",
        )
    return (
        "failed",
        "Local approval is recorded. "
        "Webhook submission failed before a response arrived. "
        "The external submission still needs attention. "
        "Notion and Gmail were not confirmed.",
    )


def standing_webhook_feedback():
    """Explain persisted webhook state. Does not call the network."""
    decision = approval_status()
    if decision == "Revision requested":
        return (
            "local",
            "Revision requested. That decision stays on this computer and does not call the webhook.",
        )
    if decision != "Approved":
        return None
    marker = load_submission_marker()
    if marker and marker.get("unreadable"):
        return webhook_feedback({"outcome": "unknown", "reason": "marker_unreadable"})
    try:
        draft_hash = draft_content_hash()
    except OSError:
        draft_hash = None
    accepted = accepted_by_hash(marker)
    if marker and draft_hash and draft_hash in accepted:
        return webhook_feedback(
            {
                "outcome": "accepted",
                "http_status": accepted.get(draft_hash),
            }
        )
    if not marker:
        return (
            "local",
            "Local approval is recorded. "
            "Webhook submission has not been confirmed. "
            "The external submission still needs attention.",
        )
    last_outcome = marker.get("last_outcome")
    if last_outcome in ("accepted", "already_accepted") and marker.get("last_draft_sha256") != draft_hash:
        return (
            "local",
            "Local approval is recorded. "
            "Webhook submission has not been confirmed for the current drafts. "
            "The external submission still needs attention.",
        )
    if last_outcome == "unknown":
        return webhook_feedback({
            "outcome": "unknown",
            "error_category": marker.get("last_error_category"),
        })
    if last_outcome == "not_configured":
        return webhook_feedback({"outcome": "not_configured", "missing": []})
    if last_outcome == "failed":
        return webhook_feedback(
            {"outcome": "failed", "http_status": marker.get("last_http_status")}
        )
    return (
        "local",
        "Local approval is recorded. "
        "Webhook submission has not been confirmed. "
        "The external submission still needs attention.",
    )


def show_webhook_feedback(level, message):
    if level == "unknown":
        st.warning(message)
    elif level == "failed":
        st.error(message)
    elif level == "accepted":
        st.info(message)
    else:
        st.info(message)


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
        "Request Revision stays on this computer. "
        "Approve writes the local approval record first and only then sends a signed webhook. "
        "A webhook response does not update Notion or create a Gmail draft by itself. "
        "Email is never sent."
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
        "It does not append a document, create an email draft, or send email. "
        "Request Revision does not call Activepieces. "
        "Approve calls the webhook only after the script exits successfully."
    )
    st.session_state.setdefault("gfi_phase", "idle")
    st.session_state.setdefault("gfi_queued_decision", None)
    st.session_state.setdefault("gfi_last_result", None)
    phase = st.session_state.gfi_phase
    in_progress = phase in ("locked", "running")
    if in_progress:
        st.info("A decision is in progress. Both buttons stay unavailable until it finishes.")
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
    if not in_progress:
        last_for_status = st.session_state.get("gfi_last_result")
        if last_for_status and last_for_status.get("status") == "recorded":
            if last_for_status.get("decision") == "revise":
                st.success(
                    "Revision requested. The reason is in the local approval record. "
                    "The webhook was not called. No email was sent."
                )
            else:
                webhook = last_for_status.get("webhook")
                if webhook:
                    show_webhook_feedback(*webhook_feedback(webhook))
                else:
                    show_webhook_feedback(
                        "failed",
                        "Local approval is recorded. "
                        "Webhook submission failed before a request was sent. "
                        "The external submission still needs attention.",
                    )
        elif last_for_status and last_for_status.get("status") == "blocked":
            st.error("The approval script was not run because validation failed.")
        elif last_for_status and last_for_status.get("status") == "acknowledgement_required":
            st.error("The approval script was not run. The warning was not acknowledged.")
        elif last_for_status and last_for_status.get("status") == "reason_required":
            st.error("The approval script was not run. A revision request needs a reason.")
        elif last_for_status and last_for_status.get("status") == "rejected":
            st.error("The approval script rejected the decision. No record was written.")
        elif not last_for_status:
            standing = standing_webhook_feedback()
            if standing:
                show_webhook_feedback(*standing)
    approve_disabled = in_progress or blocked or (warnings_present and not acknowledged)
    revise_disabled = in_progress or approve_disabled or not reason.strip()
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

    if phase == "idle" and approve_clicked:
        st.session_state.gfi_phase = "locked"
        st.session_state.gfi_queued_decision = "approve"
        st.rerun()
    elif phase == "idle" and revise_clicked:
        st.session_state.gfi_phase = "locked"
        st.session_state.gfi_queued_decision = "revise"
        st.rerun()
    elif phase == "locked":
        st.session_state.gfi_phase = "running"
        st.rerun()
    elif phase == "running":
        queued = st.session_state.gfi_queued_decision
        st.session_state.gfi_queued_decision = None
        st.session_state.gfi_phase = "idle"
        result = {
            "decision": queued,
            "status": None,
            "output": "",
            "webhook": None,
        }
        try:
            if queued not in ("approve", "revise"):
                result["status"] = "rejected"
            else:
                result["status"], result["output"] = submit_decision(
                    queued,
                    reason if queued == "revise" else "",
                    acknowledged,
                )
                if queued == "approve" and result["status"] == "recorded":
                    result["webhook"] = submit_activepieces()
        except Exception:
            if result["status"] is None:
                result["status"] = "rejected"
            if queued == "approve" and result["webhook"] is None:
                result["webhook"] = {
                    "outcome": "failed",
                    "http_status": None,
                    "reason": "unexpected",
                }
        st.session_state.gfi_last_result = result
        st.rerun()

    last = st.session_state.get("gfi_last_result") or {}
    if last.get("status") == "recorded":
        record_path = approve_outputs.DEFAULT_RECORD
        if record_path.is_file():
            st.markdown(record_path.read_text(encoding="utf-8"))
    decision_output = last.get("output") or ""
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
