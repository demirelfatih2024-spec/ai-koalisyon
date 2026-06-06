import io
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.platypus import Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from reportlab.platypus import Image as RLImage


# ── Renk Paleti ────────────────────────────────────────────────
C_BG        = colors.HexColor('#0f1117')
C_CARD      = colors.HexColor('#161b27')
C_BORDER    = colors.HexColor('#2a3a50')
C_WHITE     = colors.HexColor('#e8e8e8')
C_MUTED     = colors.HexColor('#888888')
C_PURPLE    = colors.HexColor('#9c27b0')
C_RED       = colors.HexColor('#cc4444')
C_BLUE      = colors.HexColor('#378ADD')
C_GREEN     = colors.HexColor('#4caf50')
C_AMBER     = colors.HexColor('#ffa000')
C_COORD     = colors.HexColor('#4fc3f7')
C_PURPLE_BG = colors.HexColor('#1f0f35')
C_RED_BG    = colors.HexColor('#2a1010')
C_BLUE_BG   = colors.HexColor('#0d2040')
C_GREEN_BG  = colors.HexColor('#0d2510')
C_AMBER_BG  = colors.HexColor('#251800')
C_COORD_BG  = colors.HexColor('#0d1a2e')

AGENT_COLORS = {
    'Planlama Uzmanı':  (C_PURPLE, C_PURPLE_BG),
    'Risk Analisti':    (C_RED,    C_RED_BG),
    'Kıdemli Mühendis': (C_BLUE,   C_BLUE_BG),
    'Girişim Koçu':     (C_GREEN,  C_GREEN_BG),
    'Finans Uzmanı':    (C_AMBER,  C_AMBER_BG),
    'Koordinatör':      (C_COORD,  C_COORD_BG),
}

AGENT_EMOJIS = {
    'Planlama Uzmanı':  '● PLANLAMA',
    'Risk Analisti':    '● RİSK',
    'Kıdemli Mühendis': '● MÜHENDİS',
    'Girişim Koçu':     '● GİRİŞİM',
    'Finans Uzmanı':    '● FİNANS',
    'Koordinatör':      '● KOORDİNATÖR',
}


class ColoredRect(Flowable):
    def __init__(self, width, height, fill_color, radius=4):
        super().__init__()
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)


class AgentCard(Flowable):
    def __init__(self, role, text, width=150*mm):
        super().__init__()
        accent, bg = AGENT_COLORS.get(role, (C_BLUE, C_BLUE_BG))
        self.role = role
        self.text = text
        self.accent = accent
        self.bg = bg
        self.width = width
        self.height = 8*mm

    def draw(self):
        self.canv.setFillColor(self.accent)
        self.canv.rect(0, self.height - 2, self.width, 2, fill=1, stroke=0)


def build_styles():
    base = getSampleStyleSheet()
    s = {}

    s['cover_title'] = ParagraphStyle(
        'cover_title', fontName='Helvetica-Bold', fontSize=28,
        textColor=C_WHITE, leading=34, alignment=TA_LEFT
    )
    s['cover_sub'] = ParagraphStyle(
        'cover_sub', fontName='Helvetica', fontSize=13,
        textColor=C_MUTED, leading=18, alignment=TA_LEFT
    )
    s['section_title'] = ParagraphStyle(
        'section_title', fontName='Helvetica-Bold', fontSize=11,
        textColor=C_MUTED, leading=14, spaceBefore=6, spaceAfter=4,
        letterSpacing=2
    )
    s['agent_role'] = ParagraphStyle(
        'agent_role', fontName='Helvetica-Bold', fontSize=9,
        textColor=C_WHITE, leading=12, spaceBefore=0, spaceAfter=2
    )
    s['agent_text'] = ParagraphStyle(
        'agent_text', fontName='Helvetica', fontSize=10,
        textColor=colors.HexColor('#cccccc'), leading=15,
        spaceBefore=2, spaceAfter=8
    )
    s['coord_text'] = ParagraphStyle(
        'coord_text', fontName='Helvetica', fontSize=10,
        textColor=colors.HexColor('#b0d4e8'), leading=16,
        spaceBefore=2, spaceAfter=4
    )
    s['chat_user'] = ParagraphStyle(
        'chat_user', fontName='Helvetica-Bold', fontSize=10,
        textColor=C_BLUE, leading=14, spaceBefore=6, spaceAfter=2
    )
    s['chat_coord'] = ParagraphStyle(
        'chat_coord', fontName='Helvetica', fontSize=10,
        textColor=colors.HexColor('#cccccc'), leading=15,
        spaceBefore=2, spaceAfter=6
    )
    s['report_label'] = ParagraphStyle(
        'report_label', fontName='Helvetica-Bold', fontSize=10,
        textColor=C_COORD, leading=14, spaceBefore=4, spaceAfter=1
    )
    s['report_value'] = ParagraphStyle(
        'report_value', fontName='Helvetica', fontSize=11,
        textColor=C_WHITE, leading=16, spaceBefore=0, spaceAfter=6
    )
    s['footer'] = ParagraphStyle(
        'footer', fontName='Helvetica', fontSize=8,
        textColor=C_MUTED, leading=10, alignment=TA_CENTER
    )
    return s


