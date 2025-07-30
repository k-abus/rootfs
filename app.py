#!/usr/bin/env python3
"""
FSociety Discord Bot - Main Application
"""

import os
import sys
from main import bot

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ يرجى إضافة DISCORD_TOKEN في متغيرات البيئة")
        print("في Render: اذهب إلى Environment Variables وأضف DISCORD_TOKEN")
        sys.exit(1)
    
    print("🚀 بدء تشغيل البوت...")
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        print("تأكد من صحة التوكن وصلاحيات البوت")
        sys.exit(1) 