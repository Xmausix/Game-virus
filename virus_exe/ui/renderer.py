from datetime import datetime

import pygame

from virus_exe.game.state import CLIENT_ORDERS, GameState
from virus_exe.ui import theme
from virus_exe.ui.settings import Settings
from virus_exe.virus.catalog import ATTACK_METHODS, VIRUS_PROFILES
from virus_exe.ui.widgets import Button


class Renderer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.fonts = {
            "title": self._font(25, True),
            "heading": self._font(15, True),
            "body": self._font(13),
            "small": self._font(11),
            "tiny": self._font(10),
        }

    def _font(self, size: int, bold: bool = False) -> pygame.font.Font:
        scaled_size = max(8, round(size * self.settings.font_size / 11))
        candidates = [self.settings.font_name, "PxPlus IBM VGA8", "Terminus", "DejaVu Sans Mono", "Liberation Mono", "Consolas"]
        for candidate in candidates:
            path = pygame.font.match_font(candidate, bold=bold)
            if path:
                return pygame.font.Font(path, scaled_size)
        return pygame.font.Font(None, size)

    def text(self, surface: pygame.Surface, value: str, position: tuple[int, int], style: str = "body", color: str = theme.TEXT) -> None:
        if self.settings.high_contrast and color in {theme.MUTED, theme.GREEN_DARK}:
            color = theme.TEXT
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

    def render(self, surface: pygame.Surface, state: GameState, buttons: list[Button], console_input: str = "", console_active: bool = False) -> None:
        surface.fill(theme.BG)
        self._header(surface, state)
        self._map(surface, state)
        self._control_deck(surface, state)
        self._bottom(surface, state, buttons, console_input, console_active)
        self._crt_overlay(surface, state)

    def _header(self, surface: pygame.Surface, state: GameState) -> None:
        width = surface.get_width()
        pygame.draw.rect(surface, theme.PANEL, pygame.Rect(0, 0, width, 66))
        pygame.draw.line(surface, theme.BORDER, (0, 65), (width, 65), 1)
        self.text(surface, "VIRUS.EXE", (24, 10), "title", theme.GREEN)
        self.text(surface, f"SYS://{state.graph.name}   LEVEL {state.level_index:02d}/{state.total_levels:02d}", (24, 43), "tiny", theme.MUTED)
        self.text(surface, f"VIRUS {state.virus_profile.code_name} // {state.attack_method.label}", (440, 15), "small", theme.CYAN)
        self.text(surface, f"INTEL {state.intel:04.1f}", (440, 40), "tiny", theme.MUTED)
        current_time = datetime.now().strftime("%H:%M:%S")
        status_color = theme.GREEN if state.is_playing else theme.YELLOW if state.status == "WON" else theme.RED
        self.text(surface, f"STATUS: {state.security.warning_level}", (850, 12), "small", status_color)
        self.text(surface, f"DET {state.security.detection:04.1f}%", (850, 39), "tiny", status_color)
        self.text(surface, current_time, (1140, 12), "small", theme.TEXT)
        self.text(surface, f"RUN {int(state.elapsed):04d}s", (1140, 39), "tiny", theme.MUTED)

    def _map(self, surface: pygame.Surface, state: GameState) -> None:
        rect = pygame.Rect(20, 82, 790, 438)
        self.panel(surface, rect, "SYSTEM TOPOLOGY // LIVE GRAPH")
        inner = pygame.Rect(rect.x + 2, rect.y + 38, rect.width - 4, rect.height - 66)
        surface.set_clip(inner)
        for x in range(inner.left, inner.right, 40):
            pygame.draw.line(surface, "#0b1b0d", (x, inner.top), (x, inner.bottom), 1)
        for y in range(inner.top, inner.bottom, 40):
            pygame.draw.line(surface, "#0b1b0d", (inner.left, y), (inner.right, y), 1)
        surface.set_clip(None)
        origin = (30, 78)
        positions = {node_id: (origin[0] + node.x, origin[1] + node.y) for node_id, node in state.graph.nodes.items()}
        for connection in state.graph.connections:
            start = positions[connection.source]
            end = positions[connection.target]
            active_path = {connection.source, connection.target} == {state.virus.current_node_id, state.virus.selected_node_id}
            color = theme.CYAN if active_path else theme.ORANGE if connection.firewall else theme.GREEN_DARK
            width = 3 if connection.firewall or active_path else 2
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
        self.text(surface, "ACTIVE LINK", (rect.x + 18, rect.bottom - 22), "tiny", theme.CYAN)
        self.text(surface, "X FIREWALL", (rect.x + 128, rect.bottom - 22), "tiny", theme.ORANGE)
        self.text(surface, "AN ANALYZED", (rect.x + 250, rect.bottom - 22), "tiny", theme.GREEN_DARK)
        self.text(surface, "ISO ISOLATED", (rect.x + 380, rect.bottom - 22), "tiny", theme.RED)

    def _node(self, surface: pygame.Surface, state: GameState, node, center: tuple[int, int]) -> None:
        width, height = 142, 72
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
        self.text(surface, node.short_name, (rect.x + 9, rect.y + 7), "heading", name_color)
        status = "ISO" if node.isolated else "AN" if node.analyzed else node.category.upper()[:3]
        self.text(surface, status, (rect.right - 36, rect.y + 9), "tiny", theme.RED if node.isolated else theme.GREEN_DARK)
        self.text(surface, f"INF {node.infection:03.0f}%", (rect.x + 9, rect.y + 30), "tiny", theme.GREEN if node.infection > 0 else theme.MUTED)
        self.text(surface, f"VULN {node.vulnerability:02d}  SEC {node.security:02d}", (rect.x + 9, rect.y + 43), "tiny", theme.MUTED)
        self.bar(surface, pygame.Rect(rect.x + 9, rect.y + 60, width - 18, 6), node.infection, theme.GREEN_DARK)
        if node.node_id == state.scan_target_id:
            pygame.draw.rect(surface, theme.RED, pygame.Rect(rect.right - 18, rect.y + 7, 11, 11), 1)

    def _control_deck(self, surface: pygame.Surface, state: GameState) -> None:
        rect = pygame.Rect(830, 82, 430, 438)
        self.panel(surface, rect, "CONTROL DECK")
        self.text(surface, f"LVL {state.level_index:02d} // {state.mission.title}", (rect.x + 16, rect.y + 47), "heading", theme.TEXT)
        self.text(surface, "OBJECTIVES", (rect.x + 16, rect.y + 70), "tiny", theme.MUTED)
        row_y = rect.y + 84
        for node, progress, complete in state.objective_progress:
            marker = "OK" if complete else ">>"
            color = theme.GREEN if complete else theme.TEXT
            self.text(surface, f"{marker} {node.short_name:<5} {node.infection:03.0f}%", (rect.x + 16, row_y), "tiny", color)
            self.bar(surface, pygame.Rect(rect.x + 170, row_y + 2, 240, 6), progress, theme.GREEN_DARK if complete else theme.GREEN)
            row_y += 17
        metrics_y = row_y + 7
        self.text(surface, f"DETECTION {state.security.detection:05.1f}% / {state.mission.detection_limit:03.0f}", (rect.x + 16, metrics_y), "small", self._detection_color(state.security.detection))
        self.bar(surface, pygame.Rect(rect.x + 16, metrics_y + 19, rect.width - 32, 8), state.security.detection, self._detection_color(state.security.detection))
        self.text(surface, f"ANTIVIRUS // {state.graph.get_node(state.scan_target_id).short_name}", (rect.x + 16, metrics_y + 41), "tiny", theme.ORANGE)
        scan_progress = state.security.scan_elapsed / state.security.scan_duration * 100.0
        self.bar(surface, pygame.Rect(rect.x + 170, metrics_y + 43, 240, 6), scan_progress, theme.ORANGE)
        target_y = metrics_y + 67
        target = state.selected_node
        self.text(surface, f"TARGET // {target.name}", (rect.x + 16, target_y), "small", theme.CYAN)
        self.text(surface, f"SEC {target.security:02d}   VULN {target.vulnerability:02d}   USER {target.user_activity:02d}", (rect.x + 16, target_y + 18), "tiny", theme.MUTED)
        process_list = ", ".join(target.processes) if target.processes else "NO PROCESS DATA"
        self.text(surface, process_list[:48], (rect.x + 16, target_y + 34), "tiny", theme.TEXT if target.analyzed else theme.MUTED)
        loadout_y = target_y + 59
        self.text(surface, f"LOADOUT // {state.virus_profile.code_name} + {state.attack_method.label}", (rect.x + 16, loadout_y), "small", theme.YELLOW)
        self.text(surface, f"PWR {state.virus_profile.power * 100:02.0f}  STEALTH {state.virus_profile.stealth * 100:02.0f}  SPREAD {state.virus_profile.spread * 100:02.0f}", (rect.x + 16, loadout_y + 17), "tiny", theme.MUTED)
        method = state.attack_method
        cooldown = max(0.0, state.cooldowns.get(method.method_id, 0.0) - state.elapsed)
        self.text(surface, f"COST INTEL {method.intel_cost:02.0f}  CD {cooldown:04.1f}s  {'REMOTE' if method.remote else 'LOCAL'}", (rect.x + 16, loadout_y + 32), "tiny", theme.MUTED)

    def _bottom(self, surface: pygame.Surface, state: GameState, buttons: list[Button], console_input: str, console_active: bool) -> None:
        left = pygame.Rect(20, 535, 790, 210)
        right = pygame.Rect(830, 535, 430, 210)
        self.panel(surface, left, "TACTICAL TERMINAL")
        self.panel(surface, right, "LIVE READOUT")
        self.text(surface, "OPERATIONS", (left.x + 16, left.y + 41), "tiny", theme.MUTED)
        self.text(surface, f"CONSOLE {'ACTIVE' if console_active else 'STANDBY'} // TAB TO TOGGLE", (left.right - 310, left.y + 12), "tiny", theme.YELLOW if console_active else theme.MUTED)
        for button in buttons:
            button.draw(surface, self.fonts["tiny"])
        y = left.y + 105
        for line in state.console_lines[-6:]:
            color = theme.GREEN if "SUCCESS" in line or "COMPLETE" in line else theme.GREEN_DARK
            self.text(surface, line[-76:], (left.x + 16, y), "tiny", color)
            y += 14
        prompt_color = theme.GREEN if console_active else theme.MUTED
        cursor = "_" if console_active and pygame.time.get_ticks() % 1000 < 650 else " "
        self.text(surface, f"root@virus-exe:~# {console_input}{cursor}", (left.x + 16, left.bottom - 18), "tiny", prompt_color)
        self.text(surface, "E EDITOR // R RESTART", (left.right - 170, left.bottom - 18), "tiny", theme.MUTED)
        self._readout(surface, right, state)

    def _readout(self, surface: pygame.Surface, rect: pygame.Rect, state: GameState) -> None:
        self.text(surface, f"CPU       {state.cpu:05.1f}%", (rect.x + 16, rect.y + 43), "tiny", theme.TEXT)
        self.bar(surface, pygame.Rect(rect.x + 112, rect.y + 45, 295, 7), state.cpu, theme.BLUE)
        self.text(surface, f"MEMORY    {state.memory:05.1f}%", (rect.x + 16, rect.y + 62), "tiny", theme.TEXT)
        self.bar(surface, pygame.Rect(rect.x + 112, rect.y + 64, 295, 7), state.memory, theme.PURPLE)
        self.text(surface, f"NETWORK   {state.network:05.1f}%", (rect.x + 16, rect.y + 81), "tiny", theme.TEXT)
        self.bar(surface, pygame.Rect(rect.x + 112, rect.y + 83, 295, 7), state.network, theme.YELLOW)
        self.text(surface, f"INTEL     {state.intel:05.1f}%", (rect.x + 16, rect.y + 100), "tiny", theme.TEXT)
        self.bar(surface, pygame.Rect(rect.x + 112, rect.y + 102, 295, 7), state.intel, theme.CYAN)
        self.text(surface, "ACTION QUEUE", (rect.x + 16, rect.y + 124), "tiny", theme.MUTED)
        if state.virus.infection_job:
            job = state.virus.infection_job
            self.text(surface, f"RUNNING {job.method_id.upper()} -> {job.node_id.upper()} {job.progress:03.0f}%", (rect.x + 16, rect.y + 141), "tiny", theme.YELLOW)
        else:
            self.text(surface, "IDLE // READY FOR COMMAND", (rect.x + 16, rect.y + 141), "tiny", theme.GREEN_DARK)
        self.text(surface, "WORLD EVENTS", (rect.x + 16, rect.y + 163), "tiny", theme.MUTED)
        events = state.world_events[-2:] or ["NO RECENT EVENTS"]
        for index, event in enumerate(events):
            self.text(surface, event[:49], (rect.x + 16, rect.y + 179 + index * 13), "tiny", theme.ORANGE if "ISOLATION" in event else theme.MUTED)

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

    def render_console(self, surface: pygame.Surface, state: GameState, console_input: str) -> None:
        surface.fill(theme.BG)
        panel = pygame.Rect(20, 20, 1240, 720)
        self.panel(surface, panel, "TACTICAL CONSOLE // FULLSCREEN")
        self.text(surface, f"SESSION TASK {state.tasks.current_index + 1:02d}/{len(state.tasks.tasks)}  VIRUS {state.virus_profile.code_name}  TARGET {state.selected_node.node_id.upper()}", (panel.x + 18, panel.y + 45), "small", theme.CYAN)
        self.text(surface, "PAUSED VIEW // ENTER COMMAND // ESC OR TAB RETURN", (panel.right - 395, panel.y + 45), "tiny", theme.MUTED)
        line_y = panel.y + 76
        visible = 34
        for line in state.console_lines[-visible:]:
            color = theme.GREEN if "SUCCESS" in line or "COMPLETE" in line or "TRUE" in line else theme.TEXT
            self.text(surface, line[:116], (panel.x + 18, line_y), "small", color)
            line_y += 17
        pygame.draw.line(surface, theme.BORDER, (panel.x + 18, 690), (panel.right - 18, 690), 1)
        cursor = "_" if pygame.time.get_ticks() % 1000 < 650 else " "
        self.text(surface, f"root@virus-exe:~# {console_input}{cursor}", (panel.x + 18, 707), "body", theme.GREEN)
        self._crt_overlay(surface, state, intense=True)

    def render_guide(self, surface: pygame.Surface, page: int) -> None:
        surface.fill(theme.BG)
        header = pygame.Rect(20, 20, 1240, 70)
        self.panel(surface, header, "VIRUS.EXE // OPERATIONS GUIDE")
        self.text(surface, f"PAGE {page + 1:02d}/03", (1100, 33), "small", theme.YELLOW)
        left = pygame.Rect(20, 105, 600, 610)
        right = pygame.Rect(640, 105, 620, 610)
        self.panel(surface, left, "REFERENCE")
        self.panel(surface, right, "DETAILS")
        if page == 0:
            left_lines = [
                "CORE LOOP",
                "SCAN -> ANALYZE -> CHOOSE LOADOUT",
                "MOVE OR LATERAL -> ATTACK -> HIDE",
                "",
                "VIEWS",
                "TAB OR C  OPEN FULLSCREEN CONSOLE",
                "E        OPEN VIRUS EDITOR",
                "G OR F1  OPEN THIS GUIDE",
                "ESC      RETURN TO GAME",
                "",
                "ACTIONS",
                "S  SCAN SYSTEM",
                "Q  ANALYZE TARGET",
                "I  INFECT WITH ARMED METHOD",
                "H  LOWER DETECTION",
                "M  MOVE ALONG ACTIVE LINK",
                "A  EXECUTE ARMED ATTACK",
                "",
                "STRATEGY",
                "ANALYZE TARGETS BEFORE USING LOUD",
                "METHODS. INTEL IS LIMITED PER LEVEL.",
                "ANTIVIRUS CAN ISOLATE HIGH-RISK NODES.",
            ]
            right_lines = [
                "READ THE SYSTEM",
                "SCAN REVEALS THE MAP AND BUILDS INTEL.",
                "ANALYZE REVEALS PROCESSES, VULN",
                "AND USER ACTIVITY. ANALYZED TARGETS",
                "GIVE BETTER ATTACK ODDS.",
                "",
                "RISK MODEL",
                "SECURITY REDUCES SUCCESS CHANCE.",
                "VULNERABILITY INCREASES SUCCESS.",
                "NOISE RAISES DETECTION.",
                "COOLDOWNS STOP ATTACK SPAM.",
                "",
                "WORLD RESPONSE",
                "AT HIGH DETECTION THE DEFENDER MAY",
                "ISOLATE A MODULE FOR A SHORT PERIOD.",
                "USER ACTIVITY CAN CHANGE EXPOSURE.",
            ]
        elif page == 1:
            left_lines = ["VIRUS PROFILES", ""] + [f"{p.code_name:<10} PWR {p.power * 100:02.0f}  STEALTH {p.stealth * 100:02.0f}  SPREAD {p.spread * 100:02.0f}" for p in VIRUS_PROFILES]
            right_lines = ["ATTACK METHODS", ""] + [f"{m.label:<10} {'REMOTE' if m.remote else 'LOCAL':<6} INTEL {m.intel_cost:02.0f}  CD {m.cooldown:02.0f}" for m in ATTACK_METHODS]
            right_lines += ["", "CUSTOM TOOLS", "The editor also supports fictional", "EXPLOIT, BACKDOOR, PAYLOAD and WORM", "tools created by the player.", "They exist only inside the game."]
        else:
            left_lines = [
                "VIRUS DSL",
                "VIRUS NAME",
                "POWER 0..100",
                "STEALTH 0..100",
                "SPREAD 0..100",
                "PERSISTENCE 0..100",
                "TOOL NAME TYPE POWER NOISE COST RANGE",
                "METHOD NAME",
                "RULE SIGNAL OP VALUE THEN ACTION",
                "END",
                "",
                "EXAMPLE TOOL",
                "TOOL GHOSTLINK TYPE BACKDOOR",
                "POWER 58 NOISE 7 COST 2 RANGE REMOTE",
            ]
            right_lines = [
                "EXAMPLE RULES",
                "RULE DETECTION > 60 THEN HIDE",
                "RULE SECURITY < 70 THEN ATTACK GHOSTLINK",
                "RULE CPU > 80 THEN WAIT",
                "",
                "TEST RESULT",
                "F5 RETURNS TRUE OR FALSE.",
                "F6 APPLIES ONLY A TRUE PROGRAM.",
                "A PROGRAM MUST HAVE VALID FIELDS,",
                "A VALID TOOL AND A TRIGGERED RULE.",
                "",
                "SAFETY",
                "NO PYTHON EXECUTION.",
                "NO EVAL OR EXEC.",
                "NO FILE, PROCESS OR NETWORK ACCESS.",
                "ONLY THE CLOSED DSL GRAMMAR IS READ.",
            ]
        self._draw_text_lines(surface, left_lines, left.x + 18, left.y + 46, 22, "small")
        self._draw_text_lines(surface, right_lines, right.x + 18, right.y + 46, 22, "small")
        self.text(surface, "LEFT/RIGHT PAGE   TAB CONSOLE   E EDITOR   ESC RETURN", (32, 730), "tiny", theme.YELLOW)
        self._crt_overlay(surface, None, intense=True)

    def _draw_text_lines(self, surface: pygame.Surface, lines: list[str], x: int, y: int, step: int, style: str) -> None:
        for index, line in enumerate(lines):
            color = theme.GREEN if line.endswith(":") or line in {"CORE LOOP", "VIEWS", "ACTIONS", "STRATEGY", "READ THE SYSTEM", "RISK MODEL", "WORLD RESPONSE", "VIRUS PROFILES", "ATTACK METHODS", "CUSTOM TOOLS", "VIRUS DSL", "EXAMPLE RULES", "TEST RESULT", "SAFETY"} else theme.TEXT
            self.text(surface, line[:58], (x, y + index * step), style, color)

    def render_editor(self, surface: pygame.Surface, editor) -> None:
        surface.fill(theme.BG)
        self.text(surface, "VIRUS.EXE // CUSTOM VIRUS EDITOR", (24, 14), "title", theme.GREEN)
        self.text(surface, "F5 TEST // F6 APPLY IF TRUE // F1 GUIDE // ESC RETURN", (650, 22), "tiny", theme.MUTED)
        code_rect = pygame.Rect(20, 58, 820, 650)
        test_rect = pygame.Rect(860, 58, 400, 650)
        self.panel(surface, code_rect, "SOURCE CODE")
        self.panel(surface, test_rect, "TEST OUTPUT")
        line_height = 22
        visible_lines = 26
        for visible_index in range(visible_lines):
            line_index = editor.scroll + visible_index
            if line_index >= len(editor.lines):
                break
            y = code_rect.y + 46 + visible_index * line_height
            if line_index == editor.row:
                pygame.draw.rect(surface, "#0b2b10", pygame.Rect(code_rect.x + 8, y - 2, code_rect.width - 16, line_height))
            self.text(surface, f"{line_index + 1:02d}", (code_rect.x + 16, y), "tiny", theme.MUTED)
            self.text(surface, editor.lines[line_index], (code_rect.x + 56, y), "small", theme.TEXT)
            if line_index == editor.row and pygame.time.get_ticks() % 1000 < 650:
                prefix = editor.lines[line_index][: editor.column]
                cursor_x = code_rect.x + 56 + self.fonts["small"].size(prefix)[0]
                pygame.draw.rect(surface, theme.GREEN, pygame.Rect(cursor_x, y, 7, 13))
        self.text(surface, editor.message, (test_rect.x + 18, test_rect.y + 48), "small", theme.YELLOW)
        if editor.result is None:
            self.text(surface, "NO TEST RUN", (test_rect.x + 18, test_rect.y + 84), "heading", theme.MUTED)
        else:
            result_color = theme.GREEN if editor.result.passed else theme.RED
            self.text(surface, f"RESULT: {'TRUE' if editor.result.passed else 'FALSE'}", (test_rect.x + 18, test_rect.y + 84), "heading", result_color)
            y = test_rect.y + 122
            for passed, label in editor.result.checks:
                self.text(surface, f"[{'TRUE' if passed else 'FALSE'}] {label}", (test_rect.x + 18, y), "tiny", theme.GREEN if passed else theme.RED)
                y += 18
            for error in editor.result.errors:
                self.text(surface, error[:44], (test_rect.x + 18, y), "tiny", theme.RED)
                y += 18
            if editor.result.program is not None:
                y += 10
                self.text(surface, "FICTIONAL TOOLS", (test_rect.x + 18, y), "tiny", theme.MUTED)
                y += 18
                for tool in editor.result.program.tools:
                    self.text(surface, f"{tool.tool_id:<12} {tool.tool_type:<9} {'REMOTE' if tool.remote else 'LOCAL'}", (test_rect.x + 18, y), "tiny", theme.CYAN)
                    y += 16
        self.text(surface, "EDITOR PAUSED GAME CLOCK // CTRL+S SAVE", (24, 730), "tiny", theme.YELLOW)
        self._crt_overlay(surface, None, intense=True)

    def render_menu(self, surface: pygame.Surface, selection: int, settings: Settings, has_save: bool = False) -> None:
        surface.fill(theme.BG)
        width, height = surface.get_size()
        box = pygame.Rect(width // 2 - 300, 90, 600, 580)
        self.panel(surface, box, "VIRUS.EXE // SIMULATION CONTROL")
        self.text(surface, "VIRUS.EXE", (box.x + 92, box.y + 68), "title", theme.GREEN)
        self.text(surface, "FICTIONAL NETWORK INFILTRATION LAB", (box.x + 96, box.y + 110), "small", theme.MUTED)
        options = ["NEW GAME", "CONTINUE", "SETTINGS", "EXIT GAME"] if has_save else ["NEW GAME", "SETTINGS", "EXIT GAME"]
        y = box.y + 170
        for index, option in enumerate(options):
            active = index == selection
            color = theme.YELLOW if active else theme.TEXT
            prefix = ">>" if active else "  "
            pygame.draw.rect(surface, theme.GREEN_DARK if active else theme.PANEL_ALT, pygame.Rect(box.x + 86, y - 7, 428, 42), 1 if active else 0)
            self.text(surface, f"{prefix} {option}", (box.x + 112, y), "heading", color)
            y += 54
        self.text(surface, "UP/DOWN SELECT   ENTER CONFIRM", (box.x + 143, box.bottom - 58), "tiny", theme.MUTED)
        self.text(surface, f"SUBTITLES {'ON' if settings.subtitles else 'OFF'} // FONT {settings.font_name} {settings.font_size}px", (box.x + 70, box.bottom - 30), "tiny", theme.GREEN_DARK)
        self._crt_overlay(surface, None, intense=True)

    def render_slots(self, surface: pygame.Surface, selection: int, mode: str, occupied: list[int], maximum: int) -> None:
        surface.fill(theme.BG)
        width, height = surface.get_size()
        box = pygame.Rect(width // 2 - 300, 90, 600, 540)
        title = "NEW GAME // SELECT SAVE" if mode == "new" else "CONTINUE // SELECT SAVE"
        self.panel(surface, box, title)
        self.text(surface, "MAXIMUM ACTIVE SAVES: 03", (box.x + 170, box.y + 62), "small", theme.MUTED)
        for index in range(maximum):
            slot = index + 1
            active = index == selection
            exists = slot in occupied
            if mode == "new":
                state = "OCCUPIED // CHOOSE AN EMPTY SLOT" if exists else "EMPTY // CREATE NEW SAVE"
            else:
                state = "ACTIVE SAVE // LOAD" if exists else "EMPTY // UNAVAILABLE"
            color = theme.YELLOW if active else theme.GREEN if exists else theme.MUTED
            y = box.y + 130 + index * 76
            pygame.draw.rect(surface, theme.GREEN_DARK if active else theme.PANEL_ALT, pygame.Rect(box.x + 72, y - 8, 456, 56), 1 if active else 0)
            self.text(surface, f"{'>>' if active else '  '} SAVE SLOT {slot}", (box.x + 96, y), "heading", color)
            self.text(surface, state, (box.x + 250, y + 4), "tiny", color)
        self.text(surface, "UP/DOWN SELECT   ENTER CONFIRM   ESC BACK", (box.x + 128, box.bottom - 36), "tiny", theme.MUTED)
        self._crt_overlay(surface, None, intense=True)

    def render_loader(self, surface: pygame.Surface, progress: float, slot: int | None) -> None:
        surface.fill(theme.BG)
        width, height = surface.get_size()
        box = pygame.Rect(width // 2 - 360, height // 2 - 150, 720, 300)
        self.panel(surface, box, "VIRUS.EXE // SYSTEM LOADER")
        self.text(surface, "MOUNTING SYNTHETIC LAB ENVIRONMENT", (box.x + 118, box.y + 72), "heading", theme.CYAN)
        self.text(surface, f"LOADING SAVE SLOT {slot or 1:02d}", (box.x + 260, box.y + 112), "small", theme.MUTED)
        self.bar(surface, pygame.Rect(box.x + 72, box.y + 160, box.width - 144, 16), progress * 100.0, theme.GREEN)
        self.text(surface, f"{int(progress * 100):03d}%", (box.x + 330, box.y + 194), "small", theme.YELLOW)
        self.text(surface, "RESTORING VIRTUAL FILE SYSTEM // CHECKING SAFE MODULES", (box.x + 136, box.y + 236), "tiny", theme.MUTED)
        self._crt_overlay(surface, None, intense=True)

    def render_story(self, surface: pygame.Surface, story, settings: Settings) -> None:
        surface.fill(theme.BG)
        self.text(surface, "VIRUS.EXE // BOOT SEQUENCE", (28, 24), "title", theme.GREEN)
        self.text(surface, "SIMULATION LAB // STORY MODE", (960, 31), "tiny", theme.MUTED)
        for x in range(40, surface.get_width() - 40, 80):
            pygame.draw.line(surface, "#0b1b0d", (x, 110), (x, 490), 1)
        for y in range(110, 500, 40):
            pygame.draw.line(surface, "#0b1b0d", (40, y), (surface.get_width() - 40, y), 1)
        pygame.draw.rect(surface, theme.GREEN_DARK, pygame.Rect(390, 185, 500, 150), 1)
        self.text(surface, "LAB ENVIRONMENT READY", (505, 235), "heading", theme.CYAN)
        self.text(surface, "ALL NETWORK DATA IS SYNTHETIC", (484, 265), "tiny", theme.MUTED)
        dialogue = story.current
        if dialogue:
            bubble = pygame.Rect(70, 535, surface.get_width() - 140, 150)
            pygame.draw.rect(surface, theme.PANEL, bubble)
            pygame.draw.rect(surface, theme.CYAN, bubble, width=1)
            self.text(surface, f"{dialogue.speaker} //", (bubble.x + 22, bubble.y + 20), "heading", getattr(theme, dialogue.accent, theme.GREEN))
            if settings.subtitles:
                self.text(surface, dialogue.text, (bubble.x + 22, bubble.y + 62), "body", theme.TEXT)
            else:
                self.text(surface, "SUBTITLES DISABLED", (bubble.x + 22, bubble.y + 62), "body", theme.MUTED)
            self.text(surface, "ENTER / SPACE / CLICK TO CONTINUE", (bubble.right - 310, bubble.bottom - 27), "tiny", theme.YELLOW)
        self._crt_overlay(surface, None, intense=True)

    def render_settings(self, surface: pygame.Surface, settings: Settings, selection: int) -> None:
        surface.fill(theme.BG)
        box = pygame.Rect(170, 70, 940, 630)
        self.panel(surface, box, "SYSTEM SETTINGS")
        self.text(surface, "ACCESSIBILITY / DISPLAY / TEXT", (box.x + 26, box.y + 52), "heading", theme.CYAN)
        rows = [
            ("RESOLUTION", settings.resolution),
            ("WINDOW MODE", "FULLSCREEN" if settings.fullscreen else "WINDOWED"),
            ("SUBTITLES", "ON" if settings.subtitles else "OFF"),
            ("FONT", settings.font_name),
            ("FONT SIZE", f"{settings.font_size}px"),
            ("HIGH CONTRAST", "ON" if settings.high_contrast else "OFF"),
            ("REDUCE MOTION", "ON" if settings.reduce_motion else "OFF"),
            ("BACK", "RETURN"),
        ]
        y = box.y + 118
        for index, (label, value) in enumerate(rows):
            active = index == selection
            color = theme.YELLOW if active else theme.TEXT
            pygame.draw.rect(surface, theme.GREEN_DARK if active else theme.PANEL_ALT, pygame.Rect(box.x + 28, y - 7, box.width - 56, 45), 1 if active else 0)
            self.text(surface, f"{'>>' if active else '  '} {label}", (box.x + 50, y), "small", color)
            self.text(surface, value, (box.right - 265, y), "small", theme.CYAN if active else theme.MUTED)
            y += 58
        self.text(surface, "UP/DOWN SELECT   LEFT/RIGHT CHANGE   ENTER TOGGLE   ESC BACK", (box.x + 115, box.bottom - 30), "tiny", theme.MUTED)
        self._crt_overlay(surface, None, intense=True)

    def render_desktop(self, surface: pygame.Surface, state: GameState, active_app: str, taskbar_collapsed: bool, windows: dict, console_input: str, code_editor, virus_editor, settings: Settings, guide_page: int, shop_selection: int, orders_selection: int = 0) -> None:
        surface.fill(theme.BG)
        width, height = surface.get_size()
        sidebar_width = 178
        right_width = 292 if not taskbar_collapsed else 28
        workspace = pygame.Rect(sidebar_width + 12, 72, width - sidebar_width - right_width - 24, height - 118)
        pygame.draw.rect(surface, theme.PANEL, pygame.Rect(0, 0, width, height))
        pygame.draw.rect(surface, theme.PANEL_ALT, pygame.Rect(0, 0, sidebar_width, height - 42))
        self.text(surface, "VIRUS.EXE", (18, 16), "heading", theme.GREEN)
        self.text(surface, "SIM DESKTOP", (18, 38), "tiny", theme.MUTED)
        self.text(surface, "APPLICATIONS", (18, 70), "tiny", theme.MUTED)
        apps = [("CONSOLE", "console", "C"), ("TASKS", "tasks", "T"), ("GUIDE", "guide", "G"), ("EDITOR", "editor", "E"), ("VIRUS LAB", "viruslab", "V"), ("SHOP", "shop", "H"), ("ORDERS", "orders", "R"), ("FILES", "files", "F"), ("SETTINGS", "settings", "O")]
        y = 91
        for label, app_id, hotkey in apps:
            active = app_id == active_app
            open_state = windows.get(app_id)
            color = theme.YELLOW if active else theme.TEXT
            rect = pygame.Rect(10, y, sidebar_width - 20, 34)
            pygame.draw.rect(surface, theme.GREEN_DARK if active else theme.PANEL, rect)
            pygame.draw.rect(surface, theme.CYAN if active else theme.BORDER, rect, 1)
            marker = "*" if open_state and not open_state.minimized else " "
            self.text(surface, f"[{hotkey}] {label:<9}{marker}", (rect.x + 10, rect.y + 10), "tiny", color)
            y += 40
        self.text(surface, "G GUIDE", (18, height - 94), "tiny", theme.MUTED)
        self.text(surface, "TAB CONSOLE", (18, height - 74), "tiny", theme.MUTED)
        self.text(surface, "O SETTINGS", (18, height - 54), "tiny", theme.MUTED)
        top_x = sidebar_width + 12
        right_x = width - right_width - 12
        self.text(surface, f"DESKTOP // HOME-07 // TASK {state.tasks.current_index + 1:02d}/{len(state.tasks.tasks):02d}", (top_x, 16), "heading", theme.TEXT)
        self.text(surface, f"REP {state.tasks.reputation:03d} // LVL {state.tasks.level:02d}", (top_x + 370, 19), "small", theme.YELLOW)
        self.text(surface, datetime.now().strftime("%H:%M:%S"), (width - 92, 19), "tiny", theme.MUTED)
        if state.virus.infection_job:
            job = state.virus.infection_job
            progress_rect = pygame.Rect(top_x, 45, max(120, right_x - top_x - 190), 11)
            self.text(surface, f"PROCESS {job.method_id.upper()} -> {job.node_id.upper()}", (top_x, 32), "tiny", theme.YELLOW)
            self.bar(surface, progress_rect, job.progress, theme.YELLOW)
        else:
            self.text(surface, "PROCESS QUEUE IDLE", (top_x, 35), "tiny", theme.GREEN_DARK)
        self.panel(surface, workspace, f"WORKSPACE // {active_app.upper()}")
        for window in windows.values():
            if window.minimized:
                continue
            rect = self._window_rect(window.app_id, workspace, window.maximized)
            self._render_window(surface, rect, window, state, console_input, code_editor, virus_editor, settings, guide_page, shop_selection, orders_selection)
        if taskbar_collapsed:
            pygame.draw.rect(surface, theme.PANEL_ALT, pygame.Rect(width - 28, 0, 28, height - 42))
            self.text(surface, ">", (width - 21, height // 2), "heading", theme.YELLOW)
        else:
            taskbar = pygame.Rect(width - right_width, 0, right_width, height - 42)
            pygame.draw.rect(surface, theme.PANEL_ALT, taskbar)
            pygame.draw.line(surface, theme.BORDER, (taskbar.x, 0), (taskbar.x, taskbar.bottom), 1)
            self.text(surface, "TASK STEPS", (taskbar.x + 18, 18), "heading", theme.GREEN)
            self.text(surface, "ONE-TIME CAMPAIGN", (taskbar.x + 18, 42), "tiny", theme.MUTED)
            y = 75
            for index, task in enumerate(state.tasks.tasks):
                current = index == state.tasks.current_index
                complete = task.task_id in state.tasks.completed
                color = theme.YELLOW if current else theme.GREEN if complete else theme.MUTED
                marker = ">>" if current else "OK" if complete else "--"
                self.text(surface, f"{marker} {task.title}", (taskbar.x + 16, y), "tiny", color)
                y += 27
                if y > height - 95:
                    break
            if state.tasks.current:
                self.text(surface, "HINT COMMAND: hint", (taskbar.x + 16, height - 67), "tiny", theme.YELLOW)
        self._system_taskbar(surface, width, height, windows)
        self._crt_overlay(surface, state)

    def _window_rect(self, app_id: str, workspace: pygame.Rect, maximized: bool = False) -> pygame.Rect:
        if maximized:
            return pygame.Rect(workspace.x + 4, workspace.y + 38, workspace.width - 8, workspace.height - 42)
        order = {"console": 0, "tasks": 1, "guide": 2, "editor": 3, "viruslab": 4, "shop": 5, "orders": 6, "files": 7, "settings": 8}
        offset = order.get(app_id, 0) * 12
        return pygame.Rect(workspace.x + 32 + offset, workspace.y + 48 + offset, max(420, workspace.width - 92), max(280, workspace.height - 88))

    def _window_chrome(self, surface: pygame.Surface, rect: pygame.Rect, window, title: str) -> pygame.Rect:
        pygame.draw.rect(surface, theme.PANEL, rect)
        pygame.draw.rect(surface, theme.CYAN if window.app_id else theme.BORDER, rect, 1)
        bar = pygame.Rect(rect.x, rect.y, rect.width, 30)
        pygame.draw.rect(surface, theme.PANEL_ALT, bar)
        self.text(surface, f"{title} {'[PIN]' if window.pinned else ''}", (rect.x + 12, rect.y + 9), "tiny", theme.TEXT)
        controls = [("-", theme.YELLOW), ("□", theme.CYAN), ("X", theme.RED), ("P", theme.GREEN)]
        x = rect.right - 92
        for label, color in controls:
            pygame.draw.rect(surface, theme.BORDER, pygame.Rect(x, rect.y + 6, 18, 18), 1)
            self.text(surface, label, (x + 5, rect.y + 8), "tiny", color)
            x += 22
        return pygame.Rect(rect.x + 10, rect.y + 38, rect.width - 20, rect.height - 48)

    def _render_window(self, surface: pygame.Surface, rect: pygame.Rect, window, state: GameState, console_input: str, code_editor, virus_editor, settings: Settings, guide_page: int, shop_selection: int, orders_selection: int) -> None:
        content = self._window_chrome(surface, rect, window, window.app_id.upper())
        if window.app_id == "console":
            y = content.y + 8
            for line in state.console_lines[-16:]:
                self.text(surface, line[:content.width // 8], (content.x + 8, y), "tiny", theme.GREEN if "SUCCESS" in line else theme.TEXT)
                y += 16
            cursor = "_" if pygame.time.get_ticks() % 1000 < 650 else " "
            self.text(surface, f"root@sim:~# {console_input}{cursor}", (content.x + 8, content.bottom - 20), "small", theme.GREEN)
        elif window.app_id == "tasks":
            self.text(surface, "TASK CONTROL", (content.x + 12, content.y + 10), "heading", theme.CYAN)
            task = state.tasks.current
            if task:
                self.text(surface, task.title, (content.x + 12, content.y + 52), "title", theme.YELLOW)
                self.text(surface, task.description, (content.x + 12, content.y + 92), "body", theme.TEXT)
                self.text(surface, "Jedna podpowiedz na zadanie: wpisz HINT w konsoli.", (content.x + 12, content.y + 132), "small", theme.MUTED)
            else:
                self.text(surface, "CAMPAIGN COMPLETE", (content.x + 12, content.y + 80), "title", theme.GREEN)
            self.text(surface, f"REPUTATION {state.tasks.reputation}   LEVEL {state.tasks.level}", (content.x + 12, content.bottom - 28), "small", theme.YELLOW)
        elif window.app_id == "guide":
            self._render_guide_window(surface, content, guide_page)
        elif window.app_id == "editor" and code_editor:
            self._render_code_editor_window(surface, content, code_editor)
        elif window.app_id == "viruslab" and virus_editor:
            self._render_virus_editor_window(surface, content, virus_editor)
        elif window.app_id == "shop":
            self._render_shop(surface, content, state, shop_selection)
        elif window.app_id == "orders":
            self._render_orders(surface, content, state, orders_selection)
        elif window.app_id == "files":
            self.text(surface, f"VIRTUAL FILE SYSTEM // {state.vfs.cwd_path}", (content.x + 12, content.y + 10), "heading", theme.CYAN)
            y = content.y + 46
            for line in state.vfs.tree()[:24]:
                self.text(surface, line, (content.x + 16, y), "small", theme.TEXT)
                y += 18
        elif window.app_id == "settings":
            self.text(surface, f"FULLSCREEN {settings.fullscreen}", (content.x + 12, content.y + 20), "small", theme.TEXT)
            self.text(surface, f"SUBTITLES {settings.subtitles}", (content.x + 12, content.y + 50), "small", theme.TEXT)
            self.text(surface, f"FONT {settings.font_name} {settings.font_size}px", (content.x + 12, content.y + 80), "small", theme.TEXT)
            self.text(surface, "Use O to open the settings screen.", (content.x + 12, content.bottom - 30), "small", theme.MUTED)

    def _render_guide_window(self, surface: pygame.Surface, content: pygame.Rect, page: int) -> None:
        pages = (
            ("START SESJI", (
                "MENU: NEW GAME TWORZY NOWY SAVE, CONTINUE LACZY Z ISTNIEJACYM.",
                "NOWA GRA WYMAGA PUSTEGO SLOTU. SA MAKSYMALNIE 3 SLOTY.",
                "PO WYBORZE SAVE ZAWSZE POKAZUJE SIE SYSTEM LOADER.",
                "PRZY PIERWSZYM WEJSCIU OBEJRZYJ SKROT FABULY I KLIKAJ DALEJ.",
                "PO FABULE TRAFISZ NA PULPIT. GUIDE MOZESZ OTWORZYC KLAWISZEM G.",
                "CONTINUE TAKZE URUCHAMIA LOADER, NAWET GDY SAVE BYL JUZ OTWIERANY.",
            )),
            ("OKNA I TASKBAR", (
                "KAZDA APLIKACJA JEST OSOBNYM OKNEM NA PULPICIE.",
                "MINUS MINIMALIZUJE, KWADRAT ROZSZERZA, X ZAMYKA, P PRZYPINA.",
                "PRZYPINANIE DODAJE APLIKACJE DO DOLNEGO TASKBARA.",
                "TASKBAR POKAZUJE OTWARTE APLIKACJE I SAVE & EXIT.",
                "SAVE & EXIT ZAPISUJE AKTYWNY SLOT I ZAMYKA GRE.",
                "SKROT: C CONSOLE, T TASKS, G GUIDE, E EDITOR, R ORDERS.",
                "V VIRUS LAB, H SHOP, F FILES, O SETTINGS, F10 SAVE & EXIT.",
            )),
            ("CONSOLE I PLIKI", (
                "CONSOLE JEST GLOWNYM INTERFEJSEM DZIALAN W LABORATORIUM.",
                "HELP POKAZUJE KOMENDY, STATUS POKAZUJE STAN SESJI.",
                "SCAN, ANALYZE, DISCOVER, MAP I ADDRESSES CZYTAJA SYMULACJE.",
                "TARGET NODE, ASSIGN NODE, PROBE NODE WYBIERAJA CELE.",
                "DIR, LS, PWD, CD, MKDIR, TOUCH, WRITE, CAT I TREE OBSLUGUJA VFS.",
                "NMAP, NSLOOKUP, DIG I DIGHUNTER SA TYLKO DANYMI SIM.",
                "NIE MA SOCKETOW, DNS, HOSTA ANI PRAWDZIWEJ SIECI.",
            )),
            ("EDYTOR KODU", (
                "EDITOR OBSLUGUJE HTML, CSS, JS, TS ORAZ PYTHON.",
                "F5 WYKONUJE TYLKO ANALIZE STATYCZNA. KOD NIGDY NIE JEST URUCHAMIANY.",
                "BLEDY SKLADNI, NAWIASOW I BRAKUJACYCH TAGOW SA POKAZYWANE W OKNIE.",
                "W SOURCE CODE BLEDNA LINIA MA CZERWONE OZNACZENIE.",
                "TAGI HTML, ATRYBUTY, SELEKTORY I SEMANTYCZNE TAGI SA KOLOROWANE.",
                "SEMANTYCZNE TAGI: HEADER, NAV, MAIN, SECTION, ARTICLE, ASIDE, FOOTER.",
                "F6 TWORZY BEZPIECZNY PODGLAD HTML, CTRL+S ZAPISUJE DO VFS.",
            )),
            ("VIRUS LAB I ZLECENIA", (
                "VIRUS LAB TO DATA-ONLY EDYTOR FIKCYJNEGO VIRUS DSL.",
                "F5 MUSI ZWROCIC TRUE, A F6 DOPIERO WTEDY STOSUJE PROGRAM.",
                "SHOP INSTALUJE DODATKI EDYTORA, SKLADNI, SIECI SIM I VFS.",
                "ORDERS TO OSOBNA APLIKACJA ZLECEN DLA FIKCYJNYCH KLIENTOW.",
                "WYBIERZ ZLECENIE, NACISNIJ ENTER I ZAPLAC REPUTACJA.",
                "W EDITORZE ZROB CHECK WYMAGANEGO JEZYKA, WROC DO ORDERS I ZLOZ.",
                "ZLECENIE JEST JEDNORAZOWE, NAGRODA WRACA JAKO REPUTACJA I XP.",
            )),
            ("TASKI I BEZPIECZENSTWO", (
                "TASKS POKAZUJE AKTUALNY KROK, OPIS, REPUTACJE I POZIOM.",
                "JEST DOKLADNIE 50 ZADAN, ODBLOKOWYWANYCH SEKWENCYJNIE.",
                "KAZDE ZADANIE MA JEDNA PODPOWIEDZ: WPISZ HINT W CONSOLE.",
                "NAGRODY SA JEDNORAZOWE I NIE TWORZA PETLI GRINDU.",
                "SETTINGS ZMIENIA ROZDZIELCZOSC, FULLSCREEN, NAPISY, FONT,",
                "ROZMIAR FONTU, HIGH CONTRAST ORAZ REDUCE MOTION.",
                "WSZYSTKIE WIRUSY, PROFILE, ADRESY I METODY SA FIKCYJNE.",
            )),
        )
        page = page % len(pages)
        title, lines = pages[page]
        self.text(surface, f"GUIDE // {title}", (content.x + 12, content.y + 10), "heading", theme.CYAN)
        self.text(surface, f"PAGE {page + 1}/{len(pages)}", (content.right - 92, content.y + 12), "tiny", theme.YELLOW)
        self._draw_text_lines(surface, list(lines), content.x + 12, content.y + 52, 25, "small")
        self.text(surface, "LEFT/RIGHT PAGE // ESC MINIMIZE // G OPEN GUIDE", (content.x + 12, content.bottom - 20), "tiny", theme.MUTED)

    def _render_code_editor_window(self, surface: pygame.Surface, content: pygame.Rect, editor) -> None:
        self.text(surface, f"LANGUAGE {editor.language.upper()} // F5 CHECK // CTRL+S SAVE", (content.x + 12, content.y + 8), "tiny", theme.YELLOW)
        y = content.y + 34
        for index, line in enumerate(editor.lines[editor.scroll:editor.scroll + 22], start=editor.scroll):
            if index + 1 in editor.error_lines:
                pygame.draw.rect(surface, "#3a1111", pygame.Rect(content.x + 6, y - 2, content.width - 12, 20))
            number_color = theme.RED if index + 1 in editor.error_lines else theme.MUTED
            self.text(surface, f"{index + 1:02d}", (content.x + 12, y), "small", number_color)
            cursor_x = content.x + 42
            for value, kind in editor.highlighted_line(line):
                self.text(surface, value, (cursor_x, y), "small", self._code_color(kind))
                cursor_x += self.fonts["small"].size(value)[0]
            y += 20
        if editor.checks:
            y = content.bottom - 80
            for check in editor.checks[:4]:
                prefix = "TRUE" if check.passed else "FALSE"
                line_info = f" LINE {check.line}" if check.line else ""
                self.text(surface, f"[{prefix}] {check.message}{line_info}", (content.x + 12, y), "tiny", theme.GREEN if check.passed else theme.RED)
                y += 16
        self.text(surface, editor.message, (content.x + 12, content.bottom - 20), "tiny", theme.MUTED)

    def _code_color(self, kind: str) -> str:
        return {
            "keyword": theme.PURPLE,
            "string": theme.YELLOW,
            "number": theme.ORANGE,
            "comment": theme.MUTED,
            "tag": theme.CYAN,
            "semantic": theme.GREEN,
            "punctuation": theme.TEXT,
            "text": theme.TEXT,
        }.get(kind, theme.TEXT)

    def _render_virus_editor_window(self, surface: pygame.Surface, content: pygame.Rect, editor) -> None:
        self.text(surface, "VIRUS DSL // F5 TEST // F6 APPLY TRUE", (content.x + 12, content.y + 8), "tiny", theme.YELLOW)
        y = content.y + 34
        for index, line in enumerate(editor.lines[editor.scroll:editor.scroll + 22], start=editor.scroll):
            color = theme.CYAN if index == editor.row else theme.TEXT
            self.text(surface, f"{index + 1:02d} {line}", (content.x + 12, y), "small", color)
            y += 20
        if editor.result:
            self.text(surface, f"RESULT {'TRUE' if editor.result.passed else 'FALSE'}", (content.x + 12, content.bottom - 46), "small", theme.GREEN if editor.result.passed else theme.RED)
        self.text(surface, editor.message, (content.x + 12, content.bottom - 22), "tiny", theme.MUTED)

    def _render_shop(self, surface: pygame.Surface, content: pygame.Rect, state: GameState, selection: int) -> None:
        items = [("editor-pro", "Edytor wielojezykowy"), ("syntax-pack", "Dodatkowa analiza skladni"), ("sim-network", "Pakiet mapowania SIM"), ("file-tools", "Narzedzia VFS")]
        self.text(surface, "SIMULATION SOFTWARE STORE", (content.x + 12, content.y + 12), "heading", theme.CYAN)
        y = content.y + 54
        for index, (item_id, label) in enumerate(items):
            active = selection == index
            installed = item_id in state.shop_purchases
            color = theme.YELLOW if active else theme.GREEN if installed else theme.TEXT
            self.text(surface, f"{'>>' if active else '  '} {item_id:<16} {label:<28} {'INSTALLED' if installed else 'BUY'}", (content.x + 12, y), "small", color)
            y += 30
        self.text(surface, "UP/DOWN SELECT // ENTER INSTALL", (content.x + 12, content.bottom - 42), "tiny", theme.MUTED)
        self.text(surface, "ORDERS APP: R OPEN CLIENT CONTRACTS", (content.x + 12, content.bottom - 24), "tiny", theme.YELLOW)

    def _render_orders(self, surface: pygame.Surface, content: pygame.Rect, state: GameState, selection: int) -> None:
        self.text(surface, "CLIENT ORDERS // SAFE PROGRAMMING CONTRACTS", (content.x + 12, content.y + 10), "heading", theme.CYAN)
        self.text(surface, f"REPUTATION {state.tasks.reputation} // XP {state.tasks.xp}", (content.right - 190, content.y + 12), "tiny", theme.YELLOW)
        y = content.y + 48
        for index, order in enumerate(CLIENT_ORDERS):
            active = selection == index
            completed = order.order_id in state.completed_orders
            selected = state.active_order == order.order_id
            if completed:
                status = "COMPLETE"
            elif selected:
                status = "ACTIVE // SUBMIT"
            else:
                status = f"COST {order.cost} REP"
            color = theme.GREEN if completed else theme.YELLOW if active or selected else theme.TEXT
            pygame.draw.rect(surface, theme.GREEN_DARK if active else theme.PANEL_ALT, pygame.Rect(content.x + 8, y - 5, content.width - 16, 54), 1 if active else 0)
            self.text(surface, f"{'>>' if active else '  '} {order.title:<22} {order.language.upper():<7} {status}", (content.x + 18, y), "small", color)
            self.text(surface, f"CLIENT {order.client} // {order.description}", (content.x + 42, y + 22), "tiny", theme.MUTED)
            y += 62
        selected_order = CLIENT_ORDERS[selection]
        self.text(surface, f"SELECTED: {selected_order.title} // REWARD {selected_order.reward} REP", (content.x + 12, content.bottom - 44), "tiny", theme.CYAN)
        self.text(surface, "ENTER ACCEPTS WITH REP OR SUBMITS AFTER F5 CODE CHECK", (content.x + 12, content.bottom - 22), "tiny", theme.MUTED)

    def _system_taskbar(self, surface: pygame.Surface, width: int, height: int, windows: dict) -> None:
        bar = pygame.Rect(0, height - 42, width, 42)
        pygame.draw.rect(surface, theme.PANEL_ALT, bar)
        pygame.draw.line(surface, theme.BORDER, (0, bar.y), (width, bar.y), 1)
        self.text(surface, "START", (16, bar.y + 14), "tiny", theme.GREEN)
        x = 90
        for app_id, window in windows.items():
            if not window.pinned:
                continue
            self.text(surface, f"[{app_id.upper()}]", (x, bar.y + 14), "tiny", theme.YELLOW if not window.minimized else theme.MUTED)
            x += 92
        self.text(surface, "[SAVE & EXIT]", (width - 115, bar.y + 14), "tiny", theme.RED)

    def _desktop_tasks(self, surface: pygame.Surface, rect: pygame.Rect, state: GameState) -> None:
        task = state.tasks.current
        self.text(surface, "TASKBAR // SEQUENTIAL OBJECTIVES", (rect.x + 24, rect.y + 50), "heading", theme.CYAN)
        if task:
            self.text(surface, f"ACTIVE TASK: {task.title}", (rect.x + 24, rect.y + 94), "title", theme.YELLOW)
            self.text(surface, task.description, (rect.x + 24, rect.y + 142), "body", theme.TEXT)
            self.text(surface, "HINT COMMAND: hint", (rect.x + 24, rect.y + 190), "small", theme.MUTED)
            self.text(surface, "PODPOWIEDZ JEST OGNISKO-WSKAZOWKA, NIE INSTRUKCJA WYKONANIA.", (rect.x + 24, rect.y + 222), "tiny", theme.MUTED)
        else:
            self.text(surface, "ALL TASKS COMPLETE", (rect.x + 24, rect.y + 100), "title", theme.GREEN)
        y = rect.y + 288
        for index, item in enumerate(state.tasks.tasks):
            complete = item.task_id in state.tasks.completed
            current = item is task
            color = theme.GREEN if complete else theme.YELLOW if current else theme.MUTED
            self.text(surface, f"{index + 1:02d}  {'COMPLETE' if complete else 'ACTIVE' if current else 'LOCKED'}  {item.title}", (rect.x + 24, y), "small", color)
            y += 28

    def _crt_overlay(self, surface: pygame.Surface, state, intense: bool = False) -> None:
        width, height = surface.get_size()
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        line_alpha = 38 if intense else 25
        for y in range(0, height, 4):
            pygame.draw.line(overlay, (0, 30, 4, line_alpha), (0, y), (width, y), 1)
        tick = pygame.time.get_ticks()
        if not self.settings.reduce_motion and (tick % 1700 < 70 or intense and tick % 1100 < 65):
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
