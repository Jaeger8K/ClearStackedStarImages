import sys
import string
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import re


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

    def _sort_key(self, path):
        """
        Create a sort key for natural sorting (handles numbers correctly).
        Example: "folder10" comes after "folder2"
        """
        name = path.name.lower()
        
        # Split name into text and numbers for natural sorting
        def convert(text):
            return int(text) if text.isdigit() else text.lower()
        
        return [convert(c) for c in re.split(r'(\d+)', name)]

    def _load_roots(self):
        self.tree.delete(*self.tree.get_children())
        roots = list(self._get_roots())
        roots.sort(key=lambda x: self._sort_key(x))
        
        for root in roots:
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
            # Separate folders and files
            folders = []
            files = []
            
            for p in path.iterdir():
                if p.is_dir():
                    folders.append(p)
                else:
                    files.append(p)
            
            # Sort folders with natural sorting
            folders.sort(key=lambda x: self._sort_key(x))
            
            # Sort files with natural sorting
            files.sort(key=lambda x: self._sort_key(x))
            
            # Insert folders first, then files
            for p in folders:
                child = self.tree.insert(node, "end", text=p.name, values=[str(p)])
                self._insert_dummy(child)
            
            for p in files:
                self.tree.insert(node, "end", text=p.name, values=[str(p)])
                
        except PermissionError:
            pass

    def _on_select(self, _):
        node = self.tree.focus()
        if not node:
            return
        path = Path(self.tree.item(node, "values")[0])
        self.on_select(path)