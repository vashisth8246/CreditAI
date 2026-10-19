import pandas as pd

df = pd.read_csv("reports/phase_2_2_feature_leakage_audit.csv")
included = df[df["recommended_action"] == "Include"]
excluded = df[df["recommended_action"] == "Exclude"]
target = df[df["recommended_action"] == "Target Label"]

print(f"Total Columns Audited: {len(df)}")
print(f"Included Candidate Predictors: {len(included)}")
print(f"Excluded Columns: {len(excluded)}")
print(f"Target Label: {len(target)}")

print("\n--- High Missingness (>50%) Among Included Predictors ---")
high_missing = included[included["missing_pct"] > 50.0]
for idx, row in high_missing.iterrows():
    print(f"  {row['column']}: {row['missing_pct']}% missing ({row['meaning']})")

print("\n--- Low Missingness (<10%) Selected Features Sample ---")
low_missing = included[included["missing_pct"] <= 10.0]
print(f"Count of low-missingness features: {len(low_missing)}")
print("Low missingness features:", low_missing["column"].tolist())
