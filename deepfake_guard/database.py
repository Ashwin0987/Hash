import json
import os

class AssetDatabase:
    def __init__(self, db_path="database.json"):
        self.db_path = db_path
        self.data = self.load()

    def load(self):
        if not os.path.exists(self.db_path):
            return {}
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save(self):
        with open(self.db_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def register_asset(self, filename, signature_hex, content_hash_hex):
        """
        Registers an asset.
        Key: Signature (unique ID of the watermark payload)
        Value: { filename, content_hash }
        """
        # We assume signature_hex is the unique ID extracted from watermark
        # or we can use specific ID if we watermarked with "ID||Sig"
        
        # For this system, let's use the ID part of the payload as the key if possible,
        # or just store a list.
        # But for constant time lookup, we need a unique key.
        # The watermark payload is "Identity||Signature".
        # The Signature is unique to the Identity key + Content? 
        # Actually in our demo we signed just the Identity.
        # So "Identity||Sig" is constant for the user, not the image.
        
        # Correction: To detect deepfakes of specific images, we must bind the image content to the signature.
        # But we are doing invisible watermarking of the "source".
        # Our Logic:
        # 1. Image has watermark "UserX".
        # 2. Database says "UserX" only produced images with hashes [H1, H2, H3].
        # 3. New image has watermark "UserX" but hash H_new.
        # 4. H_new not in [H1, H2, H3] -> Deepfake / Tampered.
        
        # So we structure DB as:
        # { "IdentityString": { "hashes": [h1, h2, ...], "files": [f1, f2...] } }
        
        pass 
        # Wait, if I implement it above, I need to parse the identity from the watermark.
        
    def add_entry(self, identity, content_hash, filename):
        if identity not in self.data:
            self.data[identity] = []
        
        # Check if hash already exists to avoid dupes
        exists = False
        for entry in self.data[identity]:
            if entry["hash"] == content_hash:
                exists = True
                break
        
        if not exists:
            self.data[identity].append({
                "hash": content_hash,
                "filename": filename
            })
            self.save()

    def check_hash(self, identity, content_hash):
        """
        Returns True if hash exists for identity, False otherwise.
        """
        if identity not in self.data:
            return False
            
        for entry in self.data[identity]:
            if entry["hash"] == content_hash:
                return True
        return False
