from pathlib import Path
import colorsys
import sys
import numpy as np
from PIL import Image,ImageOps,ImageDraw
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from plyfile import PlyData,PlyElement
root=Path(__file__).resolve().parents[2]
out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'results/E1_baseline_reproduction/2026-10-27/one_second/instrumented'; source=out/'output'; k=np.load(out/'provenance.npz'); vertex=PlyData.read(source/'mapping.ply')['vertex'].data
assert len(vertex)==len(k['kf_id'])==len(k['pixel_index'])
ids=k['kf_id']; n=len(k['frame_ids']); palette=np.array([colorsys.hsv_to_rgb(i/max(n,1),.85,.9) for i in range(n)])
colored=vertex.copy()
for c,name in enumerate(('red','green','blue')): colored[name]=(255*palette[ids,c]).astype(np.uint8)
PlyData([PlyElement.describe(colored,'vertex')],text=False).write(out/'map_keyframe_colors.ply')
imgs=sorted((source/'keyframes/mapping').glob('*.png'),key=lambda p:float(p.stem)); assert len(imgs)==n
canvas=Image.new('RGB',(1024,((n+1)//2)*300),'white'); draw=ImageDraw.Draw(canvas)
for i,p in enumerate(imgs):
 x=(i%2)*512; y=(i//2)*300; img=ImageOps.contain(Image.open(p).convert('RGB'),(500,270));canvas.paste(img,(x,y+24)); rgb=tuple((palette[i]*255).astype(int)); draw.text((x+4,y+4),f'KF {i}  frame={k["frame_ids"][i]}  time={p.stem}',fill=rgb,stroke_width=0)
canvas.save(out/'keyframe_contact.png')
xyz=np.column_stack([vertex[a] for a in ('x','y','z')]); assert np.isfinite(xyz).all(); rng=np.random.default_rng(42); sample=rng.choice(len(xyz),min(300000,len(xyz)),replace=False); sample_xyz=xyz[sample]; lo=np.quantile(sample_xyz,.01,axis=0); hi=np.quantile(sample_xyz,.99,axis=0); sample=sample[np.all((sample_xyz>=lo)&(sample_xyz<=hi),axis=1)]; sample_xyz=xyz[sample];
fig,axes=plt.subplots(1,3,figsize=(18,6),constrained_layout=True)
for ax,(a,b) in zip(axes,((0,1),(0,2),(2,1))):
 ax.scatter(sample_xyz[:,a],sample_xyz[:,b],c=palette[ids[sample]],s=.14,alpha=.45,rasterized=True); ax.set_xlabel('world '+ 'xyz'[a]+' (arbitrary units)');ax.set_ylabel('world '+ 'xyz'[b]+' (arbitrary units)');ax.set_aspect('equal',adjustable='box'); ax.set_title('XYZ'[a]+'–'+'XYZ'[b])
fig.suptitle('Keyframe colors: 1–99% clipped sample; axes are not gravity-aligned'); fig.savefig(out/'map_keyframe_views.png',dpi=160);plt.close(fig)
print('points:',len(vertex),'keyframes:',n,'finite:',np.isfinite(xyz).all(),'counts:',np.bincount(ids,minlength=n).tolist())
