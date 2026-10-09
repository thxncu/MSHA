from pathlib import Path
import csv,zipfile,json,time
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[1];C=R/'cache';O=R/'results';T=time.time();CUT=pd.Timestamp('2025-12-31')
e=pd.read_pickle(C/'episodes.pkl');f=pd.read_pickle(C/'followups.pkl');g=pd.read_pickle(C/'ground.pkl');mines=set(e.MINE_ID)
cols=['EVENT_NO','MINE_ID','OPERATOR_ID','ACTIVITY_CODE','ACTIVITY','INSPECTION_BEGIN_DT','INSPECTION_END_DT','SUM(TOTAL_ON_SITE_HOURS)','ACTIVE_SECTIONS']
a=[];n=0
with zipfile.ZipFile(R/'inputs/source/raw/inspections.zip') as z:
 with z.open(z.namelist()[0]) as fh:
  for d in pd.read_csv(fh,sep='|',dtype=str,encoding='latin1',quoting=csv.QUOTE_NONE,na_filter=False,usecols=cols,chunksize=160000):
   for col in d:d[col]=d[col].str.strip('"')
   n+=len(d);a.append(d[d.MINE_ID.isin(mines)].copy())
i=pd.concat(a,ignore_index=True);i=i.rename(columns={'INSPECTION_BEGIN_DT':'begin','INSPECTION_END_DT':'end'})
for c in ['begin','end']:i[c]=pd.to_datetime(i[c],format='%m/%d/%Y',errors='coerce')
i=i[~i.EVENT_NO.duplicated(False)]
i.to_pickle(C/'inspections.pkl');ir={key:d.sort_values(['begin','end','EVENT_NO']) for key,d in i.groupby(['MINE_ID','OPERATOR_ID'],observed=True)}
gr={key:d.sort_values(['issue','VIOLATION_NO']) for key,d in g.groupby(['MINE_ID','OPERATOR_ID','PART_SECTION'],observed=True)}
# Full prospective inspection schedule is audited independently of whether recurrence occurred.
rows=[];alt=[]
for row in e.itertuples():
 stop=min(row.run_end,CUT+pd.Timedelta(days=1)) if pd.notna(row.run_end) else CUT+pd.Timedelta(days=1)
 hh=ir.get((row.MINE_ID,row.OPERATOR_ID),pd.DataFrame())
 h=hh[hh.ACTIVITY_CODE.eq('E01')&hh.begin.gt(row.anchor)&hh.end.lt(stop)&hh.end.ge(hh.begin)&hh.end.le(CUT)].copy()
 prev=row.anchor;good=[]
 for nr in h.itertuples():
  if nr.begin<=prev:break
  good.append(nr);prev=nr.end
 out={'episode_id':row.episode_id,'scheduled_E01_count':len(good)}
 for K in [4,8]:out['complete_schedule_'+str(K)]=len(good)>=K;out['schedule_'+str(K)+'_end']=good[K-1].end if len(good)>=K else pd.NaT
 rows.append(out)
 # First post-anchor NEW same-rule record, all event types; ambiguous first record is unresolved, never skipped.
 gg=gr[(row.MINE_ID,row.OPERATOR_ID,row.PART_SECTION)]
 gg=gg[gg.issue.gt(row.anchor)&gg.issue.lt(stop)&gg.EVENT_NO.ne(row.EVENT_NO)]
 if len(gg):
  first=gg.iloc[0];evt=gg[gg.EVENT_NO.eq(first.EVENT_NO)]
  match=hh[hh.EVENT_NO.eq(first.EVENT_NO)]
  if len(match):
   mi=match.iloc[0];act=mi.ACTIVITY_CODE;valid=first.issue>=mi.begin and evt.issue.max()<=mi.end
  else:act='unmatched';valid=False
  clean_before=sum(nr.end<first.issue for nr in good)
  # Only an upper-window location, not a regular-inspection event number for nonregular detections.
  category='new_linkable' if not evt.uncertain.any() and valid else 'ambiguous'
  alt.append(dict(episode_id=row.episode_id,first_any_issue=first.issue,first_any_EVENT_NO=first.EVENT_NO,first_any_activity=act,first_any_status=category,first_any_SS=bool(evt.ss_yes.any()),clean_regular_before=clean_before,first_any_days=(first.issue-row.anchor).days))
s=pd.DataFrame(rows);aa=e[['episode_id','MINE_ID','status','anchor','run_end']].merge(pd.DataFrame(alt),on='episode_id',how='left').merge(s,on='episode_id')
q=pd.read_pickle(C/'paths.pkl').merge(s,on='episode_id',validate='one_to_one')
# Check if a purported complete scheduled window had censoring from competing detection/ambiguity.
summary=[]
for K in [4,8]:
 full=q[q['complete_schedule_'+str(K)]];evt=full.event_k.le(K);clear=full.n_observed_E01.ge(K)&~evt;unresolved=~(evt|clear)
 summary.append({'horizon':K,'scheduled_at_least_K':len(full),'regular_recur':int(evt.sum()),'delayed_regular':int((evt&full.event_k.gt(1)).sum()),'SS_regular':int((evt&full.rec_ss.eq(True)).sum()),'completed_K_clean':int(clear.sum()),'competing_or_ambiguous':int(unresolved.sum()),'regular_delayed_share':float((evt&full.event_k.gt(1)).sum()/evt.sum()),'regular_SS_share':float((evt&full.rec_ss.eq(True)).sum()/evt.sum())})
q.to_pickle(C/'paths_schedule.pkl');q.to_csv(O/'episode_paths_schedule.csv.gz',index=False);aa.to_csv(O/'first_any_inspection_detection.csv.gz',index=False)
pd.DataFrame(summary).to_csv(O/'complete_schedule_sensitivity.csv',index=False)
check=f[['episode_id','EVENT_NO_follow','MINE_ID','OPERATOR_ID','follow_begin','follow_end']].merge(i[['EVENT_NO','MINE_ID','OPERATOR_ID','begin','end','ACTIVITY_CODE']],left_on=['EVENT_NO_follow','MINE_ID','OPERATOR_ID'],right_on=['EVENT_NO','MINE_ID','OPERATOR_ID'],how='left',validate='many_to_one')
qa={'raw_inspection_rows':n,'cohort_mine_inspection_rows':len(i),'followup_inspection_unmatched':int(check.begin.isna().sum()),'followup_begin_mismatch':int(check.begin.ne(check.follow_begin).sum()),'followup_end_mismatch':int(check.end.ne(check.follow_end).sum()),'followup_not_E01':int(check.ACTIVITY_CODE.ne('E01').sum()),'outside_pathway_activity_counts':aa.loc[aa.status.eq('nonregular_same_rule'),'first_any_activity'].value_counts().to_dict()}
(O/'followup_schedule_qa.json').write_text(json.dumps(qa,indent=2,default=str));print(qa);print(pd.DataFrame(summary).to_string(index=False));print('seconds',time.time()-T)
assert all(qa[k]==0 for k in ['followup_inspection_unmatched','followup_begin_mismatch','followup_end_mismatch','followup_not_E01'])
