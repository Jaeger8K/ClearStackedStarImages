import cv2
import numpy as np
import os
import tkinter as tk
import tifffile as tiff
from tkinter import filedialog, messagebox


def select_input_file():
    root = tk.Tk()
    root.withdraw()

    path = filedialog.askopenfilename(
        title="Select Autosave.tif",
        filetypes=[("TIFF files", "*.tif *.tiff")]
    )

    if not path:
        # User cancelled → clean exit
        return None

    if not os.path.isfile(path):
        messagebox.showerror("Error", "Selected file does not exist")
        return None

    return path



def load_image(filepath):
    img = tiff.imread(filepath)

    if img is None:
        raise FileNotFoundError(filepath)

    img = img.astype(np.float32)

    # Normalize safely
    maxv = img.max()
    if maxv > 1.5:
        img /= maxv

    return img


def save_output(rgb_result, input_file):
    out = os.path.join(
        os.path.dirname(input_file),
        "final_star_enhanced_rgb16.tif"
    )

    rgb_result = np.clip(rgb_result, 0, 1)
    cv2.imwrite(out, (rgb_result * 65535).astype(np.uint16))
    return out
