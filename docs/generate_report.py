"""Generate a professional PDF report for BTC Oracle ML System Analysis."""

import os
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether, HRFlowable, Image
    )
    from reportlab.platypus.flowables import Flowable
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("Installing reportlab...")
    os.system(f"{sys.executable} -m pip install reportlab")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, KeepTogether, HRFlowable
    )
    from reportlab.platypus.flowables import Flowable

from datetime import datetime


# ── Color Palette ──
DARK_BG = HexColor("#0F1419")
CARD_BG = HexColor("#1A2332")
ACCENT_BLUE = HexColor("#3B82F6")
ACCENT_GREEN = HexColor("#22C55E")
ACCENT_RED = HexColor("#EF4444")
ACCENT_ORANGE = HexColor("#F97316")
ACCENT_PURPLE = HexColor("#A855F7")
ACCENT_TEAL = HexColor("#14B8A6")
ACCENT_YELLOW = HexColor("#EAB308")
TEXT_PRIMARY = HexColor("#F1F5F9")
TEXT_MUTED = HexColor("#94A3B8")
BORDER_COLOR = HexColor("#334155")
WHITE = HexColor("#FFFFFF")
NEAR_BLACK = HexColor("#0A0F14")
HEADER_BG = HexColor("#1E293B")
ROW_ALT = HexColor("#1E2A3A")
ROW_NORMAL = HexColor("#141E2B")


class ColoredRect(Flowable):
    """A colored rectangle flowable for section headers."""
    def __init__(self, width, height, color):
        super().__init__()
        self.width = width
        self.height = height
        self.color = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)


class GradientHeader(Flowable):
    """A gradient header bar."""
    def __init__(self, width, height, color_start, color_end):
        super().__init__()
        self.width = width
        self.height = height
        self.color_start = color_start
        self.color_end = color_end

    def draw(self):
        c = self.canv
        steps = 50
        for i in range(steps):
            r = self.color_start.red + (self.color_end.red - self.color_start.red) * i / steps
            g = self.color_start.green + (self.color_end.green - self.color_start.green) * i / steps
            b = self.color_start.blue + (self.color_end.blue - self.color_start.blue) * i / steps
            c.setFillColorRGB(r, g, b)
            x = self.width * i / steps
            w = self.width / steps + 1
            c.rect(x, 0, w, self.height, fill=1, stroke=0)


def page_background(canvas, doc):
    """Draw dark background on every page."""
    canvas.saveState()
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

    # Footer
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(2 * cm, 1.2 * cm, "BTC Oracle  |  ML System Technical Report  |  Confidential")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")

    # Top accent line
    canvas.setStrokeColor(ACCENT_BLUE)
    canvas.setLineWidth(2)
    canvas.line(2 * cm, A4[1] - 1.5 * cm, A4[0] - 2 * cm, A4[1] - 1.5 * cm)
    canvas.restoreState()


def first_page_bg(canvas, doc):
    """Cover page background."""
    canvas.saveState()
    # Full dark background
    canvas.setFillColor(NEAR_BLACK)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

    # Gradient accent at top
    w = A4[0]
    h = 8 * cm
    y_start = A4[1] - h
    steps = 80
    for i in range(steps):
        frac = i / steps
        alpha = 0.3 * (1 - frac)
        canvas.setFillColorRGB(0.23, 0.51, 0.96, alpha)
        canvas.rect(0, y_start + h * frac, w, h / steps + 1, fill=1, stroke=0)

    # Bottom accent line
    canvas.setStrokeColor(ACCENT_BLUE)
    canvas.setLineWidth(3)
    canvas.line(3 * cm, 4 * cm, A4[0] - 3 * cm, 4 * cm)

    canvas.restoreState()


