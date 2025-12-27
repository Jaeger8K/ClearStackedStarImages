import numpy as np
from scipy.ndimage import gaussian_filter
import concurrent.futures
from .utils import create_blend_weights


def process_block(block, bg_kernel):
    return gaussian_filter(block, sigma=bg_kernel / 10)


def estimate_background_tiled(channel, config, on_progress=None):
    h, w = channel.shape
    background = np.zeros_like(channel)
    weight_sum = np.zeros_like(channel)

    step = config.BLOCK_SIZE - config.OVERLAP
    tiles = [
        (y, min(y + config.BLOCK_SIZE, h),
         x, min(x + config.BLOCK_SIZE, w))
        for y in range(0, h, step)
        for x in range(0, w, step)
    ]

    def compute(tile):
        y1, y2, x1, x2 = tile
        block = channel[y1:y2, x1:x2]
        bg = process_block(block, config.BG_KERNEL)
        weights = create_blend_weights(y2 - y1, x2 - x1, config.OVERLAP)
        return tile, bg, weights

    total = len(tiles)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=config.NUM_WORKERS
    ) as ex:
        for idx, (tile, bg, wgt) in enumerate(ex.map(compute, tiles)):
            y1, y2, x1, x2 = tile
            background[y1:y2, x1:x2] += bg * wgt
            weight_sum[y1:y2, x1:x2] += wgt

            if on_progress:
                cont = on_progress((idx + 1) / total, f"tile {idx+1}/{total}")
                if cont is False:
                    raise RuntimeError("Cancelled")

    if on_progress:
        on_progress(1.0, "background complete")

    return np.divide(background, weight_sum, where=weight_sum > 0)