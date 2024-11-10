import numpy as np
import logging
from math import log10, sqrt
from cmath import phase
from PIL import Image
from matplotlib import pyplot as plt
from scipy.signal import convolve2d


logging.basicConfig(
    filename="logger.log", level="INFO",
    format="%(asctime)s %(levelname)s Line: %(lineno)d %(message)s"
)

ALPHA = 1
CVZ = np.random.normal(0, 1, size=[256, 256])


def process_threshold(x):
    """
    Applies a threshold to the input value x.
    """
    result = 1 if x > 0.1 else 0
    logging.info(f"Applied threshold to {x}, result: {result}")
    return result


def calculate_psnr(original, compressed):
    """
    Calculates the Peak Signal-to-Noise Ratio between the original and compressed images.
    """
    mse = np.mean((original - compressed) ** 2)
    if mse == 0:
        logging.warning("MSE is zero. PSNR value is set to 100")
        return 100
    max_pixel = 255.0
    psnr_value = 20 * log10(max_pixel / sqrt(mse))
    logging.info(f"Calculated PSNR: {psnr_value}")
    return psnr_value


def calculate_psnr_alternative(c, cw):
    """
    Alternative method to calculate the PSNR.
    """
    psnr_value = 10 * np.log10(np.power(255, 2) /
                        np.mean(np.power((c - cw), 2)))
    logging.info(f"Calculated alternative PSNR: {psnr_value}")
    return psnr_value


def select_best_alpha(image):
    """
    Selects the best alpha value automatically by maximizing PSNR.
    """
    psnr = 0
    best_alpha = 0
    best_proximities = 0
    logging.info("Selecting best alpha")
    for alpha in range(1, 1001, 100):
        logging.info(f"Testing alpha: {alpha}")
        image_array = np.asarray(image)  # Convert the image to the frequency domain using FFT
        spectre_array = np.fft.fft2(image_array)
        get_phase = np.vectorize(phase)
        phase_array = get_phase(spectre_array)

        abs_spectrum = abs(spectre_array)
        original_abs_spectrum = abs(spectre_array)
        modified_abs_spectrum = abs_spectrum
        modified_abs_spectrum[128:384, 128:384] = (
                abs_spectrum[128:384, 128:384] + ALPHA * CVZ)
        modified_spectrum = (modified_abs_spectrum *
                           np.exp(phase_array * 1j))
        reverse_array = abs(np.fft.ifft2(modified_spectrum))
        reverse_image = Image.fromarray(reverse_array)
        reverse_image.convert("RGB").save("img_with_cvz.png")

        new_image = Image.open("img_with_cvz.png").convert("L")
        reverse_array = np.asarray(new_image)
        save_reverse_array = reverse_array
        reverse_array = save_reverse_array.copy()
        reverse_spectre_array = np.fft.fft2(reverse_array)
        reverse_abs_spectrum = abs(reverse_spectre_array /
                                np.exp(phase_array * 1j))  # Calculate the embedded CVZ noise in the modified spectrum
        included_cvz = (reverse_abs_spectrum[128:384, 128:384] -
                        original_abs_spectrum[128:384, 128:384]) / ALPHA
        flatten_cvz = CVZ.flatten()
        flatten_included_cvz = included_cvz.flatten()  # Compute the correlation between the original and embedded CVZ
        p = sum(flatten_cvz * flatten_included_cvz) / (
            ((sum(flatten_cvz ** 2)) ** (1 / 2)) *
            ((sum(flatten_included_cvz ** 2)) ** (1 / 2)))
        included_cvz_estimation = process_threshold(p)
        if included_cvz_estimation:
            reverse_array = np.asarray(reverse_array)
            new_psnr = calculate_psnr_alternative(image_array, reverse_array)
            if new_psnr > psnr:
                psnr = new_psnr
                best_alpha = alpha
                best_proximities = p
                logging.info(f"Found new best alpha: {best_alpha}, PSNR: {psnr}")
    return(best_alpha, psnr, best_proximities)


def generate_false_detection_vectors(count):
    """
    Generates a list of false detection vectors (CVZ) with the specified count.
    """
    false_detection_cvz = []
    for i in range(count):
        false_detection_cvz.append(np.random.normal(0, 1, size=[65536]))
    return false_detection_cvz


def calculate_proximity(first_cvz, second_cvz):
    """
    Calculates the proximity between two vectors.
    """
    proximity = sum(first_cvz * second_cvz) / (
            ((sum(first_cvz ** 2)) ** (1 / 2)) *
            ((sum(second_cvz ** 2)) ** (1 / 2)))
    return proximity


