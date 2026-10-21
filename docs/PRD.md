# Groww Feedback Intelligence Workflow — Milestone 5 PRD

## Problem

Groww’s public Google Play reviews mix a large amount of generic praise with a smaller set of specific complaints. Fee language shows up often enough to matter, but a review that says charges are high is not, by itself, a verified statement of Groww’s fees.

A product manager needs two checked outputs from the same weekly window: a short note on what customers actually wrote, and a factual explanation of the fee point grounded in official Groww sources. Those outputs should be reviewed by a person before they are appended to a document or placed in an email draft.

## Target user

The target user is a Groww product manager preparing a weekly product readout.

The user needs to see the top customer themes, the exact reviews behind them, and a fee explanation that can be traced to official sources. The user also needs a hard stop before any document or email action.

## Goals

- Use the validated 12-week review file as the input dataset.
- Identify the top three themes and keep real review quotes with their review IDs.
- Separate recurring fee confusion in the reviews from verified fee facts.
- Produce a Weekly Product Pulse and a Fee Explainer that meet the limits below.
- Require human approval before any document append or email draft.
- Never send the email automatically.

## Non-goals

- Replacing Groww’s support tools or replying to reviewers.
- Publishing investment advice, performance claims, or a recommendation to buy or sell.
- Treating keyword counts as the number of customers harmed.
- Treating one review’s fee allegation as an audited fee finding.
- Building the HDFC Mutual Fund FAQ assistant. That is a separate project.

## Scope

In scope:

- The English, India Google Play reviews for `com.nextbillion.groww` from 28 July 2026 through 19 October 2026. The review files were copied from commit `51a7f76` in the separate mutual-fund FAQ repository. The `userName` and `userImage` columns were removed in this repository before publication.
- Theme selection, quote extraction, and identification of fee confusion.
- Retrieval of official Groww fee sources.
- The two written outputs, validation, human approval, and the revision loop.
- After approval only: one structured document append and one internal email draft.

Out of scope:

- A live upload interface. The dataset is a file in `data/`.
- Automatic sending of email.
- Any MCP action before an approval exists.

## Workflow requirements

The design in `docs/workflow/Groww Feedback Intelligence Workflow.pdf` is the required sequence.

1. Start from the validated reviews CSV.
2. Identify themes, select the top three, extract real quotes, and identify recurring fee confusion.
3. Retrieve official Groww sources and verify fee facts.
4. Generate the Product Pulse and the Fee Explainer from the review analysis and the official fee evidence.
5. Validate both outputs.
6. A person reviews both outputs and either approves them or requests changes.
7. A request for changes returns to generation and validation. It does not trigger an external action.
8. Only an approval may append the structured record and create the internal email draft.

The record appended to the document includes the themes, quotes, fee issue, fee explanation, source links, and last-checked date. The email draft includes the Product Pulse and the fee explanation. The workflow must not send that email.

## Output specifications

### Weekly Product Pulse

- Maximum 250 words.
- Top three themes.
- Three real review quotes from the dataset.
- One key observation.
- Three product action ideas.

### Fee Explainer

- Maximum six bullets.
- Facts only, each traceable to a retrieved official source.
- Two official source links.
- A last-checked date.

Drafts of both outputs are in `outputs/`. `scripts/validate_outputs.py` checks their structure and citations. `scripts/approve_outputs.py` is the human gate. A local approval record exists only after a person runs that script. Document append and the email draft are still separate, unimplemented steps.

## Validation and safety

Before approval, validation must:

- Reject a Product Pulse over 250 words or a Fee Explainer over six bullets.
- Confirm each quote and review ID against `data/groww_reviews_12_weeks.csv`.
- Confirm both official links were retrieved and that each fee claim follows from those sources.
- Remove claims that the reviews or the official sources do not support.

`scripts/validate_outputs.py` implements the length, quote, review-ID, and source-link checks. It counts Product Pulse words with the title included. A quote must match the CSV text exactly, and it may be part of a longer review. Conflicting fee wording that is still unresolved is reported as a warning, not as a resolved fact. The script does not prove that the fee amounts are correct, and it does not re-fetch Groww’s pages.

