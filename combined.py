import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import exposure
import concurrent.futures
import time

# --- SETTINGS ---
input_file = "Autosave.tif"
bg_kernel = 151
thresh_sigma = 3.0
stretch_strength = 10.0
num_workers = 8
block_size = 512
enhance_factor = 1.5       # star enhancement factor
gamma = 2.2                # gamma for 8-bit export
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
else:
    print("🖤 Grayscale image detected.")
    h, w = img.shape
    c = 1
    img = img[..., np.newaxis]

# Helper functions
def process_block(block):
    return gaussian_filter(block, sigma=bg_kernel / 10)

def process_channel(channel_data):
    """Process one channel: background subtraction and star extraction."""
    h, w = channel_data.shape
    background = np.zeros_like(channel_data)

    # Divide into tiles for parallel processing
    tiles = [(y, min(y+block_size, h), x, min(x+block_size, w))
             for y in range(0, h, block_size)
             for x in range(0, w, block_size)]

    def compute_tile(tile):
        y, y2, x, x2 = tile
        return (tile, process_block(channel_data[y:y2, x:x2]))

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as ex:
        for tile, bg_block in ex.map(compute_tile, tiles):
            y, y2, x, x2 = tile
            background[y:y2, x:x2] = bg_block

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

    star_map = np.zeros_like(channel_data)
    star_map[star_mask] = channel_data[star_mask]
    starless = channel_data.copy()
    starless[star_mask] = background[star_mask]

    clean = channel_data - background
    clean[clean < 0] = 0
    result = np.clip(clean + star_map, 0, 1)
    return background, star_map, starless, result

# Process each channel
backgrounds, stars, starlesses, results = [], [], [], []
for i in range(c):
    print(f"🧠 Processing channel {i+1}/{c}...")
    bg, sm, sl, res = process_channel(img[..., i])
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

print("✨ Enhancing stars and recombining with background...")
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

# --- Save final outputs only ---
print("💾 Saving final enhanced images...")
cv2.imwrite("final_star_enhanced_rgb16.tif",
            (rgb_result * 65535).astype(np.uint16))

print("\n✅ Done!")
print("   • final_star_enhanced_rgb16.tif  (16-bit RGB, linear)")
print(f"⏱️ Total time: {time.time() - start_time:.2f}s using {num_workers} threads")
