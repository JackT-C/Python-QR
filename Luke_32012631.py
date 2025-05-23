"""
Main GUI entrypoint for the QR Code Generator application.

Handles user interface, input, and integrates with QR code logic.
"""

# Import relevant libraries
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from PIL import Image, ImageTk
import io

from Jack_32007852 import (
    VERSION_PARAMETERS, make_data_bitstream, generate_error_correction,
    initialise_matrix, apply_patterns, place_format_info, map_data,
    apply_mask, score_penalty, save_matrix_as_image
)

def gui_main():
    """
    Launch the main GUI for the QR Code Generator.

    Handles all user interactions, input validation, and displays the generated QR code.
    """
    def on_generate():
        """
        Callback for the 'Generate QR' button.

        Validates input, generates the QR code, applies customisations, and updates the GUI.
        """
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
        """
        Open a color picker dialog to select the foreground color.
        """
        color = colorchooser.askcolor(title="Choose foreground color")
        if color and color[1]:
            fg_colour_var.set(color[1])

    def pick_bg_color():
        """
        Open a color picker dialog to select the background color.
        """
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
    """
    Entry point for the application. Starts the GUI.
    """
    gui_main()