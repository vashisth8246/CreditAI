import pandas as pd
import numpy as np

LC_CSV = r"f:\NUV ACD\All SEM\7th Sem\ML&DS\New folder (3)\CreditAI\Data\archive\accepted_2007_to_2018Q4.csv"

# Good: Fully Paid, Does not meet credit policy... Fully Paid
# Bad: Charged Off, Default, Does not meet credit policy... Charged Off
GOOD_STATUSES = {"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"}
BAD_STATUSES = {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}

def check_splits():
    print("Streaming LendingClub CSV for issue year breakdown...")
    chunksize = 100000
    records = []

    for chunk in pd.read_csv(LC_CSV, chunksize=chunksize, usecols=["issue_d", "loan_status", "term"], low_memory=False):
        # Filter to closed mature loans
        closed_chunk = chunk[chunk["loan_status"].isin(GOOD_STATUSES | BAD_STATUSES)].copy()
        if len(closed_chunk) == 0:
            continue
        closed_chunk["target"] = closed_chunk["loan_status"].isin(BAD_STATUSES).astype(int)
        
        # Parse year from issue_d (format e.g. "Dec-2015" or "Jan-2018")
        closed_chunk["issue_year"] = closed_chunk["issue_d"].str.extract(r"(\d{4})")[0].astype(float)
        records.append(closed_chunk[["issue_year", "term", "target"]])

    df_closed = pd.concat(records, ignore_index=True)
    print(f"Total Closed Loans: {len(df_closed):,}")
    
    summary = df_closed.groupby("issue_year").agg(
        total_loans=("target", "count"),
        bad_loans=("target", "sum"),
        default_rate=("target", "mean")
    ).reset_index()

    summary["good_loans"] = summary["total_loans"] - summary["bad_loans"]
    summary["default_rate_pct"] = (summary["default_rate"] * 100).round(2)
    
    print("\n--- Issue Year Breakdown (Closed Loans) ---")
    print(summary.to_string(index=False))

    # Test Chronological Split Proposals:
    # Split 1: Train 2007-2013, Val 2014-2015, Test 2016-2018 (closed mature loans)
    train_mask = (df_closed["issue_year"] >= 2007) & (df_closed["issue_year"] <= 2013)
    val_mask = (df_closed["issue_year"] >= 2014) & (df_closed["issue_year"] <= 2015)
    test_mask = (df_closed["issue_year"] >= 2016) & (df_closed["issue_year"] <= 2018)

    print("\n--- Proposed Chronological Splits ---")
    for name, mask in [("Train (2007-2013)", train_mask), ("Val (2014-2015)", val_mask), ("Test (2016-2018)", test_mask)]:
        sub = df_closed[mask]
        tot = len(sub)
        bad = sub["target"].sum()
        good = tot - bad
        rate = (bad / tot * 100) if tot > 0 else 0
        print(f"  {name}: {tot:,} loans | Good: {good:,} | Bad: {bad:,} | Default Rate: {rate:.2f}%")

if __name__ == "__main__":
    check_splits()
