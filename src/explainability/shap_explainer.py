"""SHAP explanations sourced from the fitted tree model."""
import numpy as np
import pandas as pd

def explain_tree_model(model, X, feature_names, output_dir, sample_size=200):
    import shap
    import matplotlib.pyplot as plt
    sample=X.iloc[:sample_size]
    explainer=shap.TreeExplainer(model)
    values=explainer.shap_values(sample)
    if isinstance(values,list): values=values[-1]
    values=np.asarray(values)
    if values.ndim==3: values=values[:,:,1]
    imp=pd.DataFrame({"feature":feature_names,"mean_abs_shap":np.abs(values).mean(axis=0)}).sort_values("mean_abs_shap",ascending=False)
    output_dir.mkdir(parents=True,exist_ok=True); imp.to_csv(output_dir/"shap_global_importance.csv",index=False)
    shap.summary_plot(values,sample,show=False,max_display=20); plt.tight_layout(); plt.savefig(output_dir/"shap_summary.png",dpi=140); plt.close()
    local=pd.DataFrame({"feature":feature_names,"value":sample.iloc[0].to_numpy(),"shap_value":values[0]})
    local=local.sort_values("shap_value",key=abs,ascending=False); local.to_csv(output_dir/"shap_local_explanation.csv",index=False)
    return local