def detect_false_proximity(false_detection_cvz, cvz):
    """
    Detects the proximity of false CVZ vectors relative to the given CVZ vector.
    """
    false_detection_proximity_array = []
    for false_cvz in false_detection_cvz:
        false_detection_proximity_array.append(
            calculate_proximity(cvz, false_cvz)
        )
    logging.info(f"False detection proximities: {false_detection_proximity_array}")
    return false_detection_proximity_array


def rotate_and_calculate_proximity(rotation_angle):
    """
    Rotates the image by an angle and get the proximity
    """
    rotated_image = reverse_image.rotate(rotation_angle)
    rotated_image_array = np.asarray(rotated_image)
    spectre_array = np.fft.fft2(rotated_image_array)
    reverse_array = abs(np.fft.ifft2(spectre_array))
    reverse_spectre_array = np.fft.fft2(reverse_array)
    reverse_abs_spectrum = abs(reverse_spectre_array /
                              np.exp(phase_array * 1j))
    rotated_cvz = (reverse_abs_spectrum[128:384, 128:384] -
                   original_abs_spectrum[128:384, 128:384]) / ALPHA
    flatten_cvz = CVZ.flatten()
    flatten_rotated_cvz = rotated_cvz.flatten()
    p = sum(flatten_cvz * flatten_rotated_cvz) / (
                ((sum(flatten_cvz ** 2)) ** (1 / 2)) *
                ((sum(flatten_rotated_cvz ** 2)) ** (1 / 2)))
    logging.info(f"Proximity after rotation by {rotation_angle} degrees: {p}")
    return p


def apply_cut_and_calculate_proximity(replacement_proportion):
    """
    change the part of reversed image with part of original image and calculate proximity
    """
    reverse_array[
        0:int(replacement_proportion * len(reverse_array)),
        0:int(replacement_proportion * len(reverse_array))
    ] = image_array[
        0:int(replacement_proportion * len(image_array)):,
        0:int(replacement_proportion * len(image_array))
    ]
    reverse_spectre_array = np.fft.fft2(reverse_array)
    reverse_abs_spectrum = abs(reverse_spectre_array /
                              np.exp(phase_array * 1j))
    cut_cvz = (reverse_abs_spectrum[128:384, 128:384] -
               original_abs_spectrum[128:384, 128:384]) / ALPHA
    flatten_cvz = CVZ.flatten()
    flatten_cut_cvz = cut_cvz.flatten()
    p = sum(flatten_cvz * flatten_cut_cvz) / (
                ((sum(flatten_cvz ** 2)) ** (1 / 2)) *
                ((sum(flatten_cut_cvz ** 2)) ** (1 / 2)))
    logging.info(f"Proximity after applying cut with {replacement_proportion} proportion: {p}")
    return p


def smooth_and_calculate_proximity(m):
    """
    Applies smoothing with a window of given size and calculates proximity.
    """
    window = np.full((m, m), 1) / (m*m)
    smooth_array = convolve2d(
        reverse_image, window,
        boundary="symm", mode="same"
    )
    spectre_array = np.fft.fft2(smooth_array)
    reverse_array = abs(np.fft.ifft2(spectre_array))
    reverse_spectre_array = np.fft.fft2(reverse_array)
    reverse_abs_spectrum = abs(reverse_spectre_array /
                              np.exp(phase_array * 1j))
    rotated_cvz = (reverse_abs_spectrum[128:384, 128:384] -
                   original_abs_spectrum[128:384, 128:384]) / ALPHA
    flatten_cvz = CVZ.flatten()
    flatten_smoothed_cvz = rotated_cvz.flatten()
    p = sum(flatten_cvz * flatten_smoothed_cvz) / (
                ((sum(flatten_cvz ** 2)) ** (1 / 2)) *
                ((sum(flatten_smoothed_cvz ** 2)) ** (1 / 2)))
    logging.info(f"Proximity after smoothing with {m} window size: {p}")
    return p


def compress_jpeg_and_calculate_proximity(qf):
    """
    Compresses the image to JPEG with the specified quality factor and calculates proximity.
    """
    rgb_reverse_image = reverse_image.convert("RGB")
    rgb_reverse_image.save("JPEG_image.jpg", quality=qf)
    jpeg_image = Image.open("JPEG_image.jpg").convert("L")
    jpeg_array = np.asarray(jpeg_image)
    spectre_array = np.fft.fft2(jpeg_array)
    reverse_array = abs(np.fft.ifft2(spectre_array))
    reverse_spectre_array = np.fft.fft2(reverse_array)
    reverse_abs_spectrum = abs(reverse_spectre_array /
                              np.exp(phase_array * 1j))
    rotated_cvz = (reverse_abs_spectrum[128:384, 128:384] -
                   original_abs_spectrum[128:384, 128:384]) / ALPHA
    flatten_cvz = CVZ.flatten()
    flatten_jpeg_cvz = rotated_cvz.flatten()
    p = sum(flatten_cvz * flatten_jpeg_cvz) / (
                ((sum(flatten_cvz ** 2)) ** (1 / 2)) *
                ((sum(flatten_jpeg_cvz ** 2)) ** (1 / 2)))
    logging.info(f"Proximity after compress with {qf} quality factor: {p}")
    return p


