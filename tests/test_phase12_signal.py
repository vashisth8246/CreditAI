import numpy as np
import pandas as pd
from src.models.signal_validation import make_nested_splits,exclude_historical_test,bootstrap_feature_associations
from src.models.train import _select_f1_threshold

def test_old_phase11_test_borrowers_are_quarantined():
    f=pd.DataFrame({"borrower_id":["a","b","c","d"]})
    o=pd.DataFrame({"borrower_id":["a","b","c","d"],"default_90d":[0,1,0,1]})
    split=pd.DataFrame({"borrower_id":["a","b","c","d"],"split":["train","validation","test","train"]})
    dev,labels,held=exclude_historical_test(f,o,split)
    assert held=={"c"}
    assert set(dev.borrower_id)==set(labels.borrower_id)=={"a","b","d"}

def test_repeated_outer_folds_are_stratified_disjoint_and_cover_each_row_once():
    y=np.array([0]*80+[1]*20); folds=make_nested_splits(y,n_splits=5,seed=17)
    seen=[]
    for train,test in folds:
        assert not (set(train)&set(test))
        assert abs(y[test].mean()-.2)<.06
        seen.extend(test.tolist())
    assert sorted(seen)==list(range(len(y)))

def test_threshold_depends_only_on_passed_validation_scores_and_associations_have_ci():
    val_y=np.array([0,0,0,1,1,1]); val_pd=np.array([.1,.2,.3,.4,.5,.6])
    selected=_select_f1_threshold(val_y,val_pd)
    assert 0<=selected<=1
    # A separate, hypothetical holdout is not an argument to the threshold selector.
    assert selected==_select_f1_threshold(val_y,val_pd)
    x=pd.DataFrame({"signal":[0,0,0,1,1,1],"constant":[2]*6})
    result=bootstrap_feature_associations(x,val_y,n_boot=80,seed=2)
    signal=result.set_index("feature").loc["signal"]
    assert signal.point_biserial_r>0.99
    assert signal.bootstrap_95ci_low<=signal.bootstrap_95ci_high
