import os
import re
import jdatetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import random

# ==================== تنظیمات ====================
BOT_TOKEN = "7548697314:AAFjwvQzAT1ML5uwCJyGgMO1BFAjbmJFLVA"

ORG_NAME = "موسسه خیریه مهر یزدان"
CARD_NUMBER = "6037-9988-0011-8522"
DONOR_NAME = "خیر مهربان 🌹"
PURPOSE = "صدقه"
RECEIPT_PREFIX = "MY-"

# رنگ‌ها (کرم و بنفش)
BG_COLOR = (245, 235, 220)        # کرم روشن
PANEL_COLOR = (252, 245, 230)     # کرم روشن‌تر
BORDER_COLOR = (90, 50, 130)      # بنفش تیره
TEXT_DARK = (60, 30, 90)          # بنفش خیلی تیره (برای متن)
TEXT_ACCENT = (110, 60, 150)      # بنفش متوسط
GOLD = (180, 140, 70)             # طلایی ملایم

# ==================== توابع کمکی ====================
def extract_info_from_text(text: str):
    """استخراج اطلاعات از متن رسید بانکی"""
    info = {
        "amount": None,
        "date": None,
        "time": None,
        "tracking": None,
    }
    
    # مبلغ
    patterns_amount = [
        r'(\d{1,3}(?:[,\.]\d{3})+)\s*(?:ریال|تومان)',
        r'مبلغ[:\s]*([\d,\.]+)',
        r'مبلغ\s*:\s*([\d,\.]+)',
    ]
    for p in patterns_amount:
        m = re.search(p, text)
        if m:
            info["amount"] = m.group(1).replace(',', ',')
            break
    
    # تاریخ شمسی (مثل ۱۴۰۵/۰۵/۲۱ یا ۱۴۰۵-۰۵-۲۱)
    patterns_date = [
        r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',
    ]
    for p in patterns_date:
        m = re.search(p, text)
        if m:
            y, mo, d = m.groups()
            info["date"] = f"{y}/{int(mo):02d}/{int(d):02d}"
            break
    
    # ساعت
    m = re.search(r'(\d{1,2}):(\d{2})', text)
    if m:
        info["time"] = f"{m.group(1)}:{m.group(2)}"
    
    # شماره پیگیری
    patterns_track = [
        r'پیگیری[:\s]*(\d+)',
        r'شماره\s*پیگیری[:\s]*(\d+)',
        r'ref(?:erence)?[:\s]*(\d+)',
    ]
    for p in patterns_track:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            info["tracking"] = m.group(1)
            break
    
    return info


def get_persian_font(size: int):
    """تلاش برای پیدا کردن فونت فارسی"""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()


def draw_islamic_pattern(draw, x, y, size, color):
    """رسم یک گل هشت‌پر اسلامی ساده"""
    cx, cy = x + size//2, y + size//2
    r = size // 2
    points = []
    import math
    for i in range(16):
        angle = math.radians(i * 22.5)
        rr = r if i % 2 == 0 else r * 0.5
        points.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
    draw.polygon(points, outline=color, width=2)