flatten_CVZ = CVZ.flatten()
false_detection_cvz = generate_false_detection_vectors(100)
false_detection_proximity_array = (
    detect_false_proximity(false_detection_cvz, CVZ.flatten()))

x = np.arange(0, 100, 1)
y = false_detection_proximity_array
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(x, y, color="red")
plt.show()

logging.info("Loading image and converting to array")
image = Image.open("bridge.tif")
image_array = np.asarray(image)

logging.info("Transforming image to frequency domain")
spectre_array = np.fft.fft2(image_array)
get_phase = np.vectorize(phase)
phase_array = get_phase(spectre_array)
abs_spectrum = abs(spectre_array)
original_abs_spectrum = abs(spectre_array)

logging.info("Embedding CVZ into image")
modified_abs_spectrum = abs_spectrum
modified_abs_spectrum[128:384, 128:384] = (
        abs_spectrum[128:384, 128:384] + ALPHA*CVZ)
modified_spectrum = modified_abs_spectrum * np.exp(phase_array*1j)
reverse_array = abs(np.fft.ifft2(modified_spectrum))
reverse_image = Image.fromarray(reverse_array)
reverse_image.convert("RGB").save("img_with_cvz.png")

logging.info("Evaluating embedded CVZ")
new_image = Image.open("img_with_cvz.png").convert("L")
reverse_array = np.asarray(new_image)
save_reverse_array = reverse_array
reverse_array = save_reverse_array.copy()
reverse_spectre_array = np.fft.fft2(reverse_array)
reverse_abs_spectrum = abs(reverse_spectre_array /
                          np.exp(phase_array*1j))
included_cvz = (reverse_abs_spectrum[128:384, 128:384] -
                original_abs_spectrum[128:384, 128:384]) / ALPHA
flatten_cvz = CVZ.flatten()
flatten_included_cvz = included_cvz.flatten()
p = (sum(flatten_cvz*flatten_included_cvz) /
     (((sum(flatten_cvz**2))**(1/2)) *
      ((sum(flatten_included_cvz**2))**(1/2))))
included_cvz_estimation = process_threshold(p)
logging.info(f"Threshold p-value for included CVZ: {p}, inclusion estimation: {included_cvz_estimation}")
reverse_image = Image.fromarray(reverse_array)


# CUT
logging.info("Starting CUT analysis")
cut_param_array = np.arange(0.55, 1.45, 0.15)
cut_proximities = []
for cut_param in cut_param_array:
    proximity = apply_cut_and_calculate_proximity(cut_param)
    cut_proximities.append(proximity)
    logging.debug(f"CUT parameter: {cut_param}, proximity: {proximity}")


# ROTATION
logging.info("Starting ROTATION analysis")
rotation_param_array = np.arange(1, 90, 8.9)
rotation_proximities = []
for rotation_param in rotation_param_array:
    proximity = rotate_and_calculate_proximity(rotation_param)
    rotation_proximities.append(proximity)
    logging.debug(f"ROTATION parameter: {rotation_param}, proximity: {proximity}")


# SMOOTH
logging.info("Starting SMOOTH analysis")
smooth_param_array = np.arange(3, 15, 2)
smooth_proximities = []
for smooth_param in smooth_param_array:
    proximity = smooth_and_calculate_proximity(smooth_param)
    smooth_proximities.append(proximity)
    logging.debug(f"SMOOTH parameter: {smooth_param}, proximity: {proximity}")


# JPEG
logging.info("Starting JPEG compression analysis")
jpeg_param_array = np.arange(30, 91, 10)
jpeg_proximities = []
for jpeg_param in jpeg_param_array:
    proximity = compress_jpeg_and_calculate_proximity(int(jpeg_param))
    jpeg_proximities.append(proximity)
    logging.debug(f"JPEG quality parameter: {jpeg_param}, proximity: {proximity}")


# OUTPUT
logging.info("Construction CUT process graph")
x = cut_param_array
y = cut_proximities
plt.title("CUT")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(x, y, color="red")
plt.show()

logging.info("Construction ROTATION process graph")
x = rotation_param_array
y = rotation_proximities
plt.title("ROTATION")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(x, y, color="red")
plt.show()

logging.info("Construction SMOOTH process graph")
x = smooth_param_array
y = smooth_proximities
plt.title("SMOOTH")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(x, y, color="red")
plt.show()

logging.info("Construction JPEG process graph")
x = jpeg_param_array
y = jpeg_proximities
plt.title("JPEG")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(x, y, color="red")
plt.show()