import discord
from discord.ext import commands
from typing import Dict, List, Optional, TypedDict

from utils.settings import load_settings


class VoiceUnlockRule(TypedDict):
    guild_id: int
    trigger_voice_id: int
    target_channel_id: int
    role_id: Optional[int]
    min_members: int
    ignore_bots: bool
    unlock: Dict[str, Optional[bool]]
    lock: Dict[str, Optional[bool]]


class VoiceUnlocks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._valid_permission_names = self._get_valid_permission_names()
        self._rules: List[VoiceUnlockRule] = []
        self._rules_by_guild: Dict[int, List[VoiceUnlockRule]] = {}
        self._trigger_ids_by_guild: Dict[int, set] = {}
        self._load_rules()

    def _get_valid_permission_names(self):
        names = set(getattr(discord.Permissions, "VALID_FLAGS", {}).keys())
        if not names:
            names = {
                "view_channel",
                "connect",
                "send_messages",
                "speak",
                "stream",
                "use_voice_activation",
                "read_message_history",
                "add_reactions",
                "attach_files",
                "embed_links",
            }
        return names

    def _log_rule_warning(self, index: int, message: str):
        print(f"[VOICE-UNLOCK] Rule {index}: {message}", flush=True)

    def _parse_bool(self, value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if cleaned in {"true", "yes", "1", "on"}:
                return True
            if cleaned in {"false", "no", "0", "off"}:
                return False
        return default

    def _sanitize_overwrite(self, raw) -> Dict[str, Optional[bool]]:
        if not isinstance(raw, dict):
            return {}
        cleaned: Dict[str, Optional[bool]] = {}
        for name, value in raw.items():
            if name not in self._valid_permission_names:
                continue
            if value is True or value is False or value is None:
                cleaned[name] = value
                continue
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"allow", "true", "yes", "1", "on"}:
                    cleaned[name] = True
                elif lowered in {"deny", "false", "no", "0", "off"}:
                    cleaned[name] = False
                elif lowered in {"clear", "none", "null"}:
                    cleaned[name] = None
        return cleaned

    def _parse_rules(self, raw_rules) -> List[VoiceUnlockRule]:
        parsed: List[VoiceUnlockRule] = []
        if not isinstance(raw_rules, list):
            return parsed

        for index, raw in enumerate(raw_rules, start=1):
            if not isinstance(raw, dict):
                self._log_rule_warning(index, "rule must be an object")
                continue

            try:
                guild_id = int(raw.get("guild_id"))
                trigger_voice_id = int(raw.get("trigger_voice_id"))
                target_channel_id = int(raw.get("target_channel_id"))
            except (TypeError, ValueError):
                self._log_rule_warning(index, "guild_id, trigger_voice_id, target_channel_id must be numbers")
                continue

            role_id = raw.get("role_id")
            if role_id is not None:
                try:
                    role_id = int(role_id)
                except (TypeError, ValueError):
                    self._log_rule_warning(index, "role_id must be a number or null")
                    continue

            min_members = raw.get("min_members", 1)
            try:
                min_members = max(1, int(min_members))
            except (TypeError, ValueError):
                min_members = 1

            ignore_bots = self._parse_bool(raw.get("ignore_bots"), False)
            unlock = self._sanitize_overwrite(raw.get("unlock"))
            lock = self._sanitize_overwrite(raw.get("lock"))

            parsed.append(
                {
                    "guild_id": guild_id,
                    "trigger_voice_id": trigger_voice_id,
                    "target_channel_id": target_channel_id,
                    "role_id": role_id,
                    "min_members": min_members,
                    "ignore_bots": ignore_bots,
                    "unlock": unlock,
                    "lock": lock,
                }
            )

        return parsed

    def _load_rules(self):
        settings = load_settings()
        raw_rules = settings.get("voice_unlocks", [])
        self._rules = self._parse_rules(raw_rules)
        self._rules_by_guild = {}
        self._trigger_ids_by_guild = {}

        for rule in self._rules:
            self._rules_by_guild.setdefault(rule["guild_id"], []).append(rule)
            self._trigger_ids_by_guild.setdefault(rule["guild_id"], set()).add(rule["trigger_voice_id"])

    def _default_overwrites(self, channel: discord.abc.GuildChannel):
        unlock: Dict[str, Optional[bool]] = {"view_channel": True}
        text_channel_types = (discord.TextChannel, discord.NewsChannel)
        forum_channel = getattr(discord, "ForumChannel", None)
        if forum_channel is not None:
            text_channel_types = text_channel_types + (forum_channel,)

        if isinstance(channel, text_channel_types):
            unlock["send_messages"] = True
        elif isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            unlock["connect"] = True

        lock: Dict[str, Optional[bool]] = {"view_channel": False}
        unlock = {name: value for name, value in unlock.items() if name in self._valid_permission_names}
        lock = {name: value for name, value in lock.items() if name in self._valid_permission_names}
        return unlock, lock

    def _resolve_overwrite(self, rule: VoiceUnlockRule, channel: discord.abc.GuildChannel, active: bool):
        default_unlock, default_lock = self._default_overwrites(channel)
        unlock = rule["unlock"] or default_unlock
        lock = rule["lock"] or default_lock
        return unlock if active else lock

    def _overwrite_matches(self, overwrite: discord.PermissionOverwrite, desired: Dict[str, Optional[bool]]):
        for name, value in desired.items():
            if getattr(overwrite, name, None) != value:
                return False
        return True

    def _count_trigger_members(self, channel, ignore_bots: bool) -> int:
        if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            return 0
        if not ignore_bots:
            return len(channel.members)
        return sum(1 for member in channel.members if not member.bot)

    async def _apply_overwrite(
        self,
        channel: discord.abc.GuildChannel,
        role: discord.Role,
        desired: Dict[str, Optional[bool]],
    ) -> bool:
        if not desired:
            return False

        current = channel.overwrites_for(role)
        if self._overwrite_matches(current, desired):
            return False

        current.update(**desired)
        await channel.set_permissions(role, overwrite=current, reason="Voice unlock rule")
        return True

    async def _sync_guild(self, guild: discord.Guild):
        rules = self._rules_by_guild.get(guild.id)
        if not rules:
            return

        me = guild.me
        if me is None or not me.guild_permissions.manage_channels:
            print(f"[VOICE-UNLOCK] Missing manage_channels in guild {guild.id}", flush=True)
            return

        grouped: Dict[tuple, List[VoiceUnlockRule]] = {}
        for rule in rules:
            key = (rule["target_channel_id"], rule["role_id"])
            grouped.setdefault(key, []).append(rule)

        for (target_channel_id, role_id), group_rules in grouped.items():
            channel = guild.get_channel(target_channel_id)
            if not isinstance(channel, discord.abc.GuildChannel):
                print(
                    f"[VOICE-UNLOCK] Target channel {target_channel_id} not found in guild {guild.id}",
                    flush=True,
                )
                continue

            role = guild.get_role(role_id) if role_id else guild.default_role
            if role is None:
                print(f"[VOICE-UNLOCK] Role {role_id} not found in guild {guild.id}", flush=True)
                continue

            active = False
            for rule in group_rules:
                trigger = guild.get_channel(rule["trigger_voice_id"])
                if self._count_trigger_members(trigger, rule["ignore_bots"]) >= rule["min_members"]:
                    active = True
                    break

            desired = self._resolve_overwrite(group_rules[0], channel, active)
            try:
                await self._apply_overwrite(channel, role, desired)
            except (discord.Forbidden, discord.HTTPException) as exc:
                print(
                    f"[VOICE-UNLOCK] Failed to update {channel.id} in guild {guild.id}: {exc}",
                    flush=True,
                )

    async def _sync_all_guilds(self):
        for guild in self.bot.guilds:
            try:
                await self._sync_guild(guild)
            except Exception as exc:
                print(f"[VOICE-UNLOCK] Sync error in guild {guild.id}: {exc}", flush=True)

    @commands.Cog.listener()
    async def on_ready(self):
        await self._sync_all_guilds()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.guild:
            return

        if before.channel == after.channel:
            return

        rules = self._rules_by_guild.get(member.guild.id)
        if not rules:
            return

        trigger_ids = self._trigger_ids_by_guild.get(member.guild.id, set())
        before_id = before.channel.id if before and before.channel else None
        after_id = after.channel.id if after and after.channel else None
        if before_id not in trigger_ids and after_id not in trigger_ids:
            return

        await self._sync_guild(member.guild)


def setup(bot):
    bot.add_cog(VoiceUnlocks(bot))
