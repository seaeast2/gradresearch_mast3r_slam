"""Describe E2a candidate correspondence residuals along world axes and local plane."""
import csv, hashlib, json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'results/E2a_overlap/2026-10-28/flow'
OUT=ROOT/'results/E5_timeline/2026-10-28/axis_baseline'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    OUT.mkdir(parents=True,exist_ok=True); pairs=[(32,35),(31,34),(33,35)]; rows=[]; allvals=[]; roundtrips={}
    event_dir=ROOT/'results/E3_fusion/2026-10-28/instrumented/events'
    raw_dir=ROOT/'results/E2_raw_pointmap/2026-10-28/raw_pairs'
    for k in range(31,36):
        event=sorted(event_dir.glob(f'kf{k}_update_frame*.npz'),key=lambda p:int(p.stem.split('frame')[-1]))[0]
        e=np.load(event); raw=np.load(raw_dir/f'kf{k}_next_cross.npz')
        assert np.array_equal(e['pixel_index'],raw['pixel_index'])
        pose=e['relative_sim3'].reshape(-1).astype(float); assert pose[7]>0
        recovered=Rotation.from_quat(pose[3:7]).inv().apply((e['input_xyz'].astype(float)-pose[:3])/pose[7])
        error=np.linalg.norm(recovered-raw['xyz'],axis=1)
        assert error.max()<1e-5
        roundtrips[str(k)]={'max_error':float(error.max()),'median_error':float(np.median(error)),
                            'event_sha256':sha(event),'raw_sha256':sha(raw_dir/f'kf{k}_next_cross.npz')}
    for a,b in pairs:
        path=SOURCE/f'kf{a}_{b}_correspondences.npz';d=np.load(path)
        wa=d['world_a'].astype(float);wb=d['world_b'].astype(float);valid=np.isfinite(wa).all(1)&np.isfinite(wb).all(1)
        wa=wa[valid];wb=wb[valid]; delta=wb-wa
        _,_,v=np.linalg.svd(wa-wa.mean(axis=0),full_matrices=False); n=v[-1]
        if n[2]<0:n=-n
        normal=delta@n;tangent=np.linalg.norm(delta-normal[:,None]*n,axis=1)
        xy=np.linalg.norm(delta[:,:2],axis=1);z=np.abs(delta[:,2])
        assert np.allclose((delta*delta).sum(axis=1),normal**2+tangent**2,atol=1e-12)
        row={'pair':f'{a}-{b}','candidate_count':len(wa),'normal_x':float(n[0]),'normal_y':float(n[1]),'normal_z':float(n[2]),
             'normal_to_world_z_deg':float(np.degrees(np.arccos(np.clip(n[2],-1,1)))),
             'dx_signed_median':float(np.median(delta[:,0])),'dy_signed_median':float(np.median(delta[:,1])),'dz_signed_median':float(np.median(delta[:,2])),
             'abs_z_median':float(np.median(z)),'abs_z_p90':float(np.percentile(z,90)),
             'xy_distance_median':float(np.median(xy)),'xy_distance_p90':float(np.percentile(xy,90)),
             'normal_signed_median':float(np.median(normal)),'normal_abs_median':float(np.median(np.abs(normal))),
             'normal_abs_p90':float(np.percentile(np.abs(normal),90)),'tangent_distance_median':float(np.median(tangent)),
             'tangent_distance_p90':float(np.percentile(tangent,90)),'source_sha256':sha(path)}
        rows.append(row);allvals.append((f'{a}–{b}',xy,z,tangent,np.abs(normal)))
    with (OUT/'axis_baseline.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    fig,axes=plt.subplots(1,3,figsize=(12,4),constrained_layout=True)
    for ax,(label,xy,z,tangent,n) in zip(axes,allvals):
        vals=[xy,z,tangent,n]; med=[np.median(v) for v in vals];p90=[np.percentile(v,90) for v in vals]
        ax.bar(range(4),med,color=['#7498c5','#b66f5d','#769fb4','#d39567'])
        ax.scatter(range(4),p90,color='black',s=20,label='p90')
        ax.set_xticks(range(4),['XY norm','|Z|','tangent','|normal|'],rotation=20);ax.set_title(f'KF{label}');ax.set_ylabel('distance (map units)');ax.grid(axis='y',alpha=.25);ax.legend()
    fig.suptitle('Candidate correspondence residuals; medians and p90; not metric error')
    fig.savefig(OUT/'axis_baseline.png',dpi=170)
    (OUT/'manifest.json').write_text(json.dumps({'script_sha256':sha(Path(__file__)),'rows':rows,'first_cross_inverse_transform_check':roundtrips,'status':'exploratory, based on E2a optical-flow candidates, no metric or ground-truth accuracy','normal':'PCA of finite source points; sign chosen toward +world Z','note':'Screen horizontal/vertical/view depth not established by screenshot'},indent=2)+'\n')
    print(json.dumps(rows,indent=2))

if __name__=='__main__':main()
