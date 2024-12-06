import streamlit as st
from PIL import Image
import json
import io
import random
import numpy as np
import time

st.set_page_config(
    page_title="Pixel Shuffle",
    page_icon="🎲",
    layout="wide"
)

# Add custom CSS for animations
st.markdown("""
<style>
@keyframes shudder {
    0%, 100% { transform: translate(0, 0) rotate(0deg); }
    25% { transform: translate(2px, 2px) rotate(1deg); }
    50% { transform: translate(-2px, -2px) rotate(-1deg); }
    75% { transform: translate(2px, -2px) rotate(1deg); }
}

@keyframes pixelate-in {
    0% { transform: scale(0); opacity: 0; }
    50% { transform: scale(1.2); }
    100% { transform: scale(1); opacity: 1; }
}

.pixel-grid {
    display: grid;
    gap: 1px;
    background-color: black;
    padding: 1px;
    width: 500px;
    height: 500px;
    perspective: 1000px;
}

.pixel {
    width: 100%;
    height: 100%;
    transition: background-color 0.3s ease;
    transform-origin: center;
}

.pixel.colored {
    animation: shudder 0.15s linear infinite;
}

.pixel.initializing {
    animation: pixelate-in 0.2s linear forwards;
}
</style>
""", unsafe_allow_html=True)

def create_grid_html(pixels, grid_size, animation_state='ready'):
    html = f'<div class="pixel-grid" style="grid-template-columns: repeat({grid_size}, 1fr);">'
    
    # Create a 2D grid of pixels
    grid = [[None for _ in range(grid_size)] for _ in range(grid_size)]
    
    # Fill the grid with colors from pixels
    for coord, color in pixels.items():
        x, y = map(int, coord.split(','))
        if x < grid_size and y < grid_size:
            grid[y][x] = color
    
    # Generate HTML for each cell in the grid
    for y in range(grid_size):
        for x in range(grid_size):
            color = grid[y][x] or "rgb(41, 41, 41)"
            is_colored = color != "rgb(41, 41, 41)"
            classes = ['pixel']
            if is_colored:
                classes.append('colored')
            if animation_state == 'initializing':
                classes.append('initializing')
                
            delay = f"animation-delay: {random.random() * 0.2}s;" if animation_state == 'initializing' else ""
            html += f'<div class="{" ".join(classes)}" style="background-color: {color}; {delay}"></div>'
    
    html += '</div>'
    return html

def shuffle_pixels(pixel_data):
    """Randomly redistribute colored pixels across the grid"""
    # Get grid dimensions from metadata
    width = pixel_data['metadata']['width']
    height = pixel_data['metadata']['height']
    pixel_size = pixel_data['metadata']['pixel_size']
    grid_width = width // pixel_size
    grid_height = height // pixel_size
    
    # Get all non-black pixels with their original positions
    colored_pixels = []
    for coord, color in pixel_data['pixels'].items():
        x, y = map(int, coord.split(','))
        if color != "rgb(41, 41, 41)":
            colored_pixels.append((x, y, color))
    
    # Create all possible positions in the grid
    available_positions = []
    for y in range(grid_height):
        for x in range(grid_width):
            available_positions.append((x, y))
    
    random.shuffle(available_positions)
    
    # Create new shuffled data
    shuffled_data = {
        'metadata': pixel_data['metadata'].copy(),
        'pixels': {}
    }
    
    # Place each colored pixel at a random position
    for i, (_, _, color) in enumerate(colored_pixels):
        if i < len(available_positions):
            x, y = available_positions[i]
            coord = f"{x},{y}"
            shuffled_data['pixels'][coord] = color
    
    return shuffled_data

# Add the necessary functions from analyzer and processor
def analyze_pixel_art(image, pixel_size=25):
    """Analyze image and extract pixel data"""
    # Convert image to RGB if it isn't already
    image = image.convert('RGB')
    pixel_array = np.array(image)
    height, width = pixel_array.shape[:2]
    
    pixel_data = {
        'metadata': {
            'width': width,
            'height': height,
            'pixel_size': pixel_size
        },
        'pixels': {}
    }
    
    # Sample pixels at regular intervals
    for y in range(0, height, pixel_size):
        for x in range(0, width, pixel_size):
            # Get the color of the top-left pixel in each block
            color = tuple(map(int, pixel_array[y, x, :3]))
            # Only store non-black pixels
            if color != (41, 41, 41):
                coord_key = f"{x // pixel_size},{y // pixel_size}"
                pixel_data['pixels'][coord_key] = f"rgb{color}"
    
    return pixel_data

