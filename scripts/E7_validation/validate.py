import csv,hashlib,json,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; BASE=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline';OUT=ROOT/'results/E7_validation/2026-10-28/e7_amtown_probe'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def track(p):return [x for x in p.read_text().splitlines() if x.startswith(('E1_TRACK ','E1_RELOC '))]
base=track(BASE/'run.log');probe=track(OUT/'run.log');assert len(base)==239 and base==probe and all('success=1' in s for s in base)
rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open()));assert len(rows)==240 and len({r['rgb_member'] for r in rows})==240
for r in rows:assert sha(ROOT/'data/AMtown01/mapping'/r['png_filename'])==r['png_sha256']
a=json.loads((OUT/'analysis.json').read_text());assert all(x['status']=='OK' and x['max_replay_xyz']==0 and x['max_replay_weight']==0 for x in a['validation']);assert all(x['equal'] for x in a['parity'].values())
pose=np.load(OUT/'final_sim3.npy'); assert pose.shape==(51,8) and np.isfinite(pose).all() and (pose[:,7]>0).all()
r={'tracking_calls':len(base),'tracking_probe_identical':True,'all_tracking_success':True,'png_hashes_valid':len(rows),'unique_source_members':len(rows),'replay_updates':sum(x['updates'] for x in a['validation']),'all_replay_states_bitwise_equal':True,'baseline_probe_output_parity':a['parity'],'final_sim3_count':len(pose),'overlap_status':'INSUFFICIENT_SUPPORT for all planned pairs; no validated seam-free negative control','script_sha256':{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'scripts/E7_validation').glob('*.py')},'roi_sha256':sha(ROOT/'configs/E7_validation/roi.json'),'overlap_protocol_sha256':sha(ROOT/'configs/E7_validation/overlap_protocol.json')}
(OUT/'validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
