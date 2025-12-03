import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
import cv2
import numpy as np
import os

# --- الإعدادات ---
TELEGRAM_BOT_TOKEN = "5235296383:AAHDIcr6f_z1KANLITw2_sEb4Ky8dlihsiI"
ADMIN_CHAT_ID = 1148797883

# --- تعريف مراحل المحادثة ---
CONTENT_PHOTO, STYLE_PHOTO = range(2)

# --- الدوال الأساسية للمعالجة ---

def enhance_quality(image):
    """يزيد من حدة الصورة باستخدام Unsharp Masking."""
    gaussian_blur = cv2.GaussianBlur(image, (0, 0), 3.0)
    unsharp_image = cv2.addWeighted(image, 1.5, gaussian_blur, -0.5, 0)
    print("✅ تم تطبيق تحسين الجودة (Sharpening).")
    return unsharp_image

def transfer_color(source, target):
    """ينقل الألوان والإضاءة من الصورة المصدر إلى الصورة الهدف."""
    print("🎨 جاري تحليل الألوان...")
    source = cv2.cvtColor(source, cv2.COLOR_BGR2LAB)
    target = cv2.cvtColor(target, cv2.COLOR_BGR2LAB)

    s_mean, s_std = cv2.meanStdDev(source)
    t_mean, t_std = cv2.meanStdDev(target)

    print("🎨 جاري تطبيق الفلتر...")
    target_pixels = target.reshape((-1, 3))
    
    # عملية المطابقة
    target_pixels = (target_pixels - t_mean.flatten()) * (s_std.flatten() / (t_std.flatten() + 1e-8)) + s_mean.flatten()
    
    # التأكد من أن القيم ضمن النطاق الصحيح
    target_pixels = np.clip(target_pixels, [0, -128, -128], [255, 127, 127])
    
    target = target_pixels.reshape(target.shape).astype(np.uint8)
    target = cv2.cvtColor(target, cv2.COLOR_LAB2BGR)
    print("✅ تم تطبيق الفلter بنجاح.")
    return target

# --- دوال البوت ---

async def start(update, context):
    user_id = update.message.from_user.id
    if user_id == ADMIN_CHAT_ID:
        await update.message.reply_text(
            "مرحباً سيدي مهدي. أنا بوت الاستوديو الرقمي.\n\n"
            "1. أرسل لي الصورة التي تريد تعديلها (صورة المحتوى)."
        )
        return CONTENT_PHOTO
    return ConversationHandler.END

async def get_content_photo(update, context):
    """يستلم صورة المحتوى ويحفظها مؤقتاً."""
    photo_file = await update.message.photo[-1].get_file()
    file_bytes = await photo_file.download_as_bytearray()
    
    context.user_data['content_photo'] = bytes(file_bytes)
    
    await update.message.reply_text(
        "تم استلام صورة المحتوى بنجاح.\n\n"
        "2. الآن، أرسل لي الصورة التي تريد أخذ الفلتر منها (صورة الفلتر)."
    )
    return STYLE_PHOTO

async def process_photos(update, context):
    """يستلم صورة الفلتر، يقوم بكل العمليات، ويرسل النتيجة."""
    await update.message.reply_text("تم استلام صورة الفلتر. ⏳ جاري المعالجة، قد يستغرق هذا بعض الوقت...")

    # قراءة صورة الفلتر
    style_photo_file = await update.message.photo[-1].get_file()
    style_bytes = await style_photo_file.download_as_bytearray()
    style_np_array = np.frombuffer(style_bytes, np.uint8)
    style_image = cv2.imdecode(style_np_array, cv2.IMREAD_COLOR)

    # قراءة صورة المحتوى المحفوظة
    content_bytes = context.user_data['content_photo']
    content_np_array = np.frombuffer(content_bytes, np.uint8)
    content_image = cv2.imdecode(content_np_array, cv2.IMREAD_COLOR)

    # --- خط الإنتاج ---
    # 1. تحسين جودة صورة المحتوى
    enhanced_content = enhance_quality(content_image)
    
    # 2. نقل الفلتر إلى الصورة المحسنة
    final_image = transfer_color(source=style_image, target=enhanced_content)

    # حفظ الصورة النهائية لإرسالها
    output_path = "final_output.jpg"
    cv2.imwrite(output_path, final_image)

    # إرسال النتيجة
    await update.message.reply_photo(
        photo=open(output_path, 'rb'),
        caption="تم الانتهاء! تفضل صورتك الجديدة بعد تحسين الجودة وتطبيق الفلتر."
    )
    
    # تنظيف
    os.remove(output_path)
    context.user_data.clear()
    
    return ConversationHandler.END

async def cancel(update, context):
    """يلغي العملية الحالية."""
    await update.message.reply_text("تم إلغاء العملية. أرسل /start لبدء من جديد.")
    context.user_data.clear()
    return ConversationHandler.END

# --- التشغيل الرئيسي ---
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONTENT_PHOTO: [MessageHandler(filters.PHOTO, get_content_photo)],
            STYLE_PHOTO: [MessageHandler(filters.PHOTO, process_photos)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    print("✅ بوت الاستوديو الرقمي يعمل الآن.")
    application.run_polling()

if __name__ == "__main__":
    main()
