# QR Code Generator Application

## a) Application Description & Operation Instructions

This application provides a graphical interface for generating QR codes from user-supplied text. Users can customise the QR code's appearance (scale, frame, foreground/background characters and colours) and save the result as an image.

### How to Run

1. **Install dependencies**:
   - Python 3.x
   - Required packages: `reedsolo`, `Pillow`
   - Install with:
     ```sh
     pip install reedsolo pillow
     ```

2. **Start the application**:
   ```sh
   python main.py
   ```

3. **Usage**:
   - Enter the text to encode.
   - Adjust scale (1–3), frame, and character/colour options as desired.
   - Click "Generate QR" to view and save the QR code.
   - Optionally, enable "Show step-by-step" for detailed encoding steps.

### Application Structure

INSERT SS HERE OF DIRECTORY STURCTURE

- **main.py**: GUI, user input, and workflow control.
- **qr.py**: QR code construction, encoding, masking, and image saving.
- **utils.py**: Colour and ANSI code utilities.

---

## b) Programming Paradigms Used

- **Imperative**: Step-by-step QR matrix construction, data mapping, and image generation.
- **Functional**: Use of pure functions for bitstream creation, error correction, and matrix scoring.
- **Object-Oriented**: GUI components (Tkinter widgets), and use of PIL's `Image` and `ImageDraw` classes.

---

## c) Social, Legal, and Ethical Considerations

- **Accessibility**: Customisable colours and characters support users with visual needs.
- **Inclusivity**: Unicode and colour options allow for diverse representation.
- **Education**: Step-by-step explanations help users learn about QR encoding.
- **Transparency**: Step-by-step logs promote understanding.
- **Risk Mitigation**: Input validation and error handling reduce misuse.

---

## d) Known Weaknesses & Flaws

- Only supports QR Code Versions 1 and 2 (limited data capacity).
- No input sanitisation for binary or non-text payloads.
- Susceptible to misuse if used for encoding malicious links (user responsibility).
- No built-in accessibility for screen readers.

---

## e) Information Modelling, Input Management, and Data Integrity

- **Information Modelling**: QR matrix as a 2D list; codewords as lists of integers.
- **Input Management**: GUI restricts input length and validates options.
- **Data Integrity**: Error handling for invalid input, and step-by-step logs for transparency.

---

## f) Real-World Applications

- **Marketing**: Custom QR codes for campaigns.
- **Inventory**: Encode product IDs or URLs.
- **Science/Tracking**: Encode experiment or sample data.
- **Education**: Step-by-step mode for teaching QR code structure.

---

## g) Implementation Proofs (Example: "HELLO")

**Test String:** `HELLO`

**Step-by-step output (Version 1):**
```
SCREENSHOT OF GUI AND OUTPUT FOR V1
```
**Step-by-step output (Version 2):**
```
SCREENSHOT OF GUI AND OUTPUT FOR V2
```
## h) Demonstration

DEMO GIF

---
