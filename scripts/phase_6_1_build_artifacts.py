"""Build sanitized Phase 6.1 research summaries from existing local evidence.

The LendingClub source is streamed in chunks; no individual record is exported.
Run from the repository root with the project's pandas installation available.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
OUT = ROOT / "frontend" / "public" / "data"
LC_FILE = ROOT / "Data" / "archive" / "accepted_2007_to_2018Q4.csv"
GOOD = {"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"}
BAD = {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def make_inventories() -> None:
    old = read_rows(REPORTS / "phase_3_dataset_inventory.csv")
    audit = {row["column"]: row for row in read_rows(REPORTS / "phase_2_2_feature_leakage_audit.csv")}
    decisions = {row["column"]: row for row in read_rows(REPORTS / "phase_2_3_feature_decisions.csv")}
    metadata = {
        "DS001": ("LendingClub accepted loans", "https://figshare.com/articles/dataset/Lending_Club/22121477 (reference copy; local-copy provenance unverified)", "loan_status", "Closed-loan terminal outcome: Fully Paid=0; Charged Off/Default=1; excludes active/censored statuses", "19.98% among 1,348,099 closed loans (raw labeled-positive share 11.92%)", "2007–2018Q4 origination", "Commercial permission not established for this local copy", "Contains direct/free-text identifiers in source columns; 7 identifier columns excluded from model; do not expose records", "Active loans censored; terminal status is variable-horizon, not fixed-horizon PD; 40.37% unresolved/current cohort excluded", "Historical U.S. offline benchmark; no Indian transfer claim", "QUALIFIED_FOR_RESEARCH"),
        "DS002": ("LendingClub accepted loans (Excel-limited copy)", "Same reference as DS001; local-copy provenance unverified", "loan_status", "Same as DS001; copy truncated by Excel row limit", "Not separately recalculated", "2007–2018Q4, truncated", "Unknown, same terms as DS001", "Same sensitive columns as DS001", "Incomplete copy; never append to the CSV", "No analytical use; preserve as duplicate/truncated artifact", "BLOCKED"),
        "DS003": ("Default of Credit Card Clients", "https://archive.ics.uci.edu/dataset/350/default", "default payment next month", "Binary next-month default label", "22.12% (6,636/30,000)", "Taiwan credit-card history Apr–Sep 2005; next-month label", "CC BY 4.0; attribution required; commercial use permitted under CC BY subject to its terms", "Includes age, sex, marital status, and ID; exclude/protect as appropriate", "Historical cross-sectional benchmark; random split can overstate future transfer", "Independent Taiwan credit-card benchmark methods only", "QUALIFIED_FOR_RESEARCH"),
        "DS004": ("Statlog German Credit", "https://archive.ics.uci.edu/dataset/144/statlog-german-credit-data", "attribute 21", "Good/bad creditworthiness class, not a dated observed default event", "30% bad (300/1,000)", "Historical German records; no row-level dates", "CC BY 4.0; attribution required", "Age, sex/status, foreign-worker attribute; small old sample", "No time-based holdout; target is proxy creditworthiness", "Preprocessing/cost-sensitive proxy benchmark only", "REVIEW_REQUIRED"),
        "DS005": ("Statlog German Credit numeric variant", "https://archive.ics.uci.edu/dataset/144/statlog-german-credit-data", "encoded attribute 21", "Same target as DS004 in a numeric encoding", "30% bad (same 1,000 records)", "Same as DS004", "CC BY 4.0; attribution required", "Same population/attributes as DS004", "Duplicate/re-encoding of DS004, not independent data; no dates", "Encoding/preprocessing comparison only", "REVIEW_REQUIRED"),
        "DS006": ("UCI Credit Approval", "https://archive.ics.uci.edu/dataset/27/credit%2Bapproval", "A16", "Application accepted/rejected, not loan repayment/default", "44.49% approved (307/690)", "Historical source era 1987; no row-level dates", "CC BY 4.0; attribution required", "Feature labels/values anonymized; missing data", "Approval-policy label is not repayment outcome", "Preprocessing/approval classification only", "BLOCKED"),
        "DS007": ("CreditMitra UPI narrations", "Local file; no source record supplied", "None", "No repayment/default labels", "N/A", "Narration sample spans 5–15 Nov 2025 per Phase 3 report", "No license/consent evidence in workspace", "Potentially sensitive financial narration/counterparty data", "No amount, borrower key, or outcome; no documented authorization", "Only after provenance/permission review; not model training", "BLOCKED"),
        "DS008": ("Phase 1 synthetic outcomes", "Project synthetic generator", "default_30d/60d/90d", "Generated outcome flags", "Synthetic; not a real prevalence", "Synthetic", "Synthetic project output", "No real people; synthetic IDs", "Synthetic label mechanism is not real-world outcome evidence", "Pipeline tests only", "BLOCKED"),
        "DS009": ("Phase 1 synthetic transactions", "Project synthetic generator", "None", "Synthetic transaction features", "N/A", "Synthetic", "Synthetic project output", "Synthetic records", "Not observed financial behavior", "Pipeline tests only", "BLOCKED"),
        "DS010": ("Processed synthetic borrower features", "Derived from DS008/DS009", "None", "Synthetic feature table", "N/A", "Synthetic", "Synthetic project output", "Synthetic borrower IDs", "Not real financial features/outcomes", "Reproducibility tests only", "BLOCKED"),
        "DS011": ("Phase 1.1 synthetic outcomes", "Phase 1.1 synthetic generator", "default_30d/60d/90d", "Generated outcome flags with dates", "Synthetic; not a real prevalence", "Synthetic", "Synthetic project output", "No real people; synthetic IDs", "Synthetic label mechanism is not real-world outcome evidence", "Pipeline tests only", "BLOCKED"),
        "DS012": ("Phase 1.1 synthetic transactions", "Phase 1.1 synthetic generator", "None", "Synthetic transaction features", "N/A", "Synthetic", "Synthetic project output", "Synthetic records", "Not observed financial behavior", "Pipeline tests only", "BLOCKED"),
        "DS013": ("Phase 1.1 synthetic borrower features", "Derived from DS011/DS012", "None", "Synthetic feature table", "N/A", "Synthetic", "Synthetic project output", "Synthetic borrower IDs", "Not real financial features/outcomes", "Reproducibility tests only", "BLOCKED"),
        "DS014": ("NPCI monthly UPI statistics", "https://www.npci.org.in/product/upi/product-statistics", "None", "Aggregate banks/volume/value", "N/A", "FY2016-17–FY2026-27 (Apr–Sep 2026); 126 monthly observations", "Public stats page; no local redistribution license statement verified", "No borrower-level data", "Aggregate time series cannot support borrower labels", "Macro context only", "BLOCKED"),
        "DS015": ("RBI industry-wise bank credit deployment", "https://dbieold.rbi.org.in/DBIE/", "None", "Aggregate industry-sector credit", "N/A", "Multiple historical periods; workbook formats include 1997–2007 and 2019 onward", "RBI DBIE public statistics; local reuse terms not bundled", "Aggregate only", "No borrower outcomes/features", "Macro context only", "BLOCKED"),
        "DS016": ("RBI deployment by major sectors", "https://dbieold.rbi.org.in/DBIE/", "None", "Aggregate sector credit", "N/A", "Monthly series, multiple years", "RBI DBIE public statistics; local reuse terms not bundled", "Aggregate only", "No borrower outcomes/features", "Macro context only", "BLOCKED"),
        "DS017": ("RBI district-wise SCB credit (damaged workbook)", "https://dbieold.rbi.org.in/DBIE/", "Unverified", "Unknown; workbook unreadable", "Unknown", "Unknown", "RBI DBIE intended source; local file is corrupt", "Expected geographic aggregate, unverified", "BadZipFile; rows/schema cannot be inspected", "Do not use until authorized copy is acquired and checked", "BLOCKED"),
    }
    rows = []
    for oldrow in old:
        dsid = oldrow["dataset_id"]
        info = metadata.get(dsid)
        if not info:
            continue
        (name, source, target, target_def, prevalence, time_coverage, license_terms,
         pii, risks, use, qualification) = info
        rel = oldrow["local_path"]
        abs_path = ROOT / rel
        if dsid == "DS014":
            paths = list((ROOT / "Data" / "india_upi" / "NPCI").rglob("*.xlsx"))
            size = sum(p.stat().st_size for p in paths)
            format_name = "11 XLSX files"
            local_status = "present"
        else:
            size = abs_path.stat().st_size if abs_path.is_file() else "unknown"
            format_name = oldrow["file_format"]
            local_status = "present" if abs_path.is_file() else "damaged/unknown"
        column_missing = [float(item["missing_pct"]) for item in audit.values() if item.get("missing_pct", "")]
        missing = "not computed for all fields"
        if dsid == "DS001" and column_missing:
            missing = f"{sum(column_missing) / len(column_missing):.2f}% average of 151 per-column missing percentages; rounded source audit"
        elif dsid == "DS003":
            missing = "0% (local UCI report; verify when refreshing source)"
        elif dsid == "DS004":
            missing = "0% (local UCI report; verify when refreshing source)"
        elif dsid == "DS006":
            missing = "67 missing cells across 37 rows (local UCI report); cell-level denominator not recalculated"
        elif dsid in {"DS008", "DS011", "DS010", "DS013"}:
            missing = "not recalculated in Phase 6.1"
        rows.append({
            "dataset_id": dsid, "dataset_name": name, "local_path": rel, "local_status": local_status,
            "source_url": source, "format": format_name, "size_bytes": size,
            "row_count": oldrow["row_count"], "column_count": oldrow["column_count"],
            "target_column": target, "target_definition": target_def, "target_prevalence": prevalence,
            "time_coverage": time_coverage, "missing_value_percentage": missing,
            "duplicate_row_count": "not measured in Phase 6.1",
            "provenance_status": "documented project generation" if "synthetic" in oldrow["category"].lower() else "see source/licence caveat",
            "license_and_access": license_terms, "commercial_use": "Separate review required; only clearly permitted where noted",
            "pii_sensitive_concerns": pii, "leakage_temporal_risks": risks,
            "proposed_research_use": use, "qualification_decision": qualification,
        })
    external = [
        {"dataset_id":"EXT001","dataset_name":"City Bank Loan Default Prediction (vehicle finance)","local_path":"","local_status":"not downloaded","source_url":"https://www.kaggle.com/competitions/city-bank-loan-default-prediction/data","format":"Kaggle competition files (not inspected)","size_bytes":"unknown","row_count":"unknown","column_count":"unknown","target_column":"default (reported in competition data description)","target_definition":"First EMI payment default on due date; not a 90-day or general PD target","target_prevalence":"not verified","time_coverage":"not verified","missing_value_percentage":"not verified","duplicate_row_count":"not verified","provenance_status":"competition page found; underlying files not locally present/inspected","license_and_access":"Kaggle login and acceptance of competition rules required to view/download; terms need review","commercial_use":"Unknown; do not assume permitted","pii_sensitive_concerns":"Unknown until schema/file review","leakage_temporal_risks":"Need point-in-time audit and cohort/split review once authorized files are available","proposed_research_use":"Potential India vehicle-finance first-EMI research after access, terms, schema, PII and leakage review","qualification_decision":"BLOCKED"},
        {"dataset_id":"EXT002","dataset_name":"OpenML Credit-Risk-Dataset (ID 43454)","local_path":"","local_status":"public remote metadata; not downloaded","source_url":"https://www.openml.org/search?id=43454&type=data","format":"ARFF (remote)","size_bytes":"remote file; not acquired","row_count":"32,581","column_count":"12 features (OpenML metadata)","target_column":"loan_status","target_definition":"0 non-default, 1 default per dataset description","target_prevalence":"not verified from permitted metadata inspection","time_coverage":"collection date 2020-02-06; no verified per-row origination date","missing_value_percentage":"4,011 missing cells and 3,943 rows with missing attributes per OpenML quality metadata; schema denominator not verified","duplicate_row_count":"not verified","provenance_status":"OpenML verified entry; community-uploaded data; upstream provenance requires review","license_and_access":"CC0 Public Domain shown in OpenML metadata","commercial_use":"CC0 indicates no copyright restrictions on dataset; check upstream/right-of-personality and applicable law","pii_sensitive_concerns":"Age and financial attributes; no direct identifiers described in metadata","leakage_temporal_risks":"No verified row-level chronology; cannot form a proper chronological holdout; inspect target derivation and upstream source","proposed_research_use":"Preprocessing and secondary generic credit-risk benchmark only, not Indian validation","qualification_decision":"REVIEW_REQUIRED"},
        {"dataset_id":"EXT003","dataset_name":"Indian self-help-group microfinance survey (PLOS ONE 2026)","local_path":"","local_status":"supporting CSVs publicly linked; not downloaded","source_url":"https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0341674","format":"Supporting CSV files S1–S4","size_bytes":"not inspected","row_count":"400 SHG members per article; per-file rows/schema not verified","column_count":"not verified","target_column":"survey-derived group risk/repayment constructs; no standardized loan-level label established","target_definition":"Cross-sectional respondent/perception outcomes, including internal/external delinquency constructs; not point-in-time future default","target_prevalence":"not applicable/not verified","time_coverage":"Single survey/research collection; row-level outcome timing not established","missing_value_percentage":"not inspected","duplicate_row_count":"not inspected","provenance_status":"Peer-reviewed article with supporting information; study reports verbal consent for collection","license_and_access":"PLOS article CC BY; verify supplementary file rights/attribution on retrieval","commercial_use":"CC BY article reuse with attribution; confirm the supporting data's applicable terms before commercial use","pii_sensitive_concerns":"Human participants and financial/social variables; do not publish row-level microdata without ethics/privacy review","leakage_temporal_risks":"Small, cross-sectional survey; group context and self-reported measures; no suitable time-based default prediction design","proposed_research_use":"Literature/survey-method context or separate SHG behavior analysis after file and ethics review; not general PD training","qualification_decision":"REVIEW_REQUIRED"},
    ]
    rows.extend(external)
    fields = list(rows[0])
    write_csv(REPORTS / "phase_6_1_dataset_inventory.csv", rows, fields)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phase_6_1_dataset_inventory.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    feature_rows = []
    all_columns = list(audit)
    for column in all_columns:
        audit_row = audit[column]
        decision_row = decisions.get(column, {})
        action = decision_row.get("decision", "Target Label" if column == "loan_status" else "Not in Phase 2.3 matrix")
        feature_rows.append({
            "dataset_id": "DS001", "feature": column,
            "availability_time": audit_row.get("availability_time", "unknown"),
            "leakage_risk": audit_row.get("leakage_risk", "unknown"),
            "phase_2_2_recommendation": audit_row.get("recommended_action", "unknown"),
            "phase_2_3_decision": action,
            "missing_percentage_all_source_rows": audit_row.get("missing_pct", ""),
            "meaning": audit_row.get("meaning", ""),
            "decision_reason": decision_row.get("reason", audit_row.get("reason", "")),
            "proposed_ui_use": "Excluded from record-level display; feature metadata only" if action.lower().startswith("exclude") else "Model field only; no raw record display",
        })
    write_csv(REPORTS / "phase_6_1_feature_inventory.csv", feature_rows, list(feature_rows[0]))
    (OUT / "phase_6_1_feature_inventory.json").write_text(json.dumps(feature_rows, indent=2), encoding="utf-8")


def make_dashboard_data() -> None:
    if not LC_FILE.is_file():
        raise FileNotFoundError(f"Required existing dataset not found: {LC_FILE.name}")
    columns = ["issue_d", "loan_status", "grade", "purpose", "term", "loan_amnt", "int_rate", "annual_inc", "dti", "fico_range_low", "revol_util"]
    groups: dict[str, dict[str, Counter]] = {
        "vintage": defaultdict(Counter), "grade": defaultdict(Counter),
        "purpose": defaultdict(Counter), "term": defaultdict(Counter),
    }
    statuses: Counter = Counter()
    amount_bins = [0, 2_500, 5_000, 7_500, 10_000, 15_000, 20_000, 25_000, 35_000, 50_000, 100_000]
    amount_labels = ["$0–2.5k", "$2.5–5k", "$5–7.5k", "$7.5–10k", "$10–15k", "$15–20k", "$20–25k", "$25–35k", "$35–50k", "$50–100k"]
    amount_hist: Counter = Counter()
    numeric_names = ["loan_amnt", "int_rate", "annual_inc", "dti", "fico_range_low", "revol_util"]
    corr_n = 0
    corr_sum = pd.Series(0.0, index=numeric_names)
    corr_cross = pd.DataFrame(0.0, index=numeric_names, columns=numeric_names)
    rows_seen = 0
    for chunk in pd.read_csv(LC_FILE, usecols=columns, chunksize=100_000, low_memory=False):
        rows_seen += len(chunk)
        chunk["loan_status"] = chunk["loan_status"].fillna("Missing status")
        statuses.update(chunk["loan_status"].value_counts(dropna=False).to_dict())
        loan_amount = pd.to_numeric(chunk["loan_amnt"], errors="coerce")
        cuts = pd.cut(loan_amount, bins=amount_bins, labels=amount_labels, right=True, include_lowest=True)
        amount_hist.update(cuts.value_counts().to_dict())
        numeric = chunk[numeric_names].apply(pd.to_numeric, errors="coerce").dropna()
        if not numeric.empty:
            values = numeric.to_numpy(dtype="float64")
            corr_n += len(values)
            corr_sum += values.sum(axis=0)
            corr_cross += pd.DataFrame(values.T @ values, index=numeric_names, columns=numeric_names)
        years = chunk["issue_d"].astype("string").str.extract(r"(\d{4})", expand=False)
        valid_year = years.notna()
        closed = chunk["loan_status"].isin(GOOD | BAD)
        bad = chunk["loan_status"].isin(BAD)
        for key, values in (("vintage", years), ("grade", chunk["grade"]), ("purpose", chunk["purpose"]), ("term", chunk["term"])):
            ok = values.notna()
            work = pd.DataFrame({"segment": values[ok].astype(str), "closed": closed[ok].astype(int), "bad": bad[ok].astype(int)})
            summary = work.groupby("segment", sort=True).agg(records=("closed", "size"), closed=("closed", "sum"), defaults=("bad", "sum"))
            for segment, record in summary.iterrows():
                counter = groups[key][str(segment)]
                counter.update({"records": int(record["records"]), "closed": int(record["closed"]), "defaults": int(record["defaults"])})

    def segment_rows(name: str) -> list[dict]:
        result = []
        for segment, counts in groups[name].items():
            closed_count = counts["closed"]
            result.append({"segment": segment, "records": counts["records"], "closed": closed_count,
                           "defaults": counts["defaults"],
                           "observed_closed_default_rate": round(counts["defaults"] / closed_count, 6) if closed_count else None})
        return sorted(result, key=lambda x: x["segment"])

    metrics = read_rows(REPORTS / "phase_2_3_metrics.csv")
    splits = read_rows(REPORTS / "phase_2_3_split_summary.csv")
    test_metrics = [row for row in metrics if row["split_name"] == "Test"]
    data = {
        "generated_at": "2026-10-13",
        "source_label": "HISTORICAL RESEARCH DATA",
        "dataset": {"id": "DS001", "name": "LendingClub accepted loans", "source_file": "Data/archive/accepted_2007_to_2018Q4.csv",
                    "records": rows_seen, "source_columns": 151, "origination_period": "2007–2018Q4",
                    "raw_default_share": round(sum(statuses[s] for s in BAD) / rows_seen, 6),
                    "closed_records": sum(statuses[s] for s in GOOD | BAD),
                    "closed_defaults": sum(statuses[s] for s in BAD),
                    "closed_default_rate": round(sum(statuses[s] for s in BAD) / sum(statuses[s] for s in GOOD | BAD), 6),
                    "unresolved_or_censored": rows_seen - sum(statuses[s] for s in GOOD | BAD),
                    "status_distribution": [{"status": s, "count": int(n)} for s, n in sorted(statuses.items(), key=lambda item: (-item[1], item[0]))]},
        "evaluation": {"id": "phase_2_3_closed_loan_time_split", "evaluation_date": "2026-10-11",
                       "target": "terminal closed-loan outcome at dataset cutoff; not fixed-horizon PD",
                       "split_design": "issue_d chronological: train 2007–2013, validation 2014–2015, untouched test 2016–2018",
                       "calibration": "not fitted", "curve_coordinates_available": False,
                       "saved_prediction_rows_available": False,
                       "metrics": [{key: (None if value == "" else value) for key, value in row.items()} for row in test_metrics],
                       "all_split_metrics": [{key: (None if value == "" else value) for key, value in row.items()} for row in metrics],
                       "splits": [{key: (None if value == "" else value) for key, value in row.items()} for row in splits]},
        "portfolio": {"vintage": segment_rows("vintage"), "grade": segment_rows("grade"),
                      "purpose": segment_rows("purpose"), "term": segment_rows("term"),
                      "loan_amount_histogram": [{"bin": label, "count": int(amount_hist[label])} for label in amount_labels],
                      "numeric_correlation_fields": numeric_names,
                      "numeric_correlation_complete_rows": corr_n,
                      "numeric_correlation": []},
        "limitations": ["U.S. LendingClub cohort only; no Indian transfer claim.",
                        "Historical terminal closed-loan status, variable outcome horizon.",
                        "Active and unresolved records are censored/excluded from binary closed-cohort rates.",
                        "No saved row-level prediction scores, ROC/PR curve coordinates, or local explanation values.",
                        "No raw borrower records are exported by this summary."],
    }
    if corr_n > 1:
        means = corr_sum / corr_n
        covariance = corr_cross / corr_n - pd.DataFrame([[means[i] * means[j] for j in numeric_names] for i in numeric_names], index=numeric_names, columns=numeric_names)
        scales = covariance.clip(lower=0).pow(0.5)
        denom = pd.DataFrame([[scales.loc[i, i] * scales.loc[j, j] for j in numeric_names] for i in numeric_names], index=numeric_names, columns=numeric_names)
        matrix = covariance.divide(denom.where(denom != 0)).fillna(0).clip(-1, 1)
        data["portfolio"]["numeric_correlation"] = [{"feature": row, "values": {col: round(float(matrix.loc[row, col]), 4) for col in numeric_names}} for row in numeric_names]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "phase_6_1_lendingclub_summary.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Streamed {rows_seen:,} source rows; wrote sanitized aggregate summary to frontend/public/data/phase_6_1_lendingclub_summary.json")


if __name__ == "__main__":
    make_inventories()
    make_dashboard_data()
