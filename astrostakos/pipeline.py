import numpy as np
from scipy.ndimage import label
from .config import Config
from .io import load_image, save_output, select_input_file
from .preprocessing import remove_hot_pixels, prepare_channels
from .background import estimate_background_tiled
from .stars import detect_stars, enhance_stars, stretch, sharpen


def run(input_file=None, config=None):
    config = config or Config()

    if input_file is None:
        input_file = select_input_file()
    if not input_file:
        return None

    img = load_image(input_file)
    img = remove_hot_pixels(img)

    img, luminance, is_color = prepare_channels(img)
    h, w, c = img.shape

    # Star detection
    star_mask = detect_stars(luminance, config)

    # Count individual stars
    labeled_stars, num_stars = label(star_mask)

    backgrounds = []
    stars = []
    starless = []

    for i in range(c):
        gated_mask = star_mask * (img[..., i] > 0.01)

        bg = estimate_background_tiled(img[..., i], config)
        star_signal = np.clip(img[..., i] - bg, 0, 1)

        sm = star_signal * gated_mask
        sl = img[..., i] - sm

        backgrounds.append(bg)
        stars.append(sm)
        starless.append(sl)

    star_map = np.stack(stars, axis=-1)
    starless = np.stack(starless, axis=-1)

    enhanced = enhance_stars(star_map, is_color, config)
    stretched = stretch(enhanced, config.STRETCH_STRENGTH)

    result = np.clip(starless + stretched, 0, 1)
    result = sharpen(result)

    return save_output(result, input_file, num_stars)
