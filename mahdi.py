import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import replicate
import os
import time
from flask import Flask
import threading

# ==============================================================================
# --- الإعدادات (سيتم ملؤها من متغيرات البيئة) ---
# ==============================================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
ADMIN_CHAT_ID_STR = os.environ.get("ADMIN_CHAT_ID")
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_STR) if ADMIN_CHAT_ID_STR else None
VIDEO_MODEL = "anotherjesse/zeroscope-v2-xl:9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351"

# ==============================================================================
# --- الخادم الوهمي لإبقاء Render سعيداً ---
# ==============================================================================

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Bot is alive!'

def run_flask_app():
    # Render يبحث عن منفذ 10000 بشكل افتراضي
    app.run(host='0.0.0.0', port=10000)

# ==============================================================================
# --- (لا تقم بتعديل أي شيء تحت هذا الخط) ---
# ==============================================================================

def create_video(prompt: str) -> str:
    try:
        print(f"🎬 جاري إرسال الطلب إلى Replicate لإنشاء فيديو من النص: '{prompt}'")
        output = replicate.run(
            VIDEO_MODEL,
            input={"prompt": prompt}
        )
        video_url = output[0]
        print(f"✅ تم استلام رابط الفيديو من Replicate: {video_url}")
        return video_url
    except Exception as e:
        print(f"❌ حدث خطأ أثناء التواصل مع Replicate: {e}")
        return None

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

def run_bot():
    if not all([TELEGRAM_BOT_TOKEN, REPLICATE_API_TOKEN, ADMIN_CHAT_ID]):
        print("❌ خطأ فادح: بعض متغيرات البيئة مفقودة.")
        return

    print("🚀 جاري تشغيل بوت الفيديو الاحترافي...")
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ البوت يعمل الآن وجاهز لإنشاء الفيديوهات.")
    application.run_polling()

# --- التشغيل الرئيسي ---
if __name__ == "__main__":
    # تشغيل خادم Flask في خيط منفصل
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    print("🌐 الخادم الوهمي يعمل في الخلفية لإبقاء الخدمة حية.")

    # تشغيل البوت في الخيط الرئيسي
    run_bot()
