"""Check exported XYZ against saved local canonical points and final actual Sim3."""
import json
from pathlib import Path
import numpy as np
from plyfile import PlyData
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[2];E7=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline';A=ROOT/'results/E7a_overlap_support/2026-10-28/e7a_amtown_probe';OUT=ROOT/'results/E7c_surface_calibration_qa/2026-10-28/provenance_review';d=np.load(E7/'provenance.npz');v=PlyData.read(E7/'output/mapping.ply')['vertex'].data;poses=np.load(A/'final_sim3.npy');reports=[]
for k in range(8,13):
 z=np.load(A/f'kf{k}_replay.npz');lookup=np.full(512*416,-1,np.int64);lookup[z['index']]=np.arange(len(z['index']));ei=np.flatnonzero(d['kf_id']==k);ii=lookup[d['pixel_index'][ei]];m=ii>=0;ei=ei[m];ii=ii[m];assert len(ii)>0
 local=z['original'][ii].astype(float);p=poses[k].astype(float);calc=p[7]*Rotation.from_quat(p[3:7]).apply(local)+p[:3];stored=np.column_stack([v[n][ei] for n in 'xyz']);err=np.linalg.norm(calc-stored,axis=1);assert np.isfinite(err).all() and err.max()<2e-5
 reports.append({'kf':k,'capture_intersect_export':len(err),'max_world_distance':float(err.max()),'p90_world_distance':float(np.percentile(err,90))})
(OUT/'world_provenance_validation.json').write_text(json.dumps({'checks':reports,'scope':'Five available E7a captures; not all 51 KFs. Proves coordinate/source ID linkage for these pixels, not surface identity.'},indent=2)+'\n');print(json.dumps(reports,indent=2))
