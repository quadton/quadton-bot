from __future__ import annotations

from typing import Awaitable, Callable, Sequence

import discord
from discord import ui

from quadton.ui.embeds import error


class OwnerRestrictedView(ui.View):
    """Base view that only the invoker may interact with.

    Handles:
      - ownership enforcement (per-interaction check)
      - timeout cleanup (disables children, edits the message)
      - error fallback so a thrown callback never leaves the user hanging
    """

    def __init__(self, owner_id: int, *, timeout: float = 180.0) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This menu belongs to another user. Run the command yourself.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True  # type: ignore[attr-defined]
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass

    async def on_error(
        self,
        interaction: discord.Interaction,
        error_: Exception,
        item: ui.Item,
    ) -> None:
        msg = "Something went wrong. Please try again."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def start(
        self,
        interaction: discord.Interaction,
        *,
        embed: discord.Embed | None = None,
        ephemeral: bool = True,
    ) -> None:
        """Send the view, and remember the message so on_timeout can edit it."""
        if interaction.response.is_done():
            self.message = await interaction.followup.send(
                embed=embed, view=self, ephemeral=ephemeral, wait=True
            )
        else:
            await interaction.response.send_message(
                embed=embed, view=self, ephemeral=ephemeral
            )
            self.message = await interaction.original_response()


class Paginator(OwnerRestrictedView):
    """Two-button paginator. Subclass and implement ``render_page``."""

    def __init__(
        self, owner_id: int, total_pages: int, *, timeout: float = 180.0
    ) -> None:
        super().__init__(owner_id, timeout=timeout)
        self.page = 0
        self.total_pages = max(1, total_pages)
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        for child in self.children:
            if not isinstance(child, ui.Button):
                continue
            if child.custom_id == "quadton_prev":
                child.disabled = self.page == 0
            elif child.custom_id == "quadton_next":
                child.disabled = self.page >= self.total_pages - 1

    async def render_page(self, page: int) -> discord.Embed:
        raise NotImplementedError

    @ui.button(
        label="◀ Prev",
        style=discord.ButtonStyle.secondary,
        custom_id="quadton_prev",
        row=0,
    )
    async def prev_button(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        if self.page > 0:
            self.page -= 1
        self._sync_buttons()
        embed = await self.render_page(self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    @ui.button(
        label="Next ▶",
        style=discord.ButtonStyle.secondary,
        custom_id="quadton_next",
        row=0,
    )
    async def next_button(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        if self.page < self.total_pages - 1:
            self.page += 1
        self._sync_buttons()
        embed = await self.render_page(self.page)
        await interaction.response.edit_message(embed=embed, view=self)


class ConfirmView(OwnerRestrictedView):
    """Yes / No confirmation. ``on_confirm`` is awaited if the user accepts."""

    def __init__(
        self,
        owner_id: int,
        *,
        on_confirm: Callable[[discord.Interaction], Awaitable[None]],
        timeout: float = 60.0,
    ) -> None:
        super().__init__(owner_id, timeout=timeout)
        self._on_confirm = on_confirm

    @ui.button(label="Confirm", style=discord.ButtonStyle.danger, row=0)
    async def confirm(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await self._on_confirm(interaction)
        try:
            if self.message is not None:
                await self.message.edit(view=self)
        except discord.HTTPException:
            pass
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=0)
    async def cancel(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        await interaction.response.edit_message(
            embed=error("Cancelled", "No changes were made."),
            view=self,
        )
        self.stop()


class SelectView(OwnerRestrictedView):
    """View containing a single dropdown.

    ``on_select`` receives the raw selected value (str) and is awaited with
    the interaction, so it can edit the message or send new content.
    """

    def __init__(
        self,
        owner_id: int,
        *,
        placeholder: str,
        options: Sequence[discord.SelectOption],
        on_select: Callable[[discord.Interaction, str], Awaitable[None]],
        timeout: float = 180.0,
        min_values: int = 1,
        max_values: int = 1,
    ) -> None:
        super().__init__(owner_id, timeout=timeout)
        self._on_select = on_select
        select: ui.Select = ui.Select(
            placeholder=placeholder,
            options=list(options),
            min_values=min_values,
            max_values=max_values,
        )
        select.callback = self._handle  # type: ignore[method-assign]
        self.add_item(select)

    async def _handle(self, interaction: discord.Interaction) -> None:
        values = interaction.data.get("values", []) if interaction.data else []
        if not values:
            return
        await self._on_select(interaction, values[0])
