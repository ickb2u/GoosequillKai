#!/usr/bin/env python3
"""构建 鹅管楷 Goosequill Kai。用法: python3 sources/build.py [Light|Regular|Bold ...] [--only 字符]"""
import json, math, os, sys, time
from multiprocessing import Pool
from shapely.geometry.polygon import orient
import quill

HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
DATADIR=os.environ.get('GQK_DATA', os.path.join(HERE,'data'))
# 骨架数据，按优先级排列：同一个字只取最先出现的那份
DATAFILES=['graphics.txt','graphicsZhHans.txt','graphicsZhHant.txt','graphicsJa.txt','graphicsKo.txt','graphicsJaKana.txt']
VERSION='1.200'
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

def is_kana(ch): return 0x3040<=ord(ch)<=0x30ff
def clean_kana(medians):
    """AnimCJK 的假名骨架为动画做过处理：自相交的笔画被复制成多段、起笔前多一个引导点。这里还原成一笔一线。"""
    out=[]
    for m in medians:
        m=[tuple(p) for p in m]
        if any(len(o)>=3 and len(m)>=3 and o[-3:]==m[-3:] for o in out): continue
        if len(m)>=3:
            (x0,y0),(x1,y1),(x2,y2)=m[:3]; l=math.hypot(x1-x0,y1-y0)
            a=(x1-x0,y1-y0); c=(x2-x1,y2-y1); lc=math.hypot(*c)
            turn=math.degrees(math.acos(max(-1,min(1,(a[0]*c[0]+a[1]*c[1])/(l*lc+1e-9)))))
            if l<120 and turn>25: m=m[1:]
        out.append(m)
    return out

def do_hanzi(item):
    ch, medians = item; kana=is_kana(ch)
    if kana: medians=clean_kana(medians)
    meds=[quill.mmh_to_font(m) for m in medians if len(m)>1]
    ws = 1.04 if kana else wscale_for(len(meds))
    return ch, to_contours(quill.glyph_poly(meds, quill.P, ws, kana)), 1000

def load_skeletons(only=None):
    seen={}
    for fn in DATAFILES:
        p=os.path.join(DATADIR,fn)
        if not os.path.exists(p): print('missing data file:',fn); continue
        for l in open(p,encoding='utf8'):
            if not l.strip(): continue
            j=json.loads(l); ch=j['character']
            if len(ch)==1 and ch not in seen and (not only or ch in only): seen[ch]=j['medians']
    return list(seen.items())

# ---------- 西文：Hershey Simplex 单线骨架，同一支笔 ----------
def latin():
    from HersheyFonts import HersheyFonts
    hf=HersheyFonts(); hf.load_default_font('futural'); K=700/21; res=[]
    LP=dict(quill.P, CORNER=75, CHAIKIN=2, W=quill.P['W']*1.12, T=quill.P['T']*0.86)
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
def seg(*p): return list(p)
SYMBOLS = {   # 字符: (骨架, 字宽)
 '×':([seg((110,560),(490,180)),seg((490,560),(110,180))],600),
 '÷':([seg((90,370),(510,370)),dot(300,560),dot(300,180)],600),
 '±':([seg((90,430),(510,430)),seg((300,630),(300,230)),seg((90,110),(510,110))],600),
 '°':([arc(200,600,90,90,100,460,16)],400),
 '¥':([seg((90,700),(300,400)),seg((510,700),(300,400)),seg((300,400),(300,0)),seg((110,330),(490,330)),seg((110,190),(490,190))],600),
 '•':([arc(300,350,45,45,100,460,12)],600),
 '→':([seg((90,340),(900,340)),seg((680,540),(910,340),(680,140))],1000),
 '←':([seg((910,340),(100,340)),seg((320,540),(90,340),(320,140))],1000),
 '↑':([seg((500,-60),(500,750)),seg((300,530),(500,760),(700,530))],1000),
 '↓':([seg((500,750),(500,-60)),seg((300,170),(500,-70),(700,170))],1000),
 '〇':([arc(500,380,330,380,100,460,28)],1000),
}
CX, CY = 500, 380   # 字框中心
def rot(st):  return [[(CX+(y-CY), CY-(x-CX)) for x,y in s] for s in st]      # 顺时针 90°
def shift(st,dx,dy): return [[(x+dx,y+dy) for x,y in s] for s in st]
# 竖排形式：横排字符 -> (竖排码位或 None, 变换)
VERT = {
 '，':('\ufe10', lambda s: shift(s,560,560)), '、':('\ufe11', lambda s: shift(s,560,560)),
 '。':('\ufe12', lambda s: shift(s,560,560)), '：':('\ufe13', lambda s: shift(s,300,150)),
 '；':('\ufe14', lambda s: shift(s,300,150)), '！':('\ufe15', lambda s: shift(s,300,0)),
 '？':('\ufe16', lambda s: shift(s,250,0)),
 '—':('\ufe31', rot), '…':('\ufe19', rot), '～':(None, rot),
 '（':('\ufe35', rot), '）':('\ufe36', rot), '【':('\ufe3b', rot), '】':('\ufe3c', rot),
 '《':('\ufe3d', rot), '》':('\ufe3e', rot), '〈':('\ufe3f', rot), '〉':('\ufe40', rot),
 '「':('\ufe41', rot), '」':('\ufe42', rot), '『':('\ufe43', rot), '』':('\ufe44', rot),
}
def punct():
    PP=dict(quill.P, CORNER=75)
    mk=lambda st: to_contours(quill.glyph_poly(st, PP, 1.12, True)) if st else []
    res=[(ch, mk(st), 1000) for ch,st in PUNCT.items()]
    res+=[(ch, mk(st), adv) for ch,(st,adv) in SYMBOLS.items()]
    vert=[(ch, code, mk(f(PUNCT[ch]))) for ch,(code,f) in VERT.items()]
    return res, vert

