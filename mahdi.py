import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import cv2
import numpy as np
import os
import rawpy
import imageio

# ==============================================================================
# --- الإعدادات (املأ هذه الفراغات فقط) ---
# ==============================================================================

# 1. ضع توكن بوت تيليجرام الخاص بك هنا
TELEGRAM_BOT_TOKEN = "5235296383:AAHDIcr6f_z1KANLITw2_sEb4Ky8dlihsiI"

# 2. ضع معرف حساب تيليجرام الخاص بك (الأيدي) هنا
ADMIN_CHAT_ID = 1148797883  # استبدل هذا الرقم بالأيدي الخاص بك

# ==============================================================================
# --- (لا تقم بتعديل أي شيء تحت هذا الخط) ---
# ==============================================================================

# --- تعريف مراحل المحادثة ---
CONTENT_FILE, STYLE_FILE = range(2)

# --- دوال معالجة الصور ---

def white_balance(img):
    """
    يطبق توازن البياض التلقائي باستخدام خوارزمية Grayscale World.
    """
    avg_b = np.mean(img[:, :, 0])
    avg_g = np.mean(img[:, :, 1])
    avg_r = np.mean(img[:, :, 2])
    
    avg_gray = (avg_b + avg_g + avg_r) / 3
    
    scale_b = avg_gray / (avg_b + 1e-8)
    scale_g = avg_gray / (avg_g + 1e-8)
    scale_r = avg_gray / (avg_r + 1e-8)
    
    img[:, :, 0] = np.clip(img[:, :, 0] * scale_b, 0, 255)
    img[:, :, 1] = np.clip(img[:, :, 1] * scale_g, 0, 255)
    img[:, :, 2] = np.clip(img[:, :, 2] * scale_r, 0, 255)
    
    return img

def enhance_quality(image):
    """
    يزيد من حدة الصورة باستخدام Unsharp Masking.
    """
    gaussian_blur = cv2.GaussianBlur(image, (0, 0), 3.0)
    unsharp_image = cv2.addWeighted(image, 1.5, gaussian_blur, -0.5, 0)
    print("✅ تم تطبيق تحسين الجودة (Sharpening).")
    return unsharp_image

def transfer_color(source, target):
    """
    [V3] ينقل الألوان بعد تطبيق توازن البياض على كلتا الصورتين.
    """
    print("🎨 [v3] تطبيق توازن البياض (White Balance)...")
    source_wb = white_balance(source.copy())
    target_wb = white_balance(target.copy())

    print("🎨 [v3] جاري تحليل الألوان المحايدة...")
    source_lab = cv2.cvtColor(source_wb, cv2.COLOR_BGR2LAB)
    target_lab = cv2.cvtColor(target_wb, cv2.COLOR_BGR2LAB)

    s_l, s_a, s_b = cv2.split(source_lab)
    t_l, t_a, t_b = cv2.split(target_lab)

    print("🎨 [v3] جاري تطبيق الفلتر...")
    s_a_mean, s_a_std = cv2.meanStdDev(s_a)
    s_b_mean, s_b_std = cv2.meanStdDev(s_b)
    t_a_mean, t_a_std = cv2.meanStdDev(t_a)
    t_b_mean, t_b_std = cv2.meanStdDev(t_b)

    new_a = (t_a - t_a_mean) * (s_a_std / (t_a_std + 1e-8)) + s_a_mean
    new_b = (t_b - t_b_mean) * (s_b_std / (t_b_std + 1e-8)) + s_b_mean
    
    new_a = np.clip(new_a, -128, 127)
    new_b = np.clip(new_b, -128, 127)

    original_target_lab = cv2.cvtColor(target, cv2.COLOR_BGR2LAB)
    original_t_l, _, _ = cv2.split(original_target_lab)
    
    final_lab = cv2.merge([original_t_l, new_a.astype(np.uint8), new_b.astype(np.uint8)])
    final_bgr = cv2.cvtColor(final_lab, cv2.COLOR_LAB2BGR)
    
    print("✅ [v3] تم تطبيق الفلتر بنجاح.")
    return final_bgr

