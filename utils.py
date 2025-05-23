"""
Utility functions for QR code generation.

Includes color conversion and ANSI code mapping.
"""

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

def ansi_to_rgb(ansi_code):
    """
    Converts ANSI escape code, numeric value, or hex color string to an RGB tuple value.

    @param ansi_code: The ANSI code or hex color to convert
    @return: Tuple of (R, G, B) or None if conversion fails
    """
    if not ansi_code:
        return None
    if isinstance(ansi_code, str) and ansi_code.startswith("#") and len(ansi_code) == 7:
        try:
            return tuple(int(ansi_code[i:i+2], 16) for i in (1, 3, 5))
        except Exception:
            return None
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
    try:
        code = int(str(ansi_code).strip().replace('\033[', '').replace('m', ''))
        return ANSI_RGB_MAP.get(code)
    except Exception:
        return None
