#!/usr/bin/env python3
"""构建 鹅管楷 Goosequill Kai。用法: python3 sources/build.py [Light|Regular|Bold ...] [--only 字符]"""
import json, math, os, sys, time
from multiprocessing import Pool
from shapely.geometry.polygon import orient
import quill

HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
DATA=os.environ.get('MMH_GRAPHICS', os.path.join(HERE,'data','graphics.txt'))
VERSION='1.100'
FAMILY_EN, FAMILY_ZH, PS = 'Goosequill Kai', '鹅管楷', 'GoosequillKai'
WEIGHTS = {   # 笔宽 W / 笔尖厚 T / 密字减细斜率 / OS2 字重
 'Light':   dict(W=54,  T=15, slope=0.014, floor=0.78, cls=300),
 'Regular': dict(W=82,  T=21, slope=0.022, floor=0.70, cls=400),
 'Bold':    dict(W=108, T=27, slope=0.028, floor=0.58, cls=700),
}
CUR=None
def setw(name):
    global CUR; CUR=WEIGHTS[name]; quill.P.update(W=CUR['W'], T=CUR['T'])
def wscale_for(n): return max(CUR['floor'], min(1.06, 1.0 + CUR['slope']*(6-n)))

# ---------- 多边形 → 带曲线的 TrueType 轮廓 ----------
def smooth(c, r=13.0, corner=38.0):
    n=len(c); out=[]
    for i in range(n):
        p0,p1,p2=c[i-1],c[i],c[(i+1)%n]
        ax,ay=p1[0]-p0[0],p1[1]-p0[1]; bx,by=p2[0]-p1[0],p2[1]-p1[1]
        la,lb=math.hypot(ax,ay),math.hypot(bx,by)
        if la<1e-6 or lb<1e-6: continue
        ang=math.degrees(math.acos(max(-1,min(1,(ax*bx+ay*by)/(la*lb)))))
        if ang>corner or ang<1.5:
            out.append((p1[0],p1[1],1)); continue
        if la>2*r: out.append((p1[0]-ax/la*r, p1[1]-ay/la*r, 1))
        out.append((p1[0],p1[1],0))
        if lb>2*r: out.append((p1[0]+bx/lb*r, p1[1]+by/lb*r, 1))
    res=[]
    for x,y,o in out:
        q=(int(round(x)),int(round(y)),o)
        if not res or res[-1][:2]!=q[:2]: res.append(q)
    if len(res)>1 and res[0][:2]==res[-1][:2]: res.pop()
    return res

def to_contours(g):
    out=[]
    for p in quill.polys(g):
        if p.area<30: continue
        p=orient(p,-1)
        for ring in [p.exterior]+list(p.interiors):
            c=smooth(list(ring.coords[:-1]))
            if len(c)>=3: out.append(c)
    return out

def draw(pen, c):
    idx=next((i for i,q in enumerate(c) if q[2]), None)
    if idx is None:
        pen.qCurveTo(*[(x,y) for x,y,_ in c], None); pen.closePath(); return
    c=c[idx:]+c[:idx]; pen.moveTo(c[0][:2]); offs=[]
    for x,y,o in c[1:]:
        if o:
            (pen.qCurveTo(*offs,(x,y)) if offs else pen.lineTo((x,y))); offs=[]
        else: offs.append((x,y))
    if offs: pen.qCurveTo(*offs, c[0][:2])
    pen.closePath()

def do_hanzi(line):
    j=json.loads(line); meds=[quill.mmh_to_font(m) for m in j['medians']]
    return j['character'], to_contours(quill.glyph_poly(meds, quill.P, wscale_for(len(meds)))), 1000

# ---------- 西文：Hershey Simplex 单线骨架，同一支笔 ----------
def latin():
    from HersheyFonts import HersheyFonts
    hf=HersheyFonts(); hf.load_default_font('futural'); K=700/21; res=[]
    LP=dict(quill.P, CORNER=75, W=quill.P['W']*1.12, T=quill.P['T']*0.86)
    for code in range(0x21,0x7f):
        ch=chr(code); gl=hf.all_glyphs.get(ch)
        if gl is None: continue
        st=[[(x*K+18,(9-y)*K) for x,y in s] for s in hf.strokes_for_text(ch) if len(s)>1]
        if not st: continue
        res.append((ch, to_contours(quill.glyph_poly(st, LP, 1.0, True)), int(round(gl.char_width*K))+36))
    return res

