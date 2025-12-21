import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from skimage import exposure
import concurrent.futures
import tkinter as tk
from tkinter import filedialog, messagebox
import time
import os

# --- CONFIGURATION ---
class Config:
    """Configuration parameters for star enhancement"""
    BG_KERNEL = 75
    THRESH_SIGMA = 3.0
    STRETCH_STRENGTH = 10.0
    NUM_WORKERS = 8
    BLOCK_SIZE = 512
    OVERLAP = 150
    ENHANCE_FACTOR = 1.3
    DIM_STAR_BOOST = 3.5
    BRIGHT_STAR_THRESHOLD = 0.3
    GAMMA = 2.2
    USE_CIRCULAR_KERNEL = True


# --- FILE I/O FUNCTIONS ---
def select_input_file():
    """Open file dialog to select input TIFF file"""
    root = tk.Tk()
    root.withdraw()
    
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
    return input_file


def load_and_normalize_image(filepath):
    """Load image and normalize to [0, 1] range"""
    print("📂 Loading image...")
    img = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"❌ Could not load {filepath}")
    
    img = img.astype(np.float32)
    if np.max(img) > 1.5:
        img /= 65535.0  # Handle 16-bit
    
    return img


def prepare_image_channels(img):
    """Prepare image channels and compute luminance"""
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
    
    return img, luminance, is_color, (h, w, c)


def save_output(rgb_result, input_file):
    """Save the final enhanced image"""
    print("💾 Saving final enhanced images...")
    output_dir = os.path.dirname(input_file)
    output_path = os.path.join(output_dir, "final_star_enhanced_rgb16.tif")
    
    cv2.imwrite(output_path, (rgb_result * 65535).astype(np.uint16))
    print(f"💾 Saved output to:\n{output_path}")


