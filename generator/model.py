"""Builds the low-poly hedgehog battle-buggy.  +Z = forward (snout), +Y = up.
The rear-deck turret is forward-firing: barrels overhang the head."""
import numpy as np
from mesh import (Mesh, hex2rgb, icosphere, tube, box, ellipsoid,
                  rot_x, rot_y, rot_z, rng)

C = {
    'fur':      hex2rgb('#c9884e'),
    'fur_dark': hex2rgb('#a96c3a'),
    'belly':    hex2rgb('#e8cda2'),
    'quill':    hex2rgb('#3a3742'),
    'quill2':   hex2rgb('#4e4a58'),
    'tip':      hex2rgb('#cfc4ae'),
    'nose':     hex2rgb('#241f26'),
    'eye':      hex2rgb('#1b1820'),
    'shine':    hex2rgb('#f2f4f8'),
    'tire':     hex2rgb('#26252c'),
    'tread':    hex2rgb('#17161b'),
    'hub':      hex2rgb('#e3902f'),
    'hub_dk':   hex2rgb('#b06c1d'),
    'metal':    hex2rgb('#5a6070'),
    'metal_dk': hex2rgb('#3d434f'),
    'gun':      hex2rgb('#34394a'),
    'accent':   hex2rgb('#d8503c'),
    'brass':    hex2rgb('#d9a441'),
}

BODY_C = np.array([0.0, 1.30, -0.05])
BODY_S = np.array([1.06, 0.98, 1.34])

# ---- forward-firing gun rig ------------------------------------------------
EL = np.radians(3.5)                                   # barrel elevation
BDIR = np.array([0.0, np.sin(EL), np.cos(EL)])         # aims at +Z (forward)
BARREL_X = 1.44                                        # sponsons flank the body
BARREL_ROOT_Y = 1.58
BARREL_ROOT_Z = -1.00
BARREL_LEN = 2.78
PED = np.array([0.0, 1.78, -1.16])                     # turret base


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0, 1)
    return np.linalg.norm(p - (a + ab * t))


def clearance_capsules():
    """Keep-out volumes the quills must not grow into."""
    caps = []
    for sx in (-1, 1):
        root = np.array([sx * BARREL_X, BARREL_ROOT_Y, BARREL_ROOT_Z])
        caps.append((root - BDIR * 0.45, root + BDIR * BARREL_LEN, 0.27))
    caps.append((PED, np.array([0.0, 2.34, -1.10]), 0.74))   # turret housing
    for sx in (-1, 1):                                       # feed arms
        caps.append((np.array([sx * 0.40, 2.02, -1.04]),
                     np.array([sx * BARREL_X, 1.66, -1.04]), 0.26))
    return caps


def trim_quill(p, d, L, caps):
    """Shorten (or reject) a quill that would grow into the gun rig."""
    for t in np.linspace(0.10, L, 26):
        pt = p + d * t
        if any(seg_dist(pt, a, b) < r for a, b, r in caps):
            return max(0.0, t - 0.10)
    return L


