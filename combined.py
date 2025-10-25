import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import exposure
import concurrent.futures
import time
import os

# --- SETTINGS ---

# --- Request input folder path from user ---
folder_path = input("📁 Enter the folder containing 'Autosave.tif': ").strip()
input_file = os.path.join(folder_path, "Autosave.tif")

if not os.path.isfile(input_file):
    raise FileNotFoundError(f"❌ Could not find {input_file}")

print(f"✅ Using input file: {input_file}")

bg_kernel = 75                # REDUCED from 151 to avoid over-smoothing
thresh_sigma = 3.0
stretch_strength = 10.0
num_workers = 8
block_size = 512
overlap = 50                  # NEW: overlap tiles to prevent seams
enhance_factor = 1.3          # REDUCED from 1.5 for subtler enhancement
gamma = 2.2
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
    # NEW: Use luminance channel for star detection to avoid per-channel artifacts
    luminance = 0.2126 * img[..., 2] + 0.7152 * img[..., 1] + 0.0722 * img[..., 0]
else:
    print("🖤 Grayscale image detected.")
    h, w = img.shape
    c = 1
    img = img[..., np.newaxis]
    luminance = img[..., 0]

# Helper functions with overlap handling
def process_block_with_blend(block):
    return gaussian_filter(block, sigma=bg_kernel / 10)

def create_blend_weights(h, w, overlap):
    """Create smooth blend weights for tile edges"""
    weights = np.ones((h, w), dtype=np.float32)
    if overlap > 0:
        # Feather edges
        for i in range(overlap):
            alpha = i / overlap
            weights[i, :] *= alpha
            weights[-(i+1), :] *= alpha
            weights[:, i] *= alpha
            weights[:, -(i+1)] *= alpha
    return weights

def process_channel_improved(channel_data, star_mask_ref=None):
    """Process one channel with improved blending and optional shared star mask."""
    h, w = channel_data.shape
    background = np.zeros_like(channel_data)
    weight_sum = np.zeros_like(channel_data)

    # Create overlapping tiles
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
        star_mask = hp > threshold_value
        
        # Slight dilation
        kernel = np.ones((3, 3), np.uint8)
        star_mask = cv2.dilate(star_mask.astype(np.uint8), kernel, iterations=2).astype(bool)
    else:
        star_mask = star_mask_ref

    star_map = np.zeros_like(channel_data)
    star_map[star_mask] = channel_data[star_mask]
    starless = channel_data.copy()
    starless[star_mask] = background[star_mask]

    clean = channel_data - background
    clean[clean < 0] = 0
    result = np.clip(clean + star_map, 0, 1)
    return background, star_map, starless, result, star_mask

# NEW: Detect stars using luminance channel only (prevents per-channel detection differences)
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

print("✨ Enhancing stars using luminosity-based method...")

# Luminosity-based enhancement (preserves color ratios)
if is_color:
    star_luminosity = 0.2126 * star_map[..., 2] + 0.7152 * star_map[..., 1] + 0.0722 * star_map[..., 0]
    enhancement_mask = np.clip(star_luminosity * enhance_factor, 0, 1)
    
    enhanced_stars = np.zeros_like(star_map)
    for i in range(3):
        ratio = np.divide(star_map[..., i], star_luminosity + 1e-10, 
                         out=np.zeros_like(star_map[..., i]), 
                         where=star_luminosity > 1e-10)
        enhanced_stars[..., i] = enhancement_mask * ratio
    
    enhanced_stars = np.clip(enhanced_stars, 0, 1)
else:
    enhanced_stars = np.clip(star_map * enhance_factor, 0, 1)

enhanced_result = np.clip(starless + enhanced_stars, 0, 1)

print("🎨 Applying asinh stretch...")
stretched_result = stretch(enhanced_result, stretch_strength)

# Optional mild sharpening
blur = cv2.GaussianBlur(stretched_result, (0, 0), sigmaX=1)
sharpened = cv2.addWeighted(stretched_result, 1.3, blur, -0.3, 0)
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
print("\n💡 If you still see color patches:")
print("   - Try reducing bg_kernel further (e.g., 50)")
print("   - Increase overlap (e.g., 100)")
print("   - Check if your input image has gradient issues")