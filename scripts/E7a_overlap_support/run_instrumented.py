"""Run the existing main.py with read-only ROI probes on tracker updates."""
import json
import os
import runpy
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / 'thirdparty/MASt3R-SLAM'
sys.path.insert(0, str(UPSTREAM))

def main():
    import mast3r_slam.evaluate as evaluate
    from mast3r_slam.frame import Frame
    import mast3r_slam.tracker as tracker
    from mast3r_slam.tracker import FrameTracker

    out = Path(os.environ['E3_OUTPUT']).resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec=json.loads((ROOT/'configs/E7a_overlap_support/regions.json').read_text())
    provenance=np.load(ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline/provenance.npz')
    targets={int(provenance['frame_ids'][k]):k for k in spec['keyframes']}
    roi={}
    for frame_id,kf in targets.items():
        mask=np.zeros((416,512),np.uint8)
        cv2.fillPoly(mask,[np.asarray(poly,np.int32) for poly in spec['capture_polygons_xy']],1)
        roi[frame_id]=np.flatnonzero(mask.ravel())
    context={}
    original_track=FrameTracker.track
    original_update=Frame.update_pointmap
    original_match=tracker.mast3r_match_asymmetric
    original_pose=FrameTracker.opt_pose_ray_dist_sim3

    def array(t, indices=None):
        if indices is not None:
            t=t[torch.as_tensor(indices,device=t.device)]
        return t.detach().cpu().numpy().copy()

    def match(*args,**kwargs):
        result=original_match(*args,**kwargs)
        if context.get('reference') in targets:
            idx, valid, xff, cff, qff, xkf, ckf, qkf=result
            p=roi[context['reference']]
            matched=array(idx[0,:,0] if idx.ndim==3 else idx[0],p)
            context['match']={
                'matched_frame_pixel':matched,
                'valid_match':array(valid[0].reshape(-1),p),
                'descriptor_conf_kf':array(qkf.reshape(-1),p),
                'descriptor_conf_frame':array(qff.reshape(-1),matched),
                'frame_self_conf':array(cff.reshape(-1),matched),
            }
        return result

    def pose(self,*args,**kwargs):
        result=original_pose(self,*args,**kwargs)
        if context.get('reference') in targets:
            context['relative_sim3']=array(result[1].data)
        return result

    def update(self,X,C):
        if not context or self.frame_id not in targets:
            return original_update(self,X,C)
        current=context['current']; ref=context['reference']
        if self.frame_id==current:
            result=original_update(self,X,C)
            p=roi[self.frame_id]
            np.savez_compressed(out/f"kf{targets[self.frame_id]}_initial_frame{current}.npz",
                                pixel_index=p, xyz=array(self.X_canon,p), confidence=array(self.C,p),
                                frame_id=current, reference_frame=ref)
            return result
        if self.frame_id!=ref:
            return original_update(self,X,C)
        p=roi[ref]
        saved={'pixel_index':p,'before_xyz':array(self.X_canon,p),'before_weight':array(self.C,p),
               'input_xyz':array(X,p),'input_weight':array(C,p),'before_N':self.N,
               'before_updates':self.N_updates,'frame_id':current,'keyframe_frame_id':ref,
               'relative_sim3':context['relative_sim3'], **context['match']}
        result=original_update(self,X,C)
        saved.update(after_xyz=array(self.X_canon,p),after_weight=array(self.C,p),after_N=self.N,after_updates=self.N_updates)
        np.savez_compressed(out/f"kf{targets[ref]}_update_frame{current}.npz",**saved)
        return result

    def track(self,frame,*args,**kwargs):
        context.clear()
        context.update(current=frame.frame_id,reference=self.keyframes.last_keyframe().frame_id)
        try:
            return original_track(self,frame,*args,**kwargs)
        finally:
            context.clear()

    original_save = evaluate.save_reconstruction
    def save_reconstruction(savedir, filename, keyframes, threshold):
        poses = np.stack([keyframes[k].T_WC.data.detach().cpu().numpy().reshape(-1) for k in range(len(keyframes))])
        np.save(out.parent/'final_sim3.npy', poses)
        return original_save(savedir, filename, keyframes, threshold)
    evaluate.save_reconstruction = save_reconstruction
    tracker.mast3r_match_asymmetric=match
    FrameTracker.opt_pose_ray_dist_sim3=pose
    Frame.update_pointmap=update
    FrameTracker.track=track
    os.chdir(UPSTREAM)
    sys.argv=[str(UPSTREAM/'main.py'), '--dataset',str(ROOT/'data/AMtown01/mapping'),
              '--config',str(ROOT/'configs/E0_environment_preparation/low_vram_base.yaml'),
              '--no-viz','--save-as',os.environ['E3_RUN_ID'],'--keyframe-buffer','64','--low-vram',
              '--frame-time-csv',str(ROOT/'data/AMtown01/mapping_frames.csv'),
              '--min-keyframe-seconds','1','--force-periodic-keyframes']
    runpy.run_path(str(UPSTREAM/'main.py'),run_name='__main__')

if __name__=='__main__':
    main()
