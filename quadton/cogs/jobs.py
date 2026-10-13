from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.data.jobs import JOBS, by_id, pay_for, xp_needed


def fmt(n: int) -> str:
    return f"{n:,} QC"


class Jobs(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="List available careers.")
    async def jobs(self, interaction: discord.Interaction) -> None:
        lines = [
            f"`{j.job_id}` — **{j.name}** · base {j.base_pay} QC / "
            f"{j.cooldown // 60}m — {j.description}"
            for j in JOBS
        ]
        embed = discord.Embed(
            title="Careers", description="\n".join(lines), color=0x8E44AD
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Choose your career.")
    @app_commands.describe(job_id="Career ID (see /jobs)")
    async def job_change(
        self, interaction: discord.Interaction, job_id: str
    ) -> None:
        uid = interaction.user.id
        job = by_id(job_id)
        if job is None:
            await interaction.response.send_message(
                "Unknown career.", ephemeral=True
            )
            return
        async with self.bot.db.transaction() as conn:
            await self.bot.currency.ensure_user(conn, uid)
            await conn.execute(
                """
                INSERT INTO user_jobs(user_id, job_id) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    job_id=excluded.job_id, level=1, xp=0, promotions=0
                """,
                (uid, job.job_id),
            )
        await interaction.response.send_message(
            f"You are now a **{job.name}**. Progress reset to level 1.",
            ephemeral=True,
        )

    @app_commands.command(description="Show your current career.")
    async def career(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        row = await self.bot.db.fetchone(
            "SELECT job_id, level, xp, promotions FROM user_jobs WHERE user_id=?",
            (uid,),
        )
        if row is None:
            await interaction.response.send_message(
                "You have no career. Use `/job-change` first.", ephemeral=True
            )
            return
        job = by_id(row["job_id"])
        if job is None:
            await interaction.response.send_message(
                "Your career is invalid; pick a new one.", ephemeral=True
            )
            return
        need = xp_needed(int(row["level"]))
        pay = pay_for(job, int(row["level"]))
        embed = discord.Embed(title=job.name, color=0xE67E22)
        embed.add_field(name="Level", value=str(row["level"]))
        embed.add_field(name="XP", value=f"{row['xp']} / {need}")
        embed.add_field(name="Pay per shift", value=fmt(pay))
        embed.add_field(name="Promotions", value=str(row["promotions"]))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Work a shift at your current job.")
    async def work(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        row = await self.bot.db.fetchone(
            "SELECT job_id, level, xp FROM user_jobs WHERE user_id=?", (uid,)
        )
        if row is None:
            await interaction.response.send_message(
                "You have no career. Use `/job-change` first.", ephemeral=True
            )
            return
        job = by_id(row["job_id"])
        if job is None:
            await interaction.response.send_message(
                "Your career is invalid; pick a new one.", ephemeral=True
            )
            return
        level = int(row["level"])
        base = pay_for(job, level)
        mult = await self.bot.effects.multiplier(uid, "prosperity")
        pay = int(base * mult)
        xp_mult = await self.bot.effects.multiplier(uid, "xp_boost")
        xp_gain = int(job.xp_per_work * xp_mult)

        async def grant(conn):
            await self.bot.currency.credit_in_tx(
                conn, uid, pay, "JOB_REWARD", count_as_earned=True
            )
            await conn.execute(
                "UPDATE user_stats SET jobs_completed = jobs_completed + 1 "
                "WHERE user_id=?",
                (uid,),
            )
            await conn.execute(
                "UPDATE user_jobs SET xp = xp + ? WHERE user_id=?", (xp_gain, uid)
            )
            await self._try_levelup(conn, uid)

        status = await self.bot.cooldowns.reward_with_cooldown(
            uid, f"job:{job.job_id}", job.cooldown, grant
        )
        if not status.ready:
            m, s = divmod(status.remaining, 60)
            await interaction.response.send_message(
                f"Shift cooldown: {m}m {s}s remaining.", ephemeral=True
            )
            return
        await self.bot.achievements.check_and_grant(uid)
        await interaction.response.send_message(
            f"Worked a shift as **{job.name}** and earned **{fmt(pay)}** (+{xp_gain} XP)."
        )

    async def _try_levelup(self, conn, uid: int) -> None:
        while True:
            cur = await conn.execute(
                "SELECT job_id, level, xp FROM user_jobs WHERE user_id=?", (uid,)
            )
            row = await cur.fetchone()
            if row is None:
                return
            job = by_id(row["job_id"])
            if job is None:
                return
            need = xp_needed(int(row["level"]))
            if int(row["xp"]) < need or int(row["level"]) >= job.max_level:
                return
            await conn.execute(
                "UPDATE user_jobs SET level = level + 1, xp = xp - ?, "
                "promotions = promotions + 1 WHERE user_id=?",
                (need, uid),
            )


async def setup(bot) -> None:
    await bot.add_cog(Jobs(bot))
