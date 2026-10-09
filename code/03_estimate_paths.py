from pathlib import Path
import numpy as np,pandas as pd,json
R=Path(__file__).resolve().parents[1];O=R/'results';C=R/'cache'
e=pd.read_pickle(C/'episodes.pkl');f=pd.read_pickle(C/'followups.pkl')
r=f[f.y.eq(1)].copy();r['event_days']=(r.f_raw_issue-r.anchor).dt.days
q=e.merge(r[['episode_id','k','f_raw_ss','f_raw_serious','f_raw_n','f_raw_issue','event_days']],on='episode_id',how='left',validate='one_to_one').rename(columns={'k':'event_k','f_raw_ss':'rec_ss','f_raw_serious':'rec_serious','f_raw_n':'rec_n','f_raw_issue':'rec_issue'})
q['period']=np.where(q.begin.dt.year.le(2016),'2008-2016','2017-2024')
first=f[f.k.eq(1)].set_index('episode_id').y
q['first_y']=q.episode_id.map(first);q['first_clear']=q.first_y.eq(0)
q['first_per_mine']=False;q.loc[q.sort_values(['anchor','EVENT_NO','PART_SECTION']).drop_duplicates('MINE_ID').index,'first_per_mine']=True
q.to_pickle(C/'paths.pkl');q.to_csv(O/'episode_paths.csv.gz',index=False)
# Matrix of cluster-level numerator/denominator contributions. No independent-row resampling.
metrics=[];num=[];den=[]; minecodes, minelist=pd.factorize(q.MINE_ID,sort=True); G=len(minelist)
def add(name,select,numerator,scope='all',horizon=None):
 a=np.asarray(select,dtype=bool);b=np.asarray(numerator,dtype=bool)&a
 if a.sum()==0:return
 num.append(np.bincount(minecodes,weights=b.astype(float),minlength=G));den.append(np.bincount(minecodes,weights=a.astype(float),minlength=G))
 metrics.append(dict(metric=name,scope=scope,horizon=horizon,numerator=int(b.sum()),denominator=int(a.sum()),mines=int(q.loc[a,'MINE_ID'].nunique()),estimate=float(b.sum()/a.sum())))
allm=np.ones(len(q),bool)
scopes={'all':allm,'all_citations_closed_le1day':q.fast_all1,'one_episode_per_mine':q.first_per_mine}
scopes.update({'part'+p:q.prefix.eq(p) for p in sorted(q.prefix.unique())});scopes.update({p:q.period.eq(p) for p in sorted(q.period.unique())})
for scope,s in scopes.items():
 add('fast_closure_share',s,q.fast_all1,scope)
 add('first_inspection_recurrence',s&q.first_y.notna(),q.first_y.eq(1),scope,1)
 for K in [4,8]:
  event=q.event_k.le(K);clean=q.n_observed_E01.ge(K)&~event;unknown=~(event|clean)
  delayed=event&q.event_k.gt(1); ss=event&q.rec_ss.eq(True)
  add('observed_recurrence_fraction_full_cohort',s,event,scope,K)
  add('observed_K_clean_fraction_full_cohort',s,clean,scope,K)
  add('followup_unresolved_fraction_full_cohort',s,unknown,scope,K)
  add('delayed_share_among_recurrences',s&event,delayed,scope,K)
  add('SS_share_among_recurrences',s&event,ss,scope,K)
  add('SS_share_among_delayed_recurrences',s&delayed,ss,scope,K)
  add('delayed_share_among_SS_recurrences',s&ss,delayed,scope,K)
  add('initial_nonSS_share_among_SS_recurrences',s&ss,q.ss.eq(0),scope,K)
  add('observed_delayed_recurrence_after_first_clear',s&q.first_clear,delayed,scope,K)
  add('observed_delayed_SS_after_first_clear',s&q.first_clear,ss,scope,K)
  for base in [0,1]:
   add('rec_SS_given_index_SS'+str(base),s&event&q.ss.eq(base),ss,scope,K)
  for status in q.status.unique():
   add('unresolved_'+status,s,unknown&q.status.eq(status),scope,K)
# fixed observed mine-cluster resampling, all outcomes of each unit kept together
B=3000;rng=np.random.default_rng(20261007)
N=np.stack(num,axis=1);D=np.stack(den,axis=1);draws=[]
for a in range(0,B,100):
 w=rng.multinomial(G,np.full(G,1/G),size=min(100,B-a));nn=w@N;dd=w@D
 draws.append(np.divide(nn,dd,out=np.full_like(nn,np.nan),where=dd>0))
boot=np.concatenate(draws)
m=pd.DataFrame(metrics);m['lower']=np.nanquantile(boot,.025,axis=0);m['upper']=np.nanquantile(boot,.975,axis=0)
m.to_csv(O/'path_metrics_cluster_CI.csv',index=False)
# Observed inspection-specific counts; no population cumulative risk is estimated.
curve=[]
for scope,s in scopes.items():
 h=f[f.episode_id.isin(q.loc[s,'episode_id'])]
 S=1.;css=0.;cns=0.
 for k in range(1,9):
  x=h[h.k.eq(k)];n=len(x);d=int(x.y.sum());ss=int((x.y.eq(1)&x.f_raw_ss.eq(True)).sum())
  if not n:continue
  curve.append(dict(scope=scope,k=k,at_risk=n,events=d,SS_events=ss,hazard=d/n))
cv=pd.DataFrame(curve);cv.to_csv(O/'inspection_opportunity_curve.csv',index=False)
# Counts for complete-observation paths, not success assumed for excluded episodes.
trans=[]
for scope,s in scopes.items():
 for K in [4,8]:
  x=q[s&q.event_k.le(K)]
  for orig in [0,1]:
   for post in [False,True]:
    a=x[x.ss.eq(orig)&x.rec_ss.eq(post)]
    trans.append(dict(scope=scope,horizon=K,index_SS=orig,recurrence_SS=int(post),n=len(a),delayed_n=int(a.event_k.gt(1).sum())))
pd.DataFrame(trans).to_csv(O/'severity_transition_counts.csv',index=False)
# calendar descriptions refer to observed detections only; not hazard onset.
t=[]
for scope,s in scopes.items():
 for K in [4,8]:
  x=q[s&q.event_k.le(K)]
  for typ,z in [('all',x),('delayed',x[x.event_k.gt(1)])]:
   t.append(dict(scope=scope,horizon=K,type=typ,n=len(z),days_median=z.event_days.median(),days_q25=z.event_days.quantile(.25),days_q75=z.event_days.quantile(.75)))
pd.DataFrame(t).to_csv(O/'observed_detection_times.csv',index=False)
print(m[(m.scope=='all')&m.horizon.eq(4)&~m.metric.str.startswith('unresolved_')].to_string(index=False))
print('fast',m[(m.scope=='all_citations_closed_le1day')&m.horizon.eq(4)&~m.metric.str.startswith('unresolved_')].to_string(index=False))

print('end statuses',q.status.value_counts().to_dict())
