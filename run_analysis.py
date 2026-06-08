import argparse
from deepfake_guard.batch import BatchProcessor

def main():
    processor = BatchProcessor()
    
    # 1. Process Inputs -> Outputs (Register Originals)
    print("--- Phase 1: Processing Inputs (Registering Originals) ---")
    processor.process_and_register("inputs", "outputs", identity="SecureCam_01")
    
    # 2. Analyze Outputs (Self-Check - Should be Original)
    print("\n--- Phase 2: Analyzing Outputs (Self-Check) ---")
    processor.analyze_folder("outputs", "report_outputs.txt")
    
    # 3. Analyze Deepfakes (Tamper Check)
    print("\n--- Phase 3: Analyzing Deepfakes (Tamper Check) ---")
    processor.analyze_folder("deepfakes", "report_deepfakes.txt")

    # 4. Analyze User Check Folder
    print("\n--- Phase 4: Analyzing User Check Folder (deepfake_check) ---")
    processor.analyze_folder("deepfake_check", "report_deepfake_check.txt")

    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()
