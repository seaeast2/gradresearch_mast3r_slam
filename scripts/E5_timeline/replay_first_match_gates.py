"""Replay only the first tracking update after each selected KF; matching starts reset."""
import csv,hashlib,json,os,sys
from pathlib import Path
import cv2
import numpy as np
import torch
import lietorch

ROOT=Path(__file__).resolve().parents[2]; UPSTREAM=ROOT/'thirdparty/MASt3R-SLAM'
sys.path.insert(0,str(UPSTREAM))
from mast3r_slam.config import load_config,config
from mast3r_slam.frame import create_frame
from mast3r_slam.mast3r_utils import load_mast3r,mast3r_asymmetric_inference
from mast3r_slam import matching
import mast3r_slam_backends

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    os.chdir(UPSTREAM);torch.backends.cuda.matmul.allow_tf32=True;torch.set_grad_enabled(False)
    load_config(str(ROOT/'configs/E0_environment_preparation/low_vram_base.yaml'))
    model=load_mast3r(device='cuda:0');out=ROOT/'results/E5_timeline/2026-10-28/timeline'
    e3=ROOT/'results/E3_fusion/2026-10-28/instrumented'; prov=np.load(ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry/provenance.npz')
    inputs=list(csv.DictReader((ROOT/'data/HKairport01/mapping_frames.csv').open()));rows=[]
    for k in range(31,36):
        ref=int(prov['frame_ids'][k]); current=ref+1
        d=np.load(e3/'events'/f'kf{k}_update_frame{current}.npz'); pixel=d['pixel_index']
        frames=[]
        for i in (current,ref):
            p=ROOT/'data/HKairport01/mapping'/inputs[i]['png_filename']; assert sha(p)==inputs[i]['png_sha256']
            rgb=cv2.cvtColor(cv2.imread(str(p)),cv2.COLOR_BGR2RGB).astype(np.float32)/255
            frames.append(create_frame(i,rgb,lietorch.Sim3.Identity(1,device='cuda:0'),img_size=512,device='cuda:0'))
        X,C,D,Q=mast3r_asymmetric_inference(model,*frames)
        X11,X21=X[0:1],X[1:2];D11,D21=D[0:1],D[1:2];b,h,w=X21.shape[:3]
        rays,pts,pinit=matching.prep_for_iter_proj(X11,X21,None)
        p,valid_project=mast3r_slam_backends.iter_proj(rays,pts,pinit,config['matching']['max_iter'],config['matching']['lambda_init'],config['matching']['convergence_thresh'])
        p=p.long(); batch=torch.arange(b,device='cuda:0')[:,None].repeat(1,h*w)
        dist=torch.linalg.norm(X11[batch,p[...,1],p[...,0],:].reshape(b,h,w,3)-X21,dim=-1).reshape(b,-1)
        distance_ok=dist<config['matching']['dist_thresh']
        indices,valid=matching.match(X11,X21,D11,D21)
        iv=valid[0,:,0].cpu().numpy()[pixel]; expected=d['valid_match'].reshape(-1)
        idx=indices[0].cpu().numpy()[pixel]; agree_mask=np.array_equal(iv,expected);agree_idx=np.array_equal(idx,d['matched_frame_pixel'])
        proj=valid_project[0].cpu().numpy()[pixel];distances=dist[0].cpu().numpy()[pixel];dok=distance_ok[0].cpu().numpy()[pixel]
        rows.append({'kf':k,'frame':current,'roi_pixels':len(pixel),'projection_pass':int(proj.sum()),'distance_pass':int(dok.sum()),
                     'both_pass':int((proj&dok).sum()),'valid_e3':int(expected.sum()),'match_mask_exact':agree_mask,'match_indices_exact':agree_idx,
                     'distance_threshold_local':config['matching']['dist_thresh'],'distance_median_local':float(np.median(distances)),
                     'distance_p10_local':float(np.percentile(distances,10)),'distance_p90_local':float(np.percentile(distances,90))})
        np.savez_compressed(out/f'kf{k}_frame{current}_match_gates.npz',pixel_index=pixel,projection_pass=proj,distance=distances,distance_pass=dok,match_valid=iv,match_index=idx)
        print(json.dumps(rows[-1]),flush=True);del X,C,D,Q,frames;torch.cuda.empty_cache()
    with (out/'R4_first_match_gates.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    manifest={'script_sha256':sha(Path(__file__)),'checkpoint_sha256':sha(UPSTREAM/'checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth'),
              'note':'Only first tracking update after a new KF; tracker resets match initial guess on KF creation; E3 match-mask and match-index parity tested.', 'rows':rows}
    (out/'match_gates_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
