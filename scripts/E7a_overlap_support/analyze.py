"""Replay E7a capture and inspect fixed RGB candidate support; not independent GT."""
import csv,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from plyfile import PlyData
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'configs/E7a_overlap_support';PRE=ROOT/'results/E7a_overlap_support/2026-10-28/preflight';OUT=ROOT/'results/E7a_overlap_support/2026-10-28/e7a_amtown_probe';E7=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline';REG=json.loads((P/'regions.json').read_text());H,W=416,512

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def act(p,x):return p[7]*Rotation.from_quat(p[3:7]).apply(x)+p[:3]
def med90(v):return float(np.median(v)),float(np.percentile(v,90))
def write_csv(path,rows):
 fields=sorted(set().union(*(r.keys() for r in rows)))
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
assert (OUT/'exit_code.txt').read_text().strip()=='0'
state={};checks=[]; hashlist={}
for k in REG['keyframes']:
 events=OUT/'events';initial=next(events.glob(f'kf{k}_initial_frame*.npz'));i=np.load(initial);fs=sorted(events.glob(f'kf{k}_update_frame*.npz'),key=lambda f:int(f.stem.split('frame')[-1]));assert fs
 x=i['xyz'].copy();w=i['confidence'].copy();alt=x.copy();aw=w.copy();maxx=maxw=0.
 for j,f in enumerate(fs):
  d=np.load(f);assert np.array_equal(i['pixel_index'],d['pixel_index']);assert np.max(abs(x-d['before_xyz']))<2e-6 and np.max(abs(w-d['before_weight']))<2e-5
  x=(w*x+d['input_weight']*d['input_xyz'])/(w+d['input_weight']);w=w+d['input_weight']
  if j:alt=(aw*alt+d['input_weight']*d['input_xyz'])/(aw+d['input_weight']);aw=aw+d['input_weight']
  maxx=max(maxx,float(np.max(abs(x-d['after_xyz']))));maxw=max(maxw,float(np.max(abs(w-d['after_weight']))));assert maxx<3e-6 and maxw<2e-5
  hashlist[str(f.relative_to(ROOT))]=sha(f)
 hashlist[str(initial.relative_to(ROOT))]=sha(initial);state[k]=dict(index=i['pixel_index'],original=x,excluded=alt,weight_original=w,weight_excluded=aw,n_original=len(fs)+1,n_excluded=len(fs));np.savez_compressed(OUT/f'kf{k}_replay.npz',**state[k]);checks.append({'kf':k,'count':len(x),'updates':len(fs),'max_xyz_abs':maxx,'max_weight_abs':maxw})
poses=np.load(OUT/'final_sim3.npy');prov=np.load(OUT/'provenance.npz');ply=PlyData.read(OUT/'output/mapping.ply')['vertex'].data;assert len(ply)==len(prov['kf_id']);
def indices(k,xy):
 m=np.full(W*H,-1,np.int64);m[state[k]['index']]=np.arange(len(state[k]['index']));p=m[xy[:,1]*W+xy[:,0]];assert (p>=0).all();return p
def export(k,xy):
 sel=np.flatnonzero(prov['kf_id']==k);p=np.full(H*W,-1,np.int64);p[prov['pixel_index'][sel]]=sel;return p[xy[:,1]*W+xy[:,0]]
