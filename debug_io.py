import cv2
import os
import numpy as np
from deepfake_guard.watermark import Watermarker

def test_io():
    img_path = "inputs/original.png"
    if not os.path.exists(img_path):
        print("Input not found")
        return

    img = cv2.imread(img_path)
    identity = "SecureCam_01"
    
    alpha = 5
    wm = Watermarker(alpha=alpha, block_size=64)
    
    print(f"Embedding '{identity}' with alpha={alpha}...")
    protected = wm.embed(img, identity)
    
    # 1. Test In-Memory
    print("Testing In-Memory Extraction...")
    extracted_mem = wm.extract(protected)
    print(f"Memory Extracted: '{extracted_mem}'")
    
    # 2. Test Save/Load
    out_path = "debug_io_out.png"
    cv2.imwrite(out_path, protected)
    print(f"Saved to {out_path}. Loading back...")
    
    loaded = cv2.imread(out_path)
    if np.array_equal(protected, loaded):
        print("Pixels are IDENTICAL after load.")
    else:
        diff = np.abs(protected.astype(int) - loaded.astype(int))
        print(f"Pixels CHANGED! Max diff: {np.max(diff)}")
        
    extracted_disk = wm.extract(loaded)
    print(f"Disk Extracted: '{extracted_disk}'")
    
    if identity in extracted_disk:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    test_io()
