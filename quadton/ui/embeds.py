from __future__ import annotations

import discord

COLOR_PRIMARY = 0x5865F2
COLOR_SUCCESS = 0x2ECC71
COLOR_ERROR = 0xE74C3C
COLOR_WARNING = 0xF1C40F
COLOR_MARKET = 0x9B59B6
COLOR_MUTED = 0x95A5A6


def qc(amount: int) -> str:
    """Format an integer QC amount: 1,250 QC."""
    return f"{amount:,} QC"


def success(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(
        title=f"✅ {title}",
        description=description or None,
        color=COLOR_SUCCESS,
    )


def error(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(
        title=f"⚠️ {title}",
        description=description or None,
        color=COLOR_ERROR,
    )


def info(title: str, description: str = "") -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description or None,
        color=COLOR_PRIMARY,
    )


def empty_state(message: str) -> discord.Embed:
    return discord.Embed(
        description=f"*{message}*",
        color=COLOR_MUTED,
    )
