import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.platypus import Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Türkçe font kayıt
try:
    pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    FONT = 'DejaVu'
    FONT_BOLD = 'DejaVu-Bold'
except:
    FONT = 'Helvetica'
    FONT_BOLD = 'Helvetica-Bold'

# Renkler
C_BG     = colors.HexColor('#0f1117')
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

C_PURPLE_BG = colors.HexColor('#1f0f35')
C_RED_BG    = colors.HexColor('#2a1010')
C_BLUE_BG   = colors.HexColor('#0d2040')
C_GREEN_BG  = colors.HexColor('#0d2510')
C_AMBER_BG  = colors.HexColor('#251800')
C_COORD_BG  = colors.HexColor('#0d1a2e')

AGENT_COLORS = {
    'Planlama Uzmani':  (C_PURPLE, C_PURPLE_BG),
    'Planlama Uzmanı':  (C_PURPLE, C_PURPLE_BG),
    'Risk Analisti':    (C_RED,    C_RED_BG),
    'Kidemli Muhendis': (C_BLUE,   C_BLUE_BG),
    'Kıdemli Mühendis': (C_BLUE,   C_BLUE_BG),
    'Girisim Kocu':     (C_GREEN,  C_GREEN_BG),
    'Girişim Koçu':     (C_GREEN,  C_GREEN_BG),
    'Finans Uzmani':    (C_AMBER,  C_AMBER_BG),
    'Finans Uzmanı':    (C_AMBER,  C_AMBER_BG),
    'Koordinator':      (C_COORD,  C_COORD_BG),
    'Koordinatör':      (C_COORD,  C_COORD_BG),
}

def safe(text):
    """Türkçe karakterleri koru, sorunlu karakterleri temizle"""
    if not text:
        return ""
    text = str(text)
    text = text.replace('**', '').replace('##', '').replace('---', '—')
    return text

def build_styles():
    s = {}
    def ps(name, **kw):
        return ParagraphStyle(name, fontName=kw.pop('font', FONT), **kw)

    s['cover_title'] = ps('ct', font=FONT_BOLD, fontSize=26, textColor=C_WHITE, leading=32)
    s['cover_sub']   = ps('cs', fontSize=12, textColor=C_MUTED, leading=16)
    s['section']     = ps('sec', font=FONT_BOLD, fontSize=9, textColor=C_MUTED, leading=12, spaceBefore=8, spaceAfter=4, letterSpacing=1.5)
    s['agent_label'] = ps('al', font=FONT_BOLD, fontSize=8, textColor=C_WHITE, leading=11)
    s['agent_text']  = ps('at', fontSize=10, textColor=colors.HexColor('#cccccc'), leading=15, spaceAfter=6)
    s['coord_text']  = ps('cot', fontSize=10, textColor=colors.HexColor('#b0d4e8'), leading=16, spaceAfter=4)
    s['chat_you']    = ps('cy', font=FONT_BOLD, fontSize=10, textColor=C_BLUE, leading=14, spaceBefore=8, spaceAfter=2)
    s['chat_resp']   = ps('cr', fontSize=10, textColor=colors.HexColor('#cccccc'), leading=15, spaceAfter=6)
    s['rep_label']   = ps('rl', font=FONT_BOLD, fontSize=10, textColor=C_COORD, leading=14, spaceBefore=4)
    s['rep_value']   = ps('rv', fontSize=11, textColor=C_WHITE, leading=16, spaceAfter=6)
    s['footer']      = ps('ft', fontSize=8, textColor=C_MUTED, leading=10, alignment=TA_CENTER)
    return s

