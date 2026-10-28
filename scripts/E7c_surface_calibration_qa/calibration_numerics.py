"""Audit numerical invertibility of the conditional camera-LiDAR model."""
import json,runpy
from pathlib import Path
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/E7c_surface_calibration_qa/2026-10-28/calibration_qa';d=runpy.run_path('/home/hlee221212/works/gradresearch/data/E4e/calibration_results.py')['AMtown_calibration'];K=np.array(d['camera_intrinsic'],float).reshape(3,3);dist=np.array(d['camera_dist_coeffs'],float);w,h=2448,2048;xx,yy=np.meshgrid(np.linspace(0,w-1,101),np.linspace(0,h-1,85));p=np.column_stack((xx.ravel(),yy.ravel()));P=p.reshape(-1,1,2)
def project(norm):
 xyz=np.column_stack((norm,np.ones(len(norm))));out,_=cv2.projectPoints(xyz,np.zeros(3),np.zeros(3),K,dist);return out.reshape(-1,2)
def inverse(itr):
 q=cv2.undistortPointsIter(P,K,dist,None,None,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,itr,1e-12)).reshape(-1,2);back=project(q);e=np.linalg.norm(back-p,axis=1);und=q@np.diag([K[0,0],K[1,1]])+K[:2,2];inside=np.isfinite(und).all(1)&(und[:,0]>=0)&(und[:,0]<w)&(und[:,1]>=0)&(und[:,1]<h);return q,e,inside
# Equivalent to OpenCV default 5 iterations, then 100 fixed-point iterations.
q5,e5,in5=inverse(5);q100,e100,in100=inverse(100)
# Numerical forward Jacobian on normalized pinhole rays corresponding to image grid.
x=(p[:,0]-K[0,2])/K[0,0];y=(p[:,1]-K[1,2])/K[1,1];q=np.column_stack((x,y));eps=1e-6;jx=(project(q+np.array([eps,0]))-project(q-np.array([eps,0])))/(2*eps);jy=(project(q+np.array([0,eps]))-project(q-np.array([0,eps])))/(2*eps);det=(jx[:,0]*jy[:,1]-jx[:,1]*jy[:,0])/(K[0,0]*K[1,1]);
def metrics(e,inside):
 return {'count':len(e),'finite':int(np.isfinite(e).sum()),'roundtrip_lt_0_1_px':int((e<.1).sum()),'roundtrip_ge_0_1_px':int((e>=.1).sum()),'roundtrip_ge_1_px':int((e>=1).sum()),'p90_px':float(np.percentile(e,90)),'p99_px':float(np.percentile(e,99)),'max_px':float(e.max()),'inside_and_roundtrip_lt_0_1':int((inside&(e<.1)).sum())}
out={'five_iterations':metrics(e5,in5),'hundred_iterations':metrics(e100,in100),'both_agree_normalized_lt_1e_minus_5':int((np.linalg.norm(q5-q100,axis=1)<1e-5).sum()),'forward_jacobian_grid_count':len(det),'forward_jacobian_nonpositive':int((det<=0).sum()),'forward_jacobian_min':float(det.min()),'interpretation':'Numerical inversion and local Jacobian under the published assumed model; no inference that input JPG is raw or corrected. A nonpositive Jacobian indicates loss of local invertibility at the sampled idealized rays, not necessarily the physical lens field of view.'}
np.savez_compressed(OUT/'numeric_grid.npz',pixel=p,error5=e5,error100=e100,inside5=in5,inside100=in100,forward_jacobian=det);(OUT/'numerics.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
