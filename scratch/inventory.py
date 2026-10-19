"""Verify exact row/column counts of all local datasets for Phase 3 inventory."""
import os
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data")


def try_read_csv(path):
    try:
        df = pd.read_csv(path, low_memory=False, nrows=0)
        return len(df.columns), None
    except Exception as e:
        return None, str(e)[:80]


def try_count_csv(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            n = sum(1 for _ in f)
        return n, None
    except Exception as e:
        return None, str(e)[:80]


def try_read_excel(path):
    for engine in ["openpyxl", "xlrd"]:
        try:
            xls = pd.ExcelFile(path, engine=engine)
            sheet_info = []
            for s in xls.sheet_names:
                df = xls.parse(s, nrows=5)
                sheet_info.append((s, len(df.columns)))
            return sheet_info, None
        except Exception:
            continue
    return None, "all engines failed"


files = []

# archive
csv_path = os.path.join(ROOT, "archive", "accepted_2007_to_2018Q4.csv")
ncols, err = try_read_csv(csv_path)
nrows, _ = try_count_csv(csv_path)
files.append(("archive/accepted_2007_to_2018Q4.csv", nrows, ncols, "csv", "rows incl header"))

# UCI Taiwan
taiwan = os.path.join(ROOT, "credit_default", "default of credit card clients.xls")
sheets, err = try_read_excel(taiwan)
if sheets:
    for sn, nc in sheets:
        files.append((f"credit_default/default of credit card clients.xls [{sn}]", "full", nc, "xls", "all 30000 rows per UCI doc"))
    # actual row count
    try:
        df = pd.read_excel(taiwan, engine="xlrd")
        files.append((f"credit_default/default of credit card clients.xls [actual rows]", len(df), len(df.columns), "xls", "verified"))
    except Exception as e:
        files.append((f"credit_default/default of credit card clients.xls [actual rows]", None, None, "xls", f"err: {str(e)[:60]}"))

# German credit
german = os.path.join(ROOT, "credit_default", "Dataset #3 — German Credit", "statlog+german+credit+data", "german.data")
try:
    df = pd.read_csv(german, sep=r"\s+", header=None)
    files.append(("Dataset #3 .../german.data", len(df), len(df.columns), "whitespace", "no header"))
except Exception as e:
    files.append(("Dataset #3 .../german.data", None, None, "whitespace", f"err:{str(e)[:60]}"))

german_n = os.path.join(ROOT, "credit_default", "Dataset #3 — German Credit", "statlog+german+credit+data", "german.data-numeric")
try:
    df = pd.read_csv(german_n, sep=r"\s+", header=None)
    files.append(("Dataset #3 .../german.data-numeric", len(df), len(df.columns), "whitespace", "no header"))
except Exception as e:
    files.append(("Dataset #3 .../german.data-numeric", None, None, "whitespace", f"err:{str(e)[:60]}"))

# UCI Credit Approval
crx = os.path.join(ROOT, "credit_default", "Dataset #5 — UCI Credit Approval", "credit+approval", "crx.data")
try:
    df = pd.read_csv(crx, header=None)
    files.append(("Dataset #5 .../crx.data", len(df), len(df.columns), "csv", "no header"))
except Exception as e:
    files.append(("Dataset #5 .../crx.data", None, None, "csv", f"err:{str(e)[:60]}"))

# CreditMitra
cm = os.path.join(ROOT, "transactions", "CreditMitra_transactions.csv")
try:
    df = pd.read_csv(cm)
    files.append(("transactions/CreditMitra_transactions.csv", len(df), len(df.columns), "csv", ",".join(df.columns.tolist())))
except Exception as e:
    files.append(("transactions/CreditMitra_transactions.csv", None, None, "csv", f"err:{str(e)[:60]}"))

# synthetic
syn_out = os.path.join(ROOT, "synthetic", "outcomes.csv")
try:
    df = pd.read_csv(syn_out)
    files.append(("synthetic/outcomes.csv", len(df), len(df.columns), "csv", ",".join(df.columns.tolist())))
except Exception as e:
    files.append(("synthetic/outcomes.csv", None, None, "csv", f"err:{str(e)[:60]}"))

syn_tx = os.path.join(ROOT, "synthetic", "transactions.csv")
try:
    df = pd.read_csv(syn_tx, nrows=0)
    nrows, _ = try_count_csv(syn_tx)
    files.append(("synthetic/transactions.csv", nrows, len(df.columns), "csv", ",".join(df.columns.tolist())))
except Exception as e:
    files.append(("synthetic/transactions.csv", None, None, "csv", f"err:{str(e)[:60]}"))

proc = os.path.join(ROOT, "processed", "borrower_features.csv")
try:
    df = pd.read_csv(proc)
    files.append(("processed/borrower_features.csv", len(df), len(df.columns), "csv", ",".join(df.columns.tolist())))
except Exception as e:
    files.append(("processed/borrower_features.csv", None, None, "csv", f"err:{str(e)[:60]}"))

# synthetic_phase1_1
sp1_out = os.path.join(ROOT, "synthetic_phase1_1", "outcomes.csv")
try:
    df = pd.read_csv(sp1_out)
    files.append(("synthetic_phase1_1/outcomes.csv", len(df), len(df.columns), "csv", ",".join(df.columns.tolist())))
except Exception as e:
    files.append(("synthetic_phase1_1/outcomes.csv", None, None, "csv", f"err:{str(e)[:60]}"))

sp1_tx = os.path.join(ROOT, "synthetic_phase1_1", "transactions.csv")
try:
    df = pd.read_csv(sp1_tx, nrows=0)
    nrows, _ = try_count_csv(sp1_tx)
    files.append(("synthetic_phase1_1/transactions.csv", nrows, len(df.columns), "csv", ",".join(df.columns.tolist())))
except Exception as e:
    files.append(("synthetic_phase1_1/transactions.csv", None, None, "csv", f"err:{str(e)[:60]}"))

sp1_bf = os.path.join(ROOT, "synthetic_phase1_1", "borrower_features.csv")
try:
    df = pd.read_csv(sp1_bf)
    files.append(("synthetic_phase1_1/borrower_features.csv", len(df), len(df.columns), "csv", ",".join(df.columns.tolist())))
except Exception as e:
    files.append(("synthetic_phase1_1/borrower_features.csv", None, None, "csv", f"err:{str(e)[:60]}"))

# NPCI UPI - count files
npci_root = os.path.join(ROOT, "india_upi", "NPCI")
npci_files = []
for fy in sorted(os.listdir(npci_root)):
    fy_path = os.path.join(npci_root, fy)
    if os.path.isdir(fy_path):
        for f in os.listdir(fy_path):
            if f.endswith(".xlsx"):
                npci_files.append((fy, os.path.join(fy_path, f)))
print(f"NPCI files found: {len(npci_files)}")
total_npci_rows = 0
for fy, fp in npci_files:
    sheets, err = try_read_excel(fp)
    if sheets:
        for sn, nc in sheets:
            try:
                df = pd.read_excel(fp, sheet_name=sn, engine="openpyxl")
                total_npci_rows += len(df)
                if fy == "2026-27":
                    files.append((f"india_upi/NPCI/{fy}/{f} [{sn}]", len(df), len(df.columns), "xlsx", f"cols:{nc}"))
            except Exception:
                pass
files.append((f"india_upi/NPCI (all {len(npci_files)} files)", total_npci_rows, 4, "xlsx", "aggregate monthly, 4 cols each"))

# RBI DBIE
rbi_root = os.path.join(ROOT, "india_banking", "RBI DBIE")
for dirpath, dirnames, filenames in os.walk(rbi_root):
    for f in filenames:
        if f.endswith(".xlsx"):
            fp = os.path.join(dirpath, f)
            rel = os.path.relpath(fp, ROOT)
            sheets, err = try_read_excel(fp)
            if sheets:
                for sn, nc in sheets:
                    try:
                        df = pd.read_excel(fp, sheet_name=sn, engine="openpyxl")
                        files.append((f"{rel} [{sn}]", len(df), len(df.columns), "xlsx", f"aggregate"))
                    except Exception as e:
                        files.append((f"{rel} [{sn}]", None, None, "xlsx", f"err:{str(e)[:50]}"))
            else:
                files.append((rel, None, None, "xlsx", f"unreadable: {err}"))

print()
print(f"{'FILE':<70} {'ROWS':>10} {'COLS':>6} {'FMT':<12} NOTE")
print("-" * 130)
for name, rows, cols, fmt, note in files:
    print(f"{name[:68]:<70} {str(rows):>10} {str(cols):>6} {fmt:<12} {note}")
