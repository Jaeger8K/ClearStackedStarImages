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
# -----------------

start_time = time.time()
print("🚀 Starting parallel star field processing...")
print(f"Input file: {input_file}")

# Load TIF image
print("📂 Loading image...")
img = cv2.imread(input_file, cv2.IMREAD_UNCHANGED)
if img is None:
    raise FileNotFoundError(f"❌ Could not load {input_file}")

# Normalize image
img = img.astype(np.float32)
if np.max(img) > 1.5:
    img /= 65535.0  # handle 16-bit images

# Check if color or grayscale
is_color = img.ndim == 3
if is_color:
    print("🎨 Processing RGB color image...")
    h, w, c = img.shape
else:
    print("🖤 Processing grayscale image...")
    h, w = img.shape
    c = 1
    img = img[..., np.newaxis]  # make it 3D for consistency

# Function to compute background block
def process_block(block):
    return gaussian_filter(block, sigma=bg_kernel/10)

def process_channel(channel_data):
    """Process one color channel: background subtraction and star map."""
    print("   🌌 Estimating background in parallel for one channel...")
    h, w = channel_data.shape
    background = np.zeros_like(channel_data)

    tiles = []
    for y in range(0, h, block_size):
        for x in range(0, w, block_size):
            y2 = min(y + block_size, h)
            x2 = min(x + block_size, w)
            tiles.append((y, y2, x, x2))

    def compute_tile(tile):
        y, y2, x, x2 = tile
        block = channel_data[y:y2, x:x2]
        return (tile, process_block(block))

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as ex:
        for tile, bg_block in ex.map(compute_tile, tiles):
            y, y2, x, x2 = tile
            background[y:y2, x:x2] = bg_block

    g_small = gaussian_filter(channel_data, sigma=1.0)
    g_large = gaussian_filter(channel_data, sigma=4.0)
    hp = g_small - g_large
    sigma_hp = np.std(hp)
    threshold_value = thresh_sigma * sigma_hp
    star_mask = hp > threshold_value

    kernel = np.ones((3,3), np.uint8)
    star_mask = cv2.dilate(star_mask.astype(np.uint8), kernel, iterations=2).astype(bool)

    star_map = np.zeros_like(channel_data)
    star_map[star_mask] = channel_data[star_mask]
    starless = channel_data.copy()
    starless[star_mask] = background[star_mask]

    clean = channel_data - background
    clean[clean < 0] = 0
    result = np.clip(clean + star_map, 0, 1)
    return background, star_map, starless, result

# Process all channels
backgrounds, stars, starlesses, results = [], [], [], []
for i in range(c):
    print(f"🧠 Processing channel {i+1}/{c}...")
    bg, sm, sl, res = process_channel(img[..., i])
    backgrounds.append(bg)
    stars.append(sm)
    starlesses.append(sl)
    results.append(res)

# Stack channels back
background = np.stack(backgrounds, axis=-1)
star_map = np.stack(stars, axis=-1)
starless = np.stack(starlesses, axis=-1)
result = np.stack(results, axis=-1)

def stretch(x, strength=10.0):
    return exposure.rescale_intensity(np.arcsinh(x * strength), out_range=(0, 1))

print("🎨 Stretching and saving outputs...")
stretched_result = stretch(result, stretch_strength)
stretched_background = stretch(background, stretch_strength)
stretched_stars = stretch(star_map, stretch_strength)
stretched_starless = stretch(starless, stretch_strength)

def save_tif(name, arr):
    cv2.imwrite(name, (np.clip(arr, 0, 1) * 65535).astype(np.uint16))

save_tif("result_star_preserved.tif", stretched_result)
save_tif("background_estimate.tif", stretched_background)
save_tif("star_map.tif", stretched_stars)
save_tif("starless_image.tif", stretched_starless)

print("\n✅ Done! Files created:")
print(" - result_star_preserved.tif")
print(" - background_estimate.tif")
print(" - star_map.tif")
print(" - starless_image.tif")
print(f"\n⏱️ Total time: {time.time() - start_time:.2f}s using {num_workers} threads")
