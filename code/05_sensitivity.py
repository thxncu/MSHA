from pathlib import Path
import numpy as np,pandas as pd,json
R=Path(__file__).resolve().parents[1];O=R/'results';C=R/'cache';q=pd.read_pickle(C/'paths_schedule.pkl')
# All sensitivity criteria and numerators are retained, including less supportive strata.
rows=[];contrib=[];ids,mi=pd.factorize(q.MINE_ID,sort=True);G=len(mi)
def add(scope,K,name,den,yes):
 den=np.asarray(den,bool);yes=np.asarray(yes,bool)&den
 if den.sum()==0:return
 rows.append(dict(scope=scope,horizon=K,metric=name,numerator=int(yes.sum()),denominator=int(den.sum()),estimate=yes.sum()/den.sum(),mines=q.loc[den,'MINE_ID'].nunique()))
 contrib.append((np.bincount(ids,weights=yes.astype(float),minlength=G),np.bincount(ids,weights=den.astype(float),minlength=G)))
for K in [4,8]:
 event=q.event_k.le(K);late=q.event_k.gt(1);ss=q.rec_ss.eq(True)
 scopes={'scheduled_at_least_K':q['complete_schedule_'+str(K)],'one_initial_citation':q.n.eq(1),'one_initial_and_one_recurring_citation':q.n.eq(1)&q.rec_n.eq(1),'same_inspection_office':None,'index_before_2022':q.begin.dt.year.le(2021)}
 f=pd.read_pickle(C/'followups.pkl');rec=f[f.y.eq(1)].set_index('episode_id');office=q.episode_id.map(rec.follow_office);scopes['same_inspection_office']=office.eq(q.office)
 for scope,s in scopes.items():
  add(scope,K,'delayed_share_among_recurrences',s&event,late)
  add(scope,K,'SS_share_among_recurrences',s&event,ss)
  add(scope,K,'delayed_share_among_SS_recurrences',s&event&ss,late)
# first-any-kind recurrence prior to fourth/eighth eligible inspection end; sensitivity, not primary event definition
A=pd.read_csv(O/'first_any_inspection_detection.csv.gz',dtype={'MINE_ID':str}).set_index('episode_id').reindex(q.episode_id)
for K in [4,8]:
 sel=q['complete_schedule_'+str(K)].to_numpy();issue=pd.to_datetime(A.first_any_issue).to_numpy();end=pd.to_datetime(A['schedule_'+str(K)+'_end']).to_numpy()
 event=(A.first_any_status.eq('new_linkable').to_numpy()&(issue<=end));late=A.clean_regular_before.ge(1).to_numpy();ss=A.first_any_SS.eq(True).to_numpy()
 add('any_inspection_with_complete_schedule',K,'delayed_share_among_recurrences',sel&event,late)
 add('any_inspection_with_complete_schedule',K,'SS_share_among_recurrences',sel&event,ss)
 add('any_inspection_with_complete_schedule',K,'observed_recurrence_fraction',sel,event)
N=np.stack([x[0] for x in contrib],axis=1);D=np.stack([x[1] for x in contrib],axis=1)
rng=np.random.default_rng(20261008);boot=[]
for a in range(0,3000,100):
 w=rng.multinomial(G,np.full(G,1/G),size=100);nr=w@N;dr=w@D;boot.append(np.divide(nr,dr,out=np.full_like(nr,np.nan),where=dr>0))
b=np.concatenate(boot);out=pd.DataFrame(rows);out['lower']=np.nanquantile(b,.025,axis=0);out['upper']=np.nanquantile(b,.975,axis=0);out.to_csv(O/'path_sensitivities_cluster_CI.csv',index=False)
print(out[out.horizon.eq(4)].to_string(index=False))
# Joint grading and observation history gate audit: information available after first follow-up.
# Fractions here are among OBSERVED first S&S recurrences <=K, not policy treatment-effect estimates.
metrics=[]
for K in [4,8]:
 event=q.event_k.le(K)&q.rec_ss.eq(True);ii=q.ss.eq(1);jj=q.event_k.eq(1);fast=q.fast_all1
 for rule,flag in [('initial_SS_only',ii),('first_followup_only',jj),('requires_initial_SS_and_first_followup',ii&jj),('excludes_fast_closed',~fast)]:
  n=int((event&flag).sum());metrics.append(dict(horizon=K,rule=rule,observed_SS=int(event.sum()),count_inside=n,count_outside=int(event.sum())-n,share_inside=n/event.sum()))
pd.DataFrame(metrics).to_csv(O/'descriptive_endpoint_coverage.csv',index=False)
# Paired transitions do not support a general escalation claim.
t=[]
for K in [4,8]:
 d=q[q.event_k.le(K)].copy();delta=d.rec_ss.astype(int)-d.ss
 a=pd.DataFrame({'mine':d.MINE_ID,'delta':delta,'n':1}).groupby('mine').sum();rng=np.random.default_rng(20261009);arr=[]
 for j in range(3000):
  v=rng.integers(0,len(a),size=len(a));arr.append(a.delta.to_numpy()[v].sum()/a.n.to_numpy()[v].sum())
 t.append(dict(horizon=K,n=len(d),upward=int(delta.eq(1).sum()),downward=int(delta.eq(-1).sum()),net_SS_change=delta.mean(),lower=np.quantile(arr,.025),upper=np.quantile(arr,.975)))
pd.DataFrame(t).to_csv(O/'paired_severity_change.csv',index=False)
print('paired change',pd.DataFrame(t).to_string(index=False))