def create_receipt(amount: str, date: str, time: str, tracking: str) -> BytesIO:
    """ساخت تصویر رسید"""
    
    WIDTH, HEIGHT = 900, 1300
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # حاشیه بیرونی
    draw.rectangle([20, 20, WIDTH-20, HEIGHT-20], outline=BORDER_COLOR, width=4)
    draw.rectangle([35, 35, WIDTH-35, HEIGHT-35], outline=BORDER_COLOR, width=2)
    
    # نقش‌های اسلامی گوشه‌ها
    corner_size = 60
    for cx, cy in [(60, 60), (WIDTH-60, 60), (60, HEIGHT-60), (WIDTH-60, HEIGHT-60)]:
        draw_islamic_pattern(draw, cx - corner_size//2, cy - corner_size//2, corner_size, BORDER_COLOR)
    
    # فونت‌ها
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_value = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except:
        font_title = font_subtitle = font_label = font_value = font_small = ImageFont.load_default()
    
    # بسم‌الله
    draw.text((WIDTH//2, 100), "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ", 
              fill=TEXT_DARK, font=font_title, anchor="mm")
    
    # خط زیر بسم‌الله
    draw.line([(200, 150), (WIDTH-200, 150)], fill=GOLD, width=2)
    
    # نام سازمان
    draw.text((WIDTH//2, 200), ORG_NAME, fill=BORDER_COLOR, font=font_subtitle, anchor="mm")
    draw.text((WIDTH//2, 240), "رسید پرداخت صدقه", fill=TEXT_ACCENT, font=font_small, anchor="mm")
    
    # خط جداکننده
    draw.line([(150, 280), (WIDTH-150, 280)], fill=BORDER_COLOR, width=2)
    
    # پنل اطلاعات
    panel_y = 320
    panel_h = 720
    draw.rectangle([100, panel_y, WIDTH-100, panel_y + panel_h], 
                   fill=PANEL_COLOR, outline=BORDER_COLOR, width=2)
    
    # فیلدها
    fields = [
        ("نام پرداخت‌کننده", DONOR_NAME),
        ("بابت", PURPOSE),
        ("مبلغ (ریال)", amount or "—"),
        ("تاریخ", date or jdatetime.date.today().strftime("%Y/%m/%d")),
        ("ساعت", time or "—"),
        ("شماره پیگیری", tracking or "—"),
        ("شماره کارت", CARD_NUMBER),
    ]
    
    y = panel_y + 40
    for label, value in fields:
        # لیبل
        draw.text((130, y), f"{label}:", fill=TEXT_ACCENT, font=font_label, anchor="lm")
        # مقدار
        draw.text((WIDTH-130, y), str(value), fill=TEXT_DARK, font=font_value, anchor="rm")
        # خط نقطه‌چین
        for x in range(280, WIDTH-280, 8):
            draw.line([(x, y+25), (x+4, y+25)], fill=GOLD, width=1)
        y += 90
    
    # شماره رسید
    receipt_no = f"{RECEIPT_PREFIX}{random.randint(10000, 99999)}"
    draw.text((WIDTH//2, panel_y + panel_h + 60), f"شماره رسید: {receipt_no}", 
              fill=BORDER_COLOR, font=font_subtitle, anchor="mm")
    
    # پاورقی
    draw.text((WIDTH//2, HEIGHT-90), "خدایا شکرگزار نعمت‌هایت هستیم", 
              fill=TEXT_ACCENT, font=font_small, anchor="mm")
    draw.text((WIDTH//2, HEIGHT-60), "صدقه شما در راه خداوند صرف امور خیریه خواهد شد", 
              fill=TEXT_ACCENT, font=font_small, anchor="mm")
    
    # تبدیل به BytesIO
    bio = BytesIO()
    bio.name = f"receipt_{receipt_no}.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio


# ==================== هندلرها ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🌹 به ربات {ORG_NAME} خوش آمدید!\n\n"
        "برای ساخت رسید، متن رسید بانکی خود را ارسال کنید.\n"
        "ربات مبلغ، تاریخ و شماره پیگیری را استخراج کرده و رسید زیبا می‌سازد."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    info = extract_info_from_text(text)
    
    if not info["amount"]:
        await update.message.reply_text(
            "⚠️ نتوانستم مبلغ را از متن پیدا کنم.\n"
            "لطفاً متن کامل‌تری ارسال کنید یا مبلغ را دستی وارد کنید."
        )
        return
    
    receipt_img = create_receipt(
        amount=info["amount"],
        date=info["date"],
        time=info["time"],
        tracking=info["tracking"],
    )
    
    caption = (
        f"✅ رسید شما ساخته شد\n"
        f"💰 مبلغ: {info['amount']} ریال\n"
        f"📅 تاریخ: {info['date'] or 'امروز'}"
    )
    await update.message.reply_photo(photo=receipt_img, caption=caption)


# ==================== اجرا ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()