# ---------- 中文标点：自绘骨架 ----------
def arc(cx,cy,rx,ry,a0,a1,n=14):
    return [(cx+rx*math.cos(math.radians(a0+(a1-a0)*i/n)), cy+ry*math.sin(math.radians(a0+(a1-a0)*i/n))) for i in range(n+1)]
def dot(x,y): return [(x-14,y+14),(x+14,y-14)]
def comma(x,y,s=1): return [(x-8*s,y+30*s),(x+12*s,y+5*s),(x+8*s,y-40*s),(x-38*s,y-105*s)]
def rcomma(x,y,s=1): return [(x+38*s,y+105*s),(x-8*s,y+40*s),(x-12*s,y-5*s),(x+8*s,y-30*s)]
PUNCT = {
 '，':[comma(190,40)], '。':[arc(210,50,78,78,100,460,20)], '、':[[(120,120),(235,-30)]],
 '：':[dot(200,330),dot(200,40)], '；':[dot(200,330),comma(195,40)],
 '！':[[(200,740),(200,210)],dot(200,40)],
 '？':[arc(250,590,150,150,160,-60,14)+[(260,400),(250,230)],dot(250,40)],
 '“':[rcomma(640,640,.9),rcomma(820,640,.9)], '”':[comma(180,720,.9),comma(360,720,.9)],
 '‘':[rcomma(790,640,.9)], '’':[comma(210,720,.9)],
 '（':[arc(1100,340,400,520,150,210,12)], '）':[arc(-100,340,400,520,30,-30,12)],
 '《':[[(760,720),(470,340),(760,-40)],[(940,720),(650,340),(940,-40)]],
 '》':[[(240,720),(530,340),(240,-40)],[(60,720),(350,340),(60,-40)]],
 '〈':[[(900,720),(610,340),(900,-40)]], '〉':[[(100,720),(390,340),(100,-40)]],
 '「':[[(920,760),(700,760),(700,180)]], '」':[[(300,500),(300,-80),(80,-80)]],
 '『':[[(920,760),(640,760),(640,180),(760,180),(760,650),(920,650)]],
 '』':[[(80,-80),(360,-80),(360,500),(240,500),(240,30),(80,30)]],
 '【':[[(930,780),(700,780),(700,-100),(930,-100)],[(930,780),(790,340),(930,-100)]],
 '】':[[(70,780),(300,780),(300,-100),(70,-100)],[(70,780),(210,340),(70,-100)]],
 '—':[[(0,340),(1000,340)]], '…':[dot(170,340),dot(500,340),dot(830,340)], '·':[dot(500,340)],
 '～':[[(100,320)]+arc(300,330,130,70,170,10,8)+arc(700,350,130,70,190,350,8)+[(900,370)]],
 '　':[],
}
def punct():
    PP=dict(quill.P, CORNER=75)
    return [(ch, to_contours(quill.glyph_poly(st, PP, 1.12, True)) if st else [], 1000) for ch,st in PUNCT.items()]

