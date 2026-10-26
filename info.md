# Steganography Tool — Project Specification

## 1. Overview

A tool that hides secret text messages inside image files using the **LSB (Least Significant Bit)** technique — the image looks completely normal to the human eye, but a hidden message can be extracted from it using the same tool.

**Goal:** Build a working CLI tool that can encode a message into an image and decode it back out, with an optional password-based encryption layer for real security (not just obscurity).

---

## 2. Tech Stack

- **Language:** Python 3
- **Core library:** `Pillow` (PIL) — for reading/writing image pixel data
- **Optional (encryption layer):** `cryptography` library (or `hashlib` for simpler password-based key derivation)
- **Interface:** CLI (command-line interface) — no UI needed for MVP
- **Image format:** PNG only (lossless). JPEG must NOT be used for output — its compression destroys hidden bits.

---

## 3. Build Order (do this in order, don't skip ahead)

1. Read/write raw pixel data from an image (confirm you understand the data structure)
2. Text ↔ binary conversion functions — build and test these standalone, with no image involved
3. Encode: hide a short test message in a test image
4. Decode: read that image back and confirm the message matches — this round-trip test is proof the core logic works
5. Add a stop marker so messages of any length work (not just a fixed size)
6. Add password-based encryption as a layer before hiding the message
7. Wrap everything in a clean CLI

Do not add encryption or CLI polish before the basic encode/decode round-trip works on a hardcoded test case. Get the core bit-manipulation logic correct and tested first.

---

## 4. Core Concept: LSB (Least Significant Bit) Encoding

Every pixel in an image has color values (Red, Green, Blue), each stored as an 8-bit number (0–255). The **last bit** of each value barely affects the visible color — changing it shifts the value by at most 1 (e.g., 200 → 201), which is invisible to the human eye.

The technique: convert your secret message to binary, then overwrite the last bit of each pixel's color value with one bit of your message, in sequence.

### Example
Hiding the letter `A` (binary: `01000001`) across 8 pixels' Red values:
```
Original Red values:  200, 53, 12, 240, 88, 199, 45, 6
Original last bits:     0,  1,  0,   0,  0,   1,  1, 0
Message bits:            0,  1,  0,   0,  0,   0,  0, 1
Modified Red values:  200, 53, 12, 240, 88, 198, 44, 7
```
Only 3 of the 8 values actually changed, and each by at most 1 — completely undetectable visually.

### Decoding
Read the last bit of each pixel's color value in the same order, reassemble into a binary string, then convert back to text.

---

## 5. Data Flow

### Encode
```
Input: image file (PNG) + secret message (+ optional password)
1. Open image, get raw pixel data
2. If password provided: encrypt the message first
3. Convert message (encrypted or plain) to a binary string
4. Append a stop marker to the end of the binary string (e.g., "1111111111111110")
5. Loop through pixels; for each, overwrite the last bit of a color channel
   with the next bit of the binary string
6. Save result as a NEW PNG file
Output: a normal-looking PNG containing the hidden message
```

### Decode
```
Input: image file (+ password, if encryption was used)
1. Open image, get raw pixel data
2. Loop through pixels, extract the last bit of each relevant color channel,
   building a binary string
3. Stop once the stop marker is found
4. Convert the binary string back to bytes/text
5. If a password was used: decrypt to get the original message
Output: the original secret message
```

---

## 6. Data Model / Function Signatures (suggested)

```
text_to_binary(text: str) -> str
binary_to_text(binary: str) -> str

encode_message(image_path: str, message: str, output_path: str, password: str = None) -> None
decode_message(image_path: str, password: str = None) -> str

encrypt_message(message: str, password: str) -> bytes   # stretch goal
decrypt_message(data: bytes, password: str) -> str       # stretch goal
```

---

## 7. CLI Workflow

### Commands to implement
```
encode --image <input.png> --message "<text>" --output <output.png> [--password <pw>]
decode --image <output.png> [--password <pw>]
```

### Example usage
```
python stego.py encode --image cat.png --message "meet at 5pm" --output secret_cat.png
python stego.py decode --image secret_cat.png
> meet at 5pm
```

With password:
```
python stego.py encode --image cat.png --message "meet at 5pm" --output secret_cat.png --password hunter2
python stego.py decode --image secret_cat.png --password hunter2
> meet at 5pm

python stego.py decode --image secret_cat.png --password wrongpass
> Error: could not decrypt message
```

---

## 8. MVP Feature Checklist

- [ ] Read and write raw pixel data from a PNG using Pillow
- [ ] Text-to-binary and binary-to-text conversion functions (tested standalone)
- [ ] Encode a short hardcoded message into a test image
- [ ] Decode that image and confirm the message matches (round-trip test)
- [ ] Stop marker implemented so variable-length messages work
- [ ] CLI with `encode` and `decode` commands and proper arguments
- [ ] Validate output is saved as PNG (reject/convert if user points to a JPEG)

## 9. Stretch Goals (after MVP works)

- [ ] Password-based encryption layer before hiding the message
- [ ] Support hiding small files (not just text) inside images
- [ ] Capacity check: warn the user if their message is too long for the given image's pixel count
- [ ] Support hiding data across multiple color channels (R, G, and B) instead of just one, to increase capacity
- [ ] Simple web or desktop UI wrapping the same core logic

---

## 10. Key Things to Get Right

- **Always output PNG, never JPEG.** JPEG's lossy compression will corrupt or destroy the hidden bits.
- **Capacity limit:** the number of bits you can hide is limited by the number of pixels available. A rough rule: 1 character = 8 bits, so you need at least 8 pixels (using 1 channel each) per character, plus room for the stop marker.
- **Stop marker must be a sequence unlikely to appear naturally** in your encoded message's binary, so decoding doesn't stop early.
- **Encrypt before hiding, not after** — if you add password protection, encrypt the message first, then convert the encrypted bytes to binary and hide those. This is the correct order used by real steganography tools.

---

## 11. Notes for the AI Assistant (VS Code / Copilot / Claude Code)

- Follow the build order in Section 3 strictly — do not build the CLI or encryption layer before the basic encode/decode round-trip (Section 7's core logic) is proven with a hardcoded test case.
- Keep `text_to_binary`, `binary_to_text`, `encode_message`, and `decode_message` as clearly separated, independently testable functions.
- Use Pillow's pixel access methods (e.g., `.load()` or `putpixel`/`getpixel`) rather than manual byte parsing of the image file format.
- Favor simple, readable code over premature optimization — this is a learning project, not a production system.
