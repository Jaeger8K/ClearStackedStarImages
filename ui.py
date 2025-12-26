import os
import string
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from collections import Counter
from PIL import Image, ImageTk


class FileExplorer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Astro File Explorer")
        self.geometry("1000x600")

        # Paned window (resizable)
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        self.left_frame = ttk.Frame(self, width=300)
        self.right_frame = ttk.Frame(self)

        self.paned.add(self.left_frame, weight=1)
        self.paned.add(self.right_frame, weight=3)

        # Treeview
        self.tree = ttk.Treeview(self.left_frame)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        tree_scroll = ttk.Scrollbar(
            self.left_frame, orient="vertical", command=self.tree.yview
        )
        tree_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        # Preview area
        self.preview_label = ttk.Label(self.right_frame)
        self.preview_label.pack(expand=True)

        self.text_preview = tk.Text(self.right_frame, wrap="word")
        self.text_preview.pack(fill=tk.BOTH, expand=True)
        self.text_preview.pack_forget()

        # Events
        self.tree.bind("<<TreeviewOpen>>", self.open_node)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.bind("<Configure>", lambda e: self.resize_image())

        # Keep reference
        self.current_image = None
        self.current_path = None

        self.load_roots()

    # ---------- ROOTS ----------
    def load_roots(self):
        self.tree.delete(*self.tree.get_children())
        for root in self.get_storage_roots():
            node = self.tree.insert("", "end", text=str(root), values=[root])
            self.insert_dummy(node)

    def get_storage_roots(self):
        roots = []
        if sys.platform.startswith("win"):
            for letter in string.ascii_uppercase:
                drive = Path(f"{letter}:/")
                if drive.exists():
                    roots.append(drive)
        else:
            roots.append(Path("/"))
            for mount in ["/Volumes", "/mnt", "/media"]:
                p = Path(mount)
                if p.exists():
                    roots.extend([x for x in p.iterdir() if x.is_dir()])
        return roots

    # ---------- TREE ----------
    def insert_dummy(self, parent):
        self.tree.insert(parent, "end", text="Loading...")

    def load_children(self, parent, path):
        self.tree.delete(*self.tree.get_children(parent))
        try:
            for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                node = self.tree.insert(parent, "end", text=item.name, values=[item])
                if item.is_dir():
                    self.insert_dummy(node)
        except PermissionError:
            pass

    def open_node(self, event):
        node = self.tree.focus()
        path = Path(self.tree.item(node, "values")[0])
        if path.is_dir():
            self.load_children(node, path)

    # ---------- PREVIEW ----------
    def on_select(self, event):
        self.preview_label.pack_forget()
        self.text_preview.pack_forget()
        node = self.tree.focus()
        path = Path(self.tree.item(node, "values")[0])

        if path.is_dir():
            self.show_astro_folder_summary(path)
        elif path.is_file():
            self.show_file_preview(path)

    def show_image(self, path):
        try:
            img = Image.open(path)
            self.original_image = img
            self.preview_label.pack(expand=True)
            self.resize_image()
        except Exception as e:
            self.text_preview.pack(fill=tk.BOTH, expand=True)
            self.text_preview.insert(tk.END, f"Cannot load image:\n{e}")

    def resize_image(self):
        if not hasattr(self, "original_image"):
            return

        w = self.right_frame.winfo_width()
        h = self.right_frame.winfo_height()
        if w < 10 or h < 10:
            return

        img = self.original_image.copy()
        img.thumbnail((w - 20, h - 20))
        self.current_image = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self.current_image)

    def show_astro_folder_summary(self, folder):
            # Ensure text preview is visible
        self.preview_label.pack_forget()
        self.text_preview.pack(fill=tk.BOTH, expand=True)
        self.text_preview.delete("1.0", tk.END)

        files = list(folder.iterdir())
        self.preview_label.pack_forget()

        image_exts = [".tif", ".tiff", ".fits", ".fit", ".jpg", ".jpeg", ".png", ".raw"]
        images = [f for f in files if f.suffix.lower() in image_exts]

        roles = Counter()
        dss_outputs = []

        # DSS info analysis
        star_counts, zero_star_frames = self.parse_dss_info_files(folder)

        for f in files:
            if f.name.lower().startswith("autosave"):
                dss_outputs.append(f.name)

        if images:
            self.text_preview.insert(tk.END, "📸 Frames detected:\n")
            for k, v in roles.items():
                self.text_preview.insert(tk.END, f"  • {k}: {v}\n")

            sample = images[0]
            try:
                with Image.open(sample) as img:
                    self.text_preview.insert(
                        tk.END,
                        f"\n🖼️Sample frame:\n"
                        f"  • File: {sample.name}\n"
                        f"  • Resolution: {img.width} × {img.height}\n"
                        f"  • Mode: {img.mode}\n"
                        f"  • Format: {img.format}\n"
                    )
            except Exception:
                pass
        else:
            self.text_preview.insert(tk.END, "⚠️ No image frames detected.\n")

        if star_counts:
            avg_stars = sum(star_counts) / len(star_counts)
            self.text_preview.insert(
                tk.END,
                f"\n⭐ Star statistics (from DSS):\n"
                f"  • Frames analyzed: {len(star_counts)}\n"
                f"  • Average stars: {avg_stars:.1f}\n"
                f"  • Min stars: {min(star_counts)}\n"
                f"  • Max stars: {max(star_counts)}\n"
            )

            if zero_star_frames > 0:
                self.text_preview.insert(
                    tk.END,
                    f"\n⚠️ {zero_star_frames} frame(s) had 0 detected stars "
                    f"and were classified as Darks\n"
                )

        if dss_outputs:
            self.text_preview.insert(tk.END, "\n🧪 DSS Outputs:\n")
            for f in dss_outputs:
                self.text_preview.insert(tk.END, f"  • {f}\n")

        if star_counts and 0 in star_counts:
            self.text_preview.insert(
                tk.END,
                "\n✅ Ready for stacking\n" if roles["Lights"] > 0 else "\n⚠️ No light frames found\n"
            )

    def parse_dss_info_files(self, folder):
        """
        Parse DSS .info.txt files in the folder.

        Returns:
            star_counts: list of number of stars per frame
            zero_star_frames: count of frames with 0 stars
        """
        star_counts = []
        zero_star_frames = 0

        for info_file in folder.glob("*.info.txt"):
            try:
                with open(info_file, "r", encoding="utf-8", errors="ignore") as f:
                    nr_stars = None
                    for line in f:
                        line = line.strip()
                        if line.startswith("NrStars"):
                            # Line format: NrStars = 68
                            try:
                                nr_stars = int(line.split("=")[1].strip())
                                star_counts.append(nr_stars)
                                if nr_stars == 0:
                                    zero_star_frames += 1
                            except Exception:
                                pass
                            break  # Stop after NrStars is found
            except Exception:
                pass

        return star_counts, zero_star_frames



    def show_file_preview(self, path):
        self.preview_label.pack_forget()
        self.text_preview.pack_forget()
        self.text_preview.delete("1.0", tk.END)

        suffix = path.suffix.lower()

        # Image preview
        if suffix in [".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"]:
            try:
                self.show_image(path)
            except Exception as e:
                self.text_preview.pack(fill=tk.BOTH, expand=True)
                self.text_preview.insert(tk.END, f"Cannot load image:\n{e}")

        # Text preview
        elif suffix in [".txt", ".py", ".md", ".json", ".log"]:
            self.text_preview.pack(fill=tk.BOTH, expand=True)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    self.text_preview.insert(tk.END, f.read())
            except Exception as e:
                self.text_preview.insert(tk.END, f"Error:\n{e}")


if __name__ == "__main__":
    FileExplorer().mainloop()