def read_image_from_bytes(file_bytes, filename):
    """
    [v4.1] يقرأ الصورة من البايتات، ويقوم بتحميضها إذا كانت بصيغة DNG.
    """
    file_ext = os.path.splitext(filename)[1].lower()

    if file_ext == '.dng':
        print(f"📸 تم اكتشاف ملف DNG ({filename}). جاري التحميض...")
        try:
            with rawpy.imread(file_bytes) as raw:
                rgb = raw.postprocess(use_camera_wb=True, half_size=False, no_auto_bright=True, output_bps=8)
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            print("✅ تم تحميض ملف DNG بنجاح.")
            return bgr
        except Exception as e:
            print(f"❌ فشل في معالجة ملف DNG: {e}")
            return None
    else:
        print(f"🖼️ تم اكتشاف صورة عادية ({filename}).")
        np_array = np.frombuffer(file_bytes, np.uint8)
        bgr = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        if bgr is None:
            print(f"❌ فشل في فك تشفير الصورة العادية: {filename}")
        return bgr

# --- دوال البوت ---

async def start(update, context):
    user_id = update.message.from_user.id
    if user_id == ADMIN_CHAT_ID:
        await update.message.reply_text(
            "مرحباً سيدي مهدي. أنا بوت استوديو DNG (v4.1).\n\n"
            "أنا أقبل صور JPEG/PNG (كصورة) أو ملفات DNG (كمِلَف).\n\n"
            "1. أرسل لي الصورة أو الملف الذي تريد تعديله."
        )
        return CONTENT_FILE
    return ConversationHandler.END

async def get_content_file(update, context):
    """يستلم صورة المحتوى (صورة أو ملف) ويحفظها."""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_name = f"{file_id}.jpg"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
    else:
        return CONTENT_FILE

    file = await context.bot.get_file(file_id)
    file_bytes = await file.download_as_bytearray()
    
    context.user_data['content_file_bytes'] = bytes(file_bytes)
    context.user_data['content_file_name'] = file_name
    
    await update.message.reply_text(
        "تم استلام ملف المحتوى بنجاح.\n\n"
        "2. الآن، أرسل لي صورة أو ملف الفلتر."
    )
    return STYLE_FILE

async def process_files(update, context):
    """[v4.1] يستلم ملف الفلتر، يقوم بكل العمليات، ويرسل النتيجة."""
    await update.message.reply_text("تم استلام ملف الفلتر. ⏳ جاري المعالجة الاحترافية...")

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_name = f"{file_id}.jpg"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
    else:
        return STYLE_FILE
        
    file = await context.bot.get_file(file_id)
    style_bytes = await file.download_as_bytearray()
    style_image = read_image_from_bytes(style_bytes, file_name)

    content_bytes = context.user_data['content_file_bytes']
    content_name = context.user_data['content_file_name']
    content_image = read_image_from_bytes(content_bytes, content_name)

    if content_image is None or style_image is None:
        await update.message.reply_text("❌ عذراً، لم أتمكن من قراءة أحد الملفات. قد يكون الملف تالفاً أو بصيغة غير مدعومة. يرجى المحاولة مرة أخرى. /start")
        context.user_data.clear()
        return ConversationHandler.END

    enhanced_content = enhance_quality(content_image)
    final_image = transfer_color(source=style_image, target=enhanced_content)

    output_path = "final_output.jpg"
    cv2.imwrite(output_path, final_image)
    await update.message.reply_photo(
        photo=open(output_path, 'rb'),
        caption="تم الانتهاء! تفضل صورتك الجديدة بعد المعالجة الاحترافية."
    )
    
    os.remove(output_path)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text("تم إلغاء العملية. أرسل /start لبدء من جديد.")
    context.user_data.clear()
    return ConversationHandler.END

# --- التشغيل الرئيسي ---
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONTENT_FILE: [MessageHandler(filters.PHOTO | filters.Document.ALL, get_content_file)],
            STYLE_FILE: [MessageHandler(filters.PHOTO | filters.Document.ALL, process_files)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    print("✅ بوت استوديو DNG (v4.1) يعمل الآن.")
    application.run_polling()

if __name__ == "__main__":
    main()