def build(weight, only=None):
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    setw(weight); t=time.time()
    items=load_skeletons(only)
    with Pool(initializer=setw, initargs=(weight,)) as pool: han=pool.map(do_hanzi, items, chunksize=40)
    pun, vert = punct()
    glyphs={ch:(c,adv) for ch,c,adv in han+pun}
    vsub={}   # 横排字符 -> 竖排字形名
    kana_bar='ー'
    if any(ch==kana_bar for ch,_ in items):
        med=dict(items)[kana_bar]
        vert.append((kana_bar, None, to_contours(quill.glyph_poly(rot([quill.mmh_to_font(m) for m in clean_kana(med)]), quill.P, 0.94, True))))
    for ch,c,adv in latin():
        glyphs[ch]=(c,adv); fw=chr(ord(ch)+0xFEE0)
        if fw not in glyphs:
            dx=(1000-adv)//2; glyphs[fw]=([[(x+dx,y,o) for x,y,o in k] for k in c],1000)
    glyphs[' ']=([],300); glyphs[chr(0xa0)]=([],300)
    uname=lambda ch: 'uni%04X'%ord(ch) if ord(ch)<0x10000 else 'u%05X'%ord(ch)
    extra={}   # 无码位的竖排字形
    for ch,code,c in vert:
        if code: glyphs[code]=(c,1000); vsub[uname(ch)]=uname(code)
        else: extra[uname(ch)+'.vert']=(c,1000); vsub[uname(ch)]=uname(ch)+'.vert'
    order=['.notdef']; cmap={}; gl={}; met={}
    pen=TTGlyphPen(None)
    for c in ([(100,0),(100,700),(500,700),(500,0)],[(160,60),(440,60),(440,640),(160,640)]):
        pen.moveTo(c[0]); [pen.lineTo(q) for q in c[1:]]; pen.closePath()
    gl['.notdef']=pen.glyph(); met['.notdef']=(600,100)
    empty=[]
    for ch,(cs,adv) in sorted(glyphs.items()):
        name=uname(ch)
        pen=TTGlyphPen(None)
        for c in cs: draw(pen,c)
        gl[name]=pen.glyph(); order.append(name); cmap[ord(ch)]=name
        met[name]=(adv, min((x for c in cs for x,_,_ in c), default=0))
        if not cs and not ch.isspace(): empty.append(ch)
    for name,(cs,adv) in extra.items():
        pen=TTGlyphPen(None)
        for c in cs: draw(pen,c)
        gl[name]=pen.glyph(); order.append(name); met[name]=(adv, min((x for c in cs for x,_,_ in c), default=0))
    fb=FontBuilder(1000,isTTF=True); fb.setupGlyphOrder(order); fb.setupCharacterMap(cmap)
    fb.setupGlyf(gl); fb.setupHorizontalMetrics(met); fb.setupHorizontalHeader(ascent=928,descent=-256)
    ribbi = weight in ('Regular','Bold')
    fam1 = FAMILY_EN if ribbi else f'{FAMILY_EN} {weight}'; sty1 = weight if ribbi else 'Regular'
    names=dict(familyName=fam1, styleName=sty1, uniqueFontIdentifier=f'{PS}-{weight}-{VERSION}',
        fullName=f'{FAMILY_EN} {weight}', psName=f'{PS}-{weight}', version=f'Version {VERSION}',
        copyright='Glyph outlines generated by the Goosequill Kai project. Hanzi and kana stroke skeletons derived from Make Me a Hanzi (c) Shaunak Kishore and AnimCJK (c) FM-SH, which are derived from Arphic PL KaitiM GB, Arphic PL KaitiM Big5 and Arphic PL UKai (c) Arphic Technology Co., Ltd. Latin skeletons: Hershey Simplex.',
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
        fsSelection=(0x20 if weight=='Bold' else 0x40), ulCodePageRange1=(1<<18)|(1<<17)|1, ulUnicodeRange2=(1<<27)|(1<<17)|(1<<18))
    fb.font['head'].macStyle = 1 if weight=='Bold' else 0
    fb.setupPost()
    # 竖排：vhea / vmtx + vert 特性
    glyf=fb.font['glyf']; vm={}
    for n in order:
        g=glyf[n]; ymax=getattr(g,'yMax',None)
        vm[n]=(1000, 880-(ymax if ymax is not None and g.numberOfContours else 880))
    fb.setupVerticalHeader(ascent=500, descent=-500); fb.setupVerticalMetrics(vm)
    from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
    subs=''.join(f'  sub {a} by {b};\n' for a,b in sorted(vsub.items()) if a in gl and b in gl)
    fea='languagesystem DFLT dflt;\nlanguagesystem hani dflt;\nlanguagesystem kana dflt;\nlanguagesystem latn dflt;\n'+f'feature vert {{\n{subs}}} vert;\nfeature vrt2 {{\n{subs}}} vrt2;\n'
    addOpenTypeFeaturesFromString(fb.font, fea)
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