def build(weight, only=None):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    setw(weight); t=time.time()
    lines=[l for l in open(DATA,encoding='utf8').read().splitlines() if not only or json.loads(l)['character'] in only]
    with Pool(initializer=setw, initargs=(weight,)) as pool: han=pool.map(do_hanzi, lines, chunksize=40)
    glyphs={ch:(c,adv) for ch,c,adv in han+punct()}
    for ch,c,adv in latin():
        glyphs[ch]=(c,adv); fw=chr(ord(ch)+0xFEE0)
        if fw not in glyphs:
            dx=(1000-adv)//2; glyphs[fw]=([[(x+dx,y,o) for x,y,o in k] for k in c],1000)
    glyphs[' ']=([],300); glyphs[' ']=([],300)
    order=['.notdef']; cmap={}; gl={}; met={}
    pen=TTGlyphPen(None)
    for c in ([(100,0),(100,700),(500,700),(500,0)],[(160,60),(440,60),(440,640),(160,640)]):
        pen.moveTo(c[0]); [pen.lineTo(q) for q in c[1:]]; pen.closePath()
    gl['.notdef']=pen.glyph(); met['.notdef']=(600,100)
    empty=[]
    for ch,(cs,adv) in sorted(glyphs.items()):
        name='uni%04X'%ord(ch) if ord(ch)<0x10000 else 'u%05X'%ord(ch)
        pen=TTGlyphPen(None)
        for c in cs: draw(pen,c)
        gl[name]=pen.glyph(); order.append(name); cmap[ord(ch)]=name
        met[name]=(adv, min((x for c in cs for x,_,_ in c), default=0))
        if not cs and not ch.isspace(): empty.append(ch)
    fb=FontBuilder(1000,isTTF=True); fb.setupGlyphOrder(order); fb.setupCharacterMap(cmap)
    fb.setupGlyf(gl); fb.setupHorizontalMetrics(met); fb.setupHorizontalHeader(ascent=928,descent=-256)
    ribbi = weight in ('Regular','Bold')
    fam1 = FAMILY_EN if ribbi else f'{FAMILY_EN} {weight}'; sty1 = weight if ribbi else 'Regular'
    names=dict(familyName=fam1, styleName=sty1, uniqueFontIdentifier=f'{PS}-{weight}-{VERSION}',
        fullName=f'{FAMILY_EN} {weight}', psName=f'{PS}-{weight}', version=f'Version {VERSION}',
        copyright='Glyph outlines generated by the Goosequill Kai project. Hanzi stroke skeletons derived from Make Me a Hanzi (c) Shaunak Kishore, which is derived from Arphic PL KaitiM GB and Arphic PL UKai (c) Arphic Technology Co., Ltd. Latin skeletons: Hershey Simplex.',
        designer='The Goosequill Kai Project Authors',
        description='Hanzi rewritten with a simulated slanted broad-nib goose quill.',
        licenseDescription='This font is distributed under the Arphic Public License.',
        licenseInfoURL='http://ftp.gnu.org/non-gnu/chinese-fonts-truetype/LICENSE')
    if not ribbi: names.update(typographicFamily=FAMILY_EN, typographicSubfamily=weight)
    fb.setupNameTable(names)
    nm=fb.font['name']
    zh1 = FAMILY_ZH if ribbi else f'{FAMILY_ZH} {weight}'
    for nid,s in ((1,zh1),(2,sty1),(4,f'{FAMILY_ZH} {weight}')): nm.setName(s,nid,3,1,0x804)
    if not ribbi: nm.setName(FAMILY_ZH,16,3,1,0x804); nm.setName(weight,17,3,1,0x804)
    fb.setupOS2(sTypoAscender=880,sTypoDescender=-120,sTypoLineGap=0,usWinAscent=1032,usWinDescent=285,
        sxHeight=467,sCapHeight=700,achVendID='GQKI',fsType=0,usWeightClass=CUR['cls'],
        fsSelection=(0x20 if weight=='Bold' else 0x40), ulCodePageRange1=(1<<18)|1, ulUnicodeRange2=(1<<27))
    fb.font['head'].macStyle = 1 if weight=='Bold' else 0
    fb.setupPost()
    out=os.path.join(ROOT,'fonts','TTF',f'{PS}-{weight}.ttf'); fb.save(out)
    try:
        from fontTools.ttLib import TTFont
        f=TTFont(out); f.flavor='woff2'; f.save(os.path.join(ROOT,'fonts','WOFF2',f'{PS}-{weight}.woff2'))
    except Exception as e: print('woff2 skipped:', e)
    print(f'{weight}: {len(order)} glyphs, {os.path.getsize(out)/1e6:.1f} MB, {time.time()-t:.0f}s, empty={empty}')

if __name__=='__main__':
    a=sys.argv[1:]; only=None
    if '--only' in a: i=a.index('--only'); only=a[i+1]; a=a[:i]+a[i+2:]
    for w in (a or list(WEIGHTS)): build(w, only)
