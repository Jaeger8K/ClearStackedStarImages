import numpy as np
from scipy.ndimage import label
from .config import Config
from .io import load_image, save_output, select_input_file
from .preprocessing import remove_hot_pixels, prepare_channels
from .background import estimate_background_tiled
from .stars import detect_stars, enhance_stars, stretch, sharpen


def run(input_file=None, config=None, on_progress=None):
    """
    Run processing pipeline.

    on_progress: optional callable(fraction: float, message: str|None) -> bool|None.
                 If it returns False, pipeline will raise RuntimeError("Cancelled").
    """
    def _report(frac, msg=None):
        if on_progress:
            cont = on_progress(frac, msg)
            if cont is False:
                raise RuntimeError("Cancelled")

    config = config or Config()

    _report(0.00, "Starting")
    if input_file is None:
        input_file = select_input_file()
    if not input_file:
        return None

    _report(0.05, "Loading image")
    img = load_image(input_file)

    _report(0.10, "Removing hot pixels")
    img = remove_hot_pixels(img)

    _report(0.15, "Preparing channels")
    img, luminance, is_color = prepare_channels(img)
    h, w, c = img.shape

    _report(0.20, "Detecting stars")
    star_mask = detect_stars(luminance, config)
    _report(0.35, "Stars detected")

    labeled_stars, num_stars = label(star_mask)

    backgrounds = []
    stars = []
    starless = []

    for i in range(c):
        _report(0.36 + (i / max(1, c)) * 0.01, f"Channel {i+1}/{c}: preparing")
        gated_mask = star_mask * (img[..., i] > 0.01)

        # background estimation: allow progress per-tile
        bg = estimate_background_tiled(
            img[..., i],
            config,
            on_progress=(lambda p, msg=None, idx=i: on_progress and on_progress(0.35 + p * 0.30, f"Background ch {idx+1}/{c}: {msg}")) if on_progress else None
        )
        _report(0.36 + ((i + 1) / max(1, c)) * 0.30, f"Background ch {i+1}/{c} done")

        star_signal = np.clip(img[..., i] - bg, 0, 1)

        sm = star_signal * gated_mask
        sl = img[..., i] - sm

        backgrounds.append(bg)
        stars.append(sm)
        starless.append(sl)

    _report(0.67, "Combining channels")
    star_map = np.stack(stars, axis=-1)
    starless = np.stack(starless, axis=-1)

    _report(0.75, "Enhancing stars")
    enhanced = enhance_stars(star_map, is_color, config)

    _report(0.85, "Stretching")
    stretched = stretch(enhanced, config.STRETCH_STRENGTH)

    _report(0.90, "Sharpening & composing")
    result = np.clip(starless + stretched, 0, 1)
    result = sharpen(result)

    _report(0.95, "Saving output")
    out = save_output(result, input_file, num_stars)
    _report(1.00, "Done")

    return out
