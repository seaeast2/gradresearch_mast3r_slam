import csv, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'results/E7_validation/2026-10-28/e7_amtown_probe'; events=OUT/'events'; spec=json.loads((ROOT/'configs/E7_validation/roi.json').read_text()); rows=[]; validations=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(1048576),b''):h.update(x)
 return h.hexdigest()
def plane(x):
 x=x.astype(float); _,_,v=np.linalg.svd(x-x.mean(0),full_matrices=False); span=np.linalg.norm(np.ptp((x-x.mean(0))@v[:2].T,axis=0)); return v[-1],span,np.abs((x-x.mean(0))@v[-1])
for k in spec['keyframes']:
 initfile=next(events.glob(f'kf{k}_initial_frame*.npz'),None); files=sorted(events.glob(f'kf{k}_update_frame*.npz'),key=lambda p:int(p.stem.split('frame')[-1]))
 if not initfile or not files:
  validations.append({'kf':k,'status':'INSUFFICIENT_SUPPORT','reason':'missing initialization or update'});continue
 init=np.load(initfile);x=init['xyz'].copy();w=init['confidence'].copy();alt=x.copy();aw=w.copy();base=x.astype(float);n,span,_=plane(base);ray=base/np.linalg.norm(base,axis=1)[:,None];maxerr=0;maxw=0
 for j,f in enumerate(files):
  d=np.load(f); assert np.array_equal(init['pixel_index'],d['pixel_index']);assert np.max(abs(x-d['before_xyz']))<2e-6
  x=(w*x+d['input_weight']*d['input_xyz'])/(w+d['input_weight']);w=w+d['input_weight']
  if j:alt=(aw*alt+d['input_weight']*d['input_xyz'])/(aw+d['input_weight']);aw=aw+d['input_weight']
  maxerr=max(maxerr,float(np.max(abs(x-d['after_xyz']))));maxw=max(maxw,float(np.max(abs(w-d['after_weight']))));assert maxerr<3e-6 and maxw<2e-5
  before=d['before_xyz'].astype(float); after=d['after_xyz'].astype(float);delta=after-before; q=np.sqrt(d['descriptor_conf_frame']*d['descriptor_conf_kf']);valid=d['valid_match'] & (q>1.5)&(d['frame_self_conf']>0)&(d['before_weight'].reshape(-1)/int(d['before_N'])>0)
  _,_,res=plane(after);rows.append({'kf':k,'frame':int(d['frame_id']),'update':j+1,'roi_count':len(x),'valid_tracking_count':int(valid.sum()),'valid_tracking_fraction':float(valid.mean()),'input_weight_fraction_median':float(np.median(d['input_weight']/(d['before_weight']+d['input_weight']))),'normal_shift_median_over_initial_span':float(np.median(delta@n)/span),'camera_z_shift_median':float(np.median(delta[:,2])),'ray_shift_median':float(np.median(np.sum(delta*ray,axis=1))),'after_plane_p90_over_initial_span':float(np.percentile(res,90)/span)})
 diff=alt.astype(float)-x.astype(float);_,_,r0=plane(x);_,_,r1=plane(alt)
 np.savez_compressed(OUT/f'kf{k}_replay.npz',pixel_index=init['pixel_index'],original=x,excluded=alt,weight_original=w,weight_excluded=aw,n_original=len(files)+1,n_excluded=len(files))
 validations.append({'kf':k,'status':'OK','updates':len(files),'first_frame':rows[-len(files)]['frame'],'count':len(x),'max_replay_xyz':maxerr,'max_replay_weight':maxw,'final_excluded_minus_original_camera_z_median':float(np.median(diff[:,2])),'final_excluded_minus_original_ray_median':float(np.median(np.sum(diff*ray,axis=1))),'final_excluded_minus_original_normal_median_over_span':float(np.median(diff@n)/span),'original_plane_p90_over_span':float(np.percentile(r0,90)/span),'excluded_plane_p90_over_span':float(np.percentile(r1,90)/span)})
if rows:
 with (OUT/'events_summary.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 fig,ax=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
 for k in spec['keyframes']:
  rr=[r for r in rows if r['kf']==k]
  if rr:
   ax[0].plot([r['update'] for r in rr],[r['valid_tracking_fraction']*100 for r in rr],marker='o',label=f'KF{k}')
   ax[1].plot([r['update'] for r in rr],[abs(r['normal_shift_median_over_initial_span'])*100 for r in rr],marker='o',label=f'KF{k}')
 ax[0].set(xlabel='update',ylabel='valid tracking (%)');ax[1].set(xlabel='update',ylabel='absolute median initial-normal shift / initial span (%)')
 for a in ax:a.grid(alpha=.3);a.legend()
 fig.savefig(OUT/'events_summary.png',dpi=160)
base=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline';files=['output/mapping.ply','output/mapping.txt','provenance.npz'];parity={f:{'baseline':sha(base/f),'probe':sha(OUT/f),'equal':sha(base/f)==sha(OUT/f)} for f in files if (base/f).exists() and (OUT/f).exists()}
manifest={'validation':validations,'parity':parity,'protocol_sha256':sha(ROOT/'configs/E7_validation/protocol.json'),'roi_sha256':sha(ROOT/'configs/E7_validation/roi.json'),'analysis_sha256':sha(Path(__file__)),'inputs_csv_sha256':sha(ROOT/'data/AMtown01/mapping_frames.csv'),'event_sha256':{f.name:sha(f) for f in sorted(events.glob('*.npz'))},'limitations':'RGB ROI exploratory; no independently verified common physical support or normal-region control; map-unit comparisons do not establish accuracy.'}
(OUT/'analysis.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'validation':validations,'parity':parity},indent=2))
