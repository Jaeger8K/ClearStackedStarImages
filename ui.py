import os
import string
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ExifTags
from PIL import Image, ImageTk


class FileExplorer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Astro File Explorer")
        self.geometry("1400x700")

        # Three-panel layout
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left panel: Folder tree
        self.left_frame = ttk.Frame(self, width=300)
        # Middle panel: Folder preview
        self.middle_frame = ttk.Frame(self, width=400)
        # Right panel: File preview
        self.right_frame = ttk.Frame(self, width=400)

        self.paned.add(self.left_frame, weight=1)
        self.paned.add(self.middle_frame, weight=2)
        self.paned.add(self.right_frame, weight=2)

        # --- LEFT: Treeview ---
        self.tree = ttk.Treeview(self.left_frame)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        tree_scroll = ttk.Scrollbar(
            self.left_frame, orient="vertical", command=self.tree.yview
        )
        tree_scroll.pack(fill=tk.Y, side=tk.RIGHT)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        # --- MIDDLE: Folder preview ---
        middle_label = ttk.Label(self.middle_frame, text="Folder Summary", font=("Arial", 12, "bold"))
        middle_label.pack(pady=5)
        
        self.folder_preview = tk.Text(self.middle_frame, wrap="word")
        self.folder_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- RIGHT: File preview ---
        right_label = ttk.Label(self.right_frame, text="File Preview", font=("Arial", 12, "bold"))
        right_label.pack(pady=5)
        
        self.file_preview_label = ttk.Label(self.right_frame)
        self.file_preview_label.pack(expand=True)

        self.file_text_preview = tk.Text(self.right_frame, wrap="word")
        self.file_text_preview.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_text_preview.pack_forget()

        # Events
        self.tree.bind("<<TreeviewOpen>>", self.open_node)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.bind("<Configure>", lambda e: self.resize_image())

        # Keep reference
        self.current_image = None
        self.current_path = None

        self.load_roots()

    # ---------- HELPERS----------

    def get_image_properties(self, img_path):
        """
        Extract basic image properties from the original image.
        Returns a dict with keys like Exposure, ISO, Device.
        """
        props = {}
        try:
            with Image.open(img_path) as img:
                # Resolution and format
                props["Width"], props["Height"] = img.size
                props["Format"] = img.format

                # EXIF (if available)
                exif = img._getexif()
                if exif:
                    exif_data = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
                    # Exposure time
                    if "ExposureTime" in exif_data:
                        props["Exposure"] = float(exif_data["ExposureTime"][0]) / float(exif_data["ExposureTime"][1]) \
                                            if isinstance(exif_data["ExposureTime"], tuple) else float(exif_data["ExposureTime"])
                    # ISO
                    if "ISOSpeedRatings" in exif_data:
                        props["ISO"] = exif_data["ISOSpeedRatings"]
                    # Camera / Device
                    if "Model" in exif_data:
                        props["Device"] = exif_data["Model"]
                    elif "Camera" in exif_data:
                        props["Device"] = exif_data["Camera"]
        except Exception:
            pass

        return props

    # ---------- ROOTS ----------
    def load_roots(self):
        self.tree.delete(*self.tree.get_children())
        # Configure tree to hide the header row
        self.tree["show"] = "tree"
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

    # ---------- SELECTION HANDLING ----------
    def on_select(self, event):
        node = self.tree.focus()
        path = Path(self.tree.item(node, "values")[0])

        if path.is_dir():
            # Show folder summary in middle panel
            self.show_astro_folder_summary(path)
            # Clear file preview
            self.clear_file_preview()
        elif path.is_file():
            # Keep current folder summary in middle panel (don't clear)
            # Show file preview in right panel
            self.show_file_preview(path)

    # ---------- MIDDLE PANEL: FOLDER PREVIEW ----------
    def show_astro_folder_summary(self, folder):
        self.folder_preview.delete("1.0", tk.END)

        files = list(folder.iterdir())

        # DSS stacked outputs
        dss_outputs = [f.name for f in files if f.suffix.lower() in [".tif", ".tiff"]
                    and ("autosave" in f.name.lower() or "stack" in f.name.lower())]
        no_stacked = len(dss_outputs) == 0

        # DSS processed images: only images with a corresponding .info.txt
        frame_props, zero_star_frames, _ = self.parse_dss_processed_images(folder)

        # Frame counts: number of DSS-processed frames
        if frame_props:
            self.folder_preview.insert(tk.END, "📸 Frames detected:\n")
            self.folder_preview.insert(tk.END, f"  • Total DSS-processed frames: {len(frame_props)}\n")
        else:
            self.folder_preview.insert(tk.END, "⚠️ No DSS-processed frames detected.\n")

        # Star statistics
        if frame_props:
            stars_list = [f.get("Stars", 0) for f in frame_props]
            if stars_list:
                avg_stars = sum(stars_list) / len(stars_list)
                self.folder_preview.insert(
                    tk.END,
                    f"\n⭐ Star statistics (from DSS):\n"
                    f"  • Frames analyzed: {len(stars_list)}\n"
                    f"  • Average stars: {avg_stars:.1f}\n"
                    f"  • Min stars: {min(stars_list)}\n"
                    f"  • Max stars: {max(stars_list)}\n"
                )
                if zero_star_frames > 0:
                    self.folder_preview.insert(
                        tk.END,
                        f"⚠️ {zero_star_frames} frame(s) had 0 detected stars\n"
                    )

        # DSS outputs
        if dss_outputs:
            self.folder_preview.insert(tk.END, "\n🧪 DSS Outputs:\n")
            for f in dss_outputs:
                self.folder_preview.insert(tk.END, f"  • {f}\n")

        # Sample frame properties
        if frame_props:
            self.folder_preview.insert(tk.END, "\n📷 Sample processed frame properties:\n")
            sample = frame_props[0]
            for key in ["Filename", "Exposure", "ISO", "Device", "Gain", "Stars", "Width", "Height", "Format"]:
                if key in sample:
                    self.folder_preview.insert(tk.END, f"  • {key}: {sample[key]}\n")

        # Flag if no stacked images found
        if no_stacked:
            self.folder_preview.insert(tk.END, "\n⚠️ No stacked images found in this folder\n")

    def parse_dss_processed_images(self, folder):
        """
        Look at all images processed by DSS in the folder, extract properties,
        count stars from info.txt if needed, and detect missing stacked images.

        Returns:
            frame_properties: list of dicts with Exposure, ISO, Device, Filename, Stars
            zero_star_frames: count of frames with 0 stars (if known)
            no_stacked_images_found: True if no DSS output files found
        """
        frame_properties = []
        zero_star_frames = 0

        # DSS outputs
        stacked_files = [f for f in folder.iterdir() if f.suffix.lower() in [".tif", ".tiff"] and ("autosave" in f.name.lower() or "stack" in f.name.lower())]
        no_stacked_images_found = len(stacked_files) == 0

        # Loop through original images that DSS processed (by matching info.txt)
        for info_file in folder.glob("*.info.txt"):
            # Assume DSS info file name matches image name + ".info.txt"
            img_name = info_file.stem.replace(".info", "")  # remove .info suffix
            # Try to find image file with same name and known extensions
            img_file = None
            for ext in [".tif", ".tiff", ".fits", ".fit", ".jpg", ".jpeg", ".png"]:
                candidate = folder / f"{img_name}{ext}"
                if candidate.exists():
                    img_file = candidate
                    break
            if img_file is None:
                continue  # skip if original image not found

            props = self.get_image_properties(img_file)
            props["Filename"] = img_file.name

            # Optional: parse star count from info.txt
            stars = 0
            try:
                with open(info_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("NrStars"):
                            stars = int(line.split("=")[1].strip())
                            if stars == 0:
                                zero_star_frames += 1
                            break
            except Exception:
                pass
            props["Stars"] = stars

            frame_properties.append(props)

        return frame_properties, zero_star_frames, no_stacked_images_found

    # ---------- RIGHT PANEL: FILE PREVIEW ----------
    def clear_file_preview(self):
        self.file_preview_label.pack_forget()
        self.file_text_preview.pack_forget()
        self.file_text_preview.delete("1.0", tk.END)

    def show_file_preview(self, path):
        self.file_preview_label.pack_forget()
        self.file_text_preview.pack_forget()
        self.file_text_preview.delete("1.0", tk.END)

        suffix = path.suffix.lower()

        # Image preview
        if suffix in [".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"]:
            try:
                self.show_image(path)
            except Exception as e:
                self.file_text_preview.pack(fill=tk.BOTH, expand=True)
                self.file_text_preview.insert(tk.END, f"Cannot load image:\n{e}")

        # Text preview
        elif suffix in [".txt", ".py", ".md", ".json", ".log"]:
            self.file_text_preview.pack(fill=tk.BOTH, expand=True)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    self.file_text_preview.insert(tk.END, f.read())
            except Exception as e:
                self.file_text_preview.insert(tk.END, f"Error:\n{e}")

    def show_image(self, path):
        try:
            img = Image.open(path)
            self.original_image = img
            self.file_preview_label.pack(expand=True)
            self.resize_image()
        except Exception as e:
            self.file_text_preview.pack(fill=tk.BOTH, expand=True)
            self.file_text_preview.insert(tk.END, f"Cannot load image:\n{e}")

    def resize_image(self):
        if not hasattr(self, "original_image"):
            return

        w = self.right_frame.winfo_width()
        h = self.right_frame.winfo_height()
        if w < 10 or h < 10:
            return

        img = self.original_image.copy()
        img.thumbnail((w - 20, h - 80))  # Account for header label
        self.current_image = ImageTk.PhotoImage(img)
        self.file_preview_label.configure(image=self.current_image)


if __name__ == "__main__":
    FileExplorer().mainloop()