import discord
from discord.ext import commands
from discord.abc import GuildChannel
from typing import Optional, List


class VoiceCalls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_calls = {}

    @discord.slash_command(name="create_voice_call", description="Create a limited voice call with specified users")
    async def create_voice_call(
        self,
        ctx: discord.ApplicationContext,
        user1: discord.User,
        user2: discord.User,
        call_name: Optional[str] = None,
    ):
        if not ctx.guild:
            await ctx.respond("Dieser Befehl kann nur auf Servern verwendet werden.", ephemeral=True)
            return

        if user1.id == user2.id:
            await ctx.respond("Du kannst nicht mit der gleichen Person anrufen.", ephemeral=True)
            return

        if user1.id == ctx.author.id or user2.id == ctx.author.id:
            pass
        else:
            await ctx.respond(
                "Du musst einer der Teilnehmer sein, um einen Anruf zu erstellen.", ephemeral=True
            )
            return

        if call_name is None:
            call_name = f"{user1.name}-{user2.name}"

        channel_name = self._get_next_channel_name(call_name)
        
        category = await self._get_or_create_voice_category(ctx.guild)
        if category is None:
            await ctx.respond("Fehler beim Erstellen der Kategorie.", ephemeral=True)
            return

        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user1: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
            user2: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
            ctx.author: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
        }

        try:
            voice_channel = await ctx.guild.create_voice_channel(
                channel_name, category=category, overwrites=overwrites
            )
            
            self.active_calls[voice_channel.id] = {
                "creator": ctx.author.id,
                "participants": [user1.id, user2.id, ctx.author.id],
                "created_at": discord.utils.utcnow(),
            }
            
            await ctx.respond(
                f"Voice-Anruf erstellt: {voice_channel.mention}\n"
                f"Teilnehmer: {user1.mention}, {user2.mention}",
                ephemeral=True,
            )
        except discord.Forbidden:
            await ctx.respond("Ich habe keine Berechtigung, Kanäle zu erstellen.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"Fehler beim Erstellen des Kanals: {str(e)}", ephemeral=True)

    @discord.slash_command(name="list_voice_calls", description="List all active voice calls")
    async def list_voice_calls(self, ctx: discord.ApplicationContext):
        if not ctx.guild:
            await ctx.respond("Dieser Befehl kann nur auf Servern verwendet werden.", ephemeral=True)
            return

        if not self.active_calls:
            await ctx.respond("Es gibt derzeit keine aktiven Voice-Anrufe.", ephemeral=True)
            return

        embed = discord.Embed(title="Aktive Voice-Anrufe", color=discord.Color.blue())
        for channel_id, call_info in list(self.active_calls.items()):
            channel = ctx.guild.get_channel(channel_id)
            if channel is None:
                del self.active_calls[channel_id]
                continue

            creator = ctx.guild.get_member(call_info["creator"])
            creator_name = creator.name if creator else f"User {call_info['creator']}"
            embed.add_field(
                name=channel.name, value=f"Erstellt von: {creator_name}", inline=False
            )

        await ctx.respond(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        before_channel = before.channel
        after_channel = after.channel

        if before_channel and before_channel.id in self.active_calls:
            if len(before_channel.members) == 0:
                await self._delete_voice_call_channel(before_channel)

    async def _delete_voice_call_channel(self, channel: discord.VoiceChannel):
        try:
            if channel.id in self.active_calls:
                del self.active_calls[channel.id]
            await channel.delete()
        except discord.Forbidden:
            pass
        except Exception:
            pass

    async def _get_or_create_voice_category(self, guild: discord.Guild) -> Optional[discord.CategoryChannel]:
        category_name = "Voice Calls"
        for category in guild.categories:
            if category.name == category_name:
                return category

        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
            }
            category = await guild.create_category(category_name, overwrites=overwrites)
            return category
        except discord.Forbidden:
            return None

    def _get_next_channel_name(self, base_name: str) -> str:
        base_name = base_name.replace(" ", "-").lower()[:20]
        return f"{base_name}-call"


def setup(bot):
    bot.add_cog(VoiceCalls(bot))
