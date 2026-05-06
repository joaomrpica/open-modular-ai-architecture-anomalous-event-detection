"""
System Configuration File
Cloud System

All configuration values are defined as constants.
This file represents the single source of truth for the Cloud System setup.
"""

# ======================================================
# API Authentication
# ======================================================

# API Bearer Token for authentication (sample one provided)
# TODO - This logic should be replaced with secure and dynamic token management.
CLOUD_API_BEARER_TOKEN = "**********"

# ======================================================
# Data Persistence
# ======================================================

# Enable storing system health pings in the database
STORE_SYSTEM_HEALTH_IN_DB = True

# Enable storing detection records in the database
STORE_DETECTION_IN_DB = True

# If True, processed detections are archived (moved to processed folder)
ARCHIVE_PROCESSED_DETECTIONS = True  

# ======================================================
# MongoDB Atlas Connection
# ======================================================

# MongoDB connection uri
# TODO - Replace with secure credential management
MONGODB_URI = "**********"

# MongoDB database name
MONGODB_DB = "modular-system"

# MongoDB collection names
MONGODB_COLLECTION_VERIFICATION_SYSTEM = "verification_system"
MONGODB_COLLECTION_SYSTEMS = "systems"
MONGODB_COLLECTION_DETECTION = "detections"
MONGODB_COLLECTION_DATA = "data"

# ======================================================
# Detection Encryption
# ======================================================

# When enabled, detection payloads (files) are encrypted client-side
# TODO - Implement encryption logic in detection routine
DETECTION_ENCRYPTION_ENABLED = False

# Shared key for encrypting detection payloads
# TODO - Replace with secure key management and should be the same as Cloud System
DETECTION_ENCRYPTION_KEY = "" 

# ======================================================
# Communication Plugins
# ======================================================

# Enable periodic communication checks based on system health pings
COMMUNICATION_ENABLED = True

# Enabled communication plugins (names correspond to plugin folders)
ENABLED_COMMUNICATION_PLUGINS = [
	"email_notifier",
]

# Email notifier plugin configuration
COMMUNICATION_EMAIL_CONFIG = {
    "email_from": "**********",
    "email_to": ["**********"],
    "subject": "Verification System Alert",
}

# Optional per-plugin configuration mapping
COMMUNICATION_PLUGIN_CONFIGS = {
	"email_notifier": COMMUNICATION_EMAIL_CONFIG,
}

# ======================================================
# VERIFICATION SYSTEM CONFIGURATION
# ======================================================

# How often the verification routine should run (seconds)
VERIFICATION_CHECK_INTERVAL_SECONDS = 120

# Maximum age (seconds) without health pings to consider a system missing
VERIFICATION_SYSTEM_MISSING_MAX_AGE_SECONDS = 300

# ======================================================
# AI Multimodal Plugins (Cloud-side)
# ======================================================

# Enabled AI plugins (folders under cloud_system/plugins)
ENABLED_AI_PLUGINS = [
    "ai_multimodal",
]

AI_CONFIRMATION_MIN_CONFIDENCE = 0.7  # Minimum confidence to confirm detection

# ======================================================
# AI Routine Configuration
# ======================================================

# How often the AI routine should run (seconds)
AI_ROUTINE_INTERVAL_SECONDS = 120

# ======================================================
# GDPR / Privacy Controls
# ======================================================

# When True, images are stored on BDB; when False, only metadata is stored.
# TODO - Create the logic to strip images before storage when disabled.
GDPR_ALLOW_IMAGE_STORAGE_GLOBAL = False
