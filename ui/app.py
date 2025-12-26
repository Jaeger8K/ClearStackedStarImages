import tkinter as tk
from tkinter import ttk
from pathlib import Path

from ui.tree import FolderTree
from ui.folder_summary import FolderSummary
from ui.file_preview import FilePreview
from ui.dialogs import run_astrostakos


class FileExplorer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Astro File Explorer")
        self.geometry("1400x700")

        self._build_toolbar()
        self._build_layout()

    def _build_toolbar(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        run_btn = ttk.Button(
            toolbar,
            text="Run AstroStakos",
            command=run_astrostakos
        )
        run_btn.pack(side=tk.LEFT, padx=5)

    def _build_layout(self):
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        self.tree = FolderTree(self, on_select=self.on_path_selected)
        self.folder_summary = FolderSummary(self)
        self.file_preview = FilePreview(self)

        paned.add(self.tree, weight=1)
        paned.add(self.folder_summary, weight=2)
        paned.add(self.file_preview, weight=2)

    def on_path_selected(self, path: Path):
        if path.is_dir():
            self.folder_summary.show(path)
            self.file_preview.clear()
        elif path.is_file():
            self.file_preview.show(path)
