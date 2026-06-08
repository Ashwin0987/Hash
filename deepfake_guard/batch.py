import os
import cv2
import glob
import hashlib
from .watermark import Watermarker
from .crypto import CryptoEngine
from .database import AssetDatabase
from .utils import save_image

class BatchProcessor:
    def __init__(self, key_dir="keys", db_path="database.json"):
        self.key_dir = key_dir
        self.db = AssetDatabase(db_path)
        
        if not os.path.exists(self.key_dir):
            os.makedirs(self.key_dir)
            
        self.priv_path = os.path.join(self.key_dir, "private.key")
        self.pub_path = os.path.join(self.key_dir, "public.key")
        
        # Load or Gen Keys
        if os.path.exists(self.priv_path):
             with open(self.priv_path, "rb") as f:
                self.priv_bytes = f.read()
        else:
             self.priv_bytes, pub_bytes = CryptoEngine.generate_keys()
             with open(self.priv_path, "wb") as f:
                f.write(self.priv_bytes)
             with open(self.pub_path, "wb") as f:
                f.write(pub_bytes)

    def compute_image_hash(self, img):
        """Computes SHA3-512 of the image pixel data."""
        # Ensure we are hashing the content consistently
        # Use raw bytes of the array
        return hashlib.sha3_512(img.tobytes()).hexdigest()

    def process_and_register(self, input_dir, output_dir, identity="BatchUser"):
        """
        1. Reads images from input_dir
        2. Watermarks them with Identity
        3. Saves to output_dir
        4. Computes Hash of WATERMARKED image
        5. Registers (Identity, Hash) to Database
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Prepare Payload
        # For block-based embedding (64x64), capacity is limited.
        # We only embed the Identity. The integrity is checked via Database Hash.
        payload = identity
        
        wm_engine = Watermarker(alpha=2) # Use robust alpha
        
        files = glob.glob(os.path.join(input_dir, "*"))
        processed_count = 0
        
        print(f"Propcessing {len(files)} files from {input_dir}...")
        
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp']:
                continue
                
            img = cv2.imread(file_path)
            if img is None:
                continue
                
            try:
                # Watermark
                protected_img = wm_engine.embed(img, payload)
                
                # Save
                filename = os.path.basename(file_path)
                out_path = os.path.join(output_dir, filename)
                # Save as PNG to avoid compression artifacts altering the hash immediately for the "original"
                out_path = os.path.splitext(out_path)[0] + ".png"
                
                save_image(out_path, protected_img)
                
                # Read back to ensure we hash exactly what is on disk? 
                # Or just hash the array. Array is safer for consistency if read identically.
                # However, file encoding might change bytes. 
                # Ideally, we hash the PIXELS of the saved image.
                # Let's save then read back to be 100% sure of 'what is verified'.
                
                saved_img = cv2.imread(out_path)
                img_hash = self.compute_image_hash(saved_img)
                
                # Register
                self.db.add_entry(identity, img_hash, filename)
                print(f"Registered: {filename} -> Hash: {img_hash[:16]}...")
                processed_count += 1
                
            except Exception as e:
                print(f"Failed to process {file_path}: {e}")
                
        print(f"Batch Processing Complete. {processed_count} images registered.")

    def analyze_folder(self, target_dir, report_file="analysis_report.txt"):
        """
        Scans folder, extracts watermark, checks DB, reports status.
        """
        files = glob.glob(os.path.join(target_dir, "*"))
        wm_engine = Watermarker(alpha=2)
        
        report_lines = []
        report_lines.append(f"Analysis Report for: {target_dir}")
        report_lines.append("="*50)
        report_lines.append(f"{'Filename':<30} | {'Status':<15} | {'Analysis':<30}")
        report_lines.append("-" * 80)
        
        original_count = 0
        deepfake_count = 0
        unknown_count = 0
        
        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp']:
                continue
                
            filename = os.path.basename(file_path)
            img = cv2.imread(file_path)
            if img is None:
                continue
                
            # 1. Calc Hash
            current_hash = self.compute_image_hash(img)
            
            # 2. Extract Watermark
            extracted_text = wm_engine.extract(img)
            
            status = "UNKNOWN"
            detail = "No Watermark Detected"
            
            # Helper to clean extracted text (remove null bytes etc if any)
            identity = extracted_text.strip()
            
            if identity:
                # Verify DB
                if self.db.check_hash(identity, current_hash):
                    status = "ORIGINAL"
                    detail = f"Match: {identity}"
                    original_count += 1
                else:
                    # Identity found, but hash mismatch
                    status = "DEEPFAKE"
                    detail = f"Tampered. ID: {identity}"
                    deepfake_count += 1
                    
                    # Generate Tamper Map
                    print(f"Generating Tamper Map for {filename}...")
                    t_map, _ = wm_engine.detect_tampering(img, target_identity=identity)
                    
                    # Save Map
                    map_name = f"{os.path.splitext(filename)[0]}_map.png"
                    map_path = os.path.join(target_dir, map_name)
                    cv2.imwrite(map_path, t_map)
                    detail += f" [Map: {map_name}]"
            else:
                 unknown_count += 1
                 
            report_lines.append(f"{filename:<30} | {status:<15} | {detail}")
            
        report_lines.append("="*50)
        report_lines.append(f"Summary: Original={original_count}, Deepfake={deepfake_count}, Unknown={unknown_count}")
        
        with open(report_file, "w") as f:
            f.write("\n".join(report_lines))
            
        print(f"Analysis Complete. Report saved to {report_file}")
        print(report_lines[-1])
