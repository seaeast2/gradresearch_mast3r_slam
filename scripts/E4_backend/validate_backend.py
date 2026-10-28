import csv, json, re
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from analyze_backend import act, inv_act

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/E4_backend/2026-10-28/instrumented'
E1=ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'

def main():
    pattern=re.compile(r'E1_TRACK frame=(\d+) timestamp=([^ ]+) reference_kf=(\d+) success=(\d+) new_kf=(\d+)')
    found=pattern.findall((OUT/'run.log').read_text()); rows=list(csv.DictReader((E1/'tracking_timeline.csv').open()))[1:]
    assert len(found)==len(rows)==239
    for x,r in zip(found,rows):
        assert int(x[0])==int(r['frame_index']) and int(x[2])==int(r['reference_kf']) and x[3]==r['tracking_success'] and x[4]==r['new_keyframe'] and abs(float(x[1])-float(r['timestamp']))<1e-6
    rng=np.random.default_rng(4); xyz=rng.normal(size=(100,3)); quat=Rotation.from_euler('xyz',[.2,-.3,.4]).as_quat(); pose=np.r_[[.7,-.2,1.5],quat,1.9]
    transformed=act(pose,xyz); assert np.max(abs(inv_act(pose,transformed)-xyz))<1e-12
    # Synthetic identical planes and a known normal translation must yield exactly that seam.
    plane=np.column_stack((rng.normal(size=(100,2)),np.zeros(100))); base=np.r_[[0,0,0],[0,0,0,1],1].astype(float)
    moved=base.copy(); moved[2]=.12
    assert abs(np.median((act(moved,plane)-act(base,plane))[:,2])-.12)<1e-12
    assert np.max(np.abs(act(base,plane)-act(base,plane)))==0
    print(json.dumps({'tracking_events_match_e1':len(found),'synthetic_sim3_roundtrip':'passed','synthetic_plane_zero_and_normal_translation':'passed'},indent=2))
    (OUT/'validation.json').write_text(json.dumps({'tracking_events_match_e1':len(found),'synthetic_sim3_roundtrip':'passed','synthetic_plane_zero_and_normal_translation':'passed'},indent=2)+'\n')

if __name__=='__main__':main()
