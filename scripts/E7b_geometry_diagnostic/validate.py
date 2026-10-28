import csv,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/E7b_geometry_diagnostic/2026-10-28/e7b_amtown_backend';E7A=ROOT/'results/E7a_overlap_support/2026-10-28/e7a_amtown_probe';r=list(csv.DictReader((OUT/'backend_world_pairs.csv').open()));e=list(csv.DictReader((E7A/'candidate_geometry.csv').open()));checks=[]
for pair in ('8-11','9-12','10-12'):
 a=next(x for x in r if x['pair']==pair and x['step']=='50' and x['side']=='post' and x['map']=='fused');b=next(x for x in e if x['pair']==pair and x['arm']=='original'); dif={}
 for x,y in [('normal_abs_median','normal_abs_median'),('normal_abs_p90','normal_abs_p90'),('tangent_median','tangent_median'),('tangent_p90','tangent_p90'),('z_abs_median','world_z_abs_median'),('xy_median','world_xy_median')]:dif[x]=abs(float(a[x])-float(b[y]));assert dif[x]<1e-9
 checks.append({'pair':pair,'E7a_final_values_max_abs':max(dif.values())})
raw=json.loads((ROOT/'results/E7b_geometry_diagnostic/2026-10-28/conditional_raw/summary.json').read_text())
for a in raw['results']:
 assert a['common_samples']>3 and a['native_raw_saved_parity_max_abs']<2e-5
 z=np.load(ROOT/f'results/E7b_geometry_diagnostic/2026-10-28/conditional_raw/kf{a["kf"]}_mapped_common.npz');assert int(z['valid'].sum())==a['common_samples'];assert np.isfinite(z['native_xyz']).all() and np.isfinite(z['conditional_xyz']).all()
report={'e7a_fixed_support_result_parity':checks,'native_raw_parity_max':max(a['native_raw_saved_parity_max_abs'] for a in raw['results']),'conditional_raw_support':[{'kf':a['kf'],'n':a['common_samples'],'total':a['candidates']} for a in raw['results']],'scope':'No validation of physical distortion or correctness of image correspondences.'};(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
