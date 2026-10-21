# Sources

This list includes only sources used for the files in this repository. Official Groww fee pages have not been retrieved, so they are not listed.

## Groww Google Play reviews

| Item | Value |
| --- | --- |
| App | `com.nextbillion.groww` |
| Language | `en` |
| Country | `in` |
| Collector | `collect_groww_reviews.py`, using `google-play-scraper` |
| Sort | Newest first |
| Requested window | 28 July 2026–20 October 2026 |
| Reviews present | 28 July 2026–19 October 2026, 12,800 rows |
| Date timezone | Asia/Kolkata |

The collector calls the scraper with the app id, language, and country. It does not store a Play Store web URL, so none is listed here.

Purpose: review text, star rating, review time, and review ID for the weekly theme work.

Saved files:

- `data/groww_reviews_raw.csv`
- `data/groww_reviews_12_weeks.csv`
- `data/groww_weekly_coverage.csv`

The review files were copied from commit `51a7f76` in the separate mutual-fund FAQ repository. The `userName` and `userImage` columns were removed in this repository before publication. The weekly coverage file is unchanged.

Google Play can omit eligible reviews. The saved files are the collection that reached the requested start date, not a guarantee of every eligible review.

## Analysis derived from those reviews

`docs/m5-groww-feedback-analysis.md` interprets `data/groww_reviews_12_weeks.csv` with keyword rules. It is not an independent source and not an official Groww fee page.

## Official fee sources

Official Groww fee sources remain to be retrieved. The workflow requires two official links in the Fee Explainer. Add a URL here only after that page has been retrieved and checked.

HDFC Mutual Fund, SEBI, and AMFI pages used by the separate FAQ assistant are not fee evidence for this project and are not listed.
