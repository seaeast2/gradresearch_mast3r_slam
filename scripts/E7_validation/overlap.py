import csv, hashlib, json, sys
from pathlib import Path
import cv2,numpy as np
from scipy.spatial.transform import Rotation
from plyfile import PlyData
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'thirdparty/MASt3R-SLAM'))
from mast3r_slam.mast3r_utils import resize_img
OUT=ROOT/'results/E7_validation/2026-10-28/e7_amtown_probe'; BASE=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline'; P=ROOT/'configs/E7_validation'; cfg=json.loads((P/'overlap_protocol.json').read_text());roi=json.loads((P/'roi.json').read_text());rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open())); cache={}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def gray(i):
 if i not in cache:
  p=ROOT/'data/AMtown01/mapping'/rows[i]['png_filename'];assert sha(p)==rows[i]['png_sha256']; im=cv2.cvtColor(cv2.imread(str(p)),cv2.COLOR_BGR2RGB).astype(np.float32)/255;cache[i]=cv2.cvtColor(resize_img(im,512)['unnormalized_img'],cv2.COLOR_RGB2GRAY)
 return cache[i]
def mask(k):
 m=np.zeros((416,512),np.uint8);cv2.fillPoly(m,[np.array(roi['polygons_xy'][str(k)],np.int32)],1);e=cfg['roi_erode_pixels'];return cv2.erode(m,np.ones((2*e+1,2*e+1),np.uint8))
