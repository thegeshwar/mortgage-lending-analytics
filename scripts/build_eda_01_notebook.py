"""Generate notebooks/01-hmda-schema-and-quality.ipynb from cell sources.

Keeping the cell bodies in a Python file makes the notebook trivially
diffable and reviewable. The generator writes an ipynb JSON with empty
outputs; the executor (nbconvert) fills the outputs in place.

Cell layout follows /docs/eda-plan.md section 01. Eight analytical
sections plus a final artifact-writing section.

Query design: every section that touches a full table issues at most one
query per year, composing all per-column aggregates into a single SELECT
with SUM(CASE WHEN ...) per column. This keeps end-to-end runtime of the
notebook under ten minutes on the local machine once the staging DB is
built.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "01-hmda-schema-and-quality.ipynb"


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
    md("""
        # 01: HMDA Schema and Quality EDA

        Corporate-grade schema and quality profile of the HMDA LAR across 2022, 2023, and 2024.

        Scope and contract: see `/docs/eda-plan.md` section 01. Eight sections covering data presence, column surface, type inference, null profile, exempt-value profile, composite primary key uniqueness, referential integrity against the filer roster, and value-set validation on code-encoded fields.

        Reproducibility: the notebook reads from a DuckDB staging file built out of the registered raw CSVs. Build it first with:

        ```bash
        python scripts/build_staging_hmda.py
        ```

        Every finding with a downstream decision implication is written to `/docs/data-quality-notes.md` with a dated entry. Field-level observations are written to `/docs/data-dictionary.md`.

        Anchor case study: Stock Yards Bank and Trust. LEI `4LJGQ9KJ9S0CP4B1FY29`, FDIC CERT 258, RSSD 317342, Louisville KY. Pinned in `/dbt/seeds/stock_yards_anchor_ids.csv`.
    """),
    code("""
        # Imports and configuration

        from __future__ import annotations

        import json
        import re
        from datetime import datetime, timezone
        from pathlib import Path

        import duckdb
        import pandas as pd

        REPO_ROOT = Path.cwd()
        if REPO_ROOT.name == "notebooks":
            REPO_ROOT = REPO_ROOT.parent

        MANIFEST_PATH = REPO_ROOT / "data" / "raw" / "hmda" / "_manifest.json"
        STAGING_DB = REPO_ROOT / "data" / "staging" / "hmda_lar.duckdb"
        YEARS = [2022, 2023, 2024]
        TABLES = {y: f"lar_{y}" for y in YEARS}

        SYB_LEI = "4LJGQ9KJ9S0CP4B1FY29"

        pd.set_option("display.max_rows", 200)
        pd.set_option("display.max_columns", 60)
        pd.set_option("display.width", 160)

        print(f"repo root:   {REPO_ROOT}")
        print(f"manifest:    {MANIFEST_PATH}")
        print(f"staging db:  {STAGING_DB}")
        if not STAGING_DB.exists():
            raise SystemExit(
                "staging database not found. run: python scripts/build_staging_hmda.py"
            )

        con = duckdb.connect(str(STAGING_DB), read_only=True)
        con.execute("PRAGMA threads = 8")
        print("connected read-only to staging")
    """),
    md("""
        ## 1. Data presence and manifest

        Read the registered manifest and count rows per year in the staging database. The row counts must match the verified baseline in the EDA plan.
    """),
    code("""
        with open(MANIFEST_PATH) as fh:
            manifest = json.load(fh)

        manifest_df = pd.DataFrame(
            [
                {
                    "year": e["year"],
                    "asset": e["asset"],
                    "bytes": e["bytes"],
                    "downloaded_at_utc": e["downloaded_at_utc"],
                    "local_path": e["local_path"],
                    "sha256_prefix": e["sha256"][:12],
                }
                for e in manifest["entries"]
            ]
        ).sort_values(["year", "asset"]).reset_index(drop=True)
        manifest_df
    """),
    code("""
        counts = []
        for year in YEARS:
            n = con.execute(f"SELECT COUNT(*) FROM {TABLES[year]}").fetchone()[0]
            counts.append({"year": year, "rows": int(n)})
        counts_df = pd.DataFrame(counts)
        counts_df["rows_m"] = (counts_df["rows"] / 1_000_000).round(2)
        counts_df
    """),
    md("""
        ## 2. Column surface and schema delta

        For each year, list every column. Compute year-over-year schema delta. Flag any column present in fewer than 95 percent of years (in a three-year window this means any column absent from even one year).
    """),
    code("""
        def columns_for(year: int) -> list[str]:
            return [
                r[0]
                for r in con.execute(
                    f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{TABLES[year]}' "
                    f"ORDER BY ordinal_position"
                ).fetchall()
            ]

        cols_by_year = {y: columns_for(y) for y in YEARS}
        for y, cols in cols_by_year.items():
            print(f"{y}: {len(cols)} columns")

        all_cols = sorted(set().union(*cols_by_year.values()))
        presence = pd.DataFrame(
            {y: [c in cols_by_year[y] for c in all_cols] for y in YEARS},
            index=all_cols,
        )
        presence["present_in_years"] = presence[YEARS].sum(axis=1)
        presence["present_rate"] = presence["present_in_years"] / len(YEARS)

        inconsistent = presence[presence["present_rate"] < 1.0]
        print(f"\\nunion columns across all years: {len(all_cols)}")
        print(f"columns missing from at least one year: {len(inconsistent)}")
        inconsistent
    """),
    code("""
        def delta(a_year: int, b_year: int) -> dict:
            a, b = set(cols_by_year[a_year]), set(cols_by_year[b_year])
            return {
                "from": a_year,
                "to": b_year,
                "added": sorted(b - a),
                "removed": sorted(a - b),
            }

        deltas = [delta(YEARS[i], YEARS[i + 1]) for i in range(len(YEARS) - 1)]
        for d in deltas:
            print(f"{d['from']} -> {d['to']}: added={d['added']} removed={d['removed']}")
    """),
    md("""
        ## 3. Type inference and null profile

        Staging stores every column as VARCHAR to preserve the `Exempt` sentinel and mixed encodings. This section infers per-column type by scanning all non-null, non-empty values per year in a single batched query (one query per year, SUM-CASE-WHEN per column and per type bucket). The output also yields the null rate per column which feeds section 4.

        Buckets per column value:

        - `int`: matches `^-?\\d+$`
        - `float`: matches `^-?\\d+\\.\\d+$`
        - `exempt`: literal string `Exempt`
        - `text`: everything else that is not null or empty

        A column is labelled `mixed` when at least two buckets each hold more than 1 percent of non-null values.
    """),
    code("""
        INT_RE = r"^-?[0-9]+$"
        FLOAT_RE = r"^-?[0-9]+\\.[0-9]+$"

        def _alias(col: str) -> str:
            return re.sub(r"[^0-9a-zA-Z_]", "_", col)

        def type_and_null_for_year(year: int) -> pd.DataFrame:
            table = TABLES[year]
            cols = cols_by_year[year]
            parts = []
            for c in cols:
                safe = f'"{c}"'
                a = _alias(c)
                parts.append(f"SUM(CASE WHEN {safe} IS NULL OR {safe} = '' THEN 1 ELSE 0 END) AS n_null__{a}")
                parts.append(f"SUM(CASE WHEN {safe} = 'Exempt' THEN 1 ELSE 0 END) AS n_exempt__{a}")
                parts.append(f"SUM(CASE WHEN regexp_matches({safe}, '{INT_RE}') THEN 1 ELSE 0 END) AS n_int__{a}")
                parts.append(f"SUM(CASE WHEN regexp_matches({safe}, '{FLOAT_RE}') THEN 1 ELSE 0 END) AS n_float__{a}")
            sql = "SELECT COUNT(*) AS n_rows, " + ", ".join(parts) + f" FROM {table}"
            row = con.execute(sql).fetchdf().iloc[0].to_dict()
            n_rows = int(row.pop("n_rows"))

            recs = []
            for c in cols:
                a = _alias(c)
                n_null = int(row[f"n_null__{a}"])
                n_ex = int(row[f"n_exempt__{a}"])
                n_int = int(row[f"n_int__{a}"])
                n_float = int(row[f"n_float__{a}"])
                n_non_null = n_rows - n_null
                n_text = max(n_non_null - n_ex - n_int - n_float, 0)
                if n_non_null == 0:
                    inferred = "all_null"
                    pcts = {"int": 0.0, "float": 0.0, "exempt": 0.0, "text": 0.0}
                else:
                    pcts = {
                        "int": n_int / n_non_null,
                        "float": n_float / n_non_null,
                        "exempt": n_ex / n_non_null,
                        "text": n_text / n_non_null,
                    }
                    present = [k for k, v in pcts.items() if v > 0.01]
                    if len(present) > 1:
                        inferred = "mixed"
                    else:
                        inferred = max(pcts, key=pcts.get)
                recs.append({
                    "year": year,
                    "column": c,
                    "n_rows": n_rows,
                    "null_count": n_null,
                    "null_rate": round(n_null / n_rows, 4) if n_rows else 1.0,
                    "inferred": inferred,
                    "int_pct": round(100 * pcts["int"], 2),
                    "float_pct": round(100 * pcts["float"], 2),
                    "exempt_pct": round(100 * pcts["exempt"], 2),
                    "text_pct": round(100 * pcts["text"], 2),
                })
            return pd.DataFrame(recs)

        profile_frames = []
        for y in YEARS:
            print(f"profiling {y} ...", flush=True)
            profile_frames.append(type_and_null_for_year(y))
        profile_df = pd.concat(profile_frames, ignore_index=True)
        profile_df.head(20)
    """),
    code("""
        # Columns flagged as mixed in any year: these need explicit cast rules in staging.
        mixed_cols = (
            profile_df[profile_df["inferred"] == "mixed"]
            .sort_values(["column", "year"])
            .reset_index(drop=True)
        )
        print(f"columns with mixed-type values (in any year): "
              f"{mixed_cols['column'].nunique()}")
        mixed_cols[["year", "column", "inferred", "int_pct", "float_pct",
                    "exempt_pct", "text_pct"]]
    """),
    md("""
        ## 4. Null profile

        Null rate per column per year, sorted by rate descending. Rates use the null count from the batched query in section 3 (SQL NULL and empty string both treated as null since CSV parsing preserves the distinction but both indicate missing value).
    """),
    code("""
        null_df = profile_df[["year", "column", "null_count", "null_rate"]].copy()
        null_wide = (
            null_df.pivot(index="column", columns="year", values="null_rate")
            .fillna(1.0)
        )
        null_wide = null_wide.sort_values(YEARS[-1], ascending=False)
        null_wide.head(30)
    """),
    code("""
        # Columns above 50 percent null in the most recent year
        high_null = null_wide[null_wide[YEARS[-1]] > 0.50]
        print(f"columns with > 50% null rate in {YEARS[-1]}: {len(high_null)}")
        high_null
    """),
    md("""
        ## 5. Exempt-value profile

        Under HMDA partial exemption, smaller reporters may record the string `Exempt` in fields that would otherwise carry a numeric value. Count `Exempt` per year per eligible field, and count the distinct reporters exercising exemption in each year.
    """),
    code("""
        EXEMPT_ELIGIBLE = [
            "rate_spread",
            "interest_rate",
            "origination_charges",
            "debt_to_income_ratio",
            "loan_to_value_ratio",
            "total_loan_costs",
            "total_points_and_fees",
            "discount_points",
            "lender_credits",
            "loan_term",
            "prepayment_penalty_term",
            "intro_rate_period",
            "property_value",
            "multifamily_affordable_units",
        ]

        exempt_by_year = (
            profile_df[profile_df["column"].isin(EXEMPT_ELIGIBLE)]
            .assign(exempt_count=lambda d: (d["exempt_pct"] / 100
                                            * (d["n_rows"] - d["null_count"]))
                                           .round().astype(int))
            [["year", "column", "exempt_count"]]
        )
        exempt_pivot = exempt_by_year.pivot(
            index="column", columns="year", values="exempt_count"
        ).fillna(0).astype(int)
        exempt_pivot
    """),
    code("""
        # Distinct reporters (LEIs) with at least one Exempt value on any eligible
        # field per year. One SELECT per year.
        reporter_rows = []
        for year in YEARS:
            table = TABLES[year]
            present = [c for c in EXEMPT_ELIGIBLE if c in cols_by_year[year]]
            if not present:
                reporter_rows.append({"year": year, "distinct_exempt_reporters": 0})
                continue
            conds = " OR ".join(f'"{c}" = \\'Exempt\\'' for c in present)
            n = con.execute(
                f"SELECT COUNT(DISTINCT lei) FROM {table} WHERE {conds}"
            ).fetchone()[0]
            reporter_rows.append({"year": year, "distinct_exempt_reporters": int(n)})
        exempt_reporters_df = pd.DataFrame(reporter_rows)
        exempt_reporters_df
    """),
    md("""
        ## 6. Composite primary key uniqueness

        The EDA plan specifies `(lei, activity_year, universal_loan_identifier)` as the candidate loan-level primary key. The CFPB nationwide public LAR strips `universal_loan_identifier` to prevent loan-level re-identification. This section documents the absence and reports per-LEI record counts as a descriptive proxy.

        Decision implication: downstream dimensional model cannot rely on a natural loan-level PK from the nationwide LAR. Either adopt a row-ordinal synthetic PK at ingest, or source the LAR from the Loan-Application-Register dataset that preserves ULI for any model that requires loan grain.
    """),
    code("""
        uli_status = pd.DataFrame(
            [{"year": y, "has_uli": "universal_loan_identifier" in cols_by_year[y]}
             for y in YEARS]
        )
        uli_status
    """),
    code("""
        rows = []
        for year in YEARS:
            table = TABLES[year]
            n_lei = con.execute(
                f"SELECT COUNT(DISTINCT lei) FROM {table}"
            ).fetchone()[0]
            total = int(counts_df.loc[counts_df["year"] == year, "rows"].iloc[0])
            rows.append({
                "year": year,
                "rows": total,
                "distinct_leis": int(n_lei),
                "mean_rows_per_lei": round(total / n_lei, 1),
            })
        pd.DataFrame(rows)
    """),
    md("""
        ## 7. Referential integrity against the filer roster

        Every LEI that appears in the LAR should appear in the filer roster JSON for the same year. We load the roster per year, compare LEI sets, and report orphan LEIs on either side (LAR-only LEIs signal integrity defects; roster-only LEIs signal non-filing institutions).
    """),
    code("""
        ROSTER_PATHS = {
            y: REPO_ROOT / "data" / "raw" / "hmda" / str(y) / f"{y}_public_filers.json"
            for y in YEARS
        }

        def load_roster_leis(path: Path) -> set[str]:
            with open(path) as fh:
                data = json.load(fh)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = None
                for k in ("institutions", "filers", "data"):
                    if k in data and isinstance(data[k], list):
                        items = data[k]
                        break
                if items is None:
                    items = list(data.values())[0] if data else []
            else:
                items = []
            leis = set()
            for item in items:
                if not isinstance(item, dict):
                    continue
                for key in ("lei", "LEI", "legal_entity_identifier"):
                    if key in item and item[key]:
                        leis.add(str(item[key]).strip().upper())
                        break
            return leis

        ri_rows = []
        for year in YEARS:
            roster = load_roster_leis(ROSTER_PATHS[year])
            lar_leis_raw = [
                r[0] for r in con.execute(
                    f"SELECT DISTINCT lei FROM {TABLES[year]}"
                ).fetchall()
            ]
            lar_leis = {x.upper() for x in lar_leis_raw if x}
            ri_rows.append({
                "year": year,
                "roster_leis": len(roster),
                "lar_leis": len(lar_leis),
                "orphan_in_lar": len(lar_leis - roster),
                "orphan_in_roster": len(roster - lar_leis),
            })
        pd.DataFrame(ri_rows)
    """),
    code("""
        # SYB anchor sanity: confirm Stock Yards is in both roster and LAR every year.
        rows = []
        for year in YEARS:
            roster = load_roster_leis(ROSTER_PATHS[year])
            lar_has = con.execute(
                f"SELECT COUNT(*) FROM {TABLES[year]} WHERE lei = ?",
                [SYB_LEI],
            ).fetchone()[0]
            rows.append({
                "year": year,
                "in_roster": SYB_LEI in roster,
                "lar_records": int(lar_has),
            })
        pd.DataFrame(rows)
    """),
    md("""
        ## 8. Value-set validation (code-encoded fields)

        For each field with a documented code list in the HMDA filing instructions, list distinct values and counts per year. A value not in the documented set is a data defect; it is captured in the DQ notes at the bottom of the notebook.

        Code lists here follow the 2022 to 2024 HMDA filing instructions. The sentinel `1111` denotes "not applicable" on several fields (for example for purchased loans where preapproval status is structurally unavailable).
    """),
    code("""
        CODE_FIELDS = {
            "action_taken": {"1", "2", "3", "4", "5", "6", "7", "8"},
            "loan_type": {"1", "2", "3", "4"},
            "loan_purpose": {"1", "2", "31", "32", "4", "5"},
            "occupancy_type": {"1", "2", "3"},
            "construction_method": {"1", "2"},
            "business_or_commercial_purpose": {"1", "2", "1111"},
            "hoepa_status": {"1", "2", "3", "1111"},
            "lien_status": {"1", "2", "1111"},
            "preapproval": {"1", "2", "1111"},
        }

        code_rows = []
        for year in YEARS:
            table = TABLES[year]
            for field, expected in CODE_FIELDS.items():
                if field not in cols_by_year[year]:
                    continue
                safe = f'"{field}"'
                distinct = {
                    r[0]: r[1]
                    for r in con.execute(
                        f"SELECT {safe}, COUNT(*) FROM {table} "
                        f"WHERE {safe} IS NOT NULL AND {safe} <> '' "
                        f"GROUP BY {safe}"
                    ).fetchall()
                }
                for value, n in sorted(distinct.items()):
                    code_rows.append({
                        "year": year,
                        "field": field,
                        "value": value,
                        "count": int(n),
                        "undocumented": value not in expected,
                    })

        code_df = pd.DataFrame(code_rows)
        undoc = code_df[code_df["undocumented"]]
        print(f"undocumented code-value occurrences: {len(undoc)}")
        undoc
    """),
    code("""
        doc_pivot = (
            code_df[~code_df["undocumented"]]
            .pivot_table(index=["field", "value"], columns="year",
                         values="count", aggfunc="sum", fill_value=0)
        )
        doc_pivot
    """),
    md("""
        ## Artifacts: dictionary and DQ notes

        Write field-level entries to `/docs/data-dictionary.md` (HMDA LAR section) and dated findings to `/docs/data-quality-notes.md`. Both updates are idempotent: the generator replaces delimited sections rather than appending duplicates on re-run.
    """),
    code("""
        RUN_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        DICT_PATH = REPO_ROOT / "docs" / "data-dictionary.md"
        DQ_PATH = REPO_ROOT / "docs" / "data-quality-notes.md"

        DICT_BEGIN = "<!-- BEGIN:hmda-lar-fields -->"
        DICT_END = "<!-- END:hmda-lar-fields -->"
        DQ_BEGIN = f"<!-- BEGIN:eda-01-{RUN_DATE} -->"
        DQ_END = f"<!-- END:eda-01-{RUN_DATE} -->"

        # Per-column inferred type: mark mixed if any year said mixed, else mode.
        def type_mode(s: pd.Series) -> str:
            vals = set(s.tolist())
            if "mixed" in vals:
                return "mixed"
            return s.mode().iat[0]

        type_mode_series = profile_df.groupby("column")["inferred"].agg(type_mode)
        null_mean = profile_df.groupby("column")["null_rate"].mean().round(4)

        field_tbl = pd.DataFrame({
            "present_in_years": presence["present_in_years"],
            "inferred_type": type_mode_series.reindex(presence.index),
            "avg_null_rate_3y": null_mean.reindex(presence.index).fillna(1.0),
        })
        field_tbl = field_tbl.reset_index().rename(columns={"index": "column"})
        field_tbl = field_tbl.sort_values("column").reset_index(drop=True)

        code_field_names = set(CODE_FIELDS.keys())
        exempt_field_names = set(EXEMPT_ELIGIBLE)

        def note_for(col: str) -> str:
            bits = []
            if col in code_field_names:
                bits.append("code-list validated")
            if col in exempt_field_names:
                bits.append("exempt-eligible")
            return "; ".join(bits)

        field_tbl["notes"] = field_tbl["column"].map(note_for)

        dict_rows = ["| Column | Years | Inferred type | 3y avg null rate | Notes |",
                     "| --- | --- | --- | --- | --- |"]
        for _, r in field_tbl.iterrows():
            dict_rows.append(
                f"| `{r['column']}` | {int(r['present_in_years'])}/{len(YEARS)} | "
                f"{r['inferred_type']} | {r['avg_null_rate_3y']:.2%} | {r['notes']} |"
            )
        dict_block = "\\n".join([
            DICT_BEGIN,
            f"<!-- generated by notebooks/01-hmda-schema-and-quality.ipynb on {RUN_DATE} -->",
            "",
            "### HMDA LAR fields (2022 to 2024)",
            "",
            "Source: CFPB nationwide public LAR (data-browser API). "
            "Union of columns across three vintages. "
            "ULI (`universal_loan_identifier`) is intentionally absent from this "
            "release per CFPB disclosure policy.",
            "",
            "\\n".join(dict_rows),
            "",
            DICT_END,
        ])

        dq_lines = [
            DQ_BEGIN,
            f"## {RUN_DATE} | EDA-01 HMDA Schema and Quality",
            "",
            "Row counts verified per year: "
            + ", ".join(
                f"{int(r['year'])} = {int(r['rows']):,}"
                for r in counts_df.to_dict("records")
            )
            + ".",
            "",
            f"Column surface union across 2022 to 2024: {len(all_cols)} columns. "
            f"Columns absent from at least one year: {len(inconsistent)}.",
            "",
            f"Mixed-type columns flagged: {mixed_cols['column'].nunique()}. "
            "These require explicit cast rules in staging. See notebook section 3.",
            "",
            "Universal Loan Identifier absent from nationwide public LAR in "
            "all three years. Decision: downstream loan-grain models must "
            "either accept a synthesized row-ordinal key or switch source to "
            "the LAR release that preserves ULI.",
            "",
            "Exempt-value reporters per year: "
            + ", ".join(
                f"{int(r['year'])} = {int(r['distinct_exempt_reporters']):,} LEIs"
                for r in exempt_reporters_df.to_dict("records")
            )
            + ".",
            "",
            f"Undocumented code-field values found: {len(undoc)}. "
            "See notebook section 8 for the full table.",
            "",
            DQ_END,
        ]
        dq_block = "\\n".join(dq_lines)


        def splice_block(text: str, begin: str, end: str, new_block: str) -> str:
            pattern = re.compile(
                re.escape(begin) + r".*?" + re.escape(end),
                re.DOTALL,
            )
            if pattern.search(text):
                return pattern.sub(lambda _m: new_block, text)
            return text.rstrip() + "\\n\\n" + new_block + "\\n"


        dict_text = DICT_PATH.read_text() if DICT_PATH.exists() else "# Data Dictionary\\n"
        new_dict = splice_block(dict_text, DICT_BEGIN, DICT_END, dict_block)
        DICT_PATH.write_text(new_dict)

        dq_text = DQ_PATH.read_text() if DQ_PATH.exists() else "# Data Quality Notes\\n"
        new_dq = splice_block(dq_text, DQ_BEGIN, DQ_END, dq_block)
        DQ_PATH.write_text(new_dq)

        print(f"updated {DICT_PATH.relative_to(REPO_ROOT)}")
        print(f"updated {DQ_PATH.relative_to(REPO_ROOT)}")
    """),
    code("""
        con.close()
        print("done")
    """),
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
    print(f"wrote {NOTEBOOK_PATH.relative_to(REPO_ROOT)} "
          f"({len(CELLS)} cells)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
