from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/E7c_surface_calibration_qa/2026-10-28/calibration_qa';d=np.load(OUT/'numeric_grid.npz');p=d['pixel']; fig,axs=plt.subplots(1,2,figsize=(11,5),constrained_layout=True)
for ax,key,title in zip(axs,['error5','error100'],['5 iterations','100 iterations']):
 e=d[key];colors=np.where(e>=1,'#c83f3f',np.where(e>=.1,'#e0aa30','#326ea6'));ax.scatter(p[:,0],p[:,1],c=colors,s=3);ax.set(xlabel='native x (px)',ylabel='native y (px)',title=title);ax.invert_yaxis();ax.set_aspect('equal')
from matplotlib.lines import Line2D
fig.legend(handles=[Line2D([0],[0],marker='o',color='w',markerfacecolor=c,label=l,markersize=6) for c,l in [('#326ea6','< 0.1 px'),('#e0aa30','0.1–1 px'),('#c83f3f','≥ 1 px')]],loc='lower center',ncol=3)
fig.suptitle('Conditional camera-LiDAR model: pixel inverse/forward round-trip; not physical calibration proof');fig.savefig(OUT/'inverse_roundtrip.png',dpi=160)
