from pathlib import Path
import zipfile,csv,time,json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'results';C=R/'cache';C.mkdir(exist_ok=True)
SRC=R/'inputs/source/raw'; T=time.time()
DTYPES={c:str for c in ['MINE_ID','OPERATOR_ID','PART_SECTION','EVENT_NO','EVENT_NO_follow','CONTROLLER_ID','office','prefix']}
e=pd.read_csv(R/'inputs/cohort/first_episodes.csv.gz',dtype=DTYPES,low_memory=False)
f=pd.read_csv(R/'inputs/cohort/survival_panel.csv.gz',dtype=DTYPES,low_memory=False)
for d in (e,f):
 for c in ['issue','last_issue','term','begin','end','anchor','run_end','follow_begin','follow_end']:
  if c in d:d[c]=pd.to_datetime(d[c])
RULES={'56.3200','57.3200','75.202','77.1004','56.3201','57.3201','56.3202','57.3202','77.1001','77.1002','77.1005','77.1006'}
cols=['EVENT_NO','VIOLATION_NO','VIOLATOR_ID','VIOLATOR_TYPE_CD','MINE_ID','MINE_TYPE','COAL_METAL_IND','CONTRACTOR_ID','VIOLATION_ISSUE_DT','SIG_SUB','PART_SECTION','ORIG_TERM_DUE_DT','TERMINATION_DT','TERMINATION_TYPE','VACATE_DT','INITIAL_VIOL_NO','REPLACED_BY_ORDER_NO','LIKELIHOOD','INJ_ILLNESS','NO_AFFECTED','NEGLIGENCE']
G=[];IDs=[];links=[];n=0
with zipfile.ZipFile(SRC/'violations.zip') as z:
 with z.open(z.namelist()[0]) as fh:
  for d in pd.read_csv(fh,sep='|',dtype=str,encoding='latin1',quoting=csv.QUOTE_NONE,na_filter=False,usecols=cols,chunksize=160000):
   for c in d:d[c]=d[c].str.strip('"')
   n+=len(d);IDs.append(d.VIOLATION_NO.astype('int64').to_numpy())
   linked=d.INITIAL_VIOL_NO.ne('')|d.REPLACED_BY_ORDER_NO.ne('')
   links.append(d.loc[linked,['VIOLATION_NO','INITIAL_VIOL_NO','REPLACED_BY_ORDER_NO']])
   take=d.PART_SECTION.str.extract(r'^(\d+\.\d+)',expand=False).isin(RULES)
   G.append(d.loc[take].copy())
   if n%800000==0:print('raw',n,round(time.time()-T,1),flush=True)
g=pd.concat(G,ignore_index=True); ids=pd.Series(np.concatenate(IDs));dups=set(ids[ids.duplicated(False)])
l=pd.concat(links);touch=set(pd.to_numeric(l.stack(),errors='coerce').dropna().astype('int64'))
g['uncertain']=g.VIOLATION_NO.astype('int64').isin(dups|touch)|g.TERMINATION_TYPE.eq('ReplacedByOrder')
for c in ['VIOLATION_ISSUE_DT','TERMINATION_DT','ORIG_TERM_DUE_DT','VACATE_DT']:g[c]=pd.to_datetime(g[c],format='%m/%d/%Y',errors='coerce')
g=g.rename(columns={'VIOLATOR_ID':'OPERATOR_ID','VIOLATION_ISSUE_DT':'issue','TERMINATION_DT':'term','ORIG_TERM_DUE_DT':'due'})
g=g[g.VIOLATOR_TYPE_CD.eq('Operator')&g.CONTRACTOR_ID.eq('')&g.OPERATOR_ID.ne('')&g.issue.between('2000-01-01','2025-12-31')&g.VACATE_DT.isna()].copy()
g['days']=(g.term-g.issue).dt.days;g['ss_yes']=g.SIG_SUB.eq('Y');g['ss_known']=g.SIG_SUB.isin(['Y','N']);g['inj_serious']=g.INJ_ILLNESS.isin(['Fatal','Permanent']);g['like_elevated']=g.LIKELIHOOD.isin(['Reasonably','Highly','Occurred'])
keys=['MINE_ID','OPERATOR_ID','PART_SECTION','EVENT_NO']
z=g.groupby(keys,observed=True).agg(raw_n=('VIOLATION_NO','size'),raw_ss=('ss_yes','max'),raw_ss_known=('ss_known','all'),raw_term=('term','max'),raw_issue=('issue','min'),raw_last_issue=('issue','max'),days_max=('days','max'),days_min=('days','min'),raw_days_med=('days','median'),raw_uncertain=('uncertain','any'),raw_serious=('inj_serious','max'),raw_likely=('like_elevated','max')).reset_index()
e=e.merge(z,on=keys,how='left',validate='one_to_one');e['fast_all1']=e.days_max.le(1)&e.days_min.ge(0)
qa={'raw_rows':n,'ground_operator_rows':len(g),'global_duplicate_numbers':len(dups),'episodes':len(e),'mines':e.MINE_ID.nunique(),'index_n_mismatch':int(e.n.ne(e.raw_n).sum()),'index_ss_mismatch':int(e.ss.ne(e.raw_ss).sum()),'index_term_mismatch':int(e.term.ne(e.raw_term).sum()),'index_days_mismatch':int(e.days_med.ne(e.raw_days_med).sum()),'index_link_uncertain':int(e.raw_uncertain.sum())}
zz=z.rename(columns={'EVENT_NO':'EVENT_NO_follow', **{c:'f_'+c for c in z.columns if c not in keys}})
f=f.merge(zz,on=['MINE_ID','OPERATOR_ID','PART_SECTION','EVENT_NO_follow'],how='left',validate='many_to_one')
qa['outcome_mismatch']=int(f.y.ne(f.f_raw_n.notna().astype(int)).sum());qa['positive_ss_unknown']=int((f.y.eq(1)&~f.f_raw_ss_known.fillna(False).astype(bool)).sum());qa['positive_uncertain']=int((f.y.eq(1)&f.f_raw_uncertain.fillna(False).astype(bool)).sum());qa['positive_issue_before_anchor']=int((f.y.eq(1)&f.f_raw_issue.le(f.anchor)).sum())
f=f.merge(e[['episode_id','days_max','days_min','fast_all1']],on='episode_id',validate='many_to_one')
e.to_pickle(C/'episodes.pkl');f.to_pickle(C/'followups.pkl');g.to_pickle(C/'ground.pkl');z.to_pickle(C/'groups.pkl')
e.to_csv(O/'episodes_raw_linked.csv.gz',index=False);f.to_csv(O/'followups_raw_linked.csv.gz',index=False)
(O/'raw_linkage_qa.json').write_text(json.dumps(qa,indent=2,default=int))
print(qa, 'seconds',round(time.time()-T,1),flush=True)
assert all(qa[x]==0 for x in ['index_n_mismatch','index_ss_mismatch','index_term_mismatch','index_days_mismatch','outcome_mismatch','positive_ss_unknown','positive_uncertain','positive_issue_before_anchor'])
