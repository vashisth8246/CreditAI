"""Independent row count audit for LendingClub CSV to resolve Phase 2.3.1 count discrepancy."""

import os
import pandas as pd

LC_CSV_PATH = os.path.join("Data", "archive", "accepted_2007_to_2018Q4.csv")

def audit_row_counts():
    """Independently count total rows and loan_status frequencies."""
    print(f"Loading {LC_CSV_PATH} for independent row count audit...")
    
    if not os.path.exists(LC_CSV_PATH):
        raise FileNotFoundError(f"LendingClub CSV not found at {LC_CSV_PATH}")
    
    # Method 1: Count total rows using chunked read
    print("\n=== Method 1: Chunked row count ===")
    total_rows = 0
    chunksize = 100000
    for chunk in pd.read_csv(LC_CSV_PATH, chunksize=chunksize, usecols=["loan_status"], low_memory=False):
        total_rows += len(chunk)
    print(f"Total rows (chunked count): {total_rows:,}")
    
    # Method 2: Count loan_status frequencies
    print("\n=== Method 2: Loan status frequency count ===")
    status_counts = {}
    total_from_status = 0
    for chunk in pd.read_csv(LC_CSV_PATH, chunksize=chunksize, usecols=["loan_status"], low_memory=False):
        for status in chunk["loan_status"]:
            if pd.isna(status):
                status_str = "(missing)"
            else:
                status_str = str(status)
            status_counts[status_str] = status_counts.get(status_str, 0) + 1
            total_from_status += 1
    
    print(f"Total rows (sum of status counts): {total_from_status:,}")
    print("\nStatus frequencies:")
    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count:,}")
    
    # Method 3: Verify with value_counts on full load (if memory allows)
    print("\n=== Method 3: Full load value_counts (if feasible) ===")
    try:
        df_full = pd.read_csv(LC_CSV_PATH, usecols=["loan_status"], low_memory=False)
        print(f"Total rows (full load): {len(df_full):,}")
        vc = df_full["loan_status"].value_counts(dropna=False)
        print("\nValue counts:")
        for status, count in vc.items():
            status_str = "(missing)" if pd.isna(status) else str(status)
            print(f"  {status_str}: {count:,}")
    except MemoryError:
        print("Full load failed due to memory constraints (expected for large file)")
    
    # Reconciliation
    print("\n=== Reconciliation ===")
    print(f"Chunked total: {total_rows:,}")
    print(f"Status sum total: {total_from_status:,}")
    print(f"Difference: {total_rows - total_from_status:,}")
    
    if total_rows == total_from_status:
        print("✓ Counts match")
    else:
        print(f"✗ Discrepancy of {abs(total_rows - total_from_status):,} rows")
    
    # Compute closed cohort and excluded cohort
    good_statuses = {"Fully Paid", "Does not meet the credit policy. Status:Fully Paid"}
    bad_statuses = {"Charged Off", "Default", "Does not meet the credit policy. Status:Charged Off"}
    
    good_count = sum(status_counts.get(s, 0) for s in good_statuses)
    bad_count = sum(status_counts.get(s, 0) for s in bad_statuses)
    closed_cohort = good_count + bad_count
    excluded_cohort = total_from_status - closed_cohort
    
    print(f"\n=== Cohort breakdown ===")
    print(f"Good (Fully Paid + policy Fully Paid): {good_count:,}")
    print(f"Bad (Charged Off + Default + policy Charged Off): {bad_count:,}")
    print(f"Closed cohort: {closed_cohort:,}")
    print(f"Excluded cohort: {total_from_status - closed_cohort:,}")
    print(f"Total: {total_from_status:,}")
    
    return {
        "total_rows_chunked": total_rows,
        "total_from_status": total_from_status,
        "status_counts": status_counts,
        "good_count": good_count,
        "bad_count": bad_count,
        "closed_cohort": closed_cohort,
        "excluded_cohort": excluded_cohort
    }

if __name__ == "__main__":
    audit_row_counts()
