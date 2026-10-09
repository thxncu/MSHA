from pathlib import Path
import pandas as pd,numpy as np,json,time
R=Path(__file__).resolve().parents[1];C=R/'cache';O=R/'inputs/cohort';O.mkdir(parents=True,exist_ok=True);T=time.time();CUT=pd.Timestamp('2025-12-31'); flow={}
i=pd.read_pickle(C/'inspections.pkl').rename(columns={'INSPECTION_BEGIN_DT':'begin','INSPECTION_END_DT':'end','SUM(TOTAL_ON_SITE_HOURS)':'onsite','SUM(TOTAL_INSP_HOURS)':'totalhours','NBR_INSPECTOR':'inspectors','INSPECT_OFFICE_CD':'office','ACTIVE_SECTIONS':'active'})
i=i[~i.EVENT_NO.duplicated(False)&i.begin.notna()&i.OPERATOR_ID.ne('')].sort_values(['MINE_ID','begin','end','EVENT_NO']).reset_index(drop=True)
i['run']=(i.MINE_ID.ne(i.MINE_ID.shift())|i.OPERATOR_ID.ne(i.OPERATOR_ID.shift())).cumsum()
i['run_end']=i.groupby('MINE_ID')['begin'].transform(lambda v:pd.NaT) # assigned from next run below
runs=i.groupby(['MINE_ID','run'],observed=True).agg(run_begin=('begin','min')).reset_index();runs['run_end']=runs.groupby('MINE_ID').run_begin.shift(-1)
i=i.drop(columns='run_end').merge(runs[['run','run_end']],on='run',how='left',validate='many_to_one')
reg=i[i.ACTIVITY_CODE.eq('E01')&i.begin.le(CUT)&i.end.le(CUT)&i.end.ge(i.begin)].copy()
reg=reg[reg.run_end.isna()|reg.end.lt(reg.run_end)].sort_values(['MINE_ID','begin','end','EVENT_NO']).reset_index(drop=True)
reg['seq']=reg.groupby('run').cumcount();reg['duration']=(reg.end-reg.begin).dt.days
# Exclude overlapping E01 pairs explicitly at pair construction, not by skipping an intervening event.
g=pd.read_pickle(C/'ground.pkl');links=pd.read_pickle(C/'links.pkl'); dup=set(np.load(C/'duplicate_violation_ids.npy'));touch=set(pd.to_numeric(links.stack(),errors='coerce').dropna().astype('int64'))
g['VIOLATION_NO']=pd.to_numeric(g.VIOLATION_NO)
for v in ['VIOLATION_ISSUE_DT','TERMINATION_DT','ORIG_TERM_DUE_DT','VACATE_DT']:g[v]=pd.to_datetime(g[v],format='%m/%d/%Y',errors='coerce')
g=g.rename(columns={'VIOLATOR_ID':'OPERATOR_ID','VIOLATION_ISSUE_DT':'issue','TERMINATION_DT':'term','ORIG_TERM_DUE_DT':'due'})
g=g[g.VIOLATOR_TYPE_CD.eq('Operator')&g.CONTRACTOR_ID.eq('')&g.OPERATOR_ID.ne('')&g.issue.between('2000-01-01',CUT)&g.VACATE_DT.isna()].copy()
g['uncertain']=g.VIOLATION_NO.isin(dup|touch)|g.TERMINATION_TYPE.eq('ReplacedByOrder')
g['closed']=g.TERMINATION_TYPE.eq('Terminated')&g.term.ge(g.issue)&g.term.le(CUT)
g['days']=(g.term-g.issue).dt.days;g['ss']=g.SIG_SUB.eq('Y').astype(int);g['occurred']=g.LIKELIHOOD.eq('Occurred')
g['highneg']=g.NEGLIGENCE.isin(['HighNegligence','Reckless']).astype(int);g['fatal']=g.INJ_ILLNESS.eq('Fatal').astype(int);g['affected']=pd.to_numeric(g.NO_AFFECTED,errors='coerce');g['due_days']=(g.due-g.issue).dt.days
g['prefix']=g.PART_SECTION.str.split('.').str[0]
keys=['MINE_ID','OPERATOR_ID','PART_SECTION','EVENT_NO']
z=g.groupby(keys,observed=True).agg(n=('VIOLATION_NO','size'),issue=('issue','min'),last_issue=('issue','max'),term=('term','max'),closed=('closed','all'),uncertain=('uncertain','any'),occurred=('occurred','any'),ss=('ss','max'),highneg=('highneg','max'),fatal=('fatal','max'),affected=('affected','max'),days_med=('days','median'),due_med=('due_days','median'),prefix=('prefix','first')).reset_index()
z=z.merge(reg,on=['MINE_ID','OPERATOR_ID','EVENT_NO'],how='inner',validate='many_to_one');z['anchor']=z[['term','end']].max(axis=1)
z['validissue']=z.issue.ge(z.begin)&z.last_issue.le(z.end)
z['eligible']=z.validissue&z.closed&~z.uncertain&~z.occurred&z.anchor.le(CUT)&z.begin.between('2008-01-01','2024-12-31')&(z.run_end.isna()|z.anchor.lt(z.run_end))
flow['candidate_groups']=int(z.begin.between('2008-01-01','2024-12-31').sum());flow['eligible_before_open']=int(z.eligible.sum())
# Check other open records of same provision, excluding own inspection record(s).
Gdict={k:d for k,d in g.groupby(['MINE_ID','OPERATOR_ID','PART_SECTION'],observed=True,sort=False)}
z['other_open']=False
for k,inds in z[z.eligible].groupby(['MINE_ID','OPERATOR_ID','PART_SECTION'],observed=True).groups.items():
 h=Gdict[k]
 for idx in inds:
  r=z.loc[idx];a=h[h.EVENT_NO.ne(r.EVENT_NO)]
  open_start=(a.issue.lt(r.begin)&(a.term.isna()|a.term.ge(r.begin)))
  open_anchor=(a.issue.le(r.anchor)&(a.term.isna()|a.term.gt(r.anchor)))
  if open_start.any() or open_anchor.any():z.loc[idx,'other_open']=True
