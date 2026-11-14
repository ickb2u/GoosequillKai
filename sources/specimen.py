#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
f=lambda s,w='Regular':ImageFont.truetype(os.path.join(ROOT,'fonts','TTF',f'GoosequillKai-{w}.ttf'),s)
W,H=2000,2330; im=Image.new('RGB',(W,H),(246,241,230)); d=ImageDraw.Draw(im); ink=(28,26,24); red=(168,48,36)
d.text((90,60),'鹅管楷',font=f(330,'Bold'),fill=ink)
d.text((1130,110),'Goosequill Kai',font=f(104),fill=red)
d.text((1130,260),'以斜切鹅管笔重写的汉字',font=f(62),fill=ink)
d.text((1130,350),'Light · Regular · Bold',font=f(56),fill=ink)
d.line((90,480,W-90,480),fill=ink,width=3)
y=520
for w,t in (('Light','永和九年，岁在癸丑。'),('Regular','落霞与孤鹜齐飞，'),('Bold','秋水共长天一色。')):
    d.text((90,y),t,font=f(132,w),fill=ink); d.text((1440,y+85),w,font=f(44),fill=red); y+=188
y+=20
for t in ('人生如逆旅，我亦是行人。大江东去，浪淘尽，千古风流人物。','天地玄黄，宇宙洪荒。日月盈昃，辰宿列张。寒来暑往。','“你好！”她问：“这是《鹅管楷》吗？”——是的……','ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789','abcdefghijklmnopqrstuvwxyz Quill 2026'):
    d.text((90,y),t,font=f(66),fill=ink); y+=96
d.text((90,y),'いろはにほへと ちりぬるを アイウエオ カタカナ',font=f(66),fill=ink); y+=96
d.text((90,y),'繁體與日本漢字：龍鳳飛舞 書畫藝術 駅 図 働 峠',font=f(66),fill=ink); y+=96
y+=20
for t in ('我们在黑暗中并肩前行，各自朝着自己的光。星垂平野阔，月涌大江流。名岂文章著，官应老病休。飘飘何所似，天地一沙鸥。',
          '鹰击长空，鱼翔浅底，万类霜天竞自由。醉后不知天在水，满船清梦压星河。舞龙飞凤、藏锋露芒、繁體字：龍鳳飛舞書畫藝術。'):
    for i in range(0,len(t),44):
        d.text((90,y),t[i:i+44],font=f(40),fill=ink); y+=60
    y+=14
d.text((90,y+10),'横细竖粗，撇如发丝，捺似刀锋',font=f(120,'Bold'),fill=red)
# 竖排演示（手工套用 vert 替换）
V=dict(zip('，、。：；！？—…（）【】《》〈〉「」『』','︐︑︒︓︔︕︖︱︙︵︶︻︼︽︾︿﹀﹁﹂﹃﹄'))
cols=['「落霞与孤鹜齐飞，','秋水共长天一色。」','——《滕王阁序》']
vx=W-170
for col in cols:
    vy=530
    for ch in col:
        d.text((vx,vy),V.get(ch,ch),font=f(64),fill=ink); vy+=64
    vx-=84
im.save(os.path.join(ROOT,'documentation','specimen.png'))
