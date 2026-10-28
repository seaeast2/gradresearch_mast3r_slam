"""Capture only backend pose and graph snapshots around each solve."""
import os
from pathlib import Path
import numpy as np

def run_backend(cfg,model,states,keyframes,K):
    from mast3r_slam.global_opt import FactorGraph
    from main import run_backend as original_backend
    dest=Path(os.environ['E7B_EVENTS']);dest.mkdir(parents=True,exist_ok=True)
    old_solve=FactorGraph.solve_GN_rays
    def snap(graph):
        n=len(graph.frames)
        return {'poses':graph.frames.T_WC[:n].detach().cpu().numpy().copy(),
                'ii':graph.ii.detach().cpu().numpy().copy(),
                'jj':graph.jj.detach().cpu().numpy().copy(),
                'frame_ids':graph.frames.dataset_idx[:n].detach().cpu().numpy().copy()}
    def solve(graph):
        n=len(graph.frames);before=snap(graph);result=old_solve(graph);after=snap(graph)
        data={f'pre_{k}':v for k,v in before.items()};data.update({f'post_{k}':v for k,v in after.items()})
        np.savez_compressed(dest/f'backend_{n-1:03d}.npz',**data)
        print(f'E7B_BACKEND newest_kf={n-1} edges={len(before["ii"])}',flush=True)
        return result
    FactorGraph.solve_GN_rays=solve
    return original_backend(cfg,model,states,keyframes,K)
