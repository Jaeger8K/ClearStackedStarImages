import tkinter as tk
from tkinter import ttk
from pathlib import Path
import rawpy
import numpy as np
from PIL import Image, ImageTk
from PIL import Image, ImageTk


class FilePreview(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        label = ttk.Label(self, text="File Preview", font=("Arial", 12, "bold"))
        label.pack(pady=5)

        self.image_label = ttk.Label(self)
        self.text = tk.Text(self, wrap="word")

        self.original_image = None
        self.current_image = None

        self.bind("<Configure>", lambda _: self._resize_image())

    def clear(self):
        self.image_label.pack_forget()
        self.text.pack_forget()
        self.text.delete("1.0", tk.END)

        if self.original_image:
            self.original_image.close()
        self.original_image = None
        self.current_image = None
        self.image_label.configure(image='')


    def show(self, path: Path):
        self.clear()

        suffix = path.suffix.lower()

        if suffix in [".tif", ".tiff"]:
            # Don't preview TIFF files, show a message instead
            self.text.pack(fill=tk.BOTH, expand=True)
            self.text.insert(tk.END, "Preview for TIFF files is not supported.")
            return
        
        elif suffix == ".dng":
            self._show_dng_image(path)

        elif suffix in [".png", ".jpg", ".jpeg"]:
            self._show_image(path)
        else:
            self._show_text(path)


    def _show_text(self, path):
        self.text.pack(fill=tk.BOTH, expand=True)
        try:
            self.text.insert(tk.END, path.read_text(errors="ignore"))
        except Exception as e:
            self.text.insert(tk.END, str(e))

    def _show_image(self, path):
        try:
            with Image.open(path) as img:
                # For TIFF, explicitly convert to RGB to avoid gibberish
                if path.suffix.lower() in ['.tif', '.tiff']:
                    img = img.convert('RGB')
                
                self.original_image = img.copy()  # Keep a copy to resize later
                self.image_label.pack(expand=True)
                self._resize_image()
                
                # Close the original to free the file handle
                img.close()
                
        except Exception as e:
            self._show_text(path)

    def _show_dng_image(self, path):
        try:
            with rawpy.imread(str(path)) as raw:
                rgb = raw.postprocess()
            img = Image.fromarray(rgb)
            self.original_image = img
            self.image_label.pack(expand=True)
            self._resize_image()
        except Exception as e:
            self._show_text(path)

    def _resize_image(self):
        if not self.original_image:
            return

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        img = self.original_image.copy()
        img.thumbnail((w - 20, h - 60))
        self.current_image = ImageTk.PhotoImage(img)
        self.image_label.configure(image=self.current_image)
