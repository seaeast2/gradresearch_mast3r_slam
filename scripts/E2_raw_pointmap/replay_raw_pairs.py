import csv, hashlib, json, os, sys
from pathlib import Path
import cv2
import numpy as np
import torch
import lietorch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / 'thirdparty/MASt3R-SLAM'
sys.path.insert(0, str(UPSTREAM))
from mast3r_slam.config import load_config, config
from mast3r_slam.frame import create_frame
from mast3r_slam.mast3r_utils import load_mast3r, mast3r_asymmetric_inference

def sha(p):
    digest = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    out = ROOT / 'results/E2_raw_pointmap/2026-10-28/raw_pairs'
    out.mkdir(parents=True, exist_ok=True)
    os.chdir(UPSTREAM)
    load_config(str(ROOT / 'configs/E0_environment_preparation/low_vram_base.yaml'))
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.set_grad_enabled(False)
    model = load_mast3r(device='cuda:0')
    e1 = ROOT / 'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'
    provenance = np.load(e1 / 'provenance.npz')
    frame_ids = provenance['frame_ids']
    spec_path = ROOT / 'configs/E1_baseline_reproduction/periodic_1s_rois.json'
    spec = json.loads(spec_path.read_text())
    rows = list(csv.DictReader((ROOT / 'data/HKairport01/mapping_frames.csv').open()))
    timeline = list(csv.DictReader((e1 / 'tracking_timeline.csv').open()))
    results = []
    for kf in range(31, 36):
        birth = int(frame_ids[kf]); prev = int(frame_ids[kf - 1]); nxt = birth + 1
        assert timeline[birth]['new_keyframe'] == '1' and int(timeline[birth]['reference_kf']) == kf-1
        assert int(timeline[nxt]['reference_kf']) == kf and timeline[nxt]['tracking_success'] == '1'
        mask = np.zeros((416, 512), np.uint8)
        cv2.fillPoly(mask, [np.asarray(spec['polygons_xy'][str(kf)], np.int32)], 1)
        pixel = np.flatnonzero(mask)
        for label, fi, fj, branch in [('birth_self', birth, prev, 0), ('next_cross', nxt, birth, 1)]:
            frames = []
            for idx in (fi, fj):
                p = ROOT / 'data/HKairport01/mapping' / rows[idx]['png_filename']
                if sha(p) != rows[idx]['png_sha256']:
                    raise ValueError(f'input hash mismatch: {p}')
                rgb = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB).astype(np.float32)/255
                frames.append(create_frame(idx, rgb, lietorch.Sim3.Identity(1, device='cuda:0'), img_size=512, device='cuda:0'))
            X,C,D,Q = mast3r_asymmetric_inference(model, *frames)
            xyz = X[branch].cpu().numpy().reshape(-1,3)[pixel]
            confidence = C[branch].cpu().numpy().reshape(-1)[pixel]
            desc = D[branch].cpu().numpy().reshape(-1,D.shape[-1])[pixel]
            match_conf = Q[branch].cpu().numpy().reshape(-1)[pixel]
            valid = np.isfinite(xyz).all(axis=1) & np.isfinite(confidence) & (confidence > config['tracking']['C_conf'])
            pts = xyz[valid].astype(np.float64)
            center = pts.mean(axis=0); _, singular, vh = np.linalg.svd(pts-center, full_matrices=False)
            residual = (pts-center) @ vh[-1]
            span = np.linalg.norm(np.ptp((pts-center) @ vh[:2].T, axis=0))
            row = dict(kf=kf, case=label, frame_i=fi, frame_j=fj, roi_points=len(pixel), valid_points=len(pts),
                       local_frame=f'frame_{fi}', local_scale='arbitrary_pair', span=span,
                       abs_median=np.median(np.abs(residual)), abs_p90=np.percentile(np.abs(residual),90),
                       rmse=np.sqrt(np.mean(residual**2)), p90_over_span=np.percentile(np.abs(residual),90)/span,
                       confidence_median=np.median(confidence[valid]), confidence_p10=np.percentile(confidence[valid],10),
                       z_median=np.median(pts[:,2]), normal=vh[-1].tolist())
            results.append(row)
            np.savez_compressed(out/f'kf{kf}_{label}.npz', pixel_index=pixel, xyz=xyz, confidence=confidence,
                                descriptor=desc, descriptor_confidence=match_conf, valid=valid,
                                plane_center=center, plane_normal=vh[-1])
            del X,C,D,Q,frames
            torch.cuda.empty_cache()
            print(json.dumps(row, default=float), flush=True)
    with (out/'R1_raw_plane.csv').open('w', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=results[0].keys()); writer.writeheader(); writer.writerows(results)
    fig, ax = plt.subplots(figsize=(9,4.5), constrained_layout=True)
    for label, marker in [('birth_self','o'),('next_cross','s')]:
        subset=[r for r in results if r['case']==label]
        ax.plot([r['kf'] for r in subset], [r['p90_over_span'] for r in subset], marker=marker, label=label)
    ax.set(xlabel='Keyframe ROI', ylabel='PCA plane residual p90 / ROI diagonal', title='Raw pair pointmap: normalized local non-planarity')
    ax.legend(); ax.grid(alpha=.3); fig.savefig(out/'R1_raw_plane.png', dpi=170)
    manifest={'experiment':'E2 raw pair replay', 'kf_ids':list(range(31,36)), 'branch_definition':{'birth_self':'KF image first, prior KF second; self branch in KF camera coordinates', 'next_cross':'next tracking frame first, KF second; cross branch in first frame coordinates'}, 'roi':'E1 exploratory RGB polygons, not independently verified same-position support', 'roi_sha256':sha(spec_path), 'tracking_timeline_sha256':sha(e1/'tracking_timeline.csv'), 'input_csv_sha256':sha(ROOT/'data/HKairport01/mapping_frames.csv'), 'checkpoint_sha256':sha(UPSTREAM/'checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth'), 'config_sha256':sha(ROOT/'configs/E0_environment_preparation/low_vram_base.yaml'), 'script_sha256':sha(Path(__file__)), 'torch':torch.__version__, 'gpu':torch.cuda.get_device_name(), 'pca_definition':'unweighted least squares plane over finite ROI points passing tracking C_conf; p90 of absolute orthogonal residual; normalized by diagonal of projected PCA bounding box', 'limitations':['replayed pair inference, not captured in original E1 run; intermediate parity unverified', 'different pair coordinate systems and arbitrary scales; normals and z not comparable directly between pairs', 'no verified correspondence or absolute geometry', 'RGB ROI is exploratory and may contain nonplanar patches']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__ == '__main__': main()
