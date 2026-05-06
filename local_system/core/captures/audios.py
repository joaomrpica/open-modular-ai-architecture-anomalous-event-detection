import os
import datetime
import uuid

import sounddevice as sd
import soundfile as sf

from config import system_config

def capture_and_store_audio():
	"""Capture one audio chunk and store to configured folder.

	Reads `AUDIO_CHUNK_DURATION_S`, `AUDIO_STORAGE_PATH`, `MAX_STORED_AUDIOS`,
	and `ENABLE_AUDIO_CAPTURE` from `system_config`.

	Returns: saved file path, or None if capture disabled.
	"""
	if not system_config.ENABLE_AUDIO_CAPTURE:
		return None

	# Ensure storage under local_system/local_storage
	base_dir_rel = system_config.AUDIO_STORAGE_PATH
	local_system_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
	base_dir = os.path.join(local_system_root, base_dir_rel)
	os.makedirs(base_dir, exist_ok=True)

	# Record audio
	sample_rate = 44100
	channels = 1
	duration = int(system_config.AUDIO_CHUNK_DURATION_S)
	frames = duration * sample_rate
	device_index = getattr(system_config, "AUDIO_DEVICE_INDEX", None)
	audio = sd.rec(
		frames,
		samplerate=sample_rate,
		channels=channels,
		dtype="int16",
		device=device_index,
	)
	sd.wait()

	# Save file
	ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
	uid = uuid.uuid4().hex[:8]
	file_path = os.path.join(base_dir, f"audio_{ts}_{uid}.wav")
	sf.write(file_path, audio, sample_rate)

	# Prune old files (keep newest `MAX_STORED_AUDIOS`)
	files = sorted(
		[
			os.path.join(base_dir, f)
			for f in os.listdir(base_dir)
			if os.path.isfile(os.path.join(base_dir, f))
		],
		key=lambda p: os.path.getmtime(p),
	)
	max_files = int(system_config.MAX_STORED_AUDIOS) + 1 # to avoid edge cases while reading data
	if len(files) > max_files:
		for f in files[: len(files) - max_files]:
			try:
				os.remove(f)
			except OSError:
				pass

	return file_path

