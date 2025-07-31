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

bot = commands.Bot(command_prefix='', intents=intents)

async def send_error_message(ctx, message):
    """Send error message to user only in channel"""
    # Send to channel but delete after 5 seconds
    msg = await ctx.send(message)
    await asyncio.sleep(5)
    try:
        await msg.delete()
    except:
        pass

def log_command_usage(ctx, command_name):
    """Log command usage for debugging"""
    print(f"Command used: {command_name} by {ctx.author.name} in {ctx.guild.name}")

def validate_member_permissions(ctx, member):
    """Validate if member can be muted/banned/kicked"""
    if member.bot:
        return False, "لا يمكنك ميوت/حظر/طرد البوتات!"
    if member.guild_permissions.administrator:
        return False, "لا يمكنك ميوت/حظر/طرد المشرفين!"
    if member == ctx.author:
        return False, "لا يمكنك ميوت/حظر/طرد نفسك!"
    return True, ""

def has_admin_permissions(ctx):
    """Check if user has admin role or admin permissions"""
    admin_role = discord.utils.get(ctx.guild.roles, name="ادمن")
    has_admin_role = admin_role and admin_role in ctx.author.roles
    has_admin_permissions = (ctx.author.guild_permissions.administrator or 
                           ctx.author.guild_permissions.manage_roles or 
                           ctx.author.guild_permissions.ban_members or 
                           ctx.author.guild_permissions.kick_members or 
                           ctx.author.guild_permissions.manage_messages)
    return has_admin_role or has_admin_permissions

