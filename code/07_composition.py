"""Describe changing observed sets and directly standardize three recorded attributes.

No hazards, counterfactual risks, or missing follow-up outcomes are estimated.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results'
TABLES = OUT / 'tables'
SEED = 20261010
RESAMPLES = 3000

def main() -> None:
    episodes = pd.read_pickle(ROOT / 'cache/episodes.pkl').copy()
    visits = pd.read_pickle(ROOT / 'cache/followups.pkl').copy()
    episodes['part'] = episodes['prefix'].astype(str)
    episodes['index_ss'] = episodes['raw_ss'].astype(bool)
    episodes['late_period'] = pd.to_datetime(episodes['begin']).dt.year.ge(2017)
    episodes['three_plus'] = episodes['raw_n'].ge(3)
    columns = ['episode_id','part','index_ss','late_period','three_plus','fast_all1']
    data = visits.loc[visits['k'].between(1,4), ['episode_id','MINE_ID','k','y']].merge(
        episodes[columns], on='episode_id', validate='many_to_one')
    if data[['part','index_ss','late_period','three_plus','fast_all1']].isna().any().any():
        raise ValueError('Missing values in composition attributes.')
    if data.duplicated(['episode_id','k']).any():
        raise ValueError('Duplicate episode-opportunity records.')
    expected_n = [4159,3228,2739,2416]
    expected_y = [674,277,140,110]
    assert data.groupby('k').size().tolist() == expected_n
    assert data.groupby('k')['y'].sum().tolist() == expected_y

    rows = []
    for k,g in data.groupby('k',sort=True):
        attrs = {f'part{p}':g['part'].eq(p) for p in ['56','57','75','77']}
        attrs.update({'index_ss':g['index_ss'],'three_plus':g['three_plus'],
                      'late_period':g['late_period'],'rapid':g['fast_all1']})
        for key,mask in attrs.items():
            rows.append({'k':int(k),'attribute':key,'n':len(g),
                         'count':int(mask.sum()),'fraction':float(mask.mean())})
    comp = pd.DataFrame(rows)
    comp.to_csv(OUT / 'composition_by_opportunity.csv',index=False)
    labels = [('part56','Part 56'),('part57','Part 57'),('part75','Part 75'),
              ('part77','Part 77'),('index_ss','Index group includes S&S'),
              ('three_plus','At least three index citations'),
              ('late_period','Index inspection in 2017–2024'),('rapid','Rapid closure')]
    table_rows = [['Episodes observed']+[f'{n:,}' for n in expected_n]]
    for key,label in labels:
        part = comp.loc[comp['attribute'].eq(key)].set_index('k')
        table_rows.append([label]+[f"{int(part.loc[k,'count']):,} ({100*part.loc[k,'fraction']:.1f})" for k in range(1,5)])
    pd.DataFrame(table_rows,columns=['Recorded characteristic','Opportunity 1','Opportunity 2','Opportunity 3','Opportunity 4']).to_csv(TABLES/'Table_S6.csv',index=False)

    # Cross-classify baseline attributes. All 16 cells must be observed at every opportunity.
    strata = [(p,ss,late) for p in ['56','57','75','77'] for ss in [False,True] for late in [False,True]]
    lookup = {s:i for i,s in enumerate(strata)}
    data['stratum'] = [lookup[t] for t in zip(data.part,data.index_ss,data.late_period)]
    mines = pd.Index(sorted(episodes['MINE_ID'].astype(str).unique()))
    mine_i = mines.get_indexer(data['MINE_ID'].astype(str))
    assert (mine_i>=0).all()
    groups = (data['k'].to_numpy(int)-1)*16+data['stratum'].to_numpy(int)
    den = np.zeros((len(mines),64),dtype=float)
    num = np.zeros_like(den)
    np.add.at(den,(mine_i,groups),1)
    np.add.at(num,(mine_i,groups),data['y'].to_numpy(float))
    totals_d = den.sum(axis=0).reshape(4,16)
    totals_y = num.sum(axis=0).reshape(4,16)
    if (totals_d==0).any():
        raise ValueError('A reference stratum has no observations at a later opportunity.')
    weights = totals_d[0]/totals_d[0].sum()
    raw = totals_y.sum(axis=1)/totals_d.sum(axis=1)
    std = ((totals_y/totals_d)*weights).sum(axis=1)
    np.testing.assert_allclose(std[0],raw[0],atol=1e-14)
    cells=[]
    for k in range(4):
        for j,(p,ss,late) in enumerate(strata):
            cells.append({'k':k+1,'part':p,'index_ss':ss,
                          'period':'2017-2024' if late else '2008-2016',
                          'observed':int(totals_d[k,j]),'repeats':int(totals_y[k,j]),
                          'reference_weight':weights[j],'fraction':totals_y[k,j]/totals_d[k,j]})
    pd.DataFrame(cells).to_csv(OUT/'standardization_cells.csv',index=False)

    rng = np.random.default_rng(SEED)
    raw_boot, std_boot = [], []
    for first in range(0,RESAMPLES,100):
        size = min(100,RESAMPLES-first)
        mult = rng.multinomial(len(mines),np.full(len(mines),1/len(mines)),size=size)
        bd = (mult @ den).reshape(size,4,16)
        by = (mult @ num).reshape(size,4,16)
        if (bd==0).any():
            raise ValueError('Empty standardization cell in a cluster resample; no silent deletion.')
        # Re-estimate the reference composition in each resample, preserving uncertainty in weights.
        bw = bd[:,0,:]/bd[:,0,:].sum(axis=1,keepdims=True)
        raw_boot.append(by.sum(axis=2)/bd.sum(axis=2))
        std_boot.append(((by/bd)*bw[:,None,:]).sum(axis=2))
    raw_boot = np.concatenate(raw_boot)
    std_boot = np.concatenate(std_boot)
    raw_ci = np.quantile(raw_boot,[.025,.975],axis=0)
    std_ci = np.quantile(std_boot,[.025,.975],axis=0)
    estimates = pd.DataFrame({'k':range(1,5),'n':totals_d.sum(axis=1).astype(int),
       'events':totals_y.sum(axis=1).astype(int),'crude':raw,
       'crude_lower':raw_ci[0],'crude_upper':raw_ci[1],
       'standardized':std,'standardized_lower':std_ci[0],'standardized_upper':std_ci[1]})
    estimates.to_csv(OUT/'standardized_observed_fractions.csv',index=False)
    tab=[]
    for z in estimates.itertuples():
        tab.append([str(z.k),f'{z.n:,}',f'{z.events:,}',
                    f'{100*z.crude:.1f} ({100*z.crude_lower:.1f}–{100*z.crude_upper:.1f})',
                    f'{100*z.standardized:.1f} ({100*z.standardized_lower:.1f}–{100*z.standardized_upper:.1f})'])
    pd.DataFrame(tab,columns=['Opportunity','Episodes observed','First repeats','Unstandardized, % (95% interval)','Common recorded mix, % (95% interval)']).to_csv(TABLES/'Table_S7.csv',index=False)
    qa = {'passed':True,'episode_inspection_rows':len(data),'observed_mines':data.MINE_ID.nunique(),
          'cohort_mines_resampled':len(mines),'strata':16,'minimum_original_cell_n':int(totals_d.min()),
          'resamples':RESAMPLES,'seed':SEED,'empty_resample_cells':0,
          'reference':'First observed inspection; weights recalculated in each cluster resample',
          'attributes':['recorded part','index S&S group','index period'],
          'outcome':'First primary-sequence repeat at each observed eligible inspection',
          'causal_or_cumulative_risk':False}
    for name in ['composition_by_opportunity.csv','standardization_cells.csv','standardized_observed_fractions.csv']:
        reference = ROOT / 'expected' / name
        if not reference.exists():
            raise FileNotFoundError(f'Missing numerical reference output: {reference}')
        pd.testing.assert_frame_equal(pd.read_csv(OUT/name),pd.read_csv(reference),
                                      check_exact=False,atol=1e-12,rtol=1e-10)
    qa['numerically_matched_outputs'] = ['composition_by_opportunity.csv','standardization_cells.csv','standardized_observed_fractions.csv']
    (OUT/'composition_validation.json').write_text(json.dumps(qa,indent=2))
    print(estimates.to_string(index=False))
    print(json.dumps(qa,indent=2))

if __name__ == '__main__':
    main()
