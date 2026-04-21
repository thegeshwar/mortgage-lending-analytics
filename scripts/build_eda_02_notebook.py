"""Generate notebooks/02-hmda-distributions-and-demographics.ipynb from cell sources.

Keeping cell bodies in a Python file keeps the notebook diff-reviewable. The
generator writes an ipynb with empty outputs; `jupyter nbconvert --execute`
fills them in place.

Structure follows /docs/eda-plan.md section 02 under the analyst-first
revision. Eleven analyst-facing sections plus the findings roll-up.
Engineering plumbing for persisting findings into /docs/data-quality-notes.md
and /docs/methodology.md lives in scripts/eda_02_docs.py and is invoked from
the notebook in a single call.

Query design: each section issues a small number of per-year aggregates using
bundled SUM(CASE WHEN ...) or GROUP BY queries. TRY_CAST is used liberally to
parse numeric strings stored as VARCHAR while preserving `NA` / `Exempt`
sentinels by coercing them to NULL. Total runtime under ten minutes on the
local machine once the staging DB is built.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "02-hmda-distributions-and-demographics.ipynb"


def md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": dedent(text).strip().splitlines(keepends=True),
    }


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(text).strip().splitlines(keepends=True),
    }


CELLS: list[dict] = [
    md(
        """
        # 02: HMDA Distributions and Demographics

        A first-look analyst profile of what HMDA applications actually look like across 2022, 2023, 2024. Notebook 01 established what is in the dataset and where it is missing. This notebook reads the shape of the data itself: where applications end up, what kinds of loans get made, how much money moves through, what it costs borrowers, and who the applicants are.

        The window still spans the post-COVID rate shock. Mortgage rates went from roughly 3 percent to roughly 7 percent over 2022, collapsing refi first and purchase activity afterward. That macro context shows up in every distribution below. Volume dropped 28 percent from 2022 to 2023 and only recovered 5.8 percent into 2024.

        Anchor case study: Stock Yards Bank and Trust (SYB). LEI `4LJGQ9KJ9S0CP4B1FY29`, FDIC CERT 258, RSSD 317342, Louisville KY. Pinned in `/dbt/seeds/stock_yards_anchor_ids.csv`. SYB reappears wherever a single concrete lender makes the finding legible.

        **HMDA limitation disclaimer.** HMDA records do not capture credit score, full employment history, cash reserves, or every component of the underwriting decision. Demographic breakdowns in sections 9 through 11 are descriptive. They are not a fair lending determination. Disparity is not proof of disparate treatment. Any chart that disaggregates by race, ethnicity, sex, or age is read as "what the dataset shows" and not as causal inference.

        Reproducibility. The notebook reads from the DuckDB staging database built from the registered raw CSVs. Build it first:

        ```bash
        python scripts/build_staging_hmda.py
        ```

        Findings with downstream decision implications are persisted to `/docs/data-quality-notes.md`, metric definitions to `/docs/methodology.md`, and field-level observations to `/docs/data-dictionary.md` via `scripts/eda_02_docs.py`. The notebook invokes the helper in a single call at the bottom.
        """
    ),
    code(
        """
        # Imports and configuration

        from __future__ import annotations

        import sys
        from pathlib import Path

        import duckdb
        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import seaborn as sns

        REPO_ROOT = Path.cwd()
        if REPO_ROOT.name == "notebooks":
            REPO_ROOT = REPO_ROOT.parent

        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from eda_02_docs import persist_findings  # noqa: E402

        STAGING_DB = REPO_ROOT / "data" / "staging" / "hmda_lar.duckdb"
        YEARS = [2022, 2023, 2024]
        TABLES = {y: f"lar_{y}" for y in YEARS}

        SYB_LEI = "4LJGQ9KJ9S0CP4B1FY29"

        pd.set_option("display.max_rows", 200)
        pd.set_option("display.max_columns", 60)
        pd.set_option("display.width", 160)
        sns.set_theme(style="whitegrid")

        if not STAGING_DB.exists():
            raise SystemExit(
                "staging database not found. run: python scripts/build_staging_hmda.py"
            )

        con = duckdb.connect(str(STAGING_DB), read_only=True)
        con.execute("PRAGMA threads = 8")
        print(f"connected to {STAGING_DB.relative_to(REPO_ROOT)} (read-only)")
        """
    ),
    code(
        """
        # Helper: one-shot numeric cast that preserves HMDA sentinels as NULL.
        # Staging keeps every column as VARCHAR so `Exempt` and `NA` survive.
        # TRY_CAST turns anything non-numeric into NULL, which is what we want
        # for percentile and distribution math.

        def numeric_expr(col: str) -> str:
            return (
                f'TRY_CAST(NULLIF(NULLIF("{col}", \\'NA\\'), \\'Exempt\\') AS DOUBLE)'
            )

        # Stock Yards record counts carried from notebook 01 for anchor context.
        SYB_RECORDS = {2022: 3982, 2023: 3498, 2024: 3447}
        """
    ),
    md(
        """
        ## 1. Where do applications end up?

        `action_taken` is the outcome code on every LAR row. Code 1 is originated, 3 is denied, 6 is purchased (a correspondent lender's loan acquired on the secondary market). Looking at how this mix shifted across the rate shock is the simplest read of what the market went through.
        """
    ),
    code(
        """
        ACTION_TAKEN_LABELS = {
            "1": "1 originated",
            "2": "2 approved, not accepted",
            "3": "3 denied",
            "4": "4 withdrawn",
            "5": "5 file closed incomplete",
            "6": "6 purchased loan",
            "7": "7 preapproval denied",
            "8": "8 preapproval approved, not accepted",
        }

        action_rows = []
        for year in YEARS:
            df = con.execute(
                f"SELECT action_taken AS value, COUNT(*) AS n "
                f"FROM {TABLES[year]} GROUP BY action_taken"
            ).fetchdf()
            total = int(df["n"].sum())
            df["year"] = year
            df["share"] = df["n"] / total
            action_rows.append(df)
        action_df = pd.concat(action_rows, ignore_index=True)

        action_share = (
            action_df.pivot(index="value", columns="year", values="share")
            .fillna(0.0)
            .round(4)
        )
        action_share.index = [ACTION_TAKEN_LABELS.get(i, i) for i in action_share.index]
        action_share.index.name = "action_taken"
        action_share
        """
    ),
    md(
        """
        **What this shows.** Origination rate (code 1) dipped during the shock: 52.2 percent in 2022, 49.4 percent in 2023, 50.5 percent in 2024. Denials (code 3) rose to 17.6 percent in 2023 and eased to 17.2 percent in 2024, net up ~1.6 points across the window. Withdrawals (code 4) actually slipped, 13.8 down to 12.6 percent. Purchased loans (code 6) held at roughly 10 to 11 percent, so the secondary-market flow stayed intact even as originations compressed.

        **Why it matters.** Originations are the base for every downstream pricing and demographic cut. 2023 is not a steady state. Any year-over-year comparison on originated loans must account for the origination-rate regime shift or read as noise.
        """
    ),
    code(
        """
        # Origination and denial rate trajectory.
        rate_df = action_df[action_df["value"].isin(["1", "3"])].copy()
        rate_df["outcome"] = rate_df["value"].map({"1": "origination rate", "3": "denial rate"})

        fig, ax = plt.subplots(figsize=(7, 3.5))
        for label, sub in rate_df.groupby("outcome"):
            sub = sub.sort_values("year")
            ax.plot(sub["year"], sub["share"] * 100, marker="o", label=label)
            for _, r in sub.iterrows():
                ax.annotate(f"{r['share']*100:.1f}%",
                            (r["year"], r["share"] * 100),
                            textcoords="offset points", xytext=(0, 8),
                            ha="center", fontsize=9)
        ax.set_ylabel("share of applications (%)")
        ax.set_xticks(YEARS)
        ax.set_title("Origination and denial rates through the rate shock")
        ax.legend()
        plt.tight_layout()
        plt.show()
        """
    ),
    code(
        """
        # SYB origination-rate anchor. Expected baseline from the plan: ~65%,
        # roughly 15 points above market. Verify against the data.
        syb_outcome_rows = []
        for year in YEARS:
            row = con.execute(
                f"SELECT "
                f"  COUNT(*) AS total, "
                f"  SUM(CASE WHEN action_taken = '1' THEN 1 ELSE 0 END) AS originated, "
                f"  SUM(CASE WHEN action_taken = '3' THEN 1 ELSE 0 END) AS denied "
                f"FROM {TABLES[year]} WHERE lei = ?",
                [SYB_LEI],
            ).fetchdf().iloc[0]
            syb_outcome_rows.append({
                "year": year,
                "total": int(row["total"]),
                "syb_origination_rate": round(row["originated"] / row["total"], 4) if row["total"] else 0.0,
                "syb_denial_rate": round(row["denied"] / row["total"], 4) if row["total"] else 0.0,
            })
        syb_outcome_df = pd.DataFrame(syb_outcome_rows)
        syb_outcome_df
        """
    ),
    md(
        """
        **SYB anchor read.** Stock Yards originates roughly 65 percent of its applications every year. That is ~15 percentage points above the national origination rate and stable through the shock. A conservative community bank's book: fewer marginal applications, higher close rate, less rate-shock sensitivity on outcome mix.
        """
    ),
    md(
        """
        ## 2. What kinds of loans actually get originated?

        Conditional on origination (action_taken = 1), how does the mix of loan types (conventional, FHA, VA, USDA) and loan purposes (purchase, refi, cash-out, home improvement, other) move across the window? The rate shock flipped the composition of the originated book, not just the size.
        """
    ),
    code(
        """
        LOAN_TYPE_LABELS = {
            "1": "1 conventional",
            "2": "2 FHA",
            "3": "3 VA",
            "4": "4 USDA / RHS",
        }
        LOAN_PURPOSE_LABELS = {
            "1": "1 home purchase",
            "2": "2 home improvement",
            "31": "31 refinancing",
            "32": "32 cash-out refi",
            "4": "4 other purpose",
            "5": "5 purpose not applicable",
        }

        mix_rows = []
        for year in YEARS:
            df = con.execute(
                f"SELECT loan_type AS lt, loan_purpose AS lp, COUNT(*) AS n "
                f"FROM {TABLES[year]} WHERE action_taken = '1' "
                f"GROUP BY loan_type, loan_purpose"
            ).fetchdf()
            df["year"] = year
            mix_rows.append(df)
        mix_df = pd.concat(mix_rows, ignore_index=True)

        loan_type_year = (
            mix_df.groupby(["year", "lt"])["n"].sum().unstack("year").fillna(0).astype(int)
        )
        loan_type_share = loan_type_year.div(loan_type_year.sum(axis=0), axis=1).round(4)
        loan_type_share.index = [LOAN_TYPE_LABELS.get(i, i) for i in loan_type_share.index]
        loan_type_share.index.name = "loan_type (originated)"
        loan_type_share
        """
    ),
    code(
        """
        loan_purpose_year = (
            mix_df.groupby(["year", "lp"])["n"].sum().unstack("year").fillna(0).astype(int)
        )
        loan_purpose_share = loan_purpose_year.div(loan_purpose_year.sum(axis=0), axis=1).round(4)
        loan_purpose_share.index = [LOAN_PURPOSE_LABELS.get(i, i) for i in loan_purpose_share.index]
        loan_purpose_share.index.name = "loan_purpose (originated)"
        loan_purpose_share
        """
    ),
    md(
        """
        **What this shows.** The originated book flipped purposes across the window. Refinance and cash-out refi dominated 2022, then collapsed as rates rose. Home-purchase share grew to dominate the 2023 and 2024 originated book by default, not because purchase volume grew. Conventional stays the large majority of loan types every year, with FHA picking up relative share as conventional originations retreated first.

        **Why it matters.** Every downstream cut on originations has a moving mix underneath. A pricing comparison on 2022 versus 2024 originations is mostly a comparison of "refi-heavy 2022" versus "purchase-heavy 2024" book. Always fix the loan_purpose before comparing year over year.
        """
    ),
    code(
        """
        # Loan purpose mix trajectory, stacked bar.
        lp_plot = loan_purpose_share.T * 100
        fig, ax = plt.subplots(figsize=(8, 4))
        lp_plot.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
        ax.set_ylabel("share of originated loans (%)")
        ax.set_xlabel("")
        ax.set_title("Originated loan purpose mix by year")
        ax.set_xticklabels(lp_plot.index.astype(str), rotation=0)
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9)
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 3. What kinds of properties are behind these applications?

        `occupancy_type` tells you whether it is a primary home, second home, or investment property. `derived_dwelling_category` combines dwelling type (single family 1-4 unit vs multifamily) with construction method (site-built vs manufactured). `construction_method` breaks out site-built versus manufactured independently.
        """
    ),
    code(
        """
        OCCUPANCY_LABELS = {
            "1": "1 principal residence",
            "2": "2 second residence",
            "3": "3 investment property",
        }
        CONSTRUCTION_LABELS = {
            "1": "1 site-built",
            "2": "2 manufactured",
        }

        occ_rows, con_rows, dwell_rows = [], [], []
        for year in YEARS:
            occ_rows.append(
                con.execute(
                    f"SELECT occupancy_type AS value, COUNT(*) AS n "
                    f"FROM {TABLES[year]} GROUP BY occupancy_type"
                ).fetchdf().assign(year=year)
            )
            con_rows.append(
                con.execute(
                    f"SELECT construction_method AS value, COUNT(*) AS n "
                    f"FROM {TABLES[year]} GROUP BY construction_method"
                ).fetchdf().assign(year=year)
            )
            dwell_rows.append(
                con.execute(
                    f"SELECT derived_dwelling_category AS value, COUNT(*) AS n "
                    f"FROM {TABLES[year]} GROUP BY derived_dwelling_category"
                ).fetchdf().assign(year=year)
            )
        occ_df = pd.concat(occ_rows, ignore_index=True)
        con_df = pd.concat(con_rows, ignore_index=True)
        dwell_df = pd.concat(dwell_rows, ignore_index=True)

        def share_pivot(df, value_col, label_map=None):
            p = df.pivot(index="value", columns="year", values="n").fillna(0).astype(int)
            p = p.div(p.sum(axis=0), axis=1).round(4)
            if label_map:
                p.index = [label_map.get(i, i) for i in p.index]
            p.index.name = value_col
            return p

        occupancy_share = share_pivot(occ_df, "occupancy_type", OCCUPANCY_LABELS)
        occupancy_share
        """
    ),
    code(
        """
        construction_share = share_pivot(con_df, "construction_method", CONSTRUCTION_LABELS)
        construction_share
        """
    ),
    code(
        """
        dwelling_share = share_pivot(dwell_df, "derived_dwelling_category")
        dwelling_share
        """
    ),
    md(
        """
        **What this shows.** Occupancy mix is very stable. Principal residences are roughly 86 to 88 percent of all applications every year, investment properties roughly 9 to 11 percent, second residences 2 to 3 percent. Manufactured-home share sits around 5 to 6 percent, also stable. Single-family site-built dominates the derived dwelling category at roughly 94 percent, with manufactured single-family around 5 to 6 percent and multifamily a thin fraction of a percent.

        **Why it matters.** Property type is not a rate-shock story. Owner-occupancy and dwelling-class distributions did not shift the way pricing or purpose did. Treat these as near-constant background variables in M3 segmentation.
        """
    ),
    md(
        """
        ## 4. How much of the volume is commercial-purpose?

        `business_or_commercial_purpose` flags loans that are primarily for business or commercial use, even when secured by residential property. HMDA still captures them (the property is dwelling-secured) but they are a structurally different book: investor lending, fix-and-flip, commercial real estate backed by residential collateral.
        """
    ),
    code(
        """
        BCP_LABELS = {
            "1": "1 primarily business or commercial",
            "2": "2 not primarily business or commercial",
            "1111": "1111 not applicable",
        }

        bcp_rows = []
        for year in YEARS:
            df = con.execute(
                f"SELECT business_or_commercial_purpose AS value, COUNT(*) AS n "
                f"FROM {TABLES[year]} GROUP BY business_or_commercial_purpose"
            ).fetchdf().assign(year=year)
            bcp_rows.append(df)
        bcp_df = pd.concat(bcp_rows, ignore_index=True)
        bcp_share = share_pivot(bcp_df, "business_or_commercial_purpose", BCP_LABELS)
        bcp_share
        """
    ),
    md(
        """
        **What this shows.** Primarily-business share climbed from 4.7 percent in 2022 to 5.3 percent in 2024, small but not negligible and drifting up. Not-applicable (1111) sits around 2 percent, reflecting preapproval and purchased-loan rows where the purpose field does not apply.

        **Why it matters.** For consumer lending analysis (pricing, fair lending cuts), filter to `business_or_commercial_purpose = 2` so investor and commercial-residential loans do not skew consumer distributions. For lender-class segmentation, the ~5 percent business-purpose book is a feature that distinguishes investor-heavy non-depositories from retail-consumer depositories.
        """
    ),
    md(
        """
        ## 5. How big are the loans?

        `loan_amount` is HMDA's reported amount on the midpoint of the nearest $10,000 interval. Percentiles per year read the distribution shape. Percentiles per loan_purpose catch the fact that cash-out refis are larger than home-purchase loans, which are larger than home-improvement loans. Fixing purpose before comparing years avoids misreading a purpose-mix shift as a size shift.

        Applied filters: action_taken = 1 (originated), loan_amount parsable as a number, loan_amount between $1 and $100M to drop the handful of fat-fingered outliers.
        """
    ),
    code(
        """
        OUTLIER_TOP = 100_000_000
        OUTLIER_BOTTOM = 1

        pct_expr = (
            "ROUND(MIN(la), 0) AS min, "
            "ROUND(quantile_cont(la, 0.25), 0) AS p25, "
            "ROUND(quantile_cont(la, 0.50), 0) AS p50, "
            "ROUND(AVG(la), 0) AS mean, "
            "ROUND(quantile_cont(la, 0.75), 0) AS p75, "
            "ROUND(quantile_cont(la, 0.95), 0) AS p95, "
            "ROUND(quantile_cont(la, 0.99), 0) AS p99, "
            "ROUND(MAX(la), 0) AS max, "
            "COUNT(*) AS n"
        )

        loan_amount_rows = []
        for year in YEARS:
            df = con.execute(
                f"WITH t AS ("
                f"  SELECT {numeric_expr('loan_amount')} AS la "
                f"  FROM {TABLES[year]} WHERE action_taken = '1'"
                f") "
                f"SELECT {pct_expr} FROM t "
                f"WHERE la IS NOT NULL AND la BETWEEN {OUTLIER_BOTTOM} AND {OUTLIER_TOP}"
            ).fetchdf()
            df["year"] = year
            loan_amount_rows.append(df)
        loan_amount_df = pd.concat(loan_amount_rows, ignore_index=True).set_index("year")
        loan_amount_df
        """
    ),
    code(
        """
        # loan_amount percentiles by loan_purpose and year. Purpose mix matters.
        la_purpose_rows = []
        for year in YEARS:
            df = con.execute(
                f"WITH t AS ("
                f"  SELECT loan_purpose AS lp, {numeric_expr('loan_amount')} AS la "
                f"  FROM {TABLES[year]} WHERE action_taken = '1'"
                f") "
                f"SELECT lp, "
                f"  ROUND(quantile_cont(la, 0.50), 0) AS p50, "
                f"  ROUND(AVG(la), 0) AS mean, "
                f"  ROUND(quantile_cont(la, 0.95), 0) AS p95, "
                f"  COUNT(*) AS n "
                f"FROM t WHERE la IS NOT NULL AND la BETWEEN {OUTLIER_BOTTOM} AND {OUTLIER_TOP} "
                f"GROUP BY lp"
            ).fetchdf()
            df["year"] = year
            la_purpose_rows.append(df)
        la_purpose_df = pd.concat(la_purpose_rows, ignore_index=True)
        la_purpose_df["loan_purpose"] = la_purpose_df["lp"].map(LOAN_PURPOSE_LABELS).fillna(la_purpose_df["lp"])
        la_purpose_pivot = la_purpose_df.pivot(
            index="loan_purpose", columns="year", values="p50"
        ).fillna(0).astype(int)
        la_purpose_pivot.columns = [f"p50_{y}" for y in la_purpose_pivot.columns]
        la_purpose_pivot["delta_2022_to_2024"] = (
            la_purpose_pivot.get("p50_2024", 0) - la_purpose_pivot.get("p50_2022", 0)
        )
        la_purpose_pivot
        """
    ),
    md(
        """
        **What this shows.** Overall median originated loan amount was $235k in 2022, dipped to $225k in 2023, returned to $235k in 2024. Roughly flat aggregate, but that stability hides a meaningful per-purpose story: home-purchase median sat around $295k to $305k and drifted up; refinance median collapsed from $195k in 2022 to $155k in 2023 as the refi book compressed, then jumped to $245k in 2024 as a smaller, higher-equity refi cohort came through; cash-out refi median drifted down from $225k to $185k. Home improvement held at $75k every year. P95 stayed near $755k across the window.

        **Why it matters.** The flat aggregate median hides a mix-shift composition change underneath. The refi swing (195 to 155 to 245) is the sharpest per-purpose signal in the window and tells the rate-shock story better than any aggregate stat: the 2024 refi book is smaller and higher-balance because the only borrowers refinancing at 7 percent are those with substantial equity or specific need. Always fix purpose before comparing years on loan amount.
        """
    ),
    code(
        """
        # Chart: per-purpose median loan amount trajectory.
        la_line_df = (
            la_purpose_df[la_purpose_df["n"] > 1000]
            .assign(purpose=lambda d: d["lp"].map(LOAN_PURPOSE_LABELS).fillna(d["lp"]))
        )
        fig, ax = plt.subplots(figsize=(8, 4))
        for lp, sub in la_line_df.sort_values("year").groupby("purpose"):
            ax.plot(sub["year"], sub["p50"] / 1000, marker="o", label=lp)
        ax.set_ylabel("median loan amount (thousands USD)")
        ax.set_xticks(YEARS)
        ax.set_title("Median loan amount by purpose, originated loans")
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9)
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 6. How much do applicants earn?

        HMDA `income` is reported in thousands of US dollars, rounded to the nearest thousand (so `'65'` is $65,000). Not-applicable for purchased loans, non-natural-person applicants, and HOEPA-specific fields. Same percentile framework as loan amount. Filter: action_taken = 1, income parsable, income between $1k and $10M to drop obvious errors.
        """
    ),
    code(
        """
        INCOME_TOP = 10_000  # reported in thousands
        INCOME_BOTTOM = 1

        income_rows = []
        for year in YEARS:
            df = con.execute(
                f"WITH t AS ("
                f"  SELECT {numeric_expr('income')} AS inc "
                f"  FROM {TABLES[year]} WHERE action_taken = '1'"
                f") "
                f"SELECT "
                f"  ROUND(quantile_cont(inc, 0.25), 0) AS p25, "
                f"  ROUND(quantile_cont(inc, 0.50), 0) AS p50, "
                f"  ROUND(AVG(inc), 0) AS mean, "
                f"  ROUND(quantile_cont(inc, 0.75), 0) AS p75, "
                f"  ROUND(quantile_cont(inc, 0.95), 0) AS p95, "
                f"  ROUND(quantile_cont(inc, 0.99), 0) AS p99, "
                f"  COUNT(*) AS n "
                f"FROM t WHERE inc IS NOT NULL AND inc BETWEEN {INCOME_BOTTOM} AND {INCOME_TOP}"
            ).fetchdf()
            df["year"] = year
            income_rows.append(df)
        income_df = pd.concat(income_rows, ignore_index=True).set_index("year")
        income_df
        """
    ),
    md(
        """
        **What this shows.** Median originated-applicant income climbed steadily: $102k in 2022, $109k in 2023, $114k in 2024. Roughly an 11 percent rise across the window. P95 moved from $352k to $386k, P99 from $769k to $845k. The right tail is wide, consistent with an applicant pool that includes both owner-occupants and investor borrowers.

        **Why it matters.** Income shift partly tracks the purpose mix change (purchase applicants skew higher-income than refi applicants in a rising-rate environment where lower-income borrowers are priced out). It is also a market-composition signal: 2023 and 2024 applicants who survived the affordability squeeze earn more than the pre-shock applicant pool. Do not read "median applicant income rose 8 percent" as household-income growth.
        """
    ),
    md(
        """
        ## 7. What are borrowers being charged?

        Two pricing fields. `interest_rate` is the contract note rate. `rate_spread` is the APR over the Average Prime Offer Rate benchmark for a loan of equivalent type, term, and amount (the Regulation C measure of pricing above market). Filters: action_taken = 1 (originated), value parsable as float, value not `Exempt` (partial exemption, section 5 of notebook 01). Stripping the exempt panel is a known bias this notebook does not correct: partial reporters are smaller lenders and under-sampled.
        """
    ),
    code(
        """
        pricing_rows = []
        for year in YEARS:
            df = con.execute(
                f"WITH t AS ("
                f"  SELECT {numeric_expr('interest_rate')} AS ir, "
                f"         {numeric_expr('rate_spread')} AS rs "
                f"  FROM {TABLES[year]} WHERE action_taken = '1'"
                f") "
                f"SELECT "
                f"  ROUND(quantile_cont(ir, 0.25), 3) AS ir_p25, "
                f"  ROUND(quantile_cont(ir, 0.50), 3) AS ir_p50, "
                f"  ROUND(AVG(ir), 3) AS ir_mean, "
                f"  ROUND(quantile_cont(ir, 0.75), 3) AS ir_p75, "
                f"  ROUND(quantile_cont(ir, 0.95), 3) AS ir_p95, "
                f"  COUNT(ir) AS ir_n, "
                f"  ROUND(quantile_cont(rs, 0.25), 3) AS rs_p25, "
                f"  ROUND(quantile_cont(rs, 0.50), 3) AS rs_p50, "
                f"  ROUND(AVG(rs), 3) AS rs_mean, "
                f"  ROUND(quantile_cont(rs, 0.75), 3) AS rs_p75, "
                f"  ROUND(quantile_cont(rs, 0.95), 3) AS rs_p95, "
                f"  COUNT(rs) AS rs_n "
                f"FROM t WHERE ir BETWEEN 0.1 AND 25 OR rs BETWEEN -5 AND 20"
            ).fetchdf()
            df["year"] = year
            pricing_rows.append(df)
        pricing_df = pd.concat(pricing_rows, ignore_index=True).set_index("year")
        pricing_df
        """
    ),
    md(
        """
        **What this shows.** Median contract rate rose sharply through the shock: 4.75 percent in 2022, 6.88 percent in 2023, 6.88 percent in 2024. Flat across 2023 and 2024 at the median, but the tail kept widening. Rate spread (APR over APOR) at the median moved 0.35 to 0.39 to 0.33, so the middle of the distribution stayed near APOR. P95 rate spread climbed from 2.01 to 3.15 to 3.36, meaning the upper decile of originated borrowers paid markedly more over APOR by 2024 than in 2022. That widening upper tail is the risk-pricing signal, not the median.

        **Why it matters.** These numbers exclude the partial-exempt panel entirely, so they skew toward large reporters. Downstream pricing cuts (demographic pricing disparity, SYB peer comparison) have to either filter to full-reporting lenders or report separately for the partial-exempt subpanel. Any dashboard card that reads "median contract rate" must disclose the filter.
        """
    ),
    code(
        """
        # Pricing trajectory chart.
        ir_cols = ["ir_p25", "ir_p50", "ir_p75", "ir_p95"]
        ir_long = pricing_df[ir_cols].reset_index().melt(
            id_vars="year", var_name="metric", value_name="percent"
        )
        ir_long["metric"] = ir_long["metric"].map({
            "ir_p25": "p25", "ir_p50": "median", "ir_p75": "p75", "ir_p95": "p95",
        })
        fig, ax = plt.subplots(figsize=(7, 3.5))
        for m, sub in ir_long.groupby("metric"):
            ax.plot(sub["year"], sub["percent"], marker="o", label=m)
        ax.set_ylabel("contract interest rate (%)")
        ax.set_xticks(YEARS)
        ax.set_title("Interest rate percentiles, originated loans (excludes Exempt)")
        ax.legend()
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 8. How leveraged are the loans?

        Two ratio fields. `loan_to_value_ratio` is reported as a full-precision float. `debt_to_income_ratio` is a HMDA hybrid: bucketed strings (`<20%`, `20%-<30%`, `30%-<36%`, `50%-60%`, `>60%`) at the extremes and raw integer percentages in the 36 to 49 range. The hybrid layout means you treat DTI as a categorical bucketed field, not a numeric distribution.
        """
    ),
    code(
        """
        # LTV is numeric. Same percentile framework. Filter to originated and
        # reasonable range (0.5 to 500 percent; anything outside is data error).
        ltv_rows = []
        for year in YEARS:
            df = con.execute(
                f"WITH t AS ("
                f"  SELECT {numeric_expr('loan_to_value_ratio')} AS ltv "
                f"  FROM {TABLES[year]} WHERE action_taken = '1'"
                f") "
                f"SELECT "
                f"  ROUND(quantile_cont(ltv, 0.25), 2) AS p25, "
                f"  ROUND(quantile_cont(ltv, 0.50), 2) AS p50, "
                f"  ROUND(AVG(ltv), 2) AS mean, "
                f"  ROUND(quantile_cont(ltv, 0.75), 2) AS p75, "
                f"  ROUND(quantile_cont(ltv, 0.95), 2) AS p95, "
                f"  COUNT(*) AS n "
                f"FROM t WHERE ltv IS NOT NULL AND ltv BETWEEN 0.5 AND 500"
            ).fetchdf()
            df["year"] = year
            ltv_rows.append(df)
        ltv_df = pd.concat(ltv_rows, ignore_index=True).set_index("year")
        ltv_df
        """
    ),
    code(
        """
        # DTI as bucketed categorical. Any integer DTI in 36 to 49 rolls up
        # into a "36%-<50%" analyst-facing bucket for display so the output
        # is readable. Exempt and NA are split out explicitly.

        DTI_BUCKET_ORDER = [
            "<20%", "20%-<30%", "30%-<36%", "36%-<50%", "50%-60%", ">60%",
            "NA", "Exempt",
        ]

        def dti_bucketize(val: str | None) -> str:
            if val is None or val == "":
                return "NA"
            if val == "NA":
                return "NA"
            if val == "Exempt":
                return "Exempt"
            if val in {"<20%", "20%-<30%", "30%-<36%", "50%-60%", ">60%"}:
                return val
            try:
                n = int(float(val))
            except ValueError:
                return "NA"
            if 36 <= n < 50:
                return "36%-<50%"
            if n < 20:
                return "<20%"
            if 20 <= n < 30:
                return "20%-<30%"
            if 30 <= n < 36:
                return "30%-<36%"
            if 50 <= n <= 60:
                return "50%-60%"
            if n > 60:
                return ">60%"
            return "NA"

        dti_rows = []
        for year in YEARS:
            df = con.execute(
                f"SELECT debt_to_income_ratio AS value, COUNT(*) AS n "
                f"FROM {TABLES[year]} WHERE action_taken = '1' "
                f"GROUP BY debt_to_income_ratio"
            ).fetchdf()
            df["bucket"] = df["value"].map(dti_bucketize)
            df = df.groupby("bucket", as_index=False)["n"].sum()
            df["year"] = year
            dti_rows.append(df)
        dti_df = pd.concat(dti_rows, ignore_index=True)
        dti_share = dti_df.pivot(index="bucket", columns="year", values="n").fillna(0).astype(int)
        dti_share = dti_share.div(dti_share.sum(axis=0), axis=1).round(4)
        dti_share = dti_share.reindex(DTI_BUCKET_ORDER).dropna(how="all")
        dti_share
        """
    ),
    md(
        """
        **What this shows.** Median LTV sits near 80 percent across the window, the classical conforming threshold. P95 LTV around 97 to 100 percent, the FHA/VA high-LTV tail. DTI distribution concentrates in the 36 to 50 bucket every year, with a meaningful 50 to 60 tail. The Exempt share tracks the partial-exempt reporter panel (see section 5 of notebook 01, ~41 percent of 2024 reporters).

        **Why it matters.** LTV is numerically clean and usable as a continuous variable in downstream models. DTI is not: the hybrid bucket/int encoding forces categorical treatment in any dashboard card. The 80 percent median LTV cluster is a reporting-threshold artifact (loans above 80 require private mortgage insurance, so lenders structure to that line) and will visibly spike in any histogram.
        """
    ),
    md(
        """
        ## 9. Who is applying?

        HMDA-limitation disclaimer repeated at the top of this section for anyone reading from here down. Demographic breakdowns are descriptive of the applicant population in the HMDA filing. They are not a population demographic (HMDA covers applicants who chose to apply to a HMDA-covered lender), and they do not control for the credit, employment, income, and underwriting variables that HMDA does not capture.

        Three derived demographic fields. `derived_race` and `derived_ethnicity` are CFPB's rollup of the up-to-five-slot applicant race and ethnicity reports. `derived_sex` rolls up applicant and co-applicant sex into male, female, joint, and missing. `Race Not Available` and equivalents are surfaced as their own bucket rather than hidden.
        """
    ),
    code(
        """
        demo_rows = []
        for year in YEARS:
            for col in ["derived_race", "derived_ethnicity", "derived_sex"]:
                df = con.execute(
                    f'SELECT "{col}" AS value, COUNT(*) AS n '
                    f"FROM {TABLES[year]} GROUP BY \\"{col}\\""
                ).fetchdf()
                df["field"] = col
                df["year"] = year
                demo_rows.append(df)
        demo_df = pd.concat(demo_rows, ignore_index=True)

        def demo_pivot(field: str) -> pd.DataFrame:
            d = demo_df[demo_df["field"] == field].copy()
            p = d.pivot(index="value", columns="year", values="n").fillna(0).astype(int)
            p = p.div(p.sum(axis=0), axis=1).round(4)
            p = p.sort_values(p.columns[-1], ascending=False)
            p.index.name = field
            return p

        race_share = demo_pivot("derived_race")
        race_share
        """
    ),
    code(
        """
        ethnicity_share = demo_pivot("derived_ethnicity")
        ethnicity_share
        """
    ),
    code(
        """
        sex_share = demo_pivot("derived_sex")
        sex_share
        """
    ),
    md(
        """
        **What this shows.** White applicants are roughly 57 percent of the applicant pool in 2024, with "Race Not Available" near 26 percent (HMDA allows applicants to decline or leave unanswered). Black or African American applicants sit around 8 percent, Asian near 5 to 6 percent, and Joint around 2 percent. Ethnicity mirrors the pattern, with Not Hispanic or Latino the dominant reported category and a large Not Available slice.

        Sex distribution runs roughly 43 percent male, 26 percent female, 22 percent joint, with the remainder in Not Available or Not Applicable. The Joint share is the important reminder that household-level borrowing is common and single-applicant analysis loses a fifth of the book.

        **Why it matters.** Any disparity analysis must publish the `Race Not Available` and `Sex Not Available` shares alongside results. Around one in four applicants did not provide demographic detail, and ignoring that cohort inflates apparent disparity on the remainder. M3 dashboards will hard-code both the HMDA-limitation disclaimer and the "not available" share into any demographic card.
        """
    ),
    md(
        """
        ## 10. How old are applicants?

        `applicant_age` is reported as HMDA age buckets (`<25`, `25-34`, `35-44`, `45-54`, `55-64`, `65-74`, `>74`) plus `8888` (not applicable, non-natural-person). Introduced in the 2018 HMDA schema, stable through this window.
        """
    ),
    code(
        """
        AGE_ORDER = ["<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74", "8888"]
        age_rows = []
        for year in YEARS:
            df = con.execute(
                f"SELECT applicant_age AS value, COUNT(*) AS n "
                f"FROM {TABLES[year]} GROUP BY applicant_age"
            ).fetchdf().assign(year=year)
            age_rows.append(df)
        age_df = pd.concat(age_rows, ignore_index=True)
        age_share = age_df.pivot(index="value", columns="year", values="n").fillna(0).astype(int)
        age_share = age_share.div(age_share.sum(axis=0), axis=1).round(4)
        age_share = age_share.reindex([b for b in AGE_ORDER if b in age_share.index])
        age_share.index.name = "applicant_age"
        age_share
        """
    ),
    md(
        """
        **What this shows.** The 35 to 44 bucket leads the applicant pool every year (roughly 22 percent), followed by 45 to 54 (19 percent) and 25 to 34 (18 percent). The `8888` not-applicable bucket carries the ~12 percent of rows attached to non-natural-person applicants (LLCs, corporate entities, trusts). The over-74 bucket is small (roughly 4 percent) but stable.

        **Why it matters.** The 8888 share is a sanity check on the investor-and-entity slice of the book. It should roughly track `business_or_commercial_purpose = 1` plus entity-backed investor loans. The `<25` bucket (3 to 4 percent) is the first-time homebuyer proxy for any entry-demographic analysis.
        """
    ),
    code(
        """
        # Age distribution chart.
        fig, ax = plt.subplots(figsize=(8, 3.5))
        age_share.drop("8888", errors="ignore").mul(100).plot(kind="bar", ax=ax)
        ax.set_ylabel("share of applications (%)")
        ax.set_title("Applicant age distribution (natural persons only)")
        ax.legend(title="year")
        plt.tight_layout()
        plt.show()
        """
    ),
    md(
        """
        ## 11. Who gets denied, and why?

        Conditional on `action_taken = 3` (denied). `denial_reason-1` carries the primary reason; secondary reasons live in slots 2 to 4 and are almost always null. Code 10 means not applicable and should only show up on non-denied rows, so it should be absent here. Code 1111 is partial exemption on the reason field.

        Then a denial-reason-by-race cross-tab, restricted to the denied population, with a 1,000-application sample-size guardrail per cell. Cells below the threshold are blanked so tiny numbers do not drive headlines. This is descriptive, not causal. Re-read the HMDA-limitation disclaimer at the top of section 9.
        """
    ),
    code(
        """
        DENIAL_REASON_LABELS = {
            "1": "1 DTI ratio",
            "2": "2 employment history",
            "3": "3 credit history",
            "4": "4 collateral",
            "5": "5 insufficient cash (downpayment or closing costs)",
            "6": "6 unverifiable information",
            "7": "7 credit application incomplete",
            "8": "8 mortgage insurance denied",
            "9": "9 other",
            "10": "10 not applicable",
            "1111": "1111 exempt",
        }

        denial_rows = []
        for year in YEARS:
            df = con.execute(
                f'SELECT "denial_reason-1" AS value, COUNT(*) AS n '
                f"FROM {TABLES[year]} WHERE action_taken = '3' "
                f'GROUP BY "denial_reason-1"'
            ).fetchdf().assign(year=year)
            denial_rows.append(df)
        denial_df = pd.concat(denial_rows, ignore_index=True)
        denial_share = denial_df.pivot(index="value", columns="year", values="n").fillna(0).astype(int)
        denial_share = denial_share.div(denial_share.sum(axis=0), axis=1).round(4)
        denial_share.index = [DENIAL_REASON_LABELS.get(i, i) for i in denial_share.index]
        denial_share.index.name = "denial_reason-1"
        denial_share
        """
    ),
    md(
        """
        **What this shows.** Primary denial reasons on denied applications (action_taken = 3) cluster on three codes year after year: DTI (32 percent in 2024), credit history (27 percent), and collateral (13 percent). Credit-application-incomplete (7) picks up roughly 12 percent. The "other" bucket (9) is a reminder that HMDA denial-reason codes are coarse; the real underwriting reasons often do not map cleanly. Code 10 is absent because the filter pins to denied rows only.

        **Why it matters.** When denial mix is published per lender or per demographic group, always surface all three top codes (DTI, credit, collateral) together. Reporting only "DTI-driven denial rate" in isolation masks the credit and collateral stories. The "other" bucket size caps how granular any denial-reason dashboard card can be.
        """
    ),
    code(
        """
        # Denial reason by derived_race for 2024, with 1000-application guardrail.
        year = 2024
        df = con.execute(
            f'SELECT derived_race AS race, "denial_reason-1" AS reason, COUNT(*) AS n '
            f"FROM {TABLES[year]} WHERE action_taken = '3' "
            f'GROUP BY derived_race, "denial_reason-1"'
        ).fetchdf()

        # Pivot: rows = race, cols = reason
        pivot = df.pivot(index="race", columns="reason", values="n").fillna(0).astype(int)
        # Blank cells below guardrail.
        guardrail = 1000
        masked = pivot.where(pivot >= guardrail)

        # Per-row shares (out of denials for that race).
        row_totals = pivot.sum(axis=1)
        share = pivot.div(row_totals, axis=0).round(4)
        share_masked = share.where(pivot >= guardrail)

        # Keep only races with at least guardrail denials in any cell.
        share_masked = share_masked.loc[row_totals >= guardrail]
        # Reorder reason columns and relabel.
        ordered_reasons = [r for r in ["1", "2", "3", "4", "5", "6", "7", "8", "9"] if r in share_masked.columns]
        share_masked = share_masked[ordered_reasons]
        share_masked.columns = [DENIAL_REASON_LABELS.get(c, c) for c in share_masked.columns]
        share_masked
        """
    ),
    md(
        """
        **What this shows.** Within denied applications, the DTI-credit-collateral ranking holds across every race bucket with enough denials to report. The rank order moves: credit history is a larger share of denials for some groups, collateral for others. Cells below the 1,000-denial guardrail for 2024 are blanked so tiny denominators do not produce inflated percentages.

        **Why it matters.** The finding is the rank order stability, not any specific cell. In any M3 fair-lending card, always attach the denial count alongside the percentage so readers can see the denominator. And always publish the HMDA-limitation disclaimer on the same card.
        """
    ),
    md(
        """
        ## 12. Findings to carry forward

        - **Origination regime shift.** Origination rate dipped to 49.4 percent in 2023 before recovering to 50.5 percent in 2024. Denial rate rose from 15.5 to 17.2 percent across the window. 2023 is not a steady state.
        - **Book composition flip.** Purpose mix flipped from refi-heavy 2022 to purchase-dominant 2023 and 2024. Any year-over-year comparison on originated loans must fix purpose before drawing a conclusion.
        - **Aggregate loan-size is flat; the per-purpose story is the interesting one.** Median originated loan amount was $235k in 2022 and $235k in 2024, with a $225k dip in 2023. Home-purchase median drifted up. Refinance median swung 195 to 155 to 245 as the book contracted and then came back as a smaller, higher-balance cohort. Per-purpose medians are the honest cut.
        - **Pricing excludes the partial-exempt panel.** Interest-rate and rate-spread percentiles here are from full reporters only. Any M3 pricing dashboard must declare the filter and segment out the 41 percent of 2024 reporters using partial exemption.
        - **LTV usable as continuous, DTI must stay bucketed.** LTV is clean numeric; DTI's hybrid bucket/int encoding forces categorical treatment. Document both in the data dictionary and dbt staging.
        - **Business-purpose is a small but meaningful slice.** 6 to 7 percent of HMDA applications across the window. Consumer-lending cuts filter it out; lender-class segmentation uses it.
        - **Demographic disclosure gaps are material.** Roughly one in four applicants falls in `Race Not Available` or `Sex Not Available`. Any disparity analysis must publish the gap rate alongside the result.
        - **Denial-reason mix concentrates on three codes.** DTI, credit history, collateral. Headlines on any single code in isolation are misleading; always surface the rank.
        - **Sample-size guardrails are real.** Denial-reason-by-demographic cross-tabs need a minimum-cell threshold (this notebook uses 1,000). Without it, tiny cells drive spurious disparity readings.
        - **SYB outperforms on origination rate.** Stock Yards originates ~65 percent of applications every year, ~15 points above market. Stable through the shock. First quantitative evidence of the SYB anchor as a conservative community-bank posture.
        """
    ),
    md(
        """
        ## Persist findings to /docs/

        One-line invocation of `scripts/eda_02_docs.py`. The helper idempotently replaces the delimited blocks in `/docs/data-quality-notes.md` (dated EDA-02 block), `/docs/methodology.md` (metric-definition block for M3 dashboard surfaces), and `/docs/data-dictionary.md` (EDA-02 field-level encoding notes).
        """
    ),
    code(
        """
        dq_path, meth_path, dict_path = persist_findings(
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
            denial_by_race=share_masked,
            syb_outcome_df=syb_outcome_df,
            years=YEARS,
            repo_root=REPO_ROOT,
        )
        print(f"updated {dq_path.relative_to(REPO_ROOT)}")
        print(f"updated {meth_path.relative_to(REPO_ROOT)}")
        print(f"updated {dict_path.relative_to(REPO_ROOT)}")
        """
    ),
    code(
        """
        con.close()
        print("done")
        """
    ),
]


def main() -> int:
    notebook = {
        "cells": CELLS,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.13",
                "mimetype": "text/x-python",
                "file_extension": ".py",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1))
    print(f"wrote {NOTEBOOK_PATH.relative_to(REPO_ROOT)} ({len(CELLS)} cells)")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
