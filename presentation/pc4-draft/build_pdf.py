"""Build only a presentation PDF from fixed, existing evidence. No product execution."""
from pathlib import Path
import hashlib, json
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
W,H=1280,720
FONT=Path('C:/Windows/Fonts/malgun.ttf')
BOLD=Path('C:/Windows/Fonts/malgunbd.ttf')
pdfmetrics.registerFont(TTFont('Malgun',str(FONT)))
pdfmetrics.registerFont(TTFont('MalgunBold',str(BOLD)))
OUT=ROOT/'happycall-five-minute-draft.pdf'
c=canvas.Canvas(str(OUT),pagesize=(W,H),pageCompression=1)
c.setTitle('해피콜 OneFlow - 5분 발표 초안')
c.setAuthor('pc4 / j324rst-svg')
c.setSubject('Fixed evidence at e1ef36f; five pages; 300-second plan, not timed rehearsal')
ink='#14283F'; muted='#55677A';blue='#006BB6';warm='#A64812';white='#FFFFFF'
boxes=[]; excerpts=[]; page=0

def text(value,x,y,width,size=20,bold=False,color=ink,leading=None):
    style=ParagraphStyle('p',fontName='MalgunBold' if bold else 'Malgun',fontSize=size,leading=leading or size*1.5,textColor=HexColor(color),wordWrap='CJK')
    p=Paragraph(escape(value).replace('\n','<br/>'),style)
    actual_w,actual_h=p.wrap(width,H)
    assert x>=0 and y>=0 and x+width<=W and y+actual_h<=H-12,(page,value,y,actual_h)
    p.drawOn(c,x,H-y-actual_h)
    boxes.append({'page':page,'text':value,'bbox':[x,y,x+width,y+actual_h],'font_size':size})
    return actual_h

def begin(number,title,claim):
    global page
    page=number
    c.setFillColor(HexColor(white));c.rect(0,0,W,H,fill=1,stroke=0)
    text('HappyCall OneFlow',64,30,750,14,True,color=blue)
    text(title,64,75,1152,36,True)
    text(claim,64,133,1152,22,color=blue)

def footer(number,timing,source):
    text(source,64,645,1050,12,color=muted,leading=18)
    text(f'{number}/5  {timing}',1090,674,125,12,color=muted)
    c.showPage()

