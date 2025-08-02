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
intents.message_content = True
bot = commands.Bot(command_prefix='', intents=intents)

def log_command_usage(ctx, command_name):
    """Log command usage for debugging"""
    print(f"Command '{command_name}' used by {ctx.author} in {ctx.guild}")

def validate_member_permissions(ctx, member):
    """Check if member can be targeted by moderation commands"""
    if member.bot:
        return False, "لا يمكن التصرف مع البوتات"
    if member == ctx.author:
        return False, "لا يمكنك التصرف مع نفسك"
    if member.guild_permissions.administrator:
        return False, "لا يمكن التصرف مع المشرفين"
    return True, None

def has_admin_permissions(ctx):
    """Check if user is owner or has owner role"""
    # Check if user is server owner
    if ctx.author == ctx.guild.owner:
        return True
    
    # Check if user has owner role
    owner_role = discord.utils.get(ctx.guild.roles, name="owner")
    if owner_role and owner_role in ctx.author.roles:
        return True
    
    return False

def is_owner(ctx):
    """Check if user is server owner"""
    return ctx.author == ctx.guild.owner

async def create_muted_role(ctx):
    """Create muted role if it doesn't exist"""
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted", color=discord.Color.dark_gray())
        for channel in ctx.guild.channels:
            if isinstance(channel, discord.TextChannel):
                await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
    return muted_role

def format_time_remaining(seconds):
    """Format time remaining in Arabic"""
    if seconds <= 0:
        return "انتهت المدة"
    
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    
    if minutes > 0 and remaining_seconds > 0:
        return f"{minutes} دقيقة و {remaining_seconds} ثانية"
    elif minutes > 0:
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
        
        # Search for the most recent mute action
        async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=1000):
            if entry.target == member:
                for change in entry.changes:
                    if change.key == 'roles':
                        if muted_role in change.after and muted_role not in change.before:
                            reason = entry.reason or "لا يوجد سبب محدد"
                            if "ميوت بواسطة" in reason:
                                reason_parts = reason.split(" - السبب: ")
                                if len(reason_parts) > 1:
                                    reason = reason_parts[1]
                                else:
                                    reason = reason.replace("ميوت بواسطة", "").strip()
                            
                            reason_mapping = {
                                "سب": 30, "شتائم": 30, "اساءة": 60, "استهزاء": 60,
                                "روابط": 120, "اعلانات": 120, "سبام": 45,
                                "تجاهل": 15, "تحذيرات": 15
                            }
                            duration_minutes = 30  # default
                            for keyword, dur in reason_mapping.items():
                                if keyword in reason.lower():
                                    duration_minutes = dur
                                    break
                            
                            mute_time = entry.created_at
                            current_time = datetime.datetime.now(mute_time.tzinfo)
                            elapsed_time = (current_time - mute_time).total_seconds()
                            remaining_time = (duration_minutes * 60) - elapsed_time
                            
                            return reason, entry.user, mute_time, remaining_time
        
        return "لا يوجد سبب محدد", ctx.guild.me, datetime.datetime.now(), 30 * 60
    except Exception as e:
        print(f"Error in get_mute_info: {e}")
        return "لا يوجد سبب محدد", ctx.guild.me, datetime.datetime.now(), 30 * 60

