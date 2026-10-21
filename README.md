# Groww Feedback Intelligence Workflow

This project turns public Groww app reviews into a weekly product note and a factual fee explainer. A person must approve both outputs before any document update or email draft.

The intended reader is a product manager who needs a short, checkable weekly readout, and a reviewer who needs to see which parts of that workflow already exist.

## Dataset

`collect_groww_reviews.py` collects English Google Play reviews for `com.nextbillion.groww` in India. The script requests reviews newest first. Google Play’s scraper has no date filter, so the script pages backward until it reaches the configured start date.

The requested window is 28 July 2026 through 20 October 2026. Calendar dates are Asia/Kolkata. The saved files contain 12,800 reviews from 28 July 2026 through 19 October 2026. The collection run that produced these files reported that pagination reached the 28 July start boundary and that every Monday–Sunday bucket in the window has at least one review.

| File | Contents |
| --- | --- |
| [data/groww_reviews_raw.csv](data/groww_reviews_raw.csv) | 12,800 collected reviews |
| [data/groww_reviews_12_weeks.csv](data/groww_reviews_12_weeks.csv) | The same reviews, with date and text-length fields |
| [data/groww_weekly_coverage.csv](data/groww_weekly_coverage.csv) | 13 Monday–Sunday counts, summing to 12,800 |
| [docs/m5-groww-feedback-analysis.md](docs/m5-groww-feedback-analysis.md) | Keyword theme analysis and dataset checks |

The review files were copied from commit [`51a7f76`](https://github.com/pmradha/mutual-fund-faq-rag-chatbot/commit/51a7f76cbbe6711848fb4a29ec42a282bbe4bcf3) in the separate mutual-fund FAQ repository. They were not regenerated for this repository. The collection run is also described in [pull request #1](https://github.com/pmradha/mutual-fund-faq-rag-chatbot/pull/1) of that repository. The `userName` and `userImage` columns were removed in this repository before publication.

## What is validated

The collector and the three CSV files are in place. Raw and filtered files have the same 12,800 review IDs, with no duplicates. Every filtered date falls inside 28 July–20 October 2026. The earliest review is 28 July 2026 and the latest is 19 October 2026. No weekly count is zero. The first bucket, 27 July–2 August, and the last bucket, 19–25 October, are partial weeks.

[docs/m5-groww-feedback-analysis.md](docs/m5-groww-feedback-analysis.md) is a keyword analysis of that file. The recurring specific themes are customer support, brokerage and charges, and ease of use. Quotes in that document cite review IDs and dates. Brokerage and charges are a recurring complaint in the text. That is not a verified fee audit.

There is no completed demo of the full workflow.

## Workflow

The intended design is in [Groww Feedback Intelligence Workflow.pdf](docs/workflow/Groww%20Feedback%20Intelligence%20Workflow.pdf) and [Groww Feedback Intelligence Workflow.png](docs/workflow/Groww%20Feedback%20Intelligence%20Workflow.png). The diagram is the target workflow. It is not evidence that every step has been built.

| Step | Status |
| --- | --- |
| 1. Use the validated Groww reviews CSV | Done. The 12-week file is in `data/`. |
| 2. Review intelligence: themes, top three, real quotes, fee confusion | Keyword analysis is done. Semantic clustering is not implemented. The final top-three selection for the weekly note is not a separate artifact. |
| 3. Fee evidence retrieval from official Groww sources | Not implemented. |
| 4. Generate the Weekly Product Pulse and the Fee Explainer | Not implemented. |
| 5. Validate length, quotes, review IDs, source links, and fee claims | Dataset checks are done. Output validation is not implemented. |
| 6. Human approval of both outputs | Specified. Not implemented. |
| 7. If changes are requested, return to generation | Specified. Not implemented. |
| 8. After approval, append a document record and create an internal email draft | Not implemented. The email must not be sent automatically. |

The Product Pulse is at most 250 words and contains the top three themes, three real review quotes, one key observation, and three product action ideas. The Fee Explainer is at most six factual bullets, with two official source links and a last-checked date. Neither output has been produced.

## Run the collector

From this repository root, with Python 3:

```sh
pip install -r requirements.txt
python3 collect_groww_reviews.py
```

`requirements.txt` lists `google-play-scraper>=1.2,<2` and `pandas>=2.2,<4`.

Rerunning the script sends new requests to Google Play and overwrites the three CSV files. The files already in `data/` are the validated 12-week collection. Leave them in place unless a new collection is intentional.

## Limitations

- Google Play can omit eligible reviews. Reaching the start date does not mean every eligible review was collected.
- The requested end date, 20 October 2026, has no review.
- The first and last weekly buckets are partial, so they are not comparable to full weeks.
- 4,174 of 12,800 reviews have text of five characters or fewer. Much of that text is generic praise such as “good” or “nice”.
- Keyword matching misses complaints written only in Hindi and can miss paraphrases. Counts in the analysis are a lower bound.
- `userName` and `userImage` were removed from both review files before publication. Those columns held display names and profile-image URLs, including a few names that were email addresses or phone numbers.
- Developer replies remain. They include the public address `support@groww.in`, and one reply includes Groww’s own callback number.
- A small number of review texts include a support ticket or complaint number. Review text was kept because the analysis depends on it.

## Publication note

This repository is public on GitHub and has no commits yet. The original CSV files, including display names and profile-image URLs, remain on a branch of the separate FAQ repository. The copies in this working tree do not include those two columns.
