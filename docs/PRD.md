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

Neither output exists yet.

## Validation and safety

Before approval, validation must:

- Reject a Product Pulse over 250 words or a Fee Explainer over six bullets.
- Confirm each quote and review ID against `data/groww_reviews_12_weeks.csv`.
- Confirm both official links were retrieved and that each fee claim follows from those sources.
- Remove claims that the reviews or the official sources do not support.

Dataset checks already recorded in `docs/m5-groww-feedback-analysis.md` are not a substitute for this output validation.

No document append and no email draft may run before approval. The email draft is internal and is not sent by the workflow.

## Acceptance criteria

- The repository contains the validated raw, 12-week, and weekly CSV files from the 28 July–19 October 2026 collection.
- The theme analysis cites review IDs that exist in the 12-week file and states the limits of keyword matching.
- A future Product Pulse stays within 250 words and uses three quotes whose review IDs are in the dataset.
- A future Fee Explainer stays within six bullets and names two official Groww links plus a last-checked date.
- Fee sentences that are not supported by those links are absent.
- The repository has no document-append or email-draft artifact dated before an approval record.
- No workflow step sends email.

The first two criteria are met by the files now in the repository. The rest describe outputs and controls that are still to be built.

## Success metrics

No outcome metric has been defined or measured.

These are proposed checks for later, not results:

- 100% of Product Pulse quotes resolve to a review ID in the 12-week file.
- 100% of fee bullets cite one of the two retrieved official links.
- Zero document appends or email drafts occur without an approval record.

## Dependencies and constraints

- Input data is the collection already saved by `collect_groww_reviews.py`.
- Official fee retrieval depends on public Groww sources that have not been collected yet.
- Document append and email draft are planned as MCP actions. No MCP connection is configured in this repository.
- The human approval gate is a product requirement. There is no approval record yet.

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
| Official Groww fee-source retrieval | Not implemented |
| Weekly Product Pulse | Not produced |
| Fee Explainer | Not produced |
| Automated validation of those outputs | Not implemented |
| Human approval gate | Specified, not implemented |
| MCP document append and email draft | Not implemented |
| Automatic email send | Prohibited, and not implemented |
