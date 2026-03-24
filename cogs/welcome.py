import discord
from discord.ext import commands

class welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


# WELCOME MESSAGE
    @commands.Cog.listener()
    async def on_member_join(self, member):
        member_number = member.guild.member_count

        embed = discord.Embed(
            title="👋 Willkommen!",
            description=(
                f"Hey {member.mention}!\n\n"
                f"Willkommen auf dem **{member.guild.name} Discord**\n"
                f"Du bist unser **{member_number}. Mitglied**!\n\n"
                "Lies dir bitte die Regeln durch\n"
                "Und hol dir deine Rollen"
            ),
            color=discord.Color.purple()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_image(url="https://media.discordapp.net/attachments/1413227108053811290/1482490707267813448/IMG_5138.png?ex=69b7248f&is=69b5d30f&hm=54ec524cf7f98f191a5d9c3321dfcbdd6dfbf5100ff5593a398468edfab0ba4a&=&format=webp&quality=lossless&width=2237&height=1261")  # Banner

        embed.set_footer(text=f"{member.guild.name} • Viel Spaß!")

        view = WelcomeButtons()

        channel = self.bot.get_channel(1264135592594116668)

        if channel:
            await channel.send(embed=embed, view=view)


class WelcomeButtons(discord.ui.View):

    @discord.ui.button(label="Regeln", style=discord.ButtonStyle.primary)
    async def rules(self, button, interaction):
        await interaction.response.send_message(
            "Unsere Regeln findest du hier: <#1264134616000761869>",
            ephemeral=True
        )

    @discord.ui.button(label="Rollen", style=discord.ButtonStyle.primary)
    async def roles(self, button, interaction):
        await interaction.response.send_message(
            "Hol dir deine Rollen hier: <#1442112178906988565>",
            ephemeral=True
        )




def setup(bot):
    bot.add_cog(welcome(bot))