# Import relevant libraries
import reedsolo
import time
from PIL import Image, ImageDraw, ImageFont, ImageTk
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import io

# Constants for Versions 1 and 2
VERSION_PARAMETERS = {
    # Version 1 has maximum size: 21x21
    1: {"size": 21, "data_codewords": 19, "ec_codewords": 7},

    # Version 2 has maximum size: 25x25
    2: {"size": 25, "data_codewords": 34, "ec_codewords": 10}
}

# Byte mode indicator
MODE_INDICATOR = '0100'

# Format strings for EC level L, mask patterns 0–7
FORMAT_STRINGS = [
    '111011111000100', '111001011110011', '111110110101010', '111100010011101',
    '110011000101111', '110001100011000', '110110001000001', '110100101110110'
]

# ASNI to RGB Conversion Map
ANSI_RGB_MAP = {
    30: (0, 0, 0),
    31: (128, 0, 0),
    32: (0, 128, 0),
    33: (128, 128, 0),
    34: (0, 0, 128),
    35: (128, 0, 128),
    36: (0, 128, 128),
    37: (192, 192, 192),
    90: (128, 128, 128),
    91: (255, 0, 0),
    92: (0, 255, 0),
    93: (255, 255, 0),
    94: (0, 0, 255),
    95: (255, 0, 255),
    96: (0, 255, 255),
    97: (255, 255, 255),
}

FUNCTION_MODULES = set()

def to_bitstring(data: bytes) -> str:
    """
    Convert a bytes object to a continuous bit string representation.
    
    @param data: Binary data to convert
    @return: String of binary digits representing the input data
    """
    return ''.join(f'{b:08b}' for b in data)

def make_data_bitstream(text: str, version: int) -> str:
    """
    Construct the complete data bitstream for QR encoding following ISO/IEC 18004 specifications.
    
    Includes mode indicator, length header, data payload, terminator, and padding bits.
    
    @param text: Input text to encode
    @param version: QR code version (1 or 2)
    @return: Formatted bitstring ready for error correction coding
    """
    data_len = len(text)
    count_indicator = f'{data_len:08b}'
    max_data_cw = VERSION_PARAMETERS[version]["data_codewords"]
    bitstream = MODE_INDICATOR + count_indicator + to_bitstring(text.encode('iso-8859-1'))
    # Terminator
    max_bits = max_data_cw * 8
    term = min(4, max_bits - len(bitstream))
    bitstream += '0' * term
    while len(bitstream) % 8:
        bitstream += '0'
    pads = ['11101100', '00010001']
    i = 0
    while len(bitstream) // 8 < max_data_cw:
        bitstream += pads[i % 2]
        i += 1
    return bitstream

def generate_error_correction(data_cw: list[int], version: int) -> list[int]:
    """
    Generate Reed-Solomon error correction codewords for the input data.
    
    @param data_cw: List of data codewords
    @param version: QR code version determining error correction capacity
    @return: List of error correction codewords
    """
    ec_cw = VERSION_PARAMETERS[version]['ec_codewords']
    rs = reedsolo.RSCodec(ec_cw)
    full = rs.encode(bytes(data_cw))
    return list(full[-ec_cw:])

def initialise_matrix(size: int) -> list[list[int]]:
    """
    Create an empty QR code matrix with all positions initialised to -1.
    
    @param size: Dimension of square matrix (size x size)
    @return: 2D list representing empty QR code grid
    """
    return [[-1] * size for _ in range(size)]

def mark_function(r: int, c: int):
    """
    Mark a matrix position as containing functional patterns that should not be modified.
    
    @param r: Row index
    @param c: Column index
    """
    FUNCTION_MODULES.add((r, c))

def place_finder_pattern(m, r, c):
    """
    Insert a 7x7 finder pattern at specified coordinates in the matrix.
    
    Finder patterns consist of concentric squares with centre alignment.
    
    @param m: QR code matrix
    @param r: Top-left row coordinate
    @param c: Top-left column coordinate
    """
    pat = [
        [1,1,1,1,1,1,1],
        [1,0,0,0,0,0,1],
        [1,0,1,1,1,0,1],
        [1,0,1,1,1,0,1],
        [1,0,1,1,1,0,1],
        [1,0,0,0,0,0,1],
        [1,1,1,1,1,1,1]
    ]
    for dr in range(7):
        for dc in range(7):
            m[r+dr][c+dc] = pat[dr][dc]
            mark_function(r+dr, c+dc)

