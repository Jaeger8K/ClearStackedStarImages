import cv2
import numpy as np
from skimage import exposure

# --- SETTINGS ---
star_map_file = "star_map.tif"
starless_file = "starless_image.tif"
enhance_factor = 1.5       # 1.2–2.0 gives nice enhancement
stretch_strength = 10.0     # controls contrast in arcsinh stretch
# -----------------

def stretch(x, strength=10.0):
    """Asinh stretch for natural astro look."""
    return exposure.rescale_intensity(np.arcsinh(x * strength), out_range=(0, 1))

print("📂 Loading starless background and star map...")
starless = cv2.imread(starless_file, cv2.IMREAD_UNCHANGED).astype(np.float32)
star_map = cv2.imread(star_map_file, cv2.IMREAD_UNCHANGED).astype(np.float32)

# Normalize to [0,1] if not already
starless /= np.max(starless)
star_map /= np.max(star_map)

print(f"✨ Enhancing stars by factor ×{enhance_factor}...")
enhanced_stars = np.clip(star_map * enhance_factor, 0, 1)

print("🧮 Recombining enhanced stars with background...")
enhanced_result = np.clip(starless + enhanced_stars, 0, 1)

print("🎨 Applying mild stretch for visual realism...")
stretched_result = stretch(enhanced_result, stretch_strength)

# Optional: mild sharpening of stars only
blur = cv2.GaussianBlur(stretched_result, (0, 0), sigmaX=1)
sharpened = cv2.addWeighted(stretched_result, 1.3, blur, -0.3, 0)

# --- Save a linear 16-bit and an 8-bit display version ---
# Normalize to 0–1 just to be safe
sharpened = np.clip(sharpened / (np.max(sharpened) + 1e-8), 0, 1)

# Convert grayscale result to 3-channel RGB so GIMP can use color tools
rgb_result = cv2.merge([sharpened, sharpened, sharpened])

# Ensure it's 3-channel only
if rgb_result.shape[2] > 3:
    rgb_result = rgb_result[:, :, :3]

print("🧩 Result image shape:", rgb_result.shape)

# Save 16-bit RGB (linear)
cv2.imwrite("final_star_enhanced_rgb16.tif",
            (np.clip(rgb_result, 0, 1) * 65535).astype(np.uint16))

# Optional 8-bit gamma-corrected version for GIMP
gamma = 2.2
gamma_corrected = np.power(np.clip(rgb_result, 0, 1), 1 / gamma)
cv2.imwrite("final_star_enhanced_rgb8_gimp.tif",
            (gamma_corrected * 255).astype(np.uint8))

print("✅ Saved:")
print("   • final_star_enhanced_rgb16.tif  (16-bit RGB, linear)")
print("   • final_star_enhanced_rgb8_gimp.tif  (8-bit RGB, gamma corrected)")
