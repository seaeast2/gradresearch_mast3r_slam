from pathlib import Path
import json
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image,ImageDraw
from plyfile import PlyData
root=Path(__file__).resolve().parents[2]; out=root/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'; source=out/'output'; d=np.load(out/'provenance.npz'); vertex=PlyData.read(source/'mapping.ply')['vertex'].data
ids=d['kf_id']; pix=d['pixel_index']; h,w=d['image_shape']; assert len(ids)==len(pix)==len(vertex); spec=json.loads((root/'configs/E1_baseline_reproduction/periodic_1s_rois.json').read_text()); assert [h,w]==spec['image_shape_hw']; polys=spec['polygons_xy']; ref=spec['reference_kf']; xyz=np.column_stack([vertex[k] for k in 'xyz']); assert np.isfinite(xyz).all(); selected=np.zeros(len(ids),dtype=bool)
images=sorted((source/'keyframes/mapping').glob('*.png'),key=lambda p:float(p.stem)); canvas=Image.new('RGB',(1024,((len(polys)+1)//2)*440),'white'); draw=ImageDraw.Draw(canvas)
for j,key in enumerate(polys):
 i=int(key); polygon=polys[key]; m=np.zeros((h,w),np.uint8); cv2.fillPoly(m,[np.asarray(polygon,np.int32)],1); sel=ids==i; selected[sel]=m.reshape(-1)[pix[sel]]!=0
 im=Image.open(images[i]).convert('RGB'); ddraw=ImageDraw.Draw(im); ddraw.line([tuple(p) for p in polygon]+[tuple(polygon[0])],fill='magenta',width=3); x=(j%2)*512;y=(j//2)*440; canvas.paste(im,(x,y+24));draw.text((x+5,y+5),f'KF {i}: {images[i].stem}',fill='black')
canvas.save(out/'pavement_roi_images.png')
q=xyz[(ids==ref)&selected]; mean=q.mean(axis=0); _,_,vh=np.linalg.svd(q[::max(1,len(q)//50000)]-mean,full_matrices=False); n=vh[-1];n=n if n[2]>0 else -n
rng=np.random.default_rng(17); fig,ax=plt.subplots(figsize=(14,6),constrained_layout=True); cmap=plt.get_cmap('tab10'); stats={}
for j,key in enumerate(polys):
 i=int(key); idx=np.flatnonzero((ids==i)&selected); stats[key]=int(len(idx)); idx=rng.choice(idx,min(len(idx),20000),replace=False); q=xyz[idx]-mean; ax.scatter(q@vh[0],q@n,s=.35,alpha=.22,color=cmap(j),label=f'KF {i}',rasterized=True)
ax.set_xlabel('KF29 ROI principal tangent (arbitrary units)');ax.set_ylabel('signed distance from KF29 plane (arbitrary units)');ax.set_title('Exploratory pavement ROIs; equal x does not prove same physical surface');ax.legend(markerscale=7,ncol=4);fig.savefig(out/'pavement_by_keyframe.png',dpi=180);plt.close(fig)
(out/'pavement_roi_summary.json').write_text(json.dumps({'roi_counts':stats,'reference_kf':ref,'reference_normal':n.tolist(),'same_surface_correspondence_verified':False},indent=2)+'\n');print(stats)