def build_styles():
    """Create custom paragraph styles."""
    styles = {}

    styles["cover_title"] = ParagraphStyle(
        "cover_title", fontName="Helvetica-Bold", fontSize=32,
        textColor=WHITE, alignment=TA_LEFT, leading=38,
        spaceAfter=8,
    )
    styles["cover_subtitle"] = ParagraphStyle(
        "cover_subtitle", fontName="Helvetica", fontSize=14,
        textColor=TEXT_MUTED, alignment=TA_LEFT, leading=20,
        spaceAfter=4,
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", fontName="Helvetica", fontSize=10,
        textColor=TEXT_MUTED, alignment=TA_LEFT, leading=14,
    )
    styles["section_title"] = ParagraphStyle(
        "section_title", fontName="Helvetica-Bold", fontSize=18,
        textColor=ACCENT_BLUE, alignment=TA_LEFT, leading=24,
        spaceBefore=20, spaceAfter=10,
    )
    styles["subsection"] = ParagraphStyle(
        "subsection", fontName="Helvetica-Bold", fontSize=13,
        textColor=WHITE, alignment=TA_LEFT, leading=18,
        spaceBefore=14, spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "body", fontName="Helvetica", fontSize=9.5,
        textColor=TEXT_PRIMARY, alignment=TA_JUSTIFY, leading=14,
        spaceAfter=6,
    )
    styles["body_muted"] = ParagraphStyle(
        "body_muted", fontName="Helvetica", fontSize=9,
        textColor=TEXT_MUTED, alignment=TA_LEFT, leading=13,
        spaceAfter=4,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", fontName="Helvetica", fontSize=9.5,
        textColor=TEXT_PRIMARY, alignment=TA_LEFT, leading=14,
        leftIndent=16, bulletIndent=6, spaceAfter=3,
        bulletFontName="Helvetica", bulletFontSize=9,
    )
    styles["code"] = ParagraphStyle(
        "code", fontName="Courier", fontSize=8,
        textColor=ACCENT_GREEN, alignment=TA_LEFT, leading=11,
        leftIndent=12, spaceAfter=4, backColor=HexColor("#0D1117"),
    )
    styles["highlight"] = ParagraphStyle(
        "highlight", fontName="Helvetica-Bold", fontSize=10,
        textColor=ACCENT_ORANGE, alignment=TA_LEFT, leading=14,
        spaceBefore=4, spaceAfter=4,
    )
    styles["kpi_value"] = ParagraphStyle(
        "kpi_value", fontName="Helvetica-Bold", fontSize=22,
        textColor=WHITE, alignment=TA_CENTER, leading=28,
    )
    styles["kpi_label"] = ParagraphStyle(
        "kpi_label", fontName="Helvetica", fontSize=8,
        textColor=TEXT_MUTED, alignment=TA_CENTER, leading=11,
    )
    styles["table_header"] = ParagraphStyle(
        "table_header", fontName="Helvetica-Bold", fontSize=8,
        textColor=WHITE, alignment=TA_LEFT, leading=11,
    )
    styles["table_cell"] = ParagraphStyle(
        "table_cell", fontName="Helvetica", fontSize=8,
        textColor=TEXT_PRIMARY, alignment=TA_LEFT, leading=11,
    )
    styles["table_cell_sm"] = ParagraphStyle(
        "table_cell_sm", fontName="Helvetica", fontSize=7.5,
        textColor=TEXT_PRIMARY, alignment=TA_LEFT, leading=10,
    )
    styles["toc_entry"] = ParagraphStyle(
        "toc_entry", fontName="Helvetica", fontSize=11,
        textColor=TEXT_PRIMARY, alignment=TA_LEFT, leading=20,
        leftIndent=20,
    )
    styles["toc_title"] = ParagraphStyle(
        "toc_title", fontName="Helvetica-Bold", fontSize=18,
        textColor=ACCENT_BLUE, alignment=TA_LEFT, leading=24,
        spaceBefore=20, spaceAfter=16,
    )

    return styles


def make_table(headers, rows, col_widths=None, style_override=None):
    """Create a styled table."""
    s = build_styles()
    header_row = [Paragraph(h, s["table_header"]) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([Paragraph(str(cell), s["table_cell"]) for cell in row])

    if col_widths is None:
        col_widths = [None] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)

    base_style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]

    # Alternating row colors
    for i in range(1, len(data)):
        bg = ROW_ALT if i % 2 == 0 else ROW_NORMAL
        base_style.append(("BACKGROUND", (0, i), (-1, i), bg))

    if style_override:
        base_style.extend(style_override)

    t.setStyle(TableStyle(base_style))
    return t


def make_kpi_row(items, total_width):
    """Create a KPI card row."""
    s = build_styles()
    n = len(items)
    w = total_width / n

    cells = []
    for value, label, color in items:
        cell_content = [
            Paragraph(f'<font color="{color}">{value}</font>', s["kpi_value"]),
            Paragraph(label, s["kpi_label"]),
        ]
        cells.append(cell_content)

    data = [cells]
    t = Table(data, colWidths=[w] * n)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 1, HexColor("#1E293B")),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


def section_divider():
    return HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=10, spaceBefore=10)


