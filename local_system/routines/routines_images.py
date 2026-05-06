import datetime
import time
import os
import sys

# Ensure parent directory (local_system) is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.captures.images import capture_and_store_image


def run_image_loop():
    """
    Capture exactly `IMAGE_CAPTURE_FPM` images per minute.

    Schedules a capture every `60 / IMAGE_CAPTURE_FPM` seconds using
    a regular cadence to avoid drift. On failure, logs and proceeds
    to the next scheduled tick without exceeding the rate.
    """
    from config import system_config

    prev_fpm = None
    interval = None
    next_time = None  # monotonic clock timestamp for next capture

    while True:
        try:
            fpm = int(getattr(system_config, "IMAGE_CAPTURE_FPM", 10))
            enabled = bool(getattr(system_config, "ENABLE_IMAGE_CAPTURE", True))

            if not enabled or fpm <= 0:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{ts}] Image capture disabled or FPM<=0. Waiting...")
                time.sleep(5)
                prev_fpm = None
                interval = None
                next_time = None
                continue

            if fpm != prev_fpm or interval is None or next_time is None:
                interval = 60.0 / float(fpm)
                next_time = time.monotonic() + interval
                prev_fpm = fpm

            # Wait until scheduled time
            now_mono = time.monotonic()
            sleep_for = next_time - now_mono
            if sleep_for > 0:
                time.sleep(sleep_for)

            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            saved = capture_and_store_image()
            if saved:
                print(f"[{ts}] Saved image frame: {saved}")
            else:
                print(f"[{ts}] Image capture failed or device unavailable.")

            # Schedule next tick; keeps cadence even if capture took time
            next_time += interval

        except KeyboardInterrupt:
            print("Stopping image capture loop.")
            break
        except Exception as e:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] Error capturing image: {e}")
            # Avoid tight loop; resume on next scheduled tick
            time.sleep(1.0)


if __name__ == "__main__":
    run_image_loop()
