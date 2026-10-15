from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.data.jobs import JOBS, by_id, pay_for, xp_needed
from quadton.ui.base import SelectView
from quadton.ui.embeds import COLOR_MARKET, error, info, qc, success


class Jobs(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="jobs",
        description="Browse careers with a dropdown.",
    )
    async def jobs(self, interaction: discord.Interaction) -> None:
        options = [
            discord.SelectOption(
                label=j.name[:100],
                value=j.job_id,
                description=f"Base {j.base_pay} QC · {j.cooldown // 60}m cooldown",
            )
            for j in JOBS
        ]

        async def on_select(inter2: discord.Interaction, job_id: str) -> None:
            await self._show_job(inter2, job_id)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose a career to inspect...",
            options=options,
            on_select=on_select,
        )
        embed = info(
            "💼 Careers",
            "Pick a career to see its pay, cooldown, and progression.",
        )
        embed.color = COLOR_MARKET
        await view.start(interaction, embed=embed)

    async def _show_job(
        self, interaction: discord.Interaction, job_id: str
    ) -> None:
        job = by_id(job_id)
        if job is None:
            await interaction.response.edit_message(
                embed=error("Unknown career"), view=None
            )
            return
        embed = discord.Embed(
            title=job.name,
            description=job.description,
            color=COLOR_MARKET,
        )
        embed.add_field(name="Base pay", value=qc(job.base_pay))
        embed.add_field(name="Cooldown", value=f"{job.cooldown // 60} min")
        embed.add_field(name="XP per shift", value=str(job.xp_per_work))
        embed.add_field(name="Max level", value=str(job.max_level))
        embed.add_field(
            name="Pay at level 10",
            value=qc(pay_for(job, 10)),
        )
        embed.add_field(
            name="XP for level 2",
            value=str(xp_needed(1)),
        )

        actions = [
            discord.SelectOption(label="Apply for this career", value="apply"),
            discord.SelectOption(label="← Back to careers", value="back"),
        ]

        async def on_action(inter2: discord.Interaction, value: str) -> None:
            if value == "back":
                await self.jobs(inter2)
                return
            await self._apply(inter2, job_id)

        view = SelectView(
            interaction.user.id,
            placeholder="Choose an action...",
            options=actions,
            on_select=on_action,
        )
        await interaction.response.edit_message(embed=embed, view=view)

    async def _apply(
        self, interaction: discord.Interaction, job_id: str
    ) -> None:
        job = by_id(job_id)
        if job is None:
            await interaction.response.send_message(
                embed=error("Unknown career"), ephemeral=True
            )
            return
        async with self.bot.db.transaction() as conn:
            await self.bot.currency.ensure_user(conn, interaction.user.id)
            await conn.execute(
                """
                INSERT INTO user_jobs(user_id, job_id) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    job_id=excluded.job_id, level=1, xp=0, promotions=0
                """,
                (interaction.user.id, job.job_id),
            )
        await interaction.response.send_message(
            embed=success(
                "Career updated",
                f"You are now a **{job.name}**. Progress reset to level 1.",
            ),
            ephemeral=True,
        )

    @app_commands.command(name="job-change", description="Choose a career by ID.")
    @app_commands.describe(job_id="Career ID (e.g. miner, chef)")
    async def job_change(
        self, interaction: discord.Interaction, job_id: str
    ) -> None:
        job = by_id(job_id)
        if job is None:
            await interaction.response.send_message(
                embed=error("Unknown career"), ephemeral=True
            )
            return
        async with self.bot.db.transaction() as conn:
            await self.bot.currency.ensure_user(conn, interaction.user.id)
            await conn.execute(
                """
                INSERT INTO user_jobs(user_id, job_id) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    job_id=excluded.job_id, level=1, xp=0, promotions=0
                """,
                (interaction.user.id, job.job_id),
            )
        await interaction.response.send_message(
            embed=success("Career updated", f"You are now a **{job.name}**."),
            ephemeral=True,
        )

    @app_commands.command(name="career", description="Your current career.")
    async def career(self, interaction: discord.Interaction) -> None:
        row = await self.bot.db.fetchone(
            "SELECT job_id, level, xp, promotions FROM user_jobs WHERE user_id=?",
            (interaction.user.id,),
        )
        if row is None:
            await interaction.response.send_message(
                embed=info(
                    "No career",
                    "Use `/jobs` to browse and apply for a career.",
                ),
                ephemeral=True,
            )
            return
        job = by_id(row["job_id"])
        if job is None:
            await interaction.response.send_message(
                embed=error("Career invalid — pick a new one."),
                ephemeral=True,
            )
            return
        embed = info(job.name)
        embed.add_field(name="Level", value=str(row["level"]))
        embed.add_field(
            name="XP", value=f"{row['xp']} / {xp_needed(int(row['level']))}"
        )
        embed.add_field(
            name="Pay per shift", value=qc(pay_for(job, int(row["level"])))
        )
        embed.add_field(name="Promotions", value=str(row["promotions"]))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="work", description="Work one shift.")
    async def work(self, interaction: discord.Interaction) -> None:
        uid = interaction.user.id
        row = await self.bot.db.fetchone(
            "SELECT job_id, level FROM user_jobs WHERE user_id=?", (uid,)
        )
        if row is None:
            await interaction.response.send_message(
                embed=error("You have no career. Use `/jobs` first."),
                ephemeral=True,
            )
            return
        job = by_id(row["job_id"])
        if job is None:
            await interaction.response.send_message(
                embed=error("Career invalid — pick a new one."), ephemeral=True
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
                "UPDATE user_stats SET jobs_completed = jobs_completed + 1 WHERE user_id=?",
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
                embed=error(
                    "Shift cooldown",
                    f"{m}m {s}s remaining before your next shift.",
                ),
                ephemeral=True,
            )
            return
        await self.bot.achievements.check_and_grant(uid)
        await interaction.response.send_message(
            embed=success(
                f"Worked as {job.name}",
                f"Earned **{qc(pay)}** and gained **{xp_gain} XP**.",
            )
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
