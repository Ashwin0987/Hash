import os
import cv2
import numpy as np
from deepfake_guard.watermark import Watermarker
from deepfake_guard.crypto import CryptoEngine
from deepfake_guard.utils import save_image, calculate_psnr

def create_sample_image(path):
    # Create a 512x512 image with some shapes
    img = np.zeros((512, 512, 3), dtype=np.uint8)
    # Gradient
    for i in range(512):
        img[i, :, 0] = i // 2
        img[:, i, 1] = i // 2
    
    cv2.circle(img, (256, 256), 100, (255, 255, 255), -1)
    cv2.rectangle(img, (50, 50), (150, 150), (0, 0, 255), -1)
    
    save_image(path, img)
    print(f"Created sample image at {path}")
    return img

def run_demo():
    print("=== Privacy-Preserving Deepfake Detection Demo ===")
    
    # Setup
    # Ensure directories exist
    for dir_path in ["inputs", "outputs", "deepfakes"]:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    sample_path = "inputs/original.png"
    protected_path = "outputs/protected.png"
    attacked_path = "deepfakes/attacked_compressed.jpg"
    
    # 1. Generate Image
    create_sample_image(sample_path)
    
    # 2. Crypto Setup
    print("\n[1] Generating Keys...")
    priv_bytes, pub_bytes = CryptoEngine.generate_keys()
    
    identity = "Official:NewsCorp_2024"
    print(f"Identity: {identity}")
    
    # Sign Identity
    sig = CryptoEngine.sign_message(priv_bytes, identity.encode('utf-8'))
    payload = f"{identity}||{sig.hex()}"
    print(f"Payload Size: {len(payload)} chars")
    
    # 3. Embedding
    print("\n[2] Embedding Watermark...")
    img = cv2.imread(sample_path)
    wm_engine = Watermarker(alpha=2)
    
    # Note: Payload might be long (Hex signature is 128 chars for Ed25519 - 64 bytes).
    # Plus Identity. Total ~150 chars.
    # 150 chars * 8 bits = 1200 bits.
    # Image 512x512. LH band is 256x256 = 65536 coeffs.
    # Capacity is plenty.
    
    watermarked_img = wm_engine.embed(img, payload)
    save_image(protected_path, watermarked_img)
    
    # Quality Check
    psnr = calculate_psnr(img, watermarked_img)
    print(f"Watermarking Complete.")
    print(f"PSNR: {psnr:.2f} dB (Should be > 35dB, ideally > 40dB)")
    
    # 4. Verification (Clean)
    print("\n[3] Verifying Clean Image...")
    extracted_text = wm_engine.extract(watermarked_img)
    # Check parts
    if "||" in extracted_text:
        parts = extracted_text.split("||")
        uid = parts[0]
        s_hex = parts[1]
        try:
            s_bytes = bytes.fromhex(s_hex)
            if CryptoEngine.verify_signature(pub_bytes, uid.encode('utf-8'), s_bytes):
                print("SUCCESS: Clean image verified authentic.")
            else:
                print("FAILURE: Clean image signature mismatch.")
        except:
             print("FAILURE: Hex decode error.")
    else:
        print("FAILURE: Payload structure lost.")
        
    # 5. Attack Simulation (JPEG Compression)
    print("\n[4] Simulating JPEG Attack (Quality=90)...")
    cv2.imwrite(attacked_path, watermarked_img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    
    print("Verifying Attacked Image...")
    attacked_img = cv2.imread(attacked_path)
    
    extracted_attacked = wm_engine.extract(attacked_img)
    print(f"Extracted Raw (First 50 chars): {extracted_attacked[:50]}...")
    
    if "||" in extracted_attacked:
        parts = extracted_attacked.split("||")
        uid = parts[0]
        s_hex = parts[1]
        try:
            # It's possible the signature hex got corrupted slightly?
            # QIM is fragile to JPEG.
            # DWT-SVD is usually robust, but my simple QIM implementation might need higher alpha for JPEG 90.
            # Let's see.
            
            s_bytes = bytes.fromhex(s_hex)
            if CryptoEngine.verify_signature(pub_bytes, uid.encode('utf-8'), s_bytes):
                print("SUCCESS: Attacked image verified authentic (Robustness verified).")
            else:
                print("PARTIAL SUCCESS: Payload extracted but signature invalid (Bit error).")
        except:
             print("FAILURE: Hex decode error in attacked image.")
    else:
        print("FAILURE: Watermark lost in compression.")

if __name__ == "__main__":
    run_demo()
