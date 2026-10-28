"""Build inspectable E7 KF/source-pixel support without assigning a surface class."""
import csv,hashlib,json,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from plyfile import PlyData
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'thirdparty/MASt3R-SLAM'))
from mast3r_slam.mast3r_utils import resize_img
SRC=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline';OUT=ROOT/'results/E7c_surface_calibration_qa/2026-10-28/provenance_review'; OUT.mkdir(parents=True,exist_ok=False);(OUT/'masks').mkdir();rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open())); prov=np.load(SRC/'provenance.npz');ids=prov['kf_id'];pix=prov['pixel_index'];frame=prov['frame_ids'];H,W=map(int,prov['image_shape']);assert (H,W)==(416,512);ply=PlyData.read(SRC/'output/mapping.ply');v=ply['vertex'].data;assert len(v)==len(ids)==len(pix) and ids.min()>=0 and ids.max()<len(frame) and pix.min()>=0 and pix.max()<H*W
kfimages=sorted((SRC/'output/keyframes/mapping').glob('*.png'),key=lambda p:float(p.stem));assert len(kfimages)==len(frame);tables=[]; page=None;shape_diffs=[]
for k,fid in enumerate(frame):
 fid=int(fid);path=ROOT/'data/AMtown01/mapping'/rows[fid]['png_filename'];buf=path.read_bytes();assert hashlib.sha256(buf).hexdigest()==rows[fid]['png_sha256'];raw=cv2.cvtColor(cv2.imdecode(np.frombuffer(buf,np.uint8),cv2.IMREAD_COLOR),cv2.COLOR_BGR2RGB).astype(np.float32)/255;image=resize_img(raw,512)['unnormalized_img']; actual=np.asarray(Image.open(kfimages[k]).convert('RGB')); diff=int(np.max(abs(image.astype(np.int16)-actual.astype(np.int16))));shape_diffs.append(diff);assert diff<=1
 sel=ids==k;ip=pix[sel];count=len(ip);assert len(np.unique(ip))==count;mask=np.zeros(H*W,np.uint8);mask[ip]=255;mask=mask.reshape(H,W);Image.fromarray(mask).save(OUT/'masks'/f'kf{k:02d}_export_support.png');tables.append({'kf_id':k,'frame_id':fid,'rgb_timestamp':rows[fid]['rgb_timestamp'],'source_png':rows[fid]['png_filename'],'source_png_sha256':rows[fid]['png_sha256'],'export_points':count,'image_pixels':H*W,'export_fraction':count/(H*W),'unique_pixels':len(np.unique(ip)),'keyframe_image_max_rgb_difference':diff,'export_mask':f'masks/kf{k:02d}_export_support.png'})
 page_index=k//9;tile=k%9
 if tile==0:page=Image.new('RGB',(W*3,(H+24)*3),'white');draw=ImageDraw.Draw(page)
 x=(tile%3)*W;y=(tile//3)*(H+24);page.paste(Image.fromarray(image),(x,y+24));draw.text((x+5,y+4),f'KF {k} | frame {fid} | export {count} pixels',fill='black')
 if tile==8 or k==len(frame)-1:page.save(OUT/f'keyframes_page_{page_index+1}.jpg',quality=90)
with (OUT/'kf_provenance.csv').open('w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=tables[0]);writer.writeheader();writer.writerows(tables)
assert sum(t['export_points'] for t in tables)==len(v)
manifest={'frames':len(frame),'vertices':len(v),'all_source_hashes_match':True,'pixel_indices_in_bounds':True,'per_kf_pixel_unique':True,'count_aggregation_matches_ply':True,'keyframe_image_max_rgb_difference':max(shape_diffs),'surface_mask':'NOT PROVIDED: export masks represent available points, not user-confirmed physical surface','sources':{'ply':str((SRC/'output/mapping.ply').relative_to(ROOT)),'provenance':str((SRC/'provenance.npz').relative_to(ROOT))},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
