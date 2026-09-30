from datetime import datetime

import pygame

from virus_exe.game.state import GameState
from virus_exe.ui import theme
from virus_exe.ui.widgets import Button


class Renderer:
    def __init__(self) -> None:
        self.fonts = {
            "title": self._font(25, True),
            "heading": self._font(15, True),
            "body": self._font(13),
            "small": self._font(11),
            "tiny": self._font(10),
        }

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        candidates = ["PxPlus IBM VGA8", "Terminus", "DejaVu Sans Mono", "Liberation Mono", "Consolas"]
        for candidate in candidates:
            path = pygame.font.match_font(candidate, bold=bold)
            if path:
                return pygame.font.Font(path, size)
        return pygame.font.Font(None, size)

    def text(self, surface: pygame.Surface, value: str, position: tuple[int, int], style: str = "body", color: str = theme.TEXT) -> None:
        surface.blit(self.fonts[style].render(value, False, color), position)

    def panel(self, surface: pygame.Surface, rect: pygame.Rect, title: str | None = None) -> None:
        pygame.draw.rect(surface, theme.PANEL, rect)
        pygame.draw.rect(surface, theme.BORDER, rect, width=1)
        pygame.draw.line(surface, theme.GREEN_DARK, (rect.x + 1, rect.y + 1), (rect.right - 2, rect.y + 1), 1)
        if title:
            self.text(surface, f"> {title}", (rect.x + 14, rect.y + 10), "heading", theme.GREEN)
            pygame.draw.line(surface, theme.BORDER, (rect.x + 14, rect.y + 34), (rect.right - 14, rect.y + 34), 1)

    def bar(self, surface: pygame.Surface, rect: pygame.Rect, value: float, color: str, background: str = theme.PANEL_ALT) -> None:
        pygame.draw.rect(surface, background, rect)
        filled = rect.copy()
        filled.width = max(0, min(rect.width, int(rect.width * max(0.0, min(100.0, value)) / 100.0)))
        if filled.width:
            pygame.draw.rect(surface, color, filled)
        pygame.draw.rect(surface, theme.BORDER, rect, width=1)

    def render(self, surface: pygame.Surface, state: GameState, buttons: list[Button]) -> None:
        surface.fill(theme.BG)
        self._header(surface, state)
        self._map(surface, state)
        self._sidebar(surface, state)
        self._footer(surface, state, buttons)
        self._crt_overlay(surface, state)

    def _header(self, surface: pygame.Surface, state: GameState) -> None:
        width = surface.get_width()
        pygame.draw.rect(surface, theme.PANEL, pygame.Rect(0, 0, width, 68))
        pygame.draw.line(surface, theme.BORDER, (0, 67), (width, 67), 1)
        self.text(surface, "VIRUS.EXE", (24, 12), "title", theme.GREEN)
        self.text(surface, f"SYS://{state.graph.name}   LEVEL {state.level_index:02d}/{state.total_levels:02d}", (24, 45), "tiny", theme.MUTED)
        current_time = datetime.now().strftime("%H:%M:%S")
        status_color = theme.GREEN if state.is_playing else theme.YELLOW if state.status == "WON" else theme.RED
        self.text(surface, f"STATUS: {state.security.warning_level}", (850, 14), "small", status_color)
        self.text(surface, current_time, (1140, 14), "small", theme.TEXT)
        self.text(surface, f"RUN {int(state.elapsed):04d}s", (1140, 40), "tiny", theme.MUTED)
        pygame.draw.rect(surface, theme.GREEN_DARK, pygame.Rect(790, 48, 16, 3))
        pygame.draw.rect(surface, theme.GREEN_DARK, pygame.Rect(810, 48, 8, 3))
        pygame.draw.rect(surface, theme.GREEN_DARK, pygame.Rect(822, 48, 4, 3))

    def _map(self, surface: pygame.Surface, state: GameState) -> None:
        rect = pygame.Rect(20, 84, 790, 500)
        self.panel(surface, rect, "SYSTEM TOPOLOGY")
        self.text(surface, "SELECT A MODULE TO INSPECT", (rect.right - 220, rect.y + 12), "tiny", theme.MUTED)
        origin = (30, 92)
        positions = {node_id: (origin[0] + node.x, origin[1] + node.y) for node_id, node in state.graph.nodes.items()}
        for connection in state.graph.connections:
            start = positions[connection.source]
            end = positions[connection.target]
            color = theme.ORANGE if connection.firewall else theme.GREEN_DARK
            width = 3 if connection.firewall else 2
            pygame.draw.line(surface, color, start, end, width)
            if connection.firewall:
                middle = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
                pygame.draw.line(surface, theme.RED, (middle[0] - 5, middle[1] - 5), (middle[0] + 5, middle[1] + 5), 2)
                pygame.draw.line(surface, theme.RED, (middle[0] - 5, middle[1] + 5), (middle[0] + 5, middle[1] - 5), 2)
        if state.virus.infection_job:
            job = state.virus.infection_job
            source = positions[state.virus.current_node_id]
            target = positions[job.node_id]
            progress = job.progress / 100.0
            packet = (int(source[0] + (target[0] - source[0]) * progress), int(source[1] + (target[1] - source[1]) * progress))
            pygame.draw.rect(surface, theme.YELLOW, pygame.Rect(packet[0] - 4, packet[1] - 4, 8, 8))
            pygame.draw.rect(surface, theme.TEXT, pygame.Rect(packet[0] - 8, packet[1] - 8, 16, 16), 1)
        for node in state.graph.nodes.values():
            self._node(surface, state, node, positions[node.node_id])
        self.text(surface, "SOLID LINK  ACTIVE CONNECTION", (rect.x + 18, rect.bottom - 24), "tiny", theme.GREEN_DARK)
        self.text(surface, "X LINK  FIREWALL PRESSURE", (rect.x + 230, rect.bottom - 24), "tiny", theme.ORANGE)

    def _node(self, surface: pygame.Surface, state: GameState, node, center: tuple[int, int]) -> None:
        width, height = 136, 68
        rect = pygame.Rect(center[0] - width // 2, center[1] - height // 2, width, height)
        fill = "#0b220d" if node.node_id == state.virus.current_node_id else theme.PANEL_ALT
        border = theme.GREEN if node.node_id == state.virus.current_node_id else theme.BORDER
        if node.node_id == state.virus.selected_node_id:
            border = theme.CYAN
        if node.isolated:
            border = theme.RED
        pygame.draw.rect(surface, fill, rect)
        pygame.draw.rect(surface, border, rect, width=2 if node.node_id in {state.virus.current_node_id, state.virus.selected_node_id} else 1)
        name_color = theme.MUTED if not node.discovered else theme.TEXT
        self.text(surface, node.short_name, (rect.x + 10, rect.y + 8), "heading", name_color)
        self.text(surface, f"INF {node.infection:03.0f}%", (rect.x + 10, rect.y + 31), "tiny", theme.GREEN if node.infection > 0 else theme.MUTED)
        self.bar(surface, pygame.Rect(rect.x + 10, rect.y + 49, width - 20, 7), node.infection, theme.GREEN_DARK)
        if node.node_id == state.virus.current_node_id:
            pygame.draw.rect(surface, theme.GREEN, pygame.Rect(rect.right - 16, rect.y + 9, 7, 7))
        if node.node_id == state.scan_target_id:
            pygame.draw.rect(surface, theme.RED, pygame.Rect(rect.right - 18, rect.y + 7, 11, 11), 1)

    def _sidebar(self, surface: pygame.Surface, state: GameState) -> None:
        rect = pygame.Rect(830, 84, 430, 500)
        self.panel(surface, rect, "MISSION CONTROL")
        self.text(surface, f"LVL {state.level_index:02d} // {state.mission.title}", (rect.x + 16, rect.y + 47), "heading", theme.TEXT)
        self.text(surface, "OBJECTIVES", (rect.x + 16, rect.y + 72), "tiny", theme.MUTED)
        row_y = rect.y + 88
        for node, progress, complete in state.objective_progress:
            marker = "OK" if complete else ">>"
            color = theme.GREEN if complete else theme.TEXT
            self.text(surface, f"{marker} {node.short_name:<5} {node.infection:03.0f}%", (rect.x + 16, row_y), "tiny", color)
            self.bar(surface, pygame.Rect(rect.x + 175, row_y + 2, 235, 6), progress, theme.GREEN_DARK if complete else theme.GREEN)
            row_y += 22
        metrics_y = row_y + 8
        self.text(surface, f"DETECTION  {state.security.detection:05.1f}% / {state.mission.detection_limit:03.0f}", (rect.x + 16, metrics_y), "small", self._detection_color(state.security.detection))
        self.bar(surface, pygame.Rect(rect.x + 16, metrics_y + 20, rect.width - 32, 8), state.security.detection, self._detection_color(state.security.detection))
        self.text(surface, f"AV SCAN  {state.graph.get_node(state.scan_target_id).short_name}", (rect.x + 16, metrics_y + 45), "small", theme.ORANGE)
        scan_progress = state.security.scan_elapsed / state.security.scan_duration * 100.0
        self.bar(surface, pygame.Rect(rect.x + 16, metrics_y + 65, rect.width - 32, 6), scan_progress, theme.ORANGE)
        resources_y = metrics_y + 96
        self.text(surface, "RESOURCES", (rect.x + 16, resources_y), "tiny", theme.MUTED)
        self._resource(surface, rect.x + 16, resources_y + 18, "CPU", state.cpu, theme.BLUE)
        self._resource(surface, rect.x + 16, resources_y + 40, "MEMORY", state.memory, theme.PURPLE)
        self._resource(surface, rect.x + 16, resources_y + 62, "NETWORK", state.network, theme.YELLOW)
        current_y = resources_y + 95
        current = state.current_node
        self.text(surface, f"CURRENT // {current.name}", (rect.x + 16, current_y), "small", theme.TEXT)
        self.text(surface, f"SECURITY {current.security:02d}   VALUE {current.value:02d}", (rect.x + 16, current_y + 20), "tiny", theme.MUTED)
        event_y = current_y + 49
        self.text(surface, "EVENT STREAM", (rect.x + 16, event_y), "tiny", theme.MUTED)
        y = event_y + 18
        for message in state.messages[-4:]:
            color = theme.GREEN if "COMPLETE" in message else theme.GREEN_DARK
            self.text(surface, message[-39:], (rect.x + 16, y), "tiny", color)
            y += 13

    def _resource(self, surface: pygame.Surface, x: int, y: int, label: str, value: float, color: str) -> None:
        self.text(surface, f"{label:<7} {value:05.1f}%", (x, y), "tiny", theme.TEXT)
        self.bar(surface, pygame.Rect(x + 95, y + 2, 275, 7), value, color)

    def _footer(self, surface: pygame.Surface, state: GameState, buttons: list[Button]) -> None:
        width = surface.get_width()
        pygame.draw.rect(surface, theme.PANEL, pygame.Rect(0, 600, width, 160))
        pygame.draw.line(surface, theme.BORDER, (0, 600), (width, 600), 1)
        self.text(surface, "OPERATIONS", (24, 616), "tiny", theme.MUTED)
        self.text(surface, "CRT ONLINE // 60HZ", (1045, 616), "tiny", theme.MUTED)
        for button in buttons:
            button.draw(surface, self.fonts["small"])
        if state.virus.infection_job:
            job = state.virus.infection_job
            self.text(surface, f"INFECTION PROCESS  {state.current_node.name}", (24, 728), "tiny", theme.YELLOW)
            self.bar(surface, pygame.Rect(230, 731, 320, 8), job.progress, theme.YELLOW)
        elif state.virus.is_hidden(state.elapsed):
            self.text(surface, "STEALTH CLOAK ACTIVE", (24, 728), "tiny", theme.CYAN)
        else:
            self.text(surface, "READY FOR INPUT", (24, 728), "tiny", theme.MUTED)
        self.text(surface, "S SCAN   I INFECT   H HIDE   M MOVE", (760, 728), "tiny", theme.MUTED)

    def render_end_screen(self, surface: pygame.Surface, state: GameState, chart: pygame.Surface | None, next_available: bool = False) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 4, 0, 225))
        surface.blit(overlay, (0, 0))
        box = pygame.Rect(140, 60, 1000, 630)
        pygame.draw.rect(surface, theme.PANEL, box)
        accent = theme.GREEN if state.status == "WON" else theme.RED
        pygame.draw.rect(surface, accent, box, width=2)
        pygame.draw.line(surface, accent, (box.x + 2, box.y + 2), (box.right - 3, box.y + 2), 2)
        title = "LEVEL CLEAR" if state.status == "WON" else "SYSTEM FAILURE"
        self.text(surface, f"{title} // {state.level_index:02d}", (box.x + 32, box.y + 26), "title", accent)
        self.text(surface, state.end_reason, (box.x + 34, box.y + 65), "small", theme.TEXT)
        result = state.result()
        rows = [
            ("SYSTEM INFECTED", f"{result.total_infection:05.1f}%"),
            ("FINAL DETECTION", f"{result.detection:05.1f}%"),
            ("OPERATIONS", str(result.infections)),
            ("MOVES", str(result.moves)),
            ("TIME", f"{result.duration:05.1f}s"),
            ("SCORE", str(result.score)),
        ]
        y = box.y + 116
        for label, value in rows:
            self.text(surface, label, (box.x + 36, y), "small", theme.MUTED)
            self.text(surface, value, (box.x + 245, y), "heading", accent if label == "SCORE" else theme.TEXT)
            y += 28
        self.text(surface, "OBJECTIVE STATUS", (box.x + 36, box.y + 308), "tiny", theme.MUTED)
        objective_y = box.y + 328
        for node, progress, complete in state.objective_progress:
            marker = "[OK]" if complete else "[--]"
            color = theme.GREEN if complete else theme.RED
            self.text(surface, f"{marker} {node.name:<12} {progress:03.0f}%", (box.x + 36, objective_y), "small", color)
            objective_y += 22
        if chart:
            surface.blit(chart, (box.x + 500, box.y + 105))
        prompt = "PRESS N FOR NEXT LEVEL" if next_available and state.status == "WON" else "PRESS R TO REBOOT SESSION"
        self.text(surface, prompt, (box.x + 36, box.bottom - 38), "small", theme.YELLOW)
        self._crt_overlay(surface, state, intense=True)

    def _crt_overlay(self, surface: pygame.Surface, state: GameState, intense: bool = False) -> None:
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        line_alpha = 38 if intense else 25
        for y in range(0, height, 4):
            pygame.draw.line(overlay, (0, 30, 4, line_alpha), (0, y), (width, y), 1)
        tick = pygame.time.get_ticks()
        if tick % 1700 < 70 or intense and tick % 1100 < 65:
            glitch_y = 80 + (tick // 13) % max(1, height - 100)
            pygame.draw.rect(overlay, (255, 40, 30, 32), pygame.Rect(0, glitch_y, width, 2))
            pygame.draw.rect(overlay, (30, 255, 90, 22), pygame.Rect(18, glitch_y + 3, width - 36, 2))
        pygame.draw.rect(overlay, (45, 255, 75, 70), pygame.Rect(5, 5, width - 10, height - 10), 1)
        surface.blit(overlay, (0, 0))

    def _detection_color(self, value: float) -> str:
        if value < 50:
            return theme.GREEN
        if value < 70:
            return theme.YELLOW
        return theme.RED
