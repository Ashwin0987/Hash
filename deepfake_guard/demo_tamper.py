import cv2
import numpy as np
from deepfake_guard.watermark import Watermarker
from deepfake_guard.utils import save_image

def run_tamper_demo():
    print("=== Tamper Localization Demo ===")
    
    wm = Watermarker(alpha=2, block_size=64)
    
    # 1. Create Image
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    img[:] = (100, 100, 100) # Gray background
    cv2.putText(img, "Original Content", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    save_image("demo_tamper_original.png", img)
    
    # 2. Protect
    print("Protecting...")
    # Short payload for block fitting
    identity = "UserA"
    protected = wm.embed(img, identity)
    save_image("demo_tamper_protected.png", protected)
    
    # 3. Attack (Paste a black box in the corner)
    print("Attacking (Pasting fake content)...")
    attacked = protected.copy()
    # Paste at 100,100 of size 128x128 (covering 4 blocks of 64x64)
    reversed_patch = 255 - attacked[100:228, 100:228] 
    attacked[100:228, 100:228] = reversed_patch # Invert colors to simulate fake
    
    save_image("demo_tamper_attacked.png", attacked)
    
    # 4. Detect
    print("Detecting Tampering...")
    tamper_map, extracted_id = wm.detect_tampering(attacked, target_identity=identity)
    
    print(f"Extracted Identity Consensus: {extracted_id}")
    save_image("demo_tamper_map.png", tamper_map)
    print("Tamper map saved to demo_tamper_map.png (White areas = Tampered)")

if __name__ == "__main__":
    run_tamper_demo()
