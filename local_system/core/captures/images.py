import os
import datetime
import uuid

from config import system_config

# Prefer Pi Camera 3 via Picamera2 (libcamera)
from picamera2 import Picamera2


def capture_and_store_image():
	"""Capture one image frame and store to configured folder.

	Respects `ENABLE_IMAGE_CAPTURE`, `IMAGE_STORAGE_PATH`, and `MAX_STORED_IMAGES`.

	Returns: saved file path, or None if capture disabled or failed.
	"""
	if not system_config.ENABLE_IMAGE_CAPTURE:
		return None

	# Ensure storage under local_system/local_storage
	base_dir_rel = system_config.IMAGE_STORAGE_PATH
	local_system_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
	base_dir = os.path.join(local_system_root, base_dir_rel)
	os.makedirs(base_dir, exist_ok=True)

	# Picamera2-only capture
	if Picamera2 is None:
		return None

	ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
	uid = uuid.uuid4().hex[:8]
	file_path = os.path.join(base_dir, f"image_{ts}_{uid}.jpg")

	try:
		picam = Picamera2()
		picam.configure(picam.create_still_configuration())
		picam.start()
		picam.capture_file(file_path)
		picam.stop()
	except Exception:
		return None
	finally:
		if 'picam' in locals() and picam is not None:
			try:
				picam.stop()
			except Exception:
				pass
			try:
				picam.close()
			except Exception:
				pass

	# Evaluate image luminosity and toggle GPIO accordingly
	try:
		import cv2
		gray = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
		if gray is not None:
			mean_lum = float(gray.mean())
			threshold = float(getattr(system_config, "LOW_LIGHT_LUMINOSITY_THRESHOLD", 40))
			pin = int(getattr(system_config, "LIGHT_SENSOR_GPIO_PIN", 5))
			try:
				import RPi.GPIO as GPIO
				GPIO.setwarnings(False)
				GPIO.setmode(GPIO.BCM)
				GPIO.setup(pin, GPIO.OUT)
				GPIO.output(pin, GPIO.HIGH if mean_lum < threshold else GPIO.LOW)
			except Exception:
				pass
	except Exception:
		pass

	# Prune old files
	files = sorted(
		[
			os.path.join(base_dir, f)
			for f in os.listdir(base_dir)
			if os.path.isfile(os.path.join(base_dir, f))
		],
		key=lambda p: os.path.getmtime(p),
	)
	max_files = int(system_config.MAX_STORED_IMAGES) + 1 # to avoid edge cases while reading data
	if len(files) > max_files:
		for f in files[: len(files) - max_files]:
			try:
				os.remove(f)
			except OSError:
				pass

	return file_path

