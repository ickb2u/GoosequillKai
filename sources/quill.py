"""鹅管楷 Goosequill Kai — 扁锋笔引擎：把笔画骨架用一支斜切的鹅管笔重新写一遍"""
import math, numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

P = dict(W=96, T=24, ANG=33, STEP=14, CORNER=52, SIMPL=1.1)

def _nib(w, t, ang, n=5):
    # 圆角矩形笔尖（两端半圆）
    r = t/2; h = max(w/2 - r, 0.01); pts=[]
    for i in range(n+1):
        a = -math.pi/2 + math.pi*i/n; pts.append((h + r*math.cos(a), r*math.sin(a)))
    for i in range(n+1):
        a = math.pi/2 + math.pi*i/n; pts.append((-h + r*math.cos(a), r*math.sin(a)))
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return np.array([(x*c - y*s, x*s + y*c) for x, y in pts])

def _split_corners(pts, deg):
    segs=[[pts[0]]]
    for i in range(1, len(pts)-1):
        a = pts[i]-pts[i-1]; b = pts[i+1]-pts[i]
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        segs[-1].append(pts[i])
        if la > 1e-6 and lb > 1e-6:
            cosv = np.clip(a.dot(b)/(la*lb), -1, 1)
            if math.degrees(math.acos(cosv)) > deg:
                segs.append([pts[i]])
    segs[-1].append(pts[-1])
    return [np.array(s) for s in segs]

def _catmull(pts, step):
    if len(pts) < 3:
        n = max(2, int(np.linalg.norm(pts[-1]-pts[0])/step)+1)
        return np.linspace(pts[0], pts[-1], n)
    p = np.vstack([2*pts[0]-pts[1], pts, 2*pts[-1]-pts[-2]]); out=[]
    for i in range(1, len(p)-2):
        p0,p1,p2,p3 = p[i-1],p[i],p[i+1],p[i+2]
        n = max(2, int(np.linalg.norm(p2-p1)/step)+1)
        for k in range(n):
            t=k/n; t2=t*t; t3=t2*t
            out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t2+(-p0+3*p1-3*p2+p3)*t3))
    out.append(pts[-1]); return np.array(out)

def _dedupe(pts):
    out=[pts[0]]
    for p in pts[1:]:
        if np.linalg.norm(p-out[-1])>0.5: out.append(p)
    return np.array(out) if len(out)>1 else np.array([pts[0], pts[0]+[1,0]])

def _chaikin(pts, deg):
    # 对非转角顶点做一次切角，让粗糙的折线骨架更圆
    n=len(pts)
    if n<3: return pts
    closed = np.linalg.norm(pts[0]-pts[-1])<1.0
    out=[pts[0]]
    for i in range(1,n-1):
        a=pts[i]-pts[i-1]; b=pts[i+1]-pts[i]; la,lb=np.linalg.norm(a),np.linalg.norm(b)
        ang=math.degrees(math.acos(np.clip(a.dot(b)/(la*lb+1e-9),-1,1)))
        if ang>deg or ang<3: out.append(pts[i])
        else: out += [pts[i]-a*0.25, pts[i]+b*0.25]
    out.append(pts[-1]); return np.array(out)

def stroke_poly(median, P=P, wscale=1.0, plain=False):
    """median: list of (x,y) 字体坐标(y向上)。返回 shapely 多边形"""
    pts = _dedupe(np.array(median, float))
    for _ in range(P.get('CHAIKIN',0)): pts = _chaikin(pts, P['CORNER'])
    length = float(np.sum(np.linalg.norm(np.diff(pts,axis=0),axis=1)))
    parts = _split_corners(pts, P['CORNER'])
    path = np.vstack([_catmull(s, P['STEP'])[(0 if i==0 else 1):] for i,s in enumerate(parts)])
    d = np.linalg.norm(np.diff(path,axis=0),axis=1); cum = np.concatenate([[0],np.cumsum(d)])
    L = cum[-1] if cum[-1]>0 else 1
    # 收笔方向
    e = pts[-1]-pts[-2]; ea = math.degrees(math.atan2(e[1], e[0]))
    last_len = np.linalg.norm(e)
    hook = len(parts)>1 and last_len < 0.45*L and last_len < 170
    pie = -170 < ea < -100            # 撇：向左下
    ti  = 15 < ea < 80                # 提：向右上
    na  = -75 < ea < -20 and L > 150  # 捺：向右下
    if plain and len(median)!=4: hook=pie=ti=na=False
    W, T = P['W']*wscale, P['T']*wscale
    W *= min(1.0, 0.72 + L/420)       # 短笔（点）笔尖收窄
    hulls=[]; prev=None
    for q, s in zip(path, cum):
        t = s/L
        w = W*(1.0 + 0.10*math.exp(-(s/38)**2))          # 起笔一顿
        tt = T
        if hook:
            hs = max(0.0, (s-(L-last_len))/max(last_len,1))
            w *= 1-0.75*hs**1.3; tt *= 1-0.45*hs
        elif pie or ti:
            k = max(0.0,(t-0.35)/0.65); w *= 1-0.80*k**1.4; tt *= 1-0.38*k**2
        elif na:
            k = max(0.0,(t-0.25)/0.75); w *= 1+0.22*math.sin(math.pi*min(k/0.8,1)*0.5) if k<0.8 else 1.22*(1-0.75*((k-0.8)/0.2)**1.5)
        else:
            w *= 1 - 0.10*math.sin(math.pi*t)               # 中段微收，行笔提按
        nb = _nib(max(w,tt), tt, P['ANG']) + q
        if prev is not None:
            hulls.append(Polygon(np.vstack([prev, nb])).convex_hull)
        prev = nb
    return unary_union(hulls)

def glyph_poly(medians, P=P, wscale=1.0, plain=False):
    g = unary_union([stroke_poly(m, P, wscale, plain) for m in medians]).buffer(0)
    return g.simplify(P['SIMPL'], preserve_topology=True)

def polys(g):
    if g.is_empty: return []
    return list(g.geoms) if isinstance(g, MultiPolygon) or g.geom_type=='GeometryCollection' else [g]

S = 1000/1024
def mmh_to_font(median): return [(x*S, (y-124)*S) for x,y in median]
