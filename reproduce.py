#!/usr/bin/env python3
"""Reproduce reported MSHA closure-pathway results from linked records or source files."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for block in iter(lambda:fh.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['derived','raw'],default='derived')
    parser.add_argument('--source-zip',type=Path,help='Exact source archive identified in source_manifest.json; required for raw mode.')
    parser.add_argument('--output-dir',type=Path,default=Path('reproduced_output'))
    args=parser.parse_args();pkg=Path(__file__).resolve().parent;out=args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):parser.error('Output directory must be new or empty; existing results will not be overwritten.')
    out.mkdir(parents=True,exist_ok=True)
    # Input checks prevent silent use of altered packaged analysis records.
    hashes=json.loads((pkg/'input_checksums.json').read_text())
    for rel,expected in hashes.items():
        if sha256(pkg/rel)!=expected:raise ValueError(f'Packaged input checksum mismatch: {rel}')
    for folder in ['code','data','expected']:shutil.copytree(pkg/folder,out/folder)
    for folder in ['cache','results','inputs/cohort','inputs/source/raw']:(out/folder).mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env.update({'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','MPLBACKEND':'Agg'})
    def run(name: str) -> None:
        print(f'Running {name}',flush=True)
        log=out/'results'/(Path(name).stem+'.log')
        with log.open('w') as fh:
            result=subprocess.run([sys.executable,str(out/'code'/name)],stdout=fh,stderr=subprocess.STDOUT,env=env)
        if result.returncode:
            raise RuntimeError(f'{name} failed. Inspect {log}\n{log.read_text()[-3000:]}')
    if args.mode=='raw':
        if args.source_zip is None:parser.error('--source-zip is required in raw mode.')
        src=args.source_zip.resolve();manifest=json.loads((pkg/'source_manifest.json').read_text())
        if not src.is_file():raise FileNotFoundError(src)
        if src.stat().st_size!=manifest['source_archive_bytes'] or sha256(src)!=manifest['source_archive_sha256']:
            raise ValueError('The source archive does not match the study snapshot. No substitution was performed.')
        with zipfile.ZipFile(src) as archive:
            for member in manifest['required_archive_members']:
                dest=out/'inputs/source'/member
                with archive.open(member) as reader,dest.open('wb') as writer:shutil.copyfileobj(reader,writer)
        for name in ['00_prepare_source.py','01_build_cohort.py','02_link_classifications.py','03_estimate_paths.py','04_followup_schedule.py','05_sensitivity.py']:run(name)
    else:
        import numpy as np
        import pandas as pd
        ids={x:str for x in ['MINE_ID','OPERATOR_ID','PART_SECTION','EVENT_NO','EVENT_NO_follow','prefix','office','follow_office']}
        e=pd.read_csv(out/'data/episode_records.csv.gz',dtype=ids,low_memory=False)
        f=pd.read_csv(out/'data/inspection_records.csv.gz',dtype=ids,low_memory=False)
        dates=['issue','last_issue','term','begin','end','anchor','run_end','raw_term','raw_issue','raw_last_issue','follow_begin','follow_end','f_raw_term','f_raw_issue','f_raw_last_issue']
        bools=['raw_ss','raw_ss_known','raw_uncertain','fast_all1','f_raw_ss','f_raw_ss_known','f_raw_uncertain','f_raw_serious']
        for d in [e,f]:
            for c in dates:
                if c in d:d[c]=pd.to_datetime(d[c],errors='raise')
            for c in bools:
                if c in d:d[c]=d[c].map(lambda v:np.nan if pd.isna(v) else (v is True or str(v)=='True'))
        e.to_pickle(out/'cache/episodes.pkl');f.to_pickle(out/'cache/followups.pkl')
        run('03_estimate_paths.py')
        schedule=pd.read_csv(out/'data/schedule_records.csv.gz')
        for c in ['schedule_4_end','schedule_8_end']:schedule[c]=pd.to_datetime(schedule[c])
        q=pd.read_pickle(out/'cache/paths.pkl').merge(schedule,on='episode_id',validate='one_to_one')
        q.to_pickle(out/'cache/paths_schedule.pkl');q.to_csv(out/'results/episode_paths_schedule.csv.gz',index=False)
        shutil.copy2(out/'data/first_any_inspection_detection.csv.gz',out/'results/first_any_inspection_detection.csv.gz')
        run('05_sensitivity.py')
    run('06_outputs_and_checks.py')
    run('07_composition.py')
    validation=json.loads((out/'results/validation.json').read_text());validation['mode']=args.mode
    validation['raw_linkage_rebuilt']=args.mode=='raw'
    validation['composition_checks']=json.loads((out/'results/composition_validation.json').read_text())
    (out/'results/validation.json').write_text(json.dumps(validation,indent=2))
    print(f'Completed. Tables, figures, and validation: {out / "results"}',flush=True)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(f'Reproduction stopped: {error}',file=sys.stderr)
        raise SystemExit(1)