def build():
    m = Mesh()
    caps = clearance_capsules()

    # ----------------------------------------------------------- chassis
    m.add(*box((0, 0.72, -0.05), (1.62, 0.34, 2.5)), C['metal_dk'], 0.03)
    m.add(*box((0, 0.55, -0.05), (1.9, 0.16, 1.7)), C['metal'], 0.03)
    for z in (0.95, -0.95):                               # axles
        m.add(*tube((0, 0.62, z), (1, 0, 0),
                    [(-1.05, 0.10), (1.05, 0.10)], seg=8), C['metal_dk'], 0.03)
    m.add(*box((0, 0.62, 1.32), (1.3, 0.3, 0.3), rot_x(-0.25)), C['accent'], 0.04)

    # ----------------------------------------------------------- body
    bv, bf = ellipsoid(BODY_C, BODY_S, subdiv=2)
    bv = np.array(bv)
    for f in bf:
        n = np.mean(bv[list(f)], axis=0) - BODY_C
        up = n[1] / np.linalg.norm(n)
        col = C['belly'] if up < -0.15 else (C['fur'] if up < 0.3 else C['fur_dark'])
        m.add(bv, [f], col, 0.05)

    # ----------------------------------------------------------- head
    head_c = np.array([0.0, 1.16, 1.03])
    m.add(*ellipsoid(head_c, (0.74, 0.70, 0.66), subdiv=2), C['fur'], 0.045)
    m.add(*tube((0, 1.06, 1.40), (0, -0.14, 1),
                [(0.0, 0.46), (0.28, 0.29), (0.50, 0.15)], seg=9),
          C['belly'], 0.045)
    m.add(*ellipsoid((0, 0.96, 1.94), (0.17, 0.15, 0.14), subdiv=1), C['nose'], 0.05)
    for sx in (-1, 1):
        m.add(*ellipsoid((sx * 0.42, 1.03, 1.44), (0.26, 0.22, 0.22), subdiv=1),
              C['belly'], 0.05)
        m.add(*ellipsoid((sx * 0.35, 1.32, 1.50), (0.155, 0.165, 0.14), subdiv=1),
              C['eye'], 0.03)
        m.add(*ellipsoid((sx * 0.30, 1.39, 1.60), (0.058, 0.058, 0.05), subdiv=0),
              C['shine'], 0.0)
        m.add(*ellipsoid((sx * 0.37, 1.48, 1.42), (0.20, 0.07, 0.12), subdiv=1,
                         rot=rot_z(sx * 0.35)), C['fur_dark'], 0.05)
        m.add(*ellipsoid((sx * 0.62, 1.62, 0.92), (0.24, 0.24, 0.09), subdiv=1,
                         rot=rot_y(sx * 0.5) @ rot_z(-sx * 0.25)), C['fur_dark'], 0.05)
        m.add(*ellipsoid((sx * 0.64, 1.60, 0.88), (0.15, 0.15, 0.07), subdiv=1,
                         rot=rot_y(sx * 0.5) @ rot_z(-sx * 0.25)), C['belly'], 0.05)
        m.add(*ellipsoid((sx * 0.80, 0.94, 1.02), (0.20, 0.20, 0.26), subdiv=1,
                         rot=rot_z(sx * 0.3)), C['fur_dark'], 0.05)

    # ----------------------------------------------------------- quills
    sv, _ = icosphere(3)
    m.quill_count = 0
    for v in sv:
        if rng.random() > 0.52:                   # thin the dense sampling
            continue
        n = v / np.linalg.norm(v)
        if n[1] < 0.12:                           # spines ride the upper back
            continue
        surf = BODY_C + n * BODY_S
        if surf[2] > 0.88 and n[1] < 0.55:        # keep the face clear
            continue
        if surf[2] < -0.42 and n[1] > 0.30:       # clear deck for the gun mount
            continue
        p = BODY_C + n * BODY_S * 0.94
        d = n / (BODY_S ** 2)
        d = d / np.linalg.norm(d)
        d = d * 0.78 + np.array([0.0, 0.30, -0.42])       # sweep back & up
        d /= np.linalg.norm(d)
        d += rng.normal(0, 0.06, 3)
        d /= np.linalg.norm(d)
        L = 0.60 + 0.46 * max(0.0, n[1]) + rng.uniform(-0.10, 0.16)
        L = trim_quill(p, d, L, caps)
        if L < 0.30:
            continue
        r = (0.115 + rng.uniform(-0.02, 0.025)) * min(1.0, 0.55 + L / 1.2)
        m.quill_count += 1
        base = C['quill'] if rng.random() < 0.6 else C['quill2']
        seg, tw = 6, rng.uniform(0, 1.0)
        m.add(*tube(p, d, [(0.0, r), (L * 0.55, r * 0.72)], seg=seg,
                    cap_start=False, cap_end=False, twist=tw), base, 0.07)
        m.add(*tube(p, d, [(L * 0.55, r * 0.72), (L * 0.80, r * 0.42)], seg=seg,
                    cap_start=False, cap_end=False, twist=tw), C['tip'], 0.07)
        m.add(*tube(p, d, [(L * 0.80, r * 0.42), (L, 0.012)], seg=seg,
                    cap_start=False, cap_end=True, twist=tw), C['quill'], 0.07)

    # ----------------------------------------------------------- wheels
    def wheel(cx, cz, R, W):
        for sx in (-1, 1):
            m.part = 'wheel_%s%s' % ('f' if cz > 0 else 'r', 'l' if sx > 0 else 'r')
            x = sx * cx
            ax = (1, 0, 0)
            m.add(*tube((x, R, cz), ax,
                        [(-W / 2, R * 0.93), (-W * 0.34, R),
                         (W * 0.34, R), (W / 2, R * 0.93)], seg=13),
                  C['tire'], 0.045)
            for i in range(13):
                th = 2 * np.pi * i / 13
                m.add(*box((x, R + np.cos(th) * R, cz + np.sin(th) * R),
                           (W * 0.92, 0.10, R * 0.40), rot_x(-th)), C['tread'], 0.05)
            m.add(*tube((x, R, cz), ax,
                        [(sx * (W / 2 - 0.02), R * 0.52),
                         (sx * (W / 2 + 0.07), R * 0.44)], seg=11), C['hub'], 0.04)
            m.add(*tube((x, R, cz), ax,
                        [(sx * (W / 2 + 0.06), R * 0.18),
                         (sx * (W / 2 + 0.15), R * 0.14)], seg=8), C['hub_dk'], 0.04)
            for i in range(5):
                th = 2 * np.pi * i / 5 + 0.3
                m.add(*box((x + sx * (W / 2 + 0.05), R + np.cos(th) * R * 0.33,
                            cz + np.sin(th) * R * 0.33),
                           (0.05, 0.10, 0.10), rot_x(-th)), C['metal'], 0.05)
    wheel(1.02, -0.95, 0.72, 0.42)
    wheel(0.96, 0.95, 0.58, 0.34)
    m.part = 'body'

    for sx in (-1, 1):                                    # rear fenders
        v, f = tube((sx * 1.02, 0.72, -0.95), (1, 0, 0),
                    [(-0.24, 0.0), (-0.20, 0.86), (0.20, 0.86), (0.24, 0.0)], seg=13)
        v = np.array(v)
        m.add(v, [t for t in f if np.mean(v[list(t)], axis=0)[1] > 0.95],
              C['accent'], 0.045)

    # ----------------------------------------------------------- gun rig
    # armoured rear deck + low turret base
    m.add(*box((0, 1.72, -1.16), (1.40, 0.22, 1.30), rot_x(-0.20)), C['metal_dk'], 0.035)
    m.add(*box((0, 1.83, -1.16), (1.14, 0.12, 1.06), rot_x(-0.20)), C['metal'], 0.035)
    m.add(*tube((0, 1.84, -1.16), (0, 1, 0), [(0, 0.50), (0.14, 0.44)], seg=11),
          C['metal_dk'], 0.04)
    m.add(*box((0, 2.06, -1.14), (1.22, 0.56, 0.92)), C['gun'], 0.04)
    m.add(*box((0, 2.36, -1.14), (0.84, 0.14, 0.78)), C['metal'], 0.04)
    m.add(*box((0, 2.06, -0.70), (0.80, 0.34, 0.16)), C['accent'], 0.045)
    # ammo drum across the top, feeding both guns
    m.add(*tube((0, 2.50, -1.16), (1, 0, 0), [(-0.62, 0.28), (0.62, 0.28)], seg=10),
          C['metal_dk'], 0.04)
    for sx in (-1, 1):
        m.add(*tube((0, 2.50, -1.16), (1, 0, 0),
                    [(sx * 0.62, 0.15), (sx * 0.70, 0.13)], seg=8), C['brass'], 0.04)

    # outrigger arms carrying the sponsons
    for sx in (-1, 1):
        m.add(*box((sx * 0.95, 1.82, -1.06), (1.24, 0.24, 0.42),
                   rot_z(-sx * 0.37)), C['metal'], 0.04)
        m.add(*box((sx * 1.44, 1.68, -1.06), (0.28, 0.46, 0.40)), C['metal_dk'], 0.04)
        # ammo feed chute down the arm
        m.add(*tube((sx * 0.55, 2.40, -1.12), (0, -1, 0),
                    [(0.0, 0.11), (0.52, 0.11)], seg=8), C['brass'], 0.05)

    # twin cannons, aimed forward past the head
    for sx in (-1, 1):
        root = np.array([sx * BARREL_X, BARREL_ROOT_Y, BARREL_ROOT_Z])
        m.add(*tube(root, BDIR, [(-0.46, 0.22), (0.10, 0.24), (0.24, 0.15)], seg=10),
              C['metal_dk'], 0.04)
        m.add(*tube(root, BDIR, [(0.24, 0.125), (BARREL_LEN - 0.32, 0.112)], seg=10),
              C['gun'], 0.04)
        for d in (0.52, 0.80, 1.08):                      # cooling rings
            m.add(*tube(root, BDIR, [(d, 0.165), (d + 0.08, 0.165)], seg=10),
                  C['metal'], 0.04)
        m.add(*tube(root, BDIR,                           # muzzle brake
                    [(BARREL_LEN - 0.32, 0.18), (BARREL_LEN - 0.06, 0.17),
                     (BARREL_LEN - 0.02, 0.112)], seg=10), C['metal_dk'], 0.04)
        m.add(*tube(root, BDIR, [(BARREL_LEN - 0.11, 0.082), (BARREL_LEN, 0.082)],
                    seg=10), C['accent'], 0.04)
        # brace tying the barrel back to the fender
        m.add(*box((sx * 1.26, 1.36, -0.28), (0.66, 0.14, 0.22),
                   rot_z(sx * 0.62)), C['metal_dk'], 0.045)
    # sight + antenna on the turret
    m.add(*box((0, 2.46, -0.78), (0.24, 0.18, 0.46), rot_x(-EL)), C['metal_dk'], 0.04)
    m.add(*tube((0.46, 2.42, -1.42), (0, 1, 0), [(0, 0.035), (0.92, 0.018)], seg=6),
          C['metal_dk'], 0.04)
    m.add(*ellipsoid((0.46, 3.36, -1.42), (0.07, 0.07, 0.07), subdiv=1),
          C['accent'], 0.03)
    # exhaust stacks
    for sx in (-1, 1):
        m.add(*tube((sx * 0.78, 1.52, -1.52), (0, 1, 0) @ rot_x(0.22).T,
                    [(0, 0.10), (0.62, 0.095), (0.70, 0.13)], seg=8),
              C['metal_dk'], 0.05)

    # headlight pods
    for sx in (-1, 1):
        m.add(*tube((sx * 0.62, 0.95, 1.26), (0, 0.18, 1),
                    [(0.0, 0.17), (0.16, 0.19)], seg=8), C['metal_dk'], 0.04)
        m.add(*tube((sx * 0.62, 0.95, 1.26), (0, 0.18, 1),
                    [(0.16, 0.15), (0.20, 0.13)], seg=8), C['brass'], 0.03)

    m.add(*box((0, 1.05, -1.52), (0.9, 0.14, 0.12), rot_x(0.1)), C['brass'], 0.05)
    return m
