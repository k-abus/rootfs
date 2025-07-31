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

# Global set to prevent duplicate messages
sent_messages = set()

# Helper functions
async def send_error_message(ctx, message, duration: int = 5):
    """Send error message as ephemeral"""
    message_id = f"{ctx.message.id}_{message}"
    if message_id in sent_messages:
        return
    sent_messages.add(message_id)
    try:
        await ctx.send(message, ephemeral=True)
    except Exception as e:
        print(f"Error sending ephemeral message: {e}")
        await ctx.send(message)

async def send_hidden_message(ctx, message=None, embed=None, duration: int = 10):
    """Send hidden message as ephemeral"""
    message_id = f"{ctx.message.id}_{'hidden'}"
    if message_id in sent_messages:
        return
    sent_messages.add(message_id)
    try:
        if embed:
            await ctx.send(embed=embed, ephemeral=True)
        else:
            await ctx.send(message, ephemeral=True)
    except Exception as e:
        print(f"Error sending hidden message: {e}")
        if embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send(message)

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

# Button Views for interactive commands (ONLY for اسكات and مساعدة)
class MuteOptionsView(discord.ui.View):
    def __init__(self, member: discord.Member, ctx):
        super().__init__(timeout=60)
        self.member = member
        self.ctx = ctx

    @discord.ui.button(label="سب/شتائم", style=discord.ButtonStyle.danger, emoji="🤬")
    async def swear_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(self.ctx):
            await interaction.response.send_message("❌ ليس لديك صلاحيات كافية", ephemeral=True)
            return
        
        await self.execute_mute(interaction, "سب/شتائم", 30)

    @discord.ui.button(label="إساءة/استهزاء", style=discord.ButtonStyle.danger, emoji="😤")
    async def abuse_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(self.ctx):
            await interaction.response.send_message("❌ ليس لديك صلاحيات كافية", ephemeral=True)
            return
        
        await self.execute_mute(interaction, "إساءة/استهزاء", 60)

    @discord.ui.button(label="روابط/إعلانات", style=discord.ButtonStyle.secondary, emoji="🔗")
    async def links_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(self.ctx):
            await interaction.response.send_message("❌ ليس لديك صلاحيات كافية", ephemeral=True)
            return
        
        await self.execute_mute(interaction, "روابط/إعلانات", 120)

    @discord.ui.button(label="سبام", style=discord.ButtonStyle.secondary, emoji="📢")
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(self.ctx):
            await interaction.response.send_message("❌ ليس لديك صلاحيات كافية", ephemeral=True)
            return
        
        await self.execute_mute(interaction, "سبام", 45)

    @discord.ui.button(label="تجاهل التحذيرات", style=discord.ButtonStyle.secondary, emoji="⚠️")
    async def ignore_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(self.ctx):
            await interaction.response.send_message("❌ ليس لديك صلاحيات كافية", ephemeral=True)
            return
        
        await self.execute_mute(interaction, "تجاهل التحذيرات", 15)

    async def execute_mute(self, interaction: discord.Interaction, reason: str, duration_minutes: int):
        """Execute mute with the selected reason"""
        try:
            # Validate member
            can_target, error_msg = validate_member_permissions(self.ctx, self.member)
            if not can_target:
                await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
                return

            # Create muted role
            muted_role = await create_muted_role(self.ctx)
            
            # Apply mute
            await self.member.add_roles(muted_role, reason=f"ميوت بواسطة {self.ctx.author} - السبب: {reason}")
            
            # Create embed
            embed = discord.Embed(
                title="✅ تم الإسكات بنجاح",
                description=f"تم إسكات {self.member.mention}",
                color=discord.Color.red()
            )
            embed.add_field(name="السبب", value=reason, inline=True)
            embed.add_field(name="المدة", value=f"{duration_minutes} دقيقة", inline=True)
            embed.add_field(name="بواسطة", value=self.ctx.author.mention, inline=True)
            embed.set_footer(text=f"سيتم إلغاء الإسكات تلقائياً بعد {duration_minutes} دقيقة")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Schedule unmute
            async def unmute_after_duration():
                await asyncio.sleep(duration_minutes * 60)
                try:
                    if muted_role in self.member.roles:
                        await self.member.remove_roles(muted_role, reason="انتهاء مدة الميوت")
                        await self.ctx.send(f"✅ تم إلغاء ميوت {self.member.mention} بعد انتهاء المدة")
                except Exception as e:
                    print(f"Error in unmute task: {e}")
            
            asyncio.create_task(unmute_after_duration())
            
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ: {str(e)}", ephemeral=True)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="الأوامر العامة", style=discord.ButtonStyle.primary, emoji="📋")
    async def general_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📋 الأوامر العامة",
            description="الأوامر المتاحة لجميع الأعضاء",
            color=discord.Color.blue()
        )
        embed.add_field(name="اسكاتي", value="عرض حالة الإسكات الخاصة بك", inline=False)
        embed.add_field(name="مساعدة", value="عرض قائمة الأوامر المتاحة", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="أوامر الإدارة", style=discord.ButtonStyle.danger, emoji="🛡️")
    async def admin_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_admin_permissions(interaction):
            await interaction.response.send_message("❌ هذا القسم للمشرفين فقط", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🛡️ أوامر الإدارة",
            description="الأوامر المتاحة للمشرفين فقط",
            color=discord.Color.red()
        )
        embed.add_field(name="اسكات @عضو", value="عرض خيارات الإسكات", inline=False)
        embed.add_field(name="اسكت @عضو سبب", value="إسكات مباشر", inline=False)
        embed.add_field(name="تكلم @عضو", value="إلغاء الإسكات", inline=False)
        embed.add_field(name="باند @عضو", value="حظر العضو", inline=False)
        embed.add_field(name="كيك @عضو", value="طرد العضو", inline=False)
        embed.add_field(name="مسح عدد", value="حذف الرسائل", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Bot commands
@bot.command(name='اسكات')
async def show_mute_options(ctx, member: discord.Member):
    """Show mute options with buttons (admin only)"""
    log_command_usage(ctx, 'اسكات')
    
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر")
        return
    
    if not member:
        await send_error_message(ctx, "❌ يرجى منشن العضو المراد إسكاته")
        return
    
    # Validate member
    can_target, error_msg = validate_member_permissions(ctx, member)
    if not can_target:
        await send_error_message(ctx, f"❌ {error_msg}")
        return
    
    # Create embed
    embed = discord.Embed(
        title="🔇 خيارات الإسكات",
        description=f"اختر سبب الإسكات لـ {member.mention}",
        color=discord.Color.orange()
    )
    embed.add_field(name="🤬 سب/شتائم", value="30 دقيقة", inline=True)
    embed.add_field(name="😤 إساءة/استهزاء", value="60 دقيقة", inline=True)
    embed.add_field(name="🔗 روابط/إعلانات", value="120 دقيقة", inline=True)
    embed.add_field(name="📢 سبام", value="45 دقيقة", inline=True)
    embed.add_field(name="⚠️ تجاهل التحذيرات", value="15 دقيقة", inline=True)
    
    # Create view with buttons
    view = MuteOptionsView(member, ctx)
    
    await ctx.send(embed=embed, view=view, ephemeral=True)

@bot.command(name='اسكت')
async def mute_member_direct(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """Direct mute with reason (admin only)"""
    log_command_usage(ctx, 'اسكت')
    
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر")
        return
    
    # Validate member
    can_target, error_msg = validate_member_permissions(ctx, member)
    if not can_target:
        await send_error_message(ctx, f"❌ {error_msg}")
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
        await asyncio.sleep(10)
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
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='تكلم')
async def unmute_member(ctx, member: discord.Member):
    """Unmute member (admin only)"""
    log_command_usage(ctx, 'تكلم')
    
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر")
        return
    
    try:
        muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not muted_role:
            await send_error_message(ctx, "❌ لا يوجد دور 'Muted' في السيرفر")
            return
        
        if muted_role not in member.roles:
            await send_error_message(ctx, f"❌ {member.mention} غير مكتوم أصلاً")
            return
        
        await member.remove_roles(muted_role, reason=f"إلغاء ميوت بواسطة {ctx.author}")
        
        embed = discord.Embed(
            title="✅ تم إلغاء الإسكات",
            description=f"تم إلغاء إسكات {member.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="بواسطة", value=ctx.author.mention, inline=True)
        
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        try:
            await msg.delete()
        except:
            pass
        
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='اسكاتي')
async def check_mute_status(ctx, member: discord.Member = None):
    """Check mute status (everyone)"""
    log_command_usage(ctx, 'اسكاتي')
    
    if not member:
        member = ctx.author
    
    # Check if user is checking someone else's status
    if member != ctx.author and not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ لا يمكنك التحقق من حالة إسكات الآخرين")
        return
    
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role or muted_role not in member.roles:
        embed = discord.Embed(
            title="🔊 حالة الإسكات",
            description=f"{member.mention} غير مكتوم",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, ephemeral=True)
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
    
    await ctx.send(embed=embed, ephemeral=True)

@bot.command(name='مساعدة')
async def help_command(ctx):
    """Help command with buttons (everyone)"""
    log_command_usage(ctx, 'مساعدة')
    
    embed = discord.Embed(
        title="🤖 بوت الإدارة",
        description="مرحباً! أنا بوت إدارة متقدم مع ميزات تفاعلية",
        color=discord.Color.blue()
    )
    embed.add_field(name="💡 كيف تستخدم البوت؟", value="اضغط على الأزرار أدناه لرؤية الأوامر المتاحة", inline=False)
    
    # Create view with buttons
    view = HelpView()
    
    await ctx.send(embed=embed, view=view, ephemeral=True)

@bot.command(name='باند')
async def ban_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """Ban member (admin only)"""
    log_command_usage(ctx, 'باند')
    
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر")
        return
    
    # Validate member
    can_target, error_msg = validate_member_permissions(ctx, member)
    if not can_target:
        await send_error_message(ctx, f"❌ {error_msg}")
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
        await asyncio.sleep(10)
        try:
            await msg.delete()
        except:
            pass
        
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='كيك')
async def kick_member(ctx, member: discord.Member, *, reason: str = "لا يوجد سبب محدد"):
    """Kick member (admin only)"""
    log_command_usage(ctx, 'كيك')
    
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر")
        return
    
    # Validate member
    can_target, error_msg = validate_member_permissions(ctx, member)
    if not can_target:
        await send_error_message(ctx, f"❌ {error_msg}")
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
        await asyncio.sleep(10)
        try:
            await msg.delete()
        except:
            pass
        
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

@bot.command(name='مسح')
async def clear_messages(ctx, amount: int = 5):
    """Clear messages (admin only)"""
    log_command_usage(ctx, 'مسح')
    
    if not has_admin_permissions(ctx):
        await send_error_message(ctx, "❌ ليس لديك صلاحيات كافية لاستخدام هذا الأمر")
        return
    
    if amount < 1 or amount > 100:
        await send_error_message(ctx, "❌ يرجى تحديد عدد بين 1 و 100")
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
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except:
            pass
        
    except Exception as e:
        await send_error_message(ctx, f"❌ حدث خطأ: {str(e)}")

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
    await send_error_message(ctx, error_message)

# Bot events
@bot.event
async def on_ready():
    print(f'✅ {bot.user} تم تسجيل الدخول بنجاح!')
    print(f'🆔 Bot ID: {bot.user.id}')
    print(f'📊 عدد السيرفرات: {len(bot.guilds)}')

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ لم يتم العثور على DISCORD_TOKEN في متغيرات البيئة")
        exit(1)
    
    bot.run(token) 