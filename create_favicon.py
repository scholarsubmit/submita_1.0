from PIL import Image
import os

# Open your logo
img = Image.open('static/images/logo.png')
# Resize to 32x32 for favicon
img = img.resize((32, 32), Image.Resampling.LANCZOS)
# Save as ICO
img.save('static/images/favicon.ico', format='ICO', sizes=[(32, 32)])
print("✅ Favicon created successfully!")