import csv,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/E7b_geometry_diagnostic/2026-10-28/e7b_amtown_backend';E7=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline';E7A=ROOT/'results/E7a_overlap_support/2026-10-28/e7a_amtown_probe';PAIRS=[(8,11),(9,12),(10,12)]; events=sorted((OUT/'events').glob('backend_*.npz'));files={int(p.stem.split('_')[-1]):p for p in events};assert (OUT/'exit_code.txt').read_text().strip()=='0'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def act(p,x):return p[7]*Rotation.from_quat(p[3:7]).apply(x)+p[:3]
def plane(x):
 c=x.mean(axis=0);_,sv,v=np.linalg.svd(x-c,full_matrices=False);span=np.linalg.norm(np.ptp((x-c)@v[:2].T,axis=0));return c,v[-1],sv,span,abs((x-c)@v[-1])
def idx(k,xy):
 d=np.load(E7A/f'kf{k}_replay.npz');index=np.full(416*512,-1,np.int64);index[d['index']]=np.arange(len(d['index']));q=index[xy[:,1]*512+xy[:,0]];assert (q>=0).all();return d,q
def raw(k,index):
 f=next((E7A/'events').glob(f'kf{k}_initial_frame*.npz'));d=np.load(f);assert np.array_equal(d['pixel_index'],index);return d['xyz'].astype(float)
def stats(v):return float(np.median(v)),float(np.percentile(v,90))
def write(name,rows):
 keys=sorted(set().union(*(r.keys() for r in rows)))
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
assert all(k in files for k in range(13,51));final=np.load(files[50]);prev=np.load(files[13]); assert final['post_poses'].shape[0]==51
final_poses=final['post_poses'][:,0,:].astype(float);e7a_poses=np.load(E7A/'final_sim3.npy').astype(float);pose_err=float(np.max(abs(final_poses-e7a_poses)));assert pose_err<2e-6
local=[];world=[];gauge=[]; plotdata=[];max_reproduction=0.
for a,b in PAIRS:
 support=np.load(E7A/f'road_{a}_{b}_common_support.npz');keep=support['common'];xya=support['source_xy'][keep];xyb=support['target_xy'][keep];assert len(xya)>=3
 maps=[]
 for k,xy in ((a,xya),(b,xyb)):
  d,ii=idx(k,xy);xx=raw(k,d['index'])[ii];finalx=d['original'][ii].astype(float);_,nr,sr,span,rr=plane(xx);_,nf,sf,_,rf=plane(finalx);angle=np.degrees(np.arccos(np.clip(abs(nr@nf),0,1)))
  for label,sv,res in [('initial',sr,rr),('fused',sf,rf)]:
   local.append({'pair':f'{a}-{b}','kf':k,'stage':label,'points':len(ii),'initial_span':span,'plane_abs_median_over_initial_span':float(np.median(res)/span),'plane_abs_p90_over_initial_span':float(np.percentile(res,90)/span),'plane_abs_rmse_over_initial_span':float(np.sqrt(np.mean(res**2))/span),'normal_angle_initial_final_deg':float(angle),'svd_second_first':float(sv[1]/sv[0]),'svd_third_second':float(sv[2]/sv[1]),'image_x_span':int(np.ptp(xy[:,0])),'image_y_span':int(np.ptp(xy[:,1]))})
  maps.append((xx,finalx))
 wa=act(final_poses[a],maps[0][1]);center,n,_,_,_=plane(wa);n=n if n[2]>=0 else -n
 exp=np.load(E7A/f'road_{a}_{b}_common_support.npz');assert np.all(exp['common']==keep)
 for k in (a,b):
  p=final_poses[k];sample=maps[0 if k==a else 1][1];wx=act(p,sample);back=Rotation.from_quat(p[3:7]).inv().apply((wx-p[:3])/p[7]);q=2.3;pp=p.copy();pp[7]/=q
  err=float(np.max(np.abs(back-sample)));g=float(np.max(np.abs(act(pp,q*sample)-wx)));assert err<1e-10 and g<1e-10;gauge.append({'pair':f'{a}-{b}','kf':k,'roundtrip':err,'gauge':g})
 for step in range(13,51):
  d=np.load(files[step]);assert len(d['pre_poses'])>b
  for side in ('pre','post'):
   pose=d[side+'_poses'][:,0,:].astype(float)
   for kind,index in [('initial',0),('fused',1)]:
    pa=act(pose[a],maps[0][index]);pb=act(pose[b],maps[1][index]);delta=pb-pa;dn=delta@n;dt=np.linalg.norm(delta-dn[:,None]*n,axis=1);xy=np.linalg.norm(delta[:,:2],axis=1);z=abs(delta[:,2]);r={'pair':f'{a}-{b}','step':step,'side':side,'map':kind,'points':len(pa),'normal_signed_median':float(np.median(dn)),'normal_signed_p10':float(np.percentile(dn,10)),'normal_signed_p90':float(np.percentile(dn,90))}
    for key,v in [('normal_abs',abs(dn)),('tangent',dt),('z_abs',z),('xy',xy)]:r[key+'_median'],r[key+'_p90']=stats(v)
    world.append(r)
    if step==50 and side=='post' and kind=='fused':
     original=np.load(E7A/'analysis.json') if False else None
     error=max(np.max(abs(pa-act(e7a_poses[a],maps[0][1]))),np.max(abs(pb-act(e7a_poses[b],maps[1][1]))));max_reproduction=max(max_reproduction,float(error));assert error<2e-5
 write_dummy=0
