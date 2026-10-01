import json
from pathlib import Path

import pygame

from virus_exe.analytics.chart import detection_chart
from virus_exe.config import CUSTOM_DSL_PATH, DATABASE_PATH, FPS, GAME_TITLE, MAX_SAVE_SLOTS, MISSION_PATH, SAVE_DIR, SAVE_PATH, SETTINGS_PATH, SYSTEM_PATH, WINDOW_SIZE
from virus_exe.core.system import load_system
from virus_exe.core.vfs import VirtualEntry
from virus_exe.game.state import CLIENT_ORDERS, GameState
from virus_exe.game.story import StoryState
from virus_exe.missions.loader import load_missions
from virus_exe.storage.database import Database
from virus_exe.ui.code_editor import CodeEditor
from virus_exe.ui.editor import DslEditor
from virus_exe.ui.renderer import Renderer
from virus_exe.ui.settings import Settings
from virus_exe.ui.windowing import WindowState


class GameController:
    def __init__(self) -> None:
        pygame.init()
        self.settings = Settings.load(SETTINGS_PATH)
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self._apply_display()
        pygame.display.set_caption(GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.settings)
        self.database = Database(DATABASE_PATH)
        self.mission = load_missions(MISSION_PATH)[0]
        self.state = self._new_state()
        self.chart = None
        self.running = True
        self.view = "menu"
        self.return_view = "menu"
        self.menu_selection = 0
        self.settings_selection = 0
        self.slot_selection = 0
        self.slot_mode = "continue"
        self.pending_slot: int | None = None
        self.active_slot: int | None = None
        self.story_seen = False
        self.loader_progress = 0.0
        self.loader_time = 0.0
        self.story = StoryState()
        self.windows: dict[str, WindowState] = {}
        self.active_app = "tasks"
        self.taskbar_collapsed = False
        self.console_input = ""
        self.code_editor: CodeEditor | None = None
        self.virus_editor: DslEditor | None = None
        self.guide_page = 0
        self.shop_selection = 0
        self.orders_selection = 0
        self._session_saved = False

    @property
    def has_save(self) -> bool:
        return bool(self._list_save_slots())

    def _slot_path(self, slot: int) -> Path:
        return SAVE_DIR / f"save_{slot}.json"

    def _list_save_slots(self) -> list[int]:
        slots = [slot for slot in range(1, MAX_SAVE_SLOTS + 1) if self._slot_path(slot).exists()]
        if SAVE_PATH.exists() and 1 not in slots:
            slots.insert(0, 1)
        return sorted(set(slots))

    def _slot_exists(self, slot: int) -> bool:
        return slot in self._list_save_slots()

    def _apply_display(self) -> None:
        try:
            size = self.settings.resolution_size()
        except (ValueError, TypeError):
            size = WINDOW_SIZE
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.settings.fullscreen else pygame.RESIZABLE)
        self.screen = pygame.display.set_mode(size, flags)

    def _new_state(self) -> GameState:
        return GameState(graph=load_system(SYSTEM_PATH), mission=self.mission, level_index=1, total_levels=1)

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            if self.view == "menu":
                self._menu_events()
                self.renderer.render_menu(self.screen, self.menu_selection, self.settings, self.has_save)
            elif self.view == "slots":
                self._slot_events()
                self.renderer.render_slots(self.screen, self.slot_selection, self.slot_mode, self._list_save_slots(), MAX_SAVE_SLOTS)
            elif self.view == "loader":
                self._loader_events(dt)
                self.renderer.render_loader(self.screen, self.loader_progress, self.pending_slot)
            elif self.view == "story":
                self._story_events()
                self.renderer.render_story(self.screen, self.story, self.settings)
            elif self.view == "settings":
                self._settings_events()
                self.renderer.render_settings(self.screen, self.settings, self.settings_selection)
            else:
                self._desktop_events()
                self.state.update(dt)
                self._persist_finished_session()
                self.renderer.render_desktop(self.screen, self.state, self.active_app, self.taskbar_collapsed, self.windows, self.console_input, self.code_editor, self.virus_editor, self.settings, self.guide_page, self.shop_selection, self.orders_selection)
            pygame.display.flip()
        pygame.quit()

    def _menu_events(self) -> None:
        option_count = 4 if self.has_save else 3
        self.menu_selection = min(self.menu_selection, option_count - 1)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.menu_selection = (self.menu_selection - 1) % option_count
                elif event.key == pygame.K_DOWN:
                    self.menu_selection = (self.menu_selection + 1) % option_count
                elif event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                    self._menu_activate()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                box_x = self.screen.get_width() // 2 - 300
                for index in range(option_count):
                    if pygame.Rect(box_x + 86, 260 + index * 54, 428, 42).collidepoint(event.pos):
                        self.menu_selection = index
                        self._menu_activate()
                        break

    def _menu_activate(self) -> None:
        if self.has_save:
            actions = [self._start_new_game, self._continue_game, self._open_settings_from_menu, self._quit]
        else:
            actions = [self._start_new_game, self._open_settings_from_menu, self._quit]
        actions[self.menu_selection]()

    def _quit(self) -> None:
        self.running = False

    def _open_settings_from_menu(self) -> None:
        self.return_view = "menu"
        self.settings_selection = 0
        self.view = "settings"

    def _start_new_game(self) -> None:
        self.slot_mode = "new"
        self.slot_selection = 0
        self.view = "slots"

    def _continue_game(self) -> None:
        self.slot_mode = "continue"
        available = self._list_save_slots()
        self.slot_selection = available[0] - 1 if available else 0
        self.view = "slots"

    def _slot_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.view = "menu"
                elif event.key == pygame.K_UP:
                    self.slot_selection = (self.slot_selection - 1) % MAX_SAVE_SLOTS
                elif event.key == pygame.K_DOWN:
                    self.slot_selection = (self.slot_selection + 1) % MAX_SAVE_SLOTS
                elif event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                    self._activate_slot(self.slot_selection + 1)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                box_x = self.screen.get_width() // 2 - 300
                for index in range(MAX_SAVE_SLOTS):
                    if pygame.Rect(box_x + 86, 260 + index * 62, 428, 46).collidepoint(event.pos):
                        self.slot_selection = index
                        self._activate_slot(index + 1)
                        break

    def _activate_slot(self, slot: int) -> None:
        if self.slot_mode == "new":
            if self._slot_exists(slot):
                return
            self._create_new_save(slot)
        elif self._slot_exists(slot):
            self._begin_loader(slot)

    def _create_new_save(self, slot: int) -> None:
        self.state = self._new_state()
        self.story = StoryState()
        self.chart = None
        self.windows.clear()
        self.active_app = "tasks"
        self.active_slot = slot
        self.story_seen = False
        self._session_saved = False
        self._write_save()
        self._begin_loader(slot)

    def _begin_loader(self, slot: int) -> None:
        self.pending_slot = slot
        self.loader_progress = 0.0
        self.loader_time = 0.0
        self.view = "loader"

    def _loader_events(self, dt: float) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
        self.loader_time += max(0.0, dt)
        self.loader_progress = min(1.0, self.loader_time / 1.8)
        if self.loader_progress >= 1.0 and self.pending_slot is not None:
            slot = self.pending_slot
            self.pending_slot = None
            self._load_game(slot)
            if self.story_seen:
                self._enter_desktop()
            else:
                self.story = StoryState()
                self.view = "story"

    def _enter_desktop(self) -> None:
        self.view = "desktop"
        self._open_app("tasks", pinned=True)
        self._open_app("console", pinned=True)
        self.active_app = "tasks"

    def _story_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key in {pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT}:
                self.story.advance()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.story.advance()
        if self.story.finished:
            if not self.story_seen:
                self.story_seen = True
                self._write_save()
            self._enter_desktop()

    def _settings_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.settings.save(SETTINGS_PATH)
                    self.view = self.return_view
                elif event.key == pygame.K_UP:
                    self.settings_selection = (self.settings_selection - 1) % 8
                elif event.key == pygame.K_DOWN:
                    self.settings_selection = (self.settings_selection + 1) % 8
                elif event.key in {pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN, pygame.K_SPACE}:
                    self._change_setting(1 if event.key in {pygame.K_RIGHT, pygame.K_RETURN, pygame.K_SPACE} else -1)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                for index in range(8):
                    if pygame.Rect(198, 181 + index * 58, 884, 45).collidepoint(event.pos):
                        self.settings_selection = index
                        self._change_setting(1)
                        break

    def _change_setting(self, direction: int) -> None:
        if self.settings_selection == 0:
            self.settings.cycle_resolution(direction)
            self._apply_display()
        elif self.settings_selection == 1:
            self.settings.fullscreen = not self.settings.fullscreen
            self._apply_display()
        elif self.settings_selection == 2:
            self.settings.subtitles = not self.settings.subtitles
        elif self.settings_selection == 3:
            self.settings.cycle_font()
        elif self.settings_selection == 4:
            self.settings.change_size(direction)
        elif self.settings_selection == 5:
            self.settings.high_contrast = not self.settings.high_contrast
        elif self.settings_selection == 6:
            self.settings.reduce_motion = not self.settings.reduce_motion
        elif self.settings_selection == 7:
            self.settings.save(SETTINGS_PATH)
            self.view = self.return_view
        self.settings.save(SETTINGS_PATH)
        self.renderer = Renderer(self.settings)

    def _desktop_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._save_and_exit()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._desktop_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                self._desktop_key(event)

    def _desktop_key(self, event: pygame.event.Event) -> None:
        if self.active_app == "console" and self._active_window_open():
            if event.key in {pygame.K_ESCAPE, pygame.K_TAB}:
                self._minimize_active()
            elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                self._execute_console_input()
            elif event.key == pygame.K_BACKSPACE:
                self.console_input = self.console_input[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.console_input) < 120:
                self.console_input += event.unicode
            return
        if self.active_app == "guide" and self._active_window_open():
            if event.key == pygame.K_ESCAPE:
                self._minimize_active()
            elif event.key == pygame.K_LEFT:
                self.guide_page = (self.guide_page - 1) % 6
            elif event.key == pygame.K_RIGHT:
                self.guide_page = (self.guide_page + 1) % 6
            return
        if self.active_app == "editor" and self._active_window_open():
            self._code_editor_key(event)
            return
        if self.active_app == "viruslab" and self._active_window_open():
            self._virus_editor_key(event)
            return
        if self.active_app == "shop" and self._active_window_open():
            if event.key == pygame.K_UP:
                self.shop_selection = (self.shop_selection - 1) % 4
            elif event.key == pygame.K_DOWN:
                self.shop_selection = (self.shop_selection + 1) % 4
            elif event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                self._buy_selected()
            return
        if self.active_app == "orders" and self._active_window_open():
            if event.key == pygame.K_ESCAPE:
                self._minimize_active()
            elif event.key == pygame.K_UP:
                self.orders_selection = (self.orders_selection - 1) % len(CLIENT_ORDERS)
            elif event.key == pygame.K_DOWN:
                self.orders_selection = (self.orders_selection + 1) % len(CLIENT_ORDERS)
            elif event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                self._order_action()
            return
        if event.key in {pygame.K_TAB, pygame.K_c}:
            self._open_app("console", pinned=True)
        elif event.key in {pygame.K_e, pygame.K_F2}:
            self._open_app("editor", pinned=False)
        elif event.key in {pygame.K_v}:
            self._open_app("viruslab", pinned=False)
        elif event.key in {pygame.K_g, pygame.K_F1}:
            self._open_app("guide", pinned=True)
        elif event.key == pygame.K_t:
            self._open_app("tasks", pinned=True)
        elif event.key == pygame.K_h:
            self._open_app("shop", pinned=False)
        elif event.key == pygame.K_r:
            self._open_app("orders", pinned=True)
        elif event.key == pygame.K_f:
            self._open_app("files", pinned=False)
        elif event.key == pygame.K_o:
            self.return_view = "desktop"
            self.view = "settings"
        elif event.key == pygame.K_F10:
            self._save_and_exit()

    def _desktop_click(self, position: tuple[int, int]) -> None:
        width, height = self.screen.get_size()
        sidebar_width = 178
        right_width = 292 if not self.taskbar_collapsed else 28
        workspace = pygame.Rect(sidebar_width + 12, 72, width - sidebar_width - right_width - 24, height - 118)
        if position[1] >= height - 42 and position[0] >= width - 125:
            self._save_and_exit()
            return
        if self.taskbar_collapsed:
            if position[0] >= width - 28:
                self.taskbar_collapsed = False
            return
        if position[0] >= width - right_width and position[1] < 60:
            self.taskbar_collapsed = True
            return
        if position[0] < sidebar_width:
            y = 91
            actions = ["console", "tasks", "guide", "editor", "viruslab", "shop", "orders", "files", "settings"]
            for app_id in actions:
                if pygame.Rect(10, y, sidebar_width - 20, 34).collidepoint(position):
                    if app_id == "settings":
                        self.return_view = "desktop"
                        self.view = "settings"
                    else:
                        self._open_app(app_id, pinned=app_id in {"console", "tasks", "guide"})
                    return
                y += 40
        for app_id, window in list(self.windows.items()):
            if window.minimized:
                continue
            rect = self.renderer._window_rect(app_id, workspace, window.maximized)
            if not rect.collidepoint(position):
                continue
            if position[1] < rect.y + 30:
                button_start = rect.right - 92
                if pygame.Rect(button_start, rect.y + 6, 18, 18).collidepoint(position):
                    window.minimized = True
                    return
                if pygame.Rect(button_start + 22, rect.y + 6, 18, 18).collidepoint(position):
                    window.maximized = not window.maximized
                    return
                if pygame.Rect(button_start + 44, rect.y + 6, 18, 18).collidepoint(position):
                    self._close_app(app_id)
                    return
                if pygame.Rect(button_start + 66, rect.y + 6, 18, 18).collidepoint(position):
                    window.pinned = not window.pinned
                    return
            self.active_app = app_id
            if app_id == "shop":
                self._buy_selected()
            return

    def _open_app(self, app_id: str, pinned: bool = False) -> None:
        if app_id == "settings":
            self.return_view = "desktop"
            self.view = "settings"
            return
        if app_id not in self.windows:
            self.windows[app_id] = WindowState(app_id, pinned=pinned)
        else:
            self.windows[app_id].minimized = False
            if pinned:
                self.windows[app_id].pinned = True
        self.active_app = app_id
        if app_id == "editor" and self.code_editor is None:
            self.code_editor = CodeEditor("<html>\n  <body>\n    <h1>SIM LAB</h1>\n  </body>\n</html>\n", "html")
        if app_id == "viruslab" and self.virus_editor is None:
            source = CUSTOM_DSL_PATH.read_text(encoding="utf-8") if CUSTOM_DSL_PATH.exists() else None
            self.virus_editor = DslEditor(source)

    def _close_app(self, app_id: str) -> None:
        self.windows.pop(app_id, None)
        if self.active_app == app_id:
            self.active_app = "tasks"
            self._open_app("tasks", pinned=True)

    def _minimize_active(self) -> None:
        if self.active_app in self.windows:
            self.windows[self.active_app].minimized = True
            self.active_app = "tasks"

    def _active_window_open(self) -> bool:
        return self.active_app in self.windows and not self.windows[self.active_app].minimized

    def _execute_console_input(self) -> None:
        command = self.console_input.strip().lower()
        self.console_input = ""
        if command in {"editor", "edit"}:
            self._open_app("editor")
        elif command in {"viruslab", "virus-editor"}:
            self._open_app("viruslab")
        elif command in {"shop", "store"}:
            self._open_app("shop")
        elif command in {"orders", "jobs", "contracts"}:
            self._open_app("orders", pinned=True)
        elif command in {"files", "explorer"}:
            self._open_app("files")
        elif command in {"guide", "help-ui"}:
            self._open_app("guide", pinned=True)
        else:
            self.state.execute_command(command)

    def _code_editor_key(self, event: pygame.event.Event) -> None:
        if not self.code_editor:
            return
        if event.key == pygame.K_ESCAPE:
            self._minimize_active()
        elif event.key == pygame.K_F1:
            self._open_app("guide", pinned=True)
        elif event.key == pygame.K_F5:
            checks = self.code_editor.check()
            if all(check.passed for check in checks):
                self.state.code_checks.add(self.code_editor.language)
                self.state.emit_event(f"code:{self.code_editor.language}")
        elif event.key == pygame.K_F6 and self.code_editor.language == "html" and self.code_editor.check() and all(check.passed for check in self.code_editor.checks):
            self.code_editor.preview = self.code_editor.source
            self.state.emit_event("preview")
            self.code_editor.message = "VIRTUAL LIVE PREVIEW READY"
        elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
            self.state.vfs.touch(f"{self.code_editor.language}.code", self.code_editor.source)
            self.state.emit_event("project:saved")
            self.code_editor.message = "SAVED TO VIRTUAL FILE SYSTEM"
        elif event.key == pygame.K_TAB and event.mod & pygame.KMOD_CTRL:
            self.code_editor.cycle_language()
        elif event.key == pygame.K_LEFT:
            self.code_editor.move_left()
        elif event.key == pygame.K_RIGHT:
            self.code_editor.move_right()
        elif event.key == pygame.K_UP:
            self.code_editor.move_up()
        elif event.key == pygame.K_DOWN:
            self.code_editor.move_down()
        elif event.key == pygame.K_RETURN:
            self.code_editor.newline()
        elif event.key == pygame.K_BACKSPACE:
            self.code_editor.backspace()
        elif event.key == pygame.K_DELETE:
            self.code_editor.delete()
        elif event.unicode and event.unicode.isprintable():
            self.code_editor.insert(event.unicode)

    def _virus_editor_key(self, event: pygame.event.Event) -> None:
        if not self.virus_editor:
            return
        if event.key == pygame.K_ESCAPE:
            self._minimize_active()
        elif event.key == pygame.K_F1:
            self._open_app("guide", pinned=True)
        elif event.key == pygame.K_F5:
            self.virus_editor.test()
        elif event.key == pygame.K_F6:
            result = self.virus_editor.result or self.virus_editor.test()
            if result.passed and result.program:
                self.state.apply_custom_program(result.program)
                self.virus_editor.message = "CUSTOM VIRUS APPLIED TO SIMULATION"
            else:
                self.virus_editor.message = "TEST FALSE // APPLY BLOCKED"
        elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
            self.virus_editor.save(CUSTOM_DSL_PATH)
        elif event.key == pygame.K_LEFT:
            self.virus_editor.move_left()
        elif event.key == pygame.K_RIGHT:
            self.virus_editor.move_right()
        elif event.key == pygame.K_UP:
            self.virus_editor.move_up()
        elif event.key == pygame.K_DOWN:
            self.virus_editor.move_down()
        elif event.key == pygame.K_RETURN:
            self.virus_editor.newline()
        elif event.key == pygame.K_BACKSPACE:
            self.virus_editor.backspace()
        elif event.key == pygame.K_DELETE:
            self.virus_editor.delete()
        elif event.key == pygame.K_TAB:
            self.virus_editor.insert("    ")
        elif event.unicode and event.unicode.isprintable():
            self.virus_editor.insert(event.unicode)

    def _buy_selected(self) -> None:
        packages = ["editor-pro", "syntax-pack", "sim-network", "file-tools"]
        if self.state.install_package(packages[self.shop_selection]):
            self.state.console_write(f"PACKAGE INSTALLED: {packages[self.shop_selection]}")

    def _order_action(self) -> None:
        order = CLIENT_ORDERS[self.orders_selection]
        if order.order_id in self.state.completed_orders:
            return
        if self.state.active_order == order.order_id:
            self.state.submit_order(order.order_id)
        elif not self.state.active_order:
            self.state.accept_order(order.order_id)

    def _persist_finished_session(self) -> None:
        if self.state.is_playing or self._session_saved:
            return
        self.database.save_session(self.mission.mission_id, self.state.result())
        self.chart = detection_chart(self.state.history)
        self._session_saved = True

    def _serialize_vfs_entry(self, entry: VirtualEntry) -> dict:
        return {
            "name": entry.name,
            "kind": entry.kind,
            "content": entry.content,
            "children": {name: self._serialize_vfs_entry(child) for name, child in entry.children.items()},
        }

    def _restore_vfs_entry(self, payload: dict) -> VirtualEntry:
        children = payload.get("children", {}) if isinstance(payload, dict) else {}
        entry = VirtualEntry(
            str(payload.get("name", "DESKTOP")),
            str(payload.get("kind", "dir")),
            str(payload.get("content", "")),
        )
        if isinstance(children, dict):
            entry.children = {str(name): self._restore_vfs_entry(child) for name, child in children.items() if isinstance(child, dict)}
        return entry

    def _build_save_payload(self) -> dict:
        return {
            "slot": self.active_slot,
            "story_seen": self.story_seen,
            "current_index": self.state.tasks.current_index,
            "completed": sorted(self.state.tasks.completed),
            "hint_used": sorted(self.state.tasks.hint_used),
            "reputation": self.state.tasks.reputation,
            "xp": self.state.tasks.xp,
            "level": self.state.tasks.level,
            "events": sorted(self.state.event_flags),
            "code_checks": sorted(self.state.code_checks),
            "shop_purchases": sorted(self.state.shop_purchases),
            "active_order": self.state.active_order,
            "completed_orders": sorted(self.state.completed_orders),
            "vfs": {
                "root": self._serialize_vfs_entry(self.state.vfs.root),
                "cwd": list(self.state.vfs.cwd),
            },
        }

    def _write_save(self) -> None:
        if self.active_slot is None:
            return
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        self._slot_path(self.active_slot).write_text(json.dumps(self._build_save_payload(), indent=2), encoding="utf-8")

    def _save_and_exit(self) -> None:
        self._write_save()
        self.settings.save(SETTINGS_PATH)
        self.running = False

    def _load_game(self, slot: int | None = None) -> None:
        slot = slot or self.active_slot or 1
        self.state = self._new_state()
        self.active_slot = slot
        path = self._slot_path(slot) if self._slot_path(slot).exists() else SAVE_PATH
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.story_seen = bool(payload.get("story_seen", True))
            self.state.tasks.current_index = int(payload.get("current_index", 0))
            self.state.tasks.completed = set(payload.get("completed", []))
            self.state.tasks.hint_used = set(payload.get("hint_used", []))
            self.state.tasks.reputation = int(payload.get("reputation", 0))
            self.state.tasks.xp = int(payload.get("xp", 0))
            self.state.tasks.level = int(payload.get("level", 1))
            self.state.event_flags = set(payload.get("events", []))
            self.state.code_checks = set(payload.get("code_checks", []))
            self.state.shop_purchases = set(payload.get("shop_purchases", []))
            self.state.active_order = str(payload.get("active_order", ""))
            self.state.completed_orders = set(payload.get("completed_orders", []))
            vfs_payload = payload.get("vfs", {})
            if isinstance(vfs_payload, dict) and isinstance(vfs_payload.get("root"), dict):
                self.state.vfs.root = self._restore_vfs_entry(vfs_payload["root"])
                cwd = vfs_payload.get("cwd", [])
                self.state.vfs.cwd = [str(item) for item in cwd] if isinstance(cwd, list) else []
        except (OSError, ValueError, TypeError):
            self.state = self._new_state()
            self.story_seen = False
        self._session_saved = False
