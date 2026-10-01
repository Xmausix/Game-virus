from dataclasses import dataclass, field


@dataclass(slots=True)
class VirtualEntry:
    name: str
    kind: str
    content: str = ""
    children: dict[str, "VirtualEntry"] = field(default_factory=dict)


class VirtualFileSystem:
    def __init__(self) -> None:
        self.root = VirtualEntry("DESKTOP", "dir")
        self.cwd: list[str] = []
        self.mkdir("Documents")
        self.mkdir("Projects")
        self.touch("readme.txt", "SIMULATION DESKTOP")
        self.touch("Projects/briefing.code", "TASK PROJECT FILE")

    @property
    def cwd_path(self) -> str:
        return "/" + "/".join(self.cwd) if self.cwd else "/DESKTOP"

    def _resolve(self, path: str, create: bool = False) -> VirtualEntry | None:
        clean = path.strip().replace("\\", "/")
        if clean.startswith("/"):
            parts = [part for part in clean.split("/") if part]
            current = self.root
        else:
            parts = [part for part in (self.cwd + clean.split("/")) if part and part != "."]
            current = self.root
        for part in parts:
            if part == "..":
                continue
            if part not in current.children:
                if not create:
                    return None
                current.children[part] = VirtualEntry(part, "dir")
            current = current.children[part]
        return current

    def _parent(self, path: str) -> tuple[VirtualEntry | None, str]:
        clean = path.strip().replace("\\", "/").rstrip("/")
        name = clean.split("/")[-1]
        parent_path = "/".join(clean.split("/")[:-1]) or "."
        return self._resolve(parent_path), name

    def exists(self, path: str) -> bool:
        return self._resolve(path) is not None

    def mkdir(self, path: str) -> bool:
        parent, name = self._parent(path)
        if parent is None or parent.kind != "dir" or not name or name in parent.children:
            return False
        parent.children[name] = VirtualEntry(name, "dir")
        return True

    def touch(self, path: str, content: str = "") -> bool:
        parent, name = self._parent(path)
        if parent is None or parent.kind != "dir" or not name:
            return False
        parent.children[name] = VirtualEntry(name, "file", content)
        return True

    def write(self, path: str, content: str) -> bool:
        entry = self._resolve(path)
        if entry is None or entry.kind != "file":
            return False
        entry.content = content
        return True

    def read(self, path: str) -> str | None:
        entry = self._resolve(path)
        return entry.content if entry and entry.kind == "file" else None

    def cd(self, path: str) -> bool:
        entry = self._resolve(path)
        if entry is None or entry.kind != "dir":
            return False
        clean = path.strip().replace("\\", "/")
        if clean.startswith("/"):
            self.cwd = [part for part in clean.split("/") if part]
        elif clean == "..":
            self.cwd = self.cwd[:-1]
        elif clean != ".":
            self.cwd += [part for part in clean.split("/") if part]
        return True

    def list_dir(self) -> list[tuple[str, str]]:
        current = self._resolve(".") or self.root
        return sorted([(entry.name, entry.kind) for entry in current.children.values()])

    def tree(self, entry: VirtualEntry | None = None, prefix: str = "") -> list[str]:
        entry = entry or self.root
        lines = [f"{prefix}{entry.name}/" if entry.kind == "dir" else f"{prefix}{entry.name}"]
        for child in sorted(entry.children.values(), key=lambda item: item.name):
            lines.extend(self.tree(child, prefix + "  "))
        return lines
