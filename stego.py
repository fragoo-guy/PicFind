from __future__ import annotations

import argparse
import sys
import base64
import os
from pathlib import Path
from typing import Optional

from PIL import Image
import zlib

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken

STOP_MARKER = "1111111111111110"

SALT_SIZE = 16
KDF_ITERATIONS = 390000


def text_to_binary(text: str) -> str:
    return "".join(format(ord(char), "08b") for char in text)


def bytes_to_binary(data: bytes) -> str:
    return "".join(format(byte, "08b") for byte in data)

def estimate_capacity_bits(width: int, height: int, channels: int) -> int:
    return width * height * channels


def binary_to_text(binary: str) -> str:
    if len(binary) % 8 != 0:
        raise ValueError("Binary length must be a multiple of 8")
    chars = [binary[i : i + 8] for i in range(0, len(binary), 8)]
    return "".join(chr(int(chunk, 2)) for chunk in chars)


def binary_to_bytes(binary: str) -> bytes:
    if len(binary) % 8 != 0:
        raise ValueError("Binary length must be a multiple of 8")
    chunks = [binary[i : i + 8] for i in range(0, len(binary), 8)]
    return bytes(int(chunk, 2) for chunk in chunks)


def _iter_pixel_channels(image: Image.Image):
    width, height = image.size
    for y in range(height):
        for x in range(width):
            pixel = image.getpixel((x, y))
            if isinstance(pixel, int):
                yield pixel
                continue
            for channel in pixel:
                yield channel


def _prepare_bits(message: str) -> str:
    return text_to_binary(message) + STOP_MARKER


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_message(message: str, password: str) -> bytes:
    salt = os.urandom(SALT_SIZE)
    key = _derive_key(password, salt)
    f = Fernet(key)
    token = f.encrypt(message.encode("utf-8"))
    return salt + token


def decrypt_message(data: bytes, password: str) -> str:
    if len(data) < SALT_SIZE:
        raise ValueError("Encrypted payload too short")
    salt = data[:SALT_SIZE]
    token = data[SALT_SIZE:]
    key = _derive_key(password, salt)
    f = Fernet(key)
    try:
        dec = f.decrypt(token)
    except InvalidToken:
        raise ValueError("Could not decrypt message with provided password")
    return dec.decode("utf-8")


