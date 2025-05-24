"""
V1_QR_Logic: Contains all Version 1 specific QR code logic.
"""

from Jack_32007852 import (
    VERSION_PARAMETERS, make_data_bitstream, generate_error_correction,
    initialise_matrix, apply_patterns, place_format_info, map_data,
    apply_mask, score_penalty, save_matrix_as_image, reset_function_modules
)
import io

def make_v1_data_bitstream(text: str) -> str:
    """
    Create data bitstream for Version 1 QR code.
    """
    return make_data_bitstream(text, 1)

def generate_v1_error_correction(data_cw: list[int]) -> list[int]:
    """
    Generate error correction codewords for Version 1 QR code.
    """
    return generate_error_correction(data_cw, 1)
