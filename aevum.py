import discord
from discord.ext import menus, commands
import pendulum
import sys
import os
import json
import aevum_auth

json_path = f"{sys.path[0]}/tz.json"


class NoTimezonesFoundError(Exception):
    pass


class TimezoneMenu(menus.ListPageSource):
    """A simple menu class for paginating lists."""

    def __init__(self, data, title, per_page: int = 10) -> None:
        super().__init__(data, per_page=per_page)
        self.title = title

    async def format_page(self, menu, entries) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            color=16202876,
            description="All times are in 24-hour format.\n\n" + "\n".join(entries))

        embed.set_footer(text=f"This is page {menu.current_page + 1}")

        return embed


def ensure_data(member_id_to_find=None):
    if not os.path.exists(json_path):
        raise NoTimezonesFoundError("Nobody has registered any timezones yet!")

    with open(json_path, "r") as to_be_loaded:
        loaded = json.load(to_be_loaded)

    if not loaded:
        raise NoTimezonesFoundError("Nobody has registered any timezones yet!")

    if member_id_to_find:
        member = loaded.get(member_id_to_find, None)
        if member:
            return member
        else:
            raise NoTimezonesFoundError("This member has not registered a timezxone yet!")

    return loaded


bot = commands.AutoShardedBot(command_prefix="tz ", case_insensitive=True)
bot.load_extension("Jishaku")


@bot.command()
async def all(ctx):
    """Displays the current time (and timezone) for all registered members.
    This bot will never spread past 1 guild so the "all registered members" bit really doesn't matter."""

    loaded = ensure_data()

    data = []
    for user_id, tz in loaded.items():
        readable = getattr(bot.get_user(user_id), "display_name", None) or user_id
        current_time = pendulum.now(tz=tz).format("dddd DD MMMM YYYY HH:mm:ss")
        data.append(f"{readable}: {current_time}")

    page_data = TimezoneMenu(data, "Timezones for all members")
    menu = menus.MenuPages(page_data, 180, clear_reactions_after=True)
    await menu.start(ctx)


@bot.command()
async def user(ctx, *, member: discord.Member):
    """Displays the current time (and timezone) for a specific member."""

    loaded = ensure_data(member.id)
    embed = discord.Embed(
            title=f"Time for {member.display_name}",
            color=16202876,
            description=pendulum.now(tz=loaded).format("dddd DD MMMM YYYY HH:mm:ss"))

    await ctx.send(embed=embed)


@bot.command(name="set")
async def set_tz(ctx, *, tz: discord.Member):
    """Sets your timezone. The tz argument should be a TZ database code, which generally boils down to a "Country/City".
    Examples of valid TZ database codes are "Europe/Lisbon", "Pacific/Auckland" and "America/Los_Angeles".
    See https://en.wikipedia.org/wiki/List_of_tz_database_time_zones#List for more details.
    """

    pendulum.now(tz=tz)
    if os.path.exists(json_path):
        with open(json_path, "r") as to_be_loaded:
            data = json.load(to_be_loaded)
            data[ctx.author.id] = tz
    else:
        data = {ctx.author.id: tz}

    with open(json_path, "w+") as to_write:    
        json.dump(data, to_write)

    await ctx.send("Timezone set!")


@bot.event
async def on_command_error(ctx, error):
    """Run when shit breaks."""

    if isinstance(error, commands.CommandNotFound):
        return  # fuck that
    elif isinstance(error, NoTimezonesFoundError):
        embed = discord.Embed(title="Whoops", color=16202876, description=error.args[0])
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="You suck", color=16202876,
            description="Couldn't understand the provided arguments! Check your spelling.")
    elif isinstance(error, commands.TooManyArguments):
        embed = discord.Embed(title="Whoops", color=16202876, description="Too many arguments provided.")
    elif isinstance(error, pendulum.tz.zoneinfo.exceptions.InvalidTimezone):
        embed = discord.Embed(title="Whoops", color=16202876, description="Invalid timezone code.")
    else:
        embed = discord.Embed(
            title="You suck.", color=16202876,
            description="<generic error message here> - you screwed something up.")

    await ctx.send(embed=embed)

bot.run(aevum_auth.TOKEN)