"""Entrypoint: render the 21 November 2026 front page to entry.png.

Standard library only. No network. Deterministic output.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from render import build_page


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(out_dir, exist_ok=True)
    data = build_page()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("render did not produce a PNG")
    if len(data) > 1048576:
        raise SystemExit("entry.png exceeds 1 MiB: %d bytes" % len(data))
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
