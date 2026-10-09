from pathlib import Path
import zipfile,csv,time,json,collections
import pandas as pd,numpy as np
R=Path(__file__).resolve().parents[1]; O=R/'cache';O.mkdir(parents=True,exist_ok=True)
RULES={'56.3200','57.3200','75.202','77.1004','56.3201','57.3201','56.3202','57.3202','77.1001','77.1002','77.1005','77.1006'}
t0=time.time()
def read(name,cols):
 with zipfile.ZipFile(R/'inputs/source/raw'/f'{name}.zip') as z:
  with z.open(z.namelist()[0]) as f:
   for c in pd.read_csv(f,sep='|',dtype=str,encoding='latin1',quoting=csv.QUOTE_NONE,na_filter=False,usecols=cols,chunksize=120000,on_bad_lines='error'):
    for col in c:c[col]=c[col].str.strip('"')
    yield c
cols=['EVENT_NO','VIOLATION_NO','VIOLATOR_ID','VIOLATOR_TYPE_CD','MINE_ID','MINE_TYPE','COAL_METAL_IND','CONTRACTOR_ID','VIOLATION_ISSUE_DT','CAL_YR','SIG_SUB','PART_SECTION','SECTION_OF_ACT_1','CIT_ORD_SAFE','ORIG_TERM_DUE_DT','TERMINATION_DT','TERMINATION_TYPE','VACATE_DT','INITIAL_VIOL_NO','REPLACED_BY_ORDER_NO','LIKELIHOOD','INJ_ILLNESS','NO_AFFECTED','NEGLIGENCE']
G=[];A=[];L=[];IDs=[];cnt=collections.Counter();n=0
for c in read('violations',cols):
 n+=len(c); cnt.update(c.TERMINATION_TYPE)
 IDs.append(pd.to_numeric(c.VIOLATION_NO,errors='raise').to_numpy(dtype=np.int64))
 base=c.PART_SECTION.str.extract(r'^(\d+\.\d+)',expand=False); gr=base.isin(RULES)
 g=c.loc[gr].copy();g['BASE_RULE']=base.loc[gr];G.append(g)
 linked=(c.INITIAL_VIOL_NO!='')|(c.REPLACED_BY_ORDER_NO!='');L.append(c.loc[linked,['VIOLATION_NO','INITIAL_VIOL_NO','REPLACED_BY_ORDER_NO']])
 take=(c.VIOLATOR_TYPE_CD=='Operator')&c.CONTRACTOR_ID.eq('')&c.VIOLATOR_ID.ne('')&c.CAL_YR.between('2000','2025')
 a=c.loc[take,['EVENT_NO','VIOLATION_NO','MINE_ID','VIOLATOR_ID','VIOLATION_ISSUE_DT','TERMINATION_DT','TERMINATION_TYPE','VACATE_DT','PART_SECTION']].copy()
 for v in ['VIOLATION_ISSUE_DT','TERMINATION_DT','VACATE_DT']:a[v]=pd.to_datetime(a[v],format='%m/%d/%Y',errors='coerce')
 for v in ['VIOLATION_NO']:a[v]=pd.to_numeric(a[v],errors='raise').astype('int64')
 a['ground']=gr.loc[take].to_numpy();a=a.rename(columns={'VIOLATOR_ID':'OPERATOR_ID','VIOLATION_ISSUE_DT':'issue','TERMINATION_DT':'term','VACATE_DT':'vacate','TERMINATION_TYPE':'termtype'})
 for v in ['EVENT_NO','MINE_ID','OPERATOR_ID','termtype','PART_SECTION']:a[v]=a[v].astype('category')
 A.append(a)
 if True:print('violations',n,round(time.time()-t0,1),flush=True)
ids=pd.Series(np.concatenate(IDs));dup=ids[ids.duplicated(False)].unique();np.save(O/'duplicate_violation_ids.npy',dup)
g=pd.concat(G,ignore_index=True);g.to_pickle(O/'ground.pkl');l=pd.concat(L,ignore_index=True);l.to_pickle(O/'links.pkl')
a=pd.concat(A,ignore_index=True)
for v in ['EVENT_NO','MINE_ID','OPERATOR_ID','termtype','PART_SECTION']:a[v]=a[v].astype('category')
a.to_pickle(O/'operator_violations.pkl');mines=set(g.MINE_ID)
print('violations done',len(a),len(g),len(dup),round(time.time()-t0,1),flush=True)
del A,a,G,IDs,ids,L,l
cols=['EVENT_NO','MINE_ID','OPERATOR_ID','CONTROLLER_ID','INSPECTION_BEGIN_DT','INSPECTION_END_DT','INSPECT_OFFICE_CD','ACTIVITY_CODE','ACTIVITY','ACTIVE_SECTIONS','IDLE_SECTIONS','OUTBY_AREAS','SURF_UG_MINE','SURF_FACILITY_MINE','NBR_INSPECTOR','SUM(TOTAL_INSP_HOURS)','SUM(TOTAL_ON_SITE_HOURS)','COAL_METAL_IND']
I=[];n=0
for c in read('inspections',cols):
 n+=len(c);I.append(c[c.MINE_ID.isin(mines)].copy())
i=pd.concat(I,ignore_index=True)
for v in ['INSPECTION_BEGIN_DT','INSPECTION_END_DT']:i[v]=pd.to_datetime(i[v],format='%m/%d/%Y',errors='coerce')
for v in ['ACTIVE_SECTIONS','IDLE_SECTIONS','NBR_INSPECTOR','SUM(TOTAL_INSP_HOURS)','SUM(TOTAL_ON_SITE_HOURS)']:i[v]=pd.to_numeric(i[v],errors='coerce')
i.to_pickle(O/'inspections.pkl'); n_inspections=n; print('inspections done',n,len(i),round(time.time()-t0,1),flush=True)

(O/'source_counts.json').write_text(json.dumps({'violation_rows':sum(cnt.values()),'global_duplicate_violation_numbers':len(dup),'inspection_rows':n_inspections,'ground_rows':len(g)},indent=2))
