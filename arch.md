# Architecture Notes

## Goals
Build a small Python-based steganography tool that hides text in PNG images using LSB encoding.

## Proposed Structure
- `stego.py`: core encode/decode logic and CLI entrypoint
- `tests/test_stego.py`: round-trip and conversion tests
- `requirements.txt`: runtime and test dependencies

## Core Functions
- `text_to_binary(text: str) -> str`
- `binary_to_text(binary: str) -> str`
- `encode_message(image_path: str, message: str, output_path: str, password: str | None = None) -> None`
- `decode_message(image_path: str, password: str | None = None) -> str`

## Data Flow
1. Convert text to bytes and then to binary.
2. Append a stop marker.
3. Replace the least-significant bit of selected pixel channel values.
4. Re-read the bits from the modified image and reconstruct the message.

## Notes
- PNG is the only supported output format for the MVP.
- The implementation should stay readable and independent from the CLI layer.
