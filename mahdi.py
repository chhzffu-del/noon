import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import requests
import os
import time
from flask import Flask
import threading

# ==============================================================================
# --- الإعدادات الثابتة ---
# ==============================================================================

# تم دمج كل شيء هنا لسهولة النشر
TELEGRAM_BOT_TOKEN = "5235296383:AAHLfTvwKtG8ZQuQvP4Ua0yP7AfWkwVo7mo"
SEGMIND_API_KEY = "SG_047ed0e22f564d48"
ADMIN_CHAT_ID = 1148797883

# ==============================================================================
# --- الخادم الوهمي لإبقاء Render سعيداً ---
# ==============================================================================

app = Flask(__name__)
@app.route('/')
def hello_world():
    return 'Bot is alive!'

def run_flask_app():
    app.run(host='0.0.0.0', port=10000)

# ==============================================================================
# --- (لا تقم بتعديل أي شيء تحت هذا الخط) ---
# ==============================================================================

def create_video_segmind(prompt: str) -> bytes:
    """
    يتواصل مع Segmind API لإنشاء الفيديو.
    """
    url = "https://api.segmind.com/v1/sd-svd"
    headers = {'x-api-key': SEGMIND_API_KEY}
    data = {
        "prompt": prompt,
        "size": "1024x576",
        "num_inference_steps": 25,
        "base64": False
    }
    
    try:
        print(f"🎬 جاري إرسال الطلب إلى Segmind لإنشاء فيديو من النص: '{prompt}'")
        # زيادة مهلة الانتظار إلى 3 دقائق (180 ثانية)
        response = requests.post(url, json=data, headers=headers, timeout=180)
        
        if response.status_code == 200:
            video_content = response.content
            print("✅ Segmind - تم استلام الفيديو بنجاح.")
            return video_content
        else:
            error_message = response.text # استخدام .text للحصول على تفاصيل الخطأ
            print(f"❌ Segmind - حدث خطأ: {response.status_code} - {error_message}")
            return None

    except requests.exceptions.Timeout:
        print("❌ Segmind - انتهت مهلة الانتظار (Timeout). استغرقت العملية وقتاً طويلاً جداً.")
        return "timeout"
    except Exception as e:
        print(f"❌ حدث خطأ فادح أثناء التواصل مع Segmind: {e}")
        return None

async def start_command(update, context):
    user_id = update.message.from_user.id
    if user_id == ADMIN_CHAT_ID:
        await update.message.reply_text("مرحباً سيدي مهدي. أنا بوت الفيديو (إصدار Segmind). أرسل لي نصاً وسأحوله إلى فيديو.")

async def handle_message(update, context):
    user_id = update.message.from_user.id
    if user_id != ADMIN_CHAT_ID:
        return

    prompt = update.message.text
    await update.message.reply_text("⏳ تم استلام طلبك (Segmind). قد تستغرق العملية دقيقة أو دقيقتين. من فضلك انتظر...")

    video_content = create_video_segmind(prompt)

    if video_content and video_content != "timeout":
        await update.message.reply_video(
            video=video_content,
            caption=f"✅ (Segmind) تم إنشاء الفيديو بنجاح!\n\nالنص الأصلي: {prompt}"
        )
    elif video_content == "timeout":
        await update.message.reply_text("❌ عذراً، استغرقت العملية وقتاً طويلاً جداً وتجاوزت مهلة الانتظار. قد تكون خوادم Segmind مشغولة. يرجى المحاولة مرة أخرى لاحقاً.")
    else:
        await update.message.reply_text("❌ عذراً، حدث خطأ أثناء إنشاء الفيديو. يرجى التحقق من سجلات Render.")

def run_bot():
    print("🚀 جاري تشغيل بوت الفيديو (إصدار Segmind)...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ البوت يعمل الآن وجاهز لإنشاء الفيديوهات.")
    application.run_polling()

# --- التشغيل الرئيسي ---
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True
    flask_thread.start()
    print("🌐 الخادم الوهمي يعمل في الخلفية لإبقاء الخدمة حية.")
    run_bot()
