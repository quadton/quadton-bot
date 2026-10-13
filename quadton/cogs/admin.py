from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.services.backups import BackupService


def is_admin(bot, user_id: int) -> bool:
    return user_id in bot.config.admin_user_ids


class Admin(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="[Admin] Grant QC to a user.")
    @app_commands.describe(
        member="Target member", amount="Positive integer QC", reason="Audit reason"
    )
    async def admin_give(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
        reason: str = "admin adjustment",
    ) -> None:
        if not is_admin(self.bot, interaction.user.id):
            await interaction.response.send_message(
                "Not authorized.", ephemeral=True
            )
            return
        if amount == 0:
            await interaction.response.send_message(
                "Amount cannot be zero.", ephemeral=True
            )
            return
        async with self.bot.db.transaction() as conn:
            if amount > 0:
                await self.bot.currency.credit_in_tx(
                    conn, member.id, amount, "ADMIN_ADJUSTMENT"
                )
            else:
                await self.bot.currency.debit_in_tx(
                    conn, member.id, -amount, "ADMIN_ADJUSTMENT"
                )
            await conn.execute(
                "INSERT INTO audit_log(actor_id, action, target_id, details, created_at) "
                "VALUES (?, ?, ?, ?, strftime('%s','now'))",
                (interaction.user.id, "admin_give", member.id,
                 f"amount={amount} reason={reason}"),
            )
        await interaction.response.send_message(
            f"Applied {amount:+,} QC to {member.mention}.", ephemeral=True
        )

    @app_commands.command(description="[Admin] Run SQLite integrity check.")
    async def admin_integrity(self, interaction: discord.Interaction) -> None:
        if not is_admin(self.bot, interaction.user.id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        result = await self.bot.db.integrity_check()
        await interaction.response.send_message(f"Integrity: `{result}`", ephemeral=True)

    @app_commands.command(description="[Admin] Create a database backup.")
    async def admin_backup(self, interaction: discord.Interaction) -> None:
        if not is_admin(self.bot, interaction.user.id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        svc = BackupService(self.bot.db, self.bot.config.backup_dir)
        import asyncio
        path = await asyncio.to_thread(svc.backup)
        ok = await asyncio.to_thread(svc.verify, path)
        await interaction.response.send_message(
            f"Backup at `{path}` — integrity {'OK' if ok else 'FAILED'}.",
            ephemeral=True,
        )

    @app_commands.command(description="[Admin] Purge expired effects.")
    async def admin_purge_effects(self, interaction: discord.Interaction) -> None:
        if not is_admin(self.bot, interaction.user.id):
            await interaction.response.send_message("Not authorized.", ephemeral=True)
            return
        n = await self.bot.effects.purge_expired()
        await interaction.response.send_message(
            f"Purged {n} expired effects.", ephemeral=True
        )


async def setup(bot) -> None:
    await bot.add_cog(Admin(bot))
