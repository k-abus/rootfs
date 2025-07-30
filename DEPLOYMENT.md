# 🚀 دليل النشر السريع

## النشر على Render

### 1. إعداد البوت في Discord
1. اذهب إلى [Discord Developer Portal](https://discord.com/developers/applications)
2. أنشئ تطبيق جديد
3. اذهب إلى قسم "Bot" وأنشئ بوت
4. انسخ التوكن (Token)

### 2. النشر على Render
1. اذهب إلى [Render Dashboard](https://dashboard.render.com/)
2. اضغط "New +" → "Web Service"
3. اربط حساب GitHub واختر الـ repository
4. املأ المعلومات:
   - **Name**: fsociety-discord-bot
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. أضف متغير البيئة:
   - **Key**: `DISCORD_TOKEN`
   - **Value**: `your_bot_token_here`
6. اضغط "Create Web Service"

### 3. إضافة البوت للسيرفر
1. اذهب إلى "OAuth2" في Discord Developer Portal
2. في "Scopes" اختر "bot"
3. في "Bot Permissions" اختر:
   - Manage Roles
   - Ban Members
   - Kick Members
   - Manage Messages
   - Send Messages
4. انسخ الرابط وأضف البوت لسيرفرك

## الأوامر المتاحة
- `مساعدة` - قائمة الأوامر
- `اسكات` - خيارات الميوت (للمشرفين)
- `اسكت @user السبب` - ميوت مباشر (مثال: اسكت @user سب)
- `ميوت @user 1 30` - ميوت عضو
- `باند @user` - حظر عضو
- `كيك @user` - طرد عضو
- `مسح 10` - مسح رسائل 