def parse_report_fields(coord_text):
    """Koordinatör raporundan anahtar alanları çıkar"""
    fields = {}
    patterns = {
        'Karar': r'(?:Karar|KARAR)\s*[:：]\s*(.+?)(?:\n|$)',
        'Ürün/Niş': r'(?:Ürün[/\/]Niş|Ürün|ÜRÜN)\s*[:：]\s*(.+?)(?:\n|$)',
        'Platform': r'(?:Platform|PLATFORM)\s*[:：]\s*(.+?)(?:\n|$)',
        'Başlangıç Maliyeti': r'(?:Başlangıç Maliyeti|Maliyet|MALİYET)\s*[:：]\s*(.+?)(?:\n|$)',
        'Finansman': r'(?:Finansman|FİNANSMAN)\s*[:：]\s*(.+?)(?:\n|$)',
        'Kar Süresi': r'(?:Kar Süresi|KAR SÜRESİ)\s*[:：]\s*(.+?)(?:\n|$)',
        'Ana Risk': r'(?:Ana Risk|RİSK)\s*[:：]\s*(.+?)(?:\n|$)',
        'İlk Adım': r'(?:İlk Adım|İLK ADIM)\s*[:：]\s*(.+?)(?:\n|$)',
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, coord_text, re.IGNORECASE)
        if m:
            fields[key] = m.group(1).strip()
    return fields


def create_summary_table(fields, styles):
    """Özet rapor tablosu"""
    if not fields:
        return None

    icons = {
        'Karar': '✓',
        'Ürün/Niş': '◆',
        'Platform': '▶',
        'Başlangıç Maliyeti': '₺',
        'Finansman': '◉',
        'Kar Süresi': '◷',
        'Ana Risk': '⚠',
        'İlk Adım': '→',
    }

    data = []
    for key, val in fields.items():
        icon = icons.get(key, '•')
        data.append([
            Paragraph(f"{icon}  {key}", styles['report_label']),
            Paragraph(val[:120], styles['report_value'])
        ])

    table = Table(data, colWidths=[45*mm, 105*mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_CARD),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [C_CARD, colors.HexColor('#1a2030')]),
        ('TEXTCOLOR', (0, 0), (-1, -1), C_WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, C_BORDER),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    return table


def create_risk_chart(fields):
    """Basit risk/fırsat görseli"""
    drawing = Drawing(150*mm, 50*mm)

    categories = ['Pazar\nRiski', 'Finansal\nRisk', 'Teknik\nRisk', 'Rekabet\nRiski']
    values = [65, 55, 40, 70]

    bar_w = 25*mm
    gap = 10*mm
    x_start = 15*mm
    max_h = 35*mm

    for i, (cat, val) in enumerate(zip(categories, values)):
        x = x_start + i * (bar_w + gap)
        bar_h = (val / 100) * max_h
        color = C_RED if val > 60 else C_AMBER if val > 40 else C_GREEN
        r = Rect(x, 8*mm, bar_w, bar_h, fillColor=color, strokeColor=None)
        drawing.add(r)
        label = String(x + bar_w/2, 4*mm, cat.replace('\n', ' '),
                      fontSize=7, fillColor=C_MUTED, textAnchor='middle')
        drawing.add(label)
        pct = String(x + bar_w/2, bar_h + 10*mm, f'%{val}',
                    fontSize=8, fillColor=C_WHITE, textAnchor='middle')
        drawing.add(pct)

    return drawing


