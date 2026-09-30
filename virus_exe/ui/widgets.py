from dataclasses import dataclass

import pygame

from virus_exe.ui import theme


@dataclass(slots=True)
class Button:
    rect: pygame.Rect
    label: str
    action: str
    hotkey: str
    active: bool = True
    hover: bool = False

    def update_hover(self, position: tuple[int, int]) -> None:
        self.hover = self.rect.collidepoint(position)

    def clicked(self, event: pygame.event.Event) -> bool:
        return (
            self.active
            and event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        fill = theme.GREEN_DARK if self.hover and self.active else theme.PANEL_ALT
        border = theme.GREEN if self.hover and self.active else theme.BORDER
        if not self.active:
            fill = theme.PANEL
            border = theme.BORDER
        pygame.draw.rect(surface, fill, self.rect)
        pygame.draw.rect(surface, border, self.rect, width=1)
        color = theme.TEXT if self.active else theme.MUTED
        label = f"[{self.hotkey}] {self.label}"
        text = font.render(label, False, color)
        surface.blit(text, text.get_rect(center=self.rect.center))
