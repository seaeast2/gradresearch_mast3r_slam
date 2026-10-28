import csv, hashlib, json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/E4_backend/2026-10-28/instrumented'
E3=ROOT/'results/E3_fusion/2026-10-28/instrumented'
E2A=ROOT/'results/E2a_overlap/2026-10-28/flow'
E1=ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'
PAIRS=[(32,35),(31,34),(33,35)]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()

def act(pose,x):
    pose=np.asarray(pose).reshape(-1); assert len(pose)==8 and pose[7]>0
    return pose[7]*Rotation.from_quat(pose[3:7]).apply(x)+pose[:3]

def inv_act(pose,x):
    pose=np.asarray(pose).reshape(-1)
    return Rotation.from_quat(pose[3:7]).inv().apply((x-pose[:3])/pose[7])

def normal(x):
    _,_,v=np.linalg.svd(x-x.mean(0),full_matrices=False)
    n=v[-1]; return n if n[np.argmax(np.abs(n))]>0 else -n

def points(k,xy,kind):
    if kind=='raw':
        f=next((E3/'events').glob(f'kf{k}_initial_frame*.npz')); d=np.load(f); xyz=d['xyz']
    else:
        files=sorted((E3/'events').glob(f'kf{k}_update_frame*.npz'),key=lambda p:int(p.stem.split('frame')[-1])); d=np.load(files[-1]); xyz=d['after_xyz']
    index=np.full(416*512,-1,np.int32); index[d['pixel_index']]=np.arange(len(d['pixel_index']))
    lookup=index[xy[:,1]*512+xy[:,0]]; assert (lookup>=0).all()
    return xyz[lookup].astype(float)

