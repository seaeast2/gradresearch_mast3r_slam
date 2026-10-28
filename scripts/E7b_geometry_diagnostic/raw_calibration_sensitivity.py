"""Conditional raw pair sensitivity; assumes JPG is distorted, not calibration validation."""
import csv,hashlib,json,os,runpy,sys
from pathlib import Path
import cv2,numpy as np,torch,lietorch
ROOT=Path(__file__).resolve().parents[2];UP=ROOT/'thirdparty/MASt3R-SLAM';sys.path.insert(0,str(UP))
from mast3r_slam.config import load_config
from mast3r_slam.frame import create_frame
from mast3r_slam.mast3r_utils import load_mast3r,mast3r_asymmetric_inference,resize_img
OUT=ROOT/'results/E7b_geometry_diagnostic/2026-10-28/conditional_raw';E7A=ROOT/'results/E7a_overlap_support/2026-10-28/e7a_amtown_probe'; rows=list(csv.DictReader((ROOT/'data/AMtown01/mapping_frames.csv').open()));prov=np.load(ROOT/'results/E7_validation/2026-10-28/e7_amtown_baseline/provenance.npz');frames=prov['frame_ids'];cal=runpy.run_path('/home/hlee221212/works/gradresearch/data/E4e/calibration_results.py')['AMtown_calibration'];K=np.asarray(cal['camera_intrinsic'],float).reshape(3,3);dist=np.asarray(cal['camera_dist_coeffs'],float);PAIRS=[(8,11),(9,12),(10,12)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def plane(x):
 c=x.mean(0);_,_,v=np.linalg.svd(x-c,full_matrices=False);res=np.abs((x-c)@v[-1]);span=np.linalg.norm(np.ptp((x-c)@v[:2].T,axis=0));return span,float(np.percentile(res,90)/span),float(np.median(res)/span)
def read(i):
 p=ROOT/'data/AMtown01/mapping'/rows[i]['png_filename'];assert sha(p)==rows[i]['png_sha256'];return cv2.imread(str(p))
def draw(i,mode):
 bgr=read(i)
 if mode=='assumed_undistorted':bgr=cv2.undistort(bgr,K,dist,None,K)
 rgb=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB).astype('float32')/255
 return create_frame(i,rgb,lietorch.Sim3.Identity(1,device='cuda:0'),img_size=512,device='cuda:0')
def bilinear(arr,pts):
 x,y=pts[:,0],pts[:,1];x0=np.floor(x).astype(int);y0=np.floor(y).astype(int);a=(x-x0)[:,None];b=(y-y0)[:,None]
 return (1-a)*(1-b)*arr[y0,x0]+a*(1-b)*arr[y0,x0+1]+(1-a)*b*arr[y0+1,x0]+a*b*arr[y0+1,x0+1]
def main():
 OUT.mkdir(parents=True,exist_ok=False);os.chdir(UP);load_config(str(ROOT/'configs/E0_environment_preparation/low_vram_base.yaml'));torch.backends.cuda.matmul.allow_tf32=True;torch.set_grad_enabled(False);model=load_mast3r(device='cuda:0');output=[];manifest={}
 for k,other in PAIRS:
  frame=int(frames[k]);prev=int(frames[k-1]);sup=np.load(E7A/f'road_{k}_{other}_common_support.npz');xy=sup['source_xy'][sup['common']];assert len(xy)>3
  rgb=cv2.cvtColor(read(frame),cv2.COLOR_BGR2RGB).astype('float32')/255;_,tr=resize_img(rgb,512,return_transformation=True);scale=np.array(tr[:2]);crop=np.array(tr[2:]);native=(xy.astype(float)+crop+.5)*scale-.5
  normalized=cv2.undistortPoints(native.reshape(-1,1,2),K,dist);newnative=cv2.undistortPoints(native.reshape(-1,1,2),K,dist,P=K).reshape(-1,2);p3=np.column_stack((normalized.reshape(-1,2),np.ones(len(xy))));back,_=cv2.projectPoints(p3,np.zeros(3),np.zeros(3),K,dist);err=np.linalg.norm(back.reshape(-1,2)-native,axis=1);newxy=(newnative+.5)/scale-.5-crop
  valid=np.isfinite(newxy).all(1)&(err<.1)&(newxy[:,0]>=0)&(newxy[:,0]<511)&(newxy[:,1]>=0)&(newxy[:,1]<415)
  generated={}
  for mode in ['native','assumed_undistorted']:
   a=draw(frame,mode);b=draw(prev,mode);X,C,_,_=mast3r_asymmetric_inference(model,a,b);generated[mode]=(X[0].detach().cpu().numpy().reshape(416,512,3).astype(float),C[0].detach().cpu().numpy().reshape(416,512,1).astype(float));del a,b,X,C;torch.cuda.empty_cache()
  init=np.load(next((E7A/'events').glob(f'kf{k}_initial_frame*.npz')));index=np.full(416*512,-1);index[init['pixel_index']]=np.arange(len(init['pixel_index']));ix=index[xy[:,1]*512+xy[:,0]];assert (ix>=0).all();expected=init['xyz'][ix];actual=generated['native'][0][xy[:,1],xy[:,0]];parity=float(np.max(abs(expected-actual)));assert parity<2e-5
  finite_native=np.isfinite(actual).all(1);uv=newxy[valid];und=bilinear(generated['assumed_undistorted'][0],uv);und_conf=bilinear(generated['assumed_undistorted'][1],uv).reshape(-1);valid_indices=np.flatnonzero(valid);valid[valid_indices] &= np.isfinite(und).all(1)&np.isfinite(und_conf)&(und_conf>0);valid &=finite_native
  p0=generated['native'][0][xy[valid,1],xy[valid,0]];p1=bilinear(generated['assumed_undistorted'][0],newxy[valid]);
  entry={'kf':k,'paired_with':other,'frame':frame,'previous_kf_frame':prev,'candidates':len(xy),'common_samples':int(valid.sum()),'roundtrip_invalid_or_outside':int((~valid).sum()),'inverse_roundtrip_max_native_px':float(err.max()),'native_raw_saved_parity_max_abs':parity,'conditional':'JPG assumed distorted; camera model not physically verified; raw pair only; no SLAM pose comparison'}
  if len(p0)>=3:
   span0,p900,med0=plane(p0);span1,p901,med1=plane(p1);entry.update({'native_span_local':span0,'undistorted_span_local':span1,'native_plane_p90_over_span':p900,'undistorted_plane_p90_over_span':p901,'native_plane_median_over_span':med0,'undistorted_plane_median_over_span':med1})
  output.append(entry);np.savez_compressed(OUT/f'kf{k}_mapped_common.npz',native_xy=xy,conditional_xy=newxy,valid=valid,inverse_roundtrip_error=err,native_xyz=p0,conditional_xyz=p1)
  print(json.dumps(entry),flush=True)
 (OUT/'summary.json').write_text(json.dumps({'results':output,'warning':'Conditional sensitivity only; no verified JPG distortion/calibration and no relative pose or SLAM rerun; samples from unverified optical-flow candidates','script_sha256':sha(Path(__file__)),'inputs_csv_sha256':sha(ROOT/'data/AMtown01/mapping_frames.csv'),'calibration_sha256':sha(Path('/home/hlee221212/works/gradresearch/data/E4e/calibration_results.py')),'checkpoint_sha256':sha(UP/'checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth')},indent=2)+'\n')
if __name__=='__main__':main()
