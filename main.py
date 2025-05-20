import math
import reedsolo
import time
from typing import Callable

# Constants for Version 1 and 2
VERSION_PARAMETERS = {
    1: {"size": 21, "data_codewords": 19, "ec_codewords": 7},
    2: {"size": 25, "data_codewords": 34, "ec_codewords": 10}
}

# Byte mode indicator
MODE_INDICATOR = '0100'

# Format strings for EC level L, mask patterns 0–7
FORMAT_STRINGS = [
    '111011111000100', '111001011110011', '111110110101010', '111100010011101',
    '110011000101111', '110001100011000', '110110001000001', '110100101110110'
]

FUNCTION_MODULES = set()


def to_bitstring(data: bytes) -> str:
    return ''.join(f'{b:08b}' for b in data)


def make_data_bitstream(text: str, version: int) -> str:
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
    ec_cw = VERSION_PARAMETERS[version]['ec_codewords']
    rs = reedsolo.RSCodec(ec_cw)
    full = rs.encode(bytes(data_cw))
    return list(full[-ec_cw:])


def initialize_matrix(size: int) -> list[list[int]]:
    return [[-1] * size for _ in range(size)]


def mark_function(r: int, c: int):
    FUNCTION_MODULES.add((r, c))


def place_finder_pattern(m, r, c):
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


