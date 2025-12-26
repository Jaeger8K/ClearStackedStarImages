import numpy as np


def create_blend_weights(h, w, overlap):
    """
    Create smooth cosine-based blend weights for tile edges.
    Matches original AstroStakos behavior exactly.
    """
    weights = np.ones((h, w), dtype=np.float32)

    if overlap <= 0:
        return weights

    overlap_h = min(overlap, h // 2)
    overlap_w = min(overlap, w // 2)

    for i in range(overlap_h):
        alpha = 0.5 * (1 - np.cos(np.pi * i / overlap_h))
        weights[i, :] *= alpha
        weights[-(i + 1), :] *= alpha

    for i in range(overlap_w):
        alpha = 0.5 * (1 - np.cos(np.pi * i / overlap_w))
        weights[:, i] *= alpha
        weights[:, -(i + 1)] *= alpha

    return weights
