from pathlib import Path
import numpy as np
from PIL import Image,ImageOps,ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from plyfile import PlyData
root=Path(__file__).resolve().parents[2]
src=root/'results/E0a_keyframe_spacing/2026-10-27/candidate_2s/output'
out=root/'results/E1_baseline_reproduction/2026-10-27/quicklook'
out.mkdir(parents=True,exist_ok=True)
imgs=sorted((src/'keyframes/mapping').glob('*.png'),key=lambda p:float(p.stem))
canvas=Image.new('RGB',(1200,720),'white'); draw=ImageDraw.Draw(canvas)
for i,p in enumerate(imgs):
 im=ImageOps.contain(Image.open(p).convert('RGB'),(590,330)); x=(i%2)*600; y=(i//2)*240; im.thumbnail((585,210)); canvas.paste(im,(x,y+24)); draw.text((x+5,y+4),f'KF {i}: {p.stem}',fill='black')
canvas.save(out/'keyframe_contact.png')
v=PlyData.read(src/'mapping.ply')['vertex'].data
rng=np.random.default_rng(42); ids=rng.choice(len(v),min(300000,len(v)),replace=False)
xyz=np.column_stack([v[a][ids] for a in ('x','y','z')]); color=np.column_stack([v[a][ids] for a in ('red','green','blue')])/255
mask=np.isfinite(xyz).all(axis=1)
xyz=xyz[mask]; color=color[mask]
lo=np.quantile(xyz,.01,axis=0); hi=np.quantile(xyz,.99,axis=0); keep=np.all((xyz>=lo)&(xyz<=hi),axis=1); xyz=xyz[keep]; color=color[keep]
fig,axes=plt.subplots(1,3,figsize=(18,6),constrained_layout=True)
for ax,(a,b) in zip(axes,[(0,1),(0,2),(2,1)]):
 ax.scatter(xyz[:,a],xyz[:,b],c=color,s=.1,alpha=.35,rasterized=True); ax.set_xlabel('world '+ 'xyz'[a]+' (arbitrary units)');ax.set_ylabel('world '+ 'xyz'[b]+' (arbitrary units)');ax.set_aspect('equal',adjustable='box');ax.set_title('XYZ'[a]+'–'+'XYZ'[b])
fig.suptitle('MASt3R-SLAM map: random sample; global 1–99% clipping; axes not gravity-aligned');fig.savefig(out/'world_views.png',dpi=180);plt.close(fig)
print('all points',len(v),'sample after global clipping',len(xyz),'limits',lo.tolist(),hi.tolist())
