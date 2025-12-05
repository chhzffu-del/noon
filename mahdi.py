import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import replicate
import os
import time

# ==============================================================================
# --- الإعدادات (سيتم ملؤها من متغيرات البيئة) ---
# ==============================================================================

# 1. توكن بوت تيليجرام (سيتم قراءته من متغيرات البيئة)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# 2. مفتاح Replicate API (سيتم قراءته من متغيرات البيئة)
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

# 3. معرف حساب تيليجرام الخاص بك (سيتم قراءته من متغيرات البيئة)
# نحوله إلى رقم صحيح لأن متغيرات البيئة تكون دائماً نصية
ADMIN_CHAT_ID_STR = os.environ.get("ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_STR) if ADMIN_CHAT_ID_STR else None

# --- إعدادات نموذج الفيديو ---
# سنستخدم نموذج Zeroscope v2 XL لأنه جيد ومناسب
VIDEO_MODEL = "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"

# ==============================================================================
# --- (لا تقم بتعديل أي شيء تحت هذا الخط) ---
# ==============================================================================

# --- دالة إنشاء الفيديو عبر Replicate ---
def create_video(prompt: str) -> str:
    """
    يرسل الطلب إلى Replicate وينتظر النتيجة.
    """
    try:
        print(f"🎬 جاري إرسال الطلب إلى Replicate لإنشاء فيديو من النص: '{prompt}'")
        output = replicate.run(
            VIDEO_MODEL,
            input={"prompt": prompt}
        )
        # الناتج يكون عادة قائمة، نأخذ الرابط الأول
        video_url = output[0]
        print(f"✅ تم استلام رابط الفيديو من Replicate: {video_url}")
        return video_url
    except Exception as e:
        print(f"❌ حدث خطأ أثناء التواصل مع Replicate: {e}")
        return None

# --- دوال البوت ---
async def start_command(update, context):
    user_id = update.message.from_user.id
    if user_id == ADMIN_CHAT_ID:
        await update.message.reply_text("مرحباً سيدي مهدي. أنا بوت الفيديو الاحترافي. أرسل لي نصاً وسأحوله إلى فيديو باستخدام Replicate.")

async def handle_message(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_CHAT_ID:
        return

    prompt = update.message.text
    await update.message.reply_text("⏳ تم استلام طلبك. قد تستغرق عملية إنشاء الفيديو عدة دقائق. من فضلك انتظر...")

    video_url = create_video(prompt)

    if video_url:
        await update.message.reply_video(
            video=video_url,
            caption=f"✅ تم إنشاء الفيديو بنجاح!\n\nالنص الأصلي: {prompt}"
        )
    else:
        await update.message.reply_text("❌ عذراً، حدث خطأ أثناء إنشاء الفيديو. يرجى المحاولة مرة أخرى لاحقاً.")

# --- التشغيل الرئيسي ---
def main():
    if not all([TELEGRAM_BOT_TOKEN, REPLICATE_API_TOKEN, ADMIN_CHAT_ID]):
        print("❌ خطأ فادح: بعض متغيرات البيئة مفقودة. تأكد من تعيين TELEGRAM_BOT_TOKEN, REPLICATE_API_TOKEN, و ADMIN_CHAT_ID.")
        return

    print("🚀 جاري تشغيل بوت الفيديو الاحترافي...")
    
    # نقوم بتعيين مفتاح Replicate API للمكتبة
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ البوت يعمل الآن وجاهز لإنشاء الفيديوهات.")
    application.run_polling()

if __name__ == "__main__":
    main()
