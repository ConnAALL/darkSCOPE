import argparse
import os
import time
from datetime import datetime

from mss import mss
from PIL import Image


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Capture X11 frames to PNGs.")
    p.add_argument("--display", default=os.environ.get("DISPLAY", ":99"))
    p.add_argument("--out", default=os.environ.get("CAPTURE_OUT", "/root/captures"))
    p.add_argument("--interval", type=float, default=float(os.environ.get("CAPTURE_INTERVAL", "3")))
    p.add_argument(
        "--count",
        type=int,
        default=int(os.environ.get("CAPTURE_COUNT", "0")),
        help="Number of frames to capture (0 = run forever).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    os.environ["DISPLAY"] = args.display
    output_dir = args.out
    os.makedirs(output_dir, exist_ok=True)

    print("Connecting to display:", os.environ["DISPLAY"])
    print("Output dir:", output_dir)

    with mss() as sct:
        monitor = sct.monitors[0]  # full virtual screen

        i = 0
        while True:
            i += 1
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"frame_{timestamp}.png")

            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            img.save(filename)

            print("Saved:", filename)

            if args.count > 0 and i >= args.count:
                break

            time.sleep(args.interval)


if __name__ == "__main__":
    main()