`scripts/approve_outputs.py` runs that validator first. A failure blocks approval and writes no record. Warnings must be acknowledged in the typed line `I acknowledge the warnings`. The reviewer then approves or requests revision. A revision stores the reason and stops. An approval stores the decision and a UTC timestamp in `outputs/approval_record.md`. Neither decision appends a document, creates an email draft, or sends email.

Dataset checks already recorded in `docs/m5-groww-feedback-analysis.md` are not a substitute for this output validation.

No document append and no email draft may run before approval. The email draft is internal and is not sent by the workflow. Those two MCP actions are not implemented. The approval record is not either of those actions.

## Acceptance criteria

- The repository contains the validated raw, 12-week, and weekly CSV files from the 28 July–19 October 2026 collection.
- The theme analysis cites review IDs that exist in the 12-week file and states the limits of keyword matching.
- A future Product Pulse stays within 250 words and uses three quotes whose review IDs are in the dataset.
- A future Fee Explainer stays within six bullets and names two official Groww links plus a last-checked date.
- Fee sentences that are not supported by those links are absent.
- The repository has no document-append or email-draft artifact dated before an approval record.
- No workflow step sends email.

The dataset and theme-analysis criteria are met by the files now in the repository. Drafts of the Product Pulse and Fee Explainer are in `outputs/`. Validation and the local approval gate are implemented. Document append and the email draft are not implemented. No workflow step sends email. The approval record does not prove that the fee amounts are correct.

## Success metrics

No outcome metric has been defined or measured.

These are proposed checks for later, not results:

- 100% of Product Pulse quotes resolve to a review ID in the 12-week file.
- 100% of fee bullets cite one of the two retrieved official links.
- Zero document appends or email drafts occur without an approval record.

## Dependencies and constraints

- Input data is the collection already saved by `collect_groww_reviews.py`.
- The current fee draft uses public Groww pages already recorded in `docs/source-list.md`. Validation checks that the explainer’s Groww URLs are in that list. It does not prove the fee amounts.
- Document append and email draft are planned as MCP actions. No MCP connection is configured in this repository. Approval does not call them.
- The human approval gate is `scripts/approve_outputs.py`. It writes `outputs/approval_record.md` only when a person approves or requests revision. There is no approval record until that script is run.

## Known limitations

- The saved collection has 12,800 reviews, from 28 July 2026 through 19 October 2026. There is no review dated 20 October 2026.
- Google Play may omit eligible reviews. The collector stopped when pagination reached the start date. That does not prove the file contains every eligible review.
- Weekly buckets are Monday–Sunday. The weeks of 27 July and 19 October are partial.
- 4,174 reviews have text of five characters or fewer.
- Keyword themes miss some wording, including Hindi-only complaints.
- The brokerage-and-charges theme is a review pattern, not a fee audit.

## Current implementation status

| Capability | Status |
| --- | --- |
| Review collection and coverage checks | Implemented and validated |
| Keyword theme analysis with review IDs | Implemented in `docs/m5-groww-feedback-analysis.md` |
| Semantic clustering of themes | Planned, not yet implemented. The current analysis uses keyword rules. |
| Official Groww fee-source retrieval | Pages used for the fee draft are listed in `docs/source-list.md`. This is not an automated retrieval step, and it is not a fee audit. |
| Weekly Product Pulse | Draft in `outputs/weekly_product_pulse.md` |
| Fee Explainer | Draft in `outputs/fee_explainer.md`. The ₹5 and lower-of-₹5-or-2.5% minimums are not reconciled. |
| Automated validation of those outputs | Implemented in `scripts/validate_outputs.py`. It checks structure and citations. It does not prove fee amounts. |
| Human approval gate | Implemented in `scripts/approve_outputs.py`. It writes a local approve or revise record and stops before any MCP action. |
| Streamlit review UI | First version in `app.py`. It displays the existing drafts, runs the validator, and calls the approval script. An upload does not regenerate the drafts. Activepieces is not connected. |
| MCP document append and email draft | Not implemented. An approval record is not a document append or an email draft. |
| Automatic email send | Prohibited, and not implemented |