rows=[];support=[]
for region in ('road','roof'):
 for a,b in REG['pairs']:
  p=PRE/f'{region}_{a}_{b}_tracks.npz';d=np.load(p);xy=d['source_xy'];uv=d['target_xy'];ia=indices(a,xy);ib=indices(b,uv);ea=export(a,xy);eb=export(b,uv);orig=(ea>=0)&(eb>=0)
  va=(state[a]['weight_excluded'][ia,0]/state[a]['n_excluded']>1.5);vb=(state[b]['weight_excluded'][ib,0]/state[b]['n_excluded']>1.5);common=orig&va&vb
  finite=np.isfinite(state[a]['original'][ia]).all(1)&np.isfinite(state[b]['original'][ib]).all(1)&np.isfinite(state[a]['excluded'][ia]).all(1)&np.isfinite(state[b]['excluded'][ib]).all(1);common &= finite
  report={'region':region,'pair':f'{a}-{b}','candidates':len(xy),'original_export_both':int(orig.sum()),'excluded_a_valid_among_original':int((orig&va).sum()),'excluded_b_valid_among_original':int((orig&vb).sum()),'fixed_common_count':int(common.sum()),'verified_correspondences':'UNVERIFIED','negative_control':'INVALID_MULTI_FACE' if region=='roof' else 'NOT_A_CONTROL'}
  if orig.any():
   qa=np.column_stack([ply[c][ea[orig]] for c in 'xyz']);qb=np.column_stack([ply[c][eb[orig]] for c in 'xyz']);wa=act(poses[a],state[a]['original'][ia[orig]]);wb=act(poses[b],state[b]['original'][ib[orig]]);err=float(max(np.linalg.norm(wa-qa,axis=1).max(),np.linalg.norm(wb-qb,axis=1).max()));assert err<2e-5;report['export_max_distance']=err
  support.append(report)
  np.savez_compressed(OUT/f'{region}_{a}_{b}_common_support.npz',source_xy=xy,target_xy=uv,original_export_both=orig,common=common)
  if region!='road' or common.sum()<3:continue
  aa=state[a]['original'][ia[common]].astype(float);bb=state[b]['original'][ib[common]].astype(float);wa=act(poses[a],aa);wb=act(poses[b],bb);center=wa.mean(0);_,sv,v=np.linalg.svd(wa-center,full_matrices=False);n=v[-1];n=n if n[2]>=0 else -n
  for arm,ka,kb in [('original','original','original'),('exclude_a','excluded','original'),('exclude_b','original','excluded')]:
   wa=act(poses[a],state[a][ka][ia[common]].astype(float));wb=act(poses[b],state[b][kb][ib[common]].astype(float));delta=wb-wa;dn=delta@n;dt=np.linalg.norm(delta-dn[:,None]*n,axis=1)
   row={'pair':f'{a}-{b}','arm':arm,'n':int(common.sum()),'source_xy_width':int(np.ptp(xy[common,0])),'source_xy_height':int(np.ptp(xy[common,1])),'source_svd_second_first':float(sv[1]/sv[0]),'source_svd_third_second':float(sv[2]/sv[1]),'normal_x':n[0],'normal_y':n[1],'normal_z':n[2],'normal_signed_median':float(np.median(dn)),'normal_signed_p10':float(np.percentile(dn,10)),'normal_signed_p90':float(np.percentile(dn,90))}
   for label,vv in [('normal_abs',abs(dn)),('tangent',dt),('world_z_abs',abs(delta[:,2])),('world_xy',np.linalg.norm(delta[:,:2],axis=1))]:row[label+'_median'],row[label+'_p90']=med90(vv)
   rows.append(row)
write_csv(OUT/'candidate_geometry.csv',rows);write_csv(OUT/'support.csv',support)
fig,axs=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
for ax,(a,b) in zip(axs,REG['pairs']):
 rr=[r for r in rows if r['pair']==f'{a}-{b}']; labels=['normal_abs','tangent','world_z_abs','world_xy'];x=np.arange(len(labels))
 for j,r in enumerate(rr):ax.bar(x+(j-1)*.25,[r[t+'_median'] for t in labels],width=.25,label=r['arm'])
 ax.set_xticks(x,['|normal|','tangent','|Z|','XY'],rotation=25);ax.set_title(f'KF{a}–{b} (n={rr[0]["n"] if rr else 0})');ax.set_ylabel('world map units');ax.grid(axis='y',alpha=.2);ax.legend(fontsize=8)
fig.suptitle('Exploratory candidates; correspondences not independently verified');fig.savefig(OUT/'candidate_geometry.png',dpi=160)
parity={}
for f in ['output/mapping.ply','output/mapping.txt','provenance.npz']:
 parity[f]={'e7_baseline':sha(E7/f),'e7a':sha(OUT/f),'equal':sha(E7/f)==sha(OUT/f)}
base=[x for x in (E7/'run.log').read_text().splitlines() if x.startswith(('E1_TRACK ','E1_RELOC '))];probe=[x for x in (OUT/'run.log').read_text().splitlines() if x.startswith(('E1_TRACK ','E1_RELOC '))];assert base==probe and len(base)==239
manifest={'replay_checks':checks,'parity':parity,'tracking_events_equal':True,'event_sha256':hashlist,'protocol_sha256':sha(P/'protocol.json'),'regions_sha256':sha(P/'regions.json'),'image_support_sha256':sha(PRE/'image_support.json'),'analysis_sha256':sha(Path(__file__)),'support':support,'limitations':'RGB candidates are not independently verified; roof spans multiple faces and is not a valid negative control; candidate geometry is exploratory.'}
(OUT/'analysis.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'replay_checks':checks,'parity':parity,'support':support,'rows':rows},indent=2))
