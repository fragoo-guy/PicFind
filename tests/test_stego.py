from pathlib import Path

from PIL import Image

from stego import binary_to_text, decode_message, encode_message, text_to_binary


def test_text_binary_round_trip():
    assert binary_to_text(text_to_binary("Hello")) == "Hello"


def test_encode_decode_round_trip(tmp_path: Path):
    image_path = tmp_path / "input.png"
    output_path = tmp_path / "secret.png"

    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(image_path)

    encode_message(str(image_path), "hello world", str(output_path))

    assert output_path.exists()
    assert decode_message(str(output_path)) == "hello world"


def test_encode_decode_with_password(tmp_path: Path):
    image_path = tmp_path / "input2.png"
    output_path = tmp_path / "secret2.png"

    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(image_path)

    encode_message(str(image_path), "top secret", str(output_path), password="hunter2")

    assert output_path.exists()
    assert decode_message(str(output_path), password="hunter2") == "top secret"


def test_decode_with_wrong_password_raises(tmp_path: Path):
    image_path = tmp_path / "input3.png"
    output_path = tmp_path / "secret3.png"

    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(image_path)

    encode_message(str(image_path), "sensitive", str(output_path), password="correcthorsebatterystaple")

    try:
        decode_message(str(output_path), password="wrongpass")
        assert False, "Decoding with wrong password should have raised"
    except ValueError:
        pass


def test_encode_decode_binary_file(tmp_path: Path):
    image_path = tmp_path / "input4.png"
    output_path = tmp_path / "secret4.png"
    bin_file = tmp_path / "payload.bin"

    data = b"\x00\x01\x02hellobinary"
    bin_file.write_bytes(data)

    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(image_path)

    encode_message(str(image_path), None, str(output_path), input_file=str(bin_file))

    assert output_path.exists()
    extracted = decode_message(str(output_path))
    assert isinstance(extracted, tuple)
    name, extracted_data = extracted
    assert name == "payload.bin"
    assert extracted_data == data


def test_capacity_check_raises(tmp_path: Path):
    image_path = tmp_path / "small.png"
    output_path = tmp_path / "out.png"
    Image.new("RGB", (2, 2), color=(255, 255, 255)).save(image_path)

    large_message = "A" * 1000
    try:
        encode_message(str(image_path), large_message, str(output_path), channels=1)
        assert False, "Expected capacity error"
    except ValueError:
        pass


def test_compression_round_trip(tmp_path: Path):
    image_path = tmp_path / "input5.png"
    output_path = tmp_path / "secret5.png"

    payload = "A" * 100
    Image.new("RGB", (64, 64), color=(255, 255, 255)).save(image_path)

    encode_message(str(image_path), payload, str(output_path), compress=True)
    assert decode_message(str(output_path)) == payload
