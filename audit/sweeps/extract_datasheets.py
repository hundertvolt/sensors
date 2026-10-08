"""Extract every datasheet PDF under datasheets/ to <outdir>/<chip dir>__<stem>.txt (read-only reference corpus).
Fails loudly when datasheets/ is an uninitialised submodule or holds no PDF; lists chips with no datasheet directory.
Run: uv run --with pypdf --with cryptography audit/sweeps/extract_datasheets.py <outdir>"""
import logging
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SHEETS = ROOT / "datasheets"
# Bus and service drivers drive no chip of their own; NeoPixel's chip is the WS2812.
NOT_CHIPS = {"i2c", "spi", "uart", "uart_link", "notification"}
ALIASES = {"neopixel": "ws2812"}


def chips_named():
    """Chip names the device TOMLs and driver file names refer to, lower-case."""
    names = {p.stem.removeprefix("asy_").removesuffix("_driver") for p in (ROOT / "src").glob("asy_*_driver.py")}
    for toml in (ROOT / "devices").glob("*.toml"):
        names |= set(re.findall(r'^\s*driver\s*=\s*"([a-z0-9_]+)"', toml.read_text(), re.M))
    return {ALIASES.get(n, n) for n in names - NOT_CHIPS}


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: extract_datasheets.py <outdir>")
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    out = Path(sys.argv[1])
    pdfs = sorted(SHEETS.rglob("*.pdf")) if SHEETS.is_dir() else []
    if not pdfs:
        print(f"{SHEETS.relative_to(ROOT)}/ holds no PDF: run `git submodule update --init datasheets` first", file=sys.stderr)
        sys.exit(1)
    out.mkdir(parents=True, exist_ok=True)
    for pdf in pdfs:
        chip = pdf.relative_to(SHEETS).parts[0]
        try:
            reader = PdfReader(str(pdf))
            if reader.is_encrypted:
                reader.decrypt("")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:  # noqa: BLE001 - any unreadable PDF is reported, the rest still extract
            print(f"unreadable: {pdf.relative_to(ROOT)}: {e}")
            continue
        (out / f"{chip}__{pdf.stem}.txt").write_text(text)
    dirs = {p.name.lower() for p in SHEETS.iterdir() if p.is_dir()}
    for chip in sorted(chips_named()):
        if not any(chip in d or d in chip for d in dirs):
            print(f"no datasheet directory: {chip}")
    print(f"extracted {len(pdfs)} PDF(s) to {out}")


if __name__ == "__main__":
    main()
