"""Create all numeric manuscript tables and both supplementary figures; validate counts."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];O=R/'results';T=O/'tables';F=O/'figures'
T.mkdir(exist_ok=True);F.mkdir(exist_ok=True)
p=pd.read_pickle(R/'cache/paths.pkl');follow=pd.read_pickle(R/'cache/followups.pkl')
m=pd.read_csv(O/'path_metrics_cluster_CI.csv');s=pd.read_csv(O/'path_sensitivities_cluster_CI.csv')
curve=pd.read_csv(O/'inspection_opportunity_curve.csv');cv=curve[curve.scope.eq('all')].copy()
def rec(K):return p.event_k.le(K)
def clean(K):return p.n_observed_E01.ge(K)&~rec(K)
def fmt_interval(df,scope,metric,K=4):
 z=df[df.scope.eq(scope)&df.metric.eq(metric)&df.horizon.eq(K)]
 if len(z)!=1:raise ValueError((scope,metric,K,len(z)))
 z=z.iloc[0]
 return f"{100*z.estimate:.1f} ({100*z.lower:.1f}–{100*z.upper:.1f})"
def save(name,headers,rows):pd.DataFrame(rows,columns=headers).to_csv(T/(name+'.csv'),index=False)
actual={'episodes':len(p),'mines':p.MINE_ID.nunique(),'followup_rows':len(follow),'unique_followup_inspections':follow.EVENT_NO_follow.nunique(),'has_first':int(p.first_y.notna().sum()),'horizon_4':{'repeats':int(rec(4).sum()),'four_noncitations':int(clean(4).sum()),'exits':int((~rec(4)&~clean(4)).sum()),'delayed':int((rec(4)&p.event_k.gt(1)).sum()),'ss':int((rec(4)&p.rec_ss.eq(True)).sum()),'delayed_ss':int((rec(4)&p.event_k.gt(1)&p.rec_ss.eq(True)).sum()),'index_nonss_then_ss':int((rec(4)&p.rec_ss.eq(True)&p.ss.eq(0)).sum())},'first_noncitation':{'n':int(p.first_clear.sum()),'repeat':int((p.first_clear&rec(4)).sum()),'ss':int((p.first_clear&rec(4)&p.rec_ss.eq(True)).sum()),'exits':int((p.first_clear&~rec(4)&~clean(4)).sum())},'exit_reasons_4':{str(k):int(v) for k,v in p.loc[~rec(4)&~clean(4),'status'].value_counts().items()},'fast':{'episodes':int(p.fast_all1.sum()),'repeat':int((p.fast_all1&rec(4)).sum()),'four_noncitations':int((p.fast_all1&clean(4)).sum()),'exits':int((p.fast_all1&~rec(4)&~clean(4)).sum()),'delayed':int((p.fast_all1&rec(4)&p.event_k.gt(1)).sum()),'ss':int((p.fast_all1&rec(4)&p.rec_ss.eq(True)).sum())},'horizon_8':{'repeats':int(rec(8).sum()),'delayed':int((rec(8)&p.event_k.gt(1)).sum()),'ss':int((rec(8)&p.rec_ss.eq(True)).sum())}}
expected=json.loads((R/'expected/key_counts.json').read_text())
if actual!=expected:raise AssertionError({'actual':actual,'expected':expected})
# Episode follow-up is unique and ceases at the first recorded primary repeat.
assert not follow.duplicated(['episode_id','k']).any()
assert follow.groupby('episode_id').y.sum().le(1).all()
assert (follow.loc[follow.y.eq(1),'k'].to_numpy()==follow.loc[follow.y.eq(1),'episode_id'].map(follow.groupby('episode_id').k.max()).to_numpy()).all()
assert follow.follow_begin.gt(follow.anchor).all()
# A known citation before the observed operator boundary is not coded as an operator-only exit.
a=pd.read_csv(O/'first_any_inspection_detection.csv.gz',dtype={'MINE_ID':str})
issue=pd.to_datetime(a.first_any_issue);stop=pd.to_datetime(a.run_end)
bad=a.status.eq('operator_change_after_last_observation')&issue.notna()&(stop.isna()|issue.lt(stop))
if bad.any():raise AssertionError('Known prior detection incorrectly assigned to operator-only termination.')
checks=[]
for name in ['path_metrics_cluster_CI.csv','path_sensitivities_cluster_CI.csv','inspection_opportunity_curve.csv','severity_transition_counts.csv','observed_detection_times.csv','paired_severity_change.csv']:
 left=pd.read_csv(O/name);right=pd.read_csv(R/'expected'/name)
 pd.testing.assert_frame_equal(left,right,check_exact=False,atol=1e-12,rtol=1e-10)
 checks.append(name)
(O/'validation.json').write_text(json.dumps({'passed':True,'key_counts':actual,'numerically_matched_outputs':checks,'absolute_tolerance':1e-12,'relative_tolerance':1e-10},indent=2))
rows=[]
for z in cv[cv.k.le(4)].itertuples():rows.append([str(z.k),f'{z.at_risk:,}',f'{z.events:,}',f'{z.SS_events:,}',f'{z.events-z.SS_events:,}'])
save('Table_1',['Inspection opportunity','Episodes observed','First repeats','Repeats with S&S','Repeats without S&S'],rows)
ms=[('Delayed repeats among observed repeats','delayed_share_among_recurrences'),('Repeats with S&S among observed repeats','SS_share_among_recurrences'),('Repeats with S&S among delayed repeats','SS_share_among_delayed_recurrences'),('Delayed repeats among repeats with S&S','delayed_share_among_SS_recurrences'),('Index without S&S among later S&S repeats','initial_nonSS_share_among_SS_recurrences'),('Later repeats after a nonciting first inspection','observed_delayed_recurrence_after_first_clear'),('Later S&S repeats after a nonciting first inspection','observed_delayed_SS_after_first_clear')]
rows=[]
for label,metric in ms:
 z=m[m.scope.eq('all')&m.horizon.eq(4)&m.metric.eq(metric)].iloc[0]
 rows.append([label,f'{int(z.numerator):,} / {int(z.denominator):,}',fmt_interval(m,'all',metric)])
save('Table_2',['Measure','Numerator / denominator','Percentage (95% interval)'],rows)
tr=pd.crosstab(p.loc[rec(4),'ss'],p.loc[rec(4),'rec_ss'])
save('Table_3',['Recorded index classification','Repeat without S&S','Repeat including S&S','Total'],[['Without S&S',str(tr.loc[0,False]),str(tr.loc[0,True]),str(tr.loc[0].sum())],['Including S&S',str(tr.loc[1,False]),str(tr.loc[1,True]),str(tr.loc[1].sum())],['Total',str(tr[False].sum()),str(tr[True].sum()),str(tr.to_numpy().sum())]])
pol=json.loads((R/'data/policy_table.json').read_text());save('Table_4',pol[0],pol[1:])
base={'56':['56.3200','56.3201','56.3202'],'57':['57.3200','57.3201','57.3202'],'75':['75.202'],'77':['77.1001','77.1002','77.1004','77.1005','77.1006']}
rows=[[v,'; '.join(rules),f'{int(p.prefix.eq(v).sum()):,}'] for v,rules in base.items()]+[['Total','12 base provisions',f'{len(p):,}']]
save('Table_S1',['Recorded part','Base provisions selected','Index episodes'],rows)
labels={'administrative_or_no_further_E01':'Administrative cutoff or no further eligible E01','operator_change_after_last_observation':'Observed operator change after the last observation','nonregular_same_rule':'Earlier same-provision citation outside the primary sequence','ambiguous_followup':'Ambiguous follow-up citation or linkage','overlapping_E01':'Overlapping E01 inspections'}
save('Table_S2',['Reason follow-up ended early','Episodes'],[[lab,str(actual['exit_reasons_4'][key])] for key,lab in labels.items()]+[['Total episodes ending primary follow-up early','952']])
scopes=[(m,'all','Primary cohort'),(m,'one_episode_per_mine','One episode per mine'),(s,'scheduled_at_least_K','Four E01 records present'),(s,'any_inspection_with_complete_schedule','All types, four E01 records'),(s,'one_initial_and_one_recurring_citation','Single-citation index and repeat'),(s,'same_inspection_office','Same index and repeat office')]
rows=[]
for df,scope,label in scopes:
 z=df[df.scope.eq(scope)&df.horizon.eq(4)&df.metric.eq('delayed_share_among_recurrences')].iloc[0]
 rows.append([label,f'{int(z.denominator):,}',fmt_interval(df,scope,'delayed_share_among_recurrences'),fmt_interval(df,scope,'SS_share_among_recurrences')])
save('Table_S3',['Restriction','Observed repeats','Delayed repeats, % (95% interval)','Repeats with S&S, % (95% interval)'],rows)
rows=[]
for scope,label,mask in [('2008-2016','2008–2016',p.period.eq('2008-2016')),('2017-2024','2017–2024',p.period.eq('2017-2024'))]+[('part'+x,'Part '+x,p.prefix.eq(x)) for x in base]:
 rows.append([label,f'{int(mask.sum()):,}',f'{int((mask&rec(4)).sum()):,}',fmt_interval(m,scope,'delayed_share_among_recurrences'),fmt_interval(m,scope,'SS_share_among_recurrences')])
save('Table_S4',['Period or part','Index episodes','Observed repeats','Delayed repeats, % (95% interval)','Repeats with S&S, % (95% interval)'],rows)
save('Table_S5',['Opportunity','Episodes observed','First repeats','Repeats with S&S','Cited at this opportunity, %'],[[str(z.k),f'{z.at_risk:,}',f'{z.events:,}',f'{z.SS_events:,}',f'{100*z.hazard:.1f}'] for z in cv.itertuples()])
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':12,'text.color':'black','axes.labelcolor':'black','xtick.color':'black','ytick.color':'black','axes.edgecolor':'black','savefig.facecolor':'white','figure.facecolor':'white'})
fig,ax=plt.subplots(figsize=(6.3,4.65))
ax.bar(cv.k,cv.SS_events,facecolor='white',edgecolor='black',hatch='///',label='Including S&S')
ax.bar(cv.k,cv.events-cv.SS_events,bottom=cv.SS_events,facecolor='white',edgecolor='black',label='Without S&S')
ax.set_xlabel('Routine inspection opportunity');ax.set_ylabel('First-repeat citations');ax.set_xticks(np.arange(1,9));ax.set_ylim(0,760)
ax.spines[['top','right']].set_visible(False);ax.legend(frameon=False,loc='upper right')
for z in cv.itertuples():ax.text(z.k,z.events+12,str(z.events),ha='center',fontsize=12)
fig.subplots_adjust(left=.14,right=.98,bottom=.18,top=.96)
fig.savefig(F/'Figure_S1.png',dpi=300);fig.savefig(F/'Figure_S1.pdf');plt.close(fig)
fig,ax=plt.subplots(figsize=(6.3,5.6))
short=['Primary cohort','One episode\nper mine','Four E01\nrecords','All inspection\ntypes','Single-citation\nbundles','Same inspection\noffice']
for metric,off,mark,label in [('delayed_share_among_recurrences',-.12,'o','Delayed share'),('SS_share_among_recurrences',.12,'s','S&S-containing share')]:
 vals=[]
 for df,scope,_ in scopes:vals.append(df[df.scope.eq(scope)&df.horizon.eq(4)&df.metric.eq(metric)].iloc[0])
 d=pd.DataFrame(vals);mean=d.estimate.to_numpy()*100
 ax.errorbar(mean,np.arange(6)+off,xerr=np.vstack([mean-d.lower.to_numpy()*100,d.upper.to_numpy()*100-mean]),color='black',fmt=mark,capsize=3,label=label,markerfacecolor='white' if mark=='s' else 'black')
ax.set_yticks(np.arange(6),short);ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xticks([0,25,50,75,100]);ax.set_xlabel('Share of observed first repeats (%)')
ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',color='.85',linewidth=.6);ax.legend(loc='upper center',bbox_to_anchor=(.4,1.19),frameon=False)
fig.subplots_adjust(left=.40,right=.94,bottom=.15,top=.81)
fig.savefig(F/'Figure_S2.png',dpi=300);fig.savefig(F/'Figure_S2.pdf');plt.close(fig)
print('All count, pathway, and numerical-output checks passed; tables and figures created.')
