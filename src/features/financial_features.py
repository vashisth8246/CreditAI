"""Leakage-aware borrower features from transaction history.

Income uses an explicit category allow-list; generic transfers are never
assumed to be income. Monthly statistics include every calendar month in the
requested observation window, including months with no records.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.data.preprocessing import prepare_transactions

INCOME_CATEGORIES={"SALARY","BUSINESS_INCOME","OTHER_INCOME","PENSION","BENEFITS","RENTAL_INCOME","REMITTANCE_INCOME"}
ESSENTIAL={"RENT","FOOD","UTILITIES","TRANSPORT","EMI","HEALTH","EDUCATION"}
DISCRETIONARY={"SHOPPING","ENTERTAINMENT"}
FEATURE_NAMES=["total_income","avg_monthly_income","income_std","income_cv","income_months","income_stability_index","income_growth","total_expense","avg_monthly_expense","expense_std","expense_ratio","essential_expense_ratio","discretionary_expense_ratio","total_cashflow","avg_monthly_cashflow","cashflow_std","cashflow_volatility","negative_cashflow_months","cashflow_surplus_ratio","mean_observed_transaction_balance","minimum_observed_transaction_balance","maximum_observed_transaction_balance","observed_transaction_balance_volatility","low_balance_transaction_dates","transaction_count","credit_transaction_count","debit_transaction_count","avg_transaction_amount","median_transaction_amount","transaction_frequency","unique_counterparties","counterparty_diversity","top_counterparty_share","emi_count","emi_amount","emi_to_income_ratio","emi_share_of_expenses","spending_consistency","financial_buffer_ratio","income_expense_gap"]

def engineer_financial_features(transactions:pd.DataFrame,as_of_date=None,observation_start=None)->pd.DataFrame:
    """Aggregate borrower behavior strictly before ``as_of_date``.

    The default window is from the earliest observed month through the month
    before cutoff. Pass observation_start to force a common full window.
    """
    df=prepare_transactions(transactions,as_of_date)
    if df.empty: raise ValueError("No transactions remain before the prediction cutoff")
    df["month"]=df.date.dt.to_period("M")
    df["amount"]=pd.to_numeric(df.amount)
    df["balance_after_transaction"]=pd.to_numeric(df.balance_after_transaction)
    df["income"]=np.where((df.transaction_type=="CREDIT") & df.category.isin(INCOME_CATEGORIES),df.amount,0.0)
    df["expense"]=np.where(df.transaction_type=="DEBIT",df.amount,0.0)
    df["net"]=np.where(df.transaction_type=="CREDIT",df.amount,-df.amount)
    window_start=pd.Period(pd.Timestamp(observation_start).to_period("M")) if observation_start is not None else df.month.min()
    cutoff=pd.Timestamp(as_of_date) if as_of_date is not None else df.date.max()+pd.Timedelta(days=1)
    window_end=(cutoff-pd.Timedelta(nanoseconds=1)).to_period("M")
    if window_start>window_end: raise ValueError("Observation start must precede prediction cutoff")
    calendar=pd.period_range(window_start,window_end,freq="M")
    rows=[]
    for borrower,g in df.groupby("borrower_id",sort=True):
        monthly=g.groupby("month").agg(income=("income","sum"),expense=("expense","sum"),net=("net","sum")).reindex(calendar,fill_value=0.0)
        inc,exp,net=monthly.income,monthly.expense,monthly.net
        mean_inc=float(inc.mean()); mean_exp=float(exp.mean()); sd_inc=float(inc.std(ddof=0)); sd_exp=float(exp.std(ddof=0)); mean_net=float(net.mean()); sd_net=float(net.std(ddof=0))
        credits=g[g.transaction_type=="CREDIT"]; debits=g[g.transaction_type=="DEBIT"]
        cp_counts=g.counterparty.value_counts(normalize=True)
        income_total=float(inc.sum()); expense_total=float(exp.sum())
        emi=g[(g.category=="EMI") & (g.transaction_type=="DEBIT")]
        essential=float(g[g.category.isin(ESSENTIAL)&(g.transaction_type=="DEBIT")].amount.sum())
        discretionary=float(g[g.category.isin(DISCRETIONARY)&(g.transaction_type=="DEBIT")].amount.sum())
        days=max(1,(g.date.max().normalize()-g.date.min().normalize()).days+1)
        balances=g.balance_after_transaction
        values={"total_income":income_total,"avg_monthly_income":mean_inc,"income_std":sd_inc,"income_cv":sd_inc/max(mean_inc,1.0),"income_months":int((inc>0).sum()),"income_stability_index":(1/(1+sd_inc/mean_inc) if mean_inc>0 else 0.0),"income_growth":float(np.polyfit(np.arange(len(inc)),inc,1)[0]/max(mean_inc,1.0)) if len(inc)>1 else 0.0,
        "total_expense":expense_total,"avg_monthly_expense":mean_exp,"expense_std":sd_exp,"expense_ratio":expense_total/max(income_total,1.0),"essential_expense_ratio":essential/max(income_total,1.0),"discretionary_expense_ratio":discretionary/max(income_total,1.0),
        "total_cashflow":float(net.sum()),"avg_monthly_cashflow":mean_net,"cashflow_std":sd_net,"cashflow_volatility":sd_net/max(abs(mean_inc),1.0),"negative_cashflow_months":int((net<0).sum()),"cashflow_surplus_ratio":float(net.clip(lower=0).sum()/max(income_total,1.0)),
        "mean_observed_transaction_balance":float(balances.mean()),"minimum_observed_transaction_balance":float(balances.min()),"maximum_observed_transaction_balance":float(balances.max()),"observed_transaction_balance_volatility":float(balances.std(ddof=0)),"low_balance_transaction_dates":int(g.loc[balances<=balances.quantile(.1),"date"].dt.normalize().nunique()),
        "transaction_count":len(g),"credit_transaction_count":len(credits),"debit_transaction_count":len(debits),"avg_transaction_amount":float(g.amount.mean()),"median_transaction_amount":float(g.amount.median()),"transaction_frequency":len(g)/days,
        "unique_counterparties":int(g.counterparty.nunique()),"counterparty_diversity":int(g.counterparty.nunique())/max(len(g),1),"top_counterparty_share":float(cp_counts.iloc[0]) if len(cp_counts) else 0.0,
        "emi_count":len(emi),"emi_amount":float(emi.amount.sum()),"emi_to_income_ratio":float(emi.amount.sum()/max(income_total,1.0)),"emi_share_of_expenses":float(emi.amount.sum()/max(expense_total,1.0)),
        "spending_consistency":1/(1+sd_exp/max(mean_exp,1.0)),"financial_buffer_ratio":float(balances.mean()/max(mean_exp,1.0)),"income_expense_gap":mean_inc-mean_exp}
        rows.append({"borrower_id":borrower,**values})
    out=pd.DataFrame(rows).replace([np.inf,-np.inf],np.nan)
    out[FEATURE_NAMES]=out[FEATURE_NAMES].fillna(0.0)
    return out

def feature_matrix(features:pd.DataFrame)->pd.DataFrame:
    """Select model fields and reject target/outcome or post-loan columns."""
    forbidden={"default_30d","default_60d","default_90d","loan_amount","loan_date","outcome_date"}
    leaked=forbidden.intersection(features.columns)
    if leaked: raise ValueError(f"Outcome/post-loan columns cannot enter features: {sorted(leaked)}")
    return features.drop(columns=["borrower_id"],errors="ignore").loc[:,FEATURE_NAMES].copy()
