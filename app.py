#!/usr/bin/env python3
"""
FSociety Discord Bot - Main Application
"""

import os
import sys
import threading
import time
import signal
import logging
import requests
from flask import Flask
from main import bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "FSociety Discord Bot is running! 🤖", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/status')
def status():
    return {
        "status": "running",
        "bot": "online",
        "timestamp": time.time()
    }, 200

@app.route('/keep-alive')
def keep_alive():
    return "alive", 200

def keep_alive_service():
    """Keep the service alive by pinging itself"""
    # Get the service URL from environment or use localhost for development
    service_url = os.getenv('RENDER_EXTERNAL_URL') or os.getenv('SERVICE_URL') or 'http://localhost:8080'
    
    logger.info(f"🚀 بدء Keep-Alive Service لـ: {service_url}")
    
    # Wait for Flask server to start
    time.sleep(10)
    
    while True:
        try:
            # Try multiple endpoints to ensure service stays alive
            endpoints = ['/', '/health', '/ping', '/keep-alive']
            
            for endpoint in endpoints:
                try:
                    url = f"{service_url}{endpoint}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Keep-alive ping successful: {endpoint}")
                    else:
                        logger.warning(f"⚠️ Keep-alive ping failed: {endpoint} - {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ Keep-alive ping error for {endpoint}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ General keep-alive error: {e}")
        
        # Wait 25 seconds before next ping (to stay well under 30s limit)
        logger.info("⏳ انتظار 25 ثانية للـ ping التالي...")
        time.sleep(25)

def run_bot():
    """Run the Discord bot in a separate thread with error handling"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("❌ يرجى إضافة DISCORD_TOKEN في متغيرات البيئة")
        logger.error("في Render: اذهب إلى Environment Variables وأضف DISCORD_TOKEN")
        return
    
    logger.info("🚀 بدء تشغيل البوت...")
    
    while True:
        try:
            logger.info("🔄 محاولة تشغيل البوت...")
            bot.run(token, log_handler=None)
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل البوت: {e}")
            logger.info("🔄 إعادة تشغيل البوت خلال 30 ثانية...")
            time.sleep(30)
            continue
        except KeyboardInterrupt:
            logger.info("🛑 إيقاف البوت...")
            break

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("🛑 استلام إشارة الإيقاف...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start Discord bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Start keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive_service, daemon=True)
    keep_alive_thread.start()
    
    # Wait a bit for bot to start
    time.sleep(5)
    
    # Start Flask app for Render
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🌐 بدء خادم Flask على port {port}")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل Flask: {e}")
        sys.exit(1) 