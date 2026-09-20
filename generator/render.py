"""Flat-shaded software rasterizer: z-buffer, hemisphere + key/fill/rim lights,
planar contact shadow, 3x supersampling."""
import numpy as np
from PIL import Image
from mesh import hex2rgb


def srgb_to_lin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def look_at(eye, target, up=(0, 1, 0)):
    eye = np.asarray(eye, float); target = np.asarray(target, float)
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float)); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    M = np.stack([r, u, -f])          # world -> view rotation
    return M, eye


KEY_DIR = np.array([-0.52, 0.80, 0.50]); KEY_DIR /= np.linalg.norm(KEY_DIR)
FILL_DIR = np.array([0.80, 0.22, 0.35]); FILL_DIR /= np.linalg.norm(FILL_DIR)
KEY_COL = srgb_to_lin(hex2rgb('#fff2dc')) * 1.28
FILL_COL = srgb_to_lin(hex2rgb('#9dc4e8')) * 0.34
SKY = srgb_to_lin(hex2rgb('#b9d3e8')) * 0.42
GND = srgb_to_lin(hex2rgb('#6b5c4e')) * 0.20
RIM_COL = srgb_to_lin(hex2rgb('#ffd9a8')) * 0.50


def ground_plane(radius=16.0, seg=44, rings=9):
    v = [np.array([0.0, 0.0, 0.0])]
    for r in range(1, rings + 1):
        rad = radius * (r / rings) ** 1.6
        for s in range(seg):
            th = 2 * np.pi * s / seg
            v.append(np.array([np.cos(th) * rad, 0.0, np.sin(th) * rad]))
    f = []
    for s in range(seg):
        f.append((0, 1 + (s + 1) % seg, 1 + s))
    for r in range(rings - 1):
        A, B = 1 + r * seg, 1 + (r + 1) * seg
        for s in range(seg):
            s2 = (s + 1) % seg
            f += [(A + s, B + s2, B + s), (A + s, A + s2, B + s2)]
    return np.array(v), f


def render(mesh, eye, target, width, height, fov=26.0, ss=3,
           bg_top='#eef4f8', bg_bot='#c2cfda', ground='#c6b79f', up=(0, 1, 0)):
    W, H = width * ss, height * ss
    V, campos = look_at(eye, target, up)

    verts, faces, cols = mesh.arrays()

    # --- assemble draw list: ground, planar shadow, model -------------------
    gv, gf = ground_plane()
    g_col = srgb_to_lin(hex2rgb(ground))

    tri_v, tri_c, tri_shade = [], [], []

    grng = np.random.default_rng(3)
    for f in gf:
        tri_v.append(gv[list(f)])
        tri_c.append(g_col * (1.0 + grng.uniform(-0.055, 0.055)))
        tri_shade.append(1)

    # planar shadow (project model along the key light onto y=0)
    L = KEY_DIR
    shadow_col = srgb_to_lin(hex2rgb(ground)) * 0.52
    for f in faces:
        p = verts[list(f)]
        t = p[:, 1] / L[1]
        sp = p - np.outer(t, L)
        sp[:, 1] = 0.004
        tri_v.append(sp); tri_c.append(shadow_col); tri_shade.append(0)

    for i, f in enumerate(faces):
        tri_v.append(verts[list(f)]); tri_c.append(srgb_to_lin(cols[i]))
        tri_shade.append(1)

    tri_v = np.array(tri_v)                      # (N,3,3)
    tri_c = np.array(tri_c)
    tri_shade = np.array(tri_shade)

    # --- shading ------------------------------------------------------------
    e0 = tri_v[:, 1] - tri_v[:, 0]
    e1 = tri_v[:, 2] - tri_v[:, 0]
    nrm = np.cross(e0, e1)
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    ln[ln == 0] = 1
    nrm = nrm / ln
    ctr = tri_v.mean(axis=1)
    vdir = campos - ctr
    vdir /= np.linalg.norm(vdir, axis=1, keepdims=True)

    # face the camera (meshes are closed, but be safe)
    flip = (np.sum(nrm * vdir, axis=1) < 0)
    nrm[flip] *= -1

    key = np.clip(nrm @ L, 0, 1)[:, None]
    fill = np.clip(nrm @ FILL_DIR, 0, 1)[:, None]
    hemi = (0.5 + 0.5 * nrm[:, 1])[:, None]
    amb = SKY * hemi + GND * (1 - hemi)
    rim = np.clip(1.0 - np.sum(nrm * vdir, axis=1), 0, 1)[:, None] ** 3.0
    rim *= np.clip(nrm @ np.array([-0.4, 0.5, -0.75]), 0, 1)[:, None]

    lit = tri_c * (amb + KEY_COL * key + FILL_COL * fill) + RIM_COL * rim
    lit = np.where(tri_shade[:, None] == 1, lit, tri_c * 0.92)

    # --- project ------------------------------------------------------------
    vw = (tri_v.reshape(-1, 3) - campos) @ V.T
    vw = vw.reshape(-1, 3, 3)
    z = -vw[:, :, 2]
    focal = (H / 2) / np.tan(np.radians(fov) / 2)
    near = 0.05
    valid = np.all(z > near, axis=1)

    zc = np.maximum(z, near)
    sx = vw[:, :, 0] / zc * focal + W / 2
    sy = -vw[:, :, 1] / zc * focal + H / 2
    invz = 1.0 / zc

    # --- rasterize ----------------------------------------------------------
    img = np.zeros((H, W, 3), dtype=np.float32)
    yy = np.arange(H)[:, None] / H
    top, bot = srgb_to_lin(hex2rgb(bg_top)), srgb_to_lin(hex2rgb(bg_bot))
    img[:] = (top * (1 - yy ** 1.25) + bot * (yy ** 1.25))[:, None, :].astype(np.float32)
    zbuf = np.full((H, W), -1e30, dtype=np.float64)

    order = np.argsort(-ctr[:, 2])  # arbitrary; z-buffer decides
    for i in order:
        if not valid[i]:
            continue
        x0, x1, x2 = sx[i]; y0, y1, y2 = sy[i]
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if abs(area) < 1e-9:
            continue
        xmin = max(int(np.floor(min(x0, x1, x2))), 0)
        xmax = min(int(np.ceil(max(x0, x1, x2))) + 1, W)
        ymin = max(int(np.floor(min(y0, y1, y2))), 0)
        ymax = min(int(np.ceil(max(y0, y1, y2))) + 1, H)
        if xmin >= xmax or ymin >= ymax:
            continue
        px = np.arange(xmin, xmax) + 0.5
        py = np.arange(ymin, ymax)[:, None] + 0.5
        w0 = ((x1 - x0) * (py - y0) - (px - x0) * (y1 - y0)) / area
        w1 = ((px - x0) * (y2 - y0) - (x2 - x0) * (py - y0)) / area
        inside = (w0 >= 0) & (w1 >= 0) & (w0 + w1 <= 1)
        if not inside.any():
            continue
        b1, b2, b0 = w1, w0, 1.0 - w0 - w1
        depth = b0 * invz[i, 0] + b1 * invz[i, 1] + b2 * invz[i, 2]
        sub = zbuf[ymin:ymax, xmin:xmax]
        msk = inside & (depth > sub)
        if not msk.any():
            continue
        sub[msk] = depth[msk]
        img[ymin:ymax, xmin:xmax][msk] = lit[i].astype(np.float32)

    # --- output -------------------------------------------------------------
    out = lin_to_srgb(img)
    out = (out * 255).astype(np.uint8)
    im = Image.fromarray(out, 'RGB')
    return im.resize((width, height), Image.LANCZOS)
