import tkinter as tk
from tkinter import ttk
from pathlib import Path

from dss.parser import parse_dss_processed_images


class FolderSummary(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)

        label = ttk.Label(
            self,
            text="Folder Summary",
            font=("Arial", 12, "bold")
        )
        label.pack(pady=5)

        self.text = tk.Text(self, wrap="word")
        self.text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def show(self, folder: Path):
        self.text.delete("1.0", tk.END)

        files = list(folder.iterdir())

        # DSS stacked output files (filtered by suffix and naming)
        dss_outputs = [
            f.name for f in files
            if f.suffix.lower() in (".tif", ".tiff")
            and ("autosave" in f.name.lower() or "stack" in f.name.lower())
        ]

        no_stacked = len(dss_outputs) == 0

        # Parse DSS processed frames info
        frame_props, zero_star_frames, no_stacked_images_found = parse_dss_processed_images(folder)

        # Frame count summary
        if frame_props:
            self.text.insert(tk.END, "📸 Frames detected:\n")
            self.text.insert(tk.END, f"  • Total DSS-processed frames: {len(frame_props)}\n")
        else:
            self.text.insert(tk.END, "⚠️ No DSS-processed frames detected.\n")

        # Star statistics summary
        if frame_props:
            stars = [f.get("Stars", 0) for f in frame_props]
            if stars:
                avg_stars = sum(stars) / len(stars)
                self.text.insert(tk.END, "\n⭐ Star statistics (from DSS):\n")
                self.text.insert(tk.END, f"  • Frames analyzed: {len(stars)}\n")
                self.text.insert(tk.END, f"  • Average stars: {avg_stars:.1f}\n")
                self.text.insert(tk.END, f"  • Min stars: {min(stars)}\n")
                self.text.insert(tk.END, f"  • Max stars: {max(stars)}\n")

                if zero_star_frames > 0:
                    self.text.insert(tk.END, f"⚠️ {zero_star_frames} frame(s) had 0 detected stars\n")

        # DSS output files summary
        if dss_outputs:
            self.text.insert(tk.END, "\n🧪 DSS Outputs:\n")
            for f in dss_outputs:
                self.text.insert(tk.END, f"  • {f}\n")

        # Sample frame properties (show first frame as example)
        if frame_props:
            self.text.insert(tk.END, "\n📷 Sample processed frame properties:\n")
            sample = frame_props[0]

            # Define keys to show in desired order
            keys_to_show = [
                "Filename",
                "Exposure",
                "ISO",
                "Device",
                "Gain",
                "Stars",
                "Width",
                "Height",
                "Format",
                "F-stop",
                "Flash",
                "Focal Length",
                "White Balance",
                "Metering Mode",
                "Exposure Program",
                "Date Taken",
                "GPSInfo",
            ]

            for key in keys_to_show:
                if key in sample:
                    value = sample[key]
                    if key == "GPSInfo" and isinstance(value, dict):
                        # Format GPS info nicely
                        gps_lines = [f"    {k}: {v}" for k, v in value.items()]
                        gps_text = "\n".join(gps_lines)
                        self.text.insert(tk.END, f"  • {key}:\n{gps_text}\n")
                    else:
                        self.text.insert(tk.END, f"  • {key}: {value}\n")

        # Warn if no stacked images found (based on dss outputs)
        if no_stacked:
            self.text.insert(tk.END, "\n⚠️ No stacked images found in this folder\n")