def image_excerpt(name,box,x,y,width,height):
    path=ROOT/'assets'/name
    with Image.open(path) as im: iw,ih=im.size
    bx,by,br,bb=box
    assert 0<=bx<br<=iw and 0<=by<bb<=ih
    scale=min(width/(br-bx),height/(bb-by))
    dw,dh=(br-bx)*scale,(bb-by)*scale
    c.saveState();clip=c.beginPath();clip.rect(x,H-y-dh,dw,dh);c.clipPath(clip,stroke=0)
    c.drawImage(str(path),x-bx*scale,H-y+by*scale-ih*scale,width=iw*scale,height=ih*scale,mask='auto')
    c.restoreState()
    excerpts.append({'page':page,'source':name,'source_pixels':list(box),'placed_bbox':[x,y,x+dw,y+dh],'original_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})

page=1
text('해피콜 OneFlow',64,96,1152,56,True,color=ink)
text('문의 원문부터 센터 최종 회신까지',64,193,1110,32,color=blue)
text('미도착과 오출고 문의를 한 사건의 근거와 연결합니다.',64,278,1090,26)
text('상담원이 확인할 것',64,362,480,22,True)
text('원문과 접수 내용\n물류 기록과 미확인 사실\n담당 부서와 남은 조치',64,407,485,23)
text('경영주가 확인할 것',674,362,510,22,True)
text('센터가 등록한 최종 회신\n처리 중인지, 종결됐는지',674,407,510,23)
text('독립 합성 사례의 시제품입니다. 실 운영 연동과 업무시간 절감은 미측정입니다.',64,579,1152,19,color=warm)
footer(1,'00:00-00:30','자료 기준 e1ef36f (2026-09-21). PROMPT_team.md, reports/goal-start-20260921.md. 300초는 계획이며 사람 리허설 미실행.')

begin(2,'접수와 사람 확인','통화 종료 후 정제 결과와 원문을 대조하고, 사람이 확인합니다.')
text('통화와 텍스트의 같은 검토 흐름',64,194,530,22,True)
text('통화는 종료 후 STT·정제\n텍스트는 원문 보존 후 정제\n사람이 요청·수량·단위·부서를 확인',64,235,530,20)
text('Bolt 1  수량·단위의 귀속 검사',64,358,530,22,True)
text('저장 모델 응답 32건을 재처리\n4건 변경 / 28건 유지\n자동 4필드 128/128',64,400,530,21)
text('새 라이브 평가나 음성 자연스러움 통과가 아닙니다.\n요청 과잉 철회 P2는 원문 대조가 필요합니다.',64,517,530,18,color=warm)
image_excerpt('desk-full-1440.png',(725,742,1398,1608),663,193,480,383)
text('기존 상담 화면 일부: 정제 실행 전·미저장 초안\npc1 고정 output 65c40b09 / 합성 사례',663,580,530,15,color=muted,leading=22)
footer(2,'00:30-01:35','근거 B1·B2·M4·M3: analysis-grounding-repair, request-grounding-final-independent, prototype-independent-acceptance. 상세: evidence-map.md')

begin(3,'물류 근거와 센터 최종 회신','미확인 사실을 남긴 채 같은 사건의 근거를 확인하고, 센터가 회신합니다.')
text('미도착 / 오출고',64,194,540,22,True)
text('TMS 계획과 실제 등록을 구분\nWMS 주문·출고 차이와 같은 사건 대조',64,235,540,20)
text('Bolt 2  ID에서 내용 카드로',64,322,540,22,True)
text('동일 선택 근거 2건의 내용 카드 0개에서 2개\n출처·시각·상태·합성 표시를 함께 확인',64,366,540,20)
text('사람 확인 후 이관, 센터 회신, 경영주 조회\n남은 조치가 있으면 처리 중',64,457,545,21,True)
text('기록 부재로 실제 미도착을 확정하지 않습니다.\n실 CCTV·GPS·재배송 실행이 아닙니다.',64,545,550,18,color=warm)
image_excerpt('tms-full-1024.png',(24,1350,1000,1920),668,197,545,318)
text('기존 TMS 선택 방문 화면 일부\npc1 output 65c40b09 / 합성 기록',668,527,545,16,color=muted,leading=24)
text('새 CCTV 수정본 브라우저 재검 0/1 NOT_RUN',668,584,545,18,color=warm)
footer(3,'01:35-03:10','근거 B3·M3·M6: evidence-cards-bolt, prototype-independent-acceptance, cctv-inspector-independent. 이전 빌드 결과를 최신 UI에 소급하지 않습니다.')

begin(4,'결과 중심 위임과 실패 수정','완료 기준을 맡기고, 실패 원본과 같은 조건의 재검증을 연결했습니다.')
text('실제 Goal 시작  9월 21일 17:22:02',64,196,780,24,True)
text('pc1 통합 / pc2 통화 / pc3 WMS / pc4 독립 QA\n상세 Goal 초안과 실제 실행 원문을 분리',64,244,760,20)
text('pc4  c6f734f 복구 검수',64,330,710,24,True)
text('1차 3/8   2차 7/8   최종 8/8',64,378,740,31,True,color=blue)
text('검사기 선택자 수정 / 최종 297개 관측 통과\n세 실행의 검사기 원본 33개 보존',64,446,735,21)
text('남은 P2: 이전 성공 알림과 새 저장 미확정 안내가 함께 표시됩니다. 제품 수정은 pc1 범위입니다.',64,541,735,19,color=warm)
image_excerpt('q3-uncertain-390.png',(0,255,390,1120),912,194,207,390)
text('pc4 390px 화면 일부\nc6f734f / 합성',857,604,340,14,color=muted,leading=19)
footer(4,'03:10-04:15','근거 M1·P3·P4: 실제 Goal 시작 기록, pc4 q3-c6f734f-results. 실패는 제품 결함이 아닌 검사기 오류이며 P2 화면 혼선은 별도로 남습니다.')

begin(5,'검증 범위와 남은 인계 조건','검증한 버전과 아직 충족하지 못한 조건을 함께 제시합니다.')
text('pc1 고정 빌드 65c40b09',64,198,548,24,True)
text('음성 흐름 6/6  /  텍스트 2/2\n별도 복구·화면 41/41',64,247,548,24,color=blue)
text('pc4 고정 제품 c6f734f',688,198,525,24,True)
text('복구 8/8축  /  297/297 관측\nP2 알림 혼선 1건 보고',688,247,525,24,color=blue)
text('다른 분모는 합산하지 않습니다. 실제 모델 실행·저장 결과 재생·합성 미디어를 구분합니다.',64,350,1152,20)
text('오프라인 전체 처리 0/1 BLOCKED\n원격 영속 저장 미연결 / 최종 배포 미완료',64,412,1152,27,True,color=warm)
text('한국어 자연스러움 개선 중: 사용자 부정 청취 피드백 1건(메인 전달).\nv4는 대본 후보이며 전체 합성·STT·제품 교체는 미완료입니다.\n고정 자료의 v3 부모 흐름·수정 CCTV UI는 미확인, 체계적 청취·사용성 평가는 미완료입니다.\n장애 시 기존 증거와 미확인 안내로 전환합니다. 공식 제출은 별도입니다.',64,512,1152,19,leading=28)
footer(5,'04:15-05:00','근거 M3·P3·M6~M8: 고정 문서. M9: #10 댓글 5761145013 (9/21 22:19 KST 전달). 청취 시각·MOS 점수로 확대하지 않습니다.')
c.save()
reader=PdfReader(str(OUT));assert len(reader.pages)==5
alltext='\n'.join(p.extract_text() or '' for p in reader.pages)
assert '\ufffd' not in alltext
assert OUT.stat().st_size<90*1024*1024
(ROOT/'pdf-layout.json').write_text(json.dumps({'page_count':5,'page_size_points':[W,H],'planned_seconds':[30,65,95,65,45],'total_planned_seconds':300,'rehearsal_executed':False,'text_boxes':boxes,'image_excerpts':excerpts,'font_paths':[str(FONT),str(BOLD)],'font_sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in [FONT,BOLD]],'pdf_bytes':OUT.stat().st_size,'pdf_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({'pdf':str(OUT),'pages':len(reader.pages),'bytes':OUT.stat().st_size,'text_boxes':len(boxes)},ensure_ascii=False))