def encode_message(image_path: str, message: Optional[str], output_path: str, password: Optional[str] = None, *, channels: int = 3, input_file: Optional[str] = None, force: bool = False, verbose: bool = False, compress: bool = False) -> None:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    if channels not in (1, 2, 3):
        raise ValueError("channels must be 1, 2, or 3")
    total_bits = estimate_capacity_bits(width, height, channels)

    # prepare content bytes
    if input_file:
        content = Path(input_file).read_bytes()
        fname = Path(input_file).name
        name_bytes = fname.encode("utf-8")
        name_len = len(name_bytes)
        if name_len > 65535:
            raise ValueError("Input filename too long")
        # store: [name_len (2 bytes)] [name_bytes] [content]
        content = name_len.to_bytes(2, "big") + name_bytes + content
        type_byte = 2
    else:
        if message is None:
            raise ValueError("No message or input file provided")
        content = message.encode("utf-8")
        type_byte = 0

    if password and type_byte == 0:
        type_byte = 1
        enc = encrypt_message(content.decode("utf-8"), password)
        content = enc

    flags = 0
    if compress:
        content = zlib.compress(content)
        flags |= 1

    payload_bytes = bytes([type_byte, channels, flags]) + content
    payload_bits = bytes_to_binary(payload_bytes) + STOP_MARKER

    if len(payload_bits) > total_bits and not force:
        raise ValueError(f"Message requires {len(payload_bits)} bits but only {total_bits} available; use --channels or --force to override")

    image_data = image.load()
    index = 0
    for y in range(height):
        for x in range(width):
            pixel = list(image_data[x, y])
            for channel_index in range(channels):
                if index >= len(payload_bits):
                    break
                bit = int(payload_bits[index])
                pixel[channel_index] = (pixel[channel_index] & 0xFE) | bit
                index += 1
                if verbose and len(payload_bits) > 0:
                    step = max(1, len(payload_bits) // 100)
                    if index % step == 0:
                        pct = (index * 100) // len(payload_bits)
                        print(f"Encoding... {pct}%")
            image_data[x, y] = tuple(pixel)
            if index >= len(payload_bits):
                break
        if index >= len(payload_bits):
            break

    output = Path(output_path)
    if output.suffix.lower() != ".png":
        raise ValueError("Output must be a PNG file")
    if output.exists() and not force:
        raise FileExistsError(f"Output file exists: {output}; pass force=True to overwrite")
    image.save(output)


def decode_message(image_path: str, password: Optional[str] = None) -> str:
    image = Image.open(image_path).convert("RGB")
    bits = []
    for y in range(image.height):
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            for channel in pixel:
                bits.append(str(channel & 1))
                if "".join(bits[-len(STOP_MARKER):]) == STOP_MARKER:
                    binary = "".join(bits[: len(bits) - len(STOP_MARKER)])
                    payload_bytes = binary_to_bytes(binary)
                    if not payload_bytes:
                        return ""
                    header = payload_bytes[0]
                    used_channels = payload_bytes[1]
                    # flags may be present at index 2
                    if len(payload_bytes) >= 3:
                        flags = payload_bytes[2]
                        content = payload_bytes[3:]
                    else:
                        flags = 0
                        content = payload_bytes[2:]
                    if flags & 1:
                        try:
                            content = zlib.decompress(content)
                        except Exception:
                            raise ValueError("Failed to decompress payload")
                    if header == 1:
                        if not password:
                            raise ValueError("Password required to decrypt this message")
                        return decrypt_message(content, password)
                    elif header == 2:
                        # content: [name_len(2)] [name_bytes] [data]
                        if len(content) >= 2:
                            name_len = int.from_bytes(content[:2], "big")
                            if len(content) >= 2 + name_len:
                                name = content[2 : 2 + name_len].decode("utf-8")
                                data = content[2 + name_len :]
                                return (name, data)
                        return (None, content)
                    else:
                        return content.decode("utf-8")
    raise ValueError("Stop marker not found")


def inspect_image(image_path: str) -> dict:
    """Return metadata about embedded payload without writing content."""
    image = Image.open(image_path).convert("RGB")
    bits = []
    for y in range(image.height):
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            for channel in pixel:
                bits.append(str(channel & 1))
                if "".join(bits[-len(STOP_MARKER):]) == STOP_MARKER:
                    binary = "".join(bits[: len(bits) - len(STOP_MARKER)])
                    payload_bytes = binary_to_bytes(binary)
                    if not payload_bytes:
                        return {}
                    header = payload_bytes[0]
                    used_channels = payload_bytes[1] if len(payload_bytes) > 1 else None
                    flags = payload_bytes[2] if len(payload_bytes) > 2 else 0
                    compressed = bool(flags & 1)
                    info = {"type": header, "channels": used_channels, "compressed": compressed}
                    if header == 2:
                        # binary: try to read name
                        content = payload_bytes[3:] if len(payload_bytes) > 3 else b""
                        if compressed:
                            try:
                                content = zlib.decompress(content)
                            except Exception:
                                content = b""
                        if len(content) >= 2:
                            name_len = int.from_bytes(content[:2], "big")
                            if len(content) >= 2 + name_len:
                                name = content[2 : 2 + name_len].decode("utf-8")
                                info["filename"] = name
                                info["size"] = len(content) - 2 - name_len
                    return info
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Hide and reveal text in PNG images")
    subparsers = parser.add_subparsers(dest="command", required=True)

    encode_parser = subparsers.add_parser("encode", help="Hide a message in an image")
    encode_parser.add_argument("--image", required=True)
    encode_parser.add_argument("--message", required=False, help="Message text to hide")
    encode_parser.add_argument("--message-file", required=False, help="Path to a text file containing the message to hide")
    encode_parser.add_argument("--input-file", required=False, help="Path to a binary file to hide instead of text")
    encode_parser.add_argument("--channels", type=int, choices=[1, 2, 3], default=3, help="How many color channels per pixel to use (1-3)")
    encode_parser.add_argument("--force", action="store_true", help="Overwrite output or ignore capacity checks")
    encode_parser.add_argument("--verbose", action="store_true", help="Verbose output")
    encode_parser.add_argument("--compress", action="store_true", help="Compress payload before embedding")
    encode_parser.add_argument("--output", required=True)
    encode_parser.add_argument("--password")

    decode_parser = subparsers.add_parser("decode", help="Recover a hidden message")
    decode_parser.add_argument("--image", required=True)
    decode_parser.add_argument("--password")
    decode_parser.add_argument("--out-file", required=False, help="When payload is binary, write to this file")
    capacity_parser = subparsers.add_parser("capacity", help="Show capacity information for an image")
    capacity_parser.add_argument("--image", required=True)
    capacity_parser.add_argument("--channels", type=int, choices=[1, 2, 3], default=3)
    show_parser = subparsers.add_parser("show", help="Inspect embedded payload metadata without extracting")
    show_parser.add_argument("--image", required=True)

    args = parser.parse_args()

    try:
        if args.command == "encode":
            if not args.message and not args.message_file and not args.input_file:
                raise ValueError("Either --message, --message-file, or --input-file must be provided")
            message = None
            if args.message_file:
                msg_path = Path(args.message_file)
                if not msg_path.exists():
                    raise FileNotFoundError(f"Message file not found: {args.message_file}")
                message = msg_path.read_text(encoding="utf-8")
            elif args.message:
                message = args.message
            encode_message(args.image, message, args.output, args.password, channels=args.channels, input_file=args.input_file, force=args.force, verbose=args.verbose)
            print(f"Message encoded into {args.output}")
        elif args.command == "decode":
            result = decode_message(args.image, args.password)
            if isinstance(result, bytes):
                out = args.out_file or "extracted.bin"
                Path(out).write_bytes(result)
                print(f"Binary payload written to {out}")
            else:
                print(result)
        elif args.command == "capacity":
            img = Image.open(args.image).convert("RGB")
            w, h = img.size
            total_bits = estimate_capacity_bits(w, h, args.channels)
            usable_bits = total_bits - len(STOP_MARKER)
            usable_bytes = usable_bits // 8
            header_overhead = 2
            max_payload_bytes = max(0, usable_bytes - header_overhead)
            print(f"Image: {args.image} size={w}x{h} channels={args.channels}")
            print(f"Total bits: {total_bits}, usable bytes: {usable_bytes}")
            print(f"Max payload bytes (excluding 2-byte header): {max_payload_bytes}")
        elif args.command == "show":
            info = inspect_image(args.image)
            if not info:
                print("No embedded payload found")
            else:
                for k, v in info.items():
                    print(f"{k}: {v}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
