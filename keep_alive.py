#!/usr/bin/env python3
"""
Keep Alive Script for Render
Prevents the bot from sleeping due to inactivity
"""

import os
import time
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def keep_alive():
    """Keep the service alive by pinging it regularly"""
    
    # Get the service URL from environment or use default
    service_url = os.getenv('SERVICE_URL', 'https://fsociety-discord-bot.onrender.com')
    
    logger.info(f"🚀 بدء Keep-Alive لـ: {service_url}")
    
    while True:
        try:
            # Try multiple endpoints to ensure service stays alive
            endpoints = ['/', '/health', '/ping']
            
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
        
        # Wait 20 seconds before next ping (to stay well under 30s limit)
        logger.info("⏳ انتظار 20 ثانية للـ ping التالي...")
        time.sleep(20)

if __name__ == "__main__":
    keep_alive() 