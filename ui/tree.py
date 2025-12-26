import sys
import string
import tkinter as tk
from tkinter import ttk
from pathlib import Path


class FolderTree(ttk.Frame):
    def __init__(self, master, on_select):
        super().__init__(master)
        self.on_select = on_select

        self.tree = ttk.Treeview(self, show="tree")
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewOpen>>", self._open_node)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self._load_roots()

    def _load_roots(self):
        self.tree.delete(*self.tree.get_children())
        for root in self._get_roots():
            node = self.tree.insert("", "end", text=str(root), values=[str(root)])
            self._insert_dummy(node)

    def _get_roots(self):
        if sys.platform.startswith("win"):
            for letter in string.ascii_uppercase:
                drive = Path(f"{letter}:/")
                if drive.exists():
                    yield drive
        else:
            yield Path("/")

    def _insert_dummy(self, parent):
        self.tree.insert(parent, "end", text="Loading...")

    def _open_node(self, _):
        node = self.tree.focus()
        path = Path(self.tree.item(node, "values")[0])

        self.tree.delete(*self.tree.get_children(node))

        try:
            for p in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                child = self.tree.insert(node, "end", text=p.name, values=[str(p)])
                if p.is_dir():
                    self._insert_dummy(child)
        except PermissionError:
            pass

    def _on_select(self, _):
        node = self.tree.focus()
        if not node:
            return
        path = Path(self.tree.item(node, "values")[0])
        self.on_select(path)
