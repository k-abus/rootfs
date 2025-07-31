#!/usr/bin/env python3
"""
FSociety Discord Bot - Main Application
"""

import os
import sys
import threading
import time
from flask import Flask
from main import bot

# Create Flask app for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "FSociety Discord Bot is running! 🤖"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    """Run the Discord bot in a separate thread"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ يرجى إضافة DISCORD_TOKEN في متغيرات البيئة")
        print("في Render: اذهب إلى Environment Variables وأضف DISCORD_TOKEN")
        return
    
    print("🚀 بدء تشغيل البوت...")
    try:
        bot.run(token, log_handler=None)
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        print("تأكد من صحة التوكن وصلاحيات البوت")

if __name__ == "__main__":
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Wait a bit for bot to start
    time.sleep(2)
    
    # Start Flask app for Render
    port = int(os.environ.get('PORT', 8000))
    print(f"🌐 بدء خادم Flask على port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 