def place_alignment_pattern(m, r, c):
    """
    Insert a 5x5 alignment pattern at specified coordinates in the matrix.
    
    Alignment patterns help scanners adjust for surface distortion.
    
    @param m: QR code matrix
    @param r: Centre row coordinate
    @param c: Centre column coordinate
    """
    pat = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 1, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1]
    ]
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            nr = r + dr
            nc = c + dc
            if 0 <= nr < len(m) and 0 <= nc < len(m):
                if (nr, nc) not in FUNCTION_MODULES:
                    m[nr][nc] = pat[dr + 2][dc + 2]
                    mark_function(nr, nc)

def apply_patterns(m, version):
    """
    Apply all functional patterns to the QR code matrix including:
    - Finder patterns
    - Separators
    - Timing patterns
    - Alignment patterns (version 2+)
    - Dark module
    
    @param m: QR code matrix
    @param version: QR code version number
    """
    size = len(m)
    for (r, c) in [(0, 0), (0, size-7), (size-7, 0)]:
        place_finder_pattern(m, r, c)

    sep_coords = [
        *((i,7) for i in range(8)), *((7,i) for i in range(8)),
        *((i,size-8) for i in range(8)), *((7,size-1-i) for i in range(8)),
        *((size-8,i) for i in range(8)), *((size-1-i,7) for i in range(8))
    ]
    for (r, c) in sep_coords:
        m[r][c] = 0
        mark_function(r, c)

    for i in range(8, size-8):
        for (r, c) in [(6, i), (i, 6)]:
            m[r][c] = i % 2
            mark_function(r, c)

    dm = (size-8, 8)
    m[dm[0]][dm[1]] = 1
    mark_function(*dm)

    # Add alignment patterns for version 2
    if version >= 2:
        # Version 2 has alignment pattern at (18, 18)
        if size == 25:
            place_alignment_pattern(m, 18, 18)

def ansi_to_rgb(ansi_code):
    """
    Converts ANSI escape code, numeric value, or hex color string to an RGB tuple value.

    @param ansi_code: The ANSI code or hex color to convert
    """
    if not ansi_code:
        return None
    # Handle hex color codes like "#ff0000"
    if isinstance(ansi_code, str) and ansi_code.startswith("#") and len(ansi_code) == 7:
        try:
            return tuple(int(ansi_code[i:i+2], 16) for i in (1, 3, 5))
        except Exception:
            return None
    # Handle named colors (basic support)
    named_colors = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128),
    }
    if isinstance(ansi_code, str) and ansi_code.lower() in named_colors:
        return named_colors[ansi_code.lower()]
    # Handle ANSI numeric codes
    try:
        code = int(str(ansi_code).strip().replace('\033[', '').replace('m', ''))
        return ANSI_RGB_MAP.get(code)
    except Exception:
        return None

def place_format_info(m, mask_id):
    """
    Encode format information in the matrix containing error correction level and mask pattern.
    
    @param m: QR code matrix
    @param mask_id: Numeric identifier for mask pattern (0-7)
    """
    fmt = FORMAT_STRINGS[mask_id]
    size = len(m)
    pos1 = [*((8, i) for i in range(0, 6)), (8, 7), (8, 8), (7, 8), *((i, 8) for i in range(5, -1, -1))]
    pos2 = [*((size - 1 - i, 8) for i in range(0, 7)), *((8, size - 1 - i) for i in range(0, 8))]
    for idx, (r, c) in enumerate(pos1):
        m[r][c] = int(fmt[idx])
        mark_function(r, c)
    for idx, (r, c) in enumerate(pos2):
        m[r][c] = int(fmt[idx])
        mark_function(r, c)

def map_data(m, full_cw):
    """
    Map data and error correction codewords into the matrix using zig-zag pattern.
    
    Skips functional module areas and maintains QR code structure requirements.
    
    @param m: QR code matrix
    @param full_cw: Combined data and error correction codewords
    """
    bits = ''.join(f'{cw:08b}' for cw in full_cw)
    bit_idx = 0
    up = True
    col = len(m) - 1
    while col > 0:
        if col == 6:
            col -= 1
            continue
        rows = range(len(m) - 1, -1, -1) if up else range(len(m))
        for r in rows:
            for c in (col, col - 1):
                if m[r][c] == -1:
                    if bit_idx < len(bits):
                        m[r][c] = int(bits[bit_idx])
                        bit_idx += 1
                    else:
                        m[r][c] = 0
        up = not up
        col -= 2

