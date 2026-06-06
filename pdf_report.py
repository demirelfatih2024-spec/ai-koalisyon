import io
import re
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Font yükleme — birden fazla yol dene
FONT = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'
for regular, bold in [
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/freefont/FreeSans.ttf', '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'),
]:
    try:
        if os.path.exists(regular) and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont('TRFont', regular))
            pdfmetrics.registerFont(TTFont('TRFont-Bold', bold))
            FONT = 'TRFont'
            FONT_BOLD = 'TRFont-Bold'
            break
    except:
        continue

# Renkler
C_CARD   = colors.HexColor('#161b27')
C_BORDER = colors.HexColor('#2a3a50')
C_WHITE  = colors.HexColor('#e8e8e8')
C_MUTED  = colors.HexColor('#888888')
C_PURPLE = colors.HexColor('#9c27b0')
C_RED    = colors.HexColor('#cc4444')
C_BLUE   = colors.HexColor('#378ADD')
C_GREEN  = colors.HexColor('#4caf50')
C_AMBER  = colors.HexColor('#ffa000')
C_COORD  = colors.HexColor('#4fc3f7')

AGENT_COLORS = {
    'Planlama Uzmanı': (C_PURPLE, colors.HexColor('#1f0f35')),
    'Risk Analisti':   (C_RED,    colors.HexColor('#2a1010')),
    'Kıdemli Mühendis':(C_BLUE,   colors.HexColor('#0d2040')),
    'Girişim Koçu':    (C_GREEN,  colors.HexColor('#0d2510')),
    'Finans Uzmanı':   (C_AMBER,  colors.HexColor('#251800')),
}

def ps(name, **kw):
    return ParagraphStyle(name, fontName=kw.pop('font', FONT), **kw)

def safe(text):
    if not text: return ""
    text = str(text)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = text.replace('---', '—').strip()
    return text[:1500]

