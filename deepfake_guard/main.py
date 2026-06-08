import argparse
import sys
import os
import cv2
from .crypto import CryptoEngine
from .watermark import Watermarker
from .utils import read_image, save_image

def main():
    parser = argparse.ArgumentParser(description="Privacy-Preserving Deepfake Detection via Invisible Watermarking")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Command: Protect
    parser_protect = subparsers.add_parser("protect", help="Embed watermark and sign content")
    parser_protect.add_argument("--input", required=True, help="Path to input image")
    parser_protect.add_argument("--output", required=True, help="Path to output watermarked image")
    parser_protect.add_argument("--identity", required=True, help="Identity string to sign (e.g., 'User:Alice')")
    parser_protect.add_argument("--key-dir", default="keys", help="Directory to save/load keys")

    # Command: Verify
    parser_verify = subparsers.add_parser("verify", help="Verify watermark and signature")
    parser_verify.add_argument("--input", required=True, help="Path to image to verify")
    parser_verify.add_argument("--key-dir", default="keys", help="Directory to load public key from")

    args = parser.parse_args()

    if args.command == "protect":
        if not os.path.exists(args.key_dir):
            os.makedirs(args.key_dir)
            
        priv_path = os.path.join(args.key_dir, "private.key")
        pub_path = os.path.join(args.key_dir, "public.key")
        
        if os.path.exists(priv_path) and os.path.exists(pub_path):
            print("Loading existing keys...")
            with open(priv_path, "rb") as f:
                priv_bytes = f.read()
            # public key not strictly needed for signing but good to check
        else:
            print("Generating new keys (Ed25519)...")
            priv_bytes, pub_bytes = CryptoEngine.generate_keys()
            with open(priv_path, "wb") as f:
                f.write(priv_bytes)
            with open(pub_path, "wb") as f:
                f.write(pub_bytes)
                
        # 1. Prepare Payload
        # We sign the Identity. 
        # Payload = Identity + "||" + Signature(Identity)
        identity_bytes = args.identity.encode('utf-8')
        signature = CryptoEngine.sign_message(priv_bytes, identity_bytes)
        
        # We need to encode this into a string to pass to our Watermarker (which expects text/binary)
        # Ideally we embed raw bytes. Our watermarker splits string to bits.
        # Let's handle generic bytes. But `text_to_binary` in utils assumes text.
        # Let's hex encode the signature to make it safe text.
        
        sig_hex = signature.hex()
        payload = f"{args.identity}||{sig_hex}"
        
        print(f"Embedding Payload: {payload}")
        print(f"Payload Length: {len(payload)} chars")
        
        # 2. Embed
        img = read_image(args.input)
        engine = Watermarker(alpha=5)
        try:
            watermarked_img = engine.embed(img, payload)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
            
        save_image(args.output, watermarked_img)
        print(f"Protected image saved to {args.output}")

    elif args.command == "verify":
        pub_path = os.path.join(args.key_dir, "public.key")
        if not os.path.exists(pub_path):
            print("Error: Public key not found. Cannot verify.")
            sys.exit(1)
            
        with open(pub_path, "rb") as f:
            pub_bytes = f.read()
            
        img = read_image(args.input)
        engine = Watermarker()
        extracted_text = engine.extract(img)
        
        print(f"Extracted Raw Text: {extracted_text}")
        
        if "||" not in extracted_text:
            print("Verification Failed: Invalid format (No separator found).")
            # Usually means watermark destroyed or noise.
            print("Result: TAMPERED OR NO WATERMARK")
            sys.exit(1)
            
        parts = extracted_text.split("||")
        identity = parts[0]
        sig_hex = parts[1]
        # There might be garbage at the end if the null terminator wasn't perfect, 
        # but our extractor stops at null.
        
        try:
            signature = bytes.fromhex(sig_hex)
            identity_bytes = identity.encode('utf-8')
            
            valid = CryptoEngine.verify_signature(pub_bytes, identity_bytes, signature)
            
            if valid:
                print(f"Signature Verified: VALID")
                print(f"Provenace Identity: {identity}")
                print("Result: AUTHENTIC")
            else:
                print("Signature Verified: INVALID")
                print(f"Claimed Identity: {identity}")
                print("Result: TAMPERED")
        except Exception as e:
            print(f"Verification Error: {e}")
            print("Result: TAMPERED")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
