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
    """Show mute information and options (admin only)"""
    log_command_usage(ctx, 'اسكات')
    
    if not has_admin_permissions(ctx):
        await ctx.respond("❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔇 معلومات الإسكات",
        description="معلومات عن نظام الإسكات في السيرفر",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🤬 سب/شتائم", value="30 دقيقة", inline=True)
    embed.add_field(name="😤 إساءة/استهزاء", value="60 دقيقة", inline=True)
    embed.add_field(name="🔗 روابط/إعلانات", value="120 دقيقة", inline=True)
    embed.add_field(name="📢 سبام", value="45 دقيقة", inline=True)
    embed.add_field(name="⚠️ تجاهل التحذيرات", value="15 دقيقة", inline=True)
    embed.add_field(name="", value="", inline=True)
    
    embed.add_field(name="📝 كيفية الاستخدام", value="اكتب: اسكت @عضو السبب", inline=False)
    embed.add_field(name="💡 أمثلة", value="اسكت @عضو سب\nاسكت @عضو روابط\nاسكت @عضو سبام", inline=False)
    
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
        
        # Map reason to duration
        reason_mapping = {
            "سب": 30, "شتائم": 30, "اساءة": 60, "استهزاء": 60,
            "روابط": 120, "اعلانات": 120, "سبام": 45,
            "تجاهل": 15, "تحذيرات": 15
        }
        
        duration = 30  # default
        for keyword, dur in reason_mapping.items():
            if keyword in reason.lower():
                duration = dur
                break
        
        # Apply mute
        await member.add_roles(muted_role, reason=f"ميوت بواسطة {ctx.author} - السبب: {reason}")
        
        # Create embed
        embed = discord.Embed(
            title="✅ تم الإسكات بنجاح",
            description=f"تم إسكات {member.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="السبب", value=reason, inline=True)
        embed.add_field(name="المدة", value=f"{duration} دقيقة", inline=True)
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        embed.set_footer(text=f"سيتم إلغاء الإسكات تلقائياً بعد {duration} دقيقة")
        
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(7)
        try:
            await msg.delete()
        except:
            pass
        
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
        
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(7)
        try:
            await msg.delete()
        except:
            pass
        
    except Exception as e:
        await ctx.respond(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

@bot.command(name='اسكاتي')
async def check_mute_status(ctx, member: discord.Member = None):
    """Check mute status (everyone)"""
    log_command_usage(ctx, 'اسكاتي')
    
    if not member:
        member = ctx.author
    
    # Check if user is checking someone else's status
    if member != ctx.author and not has_admin_permissions(ctx):
        await ctx.respond("❌ لا يمكنك التحقق من حالة إسكات الآخرين", ephemeral=True)
        return
    
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        embed = discord.Embed(
            title="🔊 حالة الإسكات",
            description=f"{member.mention} غير مكتوم",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
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
    
    await ctx.send(embed=embed)

@bot.command(name='مساعدة')
async def help_command(ctx):
    """Help command (everyone)"""
    log_command_usage(ctx, 'مساعدة')
    
    embed = discord.Embed(
        title="🤖 بوت الإدارة - قائمة الأوامر",
        description="مرحباً! أنا بوت إدارة متقدم مع ميزات متقدمة",
        color=discord.Color.blue()
    )
    
    # General commands
    embed.add_field(name="📋 الأوامر العامة", value="الأوامر المتاحة لجميع الأعضاء", inline=False)
    embed.add_field(name="اسكاتي", value="عرض حالة الإسكات الخاصة بك", inline=True)
    embed.add_field(name="مساعدة", value="عرض قائمة الأوامر المتاحة", inline=True)
    embed.add_field(name="", value="", inline=True)
    
    # Admin commands
    if has_admin_permissions(ctx):
        embed.add_field(name="🛡️ أوامر الإدارة", value="الأوامر المتاحة للمشرفين فقط", inline=False)
        embed.add_field(name="اسكات", value="عرض معلومات الإسكات", inline=True)
        embed.add_field(name="اسكت @عضو سبب", value="إسكات مباشر", inline=True)
        embed.add_field(name="تكلم @عضو", value="إلغاء الإسكات", inline=True)
        embed.add_field(name="باند @عضو", value="حظر العضو", inline=True)
        embed.add_field(name="كيك @عضو", value="طرد العضو", inline=True)
        embed.add_field(name="مسح عدد", value="حذف الرسائل", inline=True)
    else:
        embed.add_field(name="🛡️ أوامر الإدارة", value="غير متاحة لك", inline=False)
    
    embed.add_field(name="💡 نصائح", value="• استخدم @عضو لمنشن العضو\n• اكتب السبب بعد الأمر\n• الرسائل تختفي تلقائياً", inline=False)
    
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
        
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(7)
        try:
            await msg.delete()
        except:
            pass
        
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
        
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(7)
        try:
            await msg.delete()
        except:
            pass
        
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
        
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(7)
        try:
            await msg.delete()
        except:
            pass
        
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
    
    error_message = "❌ حدث خطأ في تنفيذ الأمر"
    await ctx.respond(error_message, ephemeral=True)

# Bot events
@bot.event
async def on_ready():
    print(f'✅ {bot.user} تم تسجيل الدخول بنجاح!')
    print(f'🆔 Bot ID: {bot.user.id}')
    print(f'📊 عدد السيرفرات: {len(bot.guilds)}')

# Note: bot.run() is handled in app.py to avoid conflicts 