def parse_fields(text):
    fields = {}
    keys = ['Karar', 'Ürün', 'Platform', 'Maliyet', 'Finansman', 'Kar Süresi', 'Risk', 'İlk Adım']
    for k in keys:
        m = re.search(rf'{k}[^\w]{{0,5}}[:：]\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if m:
            fields[k] = m.group(1).strip()[:150]
    return fields

def risk_chart():
    d = Drawing(150*mm, 55*mm)
    items = [('Pazar\nRiski', 65, C_AMBER), ('Finansal\nRisk', 55, C_RED),
             ('Teknik\nRisk', 40, C_BLUE), ('Rekabet\nRiski', 70, C_RED)]
    bw, gap, xs, mh = 28*mm, 8*mm, 10*mm, 38*mm
    for i, (label, val, col) in enumerate(items):
        x = xs + i*(bw+gap)
        bh = (val/100)*mh
        d.add(Rect(x, 10*mm, bw, bh, fillColor=col, strokeColor=None))
        d.add(String(x+bw/2, 5*mm, label.replace('\n',' '), fontSize=7, fillColor=C_MUTED, textAnchor='middle'))
        d.add(String(x+bw/2, bh+12*mm, f'%{val}', fontSize=8, fillColor=C_WHITE, textAnchor='middle'))
    return d

def generate_pdf(question, agent_responses, chat_messages, coord_summary):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
        title="AI Koalisyon Analiz Raporu")

    s = build_styles()
    story = []
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # KAPAK
    story.append(Spacer(1, 15*mm))
    story.append(HRFlowable(width='100%', thickness=2, color=C_COORD, spaceAfter=6*mm))
    story.append(Paragraph("AI KOALİSYON", s['section']))
    story.append(Paragraph("Analiz Raporu", s['cover_title']))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"Oluşturulma: {now}", s['cover_sub']))
    story.append(Spacer(1, 5*mm))

    q_table = Table([[Paragraph(f"Konu: {safe(question)}", ParagraphStyle('q', fontName=FONT, fontSize=11, textColor=C_COORD, leading=16))]], colWidths=[150*mm])
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), C_COORD_BG),
        ('LEFTPADDING', (0,0),(-1,-1), 12), ('RIGHTPADDING', (0,0),(-1,-1), 12),
        ('TOPPADDING', (0,0),(-1,-1), 10), ('BOTTOMPADDING', (0,0),(-1,-1), 10),
        ('LINERIGHT', (0,0),(0,-1), 3, C_COORD),
    ]))
    story.append(q_table)
    story.append(Spacer(1, 5*mm))

    chat_count = sum(1 for t,_ in chat_messages if t == 'user')
    meta = Table([
        [Paragraph('UZMAN SAYISI', s['section']), Paragraph('SORU TURLARI', s['section']), Paragraph('DURUM', s['section'])],
        [Paragraph(str(len(agent_responses)), ParagraphStyle('n', fontName=FONT_BOLD, fontSize=22, textColor=C_WHITE, leading=26)),
         Paragraph(str(chat_count), ParagraphStyle('n2', fontName=FONT_BOLD, fontSize=22, textColor=C_WHITE, leading=26)),
         Paragraph('TAMAMLANDI', ParagraphStyle('n3', fontName=FONT_BOLD, fontSize=13, textColor=C_GREEN, leading=18))],
    ], colWidths=[50*mm, 50*mm, 50*mm])
    meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,-1), C_CARD),
        ('ALIGN', (0,0),(-1,-1), 'CENTER'), ('VALIGN', (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0),(-1,-1), 8), ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LINEBELOW', (0,0),(-1,0), 0.5, C_BORDER),
        ('LINEBETWEEN', (0,0),(-1,-1), 0.5, C_BORDER),
    ]))
    story.append(meta)

    # UZMAN GÖRÜŞLERİ
    story.append(PageBreak())
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
    story.append(Paragraph("UZMAN GÖRÜŞLERİ", s['section']))
    story.append(Spacer(1, 3*mm))

    for role, text in agent_responses:
        accent, bg = AGENT_COLORS.get(role, (C_BLUE, C_BLUE_BG))
        card = Table([[
            Paragraph(role.upper(), ParagraphStyle('rl', fontName=FONT_BOLD, fontSize=8, textColor=accent, leading=11, letterSpacing=1)),
            Paragraph(safe(text), s['agent_text'])
        ]], colWidths=[30*mm, 120*mm])
        card.setStyle(TableStyle([
            ('BACKGROUND', (0,0),(-1,-1), bg),
            ('VALIGN', (0,0),(-1,-1), 'TOP'),
            ('TOPPADDING', (0,0),(-1,-1), 10), ('BOTTOMPADDING', (0,0),(-1,-1), 10),
            ('LEFTPADDING', (0,0),(-1,-1), 10), ('RIGHTPADDING', (0,0),(-1,-1), 10),
            ('LINERIGHT', (0,0),(0,-1), 2, accent),
        ]))
        story.append(card)
        story.append(Spacer(1, 3*mm))

    # ÖZET RAPOR
    story.append(PageBreak())
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
    story.append(Paragraph("KOORDİNATÖR ÖZET RAPORU", s['section']))
    story.append(Spacer(1, 3*mm))

    fields = parse_fields(coord_summary)
    icons = {'Karar':'✓', 'Ürün':'◆', 'Platform':'▶', 'Maliyet':'₺',
             'Finansman':'◉', 'Kar Süresi':'◷', 'Risk':'⚠', 'İlk Adım':'→'}
    if fields:
        data = [[Paragraph(f"{icons.get(k,'•')}  {k}", s['rep_label']),
                 Paragraph(safe(v), s['rep_value'])] for k,v in fields.items()]
        tbl = Table(data, colWidths=[45*mm, 105*mm])
        tbl.setStyle(TableStyle([
            ('ROWBACKGROUNDS', (0,0),(-1,-1), [C_CARD, colors.HexColor('#1a2030')]),
            ('VALIGN', (0,0),(-1,-1), 'TOP'),
            ('TOPPADDING', (0,0),(-1,-1), 8), ('BOTTOMPADDING', (0,0),(-1,-1), 8),
            ('LEFTPADDING', (0,0),(-1,-1), 10), ('RIGHTPADDING', (0,0),(-1,-1), 10),
            ('LINEBELOW', (0,0),(-1,-2), 0.5, C_BORDER),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6*mm))

    story.append(Paragraph("RİSK ANALİZİ", s['section']))
    story.append(Spacer(1, 2*mm))
    story.append(risk_chart())
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("KOORDİNATÖR TAM RAPOR", s['section']))
    story.append(Spacer(1, 2*mm))
    clean = re.sub(r'\*+', '', coord_summary).strip()
    for line in clean.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2*mm))
        else:
            story.append(Paragraph(safe(line), s['coord_text']))

    # SOHBET GEÇMİŞİ
    user_msgs = [(t,c) for t,c in chat_messages if t == 'user']
    if user_msgs:
        story.append(PageBreak())
        story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
        story.append(Paragraph("SOHBET GEÇMİŞİ", s['section']))
        story.append(Spacer(1, 3*mm))
        for msg_type, content in chat_messages:
            if msg_type == 'coord_initial':
                continue
            clean_c = re.sub(r'\*+', '', content.replace('<br>', '\n')).strip()
            if msg_type == 'user':
                story.append(Paragraph("► SEN", s['chat_you']))
                story.append(Paragraph(safe(clean_c[:400]), s['chat_resp']))
            elif msg_type in ('coord', 'coord_initial') or msg_type.startswith('direct::'):
                label = "⚪ KOORDİNATÖR"
                if msg_type.startswith('direct::'):
                    name = msg_type.split('::')[1].capitalize()
                    label = f"● {name.upper()}"
                story.append(Paragraph(label, ParagraphStyle('cl', fontName=FONT_BOLD, fontSize=10, textColor=C_COORD, leading=14, spaceBefore=4, spaceAfter=2)))
                story.append(Paragraph(safe(clean_c[:600]), s['chat_resp']))
            story.append(Spacer(1, 2*mm))

    # ALT BİLGİ
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceAfter=3*mm))
    story.append(Paragraph(f"Bu rapor AI Koalisyon Danışma Sistemi tarafından {now} tarihinde otomatik oluşturulmuştur.", s['footer']))

    doc.build(story)
    buf.seek(0)
    return buf.read()
