import csv,hashlib,json
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[2];O=ROOT/'results/E7c_surface_calibration_qa/2026-10-28';r=O/'provenance_review';p=json.loads((r/'manifest.json').read_text());t=json.loads((r/'traceable_ply_validation.json').read_text());w=json.loads((r/'world_provenance_validation.json').read_text());m=json.loads((O/'match_audit/match_audit.json').read_text());c=json.loads((O/'calibration_qa/metadata_comparison.json').read_text());n=json.loads((O/'calibration_qa/numerics.json').read_text());rows=list(csv.DictReader((r/'kf_provenance.csv').open()));assert len(rows)==51 and sum(int(x['export_points']) for x in rows)==p['vertices']==t['point_count'] and all(t['checks'].values());assert all(int(np.count_nonzero(np.asarray(Image.open(r/x['export_mask']))))==int(x['export_points']) for x in rows)
assert all(x['max_world_distance']<2e-5 for x in w['checks']);assert c['selected_images']==240 and c['metadata_map_distortion_distinct']==1 and c['metadata_map_distortion_k1_k2_p1_p2_k3']==[0]*5;assert n['five_iterations']['roundtrip_ge_0_1_px']==292 and n['hundred_iterations']['roundtrip_ge_0_1_px']==54
for x in m['results']:
 assert len(x['checks'])==x['sift_matches']
 for y in x['checks']:
  p1=np.array(y['sift_target']);p2=np.array(y['lk_target_same_source']);assert abs(np.linalg.norm(p1-p2)-y['sift_lk_target_displacement_px'])<1e-6
sources=[ROOT/'configs/E7c_surface_calibration_qa/protocol.json',ROOT/'data/AMtown01/mapping_frames.csv',ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline/provenance.npz',ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline/output/mapping.ply',ROOT/'results/E7_validation/2026-10-28/kf_colored/mapping_keyframe_colors.ply']+sorted((ROOT/'scripts/E7c_surface_calibration_qa').glob('*.py'))
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
out={'validation_pass':True,'kf_masks_verified':len(rows),'export_points':p['vertices'],'E7a_intersection_3d_points':sum(x['capture_intersect_export'] for x in w['checks']),'max_world_distance':max(x['max_world_distance'] for x in w['checks']),'traceable_ply_checks':t['checks'],'source_hashes':{str(x.relative_to(ROOT)):sha(x) for x in sources},'G2':'INSUFFICIENT_SUPPORT: no independent individual physical correspondences verified','G4':'INSUFFICIENT_SUPPORT: no verified seam-free control','calibration':'NOT_VERIFIED: map-vs-LiDAR metadata distinct, JPG processing not identified','original_vs_calibrated_pose':'NOT_PERFORMED: calibration and surface gate not met'}
(O/'validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='source_hashes'},indent=2))
