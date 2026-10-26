# PicFind — LSB Steganography CLI

Simple Python CLI tool to hide and recover text messages inside PNG images using LSB encoding.

Requirements

- Python 3.8+
- Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Quick usage

Encode a message:

```bash
python stego.py encode --image cat.png --message "meet at 5pm" --output secret_cat.png
```

Or read the message from a file:

```bash
python stego.py encode --image cat.png --message-file secret.txt --output secret_cat.png
```

Decode a message:

```bash
python stego.py decode --image secret_cat.png
```

Notes

- Output must be a PNG file.
- Encryption is a planned stretch goal and is not yet implemented.

New features

- Hide a binary file (stores original filename):

```bash
python stego.py encode --image cat.png --input-file payload.bin --output secret_cat.png
```

- Choose how many color channels to use (1-3) to trade capacity vs. subtlety:

```bash
python stego.py encode --image cat.png --message "secret" --output secret.png --channels 1
```

- Overwrite output file or ignore capacity checks with `--force`:

```bash
python stego.py encode --image cat.png --message-file msg.txt --output secret.png --force
```

- Show capacity information for an image:

```bash
python stego.py capacity --image cat.png --channels 3
```

- Decode a message and write binary payload to a file (defaults to `extracted.bin`):

```bash
python stego.py decode --image secret_cat.png --out-file recovered.bin
```

Notes on payload format

- The embedded payload begins with a small header: `type` (0=text,1=encrypted,2=binary) and `channels`.
- Binary payloads store the original filename length and name so decoding can restore it.

Installation (editable / local)

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

After installation you can run the tool as `picfind`:

```bash
picfind encode --image cat.png --message "hello" --output secret.png
```

Man page

If you install system manpages from `man/`, you can view the manual with:

```bash
man man/picfind.1
```
