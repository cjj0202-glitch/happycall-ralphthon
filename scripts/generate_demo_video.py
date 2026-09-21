"""Render a procedural, explicitly synthetic warehouse demo. No API or source footage.

Requires Pillow, numpy and imageio-ffmpeg. Run from any directory:
    python scripts/generate_demo_video.py
    python scripts/generate_demo_video.py --preview C:/Temp/sorter-preview.jpg
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, FPS, SECONDS = 960, 540, 24, 12
FRAMES = FPS * SECONDS
NAVY = '#101d30'
TEAL = '#62dfcd'
ORANGE = '#ffbc69'
FONT_PATH = next((p for p in [Path('C:/Windows/Fonts/malgun.ttf'),
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')] if p.exists()), None)
KOREAN = FONT_PATH is not None and FONT_PATH.name == 'malgun.ttf'


def font(size):
    return ImageFont.truetype(str(FONT_PATH), size) if FONT_PATH else ImageFont.load_default(size=size)


FONTS = {n: font(n) for n in (11, 12, 13, 14, 15, 16, 18, 23, 25)}


def p(x, y, z=0):
    return round(460 + (x-y)*35), round(140 + (x+y)*17-z*32)


def cuboid(d, x, y, z, w, depth, h, top, left, right):
    a, b, c, e = p(x,y,z+h), p(x+w,y,z+h), p(x+w,y+depth,z+h), p(x,y+depth,z+h)
    d.polygon([e,c,p(x+w,y+depth,z),p(x,y+depth,z)], fill=left)
    d.polygon([b,c,p(x+w,y+depth,z),p(x+w,y,z)], fill=right)
    d.polygon([a,b,c,e], fill=top)
    d.line([a,b,c,e,a], fill='#738994', width=1)


def text(d, pos, value, size=14, fill='#e8f0f5', **kwargs):
    d.text(pos, value, font=FONTS[size], fill=fill, **kwargs)


def badge(d, xy, value, active=False):
    x, y = xy
    box = d.textbbox((0,0), value, font=FONTS[13])
    w = box[2] + 20
    d.rounded_rectangle((x-w/2,y-12,x+w/2,y+13), radius=6,
                        fill='#163c43' if active else '#182d42', outline=TEAL if active else '#496170')
    text(d, (x,y), value, 13, TEAL if active else '#c4d4df', anchor='mm')


def base_scene():
    a = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    for y in range(HEIGHT):
        a[y,:,:] = [13+int(y/HEIGHT*5), 24+int(y/HEIGHT*8), 40+int(y/HEIGHT*9)]
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im)
    text(d,(28,20),'OneFlow  /  WMS FLOW',25)
    text(d,(29,56),'피킹부터 도크까지 · 합성 물류 이동 시연' if KOREAN else 'PICKING TO DOCK / SYNTHETIC WAREHOUSE',15,'#a3bdca')
    d.rounded_rectangle((690,22,932,53), radius=8, fill='#33402f', outline='#a99559')
    text(d,(811,37),'AI SYNTHETIC / DEMO ONLY',14, '#ffe1a6',anchor='mm')
    text(d,(930,67),'CASE-0002  /  REFERENCE ONLY',13,'#a3bdca',anchor='ra')
    # Isometric floor and warehouse grid.
    d.polygon([p(-2,-1),p(11,-1),p(11,8),p(-2,8)],fill='#213246',outline='#385269')
    for n in range(-2,12):
        d.line([p(n,-1),p(n,8)],fill='#2b4054',width=1)
    for n in range(-1,9):
        d.line([p(-2,n),p(11,n)],fill='#2b4054',width=1)
    # Storage racks: shelf beams, uprights, cartons.
    for rx in (-0.6,1.4,3.4):
        for level in (0.25,1.2,2.15):
            cuboid(d,rx,0.25,level,1.45,1,0.12,'#50677c','#30465b','#273d52')
            for j in range(2):
                cuboid(d,rx+0.1+j*0.67,0.4,level+0.12,0.52,0.65,0.56,'#bca381','#89745d','#a18b6a')
        for dx,dy in ((0,0),(1.45,0),(0,1),(1.45,1)):
            d.line([p(rx+dx,0.25+dy,0),p(rx+dx,0.25+dy,2.8)],fill='#99aabd',width=3)
    badge(d,p(1.3,0.0,3.15),'PICKING RACKS')
    cuboid(d,-0.7,1.8,0,1.2,1,0.7,'#55767f','#314c5d','#3d5c6d')
    # Conveyor structure and support legs.
    for x,y in ((0,4),(2,4),(4,4),(6,4),(7,1),(9,1),(9,4),(9,7)):
        for dy in (-0.4,0.4):
            d.line([p(x,y+dy,0),p(x,y+dy,0.55)],fill='#657c8e',width=4)
    for x,y,w,dep in ((-0.6,3.45,8.1,1.1),(6.45,0.45,1.1,7.1),(7,0.45,3.2,1.1),(7,3.45,3.2,1.1),(7,6.45,3.2,1.1)):
        cuboid(d,x,y,0.5,w,dep,0.18,'#69858e','#354e62','#405f72')
    for y,name in ((1,'D-02'),(4,'D-01'),(7,'D-03')):
        cuboid(d,10.25,y-0.75,0,0.7,1.5,0.75,'#425d6c','#233c4d','#345060')
        badge(d,p(11.15,y,0.5),name)
    # Scanner gantry.
    for y in (3.3,4.7):
        cuboid(d,2.9,y,0.5,0.18,0.18,1.9,'#9bc4ce','#416773','#577e8a')
    cuboid(d,2.9,3.3,2.35,0.2,1.58,0.18,'#9bc4ce','#416773','#577e8a')
    # Permanent case boundary and virtual time explanation.
    text(d,(28,496),'가상시간 연출 02:15–03:02 · 실제 CCTV가 아닙니다' if KOREAN else 'VIRTUAL TIME 02:15–03:02 / NOT REAL CCTV',14,'#bdcbd6')
    text(d,(28,519),'오출고 문의 참고용 · 영상으로 원인을 확정할 수 없습니다' if KOREAN else 'REFERENCE ONLY / DOES NOT ESTABLISH A MIS-SHIPMENT CAUSE',13,'#a3bdca')
    return im


BASE = base_scene()
PATH = [(0,4),(3,4),(7,4),(7,1),(10,1)]
LENGTHS = [math.dist(a,b) for a,b in zip(PATH,PATH[1:])]
TOTAL = sum(LENGTHS)


def location(progress):
    remain = progress*TOTAL
    for a,b,length in zip(PATH,PATH[1:],LENGTHS):
        if remain <= length:
            u = remain/length
            return a[0]+(b[0]-a[0])*u, a[1]+(b[1]-a[1])*u
        remain -= length
    return PATH[-1]


def tote(d,x,y,highlight=False):
    cuboid(d,x-0.34,y-0.32,0.70,0.68,0.64,0.52,
            '#ffd294' if highlight else '#9aafbc', '#b46e37' if highlight else '#506a7c',
            '#dc9549' if highlight else '#728c9d')
    cx,cy=p(x,y,1.26)
    d.line([(cx-6,cy),(cx+6,cy)], fill='#694323' if highlight else '#314b60',width=2)


def render(frame):
    im = BASE.copy()
    d = ImageDraw.Draw(im)
    progress = frame/(FRAMES-1)
    # First 1.8 seconds show the picking transfer from table to induction.
    travel=max(0,(progress-0.15)/0.85)
    x,y=location(travel)
    if progress < 0.15:
        y=2.3+1.7*(progress/0.15)
    phase = 0 if travel < 3/TOTAL else 1 if travel < 7/TOTAL else 2 if travel < 10/TOTAL else 3
    # Roller texture advances each frame in the conveyor's travel direction.
    offset=(frame/FPS*1.5)%0.36
    for n in range(22):
        xx=-0.4+n*0.36+offset
        if xx<7.3:
            d.line([p(xx,3.55,0.70),p(xx,4.45,0.70)],fill='#9cb6bd',width=2)
    for yy in (1,4,7):
        for n in range(9):
            xx=7+n*0.36+offset
            if xx<10.15:
                d.line([p(xx,yy-0.43,0.70),p(xx,yy+0.43,0.70)],fill='#9cb6bd',width=2)
    for n in range(17):
        yy=0.7+n*0.36+offset
        d.line([p(6.56,yy,0.70),p(7.43,yy,0.70)],fill='#9cb6bd',width=2)
    # Context totes and highlighted, purely illustrative route.
    for q in (0.15,0.65):
        xx=7+((progress*3+q*4)%3)
        tote(d,xx,7)
    travelled=[PATH[0]]
    length=travel*TOTAL
    for a,b,seg in zip(PATH,PATH[1:],LENGTHS):
        if length>=seg:
            travelled.append(b)
            length-=seg
        else:
            travelled.append((x,y))
            break
    if len(travelled)>1:
        d.line([p(a,b,0.73) for a,b in travelled], fill=TEAL,width=3)
    # Procedural pick arm carries the demo tote from worktable to conveyor.
    if progress < 0.15:
        base=p(-0.7,2.4,0.7)
        elbow=p(-0.7,3.0,1.9)
        grip=p(x,y,1.3)
        d.line([base,elbow,grip],fill='#84b9c7',width=7)
        for ax,ay in (base,elbow):
            d.ellipse((ax-5,ay-5,ax+5,ay+5),fill='#d7e5e9',outline='#537380')
    tote(d,x,y,True)
    cx,cy=p(x,y,1.6)
    d.line([(cx,cy+7),(cx,cy+19)],fill=ORANGE,width=1)
    badge(d,(cx,cy-7),'DEMO TOTE',True)
    # Visible pulse at scanner and sorter, with no factual inference.
    for nx,ny,node in ((0,4,'01 PICK'),(3,4,'02 SCAN'),(7,4,'03 SORT'),(10,1,'04 DOCK')):
        at=p(nx,ny,0.65)
        if math.dist((x,y),(nx,ny))<0.9:
            r=15+int(5*math.sin(frame*0.3))
            d.ellipse((at[0]-r,at[1]-r/2,at[0]+r,at[1]+r/2),outline=TEAL,width=2)
        badge(d,p(nx,ny+1.0,0),node, math.dist((x,y),(nx,ny))<1.1)
    d.rounded_rectangle((28,94,232,167),radius=9,fill=NAVY,outline='#3e576d')
    text(d,(42,104),'SIMULATED CLOCK',12,'#94b0c0')
    seconds=135+round(progress*47)
    text(d,(42,124),f'{seconds//60:02d}:{seconds%60:02d}',25,TEAL)
    text(d,(131,136),'VIRTUAL TIME',11,'#94b0c0')
    labels=['01  피킹 투입','02  스캔 통과','03  소터 분기','04  도크 이동'] if KOREAN else ['01 PICKING','02 SCANNING','03 SORTING','04 DOCK']
    for n,label in enumerate(labels):
        left=28+n*229
        d.rounded_rectangle((left,452,left+216,483),radius=7,fill='#184841' if n==phase else '#1c3145',outline=TEAL if n==phase else '#365168')
        text(d,(left+108,467),label,15,TEAL if n==phase else '#a9becb',anchor='mm')
    # Every frame gets the same explicit disclosure after all dynamic drawing.
    d.rounded_rectangle((690,22,932,53),radius=8,fill='#33402f',outline='#a99559')
    text(d,(811,37),'AI SYNTHETIC / DEMO ONLY',14,'#ffe1a6',anchor='mm')
    return im


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'apps/web/public/demo/sorter-demo.mp4')
    parser.add_argument('--preview',type=Path)
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    writer=imageio_ffmpeg.write_frames(str(args.output),(WIDTH,HEIGHT),fps=FPS,codec='libx264',
        pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=8,macro_block_size=1,
        output_params=['-preset','fast','-movflags','+faststart'],ffmpeg_log_level='error')
    writer.send(None)
    try:
        for i in range(FRAMES):
            writer.send(np.asarray(render(i)))
    finally:
        writer.close()
    # Decode the complete encoded stream, not merely the generated source frames.
    reader=imageio_ffmpeg.read_frames(str(args.output),pix_fmt='rgb24')
    metadata=next(reader)
    samples=[]
    decoded=0
    target={0,FRAMES//3,2*FRAMES//3,FRAMES-1}
    for i,data in enumerate(reader):
        decoded+=1
        if i in target:
            samples.append(Image.frombytes('RGB',(WIDTH,HEIGHT),data))
    assert decoded==FRAMES,(decoded,FRAMES)
    assert metadata['size']==(WIDTH,HEIGHT),metadata
    assert metadata['duration']>=8,metadata
    sample_hashes=[hashlib.sha256(s.tobytes()).hexdigest() for s in samples]
    assert len(set(sample_hashes))==4,'The decoded video is not changing.'
    if args.preview:
        args.preview.parent.mkdir(parents=True,exist_ok=True)
        sheet=Image.new('RGB',(WIDTH*2,HEIGHT*2))
        for i,sample in enumerate(samples):
            sheet.paste(sample,((i%2)*WIDTH,(i//2)*HEIGHT))
        sheet.save(args.preview,quality=92)
    result={'path':str(args.output.resolve()),'bytes':args.output.stat().st_size,
        'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'decoded_frames':decoded,'width':WIDTH,'height':HEIGHT,'fps':metadata['fps'],
        'duration_seconds':metadata['duration'],'codec':metadata['codec'],
        'four_distinct_decoded_samples':len(set(sample_hashes)),
        'preview':str(args.preview.resolve()) if args.preview else None}
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
