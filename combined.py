import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import exposure
import concurrent.futures
import tkinter as tk
from tkinter import filedialog, messagebox
import time
import os

# --- SETTINGS ---

# --- Simple UI for file selection ---
root = tk.Tk()
root.withdraw()  # Hide main Tk window

input_file = filedialog.askopenfilename(
    title="Select Autosave.tif",
    filetypes=[("TIFF files", "*.tif *.tiff")]
)

if not input_file:
    raise RuntimeError("❌ No file selected.")

if not os.path.isfile(input_file):
    messagebox.showerror(
        "File Not Found",
        f"Could not find:\n{input_file}"
    )
    raise FileNotFoundError(f"❌ Could not find {input_file}")

print(f"✅ Using input file: {input_file}")

bg_kernel = 75                
thresh_sigma = 3.0
stretch_strength = 10.0
num_workers = 8
block_size = 512
overlap = 150                 # INCREASED overlap for better blending
enhance_factor = 1.3          
dim_star_boost = 3.5          # NEW: Extra boost for dim stars
bright_star_threshold = 0.3   # NEW: Threshold to distinguish bright vs dim stars
gamma = 2.2
use_circular_kernel = True    # NEW: Use circular kernel for star dilation
# -----------------

start_time = time.time()
print("🚀 Starting full star-field enhancement pipeline...")
print(f"Input file: {input_file}")

# Load TIF image
print("📂 Loading image...")
img = cv2.imread(input_file, cv2.IMREAD_UNCHANGED)
if img is None:
    raise FileNotFoundError(f"❌ Could not load {input_file}")

# Normalize image
img = img.astype(np.float32)
if np.max(img) > 1.5:
    img /= 65535.0  # handle 16-bit

# Check color
is_color = img.ndim == 3
if is_color:
    print("🎨 RGB image detected.")
    h, w, c = img.shape
    luminance = 0.2126 * img[..., 2] + 0.7152 * img[..., 1] + 0.0722 * img[..., 0]
else:
    print("🖤 Grayscale image detected.")
    h, w = img.shape
    c = 1
    img = img[..., np.newaxis]
    luminance = img[..., 0]

# Helper functions with improved blending
def process_block_with_blend(block):
    return gaussian_filter(block, sigma=bg_kernel / 10)

