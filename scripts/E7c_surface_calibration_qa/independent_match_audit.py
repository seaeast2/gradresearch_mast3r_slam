"""Check SIFT features against LK at exactly the same source pixel, not a nearby grid point."""
import csv,json,hashlib,sys
from pathlib import Path
import cv2,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'thirdparty/MASt3R-SLAM'));from mast3r_slam.mast3r_utils import resize_img
OUT=ROOT/'results/E7c_surface_calibration_qa/2026-10-28/match_audit';OUT.mkdir(parents=True,exist_ok=False);PRE=ROOT/'results/E7a_overlap_support/2026-10-28/preflight';rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open()));frame=np.load(ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline/provenance.npz')['frame_ids'];cache={}
def img(i):
 if i not in cache:
  p=ROOT/'data/AMtown01/mapping'/rows[i]['png_filename'];assert hashlib.sha256(p.read_bytes()).hexdigest()==rows[i]['png_sha256'];a=cv2.cvtColor(cv2.imread(str(p)),cv2.COLOR_BGR2RGB).astype(np.float32)/255;rgb=resize_img(a,512)['unnormalized_img'];cache[i]=(rgb,cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY))
 return cache[i]
def track(seq,p):
 p=np.asarray(p,dtype=np.float32).reshape(-1,1,2);status=np.ones(len(p),bool)
 for i,j in zip(seq[:-1],seq[1:]):
  nxt,st,_=cv2.calcOpticalFlowPyrLK(img(i)[1],img(j)[1],p,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01));
  if nxt is None:return np.zeros((len(p),2)),np.zeros(len(p),bool)
  status&=st[:,0].astype(bool)&np.isfinite(nxt[:,0,:]).all(1);p=nxt
 return p[:,0,:],status
report=[]
for region in ('road','roof'):
 for a,b in ((8,11),(9,12),(10,12)):
  z=np.load(PRE/f'{region}_{a}_{b}_tracks.npz');s=z['sift_matches'];f=int(frame[a]);g=int(frame[b]);checks=[]
  if len(s):
   forward,ok=track(list(range(f,g+1)),s[:,:2]);back,ok2=track(list(range(g,f-1,-1)),forward);delta=np.linalg.norm(forward-s[:,2:],axis=1);fb=np.linalg.norm(back-s[:,:2],axis=1)
   for j in range(len(s)):checks.append({'sift_source':s[j,:2].tolist(),'sift_target':s[j,2:].tolist(),'lk_target_same_source':forward[j].tolist(),'lk_forward_backward_px':float(fb[j]),'sift_lk_target_displacement_px':float(delta[j]),'lk_status':bool(ok[j] and ok2[j])})
   fig,axs=plt.subplots(1,2,figsize=(10,5),constrained_layout=True)
   for ax,i in ((axs[0],f),(axs[1],g)):ax.imshow(img(i)[0]);ax.axis('off')
   axs[0].scatter(s[:,0],s[:,1],marker='+',color='cyan',s=100,label='SIFT source')
   axs[1].scatter(s[:,2],s[:,3],marker='+',color='cyan',s=100,label='SIFT target');axs[1].scatter(forward[:,0],forward[:,1],marker='x',color='red',s=50,label='LK same source')
   xs=np.concatenate([s[:,0],s[:,2],forward[:,0]]);ys=np.concatenate([s[:,1],s[:,3],forward[:,1]])
   for ax in axs:ax.set_xlim(max(0,xs.min()-45),min(512,xs.max()+45));ax.set_ylim(min(416,ys.max()+45),max(0,ys.min()-45));ax.legend(loc='lower right',fontsize=7)
   fig.suptitle(f'{region} KF{a}–{b}: algorithmic agreement only');fig.savefig(OUT/f'{region}_{a}_{b}_sift_lk.png',dpi=160);plt.close(fig)
  report.append({'region':region,'pair':f'{a}-{b}','sift_matches':len(s),'lk_candidates':len(z['source_xy']),'checks':checks,'physical_correspondence_verification':'NOT VERIFIED','negative_control':'invalid mixed roof faces' if region=='roof' else 'not a negative control'})
(OUT/'match_audit.json').write_text(json.dumps({'results':report,'interpretation':'Both algorithms use same image pair; agreement is not independent ground truth or proof of visibility. No manual correspondence labels provided.'},indent=2)+'\n');print(json.dumps(report,indent=2))
