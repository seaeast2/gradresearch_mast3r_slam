import json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/E7a_overlap_support/2026-10-28/e7a_amtown_probe';E7=ROOT/'results/E7_validation/2026-10-28/e7_amtown_probe';A=json.loads((OUT/'analysis.json').read_text()); assert A['tracking_events_equal'] and all(v['equal'] for v in A['parity'].values()); checks=[]
for old in sorted((E7/'events').glob('*.npz')):
 new=OUT/'events'/old.name
 assert new.exists();a=np.load(old);b=np.load(new);lookup=np.full(416*512,-1,np.int64);lookup[b['pixel_index']]=np.arange(len(b['pixel_index']));ix=lookup[a['pixel_index']];assert (ix>=0).all();fields=['xyz','confidence'] if 'initial' in old.name else ['before_xyz','before_weight','input_xyz','input_weight','after_xyz','after_weight','valid_match','matched_frame_pixel']
 diff={key:bool(np.array_equal(a[key],b[key][ix])) for key in fields};assert all(diff.values());checks.append({'file':old.name,'points':len(ix),'all_fields_bitwise_equal':True})
poses=np.load(OUT/'final_sim3.npy');gauge=[]
for k in range(8,13):
 x=np.load(OUT/f'kf{k}_replay.npz')['original'][::997].astype(float);p=poses[k].astype(float);assert p[7]>0;rot=Rotation.from_quat(p[3:7]);w=p[7]*rot.apply(x)+p[:3];back=rot.inv().apply((w-p[:3])/p[7]);q=2.3;wp=(p[7]/q)*rot.apply(q*x)+p[:3];e1=float(abs(back-x).max());e2=float(abs(wp-w).max());assert e1<1e-10 and e2<1e-10;gauge.append({'kf':k,'roundtrip_max_abs':e1,'reparameterization_max_abs':e2})
for f in (OUT/'events').glob('*.npz'):
 pass
report={'e7_intermediate_roi_parity':checks,'sim3_checks':gauge,'caveat':'Intersections only, not independent correspondence or seam-free validation.'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print('E7 subset parity:',len(checks),'Sim3 roundtrip and gauge:',len(gauge))
