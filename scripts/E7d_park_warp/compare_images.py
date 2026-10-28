import csv,hashlib,json
from pathlib import Path
import cv2,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/E7d_park_warp/2026-10-28/image_pair';OUT.mkdir(parents=True,exist_ok=False);CFG=ROOT/'configs/E7d_park_warp/protocol.json';cfg=json.loads(CFG.read_text());rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open())); images=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for i in cfg['frames']:
 p=ROOT/'data/AMtown01/mapping'/rows[i]['png_filename'];assert sha(p)==rows[i]['png_sha256'];im=cv2.imread(str(p));assert im.shape[:2]==(2048,2448);images.append(im)
a,b=images;mask=np.zeros(a.shape[:2],np.uint8);cv2.fillPoly(mask,[np.array(cfg['source_polygon_native_pixels'],np.int32)],255);sift=cv2.SIFT_create(nfeatures=25000,contrastThreshold=0.015);ka,da=sift.detectAndCompute(cv2.cvtColor(a,cv2.COLOR_BGR2GRAY),mask);kb,db=sift.detectAndCompute(cv2.cvtColor(b,cv2.COLOR_BGR2GRAY),None);matcher=cv2.BFMatcher(); fw=matcher.knnMatch(da,db,k=2);bw=matcher.knnMatch(db,da,k=2);rev={x.queryIdx:x.trainIdx for z in bw if len(z)==2 for x,y in [z] if x.distance<.75*y.distance};matches=[x for z in fw if len(z)==2 for x,y in [z] if x.distance<.75*y.distance and rev.get(x.trainIdx)==x.queryIdx];src=np.array([ka[x.queryIdx].pt for x in matches],float).reshape(-1,2);dst=np.array([kb[x.trainIdx].pt for x in matches],float).reshape(-1,2)
# Fix four spatial folds on source-image tiles, not on residuals.
fold=((src[:,0]//120).astype(int)+2*(src[:,1]//120).astype(int))%4

def fit(kind,x,y):
 if kind=='similarity':
  m,inl=cv2.estimateAffinePartial2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=5,maxIters=5000,confidence=.999,refineIters=20)
 elif kind=='affine':
  m,inl=cv2.estimateAffine2D(x,y,method=cv2.RANSAC,ransacReprojThreshold=5,maxIters=5000,confidence=.999,refineIters=20)
 else:m,inl=cv2.findHomography(x,y,method=cv2.RANSAC,ransacReprojThreshold=5,maxIters=5000,confidence=.999)
 return m, None if inl is None else inl.reshape(-1).astype(bool)
def apply(m,x):
 if m.shape==(2,3):return x@m[:,:2].T+m[:,2]
 q=np.column_stack((x,np.ones(len(x))))@m.T;return q[:,:2]/q[:,2:]
results=[];models={};cv2.setRNGSeed(20261028)
if len(src)>=8:
 for kind in ('similarity','affine','homography'):
  mat,inl=fit(kind,src,dst)
  if mat is None:continue
  err=np.linalg.norm(apply(mat,src)-dst,axis=1);he=np.full(len(src),np.nan)
  for z in range(4):
   train=fold!=z;test=~train
   if train.sum()<8 or not test.any():continue
   m,_=fit(kind,src[train],dst[train]);
   if m is not None:he[test]=np.linalg.norm(apply(m,src[test])-dst[test],axis=1)
  finite=np.isfinite(he);item={'model':kind,'candidates':len(src),'inliers':int(inl.sum()),'inlier_median_px':float(np.median(err[inl])) if inl.any() else None,'inlier_p90_px':float(np.percentile(err[inl],90)) if inl.any() else None,'heldout_count':int(finite.sum()),'heldout_median_px':float(np.median(he[finite])) if finite.any() else None,'heldout_p90_px':float(np.percentile(he[finite],90)) if finite.any() else None,'matrix':mat.tolist()};results.append(item);models[kind]=(mat,inl,err,he)
np.savez_compressed(OUT/'sift_candidates.npz',source_xy=src,target_xy=dst,fold=fold,**{f'{k}_inlier':v[1] for k,v in models.items()})
fig,axs=plt.subplots(1,2,figsize=(16,7),constrained_layout=True)
for ax,im,pts,title in [(axs[0],a,src,'0001 native image'),(axs[1],b,dst,'0072 native image')]:
 ax.imshow(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));ax.scatter(pts[:,0],pts[:,1],c=fold,s=14,cmap='tab10');ax.set_title(f'{title}: {len(pts)} candidate points');ax.set_xlim(900,2448);ax.set_ylim(1600,350)
 for j in np.linspace(0,len(pts)-1,min(25,len(pts)),dtype=int) if len(pts) else []:ax.text(pts[j,0],pts[j,1],str(j),fontsize=7,color='yellow',bbox={'facecolor':'black','alpha':.5,'pad':.1})
poly=np.array(cfg['source_polygon_native_pixels']+[cfg['source_polygon_native_pixels'][0]]);axs[0].plot(poly[:,0],poly[:,1],color='magenta',lw=1);fig.savefig(OUT/'matched_park_images.png',dpi=160);plt.close(fig)
if 'homography' in models:
 mat,inl,_,_=models['homography'];warped=cv2.warpPerspective(a,mat,(b.shape[1],b.shape[0]));roi=cv2.warpPerspective(mask,mat,(b.shape[1],b.shape[0]),flags=cv2.INTER_NEAREST)>0;blend=b.copy();blend[roi]=(0.5*b[roi]+0.5*warped[roi]).astype(np.uint8);cv2.imwrite(str(OUT/'homography_overlay.png'),blend)
summary={'frames':cfg['frames'],'timestamp_1':rows[1]['rgb_timestamp'],'timestamp_72':rows[72]['rgb_timestamp'],'delta_seconds':float(rows[72]['rgb_timestamp'])-float(rows[1]['rgb_timestamp']),'roi_polygon':cfg['source_polygon_native_pixels'],'source_sift_keypoints':len(ka),'candidate_count':len(src),'target_sift_keypoints':len(kb),'source_span_xy':np.ptp(src,axis=0).tolist() if len(src) else None,'target_span_xy':np.ptp(dst,axis=0).tolist() if len(dst) else None,'models':results,'input_sha256':{str(i):rows[i]['png_sha256'] for i in cfg['frames']},'protocol_sha256':sha(CFG),'script_sha256':sha(Path(__file__)),'caveat':'SIFT matches are candidates and spatially correlated. Residual is pixel reprojection disagreement, not physical deformation or lens error; image motion includes perspective and crop.'};(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
