"""Audit the published AMtown camera model without assuming JPG preprocessing."""
import hashlib,json,runpy,sys
from pathlib import Path
import cv2,numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'results/E7b_geometry_diagnostic/2026-10-28/calibration_qa';OUT.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(ROOT/'thirdparty/MASt3R-SLAM'));from mast3r_slam.mast3r_utils import resize_img
source=Path('/home/hlee221212/works/gradresearch/data/E4e/calibration_results.py');c=runpy.run_path(str(source))['AMtown_calibration'];K=np.array(c['camera_intrinsic'],float).reshape(3,3);dist=np.array(c['camera_dist_coeffs'],float);R=np.array(c['camera_ext_R'],float).reshape(3,3)
p=ROOT/'data/AMtown01/mapping/0039.jpg';im=cv2.imread(str(p));h,w=im.shape[:2];assert (w,h)==(2448,2048)
und=cv2.undistort(im,K,dist,None,K); xx,yy=np.meshgrid(np.linspace(0,w-1,101),np.linspace(0,h-1,85));px=np.column_stack((xx.ravel(),yy.ravel())).reshape(-1,1,2);norm=cv2.undistortPoints(px,K,dist); xyz=np.concatenate((norm.reshape(-1,2),np.ones((len(px),1))),axis=1);back,_=cv2.projectPoints(xyz,np.zeros(3),np.zeros(3),K,dist);error=np.linalg.norm(back.reshape(-1,2)-px.reshape(-1,2),axis=1);mapped=cv2.undistortPoints(px,K,dist,P=K).reshape(-1,2);shifts=np.linalg.norm(mapped-px.reshape(-1,2),axis=1);finite=np.isfinite(mapped).all(1);inside=finite&(mapped[:,0]>=0)&(mapped[:,0]<w)&(mapped[:,1]>=0)&(mapped[:,1]<h)
_,tr=resize_img(cv2.cvtColor(im,cv2.COLOR_BGR2RGB).astype('float32')/255,512,return_transformation=True);scale=np.array(tr[:2]);crop=np.array(tr[2:]);newpixels=(mapped/scale-crop);origpixels=(px.reshape(-1,2)/scale-crop);shift512=np.linalg.norm(newpixels-origpixels,axis=1)
fig,axs=plt.subplots(1,3,figsize=(15,5),constrained_layout=True)
for ax,img,title in ((axs[0],im,'Original JPG'),(axs[1],und,'Conditional undistortion'),(axs[2],cv2.absdiff(im,und),'Absolute pixel difference × 3')):
 if title.startswith('Absolute'):img=np.minimum(img.astype(float)*3,255).astype('uint8')
 ax.imshow(cv2.cvtColor(cv2.resize(img,(612,512)),cv2.COLOR_BGR2RGB));ax.set_title(title);ax.axis('off')
fig.savefig(OUT/'conditional_remap.png',dpi=140)
info={'calibration_file':str(source),'calibration_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'camera_intrinsic':K.tolist(),'distortion_k1_k2_p1_p2_k3':dist.tolist(),'extrinsic_rotation_max_orthogonality_abs':float(np.max(abs(R.T@R-np.eye(3)))),'extrinsic_rotation_determinant':float(np.linalg.det(R)),'image_size':[w,h],'image_exif_items':len(Image.open(p).getexif()),'grid_points':len(px),'finite':int(finite.sum()),'inside':int(inside.sum()),'roundtrip_max_pixel':float(error.max()),'roundtrip_p90_pixel':float(np.percentile(error,90)),'native_distortion_displacement_median_px':float(np.median(shifts)),'native_distortion_displacement_p90_px':float(np.percentile(shifts,90)),'native_distortion_displacement_max_px':float(shifts.max()),'model512_displacement_median_px':float(np.median(shift512)),'model512_displacement_p90_px':float(np.percentile(shift512,90)),'model512_displacement_max_px':float(shift512.max()),'resize_scale_w_h_crop_w_h':list(tr),'meaning':'Roundtrip is self-consistency of assumed model, not independent proof that source JPG is distorted or calibration is valid.'}
(OUT/'calibration_qa.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info,indent=2))
