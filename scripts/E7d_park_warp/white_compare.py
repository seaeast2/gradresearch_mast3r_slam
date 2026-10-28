import json,hashlib
from pathlib import Path
import cv2,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'results/E7d_park_warp/2026-10-28/image_pair';OUT=ROOT/'results/E7d_park_warp/2026-10-28/white_surface';OUT.mkdir(parents=True,exist_ok=False);cfg=ROOT/'configs/E7d_park_warp/white_surface_analysis.json';z=np.load(SRC/'sift_candidates.npz');a=z['source_xy'];b=z['target_xy'];fold=z['fold'];in1=cv2.imread(str(ROOT/'data/AMtown01/mapping/0001.png'));in2=cv2.imread(str(ROOT/'data/AMtown01/mapping/0072.png'));h1=cv2.cvtColor(in1,cv2.COLOR_BGR2HSV);h2=cv2.cvtColor(in2,cv2.COLOR_BGR2HSV);x=np.rint(a).astype(int);y=np.rint(b).astype(int);s=h1[x[:,1],x[:,0]];t=h2[y[:,1],y[:,0]];keep=(s[:,2]>=185)&(s[:,1]<=50)&(t[:,2]>=185)&(t[:,1]<=50);a=a[keep];b=b[keep];fold=fold[keep];cv2.setRNGSeed(20261028)
def fit(kind,x,y):
 if kind=='similarity':return cv2.estimateAffinePartial2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=5,maxIters=5000,confidence=.999,refineIters=20)
 if kind=='affine':return cv2.estimateAffine2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=5,maxIters=5000,confidence=.999,refineIters=20)
 return cv2.findHomography(x,y,method=cv2.RANSAC,ransacReprojThreshold=5,maxIters=5000,confidence=.999)
def act(m,x):
 if m.shape==(2,3):return x@m[:,:2].T+m[:,2]
 q=np.column_stack((x,np.ones(len(x))))@m.T;return q[:,:2]/q[:,2:]
models=[];homomask=None
for kind in ('similarity','affine','homography'):
 m,inl=fit(kind,a,b);assert m is not None;inl=inl.reshape(-1).astype(bool);err=np.linalg.norm(act(m,a)-b,axis=1);hold=np.full(len(a),np.nan)
 for k in range(4):
  tr=fold!=k;te=~tr
  if tr.sum()<8 or not te.any():continue
  mm,_=fit(kind,a[tr],b[tr]);
  if mm is not None:hold[te]=np.linalg.norm(act(mm,a[te])-b[te],axis=1)
 valid=np.isfinite(hold);models.append({'model':kind,'inliers':int(inl.sum()),'inlier_median_px':float(np.median(err[inl])),'inlier_p90_px':float(np.percentile(err[inl],90)),'holdout_n':int(valid.sum()),'holdout_median_px':float(np.median(hold[valid])),'holdout_p90_px':float(np.percentile(hold[valid],90)),'matrix':m.tolist()})
 if kind=='homography':homomask=inl
 if kind=='similarity':
  angle=np.degrees(np.arctan2(m[1,0],m[0,0]));scale=np.hypot(m[0,0],m[1,0]);models[-1].update({'scale':float(scale),'rotation_deg':float(angle)})
 if kind=='affine':models[-1]['singular_values']=np.linalg.svd(m[:,:2],compute_uv=False).tolist()
np.savez_compressed(OUT/'white_candidates.npz',source_xy=a,target_xy=b,fold=fold,homography_inlier=homomask)
fig,axs=plt.subplots(1,2,figsize=(14,7),constrained_layout=True)
for ax,img,p,title in ((axs[0],in1,a,'0001'),(axs[1],in2,b,'0072')):
 ax.imshow(cv2.cvtColor(img,cv2.COLOR_BGR2RGB));ax.scatter(p[homomask,0],p[homomask,1],s=15,c='#00ffff',label='homography candidate inlier');ax.scatter(p[~homomask,0],p[~homomask,1],s=20,c='red',label='excluded by model');ax.set(title=title,xlim=(1000,2448),ylim=(1500,400));ax.legend(fontsize=8)
fig.suptitle('White pixel proxy: candidates, not validated physical correspondences');fig.savefig(OUT/'white_candidates.png',dpi=160)
H=np.array(next(x for x in models if x['model']=='homography')['matrix']);warped=cv2.warpPerspective(in1,H,(2448,2048));sourcemask=np.zeros((2048,2448),np.uint8);srcpolygon=np.array(json.loads((ROOT/'configs/E7d_park_warp/protocol.json').read_text())['source_polygon_native_pixels'],np.int32);cv2.fillPoly(sourcemask,[srcpolygon],255);targetmask=cv2.warpPerspective(sourcemask,H,(2448,2048),flags=cv2.INTER_NEAREST);visible=(targetmask>0);ys,xs=np.where(visible);np.savez_compressed(OUT/'warped_roi_visibility.npz',visible=visible)
# Warp whole source mask into an expanded destination canvas to count clipped area.
shift=np.array([[1.,0,2000],[0,1.,1000],[0,0,1.]]);expanded=cv2.warpPerspective(sourcemask,shift@H,(6448,4048),flags=cv2.INTER_NEAREST);whole=np.count_nonzero(expanded);vis=np.count_nonzero(visible)
res={'initial_candidates':len(z['source_xy']),'white_candidates':len(a),'white_homography_inliers':int(homomask.sum()),'source_roi_pixels':int(np.count_nonzero(sourcemask)),'projected_roi_visible_pixels':int(vis),'projected_roi_total_pixels_approx':int(whole),'projected_roi_visible_fraction_approx':vis/whole if whole else None,'visibility_note':'Homography-estimated geometric clipping for entire broad source polygon; does not measure occlusion or white-only area.', 'models':models,'white_method':'HSV V>=185 and S<=50 both RGB images at SIFT centers; post-hoc exploratory proxy','config_sha256':hashlib.sha256(cfg.read_bytes()).hexdigest()}
(OUT/'summary.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