def build_document():
    """Build the full PDF report."""
    output_path = os.path.join(os.path.dirname(__file__), "BTC_Oracle_ML_System_Report.pdf")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=2.2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    s = build_styles()
    story = []
    W = doc.width  # usable width

    # ════════════════════════════════════════════════════
    # COVER PAGE
    # ════════════════════════════════════════════════════
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("BTC Oracle", s["cover_title"]))
    story.append(Paragraph("ML System &amp; Infrastructure", s["cover_title"]))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("Technical Analysis Report", s["cover_subtitle"]))
    story.append(Paragraph("Training Pipeline  |  Data Sources  |  Cost Analysis  |  Architecture Deep-Dive", s["cover_subtitle"]))
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph(f"Prepared: {datetime.now().strftime('%B %d, %Y')}", s["cover_meta"]))
    story.append(Paragraph("Classification: Internal / Confidential", s["cover_meta"]))
    story.append(Paragraph("Version: 1.0", s["cover_meta"]))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ════════════════════════════════════════════════════
    story.append(Paragraph("Table of Contents", s["toc_title"]))
    toc_items = [
        "1.  Executive Summary",
        "2.  System Architecture Overview",
        "3.  ML Models &amp; Ensemble",
        "4.  Feature Engineering (222 Features)",
        "5.  Data Sources &amp; Collectors",
        "6.  Training Pipeline",
        "7.  Continuous Learning &amp; A/B Testing",
        "8.  Quantitative Prediction Engine",
        "9.  Infrastructure &amp; Deployment",
        "10. Cost Analysis &amp; Projections",
        "11. Storage &amp; Growth Forecast",
        "12. Recommendations for Custom AI",
    ]
    for item in toc_items:
        story.append(Paragraph(item, s["toc_entry"]))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 1. EXECUTIVE SUMMARY
    # ════════════════════════════════════════════════════
    story.append(Paragraph("1. Executive Summary", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "BTC Oracle is a production-grade Bitcoin price prediction system that combines "
        "four machine learning models in a weighted ensemble, augmented by a 15-signal "
        "quantitative engine. The system ingests data from 20+ collectors across 10+ free APIs, "
        "processes 222 engineered features per hour, and generates predictions across five time "
        "horizons (1h, 4h, 24h, 1w, 1mo).",
        s["body"]
    ))
    story.append(Paragraph(
        "The platform includes continuous self-learning (every 6 hours), A/B model testing, "
        "pattern discovery, and adaptive ensemble weight adjustment. It is deployable via Docker "
        "on minimal hardware and can operate entirely on free APIs at near-zero cost, or be "
        "enhanced with premium data sources for improved accuracy.",
        s["body"]
    ))
    story.append(Spacer(1, 0.6 * cm))

    # KPI cards
    story.append(make_kpi_row([
        ("4", "ML MODELS", "#3B82F6"),
        ("222", "FEATURES", "#22C55E"),
        ("20+", "COLLECTORS", "#A855F7"),
        ("5", "TIMEFRAMES", "#F97316"),
    ], W))
    story.append(Spacer(1, 0.4 * cm))
    story.append(make_kpi_row([
        ("$10-50", "MONTHLY COST\n(Free APIs)", "#22C55E"),
        ("~500 MB", "YEARLY STORAGE", "#3B82F6"),
        ("2-3s", "INFERENCE TIME", "#14B8A6"),
        ("6h", "LEARNING CYCLE", "#EAB308"),
    ], W))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 2. SYSTEM ARCHITECTURE
    # ════════════════════════════════════════════════════
    story.append(Paragraph("2. System Architecture Overview", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "The system follows a modular pipeline architecture with clear separation between "
        "data collection, feature engineering, model inference, and evaluation.",
        s["body"]
    ))

    story.append(Paragraph("Data Pipeline Flow", s["subsection"]))
    pipeline_steps = [
        "Raw Data Sources (Binance, blockchain.info, RSS feeds, FRED, CoinGecko, etc.)",
        "20 Async Collectors (aiohttp-based, scheduled via APScheduler)",
        "Feature Engineering (222 features computed per hourly snapshot)",
        "ML Ensemble (TFT + LSTM + XGBoost + TimesFM, weighted voting)",
        "Quant Engine (15+ theory-based signals, composite scoring)",
        "Predictions &amp; Signals (stored in DB, served via FastAPI REST API)",
        "Evaluation &amp; Learning (accuracy tracking, pattern discovery, weight adaptation)",
    ]
    for i, step in enumerate(pipeline_steps, 1):
        story.append(Paragraph(f"<b>{i}.</b>  {step}", s["bullet"]))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Technology Stack", s["subsection"]))

    story.append(make_table(
        ["Component", "Technology", "Version"],
        [
            ["Backend Framework", "FastAPI (async Python)", "0.115.6"],
            ["Database ORM", "SQLAlchemy (async)", "2.0.36"],
            ["Database", "SQLite (dev) / PostgreSQL (prod)", "3.x / 16+"],
            ["ML Framework", "PyTorch + PyTorch Lightning", "2.x"],
            ["Tree Ensemble", "XGBoost", "2.1.3"],
            ["Foundation Model", "Google TimesFM 2.0", "200M params"],
            ["Technical Analysis", "ta library + custom", "0.11.0"],
            ["Scheduling", "APScheduler", "3.10.4"],
            ["Frontend", "React + Vite + Tailwind CSS", "18.x"],
            ["Deployment", "Docker Compose", "Multi-service"],
        ],
        col_widths=[5 * cm, 7 * cm, 3 * cm],
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 3. ML MODELS
    # ════════════════════════════════════════════════════
    story.append(Paragraph("3. ML Models &amp; Ensemble", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "The core prediction engine uses a weighted ensemble of four diverse model architectures. "
        "Each model processes the same 222-feature input but through different mechanisms, providing "
        "robust predictions through model diversity.",
        s["body"]
    ))

    # Model details table
    story.append(make_table(
        ["Model", "Architecture", "Input Shape", "Parameters", "Training Time"],
        [
            ["TFT", "Temporal Fusion Transformer\n4 attention heads, 64 hidden dim,\n3 LSTM layers, multi-horizon output", "(168, 222)\n7-day sequence", "~500K-1M", "5-30 min\n(GPU preferred)"],
            ["LSTM", "Bidirectional LSTM\n3 layers, 128 hidden,\n0.2 dropout, multi-head output", "(168, 222)\n7-day sequence", "~300K-500K", "5-20 min"],
            ["XGBoost", "Gradient Boosted Trees\nmax_depth=6-8, 100-200 estimators,\nbinary:sigmoid objective", "(1, 222)\ncurrent snapshot", "N/A (trees)", "1-5 min\n(CPU only)"],
            ["TimesFM", "Google Foundation Model\npre-trained 200M params,\nzero-shot forecasting", "Price history\n(variable length)", "200M\n(frozen)", "No training\n(inference only)"],
        ],
        col_widths=[2.2 * cm, 5 * cm, 2.8 * cm, 2.5 * cm, 2.5 * cm],
    ))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Ensemble Voting Mechanism", s["subsection"]))
    story.append(Paragraph(
        "Predictions from all four models are combined using adaptive weights that update every 6 hours "
        "based on recent accuracy. The weight formula is: <b>weight = accuracy^2</b> (normalized to sum to 1.0), "
        "which exponentially rewards better-performing models. When a model's accuracy drops below 50%, "
        "it triggers selective retraining on the last 72 hours of data.",
        s["body"]
    ))

    story.append(Paragraph("Prediction Outputs (Per Timeframe)", s["subsection"]))
    story.append(make_table(
        ["Timeframe", "Schedule (UTC)", "Output Fields"],
        [
            ["1 hour", "Every hour at :00", "Direction (bullish/bearish), confidence, predicted price, predicted change %"],
            ["4 hours", "00:00, 04:00, 08:00, 12:00, 16:00, 20:00", "Same fields, medium-term outlook"],
            ["24 hours", "Daily at 00:04", "Same fields, daily trend prediction"],
            ["1 week", "Via quant engine", "Composite score, target price range"],
            ["1 month", "Via quant engine", "Long-term directional bias, cycle position"],
        ],
        col_widths=[2.5 * cm, 5.5 * cm, 7 * cm],
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 4. FEATURE ENGINEERING
    # ════════════════════════════════════════════════════
    story.append(Paragraph("4. Feature Engineering (222 Features)", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "Every hour, the system computes 222 features from raw market data. Features are organized "
        "into 15 categories spanning technical analysis, sentiment, macro economics, on-chain metrics, "
        "derivatives, and more. All features are z-score normalized using saved training parameters.",
        s["body"]
    ))

    story.append(make_table(
        ["Category", "Count", "Key Examples"],
        [
            ["Technical Indicators", "111", "EMA(9,21,50,200), RSI, MACD, Bollinger Bands, ATR, Ichimoku, Stoch RSI, ADX, GARCH, Hurst, Wavelets"],
            ["Sentiment", "13", "News sentiment (1h/4h/24h), Reddit, Fear &amp; Greed, social bullish/bearish %"],
            ["Derivatives Extended", "12", "Long/short ratio, DVOL, liquidations (long/short), estimated leverage, taker buy/sell"],
            ["Whale Activity", "12", "TX count (1h/24h), exchange in/out, net flow, severity, directional signal"],
            ["Power Law &amp; Long-Term", "11", "Deviation from fair value, 200d SMA ratio, 52w high/low, halving cycle position"],
            ["Exchange Flows", "9", "Reserve BTC, netflow, NVT, MVRV Z-score, SOPR, Puell, supply in profit, LTH supply"],
            ["Macro Economics", "8", "DXY change, Gold change, S&amp;P500 change, Treasury 10Y yield, M2 supply"],
            ["On-Chain", "7", "Hash rate, mempool size/fees, TX volume, active addresses, difficulty"],
            ["Event Memory", "7", "Expected impact (1h/4h/24h), confidence, severity, active event count"],
            ["ETF Flows", "6", "Net flow USD, total holdings BTC, IBIT/FBTC/GBTC individual flows"],
            ["Stablecoin Supply", "5", "USDT/USDC market cap, total supply, 7d change %, DeFi TVL"],
            ["Market Dominance", "4", "BTC dominance, ETH dominance, total market cap, 24h change"],
            ["Derivatives Basic", "3", "Funding rate, open interest, mark-index spread"],
            ["Phrase Correlation", "3", "Top bullish/bearish phrase scores, net signal"],
            ["Supply / Mining", "4", "% mined, daily issuance, blocks until halving, halving cycle %"],
        ],
        col_widths=[3.5 * cm, 1.5 * cm, 10 * cm],
    ))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Sequence Construction for Neural Models", s["subsection"]))
    story.append(Paragraph(
        "LSTM and TFT models require sequential input. The system builds sliding windows of "
        "<b>168 hourly snapshots (7 days)</b>, each containing all 222 features. This produces "
        "input tensors of shape <font color='#22C55E'>(batch, 168, 222)</font>. Sequences shorter than 168 are "
        "left-padded with zeros. XGBoost uses only the current snapshot (1, 222).",
        s["body"]
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 5. DATA SOURCES
    # ════════════════════════════════════════════════════
    story.append(Paragraph("5. Data Sources &amp; Collectors", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "The system uses 20 asynchronous collectors to gather data from diverse sources. "
        "All primary data sources are free, with optional premium sources for enhanced accuracy.",
        s["body"]
    ))

    story.append(make_table(
        ["Collector", "Source(s)", "Interval", "Cost", "Key Data"],
        [
            ["Market", "Binance REST API", "60s", "Free", "OHLCV, funding rate, OI, premium index"],
            ["On-Chain", "blockchain.com, mempool.space", "1 hour", "Free", "Hash rate, mempool, TX volume, addresses"],
            ["News", "35+ RSS feeds", "2 min", "Free", "Headlines from CoinDesk, Cointelegraph, etc."],
            ["Fear &amp; Greed", "alternative.me", "1 hour", "Free", "Daily F&amp;G index (0-100)"],
            ["Macro", "FRED, CoinGecko", "1 hour", "Free", "DXY, Gold, S&amp;P500, Treasury yields, M2"],
            ["Reddit", "PRAW API", "1 hour", "Free", "Post titles, upvotes, sentiment"],
            ["Influencers", "Social media feeds", "10 min", "Free", "Posts from known BTC influencers"],
            ["ETF Flows", "CoinGlass, SoSoValue", "1 hour", "Free", "IBIT/FBTC/GBTC flows, total holdings"],
            ["Derivatives", "Binance Futures, Deribit", "1 hour", "Free", "Liquidations, leverage, DVOL"],
            ["Stablecoin", "CoinGecko, DeFi Llama", "1 hour", "Free", "USDT/USDC supply, DeFi TVL"],
            ["Whale", "mempool.space, BTCScan", "10 min", "Free", "Large TX tracking (&gt;100 BTC)"],
            ["Exchange Flows", "Glassnode, blockchain.com", "1 hour", "Optional", "NVT, MVRV, SOPR, reserves"],
            ["Coins", "CoinGecko", "2 min", "Free", "Altcoin prices, market cap, dominance"],
            ["Historical", "Binance, yfinance", "On demand", "Free", "Full OHLCV history since 2009"],
        ],
        col_widths=[2.5 * cm, 3.5 * cm, 1.8 * cm, 1.8 * cm, 5.4 * cm],
    ))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Free APIs Currently Used (No Keys Required)", s["subsection"]))
    free_apis = [
        "Binance REST API (public market data, unlimited)",
        "CoinGecko API (10-50 calls/min, sufficient for hourly updates)",
        "blockchain.info (free stats and on-chain data)",
        "mempool.space (free mempool and block data)",
        "alternative.me (Fear &amp; Greed Index, free)",
        "FRED (Federal Reserve data, requires free API key)",
        "DeFi Llama (TVL data, free)",
        "CoinGlass (ETF and liquidation data, public endpoints)",
        "Deribit (DVOL index, public endpoints)",
        "35+ RSS feeds (crypto news sources, unlimited)",
    ]
    for api_item in free_apis:
        story.append(Paragraph(f"\u2022  {api_item}", s["bullet"]))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 6. TRAINING PIPELINE
    # ════════════════════════════════════════════════════
    story.append(Paragraph("6. Training Pipeline", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph("How Training Works (Step by Step)", s["subsection"]))

    steps = [
        ("<b>Step 1: Dataset Construction</b> \u2014 Pull all Feature snapshots (hourly) and corresponding "
         "Price records from the database. Build sliding window sequences of 168 hours (7 days)."),
        ("<b>Step 2: Label Generation</b> \u2014 For each sample at timestamp T, compute the actual price "
         "at T+1h, T+4h, T+24h, T+1w, T+1mo. Generate binary direction labels (bullish/bearish) "
         "and magnitude percentages for each horizon."),
        ("<b>Step 3: Data Split</b> \u2014 80% training, 20% validation (chronological split to prevent "
         "data leakage from future information)."),
        ("<b>Step 4: Model Training</b> \u2014 TFT and LSTM train on sequences (168, 222) with multi-task "
         "loss across all 5 timeframes. XGBoost trains on current features (1, 222) with binary "
         "classification. TimesFM requires no training (pre-trained foundation model)."),
        ("<b>Step 5: Validation &amp; Storage</b> \u2014 Evaluate on holdout set, save weights to persistent "
         "volume (/data/weights/), record metrics in ModelVersion table."),
        ("<b>Step 6: A/B Testing</b> \u2014 New model registered as candidate. Must outperform production "
         "model by 3% over 24+ hours and 50+ predictions to be promoted."),
    ]
    for step in steps:
        story.append(Paragraph(step, s["body"]))
        story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Training Resource Requirements", s["subsection"]))
    story.append(make_table(
        ["Component", "GPU Memory", "CPU Time", "Frequency", "Notes"],
        [
            ["TFT Training", "4-6 GB", "5-30 min", "24-48h", "GPU preferred but CPU works"],
            ["LSTM Training", "2-4 GB", "5-20 min", "24h", "Bidirectional, 3 layers"],
            ["XGBoost Training", "&lt;1 GB", "1-5 min", "24h", "CPU only, very fast"],
            ["TimesFM Inference", "4 GB", "5-10s (GPU)\n20-30s (CPU)", "Per prediction", "Pre-trained, no training needed"],
            ["Feature Extraction", "&lt;1 GB", "0.5-2s", "Every hour", "222 features from raw data"],
            ["Continuous Learning", "&lt;1 GB", "1-5 min", "Every 6h", "Weight adaptation + selective retrain"],
        ],
        col_widths=[3 * cm, 2.2 * cm, 2.5 * cm, 2.3 * cm, 5 * cm],
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 7. CONTINUOUS LEARNING
    # ════════════════════════════════════════════════════
    story.append(Paragraph("7. Continuous Learning &amp; A/B Testing", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "The system implements three layers of self-improvement that run automatically:",
        s["body"]
    ))

    story.append(Paragraph("7.1 Adaptive Ensemble Weights (Every 6 Hours)", s["subsection"]))
    story.append(Paragraph(
        "Computes rolling accuracy for each model over the last 48 hours. Weights are set to "
        "<b>accuracy<super>2</super></b> (squared to exponentially reward top performers) and "
        "normalized to sum to 1.0. Minimum 20 predictions per model required.",
        s["body"]
    ))

    story.append(Paragraph("7.2 Selective Retraining", s["subsection"]))
    story.append(Paragraph(
        "If any model's accuracy drops below 50%, only that model is retrained on the last 72 hours of data. "
        "The new weights are validated against a holdout set. If improved, they are hot-swapped; if not, "
        "the current weights are retained. This prevents catastrophic degradation while allowing recovery.",
        s["body"]
    ))

    story.append(Paragraph("7.3 Pattern Discovery (Every 6 Hours)", s["subsection"]))
    story.append(Paragraph("Five pattern types are automatically discovered and applied:", s["body"]))
    story.append(make_table(
        ["Pattern Type", "What It Detects", "How It's Applied"],
        [
            ["Volatility Regime", "Accuracy varies by volatility level", "Confidence modifier when high/low volatility detected"],
            ["Confidence Calibration", "Stated confidence vs actual accuracy", "Recalibrate confidence output to match reality"],
            ["Model Disagreement", "Accuracy drops when models disagree", "Reduce confidence when agreement is low"],
            ["Feature Thresholds", "Specific feature combos predict well", "Boost/reduce confidence when pattern active"],
            ["Time Patterns", "Accuracy varies by time of day", "Adjust predictions during known weak/strong periods"],
        ],
        col_widths=[3 * cm, 5 * cm, 7 * cm],
    ))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("7.4 A/B Testing Protocol", s["subsection"]))
    story.append(make_table(
        ["Parameter", "Value"],
        [
            ["Minimum test duration", "24 hours"],
            ["Minimum predictions", "50"],
            ["Promotion threshold", "3% accuracy improvement over production"],
            ["Maximum test duration", "72 hours (auto-reject if no improvement)"],
            ["Rollback", "Automatic if candidate underperforms"],
        ],
        col_widths=[5 * cm, 10 * cm],
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 8. QUANT ENGINE
    # ════════════════════════════════════════════════════
    story.append(Paragraph("8. Quantitative Prediction Engine", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "In addition to ML models, a separate quantitative engine generates predictions using "
        "15+ theory-based signals from established Bitcoin valuation frameworks. This provides "
        "an independent second opinion that is not dependent on training data.",
        s["body"]
    ))

    story.append(make_table(
        ["Signal", "Weight", "Description"],
        [
            ["Pi Cycle Top Indicator", "8%", "111DMA vs 350DMA\u00d72 crossing (historical top detector)"],
            ["Mayer Multiple", "8%", "Price / 200DMA ratio (&lt;0.6 = buy, &gt;2.4 = sell)"],
            ["Halving Cycle Position", "8%", "Position within 4-year halving cycle (0-1460 days)"],
            ["Mean Reversion Z-Score", "8%", "Statistical reversion at \u00b12.5 standard deviations"],
            ["Momentum (20d vs 100d)", "8%", "Short vs long-term return comparison"],
            ["Rainbow Chart Bands", "7%", "9 valuation bands from fire sale to max bubble"],
            ["DXY Inverse Correlation", "7%", "USD strength inverse relationship (-0.72 correlation)"],
            ["Fear &amp; Greed Contrarian", "7%", "Buy at extreme fear, sell at extreme greed"],
            ["Funding Rate Extremes", "7%", "Extreme rates precede 70%+ of corrections"],
            ["Regime Detection", "7%", "Volatility ratio + SMA50 market regime"],
            ["NVT Ratio", "5%", "Network value vs transaction value (&lt;30 = undervalued)"],
            ["Puell Multiple", "5%", "Miner revenue vs 365d average"],
            ["Volume Profile (POC)", "5%", "Point of Control, Value Area analysis"],
            ["Round Number S/R", "5%", "Psychological support/resistance levels"],
            ["ATH Proximity", "5%", "Distance from all-time high (momentum gauge)"],
        ],
        col_widths=[4 * cm, 1.5 * cm, 9.5 * cm],
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "The composite score ranges from <b>-100</b> (extremely bearish) to <b>+100</b> (extremely bullish). "
        "Action thresholds: &gt;60 = STRONG_BUY, &gt;30 = BUY, \u00b110 = NEUTRAL, &lt;-30 = SELL, &lt;-60 = STRONG_SELL.",
        s["body"]
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 9. INFRASTRUCTURE
    # ════════════════════════════════════════════════════
    story.append(Paragraph("9. Infrastructure &amp; Deployment", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph("Current Deployment Architecture", s["subsection"]))
    story.append(make_table(
        ["Component", "Specification", "Details"],
        [
            ["Runtime", "Docker Compose", "2 services: backend + webapp"],
            ["Backend Image", "Python 3.12-slim", "FastAPI, PyTorch, XGBoost, SQLAlchemy"],
            ["Frontend", "React + Vite", "Tailwind CSS, i18n (EN/RU/ZH)"],
            ["Database (Dev)", "SQLite + aiosqlite", "Single file, zero config"],
            ["Database (Prod)", "PostgreSQL + asyncpg", "Connection pooling, async sessions"],
            ["Model Storage", "/data/weights/", "Persistent Docker volume"],
            ["Backup System", "6-hour intervals", "7-day retention, SQLite snapshots"],
            ["Scheduling", "APScheduler", "40+ jobs, cron + interval triggers"],
            ["Bot Integration", "Telegram (aiogram)", "Polling mode, webhook support"],
        ],
        col_widths=[3.5 * cm, 4 * cm, 7.5 * cm],
    ))

    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Minimum Server Requirements", s["subsection"]))
    story.append(make_table(
        ["Tier", "CPU", "RAM", "Storage", "GPU", "Monthly Cost", "Best For"],
        [
            ["Minimal", "1 vCPU", "1 GB", "5 GB", "None", "$5-10", "Development, testing"],
            ["Standard", "2 vCPU", "4 GB", "20 GB", "None", "$20-40", "Production (CPU inference)"],
            ["Enhanced", "4 vCPU", "8 GB", "50 GB", "T4 (16GB)", "$50-150", "Fast training + TimesFM"],
            ["Premium", "8 vCPU", "16 GB", "100 GB", "A10G (24GB)", "$150-400", "Full suite + custom models"],
        ],
        col_widths=[2 * cm, 1.8 * cm, 1.5 * cm, 1.5 * cm, 2.5 * cm, 2.5 * cm, 3.2 * cm],
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "<b>Note:</b> The system currently runs on the Standard tier without GPU. TFT and LSTM "
        "training takes 5-30 minutes on CPU. Adding a GPU reduces training to 1-5 minutes and "
        "enables fast TimesFM inference (5-10s vs 20-30s on CPU).",
        s["body"]
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 10. COST ANALYSIS
    # ════════════════════════════════════════════════════
    story.append(Paragraph("10. Cost Analysis &amp; Projections", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph("Current Monthly Operating Costs", s["subsection"]))
    story.append(make_table(
        ["Category", "Item", "Monthly Cost", "Notes"],
        [
            ["Hosting", "Railway / Render / AWS", "$10-50", "1-2 vCPU, 2-4 GB RAM"],
            ["Database", "PostgreSQL (managed)", "$10-25", "Optional upgrade from SQLite"],
            ["API: Binance", "Market data", "$0", "Free, no key required"],
            ["API: CoinGecko", "Prices, market cap", "$0", "Free tier sufficient"],
            ["API: blockchain.info", "On-chain data", "$0", "Free"],
            ["API: mempool.space", "Mempool, blocks", "$0", "Free, open-source"],
            ["API: FRED", "Macro economics", "$0", "Free API key"],
            ["API: CoinGlass", "ETF flows, liquidations", "$0", "Public endpoints"],
            ["API: RSS Feeds", "35+ news sources", "$0", "Standard RSS"],
            ["API: alternative.me", "Fear &amp; Greed", "$0", "Free"],
        ],
        col_widths=[2.5 * cm, 4 * cm, 2.5 * cm, 6 * cm],
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "<font color='#22C55E'><b>Total (Free APIs only): $10 - $50/month</b></font>",
        s["highlight"]
    ))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Optional Premium Additions", s["subsection"]))
    story.append(make_table(
        ["Service", "What It Adds", "Monthly Cost", "Impact on Accuracy"],
        [
            ["Glassnode Professional", "SOPR, MVRV Z-score, NVT signal,\nexchange reserves, entity flows", "$500-1,000", "High: critical on-chain metrics\nnot available elsewhere"],
            ["Nansen Basic", "Address identification, smart money\ntracking, entity labels", "$0-99", "Medium: improved whale\nclassification"],
            ["GPU Instance (T4)", "Faster training (5x), TimesFM\ninference, future model expansion", "$40-100", "Medium: enables TimesFM\nand faster iterations"],
            ["Dedicated PostgreSQL", "Better concurrency, ACID compliance,\nscalability beyond 1 GB", "$25-50", "Low: reliability improvement,\nnot accuracy"],
        ],
        col_widths=[3 * cm, 4.5 * cm, 2.5 * cm, 5 * cm],
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "<font color='#F97316'><b>Total (with Glassnode + GPU): $550 - $1,200/month</b></font>",
        s["highlight"]
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 11. STORAGE & GROWTH
    # ════════════════════════════════════════════════════
    story.append(Paragraph("11. Storage &amp; Growth Forecast", s["section_title"]))
    story.append(section_divider())

    story.append(make_table(
        ["Component", "Current Size", "Annual Growth", "3-Year Projection"],
        [
            ["Price Data (hourly OHLCV)", "~50 MB", "~9 MB/year", "~77 MB"],
            ["Feature Snapshots (222 features, JSON)", "~300 MB", "~500 MB/year", "~1.8 GB"],
            ["Predictions (all timeframes)", "~20 MB", "~2 MB/year", "~26 MB"],
            ["News &amp; Sentiment", "~30 MB", "~50 MB/year", "~180 MB"],
            ["Whale Transactions", "~10 MB", "~20 MB/year", "~70 MB"],
            ["Model Weights", "~100 MB", "~50 MB/year", "~250 MB"],
            ["Backups (7-day rolling)", "~3.5 GB", "Constant", "~3.5 GB"],
            ["Logs", "~50 MB", "~100 MB/year", "~350 MB"],
        ],
        col_widths=[4.5 * cm, 2.5 * cm, 3 * cm, 3 * cm],
    ))

    story.append(Spacer(1, 0.4 * cm))
    story.append(make_kpi_row([
        ("~500 MB", "YEAR 1\nDATABASE", "#22C55E"),
        ("~1.5 GB", "YEAR 2\nDATABASE", "#3B82F6"),
        ("~2.5 GB", "YEAR 3\nDATABASE", "#A855F7"),
        ("~6 GB", "TOTAL\n(WITH BACKUPS)", "#F97316"),
    ], W))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Storage growth is very manageable. Even at 3 years of operation, the total footprint "
        "(including rolling backups) stays under 10 GB. A 20 GB disk allocation is sufficient "
        "for 5+ years of continuous operation.",
        s["body"]
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════════
    # 12. RECOMMENDATIONS
    # ════════════════════════════════════════════════════
    story.append(Paragraph("12. Recommendations for Custom AI", s["section_title"]))
    story.append(section_divider())

    story.append(Paragraph(
        "If the goal is to build a fully custom AI model that you own and can license, "
        "here is a realistic roadmap with cost estimates:",
        s["body"]
    ))

    story.append(Paragraph("Phase 1: Data Foundation (Month 1-2)", s["subsection"]))
    story.append(Paragraph(
        "Continue running the current system to accumulate high-quality training data. "
        "The more historical predictions with outcomes you have, the better a custom model "
        "will perform. Target: 3-6 months of hourly data with evaluation results.",
        s["body"]
    ))

    story.append(Paragraph("Phase 2: Custom Model Development (Month 3-6)", s["subsection"]))
    story.append(make_table(
        ["Investment", "Cost", "What You Get"],
        [
            ["ML Engineer (contract)", "$5,000-15,000", "Custom transformer architecture trained on your data"],
            ["GPU Compute (training)", "$200-500", "Cloud GPU hours (A100/H100) for training runs"],
            ["Glassnode API", "$3,000-6,000", "6 months of premium on-chain data for training"],
            ["Data labeling / validation", "$500-1,000", "Manual verification of training labels"],
        ],
        col_widths=[4 * cm, 3 * cm, 8 * cm],
    ))

    story.append(Paragraph("Phase 3: Production Custom Model (Month 6+)", s["subsection"]))
    story.append(make_table(
        ["Scenario", "Setup Cost", "Monthly Cost", "What You Own"],
        [
            ["DIY (current system + improvements)", "$0", "$50-100", "Everything: code, weights, data pipeline"],
            ["Custom transformer model", "$5,000-15,000", "$100-300", "Proprietary model + training pipeline"],
            ["Full custom AI platform", "$20,000-50,000", "$300-1,000", "End-to-end system, licensable IP"],
        ],
        col_widths=[4 * cm, 2.5 * cm, 2.5 * cm, 6 * cm],
    ))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Key Advantages of the Current System", s["subsection"]))
    advantages = [
        "<b>You already own everything.</b> All code, models, and data pipelines are yours. No vendor lock-in.",
        "<b>Near-zero operating cost.</b> The system runs on $10-50/month using only free APIs.",
        "<b>Self-improving.</b> Continuous learning, A/B testing, and pattern discovery run automatically.",
        "<b>Production-ready.</b> Docker deployment, Telegram bot, multi-language frontend, admin dashboard.",
        "<b>Extensible.</b> Adding new data sources or models is straightforward (follow existing patterns).",
    ]
    for adv in advantages:
        story.append(Paragraph(f"\u2713  {adv}", s["body"]))

    story.append(Spacer(1, 0.6 * cm))
    story.append(Paragraph(
        "<font color='#3B82F6'><b>Bottom Line:</b></font> The current BTC Oracle system is a fully functional, "
        "self-learning ML platform that you own outright. It costs $10-50/month to operate. "
        "Building a custom AI on top of this foundation (rather than from scratch) is the most "
        "cost-effective path. Budget $5K-15K for a custom model if you want to go beyond the "
        "current 4-model ensemble, or continue improving the existing system for free.",
        s["body"]
    ))

    # ════════════════════════════════════════════════════
    # BUILD PDF
    # ════════════════════════════════════════════════════
    doc.build(story, onFirstPage=first_page_bg, onLaterPages=page_background)
    print(f"PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    build_document()
