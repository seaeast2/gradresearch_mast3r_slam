"""Compare symmetric MASt3R raw pair self branches on white image candidates."""
import json,hashlib,os,sys
from pathlib import Path
import cv2,numpy as np,torch,lietorch
ROOT=Path(__file__).resolve().parents[2];UP=ROOT/'thirdparty/MASt3R-SLAM';sys.path.insert(0,str(UP));from mast3r_slam.config import load_config
from mast3r_slam.frame import create_frame
from mast3r_slam.mast3r_utils import load_mast3r,mast3r_symmetric_inference,resize_img
OUT=ROOT/'results/E7d_park_warp/2026-10-28/white_pointmaps';OUT.mkdir(parents=True,exist_ok=False);SRC=ROOT/'results/E7d_park_warp/2026-10-28/white_surface';z=np.load(SRC/'white_candidates.npz');keep=z['homography_inlier'];xy=z['source_xy'][keep];uv=z['target_xy'][keep];fold=z['fold'][keep]
def sample(arr,p):
 x,y=p[:,0],p[:,1];i=np.floor(x).astype(int);j=np.floor(y).astype(int);u=(x-i)[:,None];v=(y-j)[:,None];return (1-u)*(1-v)*arr[j,i]+u*(1-v)*arr[j,i+1]+(1-u)*v*arr[j+1,i]+u*v*arr[j+1,i+1]
def similarity(a,b):
 ca=a.mean(0);cb=b.mean(0);aa=a-ca;bb=b-cb;u,s,v=np.linalg.svd(bb.T@aa/len(a));d=np.ones(3);d[-1]=np.linalg.det(u@v);R=u@np.diag(d)@v;scale=(s*d).sum()/np.mean(np.sum(aa*aa,axis=1));assert scale>0;return scale,R,cb-scale*R@ca
def transform(p,t):s,r,d=t;return s*(p@r.T)+d
def plane(x):
 c=x.mean(0);_,_,v=np.linalg.svd(x-c,full_matrices=False);res=(x-c)@v[-1];span=np.linalg.norm(np.ptp((x-c)@v[:2].T,axis=0));return {'p90_over_span':float(np.percentile(abs(res),90)/span),'median_over_span':float(np.median(abs(res))/span),'span':float(span),'normal':v[-1].tolist()}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
# Synthetic test verifies convention and reflection/scale behavior.
rng=np.random.default_rng(20261028);test=rng.normal(size=(50,3));rot=np.array([[0,-1,0],[1,0,0],[0,0,1.]]);truth=2.3*(test@rot.T)+np.array([3.,-2.,5.]);assert np.max(abs(transform(test,similarity(test,truth))-truth))<1e-10
os.chdir(UP);load_config(str(ROOT/'configs/E0_environment_preparation/low_vram_base.yaml'));torch.backends.cuda.matmul.allow_tf32=True;torch.set_grad_enabled(False);model=load_mast3r(device='cuda:0');images=[];coords=[]
for i,pt in [(1,xy),(72,uv)]:
 img=cv2.cvtColor(cv2.imread(str(ROOT/f'data/AMtown01/mapping/{i:04d}.png')),cv2.COLOR_BGR2RGB).astype('float32')/255;_,tr=resize_img(img,512,return_transformation=True);scale=np.array(tr[:2]);crop=np.array(tr[2:]);q=(pt+.5)/scale-.5-crop;coords.append(q);images.append(create_frame(i,img,lietorch.Sim3.Identity(1,device='cuda:0'),img_size=512,device='cuda:0'))
X,C,_,_=mast3r_symmetric_inference(model,*images);x=X[0].detach().cpu().numpy().reshape(416,512,3);y=X[2].detach().cpu().numpy().reshape(416,512,3);cx=C[0].detach().cpu().numpy().reshape(416,512,1);cy=C[2].detach().cpu().numpy().reshape(416,512,1)
valid=np.ones(len(xy),bool)
for p in coords:valid &= np.isfinite(p).all(1)&(p[:,0]>=0)&(p[:,0]<511)&(p[:,1]>=0)&(p[:,1]<415)
idx=np.flatnonzero(valid);a=sample(x,coords[0][valid]).astype(float);b=sample(y,coords[1][valid]).astype(float);ca=sample(cx,coords[0][valid]).reshape(-1);cb=sample(cy,coords[1][valid]).reshape(-1);ok=np.isfinite(a).all(1)&np.isfinite(b).all(1)&np.isfinite(ca)&np.isfinite(cb)&(ca>0)&(cb>0);idx=idx[ok];a=a[ok];b=b[ok];ca=ca[ok];cb=cb[ok];ff=fold[idx];assert len(a)>=12
T=similarity(a,b);fit=np.linalg.norm(transform(a,T)-b,axis=1);hold=np.full(len(a),np.nan);fold_counts=[]
for k in range(4):
 tr=ff!=k;te=~tr;fold_counts.append(int(te.sum()))
 if tr.sum()>=6 and te.sum():hold[te]=np.linalg.norm(transform(a[te],similarity(a[tr],b[tr]))-b[te],axis=1)
assert np.isfinite(hold).all();span=float(np.linalg.norm(np.ptp(b,axis=0)));assert span>0;pa=plane(a);pb=plane(b);na=np.array(pa['normal']);nb=np.array(pb['normal']);angle=float(np.degrees(np.arccos(np.clip(abs((T[1]@na)@nb),0,1))))
np.savez_compressed(OUT/'pointmap_candidates.npz',source_native_xy=xy[idx],target_native_xy=uv[idx],source_model_xy=coords[0][idx],target_model_xy=coords[1][idx],source_xyz=a,target_xyz=b,source_confidence=ca,target_confidence=cb,fold=ff,heldout_distance=hold)
out={'input_frames':[1,72],'raw_model_branch':'symmetric direct pair X11 and X22; each in its own camera frame, not E7 SLAM keyframe geometry','homography_inliers_in':len(xy),'common_valid':len(a),'valid_fraction':len(a)/len(xy),'spatial_fold_sizes':fold_counts,'source_plane':pa,'target_plane':pb,'alignment_scale':float(T[0]),'aligned_plane_normal_angle_deg':angle,'training_fitted_3d_median':float(np.median(fit)),'training_fitted_3d_p90':float(np.percentile(fit,90)),'heldout_3d_median':float(np.median(hold)),'heldout_3d_p90':float(np.percentile(hold,90)),'target_3d_bbox_diagonal':span,'heldout_median_over_target_span':float(np.median(hold)/span),'heldout_p90_over_target_span':float(np.percentile(hold,90)/span),'source_confidence_median':float(np.median(ca)),'target_confidence_median':float(np.median(cb)),'synthetic_sim3_test':'pass','checkpoint_sha256':sha(UP/'checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth'),'script_sha256':sha(Path(__file__)),'limitation':'55 image candidates chosen with full-data homography consensus before spatial 3D holdout: selection is not independent of all points; no external physical correspondence/depth truth; 3D similarity absorbs pose, scale, translation; direct long-baseline pair is not sequential SLAM.'}
(OUT/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
