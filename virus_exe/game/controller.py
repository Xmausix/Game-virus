import pygame

from virus_exe.analytics.chart import detection_chart
from virus_exe.config import CUSTOM_DSL_PATH, DATABASE_PATH, FPS, GAME_TITLE, MISSION_PATH, SYSTEM_PATH, WINDOW_SIZE
from virus_exe.core.system import load_system
from virus_exe.game.state import GameState
from virus_exe.missions.loader import load_missions
from virus_exe.storage.database import Database
from virus_exe.ui.editor import DslEditor
from virus_exe.ui.renderer import Renderer
from virus_exe.ui.widgets import Button


class GameController:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer()
        self.database = Database(DATABASE_PATH)
        self.missions = load_missions(MISSION_PATH)
        self.mission_index = 0
        self.mission = self.missions[self.mission_index]
        self.state = self._new_state()
        self.buttons = self._create_buttons()
        self.chart = None
        self.running = True
        self.console_input = ""
        self.console_active = True
        self.editor: DslEditor | None = None
        self._session_saved = False

    @property
    def has_next_level(self) -> bool:
        return self.mission_index + 1 < len(self.missions)

    def _new_state(self) -> GameState:
        return GameState(
            graph=load_system(SYSTEM_PATH),
            mission=self.mission,
            level_index=self.mission_index + 1,
            total_levels=len(self.missions),
        )

    def _create_buttons(self) -> list[Button]:
        labels = [
            ("SCAN", "scan", "S"),
            ("INFECT", "infect", "I"),
            ("HIDE", "hide", "H"),
            ("MOVE", "move", "M"),
            ("ATTACK", "attack", "A"),
        ]
        return [
            Button(pygame.Rect(24 + index * 174, 645, 160, 48), label, action, hotkey)
            for index, (label, action, hotkey) in enumerate(labels)
        ]

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            if self.editor is not None:
                self._editor_events()
                self.renderer.render_editor(self.screen, self.editor)
                pygame.display.flip()
                continue
            self._events()
            self.state.update(dt)
            self._persist_finished_session()
            self._update_buttons()
            self.renderer.render(self.screen, self.state, self.buttons, self.console_input, self.console_active)
            if not self.state.is_playing:
                self.renderer.render_end_screen(self.screen, self.state, self.chart, self.has_next_level)
            pygame.display.flip()
        pygame.quit()

    def _events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.MOUSEMOTION:
                for button in self.buttons:
                    button.update_hover(event.pos)
                continue
            if event.type == pygame.MOUSEBUTTONUP:
                if self._handle_buttons(event):
                    continue
                if self.state.is_playing and event.button == 1:
                    self._select_node_at(event.pos)
                continue
            if event.type == pygame.KEYDOWN:
                self._handle_key(event)

    def _handle_key(self, event: pygame.event.Event) -> None:
        if event.key in {pygame.K_F4, pygame.K_e} and self.state.is_playing and not self.console_active:
            self._open_editor()
            return
        if event.key == pygame.K_TAB:
            self.console_active = not self.console_active
            return
        if not self.state.is_playing:
            if event.key == pygame.K_r:
                self._restart()
            elif event.key == pygame.K_n and self.state.status == "WON" and self.has_next_level:
                self._next_level()
            return
        if self.console_active:
            if event.key == pygame.K_ESCAPE:
                self.console_active = False
            elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                self._execute_console_input()
            elif event.key == pygame.K_BACKSPACE:
                self.console_input = self.console_input[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.console_input) < 96:
                self.console_input += event.unicode
            return
        if event.key == pygame.K_r:
            self._restart()
            return
        actions = {
            pygame.K_s: "scan",
            pygame.K_i: "infect",
            pygame.K_h: "hide",
            pygame.K_m: "move",
            pygame.K_a: "attack",
        }
        action = actions.get(event.key)
        if action:
            self._action(action)

    def _execute_console_input(self) -> None:
        command = self.console_input.strip().lower()
        self.console_input = ""
        if command in {"editor", "edit"}:
            self._open_editor()
            return
        self.state.execute_command(command)

    def _open_editor(self) -> None:
        source = None
        if CUSTOM_DSL_PATH.exists():
            source = CUSTOM_DSL_PATH.read_text(encoding="utf-8")
        self.editor = DslEditor(source)
        self.console_input = ""
        self.console_active = False

    def _editor_events(self) -> None:
        if self.editor is None:
            return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                self.editor = None
                self.console_active = True
            elif event.key == pygame.K_F5:
                self.editor.test()
            elif event.key == pygame.K_F6:
                result = self.editor.result or self.editor.test()
                if result.passed and result.program is not None:
                    self.state.apply_custom_program(result.program)
                    self.editor = None
                    self.console_active = True
                else:
                    self.editor.message = "TEST FALSE // F6 BLOCKED"
            elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                self.editor.save(CUSTOM_DSL_PATH)
            elif event.key == pygame.K_LEFT:
                self.editor.move_left()
            elif event.key == pygame.K_RIGHT:
                self.editor.move_right()
            elif event.key == pygame.K_UP:
                self.editor.move_up()
            elif event.key == pygame.K_DOWN:
                self.editor.move_down()
            elif event.key == pygame.K_RETURN:
                self.editor.newline()
            elif event.key == pygame.K_BACKSPACE:
                self.editor.backspace()
            elif event.key == pygame.K_DELETE:
                self.editor.delete()
            elif event.key == pygame.K_TAB:
                self.editor.insert("    ")
            elif event.unicode and event.unicode.isprintable():
                self.editor.insert(event.unicode)

    def _handle_buttons(self, event: pygame.event.Event) -> bool:
        for button in self.buttons:
            if button.clicked(event):
                self._action(button.action)
                return True
        return False

    def _select_node_at(self, position: tuple[int, int]) -> None:
        origin = (30, 92)
        for node in self.state.graph.nodes.values():
            center = (origin[0] + node.x, origin[1] + node.y)
            rect = pygame.Rect(center[0] - 68, center[1] - 34, 136, 68)
            if rect.collidepoint(position):
                self.state.select_node(node.node_id)
                return

    def _action(self, action: str) -> None:
        if action == "scan":
            self.state.scan()
        elif action == "infect":
            self.state.infect()
        elif action == "hide":
            self.state.hide()
        elif action == "move":
            self.state.move()
        elif action == "attack":
            self.state.attack()

    def _update_buttons(self) -> None:
        for button in self.buttons:
            button.active = self.state.is_playing

    def _persist_finished_session(self) -> None:
        if self.state.is_playing or self._session_saved:
            return
        self.database.save_session(self.mission.mission_id, self.state.result())
        self.chart = detection_chart(self.state.history)
        self._session_saved = True

    def _restart(self) -> None:
        self.state = self._new_state()
        self.chart = None
        self.console_input = ""
        self.console_active = True
        self._session_saved = False

    def _next_level(self) -> None:
        if not self.has_next_level:
            return
        self.mission_index += 1
        self.mission = self.missions[self.mission_index]
        self.state = self._new_state()
        self.chart = None
        self.console_input = ""
        self.console_active = True
        self._session_saved = False