# --- IMAGE PROCESSING UTILITY FUNCTIONS ---
def create_blend_weights(h, w, overlap):
    """Create smooth cosine-based blend weights for tile edges"""
    weights = np.ones((h, w), dtype=np.float32)
    if overlap > 0:
        actual_overlap_h = min(overlap, h // 2)
        actual_overlap_w = min(overlap, w // 2)
        
        for i in range(actual_overlap_h):
            alpha = 0.5 * (1 - np.cos(np.pi * i / actual_overlap_h))
            weights[i, :] *= alpha
            weights[-(i+1), :] *= alpha
        
        for i in range(actual_overlap_w):
            alpha = 0.5 * (1 - np.cos(np.pi * i / actual_overlap_w))
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


def process_block_with_blend(block, bg_kernel):
    """Apply Gaussian filter to a single block"""
    return gaussian_filter(block, sigma=bg_kernel / 10)


# --- BACKGROUND ESTIMATION ---
def estimate_background_tiled(channel_data, config):
    """Estimate background using overlapping tiles with smooth blending"""
    h, w = channel_data.shape
    background = np.zeros_like(channel_data)
    weight_sum = np.zeros_like(channel_data)
    
    step = config.BLOCK_SIZE - config.OVERLAP
    tiles = [(y, min(y + config.BLOCK_SIZE, h), x, min(x + config.BLOCK_SIZE, w))
             for y in range(0, h, step)
             for x in range(0, w, step)]
    
    def compute_tile(tile):
        y, y2, x, x2 = tile
        block = channel_data[y:y2, x:x2]
        bg_block = process_block_with_blend(block, config.BG_KERNEL)
        weights = create_blend_weights(y2-y, x2-x, config.OVERLAP)
        return (tile, bg_block, weights)
    
    print(f"   Processing {len(tiles)} overlapping tiles...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.NUM_WORKERS) as ex:
        for tile, bg_block, weights in ex.map(compute_tile, tiles):
            y, y2, x, x2 = tile
            background[y:y2, x:x2] += bg_block * weights
            weight_sum[y:y2, x:x2] += weights
    
    background = np.divide(background, weight_sum, where=weight_sum > 0)
    return background


# --- STAR DETECTION ---
def detect_stars(channel_data, config):
    """Detect stars using high-pass filtering and create soft mask"""
    g_small = gaussian_filter(channel_data, sigma=1.0)
    g_large = gaussian_filter(channel_data, sigma=4.0)
    hp = g_small - g_large
    sigma_hp = np.std(hp)
    threshold_value = config.THRESH_SIGMA * sigma_hp
    star_mask_binary = hp > threshold_value
    
    star_mask_binary_uint8 = star_mask_binary.astype(np.uint8)
    
    if config.USE_CIRCULAR_KERNEL:
        kernel = create_circular_kernel(radius=1)
    else:
        kernel = np.ones((3, 3), np.uint8)
    
    star_mask_dilated = cv2.dilate(star_mask_binary_uint8, kernel, iterations=1)
    
    # Create soft mask with Gaussian falloff
    star_mask = gaussian_filter(star_mask_dilated.astype(np.float32), sigma=1.5)
    star_mask = np.clip(star_mask, 0, 1)
    
    return star_mask


# --- CHANNEL PROCESSING ---
def process_channel_improved(channel_data, config, star_mask_ref=None):
    """Process one channel with improved blending and optional shared star mask"""
    background = estimate_background_tiled(channel_data, config)
    
    if star_mask_ref is None:
        star_mask = detect_stars(channel_data, config)
    else:
        star_mask = star_mask_ref
    
    # Extract stars
    star_signal = channel_data - background
    star_signal[star_signal < 0] = 0
    star_map = star_signal * star_mask
    
    # Create starless version
    starless = channel_data - star_map
    
    clean = channel_data - background
    clean[clean < 0] = 0
    result = np.clip(clean + star_map, 0, 1)
    
    return background, star_map, starless, result, star_mask


# --- STAR ENHANCEMENT ---
def create_adaptive_boost_mask(star_map, is_color, config):
    """Create adaptive enhancement mask that boosts dim stars more"""
    if is_color:
        star_luminosity = (0.2126 * star_map[..., 2] + 
                          0.7152 * star_map[..., 1] + 
                          0.0722 * star_map[..., 0])
    else:
        star_luminosity = star_map[..., 0] if star_map.ndim == 3 else star_map
    
    normalized_luminosity = star_luminosity / (np.max(star_luminosity) + 1e-10)
    
    adaptive_boost = np.where(
        normalized_luminosity < config.BRIGHT_STAR_THRESHOLD,
        config.DIM_STAR_BOOST * (1.0 - normalized_luminosity / config.BRIGHT_STAR_THRESHOLD) + config.ENHANCE_FACTOR,
        config.ENHANCE_FACTOR
    )
    
    return star_luminosity, adaptive_boost


def enhance_stars(star_map, is_color, config):
    """Enhance stars using adaptive luminosity-based method"""
    print("✨ Enhancing stars using adaptive luminosity-based method...")
    
    star_luminosity, adaptive_boost = create_adaptive_boost_mask(star_map, is_color, config)
    
    if is_color:
        enhancement_mask = np.clip(star_luminosity * adaptive_boost, 0, 1)
        enhanced_stars = np.zeros_like(star_map)
        
        for i in range(3):
            ratio = np.divide(star_map[..., i], star_luminosity + 1e-10, 
                            out=np.zeros_like(star_map[..., i]), 
                            where=star_luminosity > 1e-10)
            enhanced_stars[..., i] = enhancement_mask * ratio
        
        enhanced_stars = np.clip(enhanced_stars, 0, 1)
    else:
        enhanced_stars = np.clip(star_map * adaptive_boost, 0, 1)
    
    return enhanced_stars


def stretch(x, strength=10.0):
    """Apply asinh stretch to image data"""
    return exposure.rescale_intensity(np.arcsinh(x * strength), out_range=(0, 1))


def apply_stretch_and_sharpen(starless, enhanced_stars, config):
    """Apply stretch to stars and recombine with background"""
    print("🎨 Applying asinh stretch to STARS ONLY...")
    
    stretched_stars = stretch(enhanced_stars, config.STRETCH_STRENGTH)
    stretched_result = np.clip(starless + stretched_stars, 0, 1)
    
    # Mild sharpening
    blur = cv2.GaussianBlur(stretched_result, (0, 0), sigmaX=1.2)
    sharpened = cv2.addWeighted(stretched_result, 1.1, blur, -0.1, 0)
    sharpened = np.clip(sharpened, 0, 1)
    
    return sharpened


def convert_to_rgb(image, is_color):
    """Convert grayscale to RGB if needed"""
    if not is_color:
        return cv2.merge([image, image, image])
    return image


# --- MAIN PIPELINE ---
def process_all_channels(img, luminance, config):
    """Process all channels using shared star mask"""
    print("🔍 Detecting stars from luminance channel...")
    _, _, _, _, common_star_mask = process_channel_improved(luminance, config)
    
    c = img.shape[-1]
    backgrounds, stars, starlesses, results = [], [], [], []
    
    for i in range(c):
        print(f"🧠 Processing channel {i+1}/{c} with shared star mask...")
        bg, sm, sl, res, _ = process_channel_improved(img[..., i], config, star_mask_ref=common_star_mask)
        backgrounds.append(bg)
        stars.append(sm)
        starlesses.append(sl)
        results.append(res)
    
    background = np.stack(backgrounds, axis=-1)
    star_map = np.stack(stars, axis=-1)
    starless = np.stack(starlesses, axis=-1)
    result = np.stack(results, axis=-1)
    
    return background, star_map, starless, result


def print_summary(start_time, config):
    """Print processing summary"""
    print("\n✅ Done!")
    print("   • final_star_enhanced_rgb16.tif  (16-bit RGB, linear)")
    print(f"⏱️ Total time: {time.time() - start_time:.2f}s using {config.NUM_WORKERS} threads")
    print("\n💡 Key improvements:")
    print("   ✓ Increased overlap to 150 pixels")
    print("   ✓ Cosine-based blending (smoother than linear)")
    print("   ✓ Soft Gaussian star mask (preserves circular shapes)")
    print("   ✓ Minimal dilation to avoid shape distortion")
    print("   ✓ Adaptive enhancement: dim stars boosted more than bright stars")
    print("   ✓ Softer sharpening parameters")
    print("   ✓ Fixed blend weights index error")


# --- MAIN EXECUTION ---
def main():
    """Main execution pipeline"""
    start_time = time.time()
    config = Config()
    
    print("🚀 Starting full star-field enhancement pipeline...")
    
    # Load and prepare image
    input_file = select_input_file()
    print(f"Input file: {input_file}")
    
    img = load_and_normalize_image(input_file)
    img, luminance, is_color, (h, w, c) = prepare_image_channels(img)
    
    # Process channels
    background, star_map, starless, result = process_all_channels(img, luminance, config)
    
    # Enhance stars
    enhanced_stars = enhance_stars(star_map, is_color, config)
    
    # Apply stretch and sharpen
    sharpened = apply_stretch_and_sharpen(starless, enhanced_stars, config)
    
    # Convert to RGB
    rgb_result = convert_to_rgb(sharpened, is_color)
    
    # Save output
    save_output(rgb_result, input_file)
    
    # Print summary
    print_summary(start_time, config)


if __name__ == "__main__":
    main()