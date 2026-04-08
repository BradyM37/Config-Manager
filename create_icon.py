"""
Create app icon for OptiLock Config Manager
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Create sizes needed for .ico
    sizes = [256, 128, 64, 48, 32, 16]
    images = []
    
    for size in sizes:
        # Create image with transparent background
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background circle with gradient effect (purple to cyan)
        padding = size // 10
        
        # Draw outer glow
        for i in range(3):
            offset = i * 2
            alpha = 80 - i * 25
            draw.ellipse(
                [padding - offset, padding - offset, size - padding + offset, size - padding + offset],
                fill=(139, 92, 246, alpha)  # Purple glow
            )
        
        # Main circle - dark background
        draw.ellipse(
            [padding, padding, size - padding, size - padding],
            fill=(18, 18, 26, 255)
        )
        
        # Inner border - gradient effect (purple)
        border_width = max(2, size // 32)
        draw.ellipse(
            [padding, padding, size - padding, size - padding],
            outline=(139, 92, 246, 255),
            width=border_width
        )
        
        # Lightning bolt in center
        center = size // 2
        bolt_size = size // 3
        
        # Lightning bolt points
        bolt_points = [
            (center + bolt_size * 0.1, center - bolt_size * 0.5),   # Top
            (center - bolt_size * 0.15, center - bolt_size * 0.05),  # Middle left
            (center + bolt_size * 0.05, center - bolt_size * 0.05),  # Middle center
            (center - bolt_size * 0.1, center + bolt_size * 0.5),    # Bottom
            (center + bolt_size * 0.15, center + bolt_size * 0.05),  # Middle right
            (center - bolt_size * 0.05, center + bolt_size * 0.05),  # Middle center
        ]
        
        # Draw lightning bolt with cyan/white gradient
        draw.polygon(bolt_points, fill=(6, 182, 212, 255))  # Cyan
        
        images.append(img)
    
    # Ensure assets directory exists
    os.makedirs('assets', exist_ok=True)
    
    # Save as ICO
    images[0].save(
        'assets/icon.ico',
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[1:]
    )
    
    print("Created assets/icon.ico")

if __name__ == "__main__":
    create_icon()