def create_blend_weights(h, w, overlap):
    """Create smooth cosine-based blend weights for tile edges"""
    weights = np.ones((h, w), dtype=np.float32)
    if overlap > 0:
        # Use cosine taper for smoother blending (better than linear)
        # Clamp overlap to actual dimensions
        actual_overlap_h = min(overlap, h // 2)
        actual_overlap_w = min(overlap, w // 2)
        
        for i in range(actual_overlap_h):
            alpha = 0.5 * (1 - np.cos(np.pi * i / actual_overlap_h))  # Cosine taper
            weights[i, :] *= alpha
            weights[-(i+1), :] *= alpha
        
        for i in range(actual_overlap_w):
            alpha = 0.5 * (1 - np.cos(np.pi * i / actual_overlap_w))  # Cosine taper
            weights[:, i] *= alpha
            weights[:, -(i+1)] *= alpha
    return weights

def create_circular_kernel(radius):
    """Create circular kernel instead of square for star dilation"""
    diameter = 2 * radius + 1
    kernel = np.zeros((diameter, diameter), dtype=np.uint8)
    center = radius
    y, x = np.ogrid[:diameter, :diameter]
    mask = (x - center)**2 + (y - center)**2 <= radius**2
    kernel[mask] = 1
    return kernel

def preserve_star_shapes(channel_data, star_mask, background):
    """Extract stars while preserving their original shapes"""
    # Instead of binary mask, use soft-edge extraction
    star_map = np.zeros_like(channel_data)
    
    # Get star pixels with a small gradient falloff at edges
    star_signal = channel_data - background
    star_signal[star_signal < 0] = 0
    
    # Apply mask but preserve the gradual falloff
    star_map = star_signal * star_mask
    
    return star_map

def process_channel_improved(channel_data, star_mask_ref=None):
    """Process one channel with improved blending and optional shared star mask."""
    h, w = channel_data.shape
    background = np.zeros_like(channel_data)
    weight_sum = np.zeros_like(channel_data)

    # Create overlapping tiles with larger overlap
    step = block_size - overlap
    tiles = [(y, min(y+block_size, h), x, min(x+block_size, w))
             for y in range(0, h, step)
             for x in range(0, w, step)]

    def compute_tile(tile):
        y, y2, x, x2 = tile
        block = channel_data[y:y2, x:x2]
        bg_block = process_block_with_blend(block)
        weights = create_blend_weights(y2-y, x2-x, overlap)
        return (tile, bg_block, weights)

    print(f"   Processing {len(tiles)} overlapping tiles...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as ex:
        for tile, bg_block, weights in ex.map(compute_tile, tiles):
            y, y2, x, x2 = tile
            background[y:y2, x:x2] += bg_block * weights
            weight_sum[y:y2, x:x2] += weights

    # Normalize by weight sum to blend overlaps smoothly
    background = np.divide(background, weight_sum, where=weight_sum > 0)

    # Use provided star mask or compute from this channel
    if star_mask_ref is None:
        # High-pass filtering for star detection
        g_small = gaussian_filter(channel_data, sigma=1.0)
        g_large = gaussian_filter(channel_data, sigma=4.0)
        hp = g_small - g_large
        sigma_hp = np.std(hp)
        threshold_value = thresh_sigma * sigma_hp
        star_mask_binary = hp > threshold_value
        
        # Create SOFT star mask using distance transform for circular falloff
        star_mask_binary_uint8 = star_mask_binary.astype(np.uint8)
        
        # Light dilation to capture full star extent
        if use_circular_kernel:
            kernel = create_circular_kernel(radius=1)  # Smaller radius
        else:
            kernel = np.ones((3, 3), np.uint8)
        
        star_mask_dilated = cv2.dilate(star_mask_binary_uint8, kernel, iterations=1)
        
        # Create soft mask with Gaussian falloff
        star_mask = gaussian_filter(star_mask_dilated.astype(np.float32), sigma=1.5)
        star_mask = np.clip(star_mask, 0, 1)
    else:
        star_mask = star_mask_ref

    # Extract stars preserving original shapes
    star_signal = channel_data - background
    star_signal[star_signal < 0] = 0
    star_map = star_signal * star_mask
    
    # Create starless version
    starless = channel_data - star_map

    clean = channel_data - background
    clean[clean < 0] = 0
    result = np.clip(clean + star_map, 0, 1)
    return background, star_map, starless, result, star_mask

# Detect stars using luminance channel only
print("🔍 Detecting stars from luminance channel...")
_, _, _, _, common_star_mask = process_channel_improved(luminance)

# Process each channel using the SAME star mask
backgrounds, stars, starlesses, results = [], [], [], []
for i in range(c):
    print(f"🧠 Processing channel {i+1}/{c} with shared star mask...")
    bg, sm, sl, res, _ = process_channel_improved(img[..., i], star_mask_ref=common_star_mask)
    backgrounds.append(bg)
    stars.append(sm)
    starlesses.append(sl)
    results.append(res)

background = np.stack(backgrounds, axis=-1)
star_map = np.stack(stars, axis=-1)
starless = np.stack(starlesses, axis=-1)
result = np.stack(results, axis=-1)

# Enhancement functions
def stretch(x, strength=10.0):
    return exposure.rescale_intensity(np.arcsinh(x * strength), out_range=(0, 1))

print("✨ Enhancing stars using adaptive luminosity-based method...")

# Luminosity-based enhancement (preserves color ratios)
if is_color:
    star_luminosity = 0.2126 * star_map[..., 2] + 0.7152 * star_map[..., 1] + 0.0722 * star_map[..., 0]
    
    # Adaptive enhancement: boost dim stars more than bright stars
    # Create enhancement curve that gives more boost to dim stars
    normalized_luminosity = star_luminosity / (np.max(star_luminosity) + 1e-10)
    
    # Smooth curve: dim stars get more boost, bright stars get less
    # Using inverse relationship: dimmer = more boost
    adaptive_boost = np.where(
        normalized_luminosity < bright_star_threshold,
        dim_star_boost * (1.0 - normalized_luminosity / bright_star_threshold) + enhance_factor,
        enhance_factor
    )
    
    enhancement_mask = np.clip(star_luminosity * adaptive_boost, 0, 1)
    
    enhanced_stars = np.zeros_like(star_map)
    for i in range(3):
        ratio = np.divide(star_map[..., i], star_luminosity + 1e-10, 
                         out=np.zeros_like(star_map[..., i]), 
                         where=star_luminosity > 1e-10)
        enhanced_stars[..., i] = enhancement_mask * ratio
    
    enhanced_stars = np.clip(enhanced_stars, 0, 1)
else:
    # Adaptive enhancement for grayscale
    normalized_luminosity = star_map / (np.max(star_map) + 1e-10)
    adaptive_boost = np.where(
        normalized_luminosity < bright_star_threshold,
        dim_star_boost * (1.0 - normalized_luminosity / bright_star_threshold) + enhance_factor,
        enhance_factor
    )
    enhanced_stars = np.clip(star_map * adaptive_boost, 0, 1)

enhanced_result = np.clip(starless + enhanced_stars, 0, 1)

print("🎨 Applying asinh stretch...")
stretched_result = stretch(enhanced_result, stretch_strength)

# Optional mild sharpening with Gaussian blur (smoother)
blur = cv2.GaussianBlur(stretched_result, (0, 0), sigmaX=1.5)
sharpened = cv2.addWeighted(stretched_result, 1.2, blur, -0.2, 0)
sharpened = np.clip(sharpened / (np.max(sharpened) + 1e-8), 0, 1)

# Convert grayscale → RGB if needed
if not is_color:
    rgb_result = cv2.merge([sharpened, sharpened, sharpened])
else:
    rgb_result = sharpened

# --- Save final outputs ---
print("💾 Saving final enhanced images...")
cv2.imwrite("final_star_enhanced_rgb16.tif",
            (rgb_result * 65535).astype(np.uint16))

print("\n✅ Done!")
print("   • final_star_enhanced_rgb16.tif  (16-bit RGB, linear)")
print(f"⏱️ Total time: {time.time() - start_time:.2f}s using {num_workers} threads")
print("\n💡 Key improvements:")
print("   ✓ Increased overlap to 150 pixels")
print("   ✓ Cosine-based blending (smoother than linear)")
print("   ✓ Soft Gaussian star mask (preserves circular shapes)")
print("   ✓ Minimal dilation to avoid shape distortion")
print("   ✓ Adaptive enhancement: dim stars boosted more than bright stars")
print("   ✓ Softer sharpening parameters")
print("   ✓ Fixed blend weights index error")