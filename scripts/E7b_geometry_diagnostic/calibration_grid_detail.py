import json,runpy
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[2];p=ROOT/'results/E7b_geometry_diagnostic/2026-10-28/calibration_qa';c=runpy.run_path('/home/hlee221212/works/gradresearch/data/E4e/calibration_results.py')['AMtown_calibration'];K=np.asarray(c['camera_intrinsic']).reshape(3,3);d=np.asarray(c['camera_dist_coeffs']);w,h=2448,2048
x,y=np.meshgrid(np.linspace(0,w-1,101),np.linspace(0,h-1,85));pix=np.column_stack((x.ravel(),y.ravel())).reshape(-1,1,2);norm=cv2.undistortPoints(pix,K,d);p3=np.column_stack((norm.reshape(-1,2),np.ones(len(pix))));back,_=cv2.projectPoints(p3,np.zeros(3),np.zeros(3),K,d);err=np.linalg.norm(back.reshape(-1,2)-pix.reshape(-1,2),axis=1);q=cv2.undistortPoints(pix,K,d,P=K).reshape(-1,2);finite=np.isfinite(q).all(1);inside=finite&(q[:,0]>=0)&(q[:,0]<w)&(q[:,1]>=0)&(q[:,1]<h);mask=inside&(err<.1)
r=np.sqrt(((pix.reshape(-1,2)[:,0]-K[0,2])/K[0,0])**2+((pix.reshape(-1,2)[:,1]-K[1,2])/K[1,1])**2)
out={'grid_total':len(err),'roundtrip_lt_0_1_px':int((err<.1).sum()),'roundtrip_ge_0_1_px':int((err>=.1).sum()),'roundtrip_ge_1_px':int((err>=1).sum()),'inside_and_roundtrip_lt_0_1':int(mask.sum()),'roundtrip_max_among_inside':float(err[inside].max()),'roundtrip_p99':float(np.percentile(err,99)),'error_ge_1_min_radius':float(r[err>=1].min()) if (err>=1).any() else None,'purpose':'sampled numerical behavior of an unverified inverse; no physical correctness guarantee'}
(p/'grid_details.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
