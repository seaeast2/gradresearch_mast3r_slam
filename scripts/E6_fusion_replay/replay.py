import csv, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
E3=ROOT/'results/E3_fusion/2026-10-28/instrumented/events'
E4=ROOT/'results/E4_backend/2026-10-28/instrumented/events'
E2=ROOT/'results/E2a_overlap/2026-10-28/flow'
OUT=ROOT/'results/E6_fusion_replay/2026-10-28'/ (sys.argv[1] if len(sys.argv)>1 else 'frozen_replay_final')
PAIRS=[(32,35),(31,34),(33,35)]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def stats(x):
 return [float(np.median(x)),float(np.percentile(x,90))]
def plane(x):
 c=x.mean(0); _,_,v=np.linalg.svd(x-c,full_matrices=False); return v[-1], np.linalg.norm(np.ptp((x-c)@v[:2].T,axis=0)), np.abs((x-c)@v[-1])
def act(p,x): return p[7]*Rotation.from_quat(p[3:7]).apply(x)+p[:3]
def save(name,rows):
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
def main():
 OUT.mkdir(parents=True,exist_ok=False)
 rows=[]; states={}; hashes={}; maxerr=0.; maxweight=0.
 for k in range(31,36):
  initfile=next(E3.glob(f'kf{k}_initial_frame*.npz')); init=np.load(initfile); files=sorted(E3.glob(f'kf{k}_update_frame*.npz'),key=lambda p:int(p.stem.split('frame')[-1])); hashes[str(initfile.relative_to(ROOT))]=sha(initfile)
  x=init['xyz'].copy(); w=init['confidence'].copy(); alt=x.copy(); aw=w.copy(); base=x.astype(float); n,span,_=plane(base); ray=base/np.linalg.norm(base,axis=1)[:,None]
  states[k]={}; index=init['pixel_index']; assert len(np.unique(index))==len(index)
  for j,f in enumerate(files):
   d=np.load(f); hashes[str(f.relative_to(ROOT))]=sha(f); assert np.array_equal(index,d['pixel_index'])
   assert np.max(np.abs(x-d['before_xyz']))<2e-6 and np.max(np.abs(w-d['before_weight']))<2e-5
   inp=d['input_xyz']; iw=d['input_weight']; x=(w*x+iw*inp)/(w+iw); w=w+iw
   if j: alt=(aw*alt+iw*inp)/(aw+iw); aw=aw+iw
   err=float(np.max(np.abs(x-d['after_xyz']))); we=float(np.max(np.abs(w-d['after_weight']))); maxerr=max(maxerr,err);maxweight=max(maxweight,we); assert err<3e-6 and we<2e-5
   before=d['before_xyz'].astype(float); after=d['after_xyz'].astype(float); incoming=inp.astype(float)
   for label,point,origin in [('actual_input',incoming,before),('actual_after',after,before),('replay_without_first',alt.astype(float),base),('replay_original',x.astype(float),base)]:
    diff=point-origin; z=diff[:,2]; rd=np.sum(diff*ray,axis=1); nd=diff@n; _,_,res=plane(point)
    rows.append(dict(kf=k,frame=int(d['frame_id']),stage=label,count=len(point),camera_z_signed_median=float(np.median(z)),camera_z_abs_median=stats(abs(z))[0],camera_z_abs_p90=stats(abs(z))[1],initial_ray_signed_median=float(np.median(rd)),initial_ray_abs_p90=stats(abs(rd))[1],initial_normal_signed_median=float(np.median(nd)),initial_normal_abs_p90=stats(abs(nd))[1],plane_p90_over_initial_span=float(np.percentile(res,90)/span),initial_span=span,tracking_valid_match_count=int(d['valid_match'].sum()),input_weight_median=float(np.median(iw)),relative_sim3=' '.join(map(str,d['relative_sim3'].reshape(-1)))))
  states[k]={'pixel':index,'original':x,'excluded':alt,'initial':base,'weight_original':w,'weight_excluded':aw}
  np.savez_compressed(OUT/f'kf{k}_replay.npz',pixel_index=index,original=x,excluded=alt,weight_original=w,weight_excluded=aw)
 save('local_events.csv',rows)
 backend={36:np.load(E4/'backend_036.npz'),52:np.load(E4/'backend_052.npz')}; pairrows=[]; exporterr=0.
 for a,b in PAIRS:
  path=E2/f'kf{a}_{b}_correspondences.npz'; hashes[str(path.relative_to(ROOT))]=sha(path); d=np.load(path)
  valid=np.isfinite(d['world_a']).all(1)&np.isfinite(d['world_b']).all(1); xy_a=d['source_xy'][valid]; xy_b=d['target_xy'][valid]
  lookup=[]
  for k,xy in [(a,xy_a),(b,xy_b)]:
   mapping=np.full(416*512,-1,dtype=int); mapping[states[k]['pixel']]=np.arange(len(states[k]['pixel'])); idx=mapping[xy[:,1]*512+xy[:,0]]; assert (idx>=0).all(); lookup.append(idx)
  wa=d['world_a'][valid].astype(float); n,_,_=plane(wa); n=n if n[2]>=0 else -n
  for step,side in [(36,'pre'),(36,'post'),(52,'post')]:
   pa=backend[step][side+'_poses'][a,0].astype(float); pb=backend[step][side+'_poses'][b,0].astype(float)
   for arm in ('original','exclude_a','exclude_b','exclude_both'):
    ak='excluded' if arm in ('exclude_a','exclude_both') else 'original'; bk='excluded' if arm in ('exclude_b','exclude_both') else 'original'
    xa=states[a][ak][lookup[0]].astype(float); xb=states[b][bk][lookup[1]].astype(float); wa2=act(pa,xa); wb2=act(pb,xb); delta=wb2-wa2; nd=delta@n; tang=np.linalg.norm(delta-nd[:,None]*n,axis=1); xy=np.linalg.norm(delta[:,:2],axis=1); z=np.abs(delta[:,2])
    if step==52 and arm=='original':
     err=max(np.linalg.norm(wa2-wa,axis=1).max(),np.linalg.norm(wb2-d['world_b'][valid],axis=1).max()); exporterr=max(exporterr,float(err)); assert err<2e-5
    row=dict(pair=f'{a}-{b}',step=step,pose=side,arm=arm,candidates_total=len(d['source_xy']),export_support=int(valid.sum()),finite_after=int(np.isfinite(delta).all(axis=1).sum()),normal_x=n[0],normal_y=n[1],normal_z=n[2],normal_signed_median=float(np.median(nd)),normal_signed_p10=float(np.percentile(nd,10)),normal_signed_p90=float(np.percentile(nd,90)))
    for label,v in [('normal_abs',abs(nd)),('tangent',tang),('world_z_abs',z),('world_xy',xy)]: row[label+'_median'],row[label+'_p90']=stats(v)
    pairrows.append(row)
  np.savez_compressed(OUT/f'pair_{a}_{b}_support.npz',source_xy=xy_a,target_xy=xy_b,normal=n)
 save('world_pairs.csv',pairrows)
 # Two one-dimensional synthetic cases exercise the same weighted update and removal logic.
 def fuse(xs,ws):
  x=np.array([xs[0]],dtype=np.float32); w=np.array([ws[0]],dtype=np.float32)
  for y,v in zip(xs[1:],ws[1:]): x=(w*x+v*y)/(w+v);w=w+v
  return float(x[0])
 assert abs(fuse([0,10,0],[1,1,1])-10/3)<1e-6 and fuse([0,0],[1,1])==0 and fuse([0,0,0],[1,1,1])==0
 fig,axs=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
 for ax,pair in zip(axs,PAIRS):
  rs=[r for r in pairrows if r['pair']==f'{pair[0]}-{pair[1]}' and r['step']==52 and r['arm'] in ('original','exclude_both')]
  names=['normal_abs','tangent','world_z_abs','world_xy']; t=np.arange(4)
  for j,r in enumerate(rs): ax.bar(t+(j-.5)*.35,[r[x+'_median'] for x in names],.35,label=r['arm'])
  ax.set_xticks(t,['|normal|','tangent','|Z|','XY'],rotation=25);ax.set_title(f'KF{pair[0]}–{pair[1]} (n={rs[0]["export_support"]})');ax.set_ylabel('world map units');ax.legend();ax.grid(axis='y',alpha=.2)
 fig.savefig(OUT/'world_comparison.png',dpi=170)
 for f in [E4/'backend_036.npz',E4/'backend_052.npz',ROOT/'configs/E6_fusion_replay/protocol.json',Path(__file__)]: hashes[str(f.relative_to(ROOT))]=sha(f)
 manifest={'hashes':hashes,'max_original_replay_xyz_abs':maxerr,'max_original_replay_weight_abs':maxweight,'max_final_export_distance':exporterr,'synthetic_controls':'pass','real_negative_control':'INSUFFICIENT_SUPPORT: no independently verified seam-free ROI','pose_convention':'Sim3 camera/local to world, s R x + t; quaternion xyzw; no metric scale','support':'fixed E3 ROI; E2a candidate and export support only, not independently verified','limitations':'stored subsequent inputs and poses are fixed, not a full tracking rerun; negative control missing'}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(manifest,indent=2))
if __name__=='__main__': main()