write('local_planes.csv',local);write('backend_world_pairs.csv',world)
fig,axs=plt.subplots(1,3,figsize=(14,4),constrained_layout=True)
for ax,(a,b) in zip(axs,PAIRS):
 for kind in ('initial','fused'):
  z=[r for r in world if r['pair']==f'{a}-{b}' and r['map']==kind and r['side']=='post'];ax.plot([r['step'] for r in z],[r['normal_signed_median'] for r in z],label=kind)
 ax.axhline(0,color='black',lw=.5);ax.set(title=f'KF{a}–{b}',xlabel='backend newest KF',ylabel='signed separation (map units)');ax.grid(alpha=.2);ax.legend()
fig.suptitle('Fixed candidate support and fixed maps: pose replay, not physical ground truth');fig.savefig(OUT/'backend_pair_replay.png',dpi=160)
parity={}
for f in ['output/mapping.ply','output/mapping.txt','provenance.npz']:
 parity[f]={'e7':sha(E7/f),'e7b':sha(OUT/f),'equal':sha(E7/f)==sha(OUT/f)}
a=[l for l in (E7/'run.log').read_text().splitlines() if l.startswith(('E1_TRACK ','E1_RELOC '))];b=[l for l in (OUT/'run.log').read_text().splitlines() if l.startswith(('E1_TRACK ','E1_RELOC '))];assert a==b and len(a)==239
report={'events':len(events),'event_13_50_complete':True,'tracking_parity':True,'output_parity':parity,'final_pose_e7a_max_abs':pose_err,'final_candidate_pose_e7a_max_abs':max_reproduction,'gauge_checks':gauge,'protocol_sha256':sha(ROOT/'configs/E7b_geometry_diagnostic/protocol.json'),'script_sha256':sha(Path(__file__)),'backend_probe_sha256':sha(ROOT/'scripts/E7b_geometry_diagnostic/backend_probe.py'),'event_hashes':{str(k):sha(v) for k,v in files.items()},'limitations':['E7a LK candidate support is not independently verified','raw initial and fused points reuse E7a capture; per-solve map snapshots not taken in E7b, so this is frozen map pose replay, not proof of historical actual map','normal from narrow candidate strip','image calibration physical validity unresolved']}
(OUT/'analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'pose_error':pose_err,'output_parity':parity,'local':local,'summary':[r for r in world if r['step'] in (13,50) and (r['side']=='post' or r['step']==13 and r['side']=='pre') and r['map']=='fused']},indent=2))
