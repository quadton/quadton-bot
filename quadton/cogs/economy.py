from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from quadton.services.currency import (
    DuplicateTransaction,
    InsufficientFunds,
)


def fmt(n: int) -> str:
    return f"{n:,} QC"


class Economy(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot

    @app_commands.command(description="Show wallet and bank balances.")
    async def balance(
        self, interaction: discord.Interaction, member: discord.Member | None = None
    ) -> None:
        target = member or interaction.user
        wallet = await self.bot.currency.get_balance(target.id, "wallet")
        bank = await self.bot.currency.get_balance(target.id, "bank")
        embed = discord.Embed(
            title=f"{target.display_name}'s Balance", color=0x2B8A3E
        )
        embed.add_field(name="Wallet", value=fmt(wallet))
        embed.add_field(name="Bank", value=fmt(bank))
        embed.add_field(name="Total", value=fmt(wallet + bank))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Deposit QC into your bank.")
    async def deposit(self, interaction: discord.Interaction, amount: int) -> None:
        if amount <= 0:
            await interaction.response.send_message(
                "Amount must be positive.", ephemeral=True
            )
            return
        try:
            await self.bot.currency.deposit(interaction.user.id, amount)
        except InsufficientFunds:
            await interaction.response.send_message(
                "Insufficient wallet balance.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Deposited {fmt(amount)}.", ephemeral=True
        )

    @app_commands.command(description="Withdraw QC from your bank.")
    async def withdraw(self, interaction: discord.Interaction, amount: int) -> None:
        if amount <= 0:
            await interaction.response.send_message(
                "Amount must be positive.", ephemeral=True
            )
            return
        try:
            await self.bot.currency.withdraw(interaction.user.id, amount)
        except InsufficientFunds:
            await interaction.response.send_message(
                "Insufficient bank balance.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Withdrew {fmt(amount)}.", ephemeral=True
        )

    @app_commands.command(description="Pay QC to another member.")
    async def pay(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: int,
    ) -> None:
        if member.id == interaction.user.id:
            await interaction.response.send_message(
                "You cannot pay yourself.", ephemeral=True
            )
            return
        if member.bot:
            await interaction.response.send_message(
                "You cannot pay a bot.", ephemeral=True
            )
            return
        if amount <= 0:
            await interaction.response.send_message(
                "Amount must be positive.", ephemeral=True
            )
            return
        key = f"pay:{interaction.id}"
        try:
            await self.bot.currency.transfer(
                interaction.user.id, member.id, amount,
                "PLAYER_TRANSFER", idempotency_key=key,
            )
        except InsufficientFunds:
            await interaction.response.send_message(
                "Insufficient funds.", ephemeral=True
            )
            return
        except DuplicateTransaction:
            await interaction.response.send_message(
                "This payment was already processed.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Sent {fmt(amount)} to {member.mention}."
        )

    @app_commands.command(description="Show your recent transaction history.")
    async def history(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.currency.history(interaction.user.id, limit=10)
        if not rows:
            await interaction.response.send_message(
                "No transactions yet.", ephemeral=True
            )
            return
        lines = []
        for r in rows:
            sign = "+" if r["to_user"] == interaction.user.id else "-"
            lines.append(
                f"`{r['tx_type']}` {sign}{r['amount']:,} QC "
                f"(<t:{r['created_at']}:R>)"
            )
        embed = discord.Embed(
            title="Recent Transactions",
            description="\n".join(lines),
            color=0x5865F2,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot) -> None:
    await bot.add_cog(Economy(bot))
