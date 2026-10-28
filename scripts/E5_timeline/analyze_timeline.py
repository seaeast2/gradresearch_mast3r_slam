import csv, hashlib, json, sys
from pathlib import Path
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'thirdparty/MASt3R-SLAM'))
from mast3r_slam.mast3r_utils import resize_img

E1=ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'
E3=ROOT/'results/E3_fusion/2026-10-28/instrumented'
E4=ROOT/'results/E4_backend/2026-10-28/instrumented'
OUT=ROOT/'results/E5_timeline/2026-10-28/timeline'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def write_csv(path,rows):
    fields=list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    inputs=list(csv.DictReader((ROOT/'data/HKairport01/mapping_frames.csv').open()))
    tracking=list(csv.DictReader((E1/'tracking_timeline.csv').open()))
    events=list(csv.DictReader((E3/'fusion_events.csv').open()))
    revisions=list(csv.DictReader((E4/'backend_pose_revisions.csv').open()))
    seams=list(csv.DictReader((E4/'pair_seams.csv').open()))
    provenance=np.load(E1/'provenance.npz'); frame_ids=provenance['frame_ids']; origin=float(tracking[0]['timestamp'])
    assert len(inputs)==len(tracking)==240 and len(events)==23
    assert all(int(r['frame_index'])==i for i,r in enumerate(tracking))
    gray_cache={}
    def gray(i):
        if i not in gray_cache:
            path=ROOT/'data/HKairport01/mapping'/inputs[i]['png_filename']
            assert sha(path)==inputs[i]['png_sha256']
            rgb=cv2.cvtColor(cv2.imread(str(path)),cv2.COLOR_BGR2RGB).astype(np.float32)/255
            im=resize_img(rgb,512)['unnormalized_img']
            gray_cache[i]=cv2.cvtColor(im,cv2.COLOR_RGB2GRAY)
        return gray_cache[i]
    def flow(a,b,xy):
        old=xy.astype(np.float32).reshape(-1,1,2)
        options=dict(winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01))
        new,s,_=cv2.calcOpticalFlowPyrLK(a,b,old,None,**options)
        back,bs,_=cv2.calcOpticalFlowPyrLK(b,a,new,None,**options)
        end=new[:,0,:]; fb=np.linalg.norm(back[:,0,:]-xy,axis=1); target=np.rint(end).astype(int)
        valid=s[:,0].astype(bool)&bs[:,0].astype(bool)&np.isfinite(end).all(axis=1)&(fb<=1.0)
        h,w=a.shape; valid &= (target[:,0]>=4)&(target[:,0]<w-4)&(target[:,1]>=4)&(target[:,1]<h-4)&(xy[:,0]>=4)&(xy[:,0]<w-4)&(xy[:,1]>=4)&(xy[:,1]<h-4)
        ncc=np.full(len(xy),np.nan)
        for i in np.flatnonzero(valid):
            x,y=xy[i]; u,v=target[i]; aa=a[y-4:y+5,x-4:x+5].astype(float); bb=b[v-4:v+5,u-4:u+5].astype(float)
            aa-=aa.mean();bb-=bb.mean(); den=np.linalg.norm(aa)*np.linalg.norm(bb)
            if den>1e-8:ncc[i]=(aa*bb).sum()/den
        valid &= ncc>=.8
        return end,valid,fb,ncc
    detail=[]; texture_bins=[]
    for r in events:
        k=int(r['kf']); f=int(r['frame']); reference=int(frame_ids[k]); entry=tracking[f]
        assert int(entry['reference_kf'])==k and entry['tracking_success']=='1'
        d=np.load(E3/'events'/f'kf{k}_update_frame{f}.npz'); p=d['pixel_index']; x=p%512;y=p//512
        image=gray(reference); current=gray(f); im=image.astype(np.float32)/255
        gx=cv2.Sobel(im,cv2.CV_32F,1,0,ksize=3)/8;gy=cv2.Sobel(im,cv2.CV_32F,0,1,ksize=3)/8
        gradient=np.hypot(gx,gy)[y,x]; corners=cv2.cornerMinEigenVal(im,blockSize=5,ksize=3)[y,x]
        q=np.sqrt(d['descriptor_conf_frame']*d['descriptor_conf_kf'])
        valid=d['valid_match'].astype(bool)&(q>1.5)&(d['frame_self_conf']>0)&(d['before_weight'].reshape(-1)/int(d['before_N'])>0)
        assert int(valid.sum())==int(r['valid_tracking_correspondences'])
        cuts=np.quantile(gradient,[.25,.5,.75]); bins=np.searchsorted(cuts,gradient,side='right')
        for bin_id in range(4):
            sel=bins==bin_id
            texture_bins.append({'kf':k,'frame':f,'texture_quartile':bin_id+1,'n_pixels':int(sel.sum()),'gradient_median':float(np.median(gradient[sel])) if sel.any() else None,'tracking_valid':int(valid[sel].sum()),'tracking_valid_fraction':float(valid[sel].mean()) if sel.any() else None})
        grid=(x%5==0)&(y%5==0); loc=np.flatnonzero(grid); xy=np.column_stack([x[grid],y[grid]]).astype(int)
        endpoint,flow_valid,fb,ncc=flow(image,current,xy)
        displacement=np.linalg.norm(endpoint-xy,axis=1); overlap=valid[loc]&flow_valid
        matches=d['matched_frame_pixel'][loc]; mast_xy=np.column_stack([matches%512,matches//512])
        endpoint_diff=np.linalg.norm(endpoint-mast_xy,axis=1)
        np.savez_compressed(OUT/f'kf{k}_frame{f}_flow.npz',source_xy=xy,flow_xy=endpoint,
                            flow_candidate=flow_valid,flow_fb=fb,patch_ncc=ncc,
                            mast3r_valid=valid[loc],mast3r_xy=mast_xy)
        if f in (149,164):
            check,axes_check=plt.subplots(1,2,figsize=(11,5),constrained_layout=True)
            for ax,img,coords in ((axes_check[0],image,xy),(axes_check[1],current,endpoint)):
                ax.imshow(img,cmap='gray',vmin=0,vmax=255)
                ax.scatter(coords[flow_valid,0],coords[flow_valid,1],s=7,c='lime',alpha=.7,label='flow candidate')
                ax.scatter(coords[overlap,0],coords[overlap,1],s=14,facecolors='none',edgecolors='red',label='also tracking-valid')
                ax.set_xlim(300,512);ax.set_ylim(285,150);ax.axis('off')
            axes_check[0].set_title(f'KF{k} reference');axes_check[1].set_title(f'frame {f}');axes_check[1].legend(loc='lower left')
            check.suptitle(f'Optical flow candidates: {flow_valid.sum()}/{len(xy)}; tracking-valid overlap: {overlap.sum()} (grid)')
            check.savefig(OUT/f'kf{k}_frame{f}_flow.png',dpi=160);plt.close(check)
        dt=float(entry['timestamp'])-float(tracking[reference]['timestamp'])
        row={'kf':k,'frame':f,'reference_frame':reference,'seconds':float(entry['timestamp'])-origin,
             'seconds_since_keyframe':dt,'new_keyframe':int(entry['new_keyframe']),'tracking_success':int(entry['tracking_success']),
             'update_number':int(r['updates_before']), 'roi_pixels':len(p),'roi_valid_tracking':int(valid.sum()),
             'roi_valid_tracking_fraction':float(valid.mean()),'valid_match_fraction':float(r['valid_match_fraction']),
             'q_pass_fraction':float(r['descriptor_q_pass_fraction']),
             'fusion_normal_median_abs_over_initial_span':abs(float(r['update_normal_shift_median_over_span'])),
             'input_weight_fraction_median':float(r['weight_fraction_median']),
             'gradient_median':float(np.median(gradient)),'gradient_p90':float(np.percentile(gradient,90)),
             'corner_min_eigen_median':float(np.median(corners)),'flow_grid_count':len(xy),'flow_candidates':int(flow_valid.sum()),
             'flow_candidate_fraction':float(flow_valid.mean()),'flow_displacement_median_px':float(np.median(displacement[flow_valid])) if flow_valid.any() else None,
             'flow_fb_p90_px':float(np.percentile(fb[flow_valid],90)) if flow_valid.any() else None,
             'flow_mast3r_valid_intersection':int(overlap.sum()),
             'flow_mast3r_endpoint_difference_median_px':float(np.median(endpoint_diff[overlap])) if overlap.any() else None}
        detail.append(row)
    e3_by_frame={r['frame']:r for r in detail}; e4_by_kf={}
    for r in revisions: e4_by_kf.setdefault(int(r['backend_kf']),r)
    pair_by_kf={}
    for r in seams:
        if r['kind']=='fused' and int(r['backend_kf'])>=36:
            pair_by_kf.setdefault(int(r['backend_kf']),{})[r['pair']]=r
    allrows=[]
    kf_for_frame={int(f):k for k,f in enumerate(frame_ids)}
    for i,t in enumerate(tracking):
        created=kf_for_frame.get(i); assert bool(created is not None)==bool(int(t['new_keyframe']))
        r={'frame':i,'timestamp':t['timestamp'],'seconds':float(t['timestamp'])-origin,
           'input_gap_seconds':float(t['timestamp'])-float(tracking[i-1]['timestamp']) if i else None,
           'reference_kf':t['reference_kf'],'tracking_success':int(t['tracking_success']),'new_keyframe':int(t['new_keyframe']),'created_kf':created}
        if i in e3_by_frame:
            e=e3_by_frame[i]
            for field in ('roi_valid_tracking_fraction','flow_candidate_fraction','flow_displacement_median_px','gradient_median','fusion_normal_median_abs_over_initial_span','input_weight_fraction_median'):
                r[field]=e[field]
        if created in e4_by_kf:
            v=e4_by_kf[created];r.update(backend_edges=int(v['edges']),backend_new_edges=int(v['new_edges']),backend_new_nonconsecutive_edges=int(v['new_nonconsecutive_edges']))
        for pair,values in pair_by_kf.get(created,{}).items():
            r[f'pair_{pair}_backend_signed_change']=float(values['change_signed_median'])
            r[f'pair_{pair}_backend_abs_change']=float(values['change_abs_median'])
        allrows.append(r)
    write_csv(OUT/'R4_timeline.csv',allrows); write_csv(OUT/'R4_roi_events.csv',detail);write_csv(OUT/'R4_texture_quartiles.csv',texture_bins)
    fig,axes=plt.subplots(4,1,figsize=(13,10),sharex=True,constrained_layout=True)
    for k in range(31,36):
        subset=[r for r in detail if r['kf']==k]; ts=[r['seconds'] for r in subset]
        axes[0].plot(ts,[r['roi_valid_tracking_fraction']*100 for r in subset],marker='o',label=f'KF{k}')
        axes[1].plot(ts,[r['fusion_normal_median_abs_over_initial_span']*100 for r in subset],marker='o')
        axes[2].plot(ts,[r['flow_displacement_median_px'] for r in subset],marker='o')
    for pair in ('32-35','31-34','33-35'):
        vals=[r for r in allrows if f'pair_{pair}_backend_abs_change' in r]
        axes[3].plot([r['seconds'] for r in vals],[r[f'pair_{pair}_backend_abs_change'] for r in vals],marker='.',label=pair)
    for ax in axes:
        for k in range(31,37): ax.axvline(float(tracking[int(frame_ids[k])]['timestamp'])-origin,color='gray',lw=.5,alpha=.5)
        ax.grid(alpha=.3)
    axes[0].set_ylabel('ROI valid matches (%)');axes[0].legend(ncol=5)
    axes[1].set_ylabel('abs median fusion shift\n(% initial ROI span)')
    axes[2].set_ylabel('candidate optical flow\nmedian displacement (px)')
    axes[3].set_ylabel('backend change in\nabsolute seam (map units)');axes[3].legend(ncol=3)
    axes[3].set_xlabel('seconds since first input');fig.savefig(OUT/'R4_timeline.png',dpi=170)
    summary={'input_frames':len(tracking),'tracking_successes':sum(int(t['tracking_success']) for t in tracking[1:]),'tracking_calls':len(tracking)-1,
             'keyframes':len(frame_ids),'detailed_roi_events':len(detail),
             'zero_roi_valid_events':sum(r['roi_valid_tracking']==0 for r in detail),
             'roi_valid_fraction_median':float(np.median([r['roi_valid_tracking_fraction'] for r in detail])),
             'flow_candidate_fraction_median':float(np.median([r['flow_candidate_fraction'] for r in detail])),
             'matching_definition':'E3 tracker mask vs independent optical-flow candidate, different criteria; neither is ground truth',
             'optical_flow_not_parallax':True,'opencv':cv2.__version__,
             'sha256':{'script':sha(Path(__file__)),'protocol':sha(ROOT/'configs/E5_timeline/protocol.json'),
                       'input_list':sha(ROOT/'data/HKairport01/mapping_frames.csv'),'tracking':sha(E1/'tracking_timeline.csv'),
                       'e3_events_csv':sha(E3/'fusion_events.csv'),'e4_seams':sha(E4/'pair_seams.csv'),
                       'e4_pose_revisions':sha(E4/'backend_pose_revisions.csv'),'e1_provenance':sha(E1/'provenance.npz'),
                       'e3_event_npz':{f.name:sha(f) for f in sorted((E3/'events').glob('*_update_frame*.npz'))}},
             'limitations':['correlation only; 5 KFs not independent scenes','flow is image displacement, not geometric parallax','no verified normal-region negative control','no edge residuals or causal intervention']}
    (OUT/'manifest.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
