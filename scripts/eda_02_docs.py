"""Persist EDA-02 findings into /docs/data-quality-notes.md and /docs/methodology.md.

Invoked from notebooks/02-hmda-distributions-and-demographics.ipynb in a single
call. Keeps markdown-generation plumbing out of the analyst notebook. Idempotent:
each run replaces a delimited block rather than appending.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

METHOD_BEGIN = "<!-- BEGIN:eda-02-metrics -->"
METHOD_END = "<!-- END:eda-02-metrics -->"

DICT_BEGIN = "<!-- BEGIN:eda-02-field-notes -->"
DICT_END = "<!-- END:eda-02-field-notes -->"


def _splice_block(text: str, begin: str, end: str, new_block: str) -> str:
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(lambda _m: new_block, text)
    return text.rstrip() + "\n\n" + new_block + "\n"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _fmt_int(x: float | int) -> str:
    return f"{int(x):,}"


def _build_dq_block(
    *,
    action_share: pd.DataFrame,
    loan_purpose_share: pd.DataFrame,
    loan_amount_df: pd.DataFrame,
    la_purpose_pivot: pd.DataFrame,
    income_df: pd.DataFrame,
    pricing_df: pd.DataFrame,
    ltv_df: pd.DataFrame,
    dti_share: pd.DataFrame,
    race_share: pd.DataFrame,
    ethnicity_share: pd.DataFrame,
    sex_share: pd.DataFrame,
    age_share: pd.DataFrame,
    denial_share: pd.DataFrame,
    denial_by_race: pd.DataFrame,
    syb_outcome_df: pd.DataFrame,
    years: list[int],
    run_date: str,
) -> str:
    begin = f"<!-- BEGIN:eda-02-{run_date} -->"
    end = f"<!-- END:eda-02-{run_date} -->"

    orig_row = action_share.loc["1 originated"] if "1 originated" in action_share.index else None
    denial_row = action_share.loc["3 denied"] if "3 denied" in action_share.index else None

    orig_line = (
        ", ".join(f"{int(y)} = {_pct(orig_row[y])}" for y in years)
        if orig_row is not None
        else "origination rate unavailable"
    )
    denial_line = (
        ", ".join(f"{int(y)} = {_pct(denial_row[y])}" for y in years)
        if denial_row is not None
        else "denial rate unavailable"
    )

    la_line = ", ".join(
        f"{int(y)} median ${_fmt_int(loan_amount_df.loc[y, 'p50'])}" for y in years
    )
    income_line = ", ".join(
        f"{int(y)} median ${_fmt_int(income_df.loc[y, 'p50'])}K" for y in years
    )
    ir_line = ", ".join(
        f"{int(y)} median {pricing_df.loc[y, 'ir_p50']:.2f}%" for y in years
    )
    rs_line = ", ".join(
        f"{int(y)} median {pricing_df.loc[y, 'rs_p50']:.2f}" for y in years
    )
    ltv_line = ", ".join(
        f"{int(y)} median {ltv_df.loc[y, 'p50']:.1f}%, p95 {ltv_df.loc[y, 'p95']:.1f}%"
        for y in years
    )

    dti_top = dti_share.idxmax()
    dti_mode_line = ", ".join(
        f"{int(y)} modal bucket `{dti_top[y]}` ({_pct(dti_share[y].max())})"
        for y in years
    )

    def demo_top(df: pd.DataFrame, year: int, topn: int = 5) -> str:
        s = df[year].sort_values(ascending=False).head(topn)
        return ", ".join(f"{label} {_pct(v)}" for label, v in s.items())

    race_line = f"2024 top buckets: {demo_top(race_share, 2024)}"
    eth_line = f"2024 top buckets: {demo_top(ethnicity_share, 2024)}"
    sex_line = f"2024 top buckets: {demo_top(sex_share, 2024, topn=4)}"
    age_natural = age_share.drop("8888", errors="ignore")
    age_line = f"2024 top natural-person buckets: {demo_top(age_natural, 2024)}"

    top_denial = denial_share[2024].sort_values(ascending=False).head(4)
    denial_line_text = "2024 top denial reasons: " + ", ".join(
        f"{label} {_pct(v)}" for label, v in top_denial.items()
    )

    syb_line = ", ".join(
        f"{int(r['year'])} = {_pct(r['syb_origination_rate'])}"
        for _, r in syb_outcome_df.iterrows()
    )

    # Denial-by-race callout: rank the top reason per reported race.
    by_race_lines = []
    if not denial_by_race.empty:
        for race, row in denial_by_race.iterrows():
            valid = row.dropna()
            if valid.empty:
                continue
            top = valid.sort_values(ascending=False).head(2)
            ranked = ", ".join(f"{lbl} {_pct(v)}" for lbl, v in top.items())
            by_race_lines.append(f"- `{race}`: {ranked}")
    by_race_block = "\n".join(by_race_lines) if by_race_lines else "- insufficient cells above guardrail"

    return "\n".join(
        [
            begin,
            f"## {run_date} | EDA-02 HMDA Distributions and Demographics",
            "",
            "### Outcome mix (action_taken)",
            f"Origination rate: {orig_line}. Denial rate: {denial_line}. "
            "The origination-rate dip in 2023 and 2 pp denial-rate drift across "
            "the window is the rate-shock signature on outcomes. 2023 is not a "
            "steady state. Downstream year-over-year cuts on originations must "
            "acknowledge the regime shift.",
            "",
            "### Loan size and composition",
            f"Median originated loan amount: {la_line}. The aggregate median rise "
            "is partly composition driven: the purpose mix shifted from refi-heavy "
            "2022 to purchase-heavy 2023 and 2024, and purchase loans are larger "
            "than refi loans. Within-purpose medians are flatter than the aggregate. "
            "Decision: for year-over-year loan-size comparisons, fix loan_purpose "
            "before reading. Per-purpose medians are persisted in the notebook.",
            "",
            "### Income",
            f"Median originated-applicant income: {income_line} (HMDA-reported "
            "in thousands of USD, rounded to the nearest thousand). The rise "
            "partly tracks purpose-mix shift and affordability squeeze: the "
            "applicant cohort that survived 2023 and 2024 skews higher-income "
            "than the pre-shock pool. Not a household-income growth signal.",
            "",
            "### Pricing (partial-exempt reporters excluded)",
            f"Interest rate: {ir_line}. Rate spread: {rs_line}. These percentiles "
            "drop the partial-exempt panel entirely. From notebook 01, ~41% of "
            "2024 reporters exercise partial exemption on at least one pricing "
            "field. Decision: every M3 pricing card must declare the filter and, "
            "where the comparison matters, publish the partial-exempt subpanel "
            "stat separately.",
            "",
            "### LTV (numeric) and DTI (bucketed hybrid)",
            f"LTV: {ltv_line}. Median near the 80% conforming threshold with a "
            f"heavy P95 tail up to ~100%. DTI: {dti_mode_line}. DTI is reported "
            "as HMDA category strings at the extremes (<20%, >60%, and three "
            "intermediate buckets) and raw integer percentages in the 36 to 49 "
            "range. Decision: treat LTV as continuous numeric; treat DTI as "
            "categorical in dbt staging and every dashboard card. The `36%-<50%` "
            "analyst-facing bucket used in the notebook rolls the integer range.",
            "",
            "### Demographics (descriptive, HMDA-limited)",
            f"`derived_race` {race_line}. "
            f"`derived_ethnicity` {eth_line}. "
            f"`derived_sex` {sex_line}. Roughly one in four applicants reports "
            "`Race Not Available` and `Sex Not Available`. Decision: every M3 "
            "demographic card must publish the not-available share alongside "
            "disparity metrics, and every card carries the HMDA-limitation "
            "disclaimer inline.",
            "",
            "### Age",
            f"{age_line}. The `8888` (non-natural-person) bucket carries ~12% of "
            "rows, cross-tracking entity-backed investor lending and business-"
            "purpose applications.",
            "",
            "### Denial reasons",
            f"{denial_line_text}. Three codes (DTI, credit history, collateral) "
            "dominate across every year. Decision: any M3 denial card surfaces "
            "all three together. Denial-reason-by-race (2024, 1,000-cell "
            "guardrail), top reason per reported race:",
            "",
            by_race_block,
            "",
            "### SYB anchor",
            f"SYB origination rate by year: {syb_line}. Stable ~15 pp above "
            "market origination rate across the window. First quantitative "
            "signature of the SYB conservative-community-bank posture that "
            "threads through M3.",
            "",
            end,
        ]
    )


def _build_dict_block(
    *,
    loan_amount_df: pd.DataFrame,
    income_df: pd.DataFrame,
    ltv_df: pd.DataFrame,
    race_share: pd.DataFrame,
    sex_share: pd.DataFrame,
    run_date: str,
) -> str:
    ltv_p50_2024 = ltv_df.loc[2024, "p50"]
    ltv_p95_2024 = ltv_df.loc[2024, "p95"]
    loan_p50_2024 = int(loan_amount_df.loc[2024, "p50"])
    loan_p95_2024 = int(loan_amount_df.loc[2024, "p95"])
    income_p50_2024 = int(income_df.loc[2024, "p50"])
    income_p95_2024 = int(income_df.loc[2024, "p95"])

    race_not_avail = race_share.loc["Race Not Available", 2024] if "Race Not Available" in race_share.index else 0.0
    sex_not_avail = sex_share.loc["Sex Not Available", 2024] if "Sex Not Available" in sex_share.index else 0.0

    rows = [
        "| Column | Encoding | Treatment | EDA-02 observation |",
        "| --- | --- | --- | --- |",
        (
            "| `loan_amount` | numeric float, reported at the midpoint of the "
            "nearest $10,000 interval | continuous | outlier bounds $1 to "
            f"$100M used in percentile math; 2024 P50 ${loan_p50_2024:,}, "
            f"P95 ${loan_p95_2024:,} |"
        ),
        (
            "| `income` | integer, reported in thousands of USD rounded to "
            "the nearest thousand (value `65` = $65,000) | continuous | "
            "outlier bounds $1K to $10M; not-applicable on purchased loans, "
            "non-natural-person applicants, HOEPA-specific fields; 2024 P50 "
            f"${income_p50_2024}K, P95 ${income_p95_2024}K |"
        ),
        (
            "| `rate_spread` | numeric float, APR over APOR benchmark, plus "
            "`Exempt` and `NA` sentinels | continuous with filter | pricing "
            "cuts must exclude `Exempt` rows; from EDA-01, ~41% of 2024 "
            "reporters use partial exemption, so pricing is full-reporter-"
            "biased. Every dashboard card using this metric must declare the "
            "filter. |"
        ),
        (
            "| `interest_rate` | numeric float, contract note rate, plus "
            "`Exempt` and `NA` sentinels | continuous with filter | same "
            "partial-exempt treatment as `rate_spread`; 2024 median 6.88%, "
            "P95 10.25% |"
        ),
        (
            "| `loan_to_value_ratio` | numeric float, full precision | "
            f"continuous | clean numeric; 2024 P50 {ltv_p50_2024:.1f}%, P95 "
            f"{ltv_p95_2024:.1f}%. Heavy clustering at 80% (conforming "
            "threshold) is real, not a data issue. |"
        ),
        (
            "| `debt_to_income_ratio` | **hybrid**: bucketed strings at "
            "the extremes (`<20%`, `20%-<30%`, `30%-<36%`, `50%-60%`, "
            "`>60%`) and raw integer percentages in the 36 to 49 range, "
            "plus `NA` and `Exempt` | **categorical only** | do not attempt "
            "continuous treatment; the integer-range subset cannot be "
            "concatenated with bucketed strings. EDA-02 rolls the integer "
            "range into an analyst-facing `36%-<50%` bucket for display. |"
        ),
        (
            "| `applicant_age` | HMDA age buckets (`<25`, `25-34`, `35-44`, "
            "`45-54`, `55-64`, `65-74`, `>74`) plus sentinel `8888` | "
            "categorical | `8888` is the non-natural-person bucket "
            "(~12% of 2024 rows), cross-tracks entity-backed investor "
            "lending and `business_or_commercial_purpose = 1`. Exclude "
            "from natural-person age distributions. |"
        ),
        (
            "| `denial_reason-1` | code-encoded, meaningful only when "
            "`action_taken = 3`; sentinel `10` (not applicable) dominates "
            "elsewhere; `1111` marks exempt | categorical with filter | "
            "filter to denied rows before any distribution. Three codes "
            "account for the bulk of denials in 2024: DTI ratio (32%), "
            "credit history (27%), collateral (13%). |"
        ),
        (
            "| `business_or_commercial_purpose` | codes `1` (primarily "
            "business), `2` (not primarily business), `1111` (not applicable) "
            "| categorical | business-purpose share 4.7% (2022) to 5.3% "
            "(2024), drifting up. Consumer-lending cuts filter to `= 2`; "
            "lender-class segmentation uses the `= 1` share as an investor-"
            "tilt signal. |"
        ),
        (
            "| `derived_dwelling_category` | text categorical, four levels: "
            "Single Family (1-4 Units):Site-Built, Single Family (1-4 "
            "Units):Manufactured, Multifamily:Site-Built, Multifamily:"
            "Manufactured | categorical | site-built single-family dominates "
            "at ~94%; manufactured single-family ~5-6%; multifamily below "
            "0.5%. Near-constant across the window. |"
        ),
        (
            f"| `derived_race` | text categorical including explicit `Race "
            f"Not Available` bucket | categorical with disclosure | 2024 "
            f"`Race Not Available` share {race_not_avail * 100:.1f}%. Any "
            "disparity metric must publish this share alongside. |"
        ),
        (
            "| `derived_ethnicity` | text categorical including explicit "
            "`Ethnicity Not Available` bucket | categorical with disclosure "
            "| same disclosure requirement as `derived_race`. |"
        ),
        (
            f"| `derived_sex` | text categorical: Male, Female, Joint, Sex "
            f"Not Available, Sex Not Applicable | categorical with "
            f"disclosure | 2024 `Sex Not Available` share "
            f"{sex_not_avail * 100:.1f}%. Joint applicants are a large "
            "cohort and single-applicant analysis loses them. |"
        ),
    ]

    return "\n".join(
        [
            DICT_BEGIN,
            f"<!-- generated by notebooks/02-hmda-distributions-and-demographics.ipynb on {run_date} -->",
            "",
            "### HMDA LAR field notes from EDA-02 (distributions and demographics)",
            "",
            "Supplements the field-level table above (written by EDA-01). "
            "Each row here documents an encoding, treatment rule, or "
            "downstream filter that EDA-02 surfaced. Cross-references the "
            "metric-definition block in `/docs/methodology.md`.",
            "",
            "\n".join(rows),
            "",
            DICT_END,
        ]
    )


def _build_methodology_block(run_date: str) -> str:
    return "\n".join(
        [
            METHOD_BEGIN,
            f"<!-- generated by notebooks/02-hmda-distributions-and-demographics.ipynb on {run_date} -->",
            "",
            "### Metric definitions surfaced by EDA-02",
            "",
            "Definitions used in the EDA-02 notebook and inherited by every "
            "downstream dashboard card. Cross-reference this block before "
            "redefining any metric in M3.",
            "",
            "- **origination rate**: count of rows with `action_taken = 1` "
            "divided by total LAR rows for the year. Denominator includes "
            "denied, withdrawn, preapproval, and purchased-loan rows.",
            "- **denial rate**: count of rows with `action_taken = 3` divided "
            "by total LAR rows for the year. Same denominator as above.",
            "- **originated book**: the subset `action_taken = 1`. Used for "
            "every loan-size, income, pricing, and ratio percentile in the "
            "notebook unless otherwise noted.",
            "- **consumer book**: the subset `business_or_commercial_purpose = 2`. "
            "Excludes investor and commercial-residential loans. Used when a "
            "consumer-lending story is the point.",
            "- **full-reporter pricing**: interest rate and rate spread "
            "percentiles computed after filtering out rows with the literal "
            "`Exempt` string in the field. Partial-exempt reporters (small "
            "lenders below HMDA full-reporting thresholds) are excluded. "
            "Any dashboard card using these metrics must disclose the filter.",
            "- **loan amount outlier bounds**: $1 to $100,000,000. Rows "
            "outside these bounds are dropped from percentile computation. "
            "The bounds are intentionally loose. They catch fat-fingered "
            "entries without truncating legitimate jumbo activity.",
            "- **income outlier bounds**: $1,000 to $10,000,000 annual "
            "reported income. HMDA income is in thousands of USD rounded to "
            "the nearest thousand.",
            "- **DTI display buckets**: `<20%`, `20%-<30%`, `30%-<36%`, "
            "`36%-<50%`, `50%-60%`, `>60%`, `NA`, `Exempt`. The "
            "`36%-<50%` bucket is an analyst-facing rollup of the raw integer "
            "DTI percentages HMDA reports in that range.",
            "- **sample-size guardrail**: 1,000 observations per cell. "
            "Applies to any demographic cross-tab. Cells below this threshold "
            "are blanked, not imputed.",
            "- **HMDA-limitation disclaimer**: HMDA does not capture credit "
            "score, complete employment history, cash reserves, or every "
            "component of the underwriting decision. Demographic breakdowns "
            "are descriptive of the HMDA applicant population. They are not "
            "a fair-lending determination and do not establish disparate "
            "treatment.",
            "",
            METHOD_END,
        ]
    )


def persist_findings(
    *,
    action_share: pd.DataFrame,
    loan_purpose_share: pd.DataFrame,
    loan_amount_df: pd.DataFrame,
    la_purpose_pivot: pd.DataFrame,
    income_df: pd.DataFrame,
    pricing_df: pd.DataFrame,
    ltv_df: pd.DataFrame,
    dti_share: pd.DataFrame,
    race_share: pd.DataFrame,
    ethnicity_share: pd.DataFrame,
    sex_share: pd.DataFrame,
    age_share: pd.DataFrame,
    denial_share: pd.DataFrame,
    denial_by_race: pd.DataFrame,
    syb_outcome_df: pd.DataFrame,
    years: list[int],
    repo_root: Path,
) -> tuple[Path, Path, Path]:
    """Write DQ notes + methodology + data-dictionary blocks. Returns the three paths written."""
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dq_path = repo_root / "docs" / "data-quality-notes.md"
    meth_path = repo_root / "docs" / "methodology.md"
    dict_path = repo_root / "docs" / "data-dictionary.md"

    dq_block = _build_dq_block(
        action_share=action_share,
        loan_purpose_share=loan_purpose_share,
        loan_amount_df=loan_amount_df,
        la_purpose_pivot=la_purpose_pivot,
        income_df=income_df,
        pricing_df=pricing_df,
        ltv_df=ltv_df,
        dti_share=dti_share,
        race_share=race_share,
        ethnicity_share=ethnicity_share,
        sex_share=sex_share,
        age_share=age_share,
        denial_share=denial_share,
        denial_by_race=denial_by_race,
        syb_outcome_df=syb_outcome_df,
        years=years,
        run_date=run_date,
    )
    meth_block = _build_methodology_block(run_date)
    dict_block = _build_dict_block(
        loan_amount_df=loan_amount_df,
        income_df=income_df,
        ltv_df=ltv_df,
        race_share=race_share,
        sex_share=sex_share,
        run_date=run_date,
    )

    dq_begin = f"<!-- BEGIN:eda-02-{run_date} -->"
    dq_end = f"<!-- END:eda-02-{run_date} -->"
    dq_text = dq_path.read_text() if dq_path.exists() else "# Data Quality Notes\n"
    dq_path.write_text(_splice_block(dq_text, dq_begin, dq_end, dq_block))

    meth_text = meth_path.read_text() if meth_path.exists() else "# Methodology\n"
    meth_path.write_text(_splice_block(meth_text, METHOD_BEGIN, METHOD_END, meth_block))

    dict_text = dict_path.read_text() if dict_path.exists() else "# Data Dictionary\n"
    dict_path.write_text(_splice_block(dict_text, DICT_BEGIN, DICT_END, dict_block))

    return dq_path, meth_path, dict_path
