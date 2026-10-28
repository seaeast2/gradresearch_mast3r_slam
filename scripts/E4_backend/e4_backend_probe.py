"""Backend wrapper, imported by the spawned process of an E1-equivalent run."""
import json
import os
from pathlib import Path
import cv2
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]

def run_backend(cfg,model,states,keyframes,K):
    from mast3r_slam.global_opt import FactorGraph
    from main import run_backend as original_backend
    dest=Path(os.environ['E4_EVENTS']); dest.mkdir(parents=True,exist_ok=True)
    spec=json.loads((ROOT/'configs/E1_baseline_reproduction/periodic_1s_rois.json').read_text())
    roi={}
    for k in range(31,36):
        mask=np.zeros((416,512),np.uint8)
        cv2.fillPoly(mask,[np.asarray(spec['polygons_xy'][str(k)],np.int32)],1)
        roi[k]=np.flatnonzero(mask.ravel())
    old_solve=FactorGraph.solve_GN_rays
    def snapshot(graph):
        n=len(graph.frames)
        # Backend operates single-threaded with the front end waiting for this task.
        data={'n_keyframes':n,'poses':graph.frames.T_WC[:n].detach().cpu().numpy().copy(),
              'ii':graph.ii.detach().cpu().numpy().copy(),'jj':graph.jj.detach().cpu().numpy().copy()}
        for k in roi:
            if k<n:
                idx=torch.as_tensor(roi[k],device=graph.frames.X.device)
                data[f'xyz_{k}']=graph.frames.X[k,idx].detach().cpu().numpy().copy()
                data[f'frame_id_{k}']=int(graph.frames.dataset_idx[k])
        return data
    def solve(graph):
        n=len(graph.frames)
        if n<31:
            return old_solve(graph)
        before=snapshot(graph)
        result=old_solve(graph)
        after=snapshot(graph)
        save={f'pre_{key}':value for key,value in before.items()}
        save.update({f'post_{key}':value for key,value in after.items()})
        np.savez_compressed(dest/f'backend_{n-1:03d}.npz',**save)
        print(f'E4_BACKEND newest_kf={n-1} edges={len(before["ii"])}',flush=True)
        return result
    FactorGraph.solve_GN_rays=solve
    return original_backend(cfg,model,states,keyframes,K)
