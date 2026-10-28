"""RGB-only preflight: source masks, dense LK candidates and separate SIFT feature checks."""
import csv,hashlib,json,sys
from pathlib import Path
import cv2,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'thirdparty/MASt3R-SLAM'))
from mast3r_slam.mast3r_utils import resize_img
REG=json.loads((ROOT/'configs/E7a_overlap_support/regions.json').read_text());OUT=ROOT/'results/E7a_overlap_support/2026-10-28/preflight';rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open()));cache={}; H,W=416,512
ids=dict(zip(REG['keyframes'],REG['frame_ids']))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rgb(i):
 if i not in cache:
  p=ROOT/'data/AMtown01/mapping'/rows[i]['png_filename'];assert sha(p)==rows[i]['png_sha256'];a=cv2.cvtColor(cv2.imread(str(p)),cv2.COLOR_BGR2RGB).astype(np.float32)/255; cache[i]=resize_img(a,512)['unnormalized_img']
 return cache[i]
def gray(i):return cv2.cvtColor(rgb(i),cv2.COLOR_RGB2GRAY)
def mask(polys,erode=0):
 out=np.zeros((H,W),np.uint8);cv2.fillPoly(out,[np.array(p,np.int32) for p in polys],1)
 return cv2.erode(out,np.ones((2*erode+1,2*erode+1),np.uint8)) if erode else out
