# Sources

This list includes only sources used for the files in this repository.

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

Checked on 21 October 2026. Each page is on `groww.in` and prints the Bengaluru address used on Groww’s pages. The pricing page also names Groww Invest Tech Private Limited (formerly Nextbillion Technology Private Limited) and SEBI stock-broker registration INZ000301838. These pages are the sources for `outputs/fee_explainer.md`. They are not a fee audit of customer complaints.

| URL | What it supports |
| --- | --- |
| https://groww.in/pricing/ | Equity brokerage is the lower of ₹20 or 0.1% per executed order, minimum ₹5. Account maintenance is ₹0. Regulatory and statutory charges are listed separately. Delivery-sell DP charge: depository ₹3.50 (male) or ₹3.25 (female), plus Groww ₹16.50, with Groww’s portion ₹0 below ₹100 debit value. 18% GST applies to brokerage, DP charges, exchange transaction charges, the IPFT charge, and the SEBI turnover charge, among other listed items. Equity brokerage for the UPI Mandate balance is 1% of order value, with no maximum cap. |
| https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-pricing/what-is-the-charge-for-buy-order-delivery | Delivery brokerage is the lower of ₹20 or 0.1%, minimum ₹5, with a stated 2.5% regulatory cap on equity-delivery brokerage. The same DP split and sub-₹100 waiver. GST at 18% is not applied to STT or stamp duty. Delivery stamp duty, exchange transaction charges, SEBI turnover charge, NSE IPFT charge, and delivery STT are stated on this page. |
| https://groww.in/help/stocks,-f&o,-ipo-&-mtf/order/why-is-money-on-hold-for-stocks | The order amount and estimated charges are held. If the order is executed, the exact amount including charges is deducted at the end of the trading day. If it is not executed, the held amount is released. |
| https://groww.in/help/stocks,-f&o,-ipo-&-mtf/searchable/how-much-is-the-brokerage | Stock brokerage is ₹20 or 0.1%, whichever is lower. If that amount would be under ₹5, this article says the minimum is the lower of ₹5 or 2.5% of trade value. F&O brokerage is ₹20 per order. This minimum wording was not reconciled with the pricing page, so the explainer does not use it as the stated minimum. |

HDFC Mutual Fund, SEBI, and AMFI pages used by the separate FAQ assistant are not fee evidence for this project and are not listed.