eligible=z[z.eligible&~z.other_open].copy();eligible['unit']=eligible.MINE_ID+'|'+eligible.run.astype(str)+'|'+eligible.PART_SECTION
flow['eligible_before_followup_requirement']=len(eligible)
# Keep first eligible index before examining future outcomes/operations completeness.
e=eligible.sort_values(['anchor','EVENT_NO']).drop_duplicates('unit',keep='first').copy().reset_index(drop=True);e['episode_id']=e.index
flow['first_eligible_episodes']=len(e)
regdict={r:d for r,d in reg.groupby('run',sort=False)}
look={(r,rule):d for (r,rule),d in z.groupby(['run','PART_SECTION'],observed=True,sort=False)}
# Enrich index with earlier completed inspection history, computed without future data.
for c in ['past4_rate','past4_n','past4_ss','past4_days','past365_same']:e[c]=np.nan
for idx,r in e.iterrows():
 hist=regdict[r.run];hist=hist[hist.end.lt(r.begin)].tail(4)
 zz=look.get((r.run,r.PART_SECTION),pd.DataFrame())
 hits=zz[zz.EVENT_NO.isin(hist.EVENT_NO)] if len(zz) else zz
 e.loc[idx,'past4_n']=len(hist);e.loc[idx,'past4_rate']=len(hits)/len(hist) if len(hist) else np.nan
 e.loc[idx,'past4_ss']=hits.ss.max() if len(hits) else 0
 a=Gdict[(r.MINE_ID,r.OPERATOR_ID,r.PART_SECTION)]
 e.loc[idx,'past365_same']=int(a.issue.between(r.begin-pd.Timedelta(days=365),r.begin-pd.Timedelta(days=1)).sum())
rows=[];endrows=[]
for _,r in e.iterrows():
 rr=regdict[r.run];future=rr[rr.begin.gt(r.anchor)].copy()
 allsame=Gdict[(r.MINE_ID,r.OPERATOR_ID,r.PART_SECTION)]
 # only records within this observed operator run
 end=r.run_end if pd.notna(r.run_end) else CUT+pd.Timedelta(days=1)
 aa=allsame[allsame.issue.gt(r.anchor)&allsame.issue.lt(end)].sort_values('issue')
 # Any non-regular same-rule citation is a competing detection process, not a zero.
 events=set(future.EVENT_NO)
 nonreg=aa[~aa.EVENT_NO.isin(events)]
 compdate=nonreg.issue.min() if len(nonreg) else pd.NaT
 prev_end=r.anchor;status='administrative_or_no_further_E01';seen=0
 for nr in future.itertuples():
  if nr.begin<=prev_end:status='overlapping_E01';break
  if pd.notna(compdate) and compdate<nr.begin:status='nonregular_same_rule';break
  h=aa[aa.EVENT_NO.eq(nr.EVENT_NO)]
  # A non-regular detection during this E01 means the sequence is not an isolated E01 recurrence.
  if pd.notna(compdate) and compdate<=nr.end and (len(h)==0 or compdate<h.issue.min()):status='nonregular_same_rule';break
  if len(h) and (h.uncertain.any() or (~h.issue.between(nr.begin,nr.end)).any()):status='ambiguous_followup';break
  seen+=1;y=int(len(h)>0)
  rows.append({'episode_id':int(r.episode_id),'EVENT_NO_follow':nr.EVENT_NO,'follow_begin':nr.begin,'follow_end':nr.end,'k':seen,'y':y,'follow_onsite':nr.onsite,'follow_duration':nr.duration,'follow_active':nr.active,'follow_office':nr.office,'gap_days':(nr.begin-prev_end).days,'calendar_days':(nr.begin-r.anchor).days})
  if y:status='E01_same_rule';break
  prev_end=nr.end
 # Determine the first known exit even when no later eligible E01 exists.
 if status=='administrative_or_no_further_E01' and pd.notna(compdate):status='nonregular_same_rule'
 if status=='administrative_or_no_further_E01' and pd.notna(r.run_end):status='operator_change_after_last_observation'
 endrows.append({'episode_id':int(r.episode_id),'status':status,'n_observed_E01':seen})
e=e.merge(pd.DataFrame(endrows),on='episode_id',validate='one_to_one'); f=pd.DataFrame(rows).merge(e,on='episode_id',validate='many_to_one')
e.to_pickle(C/'first_episodes.pkl');f.to_pickle(C/'survival_panel.pkl');e.to_csv(O/'first_episodes.csv.gz',index=False);f.to_csv(O/'survival_panel.csv.gz',index=False)
flow['followup_rows']=len(f);flow['episodes_observed']=f.episode_id.nunique();flow['E01_first_rec_events']=int(f.y.sum());flow['end_status']=e.status.value_counts().to_dict()
print('first episodes',flow,round(time.time()-T,1),flush=True)

(O/'cohort_flow.json').write_text(json.dumps(flow,indent=2,default=str))