capture=mask(REG['capture_polygons_xy'],erode=1)
def track(seq,coords):
 p=coords.astype('float32').reshape(-1,1,2);valid=np.ones(len(p),bool)
 for a,b in zip(seq[:-1],seq[1:]):
  p1,st,_=cv2.calcOpticalFlowPyrLK(gray(a),gray(b),p,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
  if p1 is None:return np.zeros((len(p),2)),np.zeros(len(p),bool)
  valid&=(st[:,0]!=0)&np.isfinite(p1[:,0]).all(1);p=p1
 return p[:,0],valid
summ=[]
for region in ('road','roof'):
 for a,b in REG['pairs']:
  ia,ib=ids[a],ids[b];m=mask([REG['source_regions'][region][str(a)]],erode=2);
  if region=='road':m[:REG['rgb_review_amendment']['road_source_min_y']]=0
  yy,xx=np.mgrid[0:H:3,0:W:3];xy=np.column_stack((xx.ravel(),yy.ravel()));xy=xy[m[xy[:,1],xy[:,0]]>0];n_grid=len(xy)
  f,ok=track(list(range(ia,ib+1)),xy);back,ok2=track(list(range(ib,ia-1,-1)),f);fb=np.linalg.norm(back-xy,axis=1);dst=np.rint(f).astype(int);inside=(dst[:,0]>=5)&(dst[:,0]<W-5)&(dst[:,1]>=5)&(dst[:,1]<H-5)
  in_capture=np.zeros(len(xy),bool);in_capture[inside]=capture[dst[inside,1],dst[inside,0]]>0
  keep=ok&ok2&inside&in_capture&(fb<=1.0);ncc=np.full(len(xy),-1.)
  ga,gb=gray(ia),gray(ib)
  for j in np.flatnonzero(keep):
   x,y=xy[j];u,v=dst[j]; p=ga[y-4:y+5,x-4:x+5].astype(float);q=gb[v-4:v+5,u-4:u+5].astype(float)
   if p.shape!=(9,9) or q.shape!=p.shape:continue
   p-=p.mean();q-=q.mean();d=np.linalg.norm(p)*np.linalg.norm(q)
   if d>1e-8:ncc[j]=float((p*q).sum()/d)
  keep&=ncc>=.8;xy=xy[keep];dst=dst[keep];f=f[keep];fb=fb[keep];ncc=ncc[keep]
  # Remove duplicate target pixels deterministically; each endpoint contributes once.
  if len(dst):
   _,u=np.unique(dst[:,1]*W+dst[:,0],return_index=True);u=np.sort(u);xy,dst,f,fb,ncc=(z[u] for z in (xy,dst,f,fb,ncc))
  # SIFT is an algorithmically separate check, not physical GT or a correctness guarantee.
  sift=cv2.SIFT_create();k1,d1=sift.detectAndCompute(ga,None);k2,d2=sift.detectAndCompute(gb,None);sm=[]
  if d1 is not None and d2 is not None:
   matcher=cv2.BFMatcher();fw=matcher.knnMatch(d1,d2,k=2);bw=matcher.knnMatch(d2,d1,k=2);rev={x.queryIdx:x.trainIdx for z in bw if len(z)==2 for x,y in [z] if x.distance<.75*y.distance}
   for z in fw:
    if len(z)<2:continue
    x,y=z
    if x.distance>=.75*y.distance or rev.get(x.trainIdx)!=x.queryIdx:continue
    p=np.array(k1[x.queryIdx].pt);q=np.array(k2[x.trainIdx].pt);px,py=np.rint(p).astype(int);qx,qy=np.rint(q).astype(int)
    if 0<=px<W and 0<=py<H and 0<=qx<W and 0<=qy<H and m[py,px] and capture[qy,qx]:sm.append([*p,*q])
  sm=np.array(sm,dtype=float).reshape(-1,4);checks=[]
  for sp in sm:
   if len(xy):
    d=np.linalg.norm(xy-sp[:2],axis=1);i=int(np.argmin(d))
    if d[i]<=5: checks.append([float(d[i]),float(np.linalg.norm(f[i]-sp[2:]))])
  np.savez_compressed(OUT/f'{region}_{a}_{b}_tracks.npz',source_xy=xy,target_xy=dst,target_float=f,fb_error=fb,ncc=ncc,sift_matches=sm,sift_lk_checks=np.asarray(checks,dtype=float).reshape(-1,2))
  r={'region':region,'pair':f'{a}-{b}','source_grid':n_grid,'lk_candidates':len(xy),'sift_independent_matches':len(sm),'sift_near_lk':len(checks),'sift_lk_target_diff_median':float(np.median(np.asarray(checks)[:,1])) if checks else None,'sift_lk_target_diff_max':float(np.max(np.asarray(checks)[:,1])) if checks else None,'fb_p90':float(np.percentile(fb,90)) if len(fb) else None,'ncc_median':float(np.median(ncc)) if len(ncc) else None};summ.append(r)
  fig,axs=plt.subplots(1,2,figsize=(13,6),constrained_layout=True)
  for ax,i,pts in ((axs[0],ia,xy),(axs[1],ib,dst)):
   ax.imshow(rgb(i));ax.set_title(f'{region} KF frame {i}, {len(pts)} candidates'); ax.axis('off')
   chosen=np.linspace(0,len(pts)-1,min(20,len(pts)),dtype=int) if len(pts) else []
   for j in chosen:ax.text(*pts[j],str(j),fontsize=6,color='yellow',bbox={'facecolor':'black','alpha':.45,'pad':.1})
  if len(xy):
   xs=np.concatenate([xy[:,0],dst[:,0]]);ys=np.concatenate([xy[:,1],dst[:,1]]);lo=max(0,int(xs.min()-35));hi=min(W,int(xs.max()+35));yl=max(0,int(ys.min()-25));yh=min(H,int(ys.max()+25))
   for ax in axs:ax.set_xlim(lo,hi);ax.set_ylim(yh,yl)
  fig.savefig(OUT/f'{region}_{a}_{b}_tracks.png',dpi=180);plt.close(fig)
(OUT/'image_support.json').write_text(json.dumps({'protocol_sha256':sha(ROOT/'configs/E7a_overlap_support/protocol.json'),'regions_sha256':sha(ROOT/'configs/E7a_overlap_support/regions.json'),'results':summ,'status':'RGB candidate support; no individual GT; SIFT agreement does not establish visibility'},indent=2)+'\n');print(json.dumps(summ,indent=2))
