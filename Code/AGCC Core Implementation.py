"""
Clean AGCC core implementation for the final submission.
This script contains the reproducible functions used in the project notebooks.
"""
import time
import numpy as np
import cv2
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def to_float_rgb(image):
    image = np.asarray(image).astype(np.float32)
    if image.max() > 1.0:
        image = image / 255.0
    return np.clip(image, 0.0, 1.0)


def rgb_statistics(image):
    image = to_float_rgb(image)
    r, g, b = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    return {
        "red_mean": float(np.mean(r)),
        "green_mean": float(np.mean(g)),
        "blue_mean": float(np.mean(b)),
        "red_std": float(np.std(r)),
        "green_std": float(np.std(g)),
        "blue_std": float(np.std(b)),
    }


def luminance_factor(image):
    stats = rgb_statistics(image)
    return 0.2126 * stats["red_mean"] + 0.7152 * stats["green_mean"] + 0.0722 * stats["blue_mean"]


def average_color_factor(image):
    stats = rgb_statistics(image)
    return (stats["red_mean"] + stats["green_mean"] + stats["blue_mean"]) / 3.0


def adaptive_gamma_value(image, gamma_control=2.0):
    L = luminance_factor(image)
    I_bar = average_color_factor(image)
    gamma = gamma_control + ((0.5 - L) * (1.0 - I_bar)) - (2.0 * L)
    return max(float(gamma), 0.1)


def adaptive_gamma_correction(image):
    image = to_float_rgb(image)
    gamma = adaptive_gamma_value(image)
    corrected = np.power(image, 1.0 / gamma)
    return np.clip(corrected, 0.0, 1.0), gamma


def color_correction_rgb_mean(image):
    image = to_float_rgb(image)
    means = image.reshape(-1, 3).mean(axis=0)
    max_mean = np.max(means)
    output = np.zeros_like(image)
    for channel in range(3):
        output[:, :, channel] = image[:, :, channel] + (max_mean - means[channel]) * image[:, :, channel]
    return np.clip(output, 0.0, 1.0)


def contrast_stretching(image, out_min=0.0, out_max=1.0):
    image = to_float_rgb(image)
    output = np.zeros_like(image)
    for channel in range(3):
        channel_data = image[:, :, channel]
        i_min, i_max = np.min(channel_data), np.max(channel_data)
        if i_max - i_min < 1e-8:
            output[:, :, channel] = channel_data
        else:
            output[:, :, channel] = ((channel_data - i_min) * (out_max - out_min) / (i_max - i_min)) + out_min
    return np.clip(output, 0.0, 1.0)


def original_agcc(image):
    start = time.time()
    step1, gamma = adaptive_gamma_correction(image)
    step2 = color_correction_rgb_mean(step1)
    step3 = contrast_stretching(step2)
    runtime = time.time() - start
    return {"step1_gamma": step1, "step2_color": step2, "final": step3, "gamma": gamma, "runtime": runtime}


def clahe_lab(image, clip_limit=2.0, tile_grid_size=(8, 8)):
    image_uint8 = (to_float_rgb(image) * 255).astype(np.uint8)
    lab = cv2.cvtColor(image_uint8, cv2.COLOR_RGB2LAB)
    L, A, B = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    L2 = clahe.apply(L)
    merged = cv2.merge((L2, A, B))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0


def bilateral_edge_preserving_filter(image, d=5, sigma_color=50, sigma_space=50):
    image_uint8 = (to_float_rgb(image) * 255).astype(np.uint8)
    filtered = cv2.bilateralFilter(image_uint8, d=d, sigmaColor=sigma_color, sigmaSpace=sigma_space)
    return filtered.astype(np.float32) / 255.0


def improved_hybrid_agcc(image):
    start = time.time()
    base = original_agcc(image)
    enhanced = clahe_lab(base["final"])
    enhanced = bilateral_edge_preserving_filter(enhanced)
    runtime = time.time() - start
    return {"final": np.clip(enhanced, 0.0, 1.0), "gamma": base["gamma"], "runtime": runtime}


def evaluate_with_reference(output, reference):
    output = to_float_rgb(output)
    reference = to_float_rgb(reference)
    psnr = peak_signal_noise_ratio(reference, output, data_range=1.0)
    ssim = structural_similarity(reference, output, channel_axis=2, data_range=1.0)
    return {"psnr": float(psnr), "ssim": float(ssim)}