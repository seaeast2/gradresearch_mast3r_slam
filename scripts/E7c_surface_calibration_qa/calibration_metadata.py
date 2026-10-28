"""Audit per-image map metadata and LiDAR calibration; do not select a winner."""
import csv,hashlib,json,runpy,zipfile
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/E7c_surface_calibration_qa/2026-10-28/calibration_qa';OUT.mkdir(parents=True,exist_ok=False);archive=Path('/home/hlee221212/works/gradresearch/data/E4e/archives/interval1_AMtown01.zip');cal=Path('/home/hlee221212/works/gradresearch/data/E4e/calibration_results.py');rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open())); frames=np.load(ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline/provenance.npz')['frame_ids'];
with zipfile.ZipFile(archive) as z:
 content=z.read('interval1_AMtown01/sampleinfos_interpolated.json')
meta=json.loads(content);byname={e['OriginalImageName']:e for e in meta};assert len(byname)==len(meta);matched=[];exif=[]; shapes=set(); transforms=[]
for r in rows:
 name=Path(r['rgb_member']).name;assert name in byname;item=byname[name];matched.append(item);shapes.add((item['Width'],item['Height']));im=Image.open(ROOT/'data/AMtown01/mapping'/r['filename']);exif.append(len(im.getexif()));assert im.size==(item['Width'],item['Height']);transforms.append(item['T4x4'])
Ks=np.array([a['P3x3'] for a in matched]);dc=np.array([[a[k] for k in ['K1','K2','P1','P2','K3']] for a in matched]);rt=np.array(transforms);R=rt[:,:3,:3];orth=np.max(abs(np.einsum('nji,njk->nik',R,R)-np.eye(3)),axis=(1,2));det=np.linalg.det(R);lid=runpy.run_path(str(cal))['AMtown_calibration'];lidK=np.array(lid['camera_intrinsic']).reshape(3,3)
out={'archive_sampleinfo_sha256':hashlib.sha256(content).hexdigest(),'sampleinfo_archive_records':len(meta),'selected_images':len(matched),'selected_keyframes':len(frames),'metadata_dimensions':list(shapes),'metadata_map_P3x3_example':Ks[0].tolist(),'metadata_map_P3x3_distinct':len(np.unique(Ks.reshape(len(Ks),-1),axis=0)),'metadata_map_distortion_k1_k2_p1_p2_k3':dc[0].tolist(),'metadata_map_distortion_distinct':len(np.unique(dc,axis=0)),'metadata_poses_rotation_max_orthogonality_error':float(orth.max()),'metadata_poses_rotation_determinant_range':[float(det.min()),float(det.max())],'camera_lidar_intrinsic':lidK.tolist(),'camera_lidar_distortion_k1_k2_p1_p2_k3':lid['camera_dist_coeffs'],'map_minus_lidar_intrinsic':(Ks[0]-lidK).tolist(),'exif_nonempty_count':sum(x>0 for x in exif),'interpretation':'Different camera-to-3D-map and camera-to-LiDAR calibration contexts; zero map distortion coefficients do not prove JPG preprocessing or prove which camera model applies.'}
(OUT/'metadata_comparison.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(out,indent=2))
