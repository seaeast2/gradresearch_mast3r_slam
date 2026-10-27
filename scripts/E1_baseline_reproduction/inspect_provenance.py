from pathlib import Path
import json
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image,ImageDraw
from plyfile import PlyData
root=Path(__file__).resolve().parents[2]
out=root/'results/E1_baseline_reproduction/2026-10-27/quicklook'
p=out/'output'; data=np.load(out/'provenance.npz'); v=PlyData.read(p/'mapping.ply')['vertex'].data
kf=data['kf_id']; pix=data['pixel_index']; h,w=data['image_shape']; assert len(v)==len(kf)==len(pix); assert 0<=pix.min() and pix.max()<h*w
xyz=np.column_stack([v[k] for k in ('x','y','z')]); assert np.isfinite(xyz).all()
polys=json.loads((root/'configs/E1_baseline_reproduction/quicklook_rois.json').read_text())['polygons_xy']; chosen=np.zeros(len(v),dtype=bool)
images=sorted((p/'keyframes/mapping').glob('*.png'),key=lambda x:float(x.stem))
canvas=Image.new('RGB',(1024,1248),'white')
for i,f in enumerate(images):
 im=Image.open(f).convert('RGB'); d=ImageDraw.Draw(im); polygon=polys.get(str(i));
 if polygon:
  d.line([tuple(x) for x in polygon]+[tuple(polygon[0])],fill='magenta',width=3)
  mask=np.zeros((h,w),np.uint8); cv2.fillPoly(mask,[np.array(polygon,dtype=np.int32)],1); sel=(kf==i); chosen[sel]=mask.reshape(-1)[pix[sel]]>0
 canvas.paste(im,((i%2)*512,(i//2)*416))
canvas.save(out/'pavement_roi_images.png')
q=xyz[(kf==1)&chosen]; mean=q.mean(axis=0); _,_,vh=np.linalg.svd(q[::max(1,len(q)//50000)]-mean,full_matrices=False); normal=vh[-1]; normal=normal if normal[2]>0 else -normal
# Tangent coordinates follow the first two principal directions of KF1 ROI.
tangent=vh[0]; height=(xyz-mean)@normal; along=(xyz-mean)@tangent
rng=np.random.default_rng(17); fig,ax=plt.subplots(figsize=(14,5),constrained_layout=True)
colors=['#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00']
for i in range(5):
 ids=np.flatnonzero((kf==i)&chosen); ids=rng.choice(ids,min(len(ids),30000),replace=False)
 ax.scatter(along[ids],height[ids],s=.25,alpha=.26,color=colors[i],label=f'KF {i} n={len(ids)}',rasterized=True)
ax.set_xlabel('KF1 ROI principal tangent (arbitrary units)');ax.set_ylabel('signed distance from KF1 fitted plane (arbitrary units)');ax.set_title('Exploratory pavement ROIs: separate KF sources; overlapping x does not prove same physical surface');ax.legend(markerscale=9); fig.savefig(out/'pavement_by_keyframe.png',dpi=180);plt.close(fig)
print('point count',len(v),'point counts by KF',np.bincount(kf).tolist(),'ROI counts',[int(((kf==i)&chosen).sum()) for i in range(6)],'reference normal',normal.tolist())
