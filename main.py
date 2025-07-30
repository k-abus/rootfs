import discord
from discord.ext import commands
import asyncio
import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Required for commands to work

bot = commands.Bot(command_prefix='$', intents=intents)

# Mute durations in seconds
MUTE_DURATIONS = {
    "سب أو شتائم": 30 * 60,  # 30 minutes
    "إساءة أو استهزاء": 60 * 60,  # 1 hour
    "روابط بدون إذن": 2 * 60 * 60,  # 2 hours
    "سبام": 45 * 60,  # 45 minutes
    "تجاهل التحذيرات": 15 * 60,  # 15 minutes
}

@bot.event
async def on_ready():
    print(f'{bot.user} تم تشغيل البوت بنجاح!')
    await bot.change_presence(activity=discord.Game(name="$اسكت للميوت | $باند للحظر"))

@bot.command(name='اسكت')
async def mute_member(ctx, member: discord.Member, reason_type: str = None, duration_minutes: int = None):
    """أمر الميوت مع خيارات متعددة"""
    
    # Check if user has permission
    if not ctx.author.guild_permissions.manage_roles:
        await ctx.send("❌ ليس لديك صلاحية لاستخدام هذا الأمر!")
        return
    
    if member.bot:
        await ctx.send("❌ لا يمكنك ميوت البوتات!")
        return
    
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكنك ميوت المشرفين!")
        return

    # Create embed for mute options
    embed = discord.Embed(
        title="🔇 خيارات الميوت",
        description="اختر سبب الميوت:",
        color=0xff6b6b
    )
    
    embed.add_field(
        name="1️⃣ سب أو شتائم عامة",
        value="⏱️ مدة الإسكات: 30 دقيقة\n🔹 ملاحظة: إذا تكررت، زيدها إلى ساعة أو أكثر.",
        inline=False
    )
    
    embed.add_field(
        name="2️⃣ إساءة أو استهزاء بعضو أو مشرف",
        value="⏱️ مدة الإسكات: 1 ساعة\n🔹 إذا كانت الإساءة مباشرة أو متعمدة، يمكن توصل لـ 3 ساعات.",
        inline=False
    )
    
    embed.add_field(
        name="3️⃣ نشر روابط بدون إذن أو إعلانات",
        value="⏱️ مدة الإسكات: 2 ساعات\n🔹 خاصة إذا كانت روابط خارجية، يمكن توصل إلى 6 ساعات لو تكررت.",
        inline=False
    )
    
    embed.add_field(
        name="4️⃣ سبام (إرسال نفس الرسالة أكثر من مرة بسرعة)",
        value="⏱️ مدة الإسكات: 45 دقيقة\n🔹 إذا كان مزعج أو يستخدم @الكل، زيدها لـ 1.5 ساعة.",
        inline=False
    )
    
    embed.add_field(
        name="5️⃣ التحدث في أماكن غير مخصصة أو تجاهل التحذيرات",
        value="⏱️ مدة الإسكات: 15 - 30 دقيقة\n🔹 المدة قصيرة لأنها مخالفة بسيطة، لكن تتضاعف لو تكررت.",
        inline=False
    )
    
    embed.set_footer(text="اكتب $ميوت [عضو] [رقم السبب] [المدة بالدقائق اختياري]")
    
    await ctx.send(embed=embed)

@bot.command(name='ميوت')
async def execute_mute(ctx, member: discord.Member, reason_number: int, duration_minutes: int = None):
    """تنفيذ الميوت بناءً على السبب المختار"""
    
    if not ctx.author.guild_permissions.manage_roles:
        await ctx.send("❌ ليس لديك صلاحية لاستخدام هذا الأمر!")
        return
    
    if member.bot:
        await ctx.send("❌ لا يمكنك ميوت البوتات!")
        return
    
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكنك ميوت المشرفين!")
        return

    # Map reason numbers to reasons and durations
    reasons = {
        1: ("سب أو شتائم عامة", 30),
        2: ("إساءة أو استهزاء بعضو أو مشرف", 60),
        3: ("نشر روابط بدون إذن أو إعلانات", 120),
        4: ("سبام (إرسال نفس الرسالة أكثر من مرة بسرعة)", 45),
        5: ("التحدث في أماكن غير مخصصة أو تجاهل التحذيرات", 15)
    }
    
    if reason_number not in reasons:
        await ctx.send("❌ رقم السبب غير صحيح! استخدم أرقام من 1 إلى 5")
        return
    
    reason, default_duration = reasons[reason_number]
    duration = duration_minutes if duration_minutes else default_duration
    
    # Find or create muted role
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        try:
            muted_role = await ctx.guild.create_role(name="Muted", reason="إنشاء دور الميوت")
            for channel in ctx.guild.channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(muted_role, speak=False, connect=False)
        except discord.Forbidden:
            await ctx.send("❌ لا أملك صلاحيات لإنشاء دور الميوت!")
            return
    
    # Apply mute
    try:
        await member.add_roles(muted_role, reason=f"ميوت بواسطة {ctx.author.name} - السبب: {reason}")
        
        embed = discord.Embed(
            title="🔇 تم الميوت بنجاح",
            description=f"تم ميوت {member.mention}",
            color=0xff6b6b,
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="المدة", value=f"{duration} دقيقة", inline=True)
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)
        
        # Remove mute after duration
        await asyncio.sleep(duration * 60)
        if muted_role in member.roles:
            await member.remove_roles(muted_role, reason="انتهاء مدة الميوت")
            await ctx.send(f"✅ تم إلغاء ميوت {member.mention} بعد انتهاء المدة")
            
    except discord.Forbidden:
        await ctx.send("❌ لا أملك صلاحيات لإضافة دور الميوت!")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.command(name='باند')
