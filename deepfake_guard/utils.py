import cv2
import numpy as np
import math

def read_image(path, color=True):
    """Reads an image from path."""
    flags = cv2.IMREAD_COLOR if color else cv2.IMREAD_GRAYSCALE
    img = cv2.imread(path, flags)
    if img is None:
        raise FileNotFoundError(f"Image not found at {path}")
    return img

def save_image(path, img):
    """Saves an image to path."""
    cv2.imwrite(path, img)

def calculate_psnr(img1, img2):
    """Calculates Peak Signal-to-Noise Ratio (PSNR) between two images."""
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return 100
    pixel_max = 255.0
    return 20 * math.log10(pixel_max / math.sqrt(mse))

def str_to_bits(s):
    """Converts a string to a list of bits."""
    result = []
    for char in s:
        bits = bin(ord(char))[2:]
        bits = '00000000'[len(bits):] + bits
        result.extend([int(b) for b in bits])
    return result

def bits_to_str(bits):
    """Converts a list of bits to a string."""
    chars = []
    for b in range(len(bits) // 8):
        byte = bits[b*8:(b+1)*8]
        chars.append(chr(int(''.join([str(bit) for bit in byte]), 2)))
    return ''.join(chars)

def text_to_binary(text):
    """Converts text string to binary string."""
    return ''.join(format(ord(char), '08b') for char in text)

def binary_to_text(binary):
    """Converts binary string to text."""
    # Split into 8-bit chunks
    bytes_list = [binary[i:i+8] for i in range(0, len(binary), 8)]
    # Filter out incomplete bytes if any
    bytes_list = [b for b in bytes_list if len(b) == 8]
    return ''.join(chr(int(byte, 2)) for byte in bytes_list)
