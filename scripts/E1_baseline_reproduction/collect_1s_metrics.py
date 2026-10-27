from pathlib import Path
import csv,hashlib,json,re
import numpy as np
from plyfile import PlyData
root=Path(__file__).resolve().parents[2]; base=root/'results/E1_baseline_reproduction/2026-10-27/one_second'; meta={}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
for name in ('baseline','instrumented'):
 p=base/name; log=(p/'run.log').read_text(); rows=[x.split() for x in (p/'output/mapping.txt').read_text().splitlines()]; times=np.array([float(x[0]) for x in rows]); gaps=np.diff(times); vertices=PlyData.read(p/'output/mapping.ply')['vertex'].data; gpu=np.genfromtxt(p/'gpu.csv',delimiter=',',skip_header=1,usecols=[1]);
 meta[name]={'exit_code':int((p/'exit_code.txt').read_text()),'keyframe_count':len(rows),'keyframe_timestamps':times.tolist(),'gap_min_s':float(gaps.min()),'gap_median_s':float(np.median(gaps)),'gap_max_s':float(gaps.max()),'gaps_under_1s':int((gaps<1).sum()),'point_count':len(vertices),'finite_xyz':all(np.isfinite(vertices[k]).all() for k in 'xyz'),'ply_sha256':sha(p/'output/mapping.ply'),'trajectory_sha256':sha(p/'output/mapping.txt'),'peak_gpu_mib_sampled':int(np.max(gpu)),'skipped_logs':len(re.findall(r'Skipped frame',log)),'cholesky_logs':len(re.findall(r'Cholesky failed',log)),'relocalization_logs':len(re.findall(r'RELOCALIZING',log)),'deferred_logs':len(re.findall(r'KF_DEFERRED',log))}
 if name=='instrumented':
  pattern=re.compile(r'E1_TRACK frame=(\d+) timestamp=([0-9.]+) reference_kf=(\d+) success=(\d+) new_kf=(\d+)'); records=[m.groups() for m in pattern.finditer(log)]; relo=re.findall(r'E1_RELOC frame=(\d+) timestamp=([0-9.]+)',log)
  with (p/'tracking_timeline.csv').open('w',newline='') as f:
   w=csv.writer(f); w.writerow(['frame_index','timestamp','reference_kf','tracking_success','new_keyframe']); w.writerows(records)
  data=np.load(p/'provenance.npz'); assert len(data['kf_id'])==len(data['pixel_index'])==len(vertices); assert (data['kf_id']>=0).all() and (data['kf_id']<len(rows)).all(); assert (data['pixel_index']>=0).all() and (data['pixel_index']<np.prod(data['image_shape'])).all()
  meta[name].update(tracking_records=len(records),tracking_successes=sum(int(x[3]) for x in records),reloc_frame_records=len(relo),pixel_ids=len(data['kf_id']),frame_ids=data['frame_ids'].tolist(),image_shape=data['image_shape'].tolist())
meta['map_parity_sha256_equal']=meta['baseline']['ply_sha256']==meta['instrumented']['ply_sha256']; meta['trajectory_parity_sha256_equal']=meta['baseline']['trajectory_sha256']==meta['instrumented']['trajectory_sha256']
print(json.dumps(meta,indent=2)); (base/'metrics.json').write_text(json.dumps(meta,indent=2)+'\n')
