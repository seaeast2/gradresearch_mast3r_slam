import csv,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/E5_timeline/2026-10-28/timeline'
E1=ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'
E3=ROOT/'results/E3_fusion/2026-10-28/instrumented'
E4=ROOT/'results/E4_backend/2026-10-28/instrumented'

def main():
    timeline=list(csv.DictReader((OUT/'R4_timeline.csv').open())); events=list(csv.DictReader((OUT/'R4_roi_events.csv').open()))
    original=list(csv.DictReader((E1/'tracking_timeline.csv').open())); seams=list(csv.DictReader((E4/'pair_seams.csv').open()))
    assert len(timeline)==len(original)==240 and len(events)==23
    for row,old in zip(timeline,original):
        assert row['frame']==old['frame_index'] and row['tracking_success']==old['tracking_success'] and row['new_keyframe']==old['new_keyframe'] and row['timestamp']==old['timestamp']
    for r in events:
        k=int(r['kf']); f=int(r['frame']); z=np.load(OUT/f'kf{k}_frame{f}_flow.npz'); e=np.load(E3/'events'/f'kf{k}_update_frame{f}.npz')
        xy=z['source_xy']; pixel=xy[:,1]*512+xy[:,0]; index=np.full(416*512,-1,int); index[e['pixel_index']]=np.arange(len(e['pixel_index'])); j=index[pixel];assert (j>=0).all()
        q=np.sqrt(e['descriptor_conf_frame']*e['descriptor_conf_kf']); valid=e['valid_match'].astype(bool)&(q>1.5)&(e['frame_self_conf']>0)&(e['before_weight'].reshape(-1)/int(e['before_N'])>0)
        assert np.array_equal(valid[j],z['mast3r_valid']); chosen=z['flow_candidate'];assert np.all(z['flow_fb'][chosen]<=1.0) and np.all(z['patch_ncc'][chosen]>=.8)
        assert int(chosen.sum())==int(r['flow_candidates']) and int((chosen&valid[j]).sum())==int(r['flow_mast3r_valid_intersection'])
    gates=list(csv.DictReader((OUT/'R4_first_match_gates.csv').open()))
    for r in gates:
        assert r['match_mask_exact']=='True' and r['match_indices_exact']=='True'
        d=np.load(OUT/f"kf{r['kf']}_frame{r['frame']}_match_gates.npz");assert np.array_equal(d['match_valid'],d['projection_pass']&d['distance_pass']);assert int(d['match_valid'].sum())==int(r['both_pass'])
    prov=np.load(E1/'provenance.npz'); ids=prov['frame_ids']
    for r in seams:
        step=int(r['backend_kf'])
        if r['kind']!='fused' or step<36:continue
        frame=int(ids[step]); outrow=timeline[frame]; assert abs(float(outrow[f"pair_{r['pair']}_backend_abs_change"])-float(r['change_abs_median']))<1e-12
    result={'timeline_rows_checked':len(timeline),'roi_event_masks_checked':len(events),'gate_replays_exact':len(gates),'backend_step_to_frame':'validated for all fused pairs at KF36-52', 'limitations':'does not prove the image matches are correct or establish causality'}
    (OUT/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