def reconstruct_pixel_art(pixel_data):
    """Simplified version of reconstruct_pixel_art"""
    metadata = pixel_data['metadata']
    pixel_size = metadata['pixel_size']
    width = metadata['width']
    height = metadata['height']
    
    new_img = Image.new('RGB', (width, height), color='black')
    pixels = new_img.load()
    
    for coord, color in pixel_data['pixels'].items():
        x, y = map(int, coord.split(','))
        # Convert color string to RGB tuple
        rgb = tuple(map(int, color.strip('rgb()').split(',')))
        
        # Fill the pixel block
        for py in range(pixel_size):
            for px in range(pixel_size):
                actual_x = (x * pixel_size) + px
                actual_y = (y * pixel_size) + py
                if actual_x < width and actual_y < height:
                    pixels[actual_x, actual_y] = rgb
    
    return new_img

def main():
    st.title("🎲 Pixel Shuffle")
    
    if 'animation_state' not in st.session_state:
        st.session_state.animation_state = 'initializing'
    if 'pixel_data_dict' not in st.session_state:
        st.session_state.pixel_data_dict = {}
    
    uploaded_files = st.file_uploader("Choose image files", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    
    if uploaded_files:
        selected_file = st.selectbox(
            "Select image to analyze",
            uploaded_files,
            format_func=lambda x: x.name
        )
        
        # Process the selected file
        if selected_file.name not in st.session_state.pixel_data_dict:
            image = Image.open(selected_file)
            pixel_data = analyze_pixel_art(image)
            st.session_state.pixel_data_dict[selected_file.name] = {
                'original_data': pixel_data,
                'current_data': None,  # Will be set after BUILD
                'image': image,
                'is_built': False  # Track if BUILD has been clicked
            }
        
        current_data = st.session_state.pixel_data_dict[selected_file.name]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Create a container for better alignment
            with st.container():
                # Add 2.5 lines of space using HTML
                st.markdown('<div style="height: 1.75em;"></div>', unsafe_allow_html=True)
                st.write("")
                st.write("")
                st.image(current_data['image'], caption="Original Image")
        
        with col2:
            # Create a row for buttons
            button_col1, button_col2 = st.columns(2)
            
            with button_col1:
                if st.button("🏗️ BUILD"):
                    st.session_state.animation_state = 'ready'
                    # Create pixelated version
                    built_image = reconstruct_pixel_art(current_data['original_data'])
                    current_data['current_image'] = built_image
                    current_data['current_data'] = current_data['original_data'].copy()
                    current_data['is_built'] = True
                    st.session_state.pixel_data_dict[selected_file.name] = current_data
                    st.rerun()  # Force refresh to show SHAKE button immediately
            
            with button_col2:
                # Show SHAKE button if image has been built
                if current_data.get('is_built'):
                    if st.button("🎲 SHAKE"):
                        shuffled_data = shuffle_pixels(current_data['current_data'])
                        current_data['current_data'] = shuffled_data
                        shuffled_image = reconstruct_pixel_art(shuffled_data)
                        current_data['current_image'] = shuffled_image
                        st.session_state.animation_state = 'shaking'
                        st.session_state.pixel_data_dict[selected_file.name] = current_data
                        st.rerun()
            
            # Show current state if exists
            if current_data.get('is_built'):
                # Display the built/shuffled image
                st.image(current_data['current_image'], caption="Pixelated Image")
                
                # Display the interactive grid
                grid_size = max(
                    current_data['current_data']['metadata']['width'] // current_data['current_data']['metadata']['pixel_size'],
                    current_data['current_data']['metadata']['height'] // current_data['current_data']['metadata']['pixel_size']
                )
                
                st.components.v1.html(
                    create_grid_html(
                        current_data['current_data']['pixels'], 
                        grid_size,
                        st.session_state.animation_state
                    ),
                    height=520
                )

if __name__ == "__main__":
    main()