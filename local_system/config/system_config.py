"""
System Configuration File
Local System (Raspberry Pi)

All configuration values are defined as constants.
This file represents the single source of truth for the Local System setup.
"""

# ======================================================
# SYSTEM IDENTIFICATION
# ======================================================

SYSTEM_ID = "LOCAL_SYSTEM_1"
CLIENT_ID = "CLIENT_001"
DEVICE_ID = "DEVICE_001"

# ======================================================
# FEATURE TOGGLES (LOCAL SYSTEM BEHAVIOUR)
# ======================================================

# Enable / disable main system features
ENABLE_IMAGE_CAPTURE = True
ENABLE_AUDIO_CAPTURE = True

# RUNTIME PARAMETERS
# Images captured per minute
IMAGE_CAPTURE_FPM = 6

# Audio chunks captured (in seconds)
AUDIO_CHUNK_DURATION_S = 10

# ======================================================
# LOCAL STORAGE CONFIGURATION
# ======================================================

# Base path under local_system/local_storage
LOCAL_STORAGE_BASE_PATH = "local_storage" 

# Image storage
MAX_STORED_IMAGES = 6
IMAGE_STORAGE_PATH = f"{LOCAL_STORAGE_BASE_PATH}/images"

# Audio storage
MAX_STORED_AUDIOS = 6
AUDIO_STORAGE_PATH = f"{LOCAL_STORAGE_BASE_PATH}/audios"


# ======================================================
# PLUGINS CONFIGURATION
# ======================================================

# List of plugins enabled in the Local System
ENABLED_PLUGINS = [
    "fall_detector"
    #"help_audio"
    #"help_audio2"
]

# ======================================================
# SYSTEM VERIFICATION CONFIGURATION
# ======================================================

# Enable system health monitoring
VERIFICATION_SYSTEM_ENABLED = True

# Time interval (seconds) between routine executions
VERIFICATION_SYSTEM_INTERVAL_SECONDS = 120

# Payload identification sent to XTEMP
VERIFICATION_SYSTEM_PAYLOAD = {
    "SYSTEM_ID": SYSTEM_ID,
    "DEVICE_ID": DEVICE_ID,
}

# ======================================================
# CLOUD API CONFIGURATION
# ======================================================

# Cloud API Bearer Token for authentication (sample one provided)
# TODO - This logic should be replaced with secure and dynamic token management.
CLOUD_API_BEARER_TOKEN = "**********"

# Cloud API endpoints
VERIFICATION_SYSTEM_API_BASE_URL = "**********"
DETECTION_SYSTEM_API_BASE_URL = "**********"

# ======================================================
# IR LIGHT SENSOR CONFIGURATION
# ======================================================

# Gayscale mean below which is considered low light
LOW_LIGHT_LUMINOSITY_THRESHOLD = 255      # 0-255 scale

 # BCM pin number used for light sensor control
LIGHT_SENSOR_GPIO_PIN = 17

# ======================================================
# DETECTION ROUTINE CONFIGURATION
# ======================================================

# Interval between detection routine runs (seconds)
DETECTION_SYSTEM_INTERVAL_SECONDS = 60

# Number of recent files to collect for detection
DETECTION_NUM_IMAGES = 6
DETECTION_NUM_AUDIOS = 6

# Local storage paths (aliases for convenience)
LOCAL_STORAGE_IMAGES_PATH = IMAGE_STORAGE_PATH
LOCAL_STORAGE_AUDIOS_PATH = AUDIO_STORAGE_PATH

# ======================================================
# DETECTION ENCRYPTION
# ======================================================

# When enabled, detection payloads (files) are encrypted client-side
# TODO - Implement encryption logic in detection routine
DETECTION_ENCRYPTION_ENABLED = False

# Shared key for encrypting detection payloads
# TODO - Replace with secure key management and should be the same as Cloud System
DETECTION_ENCRYPTION_KEY = "" 

# ======================================================

