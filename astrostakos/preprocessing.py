import cv2
import numpy as np


def remove_hot_pixels(img, threshold_sigma=8.0):
    if img.ndim == 2:
        return _clean_channel(img, threshold_sigma)

    cleaned = img.copy()
    for c in range(3):
        cleaned[..., c] = _clean_channel(img[..., c], threshold_sigma)
    return cleaned


def _clean_channel(channel, sigma_thresh):
    median = cv2.medianBlur(channel, 3)
    diff = channel - median
    sigma = np.std(diff)
    mask = diff > (sigma_thresh * sigma)
    channel = channel.copy()
    channel[mask] = median[mask]
    return channel


def prepare_channels(img):
    is_color = img.ndim == 3

    if is_color:
        luminance = (
            0.2126 * img[..., 2] +
            0.7152 * img[..., 1] +
            0.0722 * img[..., 0]
        )
    else:
        img = img[..., None]
        luminance = img[..., 0]

    return img, luminance, is_color
