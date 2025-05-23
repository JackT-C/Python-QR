"""
QR code logic module.

Contains all functions for QR matrix construction, patterns, masking, scoring, and image saving.
"""

import reedsolo
from utils import ansi_to_rgb
from PIL import Image, ImageDraw, ImageFont
import io

VERSION_PARAMETERS = {
    1: {"size": 21, "data_codewords": 19, "ec_codewords": 7},
    2: {"size": 25, "data_codewords": 34, "ec_codewords": 10}
}

MODE_INDICATOR = '0100'

FORMAT_STRINGS = [
    '111011111000100', '111001011110011', '111110110101010', '111100010011101',
    '110011000101111', '110001100011000', '110110001000001', '110100101110110'
]

FUNCTION_MODULES = set()

def reset_function_modules():
    """
    Reset the set of function module coordinates.

    Should be called before generating a new QR matrix.
    """
    global FUNCTION_MODULES
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

    if version >= 2:
        if size == 25:
            place_alignment_pattern(m, 18, 18)

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

    for r in range(size - 1):
        for c in range(size - 1):
            if m[r][c] == m[r][c+1] == m[r+1][c] == m[r+1][c+1]:
                score += 3

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

    dark = sum(cell == 1 for row in m for cell in row)
    total = size * size
    k = abs(dark * 100 // total - 50) // 5
    score += k * 10
    return score

def save_matrix_as_image(m, filename="qr_output.png", 
                        scale=10, fg_char='██', 
                        bg_char='  ', fg_colour='', 
                        bg_colour='', frame=False):
    """
    Save the QR code matrix as a PNG image using Pillow.

    @param m: QR code matrix to display
    @param filename: Name of the File or BytesIO object.
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