def apply_patterns(m):
    size = len(m)
    for (r, c) in [(0, 0), (0, size-7), (size-7, 0)]:
        place_finder_pattern(m, r, c)

    sep_coords = [
        *( (i,7) for i in range(8) ), *( (7,i) for i in range(8) ),
        *( (i,size-8) for i in range(8) ), *( (7,size-1-i) for i in range(8) ),
        *( (size-8,i) for i in range(8) ), *( (size-1-i,7) for i in range(8) )
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


def place_format_info(m, mask_id):
    fmt = FORMAT_STRINGS[mask_id]
    size = len(m)
    pos1 = [*( (8, i) for i in range(0, 6) ), (8, 7), (8, 8), (7, 8), *( (i, 8) for i in range(5, -1, -1) )]
    pos2 = [*( (size - 1 - i, 8) for i in range(0, 7) ), *( (8, size - 1 - i) for i in range(0, 8) )]
    for idx, (r, c) in enumerate(pos1):
        m[r][c] = int(fmt[idx])
        mark_function(r, c)
    for idx, (r, c) in enumerate(pos2):
        m[r][c] = int(fmt[idx])
        mark_function(r, c)


def map_data(m, full_cw):
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


def score_penalty(m):
    size = len(m)
    score = 0

    # Rule 1
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

    # Rule 2
    for r in range(size - 1):
        for c in range(size - 1):
            if m[r][c] == m[r][c+1] == m[r+1][c] == m[r+1][c+1]:
                score += 3

    # Rule 3
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

    # Rule 4
    dark = sum(cell == 1 for row in m for cell in row)
    total = size * size
    k = abs(dark * 100 // total - 50) // 5
    score += k * 10
    return score


def print_matrix(m, delay=0.0, 
                 fg_char='██', bg_char='  ', 
                 fg_color='', bg_color='', 
                 reset_color='\033[0m', 
                 frame=False, scale=1):
    # Optional: apply ANSI color codes
    fg = f"{fg_color}{fg_char * scale}"
    bg = f"{bg_color}{bg_char * scale}"
    
    # Optional frame (top)
    if frame:
        width = len(m[0]) * scale + 2
        print('┌' + '─' * width + '┐')

    for row in m:
        line = ''.join(fg if v else bg for v in row for _ in range(scale))
        if frame:
            print('│' + line + '│')
        else:
            print(line)

    # Optional frame (bottom)
    if frame:
        print('└' + '─' * width + '┘')

    if delay:
        time.sleep(delay)

def main():
    # Get user input for the text (or URL) to encode
    text = input("Enter text to encode: ")
    # Ask user if they want to see step-by-step QR creation
    explain = input("Show step-by-step QR creation? (y/N): ").strip().lower() == 'y'

    # Choose QR version based on input length
    for version in [1, 2]:
        if len(text) <= VERSION_PARAMETERS[version]['data_codewords']:
            break
    else:
        print("Input too long for Version 2 QR Code")
        return
    customize = input("Custom display? (y/N): ").strip().lower() == 'y'
    if customize:
        scale = int(input("Module scale (1-3): ") or "1")
        frame = input("Add frame? (y/N): ").strip().lower() == 'y'
        fg_color = input("Foreground color ANSI code (e.g., \033[38;5;46m for green): ") or '\033[38;5;46m'
        bg_color = input("Background color ANSI code (e.g., \033[48;5;235m for dark gray): ") or '\033[0m'
    else:
        scale = 1
        frame = False
        fg_color = ''
        bg_color = ''


    print(f"Using Version {version} QR Code")
    # Convert input text to QR data bitstream
    bitstream = make_data_bitstream(text, version)
    if explain:
        print("\nStep 1: Data bitstream")
        print(bitstream)
        input("Press Enter to continue...")

    # Split bitstream into data codewords (bytes)
    data_cw = [int(bitstream[i:i+8], 2) for i in range(0, len(bitstream), 8)]
    if explain:
        print("\nStep 2: Data codewords (bytes)")
        print(data_cw)
        input("Press Enter to continue...")

    # Generate error correction codewords
    ec_cw = generate_error_correction(data_cw, version)
    if explain:
        print("\nStep 3: Error correction codewords")
        print(ec_cw)
        input("Press Enter to continue...")

    # Combine data and error correction codewords
    full_cw = data_cw + ec_cw
    if explain:
        print("\nStep 4: Combined data + error correction codewords")
        print(full_cw)
        input("Press Enter to continue...")

    # Get QR matrix size for the chosen version
    size = VERSION_PARAMETERS[version]['size']

    best_mask = 0
    lowest_score = float('inf')
    best_matrix = None

    # Try all 8 mask patterns and select the one with the lowest penalty score
    for mask_id in range(8):
        global FUNCTION_MODULES
        FUNCTION_MODULES = set()
        # Initialize empty QR matrix
        matrix = initialize_matrix(size)
        # Add finder, timing, and other function patterns
        apply_patterns(matrix)
        if explain and mask_id == 0:
            print("\nStep 5: Function patterns (finder, timing, etc.)")
            print_matrix(matrix)
            input("Press Enter to continue...")

        # Place format information (error correction level and mask id)
        place_format_info(matrix, mask_id)
        if explain and mask_id == 0:
            print("\nStep 6: Format information")
            print_matrix(matrix)
            input("Press Enter to continue...")

        # Map data and error correction codewords into the matrix
        map_data(matrix, full_cw)
        if explain and mask_id == 0:
            print("\nStep 7: Data mapping")
            print_matrix(matrix)
            input("Press Enter to continue...")

        # Apply the current mask pattern
        apply_mask(matrix, mask_id)
        if explain and mask_id == 0:
            print("\nStep 8: Mask pattern applied (mask 0 shown)")
            print_matrix(matrix)
            input("Press Enter to continue...")

        # Calculate penalty score for the masked matrix
        score = score_penalty(matrix)
        # Keep the mask with the lowest penalty score
        if score < lowest_score:
            best_mask = mask_id
            lowest_score = score
            best_matrix = [row[:] for row in matrix]

    # Output the best mask and print the resulting QR code matrix
    print(f"Best mask: {best_mask} (score {lowest_score})")
    print_matrix(
        best_matrix,
        fg_char='██', bg_char='  ',
        fg_color=fg_color,
        bg_color=bg_color,
        frame=frame,
        scale=scale
    )

    print_matrix(best_matrix)


if __name__ == '__main__':
    main()