def apply_mask(m, mask_id):
    """
    Apply selected mask pattern to data areas of QR code to optimise scannability.
    
    @param m: QR code matrix
    @param mask_id: Numeric identifier for mask pattern (0-7)
    """
    size = len(m)
    def condition(r, c):
        if mask_id == 0: return (r + c) % 2 == 0
        if mask_id == 1: return r % 2 == 0
        if mask_id == 2: return c % 3 == 0
        if mask_id == 3: return (r + c) % 3 == 0
        if mask_id == 4: return (r // 2 + c // 3) % 2 == 0
        if mask_id == 5: return (r * c) % 2 + (r * c) % 3 == 0
        if mask_id == 6: return ((r * c) % 2 + (r * c) % 3) % 2 == 0
        if mask_id == 7: return ((r + c) % 2 + (r * c) % 3) % 2 == 0
    for r in range(size):
        for c in range(size):
            if (r, c) not in FUNCTION_MODULES and condition(r, c):
                m[r][c] ^= 1

def score_penalty(m) -> int:
    """
    Calculate penalty score for QR code matrix based on ISO/IEC 18004 evaluation criteria.
    
    Evaluation rules:
    1. Consecutive modules in row/column
    2. 2x2 blocks of same colour
    3. Finder-like patterns
    4. Dark/light module balance
    
    @param m: QR code matrix to evaluate
    @return: Calculated penalty score (lower is better)
    """
    size = len(m)
    score = 0

    # Rule 1: Consecutive modules
    for row in m:
        for i in range(size - 4):
            if row[i] == row[i+1] == row[i+2] == row[i+3] == row[i+4]:
                run_len = 5
                while i+run_len < size and row[i+run_len] == row[i]:
                    run_len += 1
                score += 3 + (run_len - 5)

    for c in range(size):
        for i in range(size - 4):
            if all(m[i+k][c] == m[i][c] for k in range(5)):
                run_len = 5
                while i+run_len < size and m[i+run_len][c] == m[i][c]:
                    run_len += 1
                score += 3 + (run_len - 5)

    # Rule 2: 2x2 blocks
    for r in range(size - 1):
        for c in range(size - 1):
            if m[r][c] == m[r][c+1] == m[r+1][c] == m[r+1][c+1]:
                score += 3

    # Rule 3: Finder patterns
    pattern1 = [1,0,1,1,1,0,1,0,0,0,0]
    pattern2 = [0,0,0,0,1,0,1,1,1,0,1]
    for row in m:
        for i in range(size - 10):
            if row[i:i+11] == pattern1 or row[i:i+11] == pattern2:
                score += 40

    for c in range(size):
        for i in range(size - 10):
            col = [m[i+k][c] for k in range(11)]
            if col == pattern1 or col == pattern2:
                score += 40

    # Rule 4: Colour balance
    dark = sum(cell == 1 for row in m for cell in row)
    total = size * size
    k = abs(dark * 100 // total - 50) // 5
    score += k * 10
    return score

def print_matrix(m, delay=0.0, 
                 fg_char='██', bg_char='  ', 
                 fg_colour='', bg_colour='', 
                 reset_colour='\033[0m', 
                 frame=False, scale=1, version=1):
    """
    Render QR code matrix to console with optional formatting.
    
    @param m: QR code matrix to display
    @param delay: Optional delay after printing
    @param fg_char: Foreground character(s)
    @param bg_char: Background character(s)
    @param fg_colour: ANSI foreground colour code
    @param bg_colour: ANSI background colour code
    @param reset_colour: ANSI reset code
    @param frame: Add border around the QR code
    @param scale: Module scaling factor (1-3)
    @param version: 21x21 or 25x25 QR code size
    """

    # Background and foreground colours.
    fg = f"{fg_colour}{fg_char * scale}"
    bg = f"{bg_colour}{bg_char * scale}"
    
    # Frame outline (Top).
    if frame:
        if version == 1:
            width = len(m[0]) * scale + 21
        else:
            width = len(m[0]) * scale + 25
        print('┌' + '─' * width + '┐')

    # Output the QR lines and append frame to start and end.
    for row in m:
        line = ''.join(fg if v else bg for v in row for _ in range(scale))
        for i in range(scale):
            if frame:
                print('│' + line + '│')
            else:
                print(line)

    # Frame outline (Bottom).
    if frame:
        print('└' + '─' * width + '┘')

    if delay:
        time.sleep(delay)

def save_matrix_as_image(m, filename="qr_output.png", 
                        scale=10, fg_char='██', 
                        bg_char='  ', fg_colour='', 
                        bg_colour='', frame=False):
    """
    Save the QR code matrix as a PNG image using Pillow.

    @param m: QR code matrix to display
    @param filename: Name of the File.
    @param scale: Size of the QR.
    @param fg_char: Foreground character(s)
    @param bg_char: Background character(s)
    @param fg_colour: ANSI foreground colour code
    @param bg_colour: ANSI background colour code
    @param frame: Add border around the QR code
    """
    size = len(m)

    is_rectangle = (fg_char == '██' and bg_char == '  ')

    fg_rgb = ansi_to_rgb(fg_colour) or (0, 0, 0)
    bg_rgb = ansi_to_rgb(bg_colour) or (255, 255, 255)

    frame_width = 10 if frame else 0
    image_size = (size * scale + 2 * frame_width, size * scale + 2 * frame_width)

    img = Image.new("RGB", image_size, bg_rgb)
    draw = ImageDraw.Draw(img)

    for r in range(size):
        for c in range(size):
            x = c * scale + frame_width
            y = r * scale + frame_width
            if is_rectangle:
                color = fg_rgb if m[r][c] else bg_rgb
                draw.rectangle([x, y, x + scale - 1, y + scale - 1], fill=color)
            else:
                char = fg_char if m[r][c] else bg_char
                color = fg_rgb if m[r][c] else bg_rgb
                draw.text((x, y), char, fill=color, font=ImageFont.load_default())

    if isinstance(filename, io.BytesIO):
        img.save(filename, format="PNG")
    else:
        img.save(filename)
    print(f"\nQR code saved as: {filename}!")

def gui_main():
    def on_generate():
        text = entry_text.get()
        if not text:
            messagebox.showwarning("Input required", "Please enter text to encode.")
            return

        # Get customisation options
        try:
            scale = int(scale_var.get())
            if scale < 1 or scale > 3:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid scale", "Scale must be 1, 2, or 3.")
            return

        frame = frame_var.get()
        fg_char = fg_char_var.get() or "██"
        bg_char = bg_char_var.get() or "  "
        fg_colour = fg_colour_var.get()
        bg_colour = bg_colour_var.get()
        explain = explain_var.get()

        # Choose version
        for version in [1, 2]:
            if len(text) <= VERSION_PARAMETERS[version]['data_codewords']:
                break
        else:
            messagebox.showerror("Too long", "The input is too long for Version 2 QR Code")
            return

        version_var.set(f"QR Version: {version}")

        # Step-by-step log
        step_log = []

        # Step 1
        bitstream = make_data_bitstream(text, version)
        if explain:
            step_log.append("Step 1: Data bitstream.\n" + bitstream)

        # Step 2
        data_cw = [int(bitstream[i:i+8], 2) for i in range(0, len(bitstream), 8)]
        if explain:
            step_log.append("Step 2: Data codewords (bytes).\n" + str(data_cw))

        # Step 3
        ec_cw = generate_error_correction(data_cw, version)
        if explain:
            step_log.append("Step 3: Error correction codewords.\n" + str(ec_cw))

        # Step 4
        full_cw = data_cw + ec_cw
        if explain:
            step_log.append("Step 4: Combined data + error correction codewords.\n" + str(full_cw))

        size = VERSION_PARAMETERS[version]['size']
        best_mask = 0
        lowest_score = float('inf')
        best_matrix = None

        for mask_id in range(8):
            global FUNCTION_MODULES
            FUNCTION_MODULES = set()
            matrix = initialise_matrix(size)
            apply_patterns(matrix, version)
            if explain and mask_id == 0:
                step_log.append("Step 5: Function patterns (finder, timing, etc).")
            place_format_info(matrix, mask_id)
            if explain and mask_id == 0:
                step_log.append("Step 6: Format information.")
            map_data(matrix, full_cw)
            if explain and mask_id == 0:
                step_log.append("Step 7: Data mapping.")
            apply_mask(matrix, mask_id)
            if explain and mask_id == 0:
                step_log.append("Step 8: Mask pattern applied (mask 0 shown).")
            score = score_penalty(matrix)
            if score < lowest_score:
                best_mask = mask_id
                lowest_score = score
                best_matrix = [row[:] for row in matrix]

        if explain:
            step_log.append(f"Best mask: {best_mask} (score {lowest_score})")

        # Save QR as image in memory
        img_bytes = io.BytesIO()
        save_matrix_as_image(
            best_matrix,
            filename=img_bytes,
            scale=10,
            fg_char=fg_char,
            bg_char=bg_char,
            fg_colour=fg_colour,
            bg_colour=bg_colour,
            frame=frame
        )
        img_bytes.seek(0)
        img = Image.open(img_bytes)
        img.thumbnail((300, 300))
        img_tk = ImageTk.PhotoImage(img)
        qr_label.config(image=img_tk)
        qr_label.image = img_tk

        # Show step log
        if explain:
            step_text.config(state="normal")
            step_text.delete(1.0, tk.END)
            step_text.insert(tk.END, "\n\n".join(step_log))
            step_text.config(state="disabled")
        else:
            step_text.config(state="normal")
            step_text.delete(1.0, tk.END)
            step_text.config(state="disabled")

    def pick_fg_color():
        color = colorchooser.askcolor(title="Choose foreground color")
        if color and color[1]:
            fg_colour_var.set(color[1])

    def pick_bg_color():
        color = colorchooser.askcolor(title="Choose background color")
        if color and color[1]:
            bg_colour_var.set(color[1])

    root = tk.Tk()
    root.title("QR Code Generator")

    mainframe = ttk.Frame(root, padding=10)
    mainframe.grid(row=0, column=0, sticky="nsew")

    # Input
    ttk.Label(mainframe, text="Text to encode:").grid(row=0, column=0, sticky="w")
    entry_text = ttk.Entry(mainframe, width=40)
    entry_text.grid(row=1, column=0, columnspan=3, sticky="ew", pady=2)
    entry_text.focus()

    # Customisation
    ttk.Label(mainframe, text="Scale (1-3):").grid(row=2, column=0, sticky="w")
    scale_var = tk.StringVar(value="1")
    ttk.Entry(mainframe, textvariable=scale_var, width=5).grid(row=2, column=1, sticky="w")

    frame_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(mainframe, text="Frame", variable=frame_var).grid(row=2, column=2, sticky="w")

    ttk.Label(mainframe, text="FG Char:").grid(row=3, column=0, sticky="w")
    fg_char_var = tk.StringVar(value="██")
    ttk.Entry(mainframe, textvariable=fg_char_var, width=5).grid(row=3, column=1, sticky="w")

    ttk.Label(mainframe, text="BG Char:").grid(row=3, column=2, sticky="w")
    bg_char_var = tk.StringVar(value="  ")
    ttk.Entry(mainframe, textvariable=bg_char_var, width=5).grid(row=3, column=3, sticky="w")

    fg_colour_var = tk.StringVar(value="")
    bg_colour_var = tk.StringVar(value="")
    ttk.Label(mainframe, text="FG Color:").grid(row=4, column=0, sticky="w")
    ttk.Entry(mainframe, textvariable=fg_colour_var, width=10).grid(row=4, column=1, sticky="w")
    ttk.Button(mainframe, text="Pick", command=pick_fg_color).grid(row=4, column=2, sticky="w")

    ttk.Label(mainframe, text="BG Color:").grid(row=5, column=0, sticky="w")
    ttk.Entry(mainframe, textvariable=bg_colour_var, width=10).grid(row=5, column=1, sticky="w")
    ttk.Button(mainframe, text="Pick", command=pick_bg_color).grid(row=5, column=2, sticky="w")

    explain_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(mainframe, text="Show step-by-step", variable=explain_var).grid(row=6, column=0, columnspan=2, sticky="w")

    ttk.Button(mainframe, text="Generate QR", command=on_generate).grid(row=7, column=0, columnspan=3, pady=5)

    # QR Image
    qr_label = ttk.Label(mainframe)
    qr_label.grid(row=8, column=0, columnspan=4, pady=10)

    # Version display
    version_var = tk.StringVar(value="")
    version_label = ttk.Label(mainframe, textvariable=version_var)
    version_label.grid(row=9, column=0, columnspan=4, pady=2)

    # Step-by-step output
    step_text = tk.Text(mainframe, width=60, height=15, state="disabled", wrap="word")
    step_text.grid(row=10, column=0, columnspan=4, pady=5)

    root.mainloop()

if __name__ == '__main__':
    gui_main()