"""Deterministic synthetic development dataset (not observed borrower data)."""
from __future__ import annotations
import numpy as np
import pandas as pd

CATEGORIES=["SALARY","BUSINESS_INCOME","OTHER_INCOME","TRANSFER_IN","RENT","FOOD","SHOPPING","UTILITIES","TRANSPORT","EMI","HEALTH","EDUCATION","ENTERTAINMENT","TRANSFER_OUT","OTHER"]

def generate_synthetic_data(n_borrowers=800, seed=42):
    rng=np.random.default_rng(seed); start=pd.Timestamp("2024-01-01"); tx=[]; outcomes=[]
    profiles=["salary_stable","business_stable","volatile","high_expense","cash_gap","gig","healthy","unstable"]
    for i in range(n_borrowers):
        bid=f"SYN{i+1:05d}"; profile=profiles[i%len(profiles)]; base=float(rng.lognormal(np.log(52000),.35))
        if profile in ("volatile","unstable","gig"): income_cv=.75
        elif profile=="business_stable": income_cv=.32
        elif profile=="gig": income_cv=.9
        else: income_cv=.16
        bal=max(2000,float(base*rng.uniform(.2,1.5))); borrower_tx=[]
        for month in range(12):
            dt=start+pd.DateOffset(months=month)
            income=max(1000,float(base*rng.lognormal(-income_cv**2/2,income_cv)))
            if profile=="salary_stable": income=base*rng.normal(1,.035)
            if profile=="business_stable": income=base*rng.lognormal(-.32**2/2,.32)
            inc_cat="SALARY" if profile=="salary_stable" else ("BUSINESS_INCOME" if profile=="business_stable" else "OTHER_INCOME")
            events=[(rng.integers(1,6),"CREDIT",income,inc_cat,"Income source")]
            n_exp=int(rng.integers(12,24))
            rent=base*rng.uniform(.12,.27)
            for j in range(n_exp):
                day=int(rng.integers(1,27)); cat=rng.choice(["RENT","FOOD","SHOPPING","UTILITIES","TRANSPORT","EMI","HEALTH","EDUCATION","ENTERTAINMENT","TRANSFER_OUT","OTHER"],p=[.06,.23,.1,.12,.13,.08,.06,.04,.07,.07,.04])
                amount=rent if cat=="RENT" else (base*rng.uniform(.06,.14) if cat=="EMI" else base*rng.uniform(.002,.055))
                if profile=="high_expense": amount*=1.38
                if profile=="healthy": amount*=.72
                events.append((day,"DEBIT",amount,cat,f"Merchant-{int(rng.integers(1,45)):02d}"))
            events.sort(key=lambda x:x[0])
            for day,typ,amt,cat,cp in events:
                bal += amt if typ=="CREDIT" else -amt
                if profile=="cash_gap" and month%3==1: bal-=base*.35
                row={"borrower_id":bid,"transaction_id":f"{bid}-M{month+1:02d}-T{len(borrower_tx)+1:03d}","date":dt+pd.Timedelta(days=int(day)-1),"transaction_type":typ,"amount":round(float(amt),2),"category":cat,"counterparty":cp,"balance_after_transaction":round(max(0.,float(bal)),2)}
                borrower_tx.append(row)
        tx.extend(borrower_tx)
        f=pd.DataFrame(borrower_tx); incomes=f.loc[f.category.isin(["SALARY","BUSINESS_INCOME","OTHER_INCOME","PENSION","BENEFITS","RENTAL_INCOME","REMITTANCE_INCOME"]),"amount"].sum(); expenses=f.loc[f.transaction_type=="DEBIT","amount"].sum(); cv=float(f.loc[f.transaction_type=="CREDIT","amount"].std()/(f.loc[f.transaction_type=="CREDIT","amount"].mean()+1)); negative=max(0.,expenses-incomes)/max(incomes,1); emi=f.loc[f.category=="EMI","amount"].sum()/max(incomes,1)
        risk=-2.25+1.05*min(cv,2)+1.5*min(negative,2)+1.1*min(emi,1)+(.48 if profile in ("cash_gap","unstable") else 0)-(.3 if profile=="healthy" else 0)
        p=1/(1+np.exp(-risk)); loan_date=pd.Timestamp("2025-01-01")
        event_day=int(rng.integers(1,91)) if rng.random()<p else None
        outcomes.append({"borrower_id":bid,"loan_amount":round(float(rng.lognormal(np.log(90000),.45)),2),"loan_date":loan_date,"outcome_date":loan_date+pd.Timedelta(days=event_day) if event_day else pd.NaT,"default_30d":int(event_day is not None and event_day<=30),"default_60d":int(event_day is not None and event_day<=60),"default_90d":int(event_day is not None)})
    return pd.DataFrame(tx),pd.DataFrame(outcomes)
