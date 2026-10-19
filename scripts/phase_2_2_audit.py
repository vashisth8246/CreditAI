"""Reproducible audit script for Phase 2.2 Real Dataset Qualification and LendingClub Label Audit."""

import os
import sys
import pandas as pd
import numpy as np

LC_CSV_PATH = os.path.join("Data", "archive", "accepted_2007_to_2018Q4.csv")
REPORTS_DIR = "reports"

# 151 Column Definitions & Feature Leakage Audit Taxonomy
COLUMN_METADATA = {
    # Identifiers & Direct Metadata / Free Text
    "id": ("Loan ID string", "Origination/Metadata", "Identifier/PII", "Exclude", "Unique loan identifier; risk of split leakage"),
    "member_id": ("Borrower member ID", "Origination/Metadata", "Identifier/PII", "Exclude", "Direct borrower identifier; risk of borrower leakage"),
    "url": ("LendingClub loan URL", "Origination/Metadata", "Identifier/PII", "Exclude", "Contains loan ID; direct link/identifier"),
    "desc": ("Borrower application text", "Application", "Identifier/PII", "Exclude", "Free-text field with personal disclosures"),
    "emp_title": ("Employer job title", "Application", "Identifier/PII", "Exclude", "Unstructured high-cardinality text; privacy/PII risk"),
    "title": ("Loan title provided by borrower", "Application", "Identifier/PII", "Exclude", "Unstructured free-text field"),
    "zip_code": ("First 3 digits of ZIP code", "Application", "Identifier/PII", "Exclude", "Coarse geographic location identifier"),

    # Target Variable
    "loan_status": ("Current loan status", "Outcome/Metadata", "High (Target Leakage)", "Target Label", "Ground truth outcome target for audit mapping"),

    # Post-Origination State / Repayment / Collection / Settlement / Hardship Leakage
    "pymnt_plan": ("Payment plan indicator", "Post-Origination", "High (Target Leakage)", "Exclude", "Indicates post-delinquency payment plan modification"),
    "out_prncp": ("Remaining outstanding principal", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination principal balance snapshot"),
    "out_prncp_inv": ("Remaining principal funded by investors", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination investor principal balance"),
    "total_pymnt": ("Total payments received to date", "Post-Origination", "High (Target Leakage)", "Exclude", "Direct function of post-origination repayment performance"),
    "total_pymnt_inv": ("Total payments received by investors", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination investor payment total"),
    "total_rec_prncp": ("Principal received to date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination principal repayment cumulative sum"),
    "total_rec_int": ("Interest received to date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination interest repayment cumulative sum"),
    "total_rec_late_fee": ("Late fees received to date", "Post-Origination", "High (Target Leakage)", "Exclude", "Direct indicator of post-origination delinquency"),
    "recoveries": ("Post-chargeoff recoveries", "Post-Origination", "High (Target Leakage)", "Exclude", "Generated strictly post-default/charge-off"),
    "collection_recovery_fee": ("Post-chargeoff collection fee", "Post-Origination", "High (Target Leakage)", "Exclude", "Generated strictly post-default/charge-off"),
    "last_pymnt_d": ("Last payment date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination timestamp"),
    "last_pymnt_amnt": ("Last payment amount", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination payment amount"),
    "next_pymnt_d": ("Next scheduled payment date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination tracking timestamp"),
    "last_credit_pull_d": ("Last credit pull date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination bureau pull timestamp"),
    "last_fico_range_high": ("Last credit pull high FICO", "Post-Origination", "High (Target Leakage)", "Exclude", "Updated post-origination credit score"),
    "last_fico_range_low": ("Last credit pull low FICO", "Post-Origination", "High (Target Leakage)", "Exclude", "Updated post-origination credit score"),
    "collections_12_mths_ex_med": ("Collections in last 12 months", "Post-Origination", "High (Target Leakage)", "Exclude", "Updated credit bureau collection indicator"),
    "mths_since_last_major_derog": ("Months since last major derog rating", "Application/Bureau", "None/Low", "Include", "Recency of major derogatory credit rating at application"),
    "policy_code": ("Policy code indicator", "Origination/Metadata", "None/Low", "Exclude", "Constant metadata value (1.0)"),

    # Settlement Fields (Post-Default)
    "debt_settlement_flag": ("Debt settlement flag", "Post-Origination", "High (Target Leakage)", "Exclude", "Indicates post-default debt restructuring"),
    "debt_settlement_flag_date": ("Settlement flag date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-default settlement timestamp"),
    "settlement_status": ("Settlement program status", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-default settlement status"),
    "settlement_date": ("Settlement agreement date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-default settlement agreement date"),
    "settlement_amount": ("Settlement agreement amount", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-default settlement negotiated amount"),
    "settlement_percentage": ("Settlement waiver percentage", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-default settlement terms"),
    "settlement_term": ("Settlement payment terms", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-default settlement period"),

    # Hardship Program Fields (Post-Origination)
    "hardship_flag": ("Hardship plan flag", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination distress accommodation flag"),
    "hardship_type": ("Hardship accommodation type", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination distress program details"),
    "hardship_reason": ("Hardship reason", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination borrower hardship reason"),
    "hardship_status": ("Hardship status", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination hardship state"),
    "deferral_term": ("Hardship deferral months", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination loan term modification"),
    "hardship_amount": ("Hardship payment amount", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination modified payment amount"),
    "hardship_start_date": ("Hardship start date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination event date"),
    "hardship_end_date": ("Hardship end date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination event date"),
    "payment_plan_start_date": ("Payment plan start date", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination plan start date"),
    "hardship_length": ("Hardship duration months", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination duration"),
    "hardship_dpd": ("Days past due at hardship entry", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination delinquency state"),
    "hardship_loan_status": ("Loan status prior to hardship", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination status snapshot"),
    "orig_projected_additional_accrued_interest": ("Projected hardship interest", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination interest calculation"),
    "hardship_payoff_balance_amount": ("Payoff balance at hardship", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination balance snapshot"),
    "hardship_last_payment_amount": ("Last payment prior to hardship", "Post-Origination", "High (Target Leakage)", "Exclude", "Post-origination payment amount"),

    # Point-in-Time Application & Credit Bureau Features (Candidate Predictors)
    "loan_amnt": ("Requested loan amount", "Application", "None/Low", "Include", "Point-in-time loan request amount"),
    "funded_amnt": ("Funded loan amount", "Origination", "None/Low", "Include", "Amount committed at origination"),
    "funded_amnt_inv": ("Investor funded amount", "Origination", "None/Low", "Include", "Investor commitment amount at origination"),
    "term": ("Loan term (36 or 60 months)", "Origination", "None/Low", "Include", "Underwriting contract term"),
    "int_rate": ("Assigned interest rate", "Origination", "None/Low", "Include", "Risk-priced interest rate at origination"),
    "installment": ("Monthly installment payment", "Origination", "None/Low", "Include", "Required monthly payment calculated at origination"),
    "grade": ("LendingClub assigned grade", "Origination", "None/Low", "Include", "Underwriting risk tier at origination"),
    "sub_grade": ("LendingClub assigned sub-grade", "Origination", "None/Low", "Include", "Detailed risk tier at origination"),
    "emp_length": ("Employment length years", "Application", "None/Low", "Include", "Applicant-reported tenure at application"),
    "home_ownership": ("Home ownership status", "Application", "None/Low", "Include", "Applicant housing status at application"),
    "annual_inc": ("Self-reported annual income", "Application", "None/Low", "Include", "Applicant annual income at application"),
    "verification_status": ("Income verification status", "Application", "None/Low", "Include", "LendingClub income verification category"),
    "issue_d": ("Loan origination date", "Origination", "None/Low", "Include", "Timestamp used for observation window and chronological splitting"),
    "purpose": ("Stated loan purpose", "Application", "None/Low", "Include", "Stated reason for borrowing"),
    "addr_state": ("Borrower state code", "Application", "None/Low", "Include", "Borrower US state location"),
    "dti": ("Debt-to-income ratio", "Application", "None/Low", "Include", "Applicant DTI calculated at application"),
    "delinq_2yrs": ("Delinquencies in past 2 years", "Application/Bureau", "None/Low", "Include", "Bureau trade line history at application"),
    "earliest_cr_line": ("Earliest credit line date", "Application/Bureau", "None/Low", "Include", "Used to compute credit history age at origination"),
    "fico_range_low": ("Bureau FICO score lower bound", "Application/Bureau", "None/Low", "Include", "Underwriting FICO score at application"),
    "fico_range_high": ("Bureau FICO score upper bound", "Application/Bureau", "None/Low", "Include", "Underwriting FICO score at application"),
    "inq_last_6mths": ("Inquiries in last 6 months", "Application/Bureau", "None/Low", "Include", "Recent bureau credit inquiries"),
    "mths_since_last_delinq": ("Months since last delinquency", "Application/Bureau", "None/Low", "Include", "Historical delinquency recency at application"),
    "mths_since_last_record": ("Months since last public record", "Application/Bureau", "None/Low", "Include", "Public record recency at application"),
    "open_acc": ("Number of open credit lines", "Application/Bureau", "None/Low", "Include", "Active bureau accounts at application"),
    "pub_rec": ("Number of derogatory public records", "Application/Bureau", "None/Low", "Include", "Public record count at application"),
    "revol_bal": ("Total credit revolving balance", "Application/Bureau", "None/Low", "Include", "Revolving debt balance at application"),
    "revol_util": ("Revolving line utilization rate", "Application/Bureau", "None/Low", "Include", "Revolving line utilization at application"),
    "total_acc": ("Total credit lines", "Application/Bureau", "None/Low", "Include", "Total historical bureau accounts"),
    "initial_list_status": ("Initial listing status (W/F)", "Origination", "None/Low", "Include", "Origination loan allocation status"),
    "application_type": ("Individual or Joint application", "Application", "None/Low", "Include", "Single vs co-borrower application indicator"),
    "annual_inc_joint": ("Joint applicant annual income", "Application", "None/Low", "Include", "Co-borrower income at application"),
    "dti_joint": ("Joint debt-to-income ratio", "Application", "None/Low", "Include", "Co-borrower DTI at application"),
    "verification_status_joint": ("Joint income verification", "Application", "None/Low", "Include", "Co-borrower income verification status"),
    "acc_now_delinq": ("Accounts currently delinquent", "Application/Bureau", "None/Low", "Include", "Delinquent account count at application"),
    "tot_coll_amt": ("Total collection amounts ever", "Application/Bureau", "None/Low", "Include", "Historical collection balance at application"),
    "tot_cur_bal": ("Total current balance all accounts", "Application/Bureau", "None/Low", "Include", "Total bureau balance at application"),
    "open_acc_6m": ("Open trades in last 6 months", "Application/Bureau", "None/Low", "Include", "Recent trade line openings"),
    "open_act_il": ("Active installment trades", "Application/Bureau", "None/Low", "Include", "Active installment accounts at application"),
    "open_il_12m": ("Installment trades opened in 12m", "Application/Bureau", "None/Low", "Include", "Recent installment trade openings"),
    "open_il_24m": ("Installment trades opened in 24m", "Application/Bureau", "None/Low", "Include", "Recent installment trade openings"),
    "mths_since_rcnt_il": ("Months since recent installment", "Application/Bureau", "None/Low", "Include", "Installment account recency"),
    "total_bal_il": ("Total balance installment trades", "Application/Bureau", "None/Low", "Include", "Installment debt balance at application"),
    "il_util": ("Installment balance to high credit", "Application/Bureau", "None/Low", "Include", "Installment line utilization"),
    "open_rv_12m": ("Revolving trades opened in 12m", "Application/Bureau", "None/Low", "Include", "Recent revolving openings"),
    "open_rv_24m": ("Revolving trades opened in 24m", "Application/Bureau", "None/Low", "Include", "Recent revolving openings"),
    "max_bal_bc": ("Maximum balance on bankcard", "Application/Bureau", "None/Low", "Include", "Peak bankcard balance at application"),
    "all_util": ("Balance to credit limit all trades", "Application/Bureau", "None/Low", "Include", "Total credit utilization at application"),
    "total_rev_hi_lim": ("Total revolving high credit limit", "Application/Bureau", "None/Low", "Include", "Total revolving credit limit"),
    "inq_fi": ("Finance inquiries", "Application/Bureau", "None/Low", "Include", "Financial bureau inquiries count"),
    "total_cu_tl": ("Finance trade accounts", "Application/Bureau", "None/Low", "Include", "Credit union trade accounts count"),
    "inq_last_12m": ("Credit inquiries in last 12 months", "Application/Bureau", "None/Low", "Include", "Total inquiries in last 12 months"),
    "acc_open_past_24mths": ("Accounts opened in past 24m", "Application/Bureau", "None/Low", "Include", "Trade line velocity in past 2 years"),
    "avg_cur_bal": ("Average current balance", "Application/Bureau", "None/Low", "Include", "Mean account balance at application"),
    "bc_open_to_buy": ("Bankcard open to buy amount", "Application/Bureau", "None/Low", "Include", "Available bankcard credit limit"),
    "bc_util": ("Bankcard utilization ratio", "Application/Bureau", "None/Low", "Include", "Bankcard line utilization at application"),
    "chargeoff_within_12_mths": ("Charge-offs in last 12 months", "Application/Bureau", "None/Low", "Include", "Recent bureau charge-offs count"),
    "delinq_amnt": ("Delinquent amount", "Application/Bureau", "None/Low", "Include", "Past-due dollar amount at application"),
    "mo_sin_old_il_acct": ("Months since oldest installment", "Application/Bureau", "None/Low", "Include", "Oldest installment account age"),
    "mo_sin_old_rev_tl_op": ("Months since oldest revolving", "Application/Bureau", "None/Low", "Include", "Oldest revolving account age"),
    "mo_sin_rcnt_rev_tl_op": ("Months since recent revolving", "Application/Bureau", "None/Low", "Include", "Recent revolving account opening"),
    "mo_sin_rcnt_tl": ("Months since recent account open", "Application/Bureau", "None/Low", "Include", "Most recent account opening age"),
    "mort_acc": ("Number of mortgage accounts", "Application/Bureau", "None/Low", "Include", "Mortgage accounts count at application"),
    "mths_since_recent_bc": ("Months since recent bankcard", "Application/Bureau", "None/Low", "Include", "Bankcard account recency"),
    "mths_since_recent_bc_dlq": ("Months since recent bankcard delinq", "Application/Bureau", "None/Low", "Include", "Bankcard delinquency recency"),
    "mths_since_recent_inq": ("Months since recent inquiry", "Application/Bureau", "None/Low", "Include", "Recency of last bureau inquiry"),
    "mths_since_recent_revol_delinq": ("Months since recent revol delinq", "Application/Bureau", "None/Low", "Include", "Revolving delinquency recency"),
    "num_accts_ever_120_pd": ("Accounts ever 120+ days past due", "Application/Bureau", "None/Low", "Include", "Severe delinquency history count"),
    "num_actv_bc_tl": ("Active bankcard trades", "Application/Bureau", "None/Low", "Include", "Currently active bankcard accounts"),
    "num_actv_rev_tl": ("Active revolving trades", "Application/Bureau", "None/Low", "Include", "Currently active revolving accounts"),
    "num_bc_sats": ("Satisfactory bankcard trades", "Application/Bureau", "None/Low", "Include", "Clean bankcard trade count"),
    "num_bc_tl": ("Total bankcard trades", "Application/Bureau", "None/Low", "Include", "Total historical bankcard trades"),
    "num_il_tl": ("Total installment trades", "Application/Bureau", "None/Low", "Include", "Total historical installment trades"),
    "num_op_rev_tl": ("Open revolving trades", "Application/Bureau", "None/Low", "Include", "Active open revolving trades"),
    "num_rev_accts": ("Total revolving accounts", "Application/Bureau", "None/Low", "Include", "Total historical revolving accounts"),
    "num_rev_tl_bal_gt_0": ("Revolving trades with balance > 0", "Application/Bureau", "None/Low", "Include", "Carrying-balance revolving trades"),
    "num_sats": ("Satisfactory trades", "Application/Bureau", "None/Low", "Include", "Clean historical bureau trades count"),
    "num_tl_120dpd_2m": ("Accounts 120+ dpd in past 2 months", "Application/Bureau", "None/Low", "Include", "Recent severe delinquency count"),
    "num_tl_30dpd": ("Accounts 30+ dpd currently", "Application/Bureau", "None/Low", "Include", "Current 30-day delinquency count"),
    "num_tl_90g_dpd_24m": ("Trades 90+ dpd in past 24 months", "Application/Bureau", "None/Low", "Include", "24-month severe delinquency count"),
    "num_tl_op_past_12m": ("Trades opened in past 12 months", "Application/Bureau", "None/Low", "Include", "1-year trade opening velocity"),
    "pct_tl_nvr_dlq": ("Percent trade lines never delinquent", "Application/Bureau", "None/Low", "Include", "Historical clean trade ratio"),
    "percent_bc_gt_75": ("Bankcard trades > 75% limit", "Application/Bureau", "None/Low", "Include", "High-utilization bankcard ratio"),
    "pub_rec_bankruptcies": ("Public record bankruptcies", "Application/Bureau", "None/Low", "Include", "Historical bankruptcy filings count"),
    "tax_liens": ("Tax liens count", "Application/Bureau", "None/Low", "Include", "Historical tax lien count"),
    "tot_hi_cred_lim": ("Total high credit limit", "Application/Bureau", "None/Low", "Include", "Aggregate high credit limit"),
    "total_bal_ex_mort": ("Total balance excluding mortgage", "Application/Bureau", "None/Low", "Include", "Non-mortgage debt balance"),
    "total_bc_limit": ("Total bankcard credit limit", "Application/Bureau", "None/Low", "Include", "Aggregate bankcard limit"),
    "total_il_high_credit_limit": ("Total installment high credit limit", "Application/Bureau", "None/Low", "Include", "Aggregate installment limit"),
    "revol_bal_joint": ("Joint revolving debt balance", "Application/Bureau", "None/Low", "Include", "Co-borrower revolving debt"),
    "sec_app_fico_range_low": ("Joint applicant FICO low", "Application/Bureau", "None/Low", "Include", "Co-borrower FICO score"),
    "sec_app_fico_range_high": ("Joint applicant FICO high", "Application/Bureau", "None/Low", "Include", "Co-borrower FICO score"),
    "sec_app_earliest_cr_line": ("Joint applicant earliest credit line", "Application/Bureau", "None/Low", "Include", "Co-borrower credit history start date"),
    "sec_app_inq_last_6mths": ("Joint applicant inquiries 6m", "Application/Bureau", "None/Low", "Include", "Co-borrower recent inquiries"),
    "sec_app_mort_acc": ("Joint applicant mortgage accounts", "Application/Bureau", "None/Low", "Include", "Co-borrower mortgage accounts count"),
    "sec_app_open_acc": ("Joint applicant open accounts", "Application/Bureau", "None/Low", "Include", "Co-borrower open accounts count"),
    "sec_app_revol_util": ("Joint applicant revolving utilization", "Application/Bureau", "None/Low", "Include", "Co-borrower revolving utilization"),
    "sec_app_open_act_il": ("Joint applicant active installment", "Application/Bureau", "None/Low", "Include", "Co-borrower active installment trades"),
    "sec_app_num_rev_accts": ("Joint applicant revolving accounts", "Application/Bureau", "None/Low", "Include", "Co-borrower revolving accounts count"),
    "sec_app_chargeoff_within_12_mths": ("Joint applicant chargeoffs 12m", "Application/Bureau", "None/Low", "Include", "Co-borrower recent chargeoffs"),
    "sec_app_collections_12_mths_ex_med": ("Joint applicant collections 12m", "Application/Bureau", "None/Low", "Include", "Co-borrower recent collections"),
    "sec_app_mths_since_last_major_derog": ("Joint applicant months major derog", "Application/Bureau", "None/Low", "Include", "Co-borrower major derog recency"),
    "disbursement_method": ("Disbursement method (Cash/DirectPay)", "Origination", "None/Low", "Include", "Loan disbursement channel"),
}


def run_audit():
    print(f"Starting Phase 2.2 Audit on {LC_CSV_PATH} ...")
    if not os.path.exists(LC_CSV_PATH):
        raise FileNotFoundError(f"LendingClub CSV not found at {LC_CSV_PATH}")

    os.makedirs(REPORTS_DIR, exist_ok=True)

    # 1. Chunked scan for counts, statuses, and nulls
    chunk_size = 100000
    total_rows = 0
    status_counts = {}
    null_counts = {}
    columns_found = []

    for chunk_idx, chunk in enumerate(pd.read_csv(LC_CSV_PATH, chunksize=chunk_size, low_memory=False)):
        if chunk_idx == 0:
            columns_found = list(chunk.columns)
            for c in columns_found:
                null_counts[c] = 0

        total_rows += len(chunk)

        # Count loan_status
        if "loan_status" in chunk.columns:
            counts = chunk["loan_status"].value_counts(dropna=False).to_dict()
            for s, val in counts.items():
                s_str = str(s)
                status_counts[s_str] = status_counts.get(s_str, 0) + val

        # Count nulls per column
        for c in columns_found:
            null_counts[c] += chunk[c].isna().sum()

    print(f"Audit completed: {total_rows:,} rows, {len(columns_found)} columns.")

    # 2. Build Label Audit Table
    label_proposal_map = {
        "Fully Paid": ("Good / Non-Default", "Included", "Loan fully repaid principal and interest to maturity"),
        "Charged Off": ("Bad / Default", "Included", "Verified default written off by lender"),
        "Current": ("Ambiguous / Active", "Excluded", "Active ongoing loan; outcome not yet observed (unseasoned)"),
        "Late (31-120 days)": ("Ambiguous / Delinquent", "Excluded", "In-flight severe delinquency; default/cure not yet final"),
        "In Grace Period": ("Ambiguous / Delinquent", "Excluded", "1-15 days late; active unseasoned status"),
        "Late (16-30 days)": ("Ambiguous / Delinquent", "Excluded", "16-30 days late; active unseasoned status"),
        "Does not meet the credit policy. Status:Fully Paid": ("Good / Non-Default", "Included", "Legacy pre-2010 loan fully repaid under older underwriting criteria"),
        "Does not meet the credit policy. Status:Charged Off": ("Bad / Default", "Included", "Legacy pre-2010 loan charged off under older underwriting criteria"),
        "Default": ("Bad / Default", "Included", "Declared loan default"),
        "nan": ("Ambiguous / Missing", "Excluded", "Missing status string / corrupted row"),
    }

    label_rows = []
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_rows) * 100.0
        prop_class, inc_stat, rationale = label_proposal_map.get(
            status, ("Ambiguous / Unknown", "Excluded", "Uncategorized status")
        )
        label_rows.append({
            "loan_status_value": status,
            "count": count,
            "percentage": round(pct, 4),
            "proposed_classification": prop_class,
            "inclusion_status": inc_stat,
            "rationale": rationale,
        })

    df_labels = pd.DataFrame(label_rows)
    label_csv_path = os.path.join(REPORTS_DIR, "phase_2_2_lendingclub_label_audit.csv")
    df_labels.to_csv(label_csv_path, index=False)
    print(f"Saved label audit to {label_csv_path}")

    # 3. Build Feature Leakage Audit Table
    leakage_rows = []
    for col in columns_found:
        null_cnt = null_counts.get(col, 0)
        null_pct = round((null_cnt / total_rows) * 100.0, 2)

        meta = COLUMN_METADATA.get(col, (
            "Unclassified feature", "Unknown", "Unknown or requires verification", "Exclude", "Column not documented in initial dictionary"
        ))

        meaning, avail_time, leakage_risk, action, reason = meta

        leakage_rows.append({
            "column": col,
            "meaning": meaning,
            "availability_time": avail_time,
            "leakage_risk": leakage_risk,
            "recommended_action": action,
            "missing_pct": null_pct,
            "reason": reason,
        })

    df_leakage = pd.DataFrame(leakage_rows)
    leakage_csv_path = os.path.join(REPORTS_DIR, "phase_2_2_feature_leakage_audit.csv")
    df_leakage.to_csv(leakage_csv_path, index=False)
    print(f"Saved feature leakage audit to {leakage_csv_path}")

    return {
        "total_rows": total_rows,
        "total_columns": len(columns_found),
        "status_counts": status_counts,
        "label_csv": label_csv_path,
        "leakage_csv": leakage_csv_path,
    }


if __name__ == "__main__":
    run_audit()
