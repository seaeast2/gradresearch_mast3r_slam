import csv, hashlib, json, re, sys
from pathlib import Path
import numpy as np
from plyfile import PlyData

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/E2a_overlap'))
from run_e2a import similarity, transform

def main():
    out=ROOT/'results/E3_fusion/2026-10-28/instrumented'
    e1=ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'
    rows=list(csv.DictReader((ROOT/'data/HKairport01/mapping_frames.csv').open()))
    for row in rows:
        p=ROOT/'data/HKairport01/mapping'/row['png_filename']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==row['png_sha256']
    pattern=re.compile(r'E1_TRACK frame=(\d+) timestamp=([^ ]+) reference_kf=(\d+) success=(\d+) new_kf=(\d+)')
    log=pattern.findall((out/'run.log').read_text())
    ref=list(csv.DictReader((e1/'tracking_timeline.csv').open()))[1:]
    assert len(log)==len(ref)==239
    for v,t in zip(log,ref):
        assert int(v[0])==int(t['frame_index']) and int(v[2])==int(t['reference_kf']) and v[3]==t['tracking_success'] and v[4]==t['new_keyframe'] and abs(float(v[1])-float(t['timestamp']))<1e-6
    prov=np.load(out/'provenance.npz'); ids=prov['kf_id']; pix=prov['pixel_index']; ply=PlyData.read(out/'output/mapping.ply')['vertex'].data
    world_check={}
    for k in range(31,36):
        init=np.load(next((out/'events').glob(f'kf{k}_initial_frame*.npz')))
        replay=np.load(ROOT/f'results/E2_raw_pointmap/2026-10-28/raw_pairs/kf{k}_birth_self.npz')
        assert np.array_equal(init['pixel_index'],replay['pixel_index']) and np.array_equal(init['xyz'],replay['xyz']) and np.array_equal(init['confidence'].reshape(-1),replay['confidence'])
        events=sorted((out/'events').glob(f'kf{k}_update_frame*.npz'),key=lambda f:int(f.stem.split('frame')[-1])); last=np.load(events[-1])
        sel=np.flatnonzero(ids==k); indices=np.full(416*512,-1,np.int64); indices[pix[sel]]=sel
        ix=indices[last['pixel_index']]; valid=ix>=0
        world=np.column_stack([ply[c][ix[valid]] for c in 'xyz']).astype(float); local=last['after_xyz'][valid].astype(float)
        err=np.linalg.norm(transform(local,similarity(local,world))-world,axis=1)
        assert err.max()<1e-5
        world_check[str(k)]={'count':int(len(err)),'rmse':float(np.sqrt(np.mean(err**2))),'max_distance':float(err.max())}
    output={'input_png_hashes_valid':len(rows),'tracking_events_match_e1':len(log),'e2_replay_exact_initial_roi_kfs':list(range(31,36)),
            'final_roi_fit_to_export_sim3':world_check,
            'caveat':'fitting an unconstrained Sim3 tests shape consistency with final export, not exact pose or world placement'}
    (out/'validation.json').write_text(json.dumps(output,indent=2)+'\n'); print(json.dumps(output,indent=2))

if __name__=='__main__': main()
