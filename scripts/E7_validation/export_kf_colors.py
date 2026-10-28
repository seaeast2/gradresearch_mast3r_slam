"""Create a keyframe-colored PLY from a reconstruction and matching provenance."""
import argparse
import colorsys
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from plyfile import PlyData, PlyElement


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('ply', type=Path)
    parser.add_argument('provenance', type=Path)
    parser.add_argument('frame_csv', type=Path)
    parser.add_argument('output_dir', type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise SystemExit('Output directory already exists; choose a new path.')
    source = PlyData.read(args.ply)
    if len(source.elements) != 1 or source.elements[0].name != 'vertex':
        raise ValueError('Expected a vertex-only PLY; refusing to discard other elements.')
    points = source['vertex'].data
    fields = points.dtype.names
    if not all(x in fields for x in ('x', 'y', 'z', 'red', 'green', 'blue')) or 'kf_id' in fields:
        raise ValueError('Expected XYZ/RGB and no existing kf_id property.')
    with np.load(args.provenance) as data:
        ids = data['kf_id'].copy()
        pixels = data['pixel_index'].copy()
        frame_ids = data['frame_ids'].copy()
        shape = data['image_shape'].copy()
    if not (len(points) == len(ids) == len(pixels)):
        raise ValueError('PLY vertex count and provenance count differ.')
    if len(ids) == 0 or ids.min() < 0 or ids.max() >= len(frame_ids):
        raise ValueError('Invalid keyframe IDs.')
    if pixels.min() < 0 or pixels.max() >= int(np.prod(shape)):
        raise ValueError('Invalid provenance pixel IDs.')
    ids_unique, counts = np.unique(ids, return_counts=True)
    palette = np.zeros((len(frame_ids), 3), dtype=np.uint8)
    for k in ids_unique:
        # Golden-ratio hue ordering separates consecutive keyframes visually.
        hue = (int(k) * 0.618033988749895) % 1.0
        saturation = (0.88, 0.70, 0.96)[int(k) % 3]
        value = (0.98, 0.90, 0.83, 0.95)[int(k) % 4]
        palette[k] = np.rint(np.asarray(colorsys.hsv_to_rgb(hue, saturation, value))*255).astype(np.uint8)
    if len(np.unique(palette[ids_unique], axis=0)) != len(ids_unique):
        raise ValueError('Palette contains duplicate RGB colors.')
    dtype = np.dtype(points.dtype.descr + [('kf_id', '<i4')])
    result = np.empty(len(points), dtype=dtype)
    for name in fields:
        result[name] = points[name]
    colors = palette[ids]
    for j, name in enumerate(('red', 'green', 'blue')):
        result[name] = colors[:, j]
    result['kf_id'] = ids
    args.output_dir.mkdir(parents=True)
    output = args.output_dir / 'mapping_keyframe_colors.ply'
    PlyData([PlyElement.describe(result, 'vertex')], text=False, byte_order='<',
            comments=['RGB shows source keyframe; kf_id is a zero-based keyframe index']).write(output)
    frames = list(csv.DictReader(args.frame_csv.open()))
    with (args.output_dir / 'keyframe_colors.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['kf_id', 'frame_id', 'rgb_timestamp', 'red', 'green', 'blue', 'hex', 'vertex_count'])
        writer.writeheader()
        for k, count in zip(ids_unique, counts):
            fid = int(frame_ids[k]); r, g, b = (int(x) for x in palette[k])
            writer.writerow({'kf_id': int(k), 'frame_id': fid, 'rgb_timestamp': frames[fid]['rgb_timestamp'],
                             'red': r, 'green': g, 'blue': b, 'hex': f'#{r:02X}{g:02X}{b:02X}', 'vertex_count': int(count)})
    check = PlyData.read(output)['vertex'].data
    checks = {'vertex_count_equal': len(check) == len(points),
              'xyz_bitwise_equal': all(np.array_equal(check[n].view('u4'), points[n].view('u4')) for n in ('x','y','z')),
              'kf_id_equal': np.array_equal(check['kf_id'], ids),
              'rgb_equal_palette': all(np.array_equal(check[n], colors[:,j]) for j,n in enumerate(('red','green','blue'))),
              'unique_kf_colors': len(np.unique(palette[ids_unique],axis=0)) == len(ids_unique)}
    if not all(checks.values()):
        raise ValueError(f'Output validation failed: {checks}')
    manifest = {'source_ply': str(args.ply), 'source_ply_sha256': sha(args.ply),
                'provenance': str(args.provenance), 'provenance_sha256': sha(args.provenance),
                'frame_csv': str(args.frame_csv), 'frame_csv_sha256': sha(args.frame_csv),
                'output_ply': str(output), 'output_sha256': sha(output), 'script_sha256': sha(Path(__file__)),
                'vertices': len(points), 'keyframes': len(ids_unique), 'checks': checks,
                'description': 'Source keyframe RGB and zero-based kf_id scalar; XYZ and order unchanged.'}
    (args.output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