# Bot commands
@bot.command(name='اسكات')
async def show_mute_info(ctx):
    """Show list of muted members (admin only)"""
    log_command_usage(ctx, 'اسكات')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    # Get muted role
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    
    if not muted_role:
        embed = discord.Embed(
            title="🔇 قائمة الأعضاء المسكات",
            description="لا يوجد أعضاء مسكات حالياً",
            color=discord.Color.green()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return
    
    # Get all muted members
    muted_members = [member for member in ctx.guild.members if muted_role in member.roles]
    
    if not muted_members:
        embed = discord.Embed(
            title="🔇 قائمة الأعضاء المسكات",
            description="لا يوجد أعضاء مسكات حالياً",
            color=discord.Color.green()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return
    
    # Create embed with muted members list
    embed = discord.Embed(
        title="🔇 قائمة الأعضاء المسكات",
        description=f"عدد الأعضاء المسكات: {len(muted_members)}",
        color=discord.Color.red()
    )
    
    # Add each muted member to the embed
    for i, member in enumerate(muted_members, 1):
        embed.add_field(
            name=f"{i}. {member.display_name}",
            value=f"ID: {member.id}\nانضم: {member.joined_at.strftime('%Y-%m-%d') if member.joined_at else 'غير معروف'}",
            inline=True
        )
    
    embed.set_footer(text="استخدم !تكلم @عضو لإلغاء الإسكات")
    
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name='اسكت')
async def mute_member_direct(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """Direct mute with reason (admin only)"""
    log_command_usage(ctx, 'اسكت')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    # Validate member
    can_target, error_msg = validate_member_permissions(ctx, member)
    if not can_target:
        await ctx.respond(f"❌ {error_msg}", ephemeral=True)
        return
    
    try:
        # Create muted role
        muted_role = await create_muted_role(ctx)
        
        # Map reason to duration - نظام أسباب مختصر ومرن
        reason_mapping = {
            # أسباب قصيرة المدى (5-15 دقيقة)
            "سب": 5, "شت": 5, "كلام": 5, "لفظ": 5, "استخدام": 5,
            "تجاهل": 10, "تحذير": 10, "تنبيه": 10,
            "كذب": 15, "دجل": 15, "خداع": 15,
            
            # أسباب متوسطة المدى (20-45 دقيقة)
            "اساءة": 20, "اهانة": 20, "استهزاء": 20,
            "سبام": 30, "تكرار": 30, "مزعج": 30,
            "روابط": 45, "اعلان": 45, "دعاية": 45,
            
            # أسباب طويلة المدى (60-120 دقيقة)
            "مخالفة": 60, "قاعدة": 60, "خطأ": 60,
            "مشكلة": 90, "مخالفة خطيرة": 90,
            "حظر مؤقت": 120, "مخالفة كبيرة": 120,
            "نقاشات": 60, "سياسة": 60, "ديني": 60
        }
        
        # تحديد المدة بناءً على أول كلمة في السبب
        duration = 15  # مدة افتراضية
        matched_reason = "مخالفة عامة"
        
        # تقسيم السبب إلى كلمات والبحث عن أول كلمة مطابقة
        reason_words = reason.lower().split()
        
        for word in reason_words:
            for keyword, dur in reason_mapping.items():
                if keyword in word or word in keyword:
                    duration = dur
                    matched_reason = keyword
                    break
            if matched_reason != "مخالفة عامة":
                break
        
        # Apply mute
        await member.add_roles(muted_role, reason=f"ميوت بواسطة {ctx.author} - السبب: {reason}")
        
        # Create embed
        embed = discord.Embed(
            title="✅ تم الإسكات بنجاح",
            description=f"تم إسكات {member.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="السبب", value=f"{matched_reason} ({reason})", inline=True)
        embed.add_field(name="المدة", value=f"{duration} دقيقة", inline=True)
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.set_footer(text=f"سيتم إلغاء الإسكات تلقائياً بعد {duration} دقيقة")
        
        await ctx.respond(embed=embed, ephemeral=True)
        
        # Schedule unmute
        async def unmute_after_duration():
            await asyncio.sleep(duration * 60)
            try:
                if muted_role in member.roles:
                    await member.remove_roles(muted_role, reason="انتهاء مدة الميوت")
                    await ctx.send(f"✅ تم إلغاء ميوت {member.mention} بعد انتهاء المدة")
            except Exception as e:
                print(f"Error in unmute task: {e}")
        
        asyncio.create_task(unmute_after_duration())
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='تكلم')
async def unmute_member(ctx, member: discord.Member):
    """Unmute member (admin only)"""
    log_command_usage(ctx, 'تكلم')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            await ctx.respond("❌ لا يوجد دور 'Muted' في السيرفر", ephemeral=True)
            return
        
        if muted_role not in member.roles:
            await ctx.respond(f"❌ {member.mention} غير مكتوم أصلاً", ephemeral=True)
            return
        
        await member.remove_roles(muted_role, reason=f"إلغاء ميوت بواسطة {ctx.author}")
        
        embed = discord.Embed(
            title="✅ تم إلغاء الإسكات",
            description=f"تم إلغاء إسكات {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        
        await ctx.respond(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='اسكاتي')
async def check_mute_status(ctx, member: discord.Member = None):
    """Check mute status (owner only)"""
    log_command_usage(ctx, 'اسكاتي')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    if not member:
        member = ctx.author
    
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        embed = discord.Embed(
            title="🔊 حالة الإسكات",
            description=f"{member.mention} غير مكتوم",
            color=discord.Color.green()
        )
        await ctx.respond(embed=embed, ephemeral=True)
        return
    
    # Get mute info
    reason, muter, mute_time, remaining_time = await get_mute_info(ctx, member)
    
    embed = discord.Embed(
        title="🔇 حالة الإسكات",
        description=f"{member.mention} مكتوم",
        color=discord.Color.red()
    )
    embed.add_field(name="السبب", value=reason, inline=True)
    embed.add_field(name="بواسطة", value=muter.mention if muter else "غير معروف", inline=True)
    embed.add_field(name="الوقت المتبقي", value=format_time_remaining(remaining_time), inline=True)
    
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name='مساعدة')
async def help_command(ctx):
    """Show help information (owner only)"""
    log_command_usage(ctx, 'مساعدة')
    
    if not is_owner(ctx):
        await ctx.respond("❌ هذا الأمر متاح لأونر السيرفر فقط", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🤖 أوامر بوت FSociety",
        description="قائمة بجميع الأوامر المتاحة",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎭 أوامر الإدارة",
        value="""
`اسكت @عضو السبب` - إسكات العضو (أول كلمة من السبب)
`تكلم @عضو` - إلغاء إسكات العضو
`اسكات` - عرض قائمة الأعضاء المسكات
`اسباب` - عرض قائمة الأسباب المتاحة
`باند @عضو السبب` - حظر العضو
`كيك @عضو السبب` - طرد العضو
`مسح عدد` - حذف رسائل محددة
`مسح الكل` - حذف جميع الرسائل
`مساعدة` - عرض هذه القائمة
`حالة` - فحص حالة البوت
        """,
        inline=False
    )
    
    embed.add_field(
        name="👑 أوامر الأونر",
        value="""
`اضافة @عضو` - إضافة رتبة الأونر
`حذف @عضو` - إزالة رتبة الأونر
        """,
        inline=False
    )
    
    embed.add_field(
        name="🔇 نظام الأسباب المختصرة",
        value="""
**قصيرة المدى (5-15 دقيقة):**
`سب` `شت` `كلام` `لفظ` `استخدام` (5 دقائق)
`تجاهل` `تحذير` `تنبيه` (10 دقائق)
`كذب` `دجل` `خداع` (15 دقيقة)

**متوسطة المدى (20-45 دقيقة):**
`اساءة` `اهانة` `استهزاء` (20 دقيقة)
`سبام` `تكرار` `مزعج` (30 دقيقة)
`روابط` `اعلان` `دعاية` (45 دقيقة)

**طويلة المدى (60-120 دقيقة):**
`مخالفة` `قاعدة` `خطأ` `نقاشات` `سياسة` `ديني` (60 دقيقة)
`مشكلة` `مخالفة خطيرة` (90 دقيقة)
`حظر مؤقت` `مخالفة كبيرة` (120 دقيقة)
        """,
        inline=False
    )
    
    embed.add_field(
        name="📝 ملاحظات",
        value="""
• جميع الأوامر تحتاج صلاحيات الأونر
• اكتب الأمر مباشرة بدون بادئة
• الأوامر تعمل باللغة العربية فقط
• اكتب أول كلمة من السبب فقط
        """,
        inline=False
    )
    
    embed.set_footer(text="FSociety Bot v1.0")
    
    # إرسال الرسالة كخاصة للأونر فقط
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name='حالة')
async def bot_status(ctx):
    """Check bot status"""
    log_command_usage(ctx, 'حالة')
    
    embed = discord.Embed(
        title="🤖 حالة البوت",
        color=discord.Color.green()
    )
    
    embed.add_field(name="الحالة", value="🟢 متصل", inline=True)
    embed.add_field(name="الاستجابة", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="عدد السيرفرات", value=len(bot.guilds), inline=True)
    embed.add_field(name="وقت التشغيل", value="متصل", inline=True)
    
    await ctx.respond(embed=embed, ephemeral=True)

@bot.command(name='باند')
async def ban_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """Ban member (admin only)"""
    log_command_usage(ctx, 'باند')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    # Validate member
    can_target, error_msg = validate_member_permissions(ctx, member)
    if not can_target:
        await ctx.respond(f"❌ {error_msg}", ephemeral=True)
        return
    
    try:
        await member.ban(reason=f"حظر بواسطة {ctx.author} - السبب: {reason}")
        
        embed = discord.Embed(
            title="🔨 تم الحظر بنجاح",
            description=f"تم حظر {member.mention}",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        
        await ctx.respond(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='كيك')
async def kick_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """Kick member (admin only)"""
    log_command_usage(ctx, 'كيك')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    # Validate member
    can_target, error_msg = validate_member_permissions(ctx, member)
    if not can_target:
        await ctx.respond(f"❌ {error_msg}", ephemeral=True)
        return
    
    try:
        await member.kick(reason=f"طرد بواسطة {ctx.author} - السبب: {reason}")
        
        embed = discord.Embed(
            title="👢 تم الطرد بنجاح",
            description=f"تم طرد {member.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        
        await ctx.respond(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='مسح')
async def clear_messages(ctx, amount: int = 5):
    """Clear messages (admin only)"""
    log_command_usage(ctx, 'مسح')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    if amount < 1 or amount > 100:
        await ctx.respond("❌ يرجى تحديد عدد بين 1 و 100", ephemeral=True)
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
        
        embed = discord.Embed(
            title="🗑️ تم الحذف بنجاح",
            description=f"تم حذف {len(deleted) - 1} رسالة",
            color=discord.Color.green()
        )
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.add_field(name="العدد المطلوب", value=amount, inline=True)
        
        await ctx.respond(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='مسح الكل')
async def clear_all_messages(ctx):
    """Clear all messages in channel (admin only)"""
    log_command_usage(ctx, 'مسح الكل')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    try:
        # Get channel history to count messages
        messages = []
        async for message in ctx.channel.history(limit=None):
            messages.append(message)
        
        # Delete all messages except pinned ones
        deleted = await ctx.channel.purge(limit=None, check=lambda m: not m.pinned)
        
        embed = discord.Embed(
            title="🗑️ تم حذف جميع الرسائل",
            description=f"تم حذف {len(deleted)} رسالة",
            color=discord.Color.red()
        )
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.add_field(name="الرسائل المثبتة", value="لم يتم حذفها", inline=True)
        
        await ctx.respond(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='اضافة')
async def add_role(ctx, member: discord.Member):
    """Add owner role to member (owner only)"""
    log_command_usage(ctx, 'اضافة')
    
    if not is_owner(ctx):
        await ctx.respond("❌ هذا الأمر متاح لأونر السيرفر فقط", ephemeral=True)
        return
    
    try:
        # Get or create owner role
        owner_role = discord.utils.get(ctx.guild.roles, name="owner")
        if not owner_role:
            owner_role = await ctx.guild.create_role(
                name="owner",
                color=discord.Color.gold(),
                reason="إنشاء رتبة الأونر بواسطة البوت"
            )
        
        # Add role to member
        await member.add_roles(owner_role, reason=f"إضافة رتبة الأونر بواسطة {ctx.author}")
        
        embed = discord.Embed(
            title="✅ تم إضافة الرتبة بنجاح",
            description=f"تم إضافة رتبة الأونر لـ {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.add_field(name="الرتبة", value=owner_role.mention, inline=True)
        
        await ctx.respond(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='حذف')
async def remove_role(ctx, member: discord.Member):
    """Remove owner role from member (owner only)"""
    log_command_usage(ctx, 'حذف')
    
    if not is_owner(ctx):
        await ctx.respond("❌ هذا الأمر متاح لأونر السيرفر فقط", ephemeral=True)
        return
    
    try:
        # Get owner role
        owner_role = discord.utils.get(ctx.guild.roles, name="owner")
        if not owner_role:
            await ctx.respond("❌ رتبة الأونر غير موجودة", ephemeral=True)
            return
        
        # Check if member has the role
        if owner_role not in member.roles:
            await ctx.respond("❌ هذا العضو لا يملك رتبة الأونر", ephemeral=True)
            return
        
        # Remove role from member
        await member.remove_roles(owner_role, reason=f"إزالة رتبة الأونر بواسطة {ctx.author}")
        
        embed = discord.Embed(
            title="✅ تم إزالة الرتبة بنجاح",
            description=f"تم إزالة رتبة الأونر من {member.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.add_field(name="الرتبة", value=owner_role.mention, inline=True)
        
        await ctx.respond(embed=embed, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if hasattr(error, 'original') or hasattr(error, 'handled'):
        return
    if isinstance(error, (commands.MissingRequiredArgument, commands.MemberNotFound, commands.BadArgument)):
        return
    
    # Log the error for debugging
    print(f"❌ خطأ في الأمر '{ctx.command}' بواسطة {ctx.author}: {error}")
    
    error_message = "❌ حدث خطأ في تنفيذ الأمر"
    try:
        await ctx.respond(error_message, ephemeral=True)
    except:
        try:
            await ctx.send(error_message)
        except:
            pass

# Bot events
@bot.event
async def on_ready():
    print(f'✅ {bot.user} تم تسجيل الدخول بنجاح!')
    print(f'🆔 Bot ID: {bot.user.id}')
    print(f'📊 عدد السيرفرات: {len(bot.guilds)}')

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Debug: Log all messages to see what's happening
    print(f"📝 رسالة من {message.author}: {message.content}")
    
    # Check if message starts with any command (without prefix)
    content = message.content.strip()
    
    # Handle commands directly
    if content == 'مساعدة':
        await help_command_direct(message)
    elif content == 'حالة':
        await status_command_direct(message)
    elif content.startswith('اسكت'):
        await handle_mute_command(message)
    elif content.startswith('تكلم'):
        await handle_unmute_command(message)
    elif content == 'اسكات':
        await handle_mute_list_command(message)
    elif content == 'اسباب':
        await handle_mute_reasons_command(message)
    elif content.startswith('باند'):
        await handle_ban_command(message)
    elif content.startswith('كيك'):
        await handle_kick_command(message)
    elif content.startswith('مسح'):
        await handle_clear_command(message)
    elif content.startswith('اضافة رتبة'):
        await handle_add_custom_role_command(message)
    elif content.startswith('حذف رتبة'):
        await handle_remove_custom_role_command(message)
    elif content.startswith('اضافة لي'):
        await handle_add_role_to_self_command(message)
    elif content.startswith('إنشاء رتبة'):
        await handle_create_admin_role_command(message)
    elif content.startswith('اضافة'):
        await handle_add_role_command(message)
    elif content.startswith('حذف'):
        await handle_remove_role_command(message)
    
    # Process commands normally as fallback
    await bot.process_commands(message)

# Direct command handlers
async def help_command_direct(message):
    """Show help information directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ هذا الأمر متاح لأونر السيرفر فقط")
        return
    
    embed = discord.Embed(
        title="🤖 أوامر بوت FSociety",
        description="قائمة بجميع الأوامر المتاحة",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎭 أوامر الإدارة",
        value="""
`اسكت @عضو السبب` - إسكات العضو (مع مدة تلقائية)
`تكلم @عضو` - إلغاء إسكات العضو
`اسكات` - عرض قائمة الأعضاء المسكات
`اسباب` - عرض قائمة الأسباب والمدة
`باند @عضو السبب` - حظر العضو
`كيك @عضو السبب` - طرد العضو
`مسح عدد` - حذف رسائل محددة
`مساعدة` - عرض هذه القائمة
`حالة` - فحص حالة البوت
        """,
        inline=False
    )
    
    embed.add_field(
        name="👑 أوامر الأونر",
        value="""
`اضافة @عضو` - إضافة رتبة الأونر
`حذف @عضو` - إزالة رتبة الأونر
`اضافة رتبة @عضو @الرتبة` - إضافة رتبة مخصصة
`حذف رتبة @عضو @الرتبة` - إزالة رتبة مخصصة
`اضافة لي @الرتبة` - إضافة رتبة لنفسك
`إنشاء رتبة اسم_الرتبة` - إنشاء رتبة إدارية جديدة
        """,
        inline=False
    )
    
    embed.set_footer(text="FSociety Bot v1.0")
    await message.channel.send(embed=embed)

async def status_command_direct(message):
    """Check bot status directly"""
    embed = discord.Embed(
        title="🤖 حالة البوت",
        color=discord.Color.green()
    )
    
    embed.add_field(name="الحالة", value="🟢 متصل", inline=True)
    embed.add_field(name="الاستجابة", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="عدد السيرفرات", value=len(bot.guilds), inline=True)
    
    await message.channel.send(embed=embed)

def is_owner_direct(message):
    """Check if user is server owner or has admin role"""
    # Check if user is server owner
    if message.author == message.guild.owner:
        return True
    
    # Check if user has owner role
    owner_role = discord.utils.get(message.guild.roles, name="owner")
    if owner_role and owner_role in message.author.roles:
        return True
    
    # Check if user has admin role (any role with admin permissions)
    admin_roles = ["admin", "Admin", "ADMIN", "مشرف", "مدير", "أدمن"]
    for role_name in admin_roles:
        admin_role = discord.utils.get(message.guild.roles, name=role_name)
        if admin_role and admin_role in message.author.roles:
            return True
    
    # Check if user has any role with admin permissions
    for role in message.author.roles:
        if role.permissions.administrator or role.permissions.manage_guild:
            return True
    
    return False

async def handle_mute_command(message):
    """Handle mute command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ ليس لديك صلاحيات كافية")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `اسكت @عضو السبب`")
        return
    
    try:
        member = message.mentions[0]
        parts = message.content.split()
        reason = " ".join(parts[2:]) if len(parts) > 2 else "لا يوجد سبب محدد"
        
        # Define mute reasons with durations
        mute_reasons = {
            "التحدث في روم غير مخصص": {"duration": 10, "description": "⏱️ مدة الإسكات: 10 دقائق\n🔹 للتنبيه والتهذيب فقط."},
            "السبام أو التكرار المزعج": {"duration": 30, "description": "⏱️ مدة الإسكات: 30 دقيقة\n🔹 كنوع من التحذير الجاد دون الطرد."},
            "استخدام ألفاظ غير لائقة": {"duration": 60, "description": "⏱️ مدة الإسكات: 1 ساعة\n🔹 إذا تم التنبيه ولم يستجب."},
            "مزاح ثقيل": {"duration": 60, "description": "⏱️ مدة الإسكات: 1 ساعة\n🔹 إذا تم التنبيه ولم يستجب."},
            "إثارة الفتن": {"duration": 120, "description": "⏱️ مدة الإسكات: 2 ساعة\n🔹 إذا تسبب بفوضى أو استفزاز عام."},
            "الجدال المفرط": {"duration": 120, "description": "⏱️ مدة الإسكات: 2 ساعة\n🔹 إذا تسبب بفوضى أو استفزاز عام."},
            "نشر روابط ممنوعة": {"duration": 240, "description": "⏱️ مدة الإسكات: 4 ساعات\n🔹 إذا كانت الروابط غير آمنة أو دعائية."},
            "محتوى مخالف": {"duration": 240, "description": "⏱️ مدة الإسكات: 4 ساعات\n🔹 إذا كانت الروابط غير آمنة أو دعائية."},
            "الاستهزاء": {"duration": 360, "description": "⏱️ مدة الإسكات: 6 ساعات\n🔹 خصوصًا إذا كان متكرر أو مؤثر على العضو المتضرر."},
            "التنمر": {"duration": 360, "description": "⏱️ مدة الإسكات: 6 ساعات\n🔹 خصوصًا إذا كان متكرر أو مؤثر على العضو المتضرر."},
            "مخالفة قرارات الإدارة": {"duration": 720, "description": "⏱️ مدة الإسكات: 12 ساعة\n🔹 تعكس عدم احترام الطاقم الإداري."},
            "التحدي المتعمد": {"duration": 720, "description": "⏱️ مدة الإسكات: 12 ساعة\n🔹 تعكس عدم احترام الطاقم الإداري."},
            "الاسم غير اللائق": {"duration": 60, "description": "⏱️ مدة الإسكات: 1 ساعة\n🔹 يُطلب منه التعديل، ثم يُفك الإسكات."},
            "الصورة غير اللائقة": {"duration": 60, "description": "⏱️ مدة الإسكات: 1 ساعة\n🔹 يُطلب منه التعديل، ثم يُفك الإسكات."},
            "نقاشات دينية": {"duration": 1440, "description": "⏱️ مدة الإسكات: 24 ساعة\n🔹 إذا كانت مثيرة للفتن أو تخالف قوانين السيرفر."},
            "نقاشات سياسية": {"duration": 1440, "description": "⏱️ مدة الإسكات: 24 ساعة\n🔹 إذا كانت مثيرة للفتن أو تخالف قوانين السيرفر."},
            "تكرار المخالفة": {"duration": 4320, "description": "⏱️ مدة الإسكات: 3 أيام\n🔹 بحسب نوع المخالفة وتكرارها."}
        }
        
        # Find matching reason and get duration
        mute_duration = None
        mute_description = ""
        
        for reason_key, reason_info in mute_reasons.items():
            if reason_key in reason:
                mute_duration = reason_info["duration"]
                mute_description = reason_info["description"]
                break
        
        # If no specific reason found, use default
        if mute_duration is None:
            mute_duration = 30  # Default 30 minutes
            mute_description = "⏱️ مدة الإسكات: 30 دقيقة\n🔹 سبب غير محدد."
        
        # Create muted role if it doesn't exist
        muted_role = discord.utils.get(message.guild.roles, name="Muted")
        if not muted_role:
            muted_role = await message.guild.create_role(name="Muted", color=discord.Color.dark_gray())
            for channel in message.guild.channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
        
        await member.add_roles(muted_role, reason=f"ميوت بواسطة {message.author} - السبب: {reason}")
        
        # Create embed with duration information
        embed = discord.Embed(
            title="🔇 تم الإسكات بنجاح",
            description=f"تم إسكات {member.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        embed.add_field(name="المدة", value=f"{mute_duration} دقيقة", inline=True)
        embed.add_field(name="التفاصيل", value=mute_description, inline=False)
        
        await message.channel.send(embed=embed)
        
        # Send report to mute-log channel
        await send_mute_report(message.guild, member, reason, message.author, mute_duration, mute_description)
        
        # Schedule unmute after duration
        if mute_duration > 0:
            async def unmute_after_duration():
                await asyncio.sleep(mute_duration * 60)  # Convert minutes to seconds
                try:
                    if muted_role in member.roles:
                        await member.remove_roles(muted_role, reason="انتهت مدة الإسكات تلقائياً")
                        
                        unmute_embed = discord.Embed(
                            title="🔊 تم إلغاء الإسكات تلقائياً",
                            description=f"تم إلغاء إسكات {member.mention} بعد انتهاء المدة",
                            color=discord.Color.green()
                        )
                        unmute_embed.add_field(name="المدة", value=f"{mute_duration} دقيقة", inline=True)
                        
                        await message.channel.send(embed=unmute_embed)
                        
                        # Send unmute report to mute-log
                        await send_unmute_report(message.guild, member, mute_duration)
                except Exception as e:
                    print(f"Error in auto-unmute: {e}")
            
            # Start the unmute task
            asyncio.create_task(unmute_after_duration())
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_unmute_command(message):
    """Handle unmute command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ ليس لديك صلاحيات كافية")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `تكلم @عضو`")
        return
    
    try:
        member = message.mentions[0]
        muted_role = discord.utils.get(message.guild.roles, name="Muted")
        
        if not muted_role or muted_role not in member.roles:
            await message.channel.send("❌ هذا العضو غير مسكات")
            return
        
        await member.remove_roles(muted_role, reason=f"إلغاء إسكات بواسطة {message.author}")
        
        embed = discord.Embed(
            title="🔊 تم إلغاء الإسكات بنجاح",
            description=f"تم إلغاء إسكات {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
        # Send manual unmute report to mute-log
        await send_manual_unmute_report(message.guild, member, message.author)
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_mute_list_command(message):
    """Handle mute list command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ ليس لديك صلاحيات كافية")
        return
    
    muted_role = discord.utils.get(message.guild.roles, name="Muted")
    if not muted_role:
        await message.channel.send("❌ لا توجد رتبة Muted")
        return
    
    muted_members = [member for member in message.guild.members if muted_role in member.roles]
    
    if not muted_members:
        await message.channel.send("✅ لا يوجد أعضاء مسكات حالياً")
        return
    
    embed = discord.Embed(
        title="🔇 قائمة الأعضاء المسكات",
        color=discord.Color.orange()
    )
    
    member_list = "\n".join([f"• {member.mention}" for member in muted_members])
    embed.add_field(name="الأعضاء المسكات", value=member_list, inline=False)
    
    await message.channel.send(embed=embed)

async def handle_ban_command(message):
    """Handle ban command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ ليس لديك صلاحيات كافية")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `باند @عضو السبب`")
        return
    
    try:
        member = message.mentions[0]
        parts = message.content.split()
        reason = " ".join(parts[2:]) if len(parts) > 2 else "لا يوجد سبب محدد"
        
        await member.ban(reason=f"حظر بواسطة {message.author} - السبب: {reason}")
        
        embed = discord.Embed(
            title="🔨 تم الحظر بنجاح",
            description=f"تم حظر {member.mention}",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_kick_command(message):
    """Handle kick command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ ليس لديك صلاحيات كافية")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `كيك @عضو السبب`")
        return
    
    try:
        member = message.mentions[0]
        parts = message.content.split()
        reason = " ".join(parts[2:]) if len(parts) > 2 else "لا يوجد سبب محدد"
        
        await member.kick(reason=f"طرد بواسطة {message.author} - السبب: {reason}")
        
        embed = discord.Embed(
            title="👢 تم الطرد بنجاح",
            description=f"تم طرد {member.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_clear_command(message):
    """Handle clear command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ ليس لديك صلاحيات كافية")
        return
    
    parts = message.content.split()
    
    # Check if it's "مسح الكل" command
    if len(parts) > 1 and parts[1] == "الكل":
        try:
            # Delete all messages in the channel
            deleted = await message.channel.purge(limit=None)
            
            embed = discord.Embed(
                title="🧹 تم حذف جميع الرسائل بنجاح",
                description=f"تم حذف {len(deleted)} رسالة",
                color=discord.Color.green()
            )
            
            await message.channel.send(embed=embed, delete_after=5)
            return
            
        except Exception as e:
            await message.channel.send(f"❌ حدث خطأ: {str(e)}")
            return
    
    # Regular clear command
    amount = 5  # default
    
    if len(parts) > 1:
        try:
            amount = int(parts[1])
            if amount > 100:
                amount = 100
        except ValueError:
            amount = 5
    
    try:
        deleted = await message.channel.purge(limit=amount + 1)  # +1 to include command message
        
        embed = discord.Embed(
            title="🧹 تم الحذف بنجاح",
            description=f"تم حذف {len(deleted) - 1} رسالة",
            color=discord.Color.green()
        )
        
        await message.channel.send(embed=embed, delete_after=5)
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_add_role_command(message):
    """Handle add role command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ هذا الأمر متاح لأونر السيرفر فقط")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `اضافة @عضو`")
        return
    
    try:
        member = message.mentions[0]
        owner_role = discord.utils.get(message.guild.roles, name="owner")
        
        if not owner_role:
            owner_role = await message.guild.create_role(name="owner", color=discord.Color.gold())
        
        if owner_role in member.roles:
            await message.channel.send("❌ هذا العضو يملك رتبة الأونر بالفعل")
            return
        
        await member.add_roles(owner_role, reason=f"إضافة رتبة الأونر بواسطة {message.author}")
        
        embed = discord.Embed(
            title="✅ تم إضافة الرتبة بنجاح",
            description=f"تم إضافة رتبة الأونر لـ {member.mention}",
            color=discord.Color.gold()
        )
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        embed.add_field(name="الرتبة", value=owner_role.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_remove_role_command(message):
    """Handle remove role command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ هذا الأمر متاح لأونر السيرفر فقط")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `حذف @عضو`")
        return
    
    try:
        member = message.mentions[0]
        owner_role = discord.utils.get(message.guild.roles, name="owner")
        
        if not owner_role or owner_role not in member.roles:
            await message.channel.send("❌ هذا العضو لا يملك رتبة الأونر")
            return
        
        await member.remove_roles(owner_role, reason=f"إزالة رتبة الأونر بواسطة {message.author}")
        
        embed = discord.Embed(
            title="✅ تم إزالة الرتبة بنجاح",
            description=f"تم إزالة رتبة الأونر من {member.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        embed.add_field(name="الرتبة", value=owner_role.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_add_custom_role_command(message):
    """Handle add custom role command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ هذا الأمر متاح لأونر السيرفر فقط")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `اضافة رتبة @عضو @الرتبة`\nمثال: `اضافة رتبة @أحمد @VIP`")
        return
    
    # Check if there are role mentions
    if not message.role_mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `اضافة رتبة @عضو @الرتبة`\nمثال: `اضافة رتبة @أحمد @VIP`")
        return
    
    try:
        member = message.mentions[0]
        role = message.role_mentions[0]
        
        # Check if bot has permissions to manage roles
        if not message.guild.me.guild_permissions.manage_roles:
            await message.channel.send("❌ البوت لا يملك صلاحيات إدارة الرتب")
            return
        
        # Check if the role is manageable by the bot
        if role.position >= message.guild.me.top_role.position:
            await message.channel.send("❌ لا يمكن إضافة رتبة أعلى من رتبة البوت")
            return
        
        if role in member.roles:
            await message.channel.send("❌ هذا العضو يملك الرتبة بالفعل")
            return
        
        await member.add_roles(role, reason=f"إضافة رتبة بواسطة {message.author}")
        
        embed = discord.Embed(
            title="✅ تم إضافة الرتبة بنجاح",
            description=f"تم إضافة رتبة {role.mention} لـ {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        embed.add_field(name="الرتبة", value=role.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except discord.Forbidden:
        await message.channel.send("❌ البوت لا يملك صلاحيات كافية لإضافة هذه الرتبة")
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_remove_custom_role_command(message):
    """Handle remove custom role command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ هذا الأمر متاح لأونر السيرفر فقط")
        return
    
    # Check if there are mentions
    if not message.mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `حذف رتبة @عضو @الرتبة`")
        return
    
    # Check if there are role mentions
    if not message.role_mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `حذف رتبة @عضو @الرتبة`")
        return
    
    try:
        member = message.mentions[0]
        role = message.role_mentions[0]
        
        # Check if bot has permissions to manage roles
        if not message.guild.me.guild_permissions.manage_roles:
            await message.channel.send("❌ البوت لا يملك صلاحيات إدارة الرتب")
            return
        
        # Check if the role is manageable by the bot
        if role.position >= message.guild.me.top_role.position:
            await message.channel.send("❌ لا يمكن إزالة رتبة أعلى من رتبة البوت")
            return
        
        if role not in member.roles:
            await message.channel.send("❌ هذا العضو لا يملك هذه الرتبة")
            return
        
        await member.remove_roles(role, reason=f"إزالة رتبة بواسطة {message.author}")
        
        embed = discord.Embed(
            title="✅ تم إزالة الرتبة بنجاح",
            description=f"تم إزالة رتبة {role.mention} من {member.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        embed.add_field(name="الرتبة", value=role.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except discord.Forbidden:
        await message.channel.send("❌ البوت لا يملك صلاحيات كافية لإزالة هذه الرتبة")
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_mute_reasons_command(message):
    """Handle mute reasons command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ ليس لديك صلاحيات كافية")
        return
    
    embed = discord.Embed(
        title="🔇 نظام الأسباب المختصرة",
        description="اكتب أول كلمة من السبب فقط - مثال: `اسكت @عضو نقاشات`",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📌 أسباب قصيرة المدى (5-15 دقيقة)",
        value="""
**5 دقائق:** `سب` `شت` `كلام` `لفظ` `استخدام`
**10 دقائق:** `تجاهل` `تحذير` `تنبيه`
**15 دقيقة:** `كذب` `دجل` `خداع`
        """,
        inline=False
    )
    
    embed.add_field(
        name="📌 أسباب متوسطة المدى (20-45 دقيقة)",
        value="""
**20 دقيقة:** `اساءة` `اهانة` `استهزاء`
**30 دقيقة:** `سبام` `تكرار` `مزعج`
**45 دقيقة:** `روابط` `اعلان` `دعاية`
        """,
        inline=False
    )
    
    embed.add_field(
        name="📌 أسباب طويلة المدى (60-120 دقيقة)",
        value="""
**60 دقيقة:** `مخالفة` `قاعدة` `خطأ` `نقاشات` `سياسة` `ديني`
**90 دقيقة:** `مشكلة` `مخالفة خطيرة`
**120 دقيقة:** `حظر مؤقت` `مخالفة كبيرة`
        """,
        inline=False
    )
    
    embed.add_field(
        name="💡 أمثلة على الاستخدام",
        value="""
`اسكت @عضو نقاشات` → 60 دقيقة
`اسكت @عضو استخدام الفاظ` → 5 دقائق
`اسكت @عضو سبام` → 30 دقيقة
`اسكت @عضو مخالفة` → 60 دقيقة
        """,
        inline=False
    )
    
    embed.set_footer(text="💡 اكتب أول كلمة من السبب فقط!")
    
    await message.channel.send(embed=embed)

async def handle_add_role_to_self_command(message):
    """Handle add role to self command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ هذا الأمر متاح لأونر السيرفر فقط")
        return
    
    # Check if there are role mentions
    if not message.role_mentions:
        await message.channel.send("❌ الاستخدام الصحيح: `اضافة لي @الرتبة`\nمثال: `اضافة لي @VIP`")
        return
    
    try:
        member = message.author
        role = message.role_mentions[0]
        
        # Check if bot has permissions to manage roles
        if not message.guild.me.guild_permissions.manage_roles:
            await message.channel.send("❌ البوت لا يملك صلاحيات إدارة الرتب")
            return
        
        # Check if the role is manageable by the bot
        if role.position >= message.guild.me.top_role.position:
            await message.channel.send("❌ لا يمكن إضافة رتبة أعلى من رتبة البوت")
            return
        
        if role in member.roles:
            await message.channel.send("❌ تملك هذه الرتبة بالفعل")
            return
        
        await member.add_roles(role, reason=f"إضافة رتبة لنفسه بواسطة {message.author}")
        
        embed = discord.Embed(
            title="✅ تم إضافة الرتبة بنجاح",
            description=f"تم إضافة رتبة {role.mention} لـ {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        embed.add_field(name="الرتبة", value=role.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except discord.Forbidden:
        await message.channel.send("❌ البوت لا يملك صلاحيات كافية لإضافة هذه الرتبة")
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def handle_create_admin_role_command(message):
    """Handle create admin role command directly"""
    if not is_owner_direct(message):
        await message.channel.send("❌ هذا الأمر متاح لأونر السيرفر فقط")
        return
    
    # Parse command: إنشاء رتبة اسم_الرتبة
    parts = message.content.split()
    if len(parts) < 3:
        await message.channel.send("❌ الاستخدام الصحيح: `إنشاء رتبة اسم_الرتبة`\nمثال: `إنشاء رتبة مشرف`")
        return
    
    try:
        role_name = " ".join(parts[2:])  # Get the role name
        existing_role = discord.utils.get(message.guild.roles, name=role_name)
        
        if existing_role:
            await message.channel.send(f"❌ الرتبة '{role_name}' موجودة بالفعل")
            return
        
        # Create admin role with permissions
        admin_role = await message.guild.create_role(
            name=role_name,
            color=discord.Color.blue(),
            permissions=discord.Permissions(
                manage_messages=True,
                kick_members=True,
                ban_members=True,
                manage_roles=True,
                manage_channels=True,
                view_audit_log=True,
                send_messages=True,
                read_messages=True
            )
        )
        
        embed = discord.Embed(
            title="✅ تم إنشاء الرتبة الإدارية بنجاح",
            description=f"تم إنشاء رتبة {admin_role.mention}",
            color=discord.Color.blue()
        )
        embed.add_field(name="اسم الرتبة", value=role_name, inline=True)
        embed.add_field(name="الصلاحيات", value="إدارية كاملة", inline=True)
        embed.add_field(name="بواسطة", value=message.author.mention, inline=True)
        
        await message.channel.send(embed=embed)
        
    except Exception as e:
        await message.channel.send(f"❌ حدث خطأ: {str(e)}")

async def send_mute_report(guild, member, reason, admin, duration, description):
    """Send mute report to mute-log channel"""
    try:
        # Find mute-log channel
        mute_log_channel = discord.utils.get(guild.channels, name="mute-log")
        
        if not mute_log_channel:
            print("❌ روم mute-log غير موجود")
            return
        
        # Get current date in Arabic
        current_date = datetime.datetime.now().strftime("%d-%B-%Y")
        
        # Convert duration to readable format
        if duration >= 1440:  # 24 hours or more
            duration_text = f"{duration // 1440} يوم"
        elif duration >= 60:  # 1 hour or more
            duration_text = f"{duration // 60} ساعة"
        else:
            duration_text = f"{duration} دقيقة"
        
        # Create report embed
        report_embed = discord.Embed(
            title="🛑 تقرير إسكات جديد",
            color=discord.Color.red()
        )
        
        report_embed.add_field(name="👤 المستخدم", value=member.mention, inline=True)
        report_embed.add_field(name="⏱️ المدة", value=duration_text, inline=True)
        report_embed.add_field(name="📄 السبب", value=reason, inline=True)
        report_embed.add_field(name="📝 بواسطة", value=admin.mention, inline=True)
        report_embed.add_field(name="📅 التاريخ", value=current_date, inline=True)
        report_embed.add_field(name="📍 الروم", value=admin.voice.channel.name if admin.voice and admin.voice.channel else "غير محدد", inline=True)
        
        if description:
            report_embed.add_field(name="📋 التفاصيل", value=description, inline=False)
        
        await mute_log_channel.send(embed=report_embed)
        
    except Exception as e:
        print(f"Error sending mute report: {e}")

async def send_unmute_report(guild, member, duration):
    """Send unmute report to mute-log channel"""
    try:
        # Find mute-log channel
        mute_log_channel = discord.utils.get(guild.channels, name="mute-log")
        
        if not mute_log_channel:
            print("❌ روم mute-log غير موجود")
            return
        
        # Get current date in Arabic
        current_date = datetime.datetime.now().strftime("%d-%B-%Y")
        
        # Convert duration to readable format
        if duration >= 1440:  # 24 hours or more
            duration_text = f"{duration // 1440} يوم"
        elif duration >= 60:  # 1 hour or more
            duration_text = f"{duration // 60} ساعة"
        else:
            duration_text = f"{duration} دقيقة"
        
        # Create unmute report embed
        unmute_embed = discord.Embed(
            title="🔊 تقرير رفع الإسكات",
            description=f"تم رفع الإسكات تلقائياً بعد انتهاء المدة",
            color=discord.Color.green()
        )
        
        unmute_embed.add_field(name="👤 المستخدم", value=member.mention, inline=True)
        unmute_embed.add_field(name="⏱️ المدة المكتملة", value=duration_text, inline=True)
        unmute_embed.add_field(name="📅 التاريخ", value=current_date, inline=True)
        unmute_embed.add_field(name="🔄 الحالة", value="تم الرفع تلقائياً", inline=True)
        
        await mute_log_channel.send(embed=unmute_embed)
        
    except Exception as e:
        print(f"Error sending unmute report: {e}")

async def send_manual_unmute_report(guild, member, admin):
    """Send manual unmute report to mute-log channel"""
    try:
        # Find mute-log channel
        mute_log_channel = discord.utils.get(guild.channels, name="mute-log")
        
        if not mute_log_channel:
            print("❌ روم mute-log غير موجود")
            return
        
        # Get current date in Arabic
        current_date = datetime.datetime.now().strftime("%d-%B-%Y")
        
        # Create manual unmute report embed
        manual_unmute_embed = discord.Embed(
            title="🔊 تقرير رفع الإسكات اليدوي",
            description=f"تم رفع الإسكات يدوياً بواسطة الإدارة",
            color=discord.Color.blue()
        )
        
        manual_unmute_embed.add_field(name="👤 المستخدم", value=member.mention, inline=True)
        manual_unmute_embed.add_field(name="📝 بواسطة", value=admin.mention, inline=True)
        manual_unmute_embed.add_field(name="📅 التاريخ", value=current_date, inline=True)
        manual_unmute_embed.add_field(name="🔄 الحالة", value="تم الرفع يدوياً", inline=True)
        
        await mute_log_channel.send(embed=manual_unmute_embed)
        
    except Exception as e:
        print(f"Error sending manual unmute report: {e}")

# Note: bot.run() is handled in app.py to avoid conflicts 