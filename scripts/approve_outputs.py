#!/usr/bin/env python3
"""Human approval gate for the Product Pulse and Fee Explainer.

Run from the repository root:

    python3 scripts/approve_outputs.py

The script runs scripts/validate_outputs.py before asking for a decision.
A failed validation blocks approval and does not write a record.
Warnings are shown first. The reviewer must type this line before deciding:

    I acknowledge the warnings

The reviewer then chooses approve or revise. Both choices write
outputs/approval_record.md. Revise also stores the reviewer's reason.
Neither choice appends a document, creates an email draft, or sends email.

This script does not prove that the fee amounts are correct.
"""

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_outputs.py"
PULSE_PATH = ROOT / "outputs" / "weekly_product_pulse.md"
FEE_PATH = ROOT / "outputs" / "fee_explainer.md"
DEFAULT_RECORD = ROOT / "outputs" / "approval_record.md"

ACK_LINE = "I acknowledge the warnings"


def run_validator(validator_path):
    completed = subprocess.run(
        [sys.executable, str(validator_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = completed.stdout
    if completed.stderr.strip():
        output = output + ("\n" if output else "") + completed.stderr
    return completed.returncode, output


def classified_lines(output):
    passes, warnings, failures = [], [], []
    for line in output.splitlines():
        if line.startswith("PASS: "):
            passes.append(line[len("PASS: "):])
        elif line.startswith("WARNING: "):
            warnings.append(line[len("WARNING: "):])
        elif line.startswith("FAIL: "):
            failures.append(line[len("FAIL: "):])
    return passes, warnings, failures


def prompt(label):
    print(label, flush=True)
    line = sys.stdin.readline()
    if line == "":
        return None
    return line.strip()


def show_warnings(warnings):
    print()
    print("=" * 72)
    print("REVIEW WARNING")
    print("Validation passed with warnings. These are not a pass on the fee facts.")
    print("=" * 72)
    for index, warning in enumerate(warnings, start=1):
        print(f"{index}. {warning}")
    print("=" * 72)
    print()


def show_outputs():
    print("=" * 72)
    print("WEEKLY PRODUCT PULSE")
    print("=" * 72)
    print(PULSE_PATH.read_text(encoding="utf-8").rstrip())
    print()
    print("=" * 72)
    print("FEE EXPLAINER")
    print("=" * 72)
    print(FEE_PATH.read_text(encoding="utf-8").rstrip())
    print()


def write_record(path, decision, timestamp, exit_code, warnings, acknowledged, reason):
    lines = [
        "# Approval record",
        "",
        "Local review decision for the current Product Pulse and Fee Explainer.",
        "This file is not a document append and it is not an email draft.",
        "",
        f"- Decision: {decision}",
        f"- Timestamp (UTC): {timestamp}",
        f"- Validation exit code: {exit_code}",
        f"- Warnings acknowledged: {acknowledged}",
        f"- Document append: not run",
        f"- Email draft: not created",
        f"- Email sent: no",
        "",
    ]
    if reason:
        lines.extend(["## Revision reason", "", reason, ""])
    lines.append("## Validation warnings")
    lines.append("")
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "The validation script checks structure and citations.",
            "It does not prove that the fee amounts themselves are correct.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run validation, show the two drafts, and record approve or revise. "
            "Does not append a document, draft an email, or send email."
        )
    )
    parser.add_argument(
        "--record",
        type=Path,
        default=DEFAULT_RECORD,
        help="Where to write the decision. Default: outputs/approval_record.md",
    )
    parser.add_argument(
        "--validator",
        type=Path,
        default=VALIDATOR,
        help="Validation script to run first. Default: scripts/validate_outputs.py",
    )
    args = parser.parse_args()

    if not args.validator.is_file():
        print(f"Approval blocked. Validation script is missing: {args.validator}")
        return 1

    exit_code, output = run_validator(args.validator)
    print(output.rstrip())
    print()

    passes, warnings, failures = classified_lines(output)
    failed = exit_code == 1 or bool(failures) or exit_code not in (0, 2)
    if failed:
        print("Approval blocked. Validation reported a failure.")
        if failures:
            print("Failed checks:")
            for item in failures:
                print(f"- {item}")
        else:
            print(f"Validator exit code: {exit_code}")
        print("No approval record was written.")
        print("No document was appended, no email draft was created, and no email was sent.")
        return 1

    if warnings or exit_code == 2:
        show_warnings(warnings or ["Validation returned a warning without a WARNING line."])
        typed = prompt(f"Type exactly: {ACK_LINE}")
        if typed != ACK_LINE:
            print("Approval blocked. The warning was not acknowledged.")
            print("No approval record was written.")
            print("No document was appended, no email draft was created, and no email was sent.")
            return 1
        acknowledged = "yes"
    else:
        acknowledged = "not required"
        print("Validation passed with no warnings.")
        print()

    missing_outputs = [path for path in (PULSE_PATH, FEE_PATH) if not path.is_file()]
    if missing_outputs:
        print("Approval blocked. A draft is missing:")
        for path in missing_outputs:
            print(f"- {path.relative_to(ROOT)}")
        print("No approval record was written.")
        return 1

    show_outputs()
    decision = prompt("Decision (approve or revise):")
    if decision not in ("approve", "revise"):
        print("Approval blocked. The decision must be approve or revise.")
        print("No approval record was written.")
        print("No document was appended, no email draft was created, and no email was sent.")
        return 1

    reason = ""
    if decision == "revise":
        reason = prompt("Revision reason:")
        if not reason:
            print("Approval blocked. A revision request needs a reason.")
            print("No approval record was written.")
            print("No document was appended, no email draft was created, and no email was sent.")
            return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    recorded = "approved" if decision == "approve" else "revision_requested"
    write_record(
        args.record,
        recorded,
        timestamp,
        exit_code,
        warnings,
        acknowledged,
        reason,
    )
    print(f"Recorded decision: {recorded}")
    print(f"Record: {args.record}")
    if decision == "revise":
        print("Revision requested. Downstream actions were not run.")
    else:
        print("Approval recorded. Document append and email draft were not run.")
    print("No email was sent.")
    print(
        "Validation summary: "
        f"{len(passes)} {'pass' if len(passes) == 1 else 'passes'}, "
        f"{len(warnings)} {'warning' if len(warnings) == 1 else 'warnings'}, "
        f"{len(failures)} {'failure' if len(failures) == 1 else 'failures'}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
