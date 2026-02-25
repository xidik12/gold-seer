"""Griffin Gold — Gold Sentiment Gauge chart."""
import io
import math
from PIL import Image, ImageDraw
from app.charts.branding import (
    create_base_image, add_watermark, get_font,
    BG_RGB, TEXT_RGB, GREEN_RGB, RED_RGB, YELLOW_RGB, GOLD_RGB, GRAY_RGB, BORDER_RGB,
)


def generate_gold_sentiment_card(
    sentiment_score: float,  # -100 to 100
    factors: dict | None = None,
    size: str = "telegram",
) -> bytes:
    """Generate a gold sentiment gauge image.

    Args:
        sentiment_score: -100 (extreme bearish) to +100 (extreme bullish)
        factors: Optional dict of factor_name -> score for breakdown display
        size: Image size preset
    """
    img, draw, w, h = create_base_image(size)

    title_font = get_font(26, bold=True)
    big_font = get_font(40, bold=True)
    medium_font = get_font(18)
    small_font = get_font(14)
    tiny_font = get_font(12)

    # Title
    draw.text((w // 2, 25), "GOLD SENTIMENT", fill=GOLD_RGB, font=title_font, anchor="mt")

    # Semicircular gauge
    cx, cy = w // 2, 220
    radius = 130
    gauge_width = 20

    # Draw gauge arc background (semicircle from left to right)
    for angle_deg in range(180, 361):
        angle_rad = math.radians(angle_deg)
        # Color gradient: red (180) -> yellow (270) -> green (360)
        t = (angle_deg - 180) / 180.0  # 0 to 1
        if t < 0.5:
            # Red to Yellow
            r = int(RED_RGB[0] + (YELLOW_RGB[0] - RED_RGB[0]) * (t * 2))
            g = int(RED_RGB[1] + (YELLOW_RGB[1] - RED_RGB[1]) * (t * 2))
            b = int(RED_RGB[2] + (YELLOW_RGB[2] - RED_RGB[2]) * (t * 2))
        else:
            # Yellow to Green
            r = int(YELLOW_RGB[0] + (GREEN_RGB[0] - YELLOW_RGB[0]) * ((t - 0.5) * 2))
            g = int(YELLOW_RGB[1] + (GREEN_RGB[1] - YELLOW_RGB[1]) * ((t - 0.5) * 2))
            b = int(YELLOW_RGB[2] + (GREEN_RGB[2] - YELLOW_RGB[2]) * ((t - 0.5) * 2))

        for rr in range(radius - gauge_width, radius):
            x = cx + int(rr * math.cos(angle_rad))
            y = cy + int(rr * math.sin(angle_rad))
            if 0 <= x < w and 0 <= y < h:
                draw.point((x, y), fill=(r, g, b))

    # Needle indicator
    # Map score (-100..100) to angle (180..360)
    clamped = max(-100, min(100, sentiment_score))
    needle_angle = 180 + ((clamped + 100) / 200.0) * 180
    needle_rad = math.radians(needle_angle)
    needle_len = radius - 30
    nx = cx + int(needle_len * math.cos(needle_rad))
    ny = cy + int(needle_len * math.sin(needle_rad))
    draw.line([(cx, cy), (nx, ny)], fill=TEXT_RGB, width=3)
    # Center dot
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=GOLD_RGB)

    # Score in center
    score_color = GREEN_RGB if sentiment_score > 20 else RED_RGB if sentiment_score < -20 else YELLOW_RGB
    draw.text((cx, cy + 25), f"{sentiment_score:+.0f}", fill=score_color, font=big_font, anchor="mt")

    # Labels
    label = (
        "EXTREME BEARISH" if sentiment_score <= -60
        else "BEARISH" if sentiment_score <= -20
        else "NEUTRAL" if sentiment_score <= 20
        else "BULLISH" if sentiment_score <= 60
        else "EXTREME BULLISH"
    )
    draw.text((cx, cy + 70), label, fill=score_color, font=medium_font, anchor="mt")

    # Gauge labels
    draw.text((cx - radius + 10, cy + 10), "BEAR", fill=RED_RGB, font=tiny_font, anchor="mt")
    draw.text((cx + radius - 10, cy + 10), "BULL", fill=GREEN_RGB, font=tiny_font, anchor="mt")

    # Factor breakdown if provided
    if factors:
        y_start = cy + 105
        draw.line([(50, y_start - 10), (w - 50, y_start - 10)], fill=BORDER_RGB, width=1)
        draw.text((w // 2, y_start), "FACTOR BREAKDOWN", fill=GRAY_RGB, font=small_font, anchor="mt")

        y_pos = y_start + 22
        bar_width = int(w * 0.4)
        bar_x = (w - bar_width) // 2

        for name, score in list(factors.items())[:5]:
            # Factor name
            draw.text((bar_x - 5, y_pos), name[:20], fill=TEXT_RGB, font=tiny_font, anchor="rt")
            # Bar background
            draw.rounded_rectangle(
                [bar_x, y_pos - 4, bar_x + bar_width, y_pos + 10],
                radius=4, fill=GRAY_RGB,
            )
            # Bar fill
            fill_pct = (score + 100) / 200.0
            fill_w = max(2, int(bar_width * fill_pct))
            f_color = GREEN_RGB if score > 10 else RED_RGB if score < -10 else YELLOW_RGB
            draw.rounded_rectangle(
                [bar_x, y_pos - 4, bar_x + fill_w, y_pos + 10],
                radius=4, fill=f_color,
            )
            # Score value
            draw.text((bar_x + bar_width + 5, y_pos), f"{score:+.0f}", fill=f_color, font=tiny_font, anchor="lt")
            y_pos += 22

    add_watermark(draw, w, h)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
