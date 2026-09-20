"""Export the model as OBJ + MTL: welded vertices, colours snapped back to the
base palette so the file carries ~15 clean materials instead of per-face jitter."""
import numpy as np
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
from model import build, C

m = build()
verts, faces, cols = m.arrays()

# --- weld vertices -----------------------------------------------------------
key = np.round(verts, 5)
uniq, inv = np.unique(key, axis=0, return_inverse=True)
faces = inv[faces]
keep = faces[(faces[:, 0] != faces[:, 1]) &
             (faces[:, 1] != faces[:, 2]) &
             (faces[:, 0] != faces[:, 2])]
cols = cols[(faces[:, 0] != faces[:, 1]) &
            (faces[:, 1] != faces[:, 2]) &
            (faces[:, 0] != faces[:, 2])]
faces = keep

# --- snap jittered colours to the palette ------------------------------------
names = list(C)
pal = np.array([C[n] for n in names])
idx = np.argmin(((cols[:, None, :] - pal[None, :, :]) ** 2).sum(-1), axis=1)

OUT = ROOT / 'mesh'
OUT.mkdir(exist_ok=True)

with open(OUT / 'hedgehog.mtl', 'w') as f:
    for n, c in zip(names, pal):
        f.write('newmtl %s\nKd %.4f %.4f %.4f\nKa 0 0 0\nKs 0.03 0.03 0.03\n'
                'Ns 10\nillum 2\n\n' % (n, *c))

with open(OUT / 'hedgehog.obj', 'w') as f:
    f.write('# Low-poly hedgehog battle-buggy  (+Z forward, +Y up, ground at y=0)\n')
    f.write('mtllib hedgehog.mtl\no hedgehog_buggy\n')
    for v in uniq:
        f.write('v %.5f %.5f %.5f\n' % tuple(v))
    order = np.argsort(idx, kind='stable')
    cur = -1
    for i in order:
        if idx[i] != cur:
            cur = idx[i]; f.write('g %s\nusemtl %s\n' % (names[cur], names[cur]))
        a, b, c = faces[i] + 1
        f.write('f %d %d %d\n' % (a, b, c))
print('verts %d  tris %d  materials %d' % (len(uniq), len(faces), len(names)))