async def create_muted_role(ctx):
    """Create muted role if it doesn't exist"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        try:
            muted_role = await ctx.guild.create_role(name="Muted", reason="إنشاء دور الميوت")
            for channel in ctx.guild.channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
                elif isinstance(channel, discord.VoiceChannel):
                    await channel.set_permissions(muted_role, speak=False, connect=False)
            return muted_role
        except discord.Forbidden:
            return None
    return muted_role

def format_time_remaining(seconds):
    """Format remaining time in Arabic"""
    if seconds <= 0:
        return "انتهى"
    
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    
    if minutes > 0:
        if remaining_seconds > 0:
            return f"{minutes} دقيقة و {remaining_seconds} ثانية"
        else:
            return f"{minutes} دقيقة"
    else:
        return f"{remaining_seconds} ثانية"

async def get_mute_info(ctx, member):
    """Get mute information from audit logs"""
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            return None, None, None, None
        if muted_role not in member.roles:
            return None, None, None, None
        
        async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=100):
            if entry.target == member:
                for change in entry.changes:
                    if change.key == 'roles':
                        if muted_role in change.after and muted_role not in change.before:
                            # Calculate remaining time based on reason
                            reason = entry.reason or "لا يوجد سبب محدد"
                            duration_minutes = 30  # default
                            
                            # Map reason keywords to durations
                            reason_mapping = {
                                "سب": 30, "شتائم": 30, "اساءة": 60, "استهزاء": 60,
                                "روابط": 120, "اعلانات": 120, "سبام": 45,
                                "تجاهل": 15, "تحذيرات": 15
                            }
                            
                            for keyword, dur in reason_mapping.items():
                                if keyword in reason.lower():
                                    duration_minutes = dur
                                    break
                            
                            # Calculate remaining time
                            mute_time = entry.created_at
                            current_time = datetime.datetime.now(mute_time.tzinfo)
                            elapsed_time = (current_time - mute_time).total_seconds()
                            remaining_time = (duration_minutes * 60) - elapsed_time
                            
                            return reason, entry.user, mute_time, remaining_time
        
        return "غير معروف", None, None, None
    except:
        return "غير معروف", None, None, None

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

@bot.command(name='اسكات')
async def show_mute_options(ctx):
    """عرض خيارات الميوت للمشرفين فقط"""
    
    log_command_usage(ctx, "اسكات")
    
    # Check if user has admin permissions
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ هذا الأمر متاح للأدمن فقط!")
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
    
    embed.set_footer(text="اكتب: اسكت @عضو السبب\nمثال: اسكت @فلان سب")
    embed.set_author(name=f"طلب بواسطة {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='اسكت')
async def mute_member_direct(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """ميوت مباشر مع السبب"""
    
    log_command_usage(ctx, "اسكت")
    
    # Check if user has admin permissions
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ هذا الأمر متاح للأدمن فقط!")
        return
    
    # Validate member permissions
    is_valid, error_message = validate_member_permissions(ctx, member)
    if not is_valid:
        await send_error_message(ctx, f"❌ {error_message}")
        return

    # Map reason keywords to durations
    reason_mapping = {
        "سب": 30,
        "شتائم": 30,
        "اساءة": 60,
        "استهزاء": 60,
        "روابط": 120,
        "اعلانات": 120,
        "سبام": 45,
        "تجاهل": 15,
        "تحذيرات": 15
    }
    
    # Find matching reason and duration
    duration = 30  # default duration
    for keyword, dur in reason_mapping.items():
        if keyword in reason.lower():
            duration = dur
            break
    
    # Find or create muted role
    muted_role = await create_muted_role(ctx)
    if not muted_role:
        await send_error_message(ctx, "❌ لا أملك صلاحيات لإنشاء دور الميوت!")
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
        await send_error_message(ctx, "❌ لا أملك صلاحيات لإضافة دور الميوت!")
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='ميوت')
async def execute_mute(ctx, member: discord.Member, reason_number: int, duration_minutes: int = None):
    """تنفيذ الميوت بناءً على السبب المختار"""
    
    log_command_usage(ctx, "ميوت")
    
    # Check if user has admin permissions
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ هذا الأمر متاح للأدمن فقط!")
        return
    
    # Validate member permissions
    is_valid, error_message = validate_member_permissions(ctx, member)
    if not is_valid:
        await send_error_message(ctx, f"❌ {error_message}")
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
        await send_error_message(ctx, "❌ رقم السبب غير صحيح! استخدم أرقام من 1 إلى 5")
        return
    
    reason, default_duration = reasons[reason_number]
    duration = duration_minutes if duration_minutes else default_duration
    
    # Find or create muted role
    muted_role = await create_muted_role(ctx)
    if not muted_role:
        await send_error_message(ctx, "❌ لا أملك صلاحيات لإنشاء دور الميوت!")
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
        await send_error_message(ctx, "❌ لا أملك صلاحيات لإضافة دور الميوت!")
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='باند')
async def ban_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """حظر عضو من السيرفر"""
    
    log_command_usage(ctx, "باند")
    
    # Check if user has admin permissions
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ هذا الأمر متاح للأدمن فقط!")
        return
    
    # Validate member permissions
    is_valid, error_message = validate_member_permissions(ctx, member)
    if not is_valid:
        await send_error_message(ctx, f"❌ {error_message}")
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
        await send_error_message(ctx, "❌ لا أملك صلاحيات لحظر الأعضاء!")
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='كيك')
async def kick_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """طرد عضو من السيرفر"""
    
    log_command_usage(ctx, "كيك")
    
    # Check if user has admin permissions
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ هذا الأمر متاح للأدمن فقط!")
        return
    
    # Validate member permissions
    is_valid, error_message = validate_member_permissions(ctx, member)
    if not is_valid:
        await send_error_message(ctx, f"❌ {error_message}")
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
        await send_error_message(ctx, "❌ لا أملك صلاحيات لطرد الأعضاء!")
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='مسح')
async def clear_messages(ctx, amount: int):
    """مسح عدد محدد من الرسائل"""
    
    log_command_usage(ctx, "مسح")
    
    # Check if user has admin permissions
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ هذا الأمر متاح للأدمن فقط!")
        return
    
    if amount < 1 or amount > 100:
        await send_error_message(ctx, "❌ يمكنك مسح من 1 إلى 100 رسالة فقط!")
        return

    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
        await ctx.send(f"🗑️ تم مسح {len(deleted) - 1} رسالة", delete_after=5)
        
    except discord.Forbidden:
        await send_error_message(ctx, "❌ لا أملك صلاحيات لمسح الرسائل!")
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='تكلم')
async def unmute_member(ctx, member: discord.Member = None):
    """فك الإسكات عن عضو"""
    
    log_command_usage(ctx, "تكلم")
    
    # If no member specified, unmute the command user
    if member is None:
        member = ctx.author
    
    # Check if user has admin permissions (only required for unmuting others)
    if member != ctx.author and not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ يمكنك فك إسكاتك فقط! للأدمن فك إسكات الآخرين")
        return
    
    # Find muted role
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await send_error_message(ctx, "❌ لا يوجد دور الميوت في السيرفر!")
        return
    
    # Check if member is muted
    if muted_role not in member.roles:
        await send_error_message(ctx, f"❌ {member.mention} ليس مكتوم!")
        return
    
    try:
        await member.remove_roles(muted_role, reason=f"فك الإسكات بواسطة {ctx.author.name}")
        
        embed = discord.Embed(
            title="🔊 تم فك الإسكات بنجاح",
            description=f"تم فك الإسكات عن {member.mention}",
            color=0x00ff00,
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await send_error_message(ctx, "❌ لا أملك صلاحيات لفك الإسكات!")
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='اسكاتي')
async def check_mute_status(ctx, member: discord.Member = None):
    """فحص حالة الإسكات للعضو"""
    
    log_command_usage(ctx, "اسكاتي")
    
    # If no member specified, check the command user
    if member is None:
        member = ctx.author
    
    # Find muted role
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        await send_error_message(ctx, "❌ لا يوجد دور الميوت في السيرفر!")
        return
    
    # Check if member is muted
    if muted_role not in member.roles:
        embed = discord.Embed(
            title="✅ حالة الإسكات",
            description=f"{member.mention} ليس مكتوم",
            color=0x00ff00,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)
        return
    
    # Get mute information
    reason, muted_by, mute_date, remaining_time = await get_mute_info(ctx, member)
    
    if reason is None:
        embed = discord.Embed(
            title="✅ حالة الإسكات",
            description=f"{member.mention} ليس مكتوم",
            color=0x00ff00,
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)
        return
    
    # Format remaining time
    time_remaining = format_time_remaining(int(remaining_time)) if remaining_time is not None else "غير معروف"
    
    embed = discord.Embed(
        title="🔇 حالة الإسكات",
        description=f"{member.mention} مكتوم",
        color=0xff6b6b,
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="السبب", value=reason, inline=True)
    embed.add_field(name="بواسطة", value=muted_by.mention if muted_by else "غير معروف", inline=True)
    embed.add_field(name="الوقت المتبقي", value=time_remaining, inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name='مساعدة')
async def help_command(ctx):
    """عرض قائمة الأوامر المتاحة"""
    
    log_command_usage(ctx, "مساعدة")
    
    # Check if user has admin permissions
    is_admin = has_admin_permissions(ctx)
    
    embed = discord.Embed(
        title="❓ قائمة الأوامر المتاحة",
        description="الأوامر المتاحة لك",
        color=0x00ff00
    )
    
    # Commands for everyone
    embed.add_field(
        name="🔊 تكلم [@عضو اختياري]",
        value="فك الإسكات عن عضو (متاح للجميع لفك إسكاتهم، للأدمن لفك إسكات الآخرين)",
        inline=False
    )
    
    embed.add_field(
        name="🔍 اسكاتي [@عضو اختياري]",
        value="فحص حالة الإسكات للعضو (متاح للجميع)",
        inline=False
    )
    
    # Admin-only commands
    if is_admin:
        embed.add_field(
            name="🔇 اسكات",
            value="عرض خيارات الميوت المتاحة (للأدمن فقط)",
            inline=False
        )
        
        embed.add_field(
            name="🔇 اسكت @عضو السبب",
            value="ميوت مباشر مع السبب (مثال: اسكت @فلان سب) - للأدمن فقط\n⚠️ يجب كتابة السبب بعد منشن العضو",
            inline=False
        )
        
        embed.add_field(
            name="🔇 ميوت @عضو [رقم السبب] [المدة اختياري]",
            value="ميوت عضو مع تحديد السبب والمدة - للأدمن فقط",
            inline=False
        )
        
        embed.add_field(
            name="🔨 باند @عضو [السبب اختياري]",
            value="حظر عضو من السيرفر - للأدمن فقط",
            inline=False
        )
        
        embed.add_field(
            name="👢 كيك @عضو [السبب اختياري]",
            value="طرد عضو من السيرفر - للأدمن فقط",
            inline=False
        )
        
        embed.add_field(
            name="🗑️ مسح [العدد]",
            value="مسح عدد محدد من الرسائل - للأدمن فقط",
            inline=False
        )
    
    embed.add_field(
        name="❓ مساعدة",
        value="عرض هذه القائمة",
        inline=False
    )
    
    embed.set_footer(text="البوت مخصص لإدارة السيرفر")
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    # Ignore errors for commands that don't exist
    if isinstance(error, commands.CommandNotFound):
        return
    
    # Send error message only to the user who used the command
    error_message = "❌ حدث خطأ في تنفيذ الأمر"
    
    if isinstance(error, commands.MissingRequiredArgument):
        error_message = "❌ يرجى إدخال جميع المعاملات المطلوبة!"
    elif isinstance(error, commands.MemberNotFound):
        error_message = "❌ لم يتم العثور على العضو المحدد!"
    elif isinstance(error, commands.BadArgument):
        error_message = "❌ معامل غير صحيح!"
    
    # Send error message to channel but delete after 5 seconds
    msg = await ctx.send(error_message)
    await asyncio.sleep(5)
    try:
        await msg.delete()
    except:
        pass

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