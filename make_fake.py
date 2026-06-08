import cv2
import os

def make_fake():
    folder = "deepfake_check"
    filename = "9b64f8640ee612c6c7d537ebf6a16037.png"
    path = os.path.join(folder, filename)
    
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    img = cv2.imread(path)
    # Tamper: Draw a black box (0,0,0) in the middle
    # Deepfake/Inpainting usually changes pixel values.
    # Box size: 100x100
    cv2.rectangle(img, (100, 100), (200, 200), (0, 0, 0), -1)
    
    # Save as new file
    out_name = "tampered_example.png"
    out_path = os.path.join(folder, out_name)
    cv2.imwrite(out_path, img)
    print(f"Created deepfake example: {out_path}")

if __name__ == "__main__":
    make_fake()
