"""Add frame and canonical pixel ID scalar fields to the E7 KF-colored map."""
import hashlib,json
from pathlib import Path
import numpy as np
from plyfile import PlyData,PlyElement
ROOT=Path(__file__).resolve().parents[2];SRC=ROOT/'results/E7_validation/2026-10-28/kf_colored/mapping_keyframe_colors.ply';PROV=ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline/provenance.npz';OUT=ROOT/'results/E7c_surface_calibration_qa/2026-10-28/provenance_review';dst=OUT/'mapping_kf_frame_pixel.ply';assert not dst.exists();v=PlyData.read(SRC)['vertex'].data;d=np.load(PROV);ids=d['kf_id'];pix=d['pixel_index'];frames=d['frame_ids'];assert len(v)==len(ids)==len(pix) and np.array_equal(v['kf_id'],ids);target=np.empty(len(v),dtype=np.dtype(v.dtype.descr+[('frame_id','<i4'),('pixel_index','<i4')]))
for name in v.dtype.names:target[name]=v[name]
target['frame_id']=frames[ids];target['pixel_index']=pix
PlyData([PlyElement.describe(target,'vertex')],text=False,byte_order='<',comments=['kf_id is zero-based, frame_id indexes mapping_frames.csv','pixel_index is y*512+x for the 512x416 keyframe image']).write(dst)
w=PlyData.read(dst)['vertex'].data;checks={'count':len(w)==len(v),'xyz_bits':all(np.array_equal(w[n].view('u4'),v[n].view('u4')) for n in 'xyz'),'kf_id':np.array_equal(w['kf_id'],ids),'pixel_index':np.array_equal(w['pixel_index'],pix),'frame_id':np.array_equal(w['frame_id'],frames[ids]),'colors':all(np.array_equal(w[n],v[n]) for n in ('red','green','blue'))};assert all(checks.values());h=hashlib.sha256()
with dst.open('rb') as f:
 for block in iter(lambda:f.read(1048576),b''):h.update(block)
(OUT/'traceable_ply_validation.json').write_text(json.dumps({'output':str(dst.relative_to(ROOT)),'sha256':h.hexdigest(),'point_count':len(w),'image_shape':[416,512],'index_definition':'pixel_index = y * 512 + x','checks':checks,'note':'IDs give source provenance, not segmentation, verified correspondence or user-confirmed surface label.'},indent=2)+'\n');print('points',len(w),'checks',checks)
