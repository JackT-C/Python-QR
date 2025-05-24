"""
V1_QR_Matrix_Image: Handles mask selection, matrix generation, and image saving for Version 1.
"""

from Jack_32007852 import (
    VERSION_PARAMETERS, initialise_matrix, apply_patterns, place_format_info, map_data,
    apply_mask, score_penalty, save_matrix_as_image, reset_function_modules
)
import io

def generate_v1_matrix_and_image(full_cw, fg_char, bg_char, fg_colour, bg_colour, frame, scale=10):
    """
    Handles mask selection, matrix generation, and image saving for Version 1.
    Returns (best_matrix, best_mask, lowest_score, img_bytes)
    """
    version = 1
    size = VERSION_PARAMETERS[version]['size']
    best_mask = 0
    lowest_score = float('inf')
    best_matrix = None

    for mask_id in range(8):
        reset_function_modules()
        matrix = initialise_matrix(size)
        apply_patterns(matrix, version)
        place_format_info(matrix, mask_id)
        map_data(matrix, full_cw)
        apply_mask(matrix, mask_id)
        score = score_penalty(matrix)
        if score < lowest_score:
            best_mask = mask_id
            lowest_score = score
            best_matrix = [row[:] for row in matrix]

    img_bytes = io.BytesIO()
    save_matrix_as_image(
        best_matrix,
        filename=img_bytes,
        scale=scale,
        fg_char=fg_char,
        bg_char=bg_char,
        fg_colour=fg_colour,
        bg_colour=bg_colour,
        frame=frame
    )
    img_bytes.seek(0)
    return best_matrix, best_mask, lowest_score, img_bytes
