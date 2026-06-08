import cv2
import os
from deepfake_guard.watermark import Watermarker
from deepfake_guard.utils import calculate_psnr

def test():
    img = cv2.imread("inputs/original.png")
    if img is None:
        print("No input image found")
        return

    identity = "TestUser"
    
    for alpha in [2]:
        print(f"\n--- Testing Alpha={alpha} ---")
        wm = Watermarker(alpha=alpha, block_size=64)
        
        # Embed
        protected = wm.embed(img, identity)
        
        # Check Invisibility
        psnr = calculate_psnr(img, protected)
        print(f"PSNR: {psnr:.2f} dB")
        
        # Check Detection (Clean)
        extracted = wm.extract(protected)
        print(f"Extracted: '{extracted}'")
        
        if identity in extracted:
            print("Status: DETECTED")
        else:
            print("Status: FAILED")

if __name__ == "__main__":
    test()
