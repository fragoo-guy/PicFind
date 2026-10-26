import subprocess
from pathlib import Path
from PIL import Image


def run(cmd):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def test_cli_encode_decode(tmp_path: Path):
    img = tmp_path / "cli_in.png"
    out = tmp_path / "cli_out.png"
    Image.new("RGB", (64, 64), color=(123, 222, 111)).save(img)

    # encode
    cmd = f"{Path('stego.py').as_posix()} encode --image {img} --message \"cli test\" --output {out}"
    code, outp, err = run(f"python {cmd}")
    assert code == 0

    # decode
    cmd2 = f"python stego.py decode --image {out}"
    code2, outp2, err2 = run(cmd2)
    assert code2 == 0
    assert 'cli test' in outp2