def generate_pdf(question, agent_responses, chat_messages, coord_summary):
    """
    Ana PDF oluşturma fonksiyonu
    agent_responses: [(role, text), ...]
    chat_messages: [(type, content), ...] — type: 'user' veya 'coord'
    coord_summary: son koordinatör özet metni
    """
    buffer = io.BytesIO()
    W, H = A4

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title="AI Koalisyon Analiz Raporu",
    )

    styles = build_styles()
    story = []
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # ── KAPAK ──────────────────────────────────────────────────
    story.append(Spacer(1, 20*mm))

    # Üst çizgi
    story.append(HRFlowable(width='100%', thickness=2, color=C_COORD, spaceAfter=8*mm))

    story.append(Paragraph("AI KOALİSYON", styles['section_title']))
    story.append(Paragraph("Analiz Raporu", styles['cover_title']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"Oluşturulma: {now}", styles['cover_sub']))
    story.append(Spacer(1, 6*mm))

    # Soru kutusu
    q_data = [[Paragraph(f"Konu: {question}", ParagraphStyle(
        'q', fontName='Helvetica', fontSize=11,
        textColor=C_COORD, leading=16
    ))]]
    q_table = Table(q_data, colWidths=[150*mm])
    q_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_COORD_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINERIGHT', (0, 0), (0, -1), 3, C_COORD),
    ]))
    story.append(q_table)
    story.append(Spacer(1, 6*mm))

    # Ajan özeti
    agent_count = len(agent_responses)
    chat_count = sum(1 for t, _ in chat_messages if t == 'user')
    meta_data = [
        [Paragraph('UZMAN SAYISI', styles['section_title']),
         Paragraph('SORU TURLAR', styles['section_title']),
         Paragraph('DURUM', styles['section_title'])],
        [Paragraph(str(agent_count), ParagraphStyle('n', fontName='Helvetica-Bold', fontSize=22, textColor=C_WHITE, leading=26)),
         Paragraph(str(chat_count), ParagraphStyle('n', fontName='Helvetica-Bold', fontSize=22, textColor=C_WHITE, leading=26)),
         Paragraph('TAMAMLANDI', ParagraphStyle('n', fontName='Helvetica-Bold', fontSize=14, textColor=C_GREEN, leading=18))],
    ]
    meta_table = Table(meta_data, colWidths=[50*mm, 50*mm, 50*mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_CARD),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, C_BORDER),
        ('LINEBETWEEN', (0, 0), (-1, -1), 0.5, C_BORDER),
    ]))
    story.append(meta_table)

    # ── SAYFA 2: UZMAN GÖRÜŞLERİ ──────────────────────────────
    story.append(PageBreak())
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
    story.append(Paragraph("UZMAN GÖRÜŞLERİ", styles['section_title']))
    story.append(Spacer(1, 3*mm))

    for role, text in agent_responses:
        accent, bg = AGENT_COLORS.get(role, (C_BLUE, C_BLUE_BG))
        label = AGENT_EMOJIS.get(role, role.upper())

        card_data = [[
            Paragraph(label, ParagraphStyle(
                'rl', fontName='Helvetica-Bold', fontSize=8,
                textColor=accent, leading=11, letterSpacing=1
            )),
            Paragraph(text, styles['agent_text'])
        ]]
        card = Table(card_data, colWidths=[28*mm, 122*mm])
        card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('LINERIGHT', (0, 0), (0, -1), 2, accent),
        ]))
        story.append(card)
        story.append(Spacer(1, 3*mm))

    # ── SAYFA 3: ÖZET RAPOR ───────────────────────────────────
    story.append(PageBreak())
    story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
    story.append(Paragraph("KOORDİNATÖR ÖZET RAPORU", styles['section_title']))
    story.append(Spacer(1, 3*mm))

    fields = parse_report_fields(coord_summary)
    if fields:
        summary_table = create_summary_table(fields, styles)
        if summary_table:
            story.append(summary_table)
            story.append(Spacer(1, 6*mm))

    # Risk grafiği
    story.append(Paragraph("RİSK ANALİZİ GÖRSELİ", styles['section_title']))
    story.append(Spacer(1, 2*mm))
    risk_chart = create_risk_chart(fields)
    story.append(risk_chart)
    story.append(Spacer(1, 4*mm))

    # Koordinatör tam metin
    story.append(Paragraph("TAM KOORDİNATÖR RAPORU", styles['section_title']))
    story.append(Spacer(1, 2*mm))
    clean_text = coord_summary.replace('<br>', '\n').replace('✅', '').strip()
    for line in clean_text.split('\n'):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 2*mm))
            continue
        if line.startswith('-') or line.startswith('•'):
            story.append(Paragraph(line, ParagraphStyle(
                'bullet', fontName='Helvetica', fontSize=10,
                textColor=colors.HexColor('#cccccc'), leading=15,
                leftIndent=10, spaceBefore=1
            )))
        else:
            story.append(Paragraph(line, styles['coord_text']))

    # ── SAYFA 4: SOHBET GEÇMİŞİ ──────────────────────────────
    if any(t == 'user' for t, _ in chat_messages):
        story.append(PageBreak())
        story.append(HRFlowable(width='100%', thickness=1, color=C_BORDER, spaceAfter=4*mm))
        story.append(Paragraph("SOHBET GEÇMİŞİ", styles['section_title']))
        story.append(Spacer(1, 3*mm))

        for msg_type, content in chat_messages:
            if msg_type == 'coord_initial':
                continue
            clean = content.replace('<br>', '\n').strip()
            if msg_type == 'user':
                story.append(Paragraph("► SEN", styles['chat_user']))
                story.append(Paragraph(clean[:500], styles['chat_coord']))
            elif msg_type == 'coord':
                story.append(Paragraph("⚪ KOORDİNATÖR", ParagraphStyle(
                    'ch', fontName='Helvetica-Bold', fontSize=10,
                    textColor=C_COORD, leading=14, spaceBefore=4, spaceAfter=2
                )))
                story.append(Paragraph(clean[:800], styles['chat_coord']))
            story.append(Spacer(1, 2*mm))

    # ── ALT BİLGİ ─────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER, spaceAfter=3*mm))
    story.append(Paragraph(
        f"Bu rapor AI Koalisyon Danışma Sistemi tarafından {now} tarihinde otomatik oluşturulmuştur.",
        styles['footer']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
