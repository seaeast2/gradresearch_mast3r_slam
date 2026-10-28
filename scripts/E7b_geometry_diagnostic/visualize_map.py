import json
from pathlib import Path
import numpy as np
from plyfile import PlyData
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'results/E7_validation/2026-10-28/kf_colored/mapping_keyframe_colors.ply';OUT=ROOT/'results/E7b_geometry_diagnostic/2026-10-28/e7b_amtown_backend';v=PlyData.read(P)['vertex'].data;rng=np.random.default_rng(20261028);sel=np.sort(rng.choice(len(v),size=min(400000,len(v)),replace=False));x=np.column_stack([v[n][sel] for n in 'xyz']);c=np.column_stack([v[n][sel] for n in ('red','green','blue')])/255.
fig,axs=plt.subplots(1,3,figsize=(18,6),constrained_layout=True)
for ax,(i,j) in zip(axs,[(0,1),(0,2),(1,2)]):
 ax.scatter(x[:,i],x[:,j],s=.15,c=c,alpha=.5,rasterized=True);ax.set_aspect('equal',adjustable='box');ax.set_xlabel('world '+ 'XYZ'[i]+' (map units)');ax.set_ylabel('world '+ 'XYZ'[j]+' (map units)');ax.grid(alpha=.15)
fig.suptitle('All exported points, sampled, colored by KF; no surface segmentation');fig.savefig(OUT/'all_point_kf_orthogonal.png',dpi=170)
(OUT/'view_manifest.json').write_text(json.dumps({'source':str(P.relative_to(ROOT)),'total_points':len(v),'sample_count':len(sel),'random_seed':20261028,'visualization_only':'all exported points; this is not a mask of the user-confirmed surface; equal world-axis scaling, arbitrary units'},indent=2)+'\n')