def main():
    event_files=sorted((OUT/'events').glob('backend_*.npz'))
    assert [int(f.stem.split('_')[-1]) for f in event_files]==list(range(30,53))
    events={int(f.stem.split('_')[-1]):np.load(f) for f in event_files}
    for k in range(31,36):
        init=np.load(next((E3/'events').glob(f'kf{k}_initial_frame*.npz')))
        last=sorted((E3/'events').glob(f'kf{k}_update_frame*.npz'),key=lambda p:int(p.stem.split('frame')[-1]))[-1]
        frozen=np.load(last)['after_xyz']
        assert np.array_equal(events[k][f'pre_xyz_{k}'],init['xyz'])
        for event in range(36,53):
            assert np.array_equal(events[event][f'pre_xyz_{k}'],frozen)
            assert np.array_equal(events[event][f'post_xyz_{k}'],frozen)
    revisions=[]
    prior_edges=set()
    for step,d in events.items():
        edges=set(zip(d['pre_ii'].tolist(),d['pre_jj'].tolist())); new=edges-prior_edges
        for k in range(31,min(36,step+1)):
            pre=d['pre_poses'][k,0].astype(float); post=d['post_poses'][k,0].astype(float)
            rot=(Rotation.from_quat(post[3:7])*Rotation.from_quat(pre[3:7]).inv()).magnitude()
            revisions.append({'backend_kf':step,'kf':k,'edges':len(edges),'new_edges':len(new),
                              'new_nonconsecutive_edges':sum(abs(i-j)>1 for i,j in new),
                              'translation_delta_world_units':float(np.linalg.norm(post[:3]-pre[:3])),
                              'rotation_delta_deg':float(np.degrees(rot)), 'delta_log_scale':float(np.log(post[7]/pre[7]))})
        prior_edges=edges
    pairrows=[]; gauges=[]; final_checks=[]
    for ka,kb in PAIRS:
        data=np.load(E2A/f'kf{ka}_{kb}_correspondences.npz')
        valid=np.isfinite(data['world_a']).all(1)&np.isfinite(data['world_b']).all(1)
        xa=data['source_xy'][valid]; xb=data['target_xy'][valid]
        refn=normal(data['world_a'][valid].astype(float))
        for kind in ('raw','fused'):
            a=points(ka,xa,kind); b=points(kb,xb,kind)
            for step in range(max(ka,kb),53):
                d=events[step]; out={'pair':f'{ka}-{kb}','kind':kind,'backend_kf':step,'n_points':len(a)}
                for side in ('pre','post'):
                    pa=d[f'{side}_poses'][ka,0]; pb=d[f'{side}_poses'][kb,0]
                    wa=act(pa,a); wb=act(pb,b); diff=(wb-wa)@refn
                    na=normal(wa); nb=normal(wb)
                    out[f'{side}_signed_median']=float(np.median(diff))
                    out[f'{side}_signed_p10']=float(np.percentile(diff,10)); out[f'{side}_signed_p90']=float(np.percentile(diff,90))
                    out[f'{side}_abs_median']=float(np.median(np.abs(diff)))
                    out[f'{side}_normal_angle_deg']=float(np.degrees(np.arccos(np.clip(abs(na@nb),0,1))))
                    out[f'{side}_symmetric_point_plane_median']=float((np.median(np.abs((wa-wb.mean(0))@nb))+np.median(np.abs((wb-wa.mean(0))@na)))/2)
                    if step==52 and side=='post' and kind=='fused':
                        ea=np.linalg.norm(wa-data['world_a'][valid],axis=1); eb=np.linalg.norm(wb-data['world_b'][valid],axis=1)
                        final_checks.append({'pair':f'{ka}-{kb}','max_export_error':float(max(ea.max(),eb.max()))})
                        assert max(ea.max(),eb.max())<2e-5
                    if step==36 and side=='pre':
                        # x'=q*x, s'=s/q is the same world map (translation unchanged).
                        q=2.3; pp=pa.astype(float).copy(); pp[7]/=q
                        change=float(np.max(np.abs(act(pp,q*a)-wa)))
                        roundtrip=float(np.max(np.abs(inv_act(pa,wa)-a)))
                        assert change<1e-10 and roundtrip<1e-10
                        gauges.append({'pair':f'{ka}-{kb}','kind':kind,'reparameterization_max_abs':change,'roundtrip_max_abs':roundtrip})
                out['change_signed_median']=out['post_signed_median']-out['pre_signed_median']
                out['change_abs_median']=out['post_abs_median']-out['pre_abs_median']
                pairrows.append(out)
    for name,data in [('backend_pose_revisions.csv',revisions),('pair_seams.csv',pairrows)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=data[0].keys()); w.writeheader(); w.writerows(data)
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),constrained_layout=True)
    for ax,(ka,kb) in zip(axes,PAIRS):
        ax.axvspan(max(ka,kb)-.25,35.5,color='gray',alpha=.12,label='future fused map replay')
        for kind in ('raw','fused'):
            r=[x for x in pairrows if x['pair']==f'{ka}-{kb}' and x['kind']==kind]
            ax.plot([max(ka,kb)]+[x['backend_kf'] for x in r],[r[0]['pre_signed_median']]+[x['post_signed_median'] for x in r],marker='.',label=kind)
        ax.axhline(0,color='black',lw=.5); ax.set(title=f'KF{ka}–{kb}',xlabel='backend newest KF',ylabel='signed median separation (map units)'); ax.grid(alpha=.3);ax.legend()
    fig.suptitle('First point is pre-solve; others post-solve. Gray: fused map not yet frozen')
    fig.savefig(OUT/'backend_frozen_overlap.png',dpi=170)
    hashes={'e1_ply':sha(E1/'output/mapping.ply'),'e4_ply':sha(OUT/'output/mapping.ply'), 'e1_traj':sha(E1/'output/mapping.txt'),'e4_traj':sha(OUT/'output/mapping.txt'),
            'e1_provenance':sha(E1/'provenance.npz'),'e4_provenance':sha(OUT/'provenance.npz')}
    manifest={'events':len(events),'comparison_events_per_pair':'from later keyframe creation through KF52 (18 or 19 solves)','hashes':hashes,'frozen_roi_equals_e3':True,
              'final_export_checks':final_checks,'gauge_checks':gauges,'correspondence':'E2a candidates, not pixel ground truth',
              'fixed_normal':'source E1 final export PCA plane, orientation set by largest absolute coordinate; common for all steps of one pair',
              'frozen_map_note':'for early poses frozen raw/fused maps are a controlled replay, not actual historical geometry',
              'protocol_sha256':sha(ROOT/'configs/E4_backend/protocol.json'),'probe_sha256':sha(ROOT/'scripts/E4_backend/e4_backend_probe.py'),
              'main_overlay_sha256':sha(OUT/'main_e4.py'), 'upstream_main_sha256':sha(ROOT/'thirdparty/MASt3R-SLAM/main.py'),
              'e3_initial_and_frozen_sha256':{str(k):{'initial':sha(next((E3/'events').glob(f'kf{k}_initial_frame*.npz'))),
                  'frozen':sha(sorted((E3/'events').glob(f'kf{k}_update_frame*.npz'),key=lambda p:int(p.stem.split('frame')[-1]))[-1])} for k in range(31,36)},
              'correspondence_sha256':{f'{a}-{b}':sha(E2A/f'kf{a}_{b}_correspondences.npz') for a,b in PAIRS},
              'input_csv_sha256':sha(ROOT/'data/HKairport01/mapping_frames.csv'),
              'config_sha256':sha(ROOT/'configs/E0_environment_preparation/low_vram_base.yaml'),
              'checkpoint_sha256':sha(ROOT/'thirdparty/MASt3R-SLAM/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth'),
              'analysis_sha256':sha(Path(__file__))}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
