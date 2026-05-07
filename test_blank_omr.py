import cv2
import numpy as np
from omr_processor import process_omr_image

# Create a blank white A4 image
width, height = int(595.27 * 3), int(841.89 * 3)
img = np.ones((height, width, 3), dtype=np.uint8) * 255

# Add 4 black markers at the corners
margin = int(15 * 2.83465 * 3)
marker_size = int(10 * 2.83465 * 3)
cv2.rectangle(img, (margin, margin), (margin + marker_size, margin + marker_size), (0, 0, 0), -1)
cv2.rectangle(img, (width - margin - marker_size, margin), (width - margin, margin + marker_size), (0, 0, 0), -1)
cv2.rectangle(img, (margin, height - margin - marker_size), (margin + marker_size, height - margin), (0, 0, 0), -1)
cv2.rectangle(img, (width - margin - marker_size, height - margin - marker_size), (width - margin, height - margin), (0, 0, 0), -1)

# Encode to bytes
_, img_bytes = cv2.imencode(".png", img)

# Process
results, _ = process_omr_image(img_bytes.tobytes(), 10, "A-E", {})

print(f"Student ID: '{results.get('student_id')}'")
print(f"Class ID: '{results.get('class_id')}'")
