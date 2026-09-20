"""Export game-ready geometry: parts split so the wheels can spin on their own,
colours packed as a palette index + per-face brightness (keeps the facet jitter)."""
import json
import pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
from model import build, C, BARREL_X, BARREL_ROOT_Y, BARREL_ROOT_Z, BARREL_LEN, BDIR

PIVOTS = {
    'wheel_fl': ((0.96, 0.58, 0.95), 0.58),
    'wheel_fr': ((-0.96, 0.58, 0.95), 0.58),
    'wheel_rl': ((1.02, 0.72, -0.95), 0.72),
    'wheel_rr': ((-1.02, 0.72, -0.95), 0.72),
}

m = build()
verts, faces, cols = m.arrays()
parts = np.array(m.parts)

names = list(C)
pal = np.array([C[n] for n in names])
mat = np.argmin(((cols[:, None, :] - pal[None, :, :]) ** 2).sum(-1), axis=1)
# recover the per-face brightness jitter that was baked into the colour
jit = np.clip((cols.sum(1) + 1e-9) / (pal[mat].sum(1) + 1e-9), 0.8, 1.25)

out = {'palette': ['#%02x%02x%02x' % tuple((c * 255).round().astype(int))
                   for c in pal], 'parts': []}

for name in ['body'] + list(PIVOTS):
    sel = np.where(parts == name)[0]
    pivot, radius = PIVOTS.get(name, ((0.0, 0.0, 0.0), 0.0))
    pf = faces[sel]
    used, inv = np.unique(pf.reshape(-1), return_inverse=True)
    pos = verts[used] - np.array(pivot)
    out['parts'].append({
        'name': name,
        'pivot': [round(float(x), 4) for x in pivot],
        'radius': radius,
        'pos': [round(float(x), 3) for x in pos.reshape(-1)],
        'idx': [int(i) for i in inv],
        'mat': [int(i) for i in mat[sel]],
        'jit': [round(float(x), 3) for x in jit[sel]],
    })
    print('%-9s verts %5d  tris %5d' % (name, len(used), len(sel)))

muzzle_y = BARREL_ROOT_Y + BDIR[1] * BARREL_LEN
muzzle_z = BARREL_ROOT_Z + BDIR[2] * BARREL_LEN
out['muzzles'] = [[round(BARREL_X, 3), round(float(muzzle_y), 3), round(float(muzzle_z), 3)],
                  [round(-BARREL_X, 3), round(float(muzzle_y), 3), round(float(muzzle_z), 3)]]
out['aim'] = [round(float(x), 4) for x in BDIR]
out['bounds'] = {
    'min': [round(float(x), 3) for x in verts.min(0)],
    'max': [round(float(x), 3) for x in verts.max(0)],
}

OUT = ROOT / 'web' / 'buggy.json'
OUT.parent.mkdir(exist_ok=True)

with open(OUT, 'w') as f:
    json.dump(out, f, separators=(',', ':'))
print('web/buggy.json  %.0f KB' % (OUT.stat().st_size / 1024))
print('muzzles', out['muzzles'], 'bounds', out['bounds'])
