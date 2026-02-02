
import base64
import re
import os

html_path = "d:/anti/Blood-Villingili/manual/pdf_layout.html"
base_dir = "d:/anti/Blood-Villingili/manual"
output_path = "d:/anti/Blood-Villingili/manual/manual_printable.html"

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

def replace_image(match):
    img_rel_path = match.group(1)
    img_full_path = os.path.join(base_dir, img_rel_path.replace("/", os.sep))
    
    print(f"Embedding {img_full_path}...")
    
    try:
        with open(img_full_path, "rb") as img_f:
            encoded_string = base64.b64encode(img_f.read()).decode("utf-8")
            return f'src="data:image/png;base64,{encoded_string}"'
    except Exception as e:
        print(f"Error embedding {img_rel_path}: {e}")
        return match.group(0) # Return original if failed

# Regex to find src="images/..."
# Matches src="images/step1.png"
content_embedded = re.sub(r'src="(images/[^"]+)"', replace_image, content)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(content_embedded)

print(f"Successfully created {output_path}")
