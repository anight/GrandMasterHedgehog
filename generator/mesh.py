"""Procedural low-poly mesh construction for the hedgehog battle-buggy."""
import numpy as np

rng = np.random.default_rng(7)


def hex2rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []   # (i, j, k)
        self.colors = []  # per-face rgb (sRGB 0..1)
        self.part = 'body'
        self.parts = []   # per-face part name (wheels spin on their own)

    def add(self, verts, faces, color, jitter=0.035, flat_jitter=None):
        base = len(self.verts)
        self.verts.extend([np.asarray(v, dtype=float) for v in verts])
        col = np.asarray(color, dtype=float)
        for f in faces:
            self.faces.append((f[0] + base, f[1] + base, f[2] + base))
            j = jitter if flat_jitter is None else flat_jitter
            k = 1.0 + rng.uniform(-j, j)
            self.colors.append(np.clip(col * k, 0, 1))
            self.parts.append(self.part)

    def arrays(self):
        return (np.array(self.verts), np.array(self.faces, dtype=np.int32),
                np.array(self.colors))


# ---------------------------------------------------------------- primitives
def icosphere(subdiv=1):
    t = (1.0 + 5.0 ** 0.5) / 2.0
    v = np.array([
        [-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
        [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
        [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], dtype=float)
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
         (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
         (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    verts = [x for x in v]
    for _ in range(subdiv):
        cache, nf = {}, []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = verts[a] + verts[b]
                verts.append(m / np.linalg.norm(m))
                cache[key] = len(verts) - 1
            return cache[key]

        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(verts), f


def basis_from(axis):
    a = np.asarray(axis, dtype=float)
    a = a / np.linalg.norm(a)
    up = np.array([0.0, 1.0, 0.0]) if abs(a[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(up, a); u /= np.linalg.norm(u)
    w = np.cross(a, u)
    return u, w, a


def tube(center, axis, rings, seg=10, cap_start=True, cap_end=True, twist=0.0):
    """rings = [(dist_along_axis, radius), ...]"""
    u, w, a = basis_from(axis)
    verts, faces = [], []
    ang = np.linspace(0, 2 * np.pi, seg, endpoint=False) + twist
    ring_idx = []
    for d, r in rings:
        idx0 = len(verts)
        for th in ang:
            verts.append(np.asarray(center, float) + a * d
                         + (u * np.cos(th) + w * np.sin(th)) * r)
        ring_idx.append(idx0)
    for n in range(len(rings) - 1):
        A, B = ring_idx[n], ring_idx[n + 1]
        for s in range(seg):
            s2 = (s + 1) % seg
            faces += [(A + s, B + s, B + s2), (A + s, B + s2, A + s2)]
    if cap_start:
        c0 = len(verts); verts.append(np.asarray(center, float) + a * rings[0][0])
        A = ring_idx[0]
        for s in range(seg):
            faces.append((c0, A + (s + 1) % seg, A + s))
    if cap_end:
        c1 = len(verts); verts.append(np.asarray(center, float) + a * rings[-1][0])
        A = ring_idx[-1]
        for s in range(seg):
            faces.append((c1, A + s, A + (s + 1) % seg))
    return verts, faces


def box(center, size, rot=None):
    c = np.asarray(center, float); s = np.asarray(size, float) / 2.0
    signs = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
    v = signs * s
    if rot is not None:
        v = v @ rot.T
    v = v + c
    f = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
         (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5), (0, 4, 7), (0, 7, 3)]
    return list(v), f


def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def ellipsoid(center, scale, subdiv=1, rot=None):
    v, f = icosphere(subdiv)
    v = v * np.asarray(scale, float)
    if rot is not None:
        v = v @ rot.T
    return list(v + np.asarray(center, float)), f