def parse_fields(text):
    fields = {}
    for k in ['Karar','Ürün','Platform','Maliyet','Finansman','Kar Süresi','Risk','İlk Adım']:
        m = re.search(rf'{k}[^\w]{{0,5}}[:：]\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if m:
            fields[k] = m.group(1).strip()[:120]
    return fields

def risk_chart():
    d = Drawing(150*mm, 55*mm)
    items = [('Pazar Riski', 65, C_AMBER), ('Finansal Risk', 55, C_RED),
             ('Teknik Risk', 40, C_BLUE), ('Rekabet Riski', 70, C_RED)]
    bw, gap, xs, mh = 26*mm, 10*mm, 12*mm, 38*mm
    for i, (label, val, col) in enumerate(items):
        x = xs + i*(bw+gap)
        bh = (val/100)*mh
        d.add(Rect(x, 10*mm, bw, bh, fillColor=col, strokeColor=None))
        d.add(String(x+bw/2, 5*mm, label, fontSize=7, fillColor=C_MUTED, textAnchor='middle'))
        d.add(String(x+bw/2, bh+12*mm, f'%{val}', fontSize=8, fillColor=C_WHITE, textAnchor='middle'))
    return d

def generate_pdf(question, agent_responses, chat_messages, coord_summary):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm)

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    story = []

    S = {
        'title':    ps('t', font=FONT_BOLD, fontSize=26, textColor=C_WHITE, leading=32),
        'sub':      ps('s', fontSize=12, textColor=C_MUTED, leading=16),
        'section':  ps('sec', font=FONT_BOLD, fontSize=9, textColor=C_MUTED, leading=12, spaceBefore=8, spaceAfter=4),
        'al':       ps('al', font=FONT_BOLD, fontSize=8, textColor=C_WHITE, leading=11),
        'at':       ps('at', fontSize=10, textColor=colors.HexColor('#cccccc'), leading=15, spaceAfter=4),
        'coord':    ps('co', fontSize=10, textColor=colors.HexColor('#b0d4e8'), leading=16, spaceAfter=4),
        'chat_you': ps('cy', font=FONT_BOLD, fontSize=10, textColor=C_BLUE, leading=14, spaceBefore=8, spaceAfter=2),
        'chat_r':   ps('cr', fontSize=10, textColor=colors.HexColor('#cccccc'), leading=15, spaceAfter=4),
        'rl':       ps('rl', font=FONT_BOLD, fontSize=10, textColor=C_COORD, leading=14, spaceBefore=4),
        'rv':       ps('rv', fontSize=11, textColor=C_WHITE, leading=16, spaceAfter=6),
        'footer':   ps('ft', fontSize=8, textColor=C_MUTED, leading=10, alignment=TA_CENTER),
    }

    # KAPAK
    story.append(Spacer(1, 15*mm))
    story.append(HRFlowable(width='100%', thickness=2, color=C_COORD, spaceAfter=6*mm))
    story.append(Paragraph("AI KOALISYON", S['section']))
    story.append(Paragraph("Analiz Raporu", S['title']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Olusturulma: {now}", S['sub']))
    story.append(Spacer(1, 5*mm))

    qt = Table([[Paragraph(f"Konu: {safe(question)}", ps('q', fontSize=11, textColor=C_COORD, leading=16))]], colWidths=[150*mm])
    qt.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#0d1a2e')),
        ('LEFTPADDING',(0,0),(-1,-1),12), ('RIGHTPADDING',(0,0),(-1,-1),12),
        ('TOPPADDING',(0,0),(-1,-1),10), ('BOTTOMPADDING',(0,0),(-1,-1),10),
        ('LINERIGHT',(0,0),(0,-1),3,C_COORD),
    ]))
    story.append(qt)
    story.append(Spacer(1, 5*mm))

    chat_count = sum(1 for t,_ in chat_messages if t == 'user')
    meta = Table([
        [Paragraph('UZMAN SAYISI', S['section']), Paragraph('SORU TURLARI', S['section']), Paragraph('DURUM', S['section'])],
        [Paragraph(str(len(agent_responses)), ps('n1', font=FONT_BOLD, fontSize=22, textColor=C_WHITE, leading=26)),
         Paragraph(str(chat_count), ps('n2', font=FONT_BOLD, fontSize=22, textColor=C_WHITE, leading=26)),
         Paragraph('TAMAMLANDI', ps('n3', font=FONT_BOLD, fontSize=13, textColor=C_GREEN, leading=18))],
    ], colWidths=[50*mm, 50*mm, 50*mm])
    meta.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),C_CARD),
        ('ALIGN',(0,0),(-1,-1),'CENTER'), ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),8), ('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('LINEBELOW',(0,0),(-1,0),0.5,C_BORDER),
        ('LINEBETWEEN',(0,0),(-1,-1),0.5,C_BORDER),
    ]))
    story.append(meta)

    # UZMAN GÖRÜSLERİ
    story.append(PageBreak())
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
    story.append(Paragraph("UZMAN GORUSLERI", S['section']))
    story.append(Spacer(1, 3*mm))

    for role, text in agent_responses:
        accent, bg = AGENT_COLORS.get(role, (C_BLUE, colors.HexColor('#0d2040')))
        card = Table([[
            Paragraph(role.upper(), ps('rl2', font=FONT_BOLD, fontSize=8, textColor=accent, leading=11)),
            Paragraph(safe(text), S['at'])
        ]], colWidths=[32*mm, 118*mm])
        card.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),bg),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),10), ('BOTTOMPADDING',(0,0),(-1,-1),10),
            ('LEFTPADDING',(0,0),(-1,-1),10), ('RIGHTPADDING',(0,0),(-1,-1),10),
            ('LINERIGHT',(0,0),(0,-1),2,accent),
        ]))
        story.append(card)
        story.append(Spacer(1, 3*mm))

    # OZET RAPOR
    story.append(PageBreak())
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
    story.append(Paragraph("KOORDINATOR OZET RAPORU", S['section']))
    story.append(Spacer(1, 3*mm))

    fields = parse_fields(coord_summary)
    icons = {'Karar':'> ','Urün':'* ','Platform':'>> ','Maliyet':'TL ','Finansman':'$ ','Kar Suresi':'T ','Risk':'! ','Ilk Adim':'-> '}
    if fields:
        data = [[Paragraph(f"{icons.get(k,'- ')}{k}", S['rl']), Paragraph(safe(v), S['rv'])] for k,v in fields.items()]
        tbl = Table(data, colWidths=[45*mm, 105*mm])
        tbl.setStyle(TableStyle([
            ('ROWBACKGROUNDS',(0,0),(-1,-1),[C_CARD, colors.HexColor('#1a2030')]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),8), ('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(-1,-1),10), ('RIGHTPADDING',(0,0),(-1,-1),10),
            ('LINEBELOW',(0,0),(-1,-2),0.5,C_BORDER),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6*mm))

    story.append(Paragraph("RISK ANALIZI", S['section']))
    story.append(Spacer(1, 2*mm))
    story.append(risk_chart())
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("KOORDINATOR TAM RAPOR", S['section']))
    story.append(Spacer(1, 2*mm))
    clean = re.sub(r'\*+', '', coord_summary).strip()
    for line in clean.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2*mm))
        else:
            story.append(Paragraph(safe(line), S['coord']))

    # SOHBET GECMİSİ
    if any(t == 'user' for t,_ in chat_messages):
        story.append(PageBreak())
        story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
        story.append(Paragraph("SOHBET GECMISI", S['section']))
        story.append(Spacer(1, 3*mm))
        for msg_type, content in chat_messages:
            if msg_type == 'coord_initial':
                continue
            clean_c = re.sub(r'\*+', '', content.replace('<br>', '\n')).strip()
            if msg_type == 'user':
                story.append(Paragraph(">> SEN", S['chat_you']))
                story.append(Paragraph(safe(clean_c[:400]), S['chat_r']))
            elif msg_type.startswith('direct::'):
                name = msg_type.split('::')[1].capitalize()
                story.append(Paragraph(f"* {name.upper()}", ps('cl', font=FONT_BOLD, fontSize=10, textColor=C_GREEN, leading=14, spaceBefore=4, spaceAfter=2)))
                story.append(Paragraph(safe(clean_c[:500]), S['chat_r']))
            else:
                story.append(Paragraph("* KOORDINATOR", ps('cl2', font=FONT_BOLD, fontSize=10, textColor=C_COORD, leading=14, spaceBefore=4, spaceAfter=2)))
                story.append(Paragraph(safe(clean_c[:500]), S['chat_r']))
            story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceAfter=3*mm))
    story.append(Paragraph(f"Bu rapor AI Koalisyon Danisma Sistemi tarafindan {now} tarihinde otomatik olusturulmustur.", S['footer']))

    doc.build(story)
    buf.seek(0)
    return buf.read()