async def ban_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """حظر عضو من السيرفر"""
    
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("❌ ليس لديك صلاحية لاستخدام هذا الأمر!")
        return
    
    if member.bot:
        await ctx.send("❌ لا يمكنك حظر البوتات!")
        return
    
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكنك حظر المشرفين!")
        return
    
    if member == ctx.author:
        await ctx.send("❌ لا يمكنك حظر نفسك!")
        return

    try:
        await member.ban(reason=f"حظر بواسطة {ctx.author.name} - السبب: {reason}")
        
        embed = discord.Embed(
            title="🔨 تم الحظر بنجاح",
            description=f"تم حظر {member.mention}",
            color=0xff0000,
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ لا أملك صلاحيات لحظر الأعضاء!")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.command(name='كيك')
async def kick_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """طرد عضو من السيرفر"""
    
    if not ctx.author.guild_permissions.kick_members:
        await ctx.send("❌ ليس لديك صلاحية لاستخدام هذا الأمر!")
        return
    
    if member.bot:
        await ctx.send("❌ لا يمكنك طرد البوتات!")
        return
    
    if member.guild_permissions.administrator:
        await ctx.send("❌ لا يمكنك طرد المشرفين!")
        return
    
    if member == ctx.author:
        await ctx.send("❌ لا يمكنك طرد نفسك!")
        return

    try:
        await member.kick(reason=f"طرد بواسطة {ctx.author.name} - السبب: {reason}")
        
        embed = discord.Embed(
            title="👢 تم الطرد بنجاح",
            description=f"تم طرد {member.mention}",
            color=0xffa500,
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ لا أملك صلاحيات لطرد الأعضاء!")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.command(name='مسح')
async def clear_messages(ctx, amount: int):
    """مسح عدد محدد من الرسائل"""
    
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ ليس لديك صلاحية لاستخدام هذا الأمر!")
        return
    
    if amount < 1 or amount > 100:
        await ctx.send("❌ يمكنك مسح من 1 إلى 100 رسالة فقط!")
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
        await ctx.send(f"✅ تم مسح {len(deleted) - 1} رسالة بنجاح!", delete_after=5)
        
    except discord.Forbidden:
        await ctx.send("❌ لا أملك صلاحيات لمسح الرسائل!")
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {str(e)}")

@bot.command(name='مساعدة')
async def help_command(ctx):
    """عرض قائمة الأوامر المتاحة"""
    
    embed = discord.Embed(
        title="🤖 قائمة الأوامر المتاحة",
        description="جميع الأوامر المتاحة للبوت",
        color=0x00ff00
    )
    
    embed.add_field(
        name="🔇 !اسكت [عضو]",
        value="عرض خيارات الميوت المتاحة",
        inline=False
    )
    
    embed.add_field(
        name="🔇 !ميوت [عضو] [رقم السبب] [المدة اختياري]",
        value="ميوت عضو مع تحديد السبب والمدة",
        inline=False
    )
    
    embed.add_field(
        name="🔨 !باند [عضو] [السبب اختياري]",
        value="حظر عضو من السيرفر",
        inline=False
    )
    
    embed.add_field(
        name="👢 !كيك [عضو] [السبب اختياري]",
        value="طرد عضو من السيرفر",
        inline=False
    )
    
    embed.add_field(
        name="🗑️ !مسح [العدد]",
        value="مسح عدد محدد من الرسائل",
        inline=False
    )
    
    embed.add_field(
        name="❓ !مساعدة",
        value="عرض هذه القائمة",
        inline=False
    )
    
    embed.set_footer(text="البوت مخصص لإدارة السيرفر")
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ يرجى إدخال جميع المعاملات المطلوبة!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ لم يتم العثور على العضو المحدد!")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ معامل غير صحيح!")
    else:
        await ctx.send(f"❌ حدث خطأ: {str(error)}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ يرجى إضافة DISCORD_TOKEN في متغيرات البيئة")
        print("في Render: اذهب إلى Environment Variables وأضف DISCORD_TOKEN")
    else:
        print("🚀 بدء تشغيل البوت...")
        try:
            bot.run(token)
        except Exception as e:
            print(f"❌ خطأ في تشغيل البوت: {e}")
            print("تأكد من صحة التوكن وصلاحيات البوت") 