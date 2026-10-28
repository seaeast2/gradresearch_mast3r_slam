import csv, hashlib, io, json, zipfile
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
ROOT=Path(__file__).resolve().parents[2]
src=Path('/home/hlee221212/works/gradresearch')
split=src/'configs/e4e_input_split.json'; archive=src/'data/E4e/archives/interval1_AMtown01.zip'
out=ROOT/'data/AMtown01/mapping'; report=ROOT/'results/E7_validation/2026-10-28/preflight'; out.mkdir(parents=True,exist_ok=True);report.mkdir(parents=True,exist_ok=True)
frames=[x for x in json.loads(split.read_text())['scene_splits']['AMtown01']['frames'] if x['role']=='mapping'];assert len(frames)==240
rows=[]; canvas=Image.new('RGB',(1200,900),'white'); draw=ImageDraw.Draw(canvas)
with zipfile.ZipFile(archive) as z:
 members=[x for x in z.namelist() if '/interval1_CAM/' in x and x.endswith('.jpg')]
 stamps=[float(Path(x).stem) for x in members]
 for i,f in enumerate(frames):
  j=min(range(len(stamps)),key=lambda n:abs(stamps[n]-f['rgb_timestamp'])); assert abs(stamps[j]-f['rgb_timestamp'])<1e-6
  actual_member=members[j]; data=z.read(actual_member); name=f'{i:04d}.png'; jpg=f'{i:04d}.jpg'
  (out/jpg).write_bytes(data); im=Image.open(io.BytesIO(data)).convert('RGB');im.save(out/name)
  rows.append({'input_index':i,'grid_index':f['grid_index'],'grid_timestamp':f['grid_timestamp'],'rgb_timestamp':f['rgb_timestamp'],'rgb_member':actual_member,'filename':jpg,'sha256':hashlib.sha256(data).hexdigest(),'png_filename':name,'png_sha256':hashlib.sha256((out/name).read_bytes()).hexdigest(),'width':im.width,'height':im.height})
  if i in [0,48,96,144,192,239]:
   j=[0,48,96,144,192,239].index(i); im.thumbnail((600,425));x=(j%2)*600;y=(j//2)*300; im.thumbnail((600,270)); canvas.paste(im,(x,y+20));draw.text((x+5,y+3),f'frame {i}',fill='black')
with (ROOT/'data/AMtown01/mapping_frames.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
canvas.save(report/'contact_sheet.jpg')
(report/'inputs.json').write_text(json.dumps({'sequence':'AMtown01','count':len(rows),'source_split_sha256':hashlib.sha256(split.read_bytes()).hexdigest(),'archive':str(archive),'archive_sha256_recorded':'5670cda374096f22804a8a907783a68d609a1247a52e04c97ad57f165a97006e','png_csv_sha256':hashlib.sha256((ROOT/'data/AMtown01/mapping_frames.csv').read_bytes()).hexdigest(),'image_shapes':sorted(set((r['width'],r['height']) for r in rows))},indent=2)+'\n')
print('prepared',len(rows))
