import csv, hashlib, json, sys
from pathlib import Path
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from plyfile import PlyData

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'thirdparty/MASt3R-SLAM'))
from mast3r_slam.mast3r_utils import resize_img

OUT=ROOT/'results/E2a_overlap/2026-10-28/flow'
E1=ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'
E2=ROOT/'results/E2_raw_pointmap/2026-10-28/raw_pairs'
PROTOCOL=ROOT/'configs/E2a_overlap/protocol.json'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def similarity(a,b):
    ma=a.mean(0); mb=b.mean(0); aa=a-ma; bb=b-mb
    u,s,vh=np.linalg.svd(bb.T@aa/len(a))
    d=np.ones(3); d[-1]=np.sign(np.linalg.det(u@vh))
    rotation=u@np.diag(d)@vh
    scale=(s*d).sum()/np.mean(np.sum(aa*aa,axis=1))
    if scale<=0: raise ValueError('Invalid scale')
    return scale,rotation,mb-scale*(rotation@ma)

def transform(x, model):
    s,r,t=model
    return s*(x@r.T)+t

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=json.loads(PROTOCOL.read_text()); polygons=json.loads((ROOT/'configs/E1_baseline_reproduction/periodic_1s_rois.json').read_text())['polygons_xy']
    data=list(csv.DictReader((ROOT/'data/HKairport01/mapping_frames.csv').open()))
    provenance=np.load(E1/'provenance.npz'); ids=provenance['kf_id']; pixels=provenance['pixel_index']; frame_ids=provenance['frame_ids']
    ply=PlyData.read(E1/'output/mapping.ply')['vertex'].data
    assert len(ply)==len(ids)==len(pixels)
    h,w=map(int,provenance['image_shape']); assert (h,w)==(416,512)
    cache={}
    def image(idx):
        if idx not in cache:
            path=ROOT/'data/HKairport01/mapping'/data[idx]['png_filename']
            assert digest(path)==data[idx]['png_sha256']
            im=cv2.cvtColor(cv2.imread(str(path)),cv2.COLOR_BGR2RGB).astype(np.float32)/255
            cache[idx]=resize_img(im,512)['unnormalized_img'].copy()
        return cache[idx]
    def gray(idx): return cv2.cvtColor(image(idx),cv2.COLOR_RGB2GRAY)
    def mask(k):
        m=np.zeros((h,w),np.uint8); cv2.fillPoly(m,[np.asarray(polygons[str(k)],np.int32)],1)
        radius=cfg['roi_erode_pixels']; return cv2.erode(m,np.ones((2*radius+1,2*radius+1),np.uint8))
    def track(seq,p):
        p=p.astype(np.float32).reshape(-1,1,2); valid=np.ones(len(p),bool)
        for a,b in zip(seq[:-1],seq[1:]):
            nxt,st,_=cv2.calcOpticalFlowPyrLK(gray(a),gray(b),p,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
            if nxt is None: raise RuntimeError('Optical flow failed')
            valid &= st[:,0].astype(bool) & np.isfinite(nxt[:,0,:]).all(1)
            p=nxt
        return p[:,0,:],valid
    def raw_lookup(k):
        z=np.load(E2/f'kf{k}_birth_self.npz'); arr=np.full((h*w,3),np.nan,np.float32); arr[z['pixel_index']]=z['xyz']; return arr
    def world_lookup(k):
        sel=np.flatnonzero(ids==k); arr=np.full((h*w,3),np.nan,np.float32)
        arr[pixels[sel]]=np.column_stack([ply[c][sel] for c in 'xyz']); return arr
    rows=[]
    for ka,kb in cfg['pairs']:
        ia,ib=int(frame_ids[ka]),int(frame_ids[kb]); assert ia<ib
        ma,mb=mask(ka),mask(kb); yy,xx=np.mgrid[0:h:cfg['grid_step_pixels'],0:w:cfg['grid_step_pixels']]
        xy=np.column_stack((xx.ravel(),yy.ravel())); xy=xy[ma[xy[:,1],xy[:,0]]!=0]
        forward,ok=track(list(range(ia,ib+1)),xy); backward,okb=track(list(range(ib,ia-1,-1)),forward)
        fb=np.linalg.norm(backward-xy,axis=1); target=np.rint(forward).astype(int)
        inside=(target[:,0]>=0)&(target[:,0]<w)&(target[:,1]>=0)&(target[:,1]<h)
        inside[inside] &= mb[target[inside,1],target[inside,0]]!=0
        keep=ok&okb&inside&(fb<=cfg['forward_backward_max_pixels'])
        rad=cfg['patch_radius_pixels']; a=gray(ia); b=gray(ib); ncc=np.full(len(xy),-1.,float)
        for q in np.flatnonzero(keep):
            x,y=xy[q]; u,v=target[q]; pa=a[y-rad:y+rad+1,x-rad:x+rad+1].astype(float); pb=b[v-rad:v+rad+1,u-rad:u+rad+1].astype(float)
            if pa.shape!=(2*rad+1,2*rad+1) or pb.shape!=pa.shape: continue
            pa-=pa.mean(); pb-=pb.mean(); denom=np.linalg.norm(pa)*np.linalg.norm(pb)
            if denom>1e-8: ncc[q]=(pa*pb).sum()/denom
        keep &= ncc>=cfg['patch_ncc_min']; xy=xy[keep]; target=target[keep]; fb=fb[keep]; ncc=ncc[keep]
        ind_a=xy[:,1]*w+xy[:,0]; ind_b=target[:,1]*w+target[:,0]
        pa=raw_lookup(ka)[ind_a]; pb=raw_lookup(kb)[ind_b]; wa=world_lookup(ka)[ind_a]; wb=world_lookup(kb)[ind_b]
        finite=np.isfinite(pa).all(1)&np.isfinite(pb).all(1); xy,target,fb,ncc,pa,pb,wa,wb=[x[finite] for x in (xy,target,fb,ncc,pa,pb,wa,wb)]
        span=np.ptp(xy,axis=0) if len(xy) else np.zeros(2)
        adequate=len(xy)>=cfg['minimum_matches'] and np.all(span>=cfg['minimum_xy_span_pixels'])
        result={'kf_a':ka,'kf_b':kb,'frame_a':ia,'frame_b':ib,'matches':len(xy),'span_x_px':int(span[0]),'span_y_px':int(span[1]),'support_status':'CANDIDATE' if adequate else 'INSUFFICIENT_SUPPORT', 'note':'Candidate image tracks; not independently verified correspondences'}
        if adequate:
            bins=((xy[:,0]//20+xy[:,1]//20)%2).astype(bool); err=np.full(len(xy),np.nan)
            for fit in (False,True):
                train=bins==fit; test=~train
                if train.sum()<10 or test.sum()<10: raise ValueError('Insufficient spatial holdout')
                err[test]=np.linalg.norm(transform(pa[test],similarity(pa[train],pb[train]))-pb[test],axis=1)
            model=similarity(pa,pb); span3=np.linalg.norm(np.ptp(pb,axis=0)); world=np.isfinite(wa).all(1)&np.isfinite(wb).all(1)
            result.update({'flow_fb_p90_px':float(np.percentile(fb,90)),'ncc_median':float(np.median(ncc)), 'sim3_scale_fit_all':float(model[0]),'raw_holdout_3d_median_over_span':float(np.median(err)/span3),'raw_holdout_3d_p90_over_span':float(np.percentile(err,90)/span3),'world_export_matches':int(world.sum())})
            if world.sum()>=10:
                center=wa[world].mean(0); _,_,v=np.linalg.svd(wa[world]-center,full_matrices=False); n=v[-1]; delta=(wb[world]-wa[world])@n
                result.update({'world_signed_normal_median':float(np.median(delta)),'world_signed_normal_p10':float(np.percentile(delta,10)),'world_signed_normal_p90':float(np.percentile(delta,90)),'world_normal_sign':'arbitrary; normal from source matched points'})
            np.savez_compressed(OUT/f'kf{ka}_{kb}_correspondences.npz',source_xy=xy,target_xy=target,fb_error=fb,ncc=ncc,raw_a=pa,raw_b=pb,world_a=wa,world_b=wb,holdout_error=err,fold=bins)
        fig,axes=plt.subplots(1,2,figsize=(14,6),constrained_layout=True)
        for ax,img,k,coords in ((axes[0],image(ia),ka,xy),(axes[1],image(ib),kb,target)):
            ax.imshow(img); ax.plot(*np.asarray(polygons[str(k)]+[polygons[str(k)][0]]).T,color='magenta',lw=1); ax.set_title(f'KF{k}, frame {frame_ids[k]}'); ax.set_xlim(300,512); ax.set_ylim(280,150); ax.axis('off')
            take=np.linspace(0,len(coords)-1,min(45,len(coords)),dtype=int) if len(coords) else []
            for num,index in enumerate(take): ax.text(coords[index,0],coords[index,1],str(num),color='yellow',fontsize=5)
        fig.suptitle(f'KF{ka}–KF{kb}: {len(xy)} candidate tracks; identical labels are paired'); fig.savefig(OUT/f'kf{ka}_{kb}_tracks.png',dpi=180); plt.close(fig)
        rows.append(result); print(json.dumps(result),flush=True)
    fields=sorted(set().union(*(r.keys() for r in rows)))
    with (OUT/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    manifest={'protocol_sha256':digest(PROTOCOL),'script_sha256':digest(Path(__file__)),'e1_ply_sha256':digest(E1/'output/mapping.ply'),'e1_provenance_sha256':digest(E1/'provenance.npz'), 'input_csv_sha256':digest(ROOT/'data/HKairport01/mapping_frames.csv'), 'roi_sha256':digest(ROOT/'configs/E1_baseline_reproduction/periodic_1s_rois.json'), 'raw_pointmap_sha256':{str(k):digest(E2/f'kf{k}_birth_self.npz') for k in sorted({k for pair in cfg['pairs'] for k in pair})},'opencv':cv2.__version__,'results':rows,'warning':'Candidate image tracks need independent visual verification; no GT, metric scale or causal attribution.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__': main()
