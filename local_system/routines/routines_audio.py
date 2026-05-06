import datetime
import time
import os
import sys

# Ensure parent directory (local_system) is on the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.captures.audios import capture_and_store_audio


def run_audio_loop():
    """
    Continuously capture audio chunks back-to-back.

    Uses configuration via `capture_and_store_audio()`.
    After one chunk finishes, starts recording the next immediately.
    """
    while True:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            saved = capture_and_store_audio()
            if saved:
                print(f"[{ts}] Saved audio chunk: {saved}")
                # Next chunk starts immediately
            else:
                print(f"[{ts}] Audio capture disabled in configuration. Waiting...")
                time.sleep(5)
        except KeyboardInterrupt:
            print("Stopping audio capture loop.")
            break
        except Exception as e:
            print(f"[{ts}] Error capturing audio: {e}")
            time.sleep(2)


if __name__ == "__main__":
    run_audio_loop()
