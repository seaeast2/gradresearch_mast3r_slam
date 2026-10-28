from pathlib import Path
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[2]
out = root / 'results/E2_raw_pointmap/2026-10-28/raw_pairs'
rows = []
fig, axes = plt.subplots(5, 2, figsize=(12, 12), constrained_layout=True)
for i, kf in enumerate(range(31, 36)):
    for j, case in enumerate(('birth_self', 'next_cross')):
        d = np.load(out/f'kf{kf}_{case}.npz')
        p = d['xyz'].astype(np.float64); valid=d['valid']; pix=d['pixel_index']; center=d['plane_center']; normal=d['plane_normal']
        residual=(p-center)@normal
        x=pix%512; y=pix//512
        xm=(x.min()+x.max())/2; ym=(y.min()+y.max())/2
        angles=[]
        for sx in (x<=xm, x>xm):
            for sy in (y<=ym, y>ym):
                tile=valid & sx & sy
                if tile.sum()<30: continue
                q=p[tile]; _,_,v=np.linalg.svd(q-q.mean(axis=0),full_matrices=False)
                angles.append(np.degrees(np.arccos(np.clip(abs(v[-1]@normal),0,1))))
        rows.append(dict(kf=kf,case=case,subregion_count=len(angles),normal_angle_max_deg=max(angles),
                         z_p10=np.percentile(p[valid,2],10),z_median=np.median(p[valid,2]),z_p90=np.percentile(p[valid,2],90),
                         confidence_p90=np.percentile(d['confidence'][valid],90)))
        image=np.full((416,512),np.nan); image.flat[pix]=residual
        lim=np.percentile(np.abs(residual[valid]),98)
        axes[i,j].imshow(image[y.min():y.max()+1, x.min():x.max()+1],cmap='coolwarm',vmin=-lim,vmax=lim,aspect='auto')
        axes[i,j].set_title(f'KF {kf} {case}; color range ±{lim:.3g} local units')
        axes[i,j].axis('off')
fig.savefig(out/'R1_signed_residual_maps.png',dpi=140)
with (out/'R1_auxiliary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
