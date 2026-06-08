import cv2
import numpy as np
import pywt
from .utils import text_to_binary, binary_to_text

class Watermarker:
    def __init__(self, alpha=25, block_size=64):
        self.alpha = alpha
        self.block_size = block_size

    def _embed_block(self, block_y, repeated_payload):
        """Helper to embed payload into a single block's Y channel."""
        h, w = block_y.shape
        if h != self.block_size or w != self.block_size:
            # Pad if edge block is smaller
            padded = np.pad(block_y, ((0, self.block_size - h), (0, self.block_size - w)), 'edge')
            target = padded
        else:
            target = block_y.astype(np.float32)

        coeffs = pywt.dwt2(target, 'haar')
        LL, (LH, HL, HH) = coeffs
        
        lh_flat = LH.flatten()
        step = self.alpha
        
        if len(repeated_payload) > len(lh_flat):
            # Truncate if too long for one block? Or assert.
            # Ideally block size should be enough.
            # 64x64 -> 32x32 LH = 1024 coeffs.
            # 100 bits * 5 reps = 500 bits. Safe.
            pass

        # Embed
        for i, val in enumerate(repeated_payload):
            if i >= len(lh_flat): break
            coeff = lh_flat[i]
            d = 2 * step
            if val == 0:
                 new_c = np.round(coeff / d) * d
            else:
                 new_c = np.round((coeff - step) / d) * d + step
            lh_flat[i] = new_c
            
        LH_new = lh_flat.reshape(LH.shape)
        coeffs_new = LL, (LH_new, HL, HH)
        watermarked_block = pywt.idwt2(coeffs_new, 'haar')
        
        # Crop back if padded
        if h != self.block_size or w != self.block_size:
            return watermarked_block[:h, :w]
        return watermarked_block

    def embed(self, image, payload_text):
        """
        Embeds a text payload into the image using Block-Based DWT (64x64).
        """
        binary_payload = text_to_binary(payload_text)
        binary_payload += '00000000' 
        
        repetitions = 9
        repeated_payload = []
        for bit in binary_payload:
            repeated_payload.extend([int(bit)] * repetitions)
            
        img_yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
        y, u, v = cv2.split(img_yuv)
        
        h, w = y.shape
        y_float = y.astype(np.float32)
        y_out = y_float.copy()
        
        # Iterate blocks
        bs = self.block_size
        for i in range(0, h, bs):
            for j in range(0, w, bs):
                # Extract block
                block_h = min(bs, h - i)
                block_w = min(bs, w - j)
                
                block = y_float[i:i+block_h, j:j+block_w]
                
                # Embed
                wm_block = self._embed_block(block, repeated_payload)
                
                y_out[i:i+block_h, j:j+block_w] = wm_block
                
        img_yuv_new = cv2.merge([y_out.astype(np.uint8), u, v])
        img_bgr_new = cv2.cvtColor(img_yuv_new, cv2.COLOR_YUV2BGR)
        
        return img_bgr_new

    def _extract_from_block(self, block_y):
        """Helper to extract bits from a single block."""
        h, w = block_y.shape
        if h != self.block_size or w != self.block_size:
            padded = np.pad(block_y, ((0, self.block_size - h), (0, self.block_size - w)), 'edge')
            target = padded
        else:
            target = block_y.astype(np.float32)
            
        coeffs = pywt.dwt2(target, 'haar')
        LL, (LH, HL, HH) = coeffs
        lh_flat = LH.flatten()
        step = self.alpha
        d = 2 * step
        
        bits = []
        for coeff in lh_flat:
            q0 = np.round(coeff / d) * d
            q1 = np.round((coeff - step) / d) * d + step
            dist0 = abs(coeff - q0)
            dist1 = abs(coeff - q1)
            if dist0 < dist1:
                bits.append(0)
            else:
                bits.append(1)
        return bits

    def extract(self, image):
        """
        Extracts by majority voting across all blocks.
        """
        img_yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
        y, u, v = cv2.split(img_yuv)
        h, w = y.shape
        
        bs = self.block_size
        all_block_bits = []
        
        for i in range(0, h, bs):
            for j in range(0, w, bs):
                block_h = min(bs, h - i)
                block_w = min(bs, w - j)
                block = y[i:i+block_h, j:j+block_w]
                
                # We skip very small edge blocks to avoid noise
                if block_h < bs/2 or block_w < bs/2:
                    continue
                    
                bits = self._extract_from_block(block)
                all_block_bits.append(bits)
                
        if not all_block_bits:
            return ""
            
        # Consensus Vote per bit index
        # We need to know max length. All blocks return fixed size (1024 bits for 32x32 band)
        # We'll just take the length of the first block
        max_len = len(all_block_bits[0])
        final_bits = []
        
        for bit_idx in range(max_len):
            ones = 0
            count = 0
            for block_bits in all_block_bits:
                if bit_idx < len(block_bits):
                    ones += block_bits[bit_idx]
                    count += 1
            if count == 0: break
            
            if ones > count / 2:
                final_bits.append(1)
            else:
                final_bits.append(0)
                
        # Decode Repetition Code (R=9)
        repetitions = 9
        decoded_text = ""
        current_byte_bits = ""
        
        # Same decoding logic as before
        for i in range(0, len(final_bits), repetitions):
            chunk = final_bits[i:i+repetitions]
            if len(chunk) < repetitions: break
            
            if sum(chunk) > repetitions/2:
                bit = '1'
            else:
                bit = '0'
            
            current_byte_bits += bit
            if len(current_byte_bits) == 8:
                if current_byte_bits == '00000000':
                    break
                try:
                    decoded_text += chr(int(current_byte_bits, 2))
                except:
                    pass
                current_byte_bits = ""
                
        return decoded_text

    def detect_tampering(self, image, target_identity=None):
        """
        Generates a heatmap of blocks that do NOT match the target identity (or consensus).
        Returns: (tamper_mask, extracted_identity)
        """
        img_yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
        y, u, v = cv2.split(img_yuv)
        h, w = y.shape
        bs = self.block_size
        
        # If target_identity is None, we first extract consensus
        if target_identity is None:
            consensus_text = self.extract(image)
            if "||" in consensus_text:
                target_identity = consensus_text.split("||")[0]
            else:
                # Fallback to consensus raw text if structure is broken
                target_identity = consensus_text 
        
        tamper_map = np.zeros((h, w), dtype=np.uint8)
        
        for i in range(0, h, bs):
            for j in range(0, w, bs):
                block_h = min(bs, h - i)
                block_w = min(bs, w - j)
                if block_h < bs or block_w < bs: continue # Skip edge blocks for simple map
                
                block = y[i:i+block_h, j:j+block_w]
                bits = self._extract_from_block(block)
                
                # Decode this block's text
                repetitions = 9
                decoded_text = ""
                current_byte_bits = ""
                
                for k in range(0, len(bits), repetitions):
                    chunk = bits[k:k+repetitions]
                    if len(chunk) < repetitions: break
                    if sum(chunk) > repetitions/2: bit = '1'
                    else: bit = '0'
                    current_byte_bits += bit
                    if len(current_byte_bits) == 8:
                        if current_byte_bits == '00000000': break
                        try:
                            decoded_text += chr(int(current_byte_bits, 2))
                        except: pass
                        current_byte_bits = ""
                
                # Check match
                # We check if target_identity is IN the decoded text 
                # (because sometimes there's trailing garbage or signature diffs)
                # Ideally exact match on Identity part.
                
                is_match = False
                if target_identity and target_identity in decoded_text:
                    is_match = True
                
                if not is_match:
                    # Mark as tampered (Red)
                    # We fill the block in the mask with 255
                    tamper_map[i:i+block_h, j:j+block_w] = 255
                    
        return tamper_map, target_identity
