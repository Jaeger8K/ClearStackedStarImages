import numpy as np
import cv2
from scipy.ndimage import gaussian_filter
from skimage import exposure


def create_circular_kernel(radius):
    d = radius * 2 + 1
    y, x = np.ogrid[:d, :d]
    mask = (x - radius)**2 + (y - radius)**2 <= radius**2
    kernel = np.zeros((d, d), np.uint8)
    kernel[mask] = 1
    return kernel


def detect_stars(channel, config):
    g_small = gaussian_filter(channel, 1.0)
    g_large = gaussian_filter(channel, 4.0)
    hp = g_small - g_large

    threshold = config.THRESH_SIGMA * np.std(hp)
    binary = hp > threshold

    local_mean = gaussian_filter(channel, 1.0)
    chromatic_ratio = channel / (local_mean + 1e-10)
    binary &= chromatic_ratio < 2.5

    binary = binary.astype(np.uint8)

    kernel = (
        create_circular_kernel(1)
        if config.USE_CIRCULAR_KERNEL
        else np.ones((3, 3), np.uint8)
    )

    dilated = cv2.dilate(binary, kernel, iterations=1)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        dilated, connectivity=8
    )

    clean = np.zeros_like(dilated)
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= 3:
            clean[labels == i] = 1

    mask = gaussian_filter(clean.astype(float), sigma=1.5)
    return np.clip(mask, 0, 1)


def create_adaptive_boost(star_map, is_color, config):
    if is_color:
        lum = (
            0.2126 * star_map[..., 2] +
            0.7152 * star_map[..., 1] +
            0.0722 * star_map[..., 0]
        )
    else:
        lum = star_map[..., 0]

    norm = lum / (np.max(lum) + 1e-10)

    boost = np.where(
        norm < config.BRIGHT_STAR_THRESHOLD,
        config.DIM_STAR_BOOST *
        (1 - norm / config.BRIGHT_STAR_THRESHOLD) +
        config.ENHANCE_FACTOR,
        config.ENHANCE_FACTOR
    )

    return lum, boost


def enhance_stars(star_map, is_color, config):
    lum, boost = create_adaptive_boost(star_map, is_color, config)

    if is_color:
        enhanced = np.zeros_like(star_map)
        for i in range(3):
            ratio = star_map[..., i] / (lum + 1e-10)
            enhanced[..., i] = boost * ratio * lum
    else:
        enhanced = star_map * boost

    return np.clip(enhanced, 0, 1)


def stretch(x, strength):
    return exposure.rescale_intensity(
        np.arcsinh(x * strength),
        out_range=(0, 1)
    )


def sharpen(img):
    blur = cv2.GaussianBlur(img, (0, 0), 1.2)
    return np.clip(cv2.addWeighted(img, 1.1, blur, -0.1, 0), 0, 1)
