"""
Main entrypoint for the QR Code Generator application.

Handles QR code generation logic and customisation options.
"""

# Import relevant libraries
import io

from Jack_32007852 import (
    VERSION_PARAMETERS, make_data_bitstream, generate_error_correction,
    initialise_matrix, apply_patterns, place_format_info, map_data,
    apply_mask, score_penalty, save_matrix_as_image
)

def generate_qr(text, scale, frame, fg_char, bg_char, fg_colour, bg_colour, explain):
    """
    Generate a QR code based on the input parameters.

    Args:
        text (str): The text to encode in the QR code.
        scale (int): The scale factor for the QR code (1-3).
        frame (bool): Whether to add a frame around the QR code.
        fg_char (str): The character for the foreground of the QR code.
        bg_char (str): The character for the background of the QR code.
        fg_colour (str): The foreground color in hex format.
        bg_colour (str): The background color in hex format.
        explain (bool): Whether to show step-by-step details.

    Returns:
        Image: The generated QR code as an image.
    """
    if not text:
        raise ValueError("Text to encode is required.")

    # Choose version
    for version in [1, 2]:
        if len(text) <= VERSION_PARAMETERS[version]['data_codewords']:
            break
    else:
        raise ValueError("The input is too long for Version 2 QR Code")

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
        from Jack_32007852 import reset_function_modules
        reset_function_modules()
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

    return img_bytes.getvalue(), step_log  # Return image bytes and step log for external use

# if __name__ == '__main__':
#     """
#     Entry point for the application. Starts the GUI.
#     """
#     gui_main()