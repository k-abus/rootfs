#!/usr/bin/env python3
"""
Keep Alive Service for FSociety Discord Bot
"""

import os
import time
import requests
import logging
from threading import Thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def keep_alive():
    """Keep the service alive by pinging itself"""
    # Get the service URL from environment
    service_url = os.getenv('RENDER_EXTERNAL_URL') or os.getenv('SERVICE_URL') or 'https://fsociety-discord-bot.onrender.com'
    
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
        
        # Wait 15 seconds before next ping (to stay well under 30s limit)
        logger.info("⏳ انتظار 15 ثانية للـ ping التالي...")
        time.sleep(15)

def run_keep_alive():
    """Run keep alive in a separate thread"""
    keep_alive_thread = Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    return keep_alive_thread

if __name__ == "__main__":
    keep_alive() 