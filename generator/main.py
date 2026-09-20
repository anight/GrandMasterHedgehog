import sys, time
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
import numpy as np
from model import build
from render import render, look_at

quick = '--quick' in sys.argv
t0 = time.time()
m = build()
verts, faces, cols = m.arrays()
print('tris:', len(m.faces), 'build %.1fs' % (time.time() - t0))

W, H, SS = (520, 380, 1) if quick else (1600, 1150, 3)

VIEWS = {
    'hero':  dict(eye=(6.6, 3.6, 6.2), target=(0, 1.35, -0.1)),
    'rear':  dict(eye=(-5.6, 3.3, -7.0), target=(0, 1.5, -0.5)),
    'side':  dict(eye=(11.0, 2.7, 0.9),  target=(0, 1.45, -0.3)),
    'front': dict(eye=(2.4, 2.8, 8.6),   target=(0, 1.3, 0.3)),
}


def fit_fov(eye, target, w, h, margin=0.90):
    V, campos = look_at(eye, target)
    p = (verts - campos) @ V.T
    z = np.maximum(-p[:, 2], 1e-3)
    fx = (w / 2) / np.max(np.abs(p[:, 0]) / z)
    fy = (h / 2) / np.max(np.abs(p[:, 1]) / z)
    focal = min(fx, fy) * margin
    return float(np.degrees(2 * np.arctan((h / 2) / focal)))


want = [a for a in sys.argv[1:] if not a.startswith('-')] or list(VIEWS)
for name in want:
    v = VIEWS[name]
    fov = fit_fov(v['eye'], v['target'], W, H)
    t = time.time()
    im = render(m, v['eye'], v['target'], W, H, fov=fov, ss=SS)
    out = ROOT / 'renders'
    out.mkdir(exist_ok=True)
    p = out / f'hedgehog_{name}.png'
    im.save(p)
    print('%-6s fov %.1f  %.1fs  -> %s' % (name, fov, time.time() - t, p.name))