def track(seq,p):
 p=p.astype(np.float32).reshape(-1,1,2);valid=np.ones(len(p),bool)
 for a,b in zip(seq[:-1],seq[1:]):
  q,st,_=cv2.calcOpticalFlowPyrLK(gray(a),gray(b),p,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
  if q is None: return np.zeros((len(p),2)),np.zeros(len(p),bool)
  valid &= st[:,0].astype(bool)&np.isfinite(q[:,0,:]).all(1);p=q
 return p[:,0,:],valid
prov=np.load(OUT/'provenance.npz'); ply=PlyData.read(OUT/'output/mapping.ply')['vertex'].data; poses=np.load(OUT/'final_sim3.npy'); assert len(ply)==len(prov['kf_id']); summary=[]
def act(p,x):return p[7]*Rotation.from_quat(p[3:7]).apply(x)+p[:3]
def mapped(k,xy):
 d=np.load(OUT/f'kf{k}_replay.npz'); l=np.full(416*512,-1);l[d['pixel_index']]=np.arange(len(d['pixel_index']));idx=l[xy[:,1]*512+xy[:,0]]; assert (idx>=0).all();return d,idx
for a,b in cfg['pairs']:
 ia,ib=int(prov['frame_ids'][a]),int(prov['frame_ids'][b]); ma,mb=mask(a),mask(b);yy,xx=np.mgrid[0:416:3,0:512:3];xy=np.column_stack((xx.ravel(),yy.ravel()));xy=xy[ma[xy[:,1],xy[:,0]]!=0]; grid=len(xy)
 forward,ok=track(range(ia,ib+1),xy);back,okb=track(range(ib,ia-1,-1),forward);fb=np.linalg.norm(back-xy,axis=1);target=np.rint(forward).astype(int);inside=(target[:,0]>=4)&(target[:,0]<508)&(target[:,1]>=4)&(target[:,1]<412);inside[inside]&=mb[target[inside,1],target[inside,0]]!=0;keep=ok&okb&inside&(fb<=1); gate_counts={'forward_valid':int(ok.sum()),'backward_valid':int((ok&okb).sum()),'target_in_roi':int((ok&okb&inside).sum()),'fb_pass':int(keep.sum())}; ncc=np.full(len(xy),-1.)
 for j in np.flatnonzero(keep):
  x,y=xy[j];u,v=target[j];pa=gray(ia)[y-4:y+5,x-4:x+5].astype(float);pb=gray(ib)[v-4:v+5,u-4:u+5].astype(float)
  if pa.shape!=(9,9) or pb.shape!=pa.shape:continue
  pa-=pa.mean();pb-=pb.mean();den=np.linalg.norm(pa)*np.linalg.norm(pb)
  if den>1e-8:ncc[j]=(pa*pb).sum()/den
 keep &= ncc>=.8; xy=xy[keep];target=target[keep];fb=fb[keep];ncc=ncc[keep]; candidates=len(xy)
 d1,i1=mapped(a,xy);d2,i2=mapped(b,target)
 def exported(k,xy):
  sel=np.flatnonzero(prov['kf_id']==k); indices=prov['pixel_index'][sel]; m=np.full(416*512,-1,dtype=np.int64);m[indices]=sel;return m[xy[:,1]*512+xy[:,0]]
 ea=exported(a,xy);eb=exported(b,target);ex=(ea>=0)&(eb>=0);new=(d1['weight_excluded'][i1,0]/int(d1['n_excluded'])>1.5)&(d2['weight_excluded'][i2,0]/int(d2['n_excluded'])>1.5);valid=ex&new
 result={'pair':f'{a}-{b}','frame_a':ia,'frame_b':ib,'grid':grid,'candidates':candidates,'original_export_both':int(ex.sum()),'both_arms_export_both':int(valid.sum()),'status':'CANDIDATE_UNVERIFIED' if valid.sum()>=cfg['minimum_candidates'] else 'INSUFFICIENT_SUPPORT',**gate_counts}
 np.savez_compressed(OUT/f'pair_{a}_{b}_candidates.npz',source_xy=xy,target_xy=target,fb=fb,ncc=ncc,original_export=ex,both_export=valid)
 if ex.any():
  wa=act(poses[a],d1['original'][i1[ex]].astype(float));wb=act(poses[b],d2['original'][i2[ex]].astype(float)); qa=np.column_stack([ply[c][ea[ex]] for c in 'xyz']);qb=np.column_stack([ply[c][eb[ex]] for c in 'xyz']);result['original_export_max_distance']=float(max(np.linalg.norm(wa-qa,axis=1).max(),np.linalg.norm(wb-qb,axis=1).max()));assert result['original_export_max_distance']<2e-5
 if valid.sum()>=cfg['minimum_candidates']:
  xa=act(poses[a],d1['original'][i1[valid]].astype(float));xb=act(poses[b],d2['original'][i2[valid]].astype(float));_,_,v=np.linalg.svd(xa-xa.mean(0),full_matrices=False);n=v[-1];n=n if n[2]>=0 else -n
  for arm,ka,kb in [('original','original','original'),('exclude_a','excluded','original'),('exclude_b','original','excluded')]:
   wa=act(poses[a],d1[ka][i1[valid]].astype(float));wb=act(poses[b],d2[kb][i2[valid]].astype(float));delta=wb-wa;dn=delta@n;dt=np.linalg.norm(delta-dn[:,None]*n,axis=1)
   for name,arr in [('normal_abs',abs(dn)),('tangent',dt),('z_abs',abs(delta[:,2])),('xy',np.linalg.norm(delta[:,:2],axis=1))]: result[arm+'_'+name+'_median']=float(np.median(arr));result[arm+'_'+name+'_p90']=float(np.percentile(arr,90))
   result[arm+'_normal_signed_median']=float(np.median(dn))
 summary.append(result)
 fig,axs=plt.subplots(1,2,figsize=(10,5),constrained_layout=True)
 for ax,k,im,points in [(axs[0],a,gray(ia),xy),(axs[1],b,gray(ib),target)]:
  ax.imshow(im,cmap='gray');poly=roi['polygons_xy'][str(k)]; ax.plot(*np.array(poly+[poly[0]]).T,color='magenta');ax.scatter(points[:,0],points[:,1],s=8,c='yellow');ax.set_title(f'KF{k}, candidates {candidates}');ax.set_xlim(365,512);ax.set_ylim(290,85)
 fig.savefig(OUT/f'pair_{a}_{b}_candidates.png',dpi=140);plt.close(fig)
(OUT/'overlap_summary.json').write_text(json.dumps({'protocol_sha256':sha(P/'overlap_protocol.json'),'results':summary,'warning':'Candidates only; no independently verified physical correspondence or actual seam-free control.'},indent=2)+'\n');print(json.dumps(summary,indent=2))
