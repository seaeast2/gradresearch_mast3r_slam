import csv, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/E3_fusion/2026-10-28/instrumented'
E1=ROOT/'results/E1_baseline_reproduction/2026-10-27/periodic_1s_retry'

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def plane(x):
    center=x.mean(0); _,_,v=np.linalg.svd(x-center,full_matrices=False)
    residual=(x-center)@v[-1]; span=np.linalg.norm(np.ptp((x-center)@v[:2].T,axis=0))
    return {'median':float(np.median(np.abs(residual))), 'p90':float(np.percentile(np.abs(residual),90)),
            'rmse':float(np.sqrt(np.mean(residual**2))), 'span':float(span), 'normal':v[-1], 'center':center}

def main():
    events=OUT/'events'; rows=[]; summary=[]; errors=[]; fig,axes=plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
    for k in range(31,36):
        files=sorted(events.glob(f'kf{k}_update_frame*.npz'),key=lambda p:int(p.stem.split('frame')[-1]))
        init_files=list(events.glob(f'kf{k}_initial_frame*.npz')); assert len(init_files)==1 and files
        initial=np.load(init_files[0]); previous=initial['xyz']; initial_plane=plane(previous.astype(float)); first_span=initial_plane['span']
        for f in files:
            d=np.load(f); before=d['before_xyz'].astype(float); after=d['after_xyz'].astype(float); inp=d['input_xyz'].astype(float)
            w0=d['before_weight'].astype(float); wi=d['input_weight'].astype(float); after_w=d['after_weight'].astype(float)
            assert np.array_equal(initial['pixel_index'],d['pixel_index'])
            assert np.all(np.isfinite(before)) and np.all(np.isfinite(after)) and np.all(np.isfinite(inp))
            continuity=float(np.max(np.abs(previous-before))); errors.append(continuity); assert continuity<1e-6
            expected=(w0*before+wi*inp)/(w0+wi)
            formula=float(np.max(np.abs(expected-after))); assert formula<2e-6
            weight_error=float(np.max(np.abs(after_w-w0-wi))); assert weight_error<2e-5
            assert int(d['after_N'])==int(d['before_N'])+1
            assert int(d['after_updates'])==int(d['before_updates'])+1
            bp,ap=plane(before),plane(after); q=np.sqrt(d['descriptor_conf_frame']*d['descriptor_conf_kf'])
            valid=d['valid_match'].astype(bool)&(q>1.5)&(d['frame_self_conf']>0)&(w0.reshape(-1)/int(d['before_N'])>0)
            normal=bp['normal'] if bp['normal']@initial_plane['normal']>=0 else -bp['normal']
            incoming_delta=(inp-before)@normal; update_delta=(after-before)@normal; weight=(wi/(w0+wi)).reshape(-1)
            row={'kf':k,'frame':int(d['frame_id']),'updates_before':int(d['before_updates']), 'n_points':len(before),
                 'valid_tracking_correspondences':int(valid.sum()), 'valid_tracking_fraction':float(valid.mean()),
                 'valid_match_fraction':float(d['valid_match'].astype(bool).mean()),
                 'descriptor_q_pass_fraction':float((q>1.5).mean()),
                 'before_p90_over_initial_span':bp['p90']/first_span,'after_p90_over_initial_span':ap['p90']/first_span,
                 'plane_normal_change_deg':float(np.degrees(np.arccos(np.clip(abs(bp['normal']@ap['normal']),0,1)))),
                 'input_normal_shift_median_over_span':float(np.median(incoming_delta)/first_span),
                 'input_normal_abs_p90_over_span':float(np.percentile(np.abs(incoming_delta),90)/first_span),
                 'input_normal_abs_p90_valid_over_span':float(np.percentile(np.abs(incoming_delta[valid]),90)/first_span) if valid.any() else float('nan'),
                 'update_normal_shift_median_over_span':float(np.median(update_delta)/first_span),
                 'weight_fraction_median':float(np.median(weight)), 'weight_fraction_p90':float(np.percentile(weight,90)),
                 'weighted_formula_max_abs':formula,'continuity_max_abs':continuity}
            rows.append(row); previous=after
        last=plane(previous); angle=float(np.degrees(np.arccos(np.clip(abs(initial_plane['normal']@last['normal']),0,1))))
        # Use the initial normal consistently for the cumulative signed displacement.
        shift=(previous-initial['xyz'])@initial_plane['normal']
        item={'kf':k,'keyframe_frame':int(initial['frame_id']),'updates':len(files),'points':len(previous),
              'initial_p90_over_initial_span':initial_plane['p90']/first_span,'final_p90_over_initial_span':last['p90']/first_span,
              'initial_to_final_normal_angle_deg':angle,'cumulative_normal_shift_median_over_initial_span':float(np.median(shift)/first_span),
              'cumulative_normal_abs_p90_over_initial_span':float(np.percentile(np.abs(shift),90)/first_span),
              'initial_span_local_units':first_span}
        summary.append(item)
        local=[r for r in rows if r['kf']==k]
        axes[0].plot([int(initial['frame_id'])]+[r['frame'] for r in local],[item['initial_p90_over_initial_span']]+[r['after_p90_over_initial_span'] for r in local],marker='o',label=f'KF{k}')
        axes[1].plot([r['frame'] for r in local],[r['weight_fraction_median'] for r in local],marker='o',label=f'KF{k}')
    for name,data in [('fusion_events.csv',rows),('fusion_summary.csv',summary)]:
        with (OUT/name).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=data[0].keys());writer.writeheader();writer.writerows(data)
    axes[0].set(xlabel='input frame',ylabel='PCA plane residual p90 / initial ROI span',title='ROI shape across fusion updates')
    axes[1].set(xlabel='input frame',ylabel='median incoming weight fraction',title='Incoming influence per update')
    for ax in axes: ax.legend(); ax.grid(alpha=.3)
    fig.savefig(OUT/'fusion_summary.png',dpi=170)
    fig2,axes2=plt.subplots(1,2,figsize=(12,4.5),constrained_layout=True)
    for k in range(31,36):
        local=[r for r in rows if r['kf']==k]
        axes2[0].plot([r['frame'] for r in local],[r['valid_tracking_fraction']*100 for r in local],marker='o',label=f'KF{k}')
        axes2[1].plot([r['frame'] for r in local],[abs(r['update_normal_shift_median_over_span'])*100 for r in local],marker='o',label=f'KF{k}')
    axes2[0].set(xlabel='input frame',ylabel='valid tracking matches in ROI (%)',title='Tracking support within the ROI')
    axes2[1].set(xlabel='input frame',ylabel='absolute median normal shift / initial span (%)',title='Per-update canonical displacement')
    for ax in axes2: ax.legend(); ax.grid(alpha=.3)
    fig2.savefig(OUT/'fusion_support_shift.png',dpi=170)
    reference={'trajectory_e1':sha(E1/'output/mapping.txt'),'trajectory_e3':sha(OUT/'output/mapping.txt'),
               'ply_e1':sha(E1/'output/mapping.ply'),'ply_e3':sha(OUT/'output/mapping.ply'),
               'provenance_e1':sha(E1/'provenance.npz'),'provenance_e3':sha(OUT/'provenance.npz')}
    manifest={'events':len(rows),'keyframes':summary,'hashes':reference,'roi_sha256':sha(ROOT/'configs/E1_baseline_reproduction/periodic_1s_rois.json'),
              'protocol_sha256':sha(ROOT/'configs/E3_fusion/protocol.json'), 'config_sha256':sha(ROOT/'configs/E0_environment_preparation/low_vram_base.yaml'),
              'base_config_sha256':sha(ROOT/'thirdparty/MASt3R-SLAM/config/base.yaml'), 'input_csv_sha256':sha(ROOT/'data/HKairport01/mapping_frames.csv'),
              'checkpoint_sha256':sha(ROOT/'thirdparty/MASt3R-SLAM/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth'),
              'instrument_script_sha256':sha(ROOT/'scripts/E3_fusion/run_instrumented.py'),'analysis_script_sha256':sha(Path(__file__)),
              'max_update_continuity_abs':max(errors),'weights':'actual canonical C plus incoming C, no masking by valid matches during update',
              'coordinate':'per-keyframe local frame; no comparison of signed shifts between KF normals',
              'caveat':'plane residual is exploratory: ROI planar assumption not verified; tracking and fusion coupled; no causal counterfactual'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
