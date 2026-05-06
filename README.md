# open-modular-ai-architecture-anomalous-event-detection
Thesis - Modular system for detecting anomalous behavior


# Local–Cloud System Repository

This repository contains the full implementation of a distributed **Local + Cloud system** for **image** and **audio** capture and processing, with **plug-and-play AI modules**.

The repository is organized into two main layers:
- **Local System** – local runtime running on a Raspberry Pi
- **Cloud System** – high-level processing layer running on a server/cloud

The entire system is mainly developed in **Python**.

---

## local-system/ (Local System – Local Runtime)

The `local-system/` directory contains the **Local System**, responsible for running the system locally on a Raspberry Pi.

This layer operates autonomously and is responsible for data capture, controlled local storage, and execution of local AI plugins.

---

### local-system/config/system_config.py

Global configuration file for the Local System (Python constants).  
Includes:
- system identification,
- client identification,
- device identification,
- device configurations.

---

### local-system/core/

Contains the core runtime logic of the Local System.

#### local-system/core/captures/images.py
Responsible for capturing **image frames** from the camera.

#### local-system/core/captures/audios.py
Responsible for capturing **audio segments/chunks** from the microphone.

#### local-system/core/plugin_loader.py
Responsible for:
- reading the system configuration,
- identifying enabled plugins,
- dynamically loading available plugins,
- exposing a unified interface for interacting with loaded plugins.

---

### local-system/local_storage/

Temporary local storage for captured data.

- `local_storage/images/` → stored image frames
- `local_storage/audios/` → stored audio segments

Storage limits are defined in `system_config.py`.

---

### local-system/plugins/

Each plugin is an independent module loaded in **plug-and-play** mode.

#### Standard plugin structure
- `index.py` → standardized plugin interface (entry point)
- `plugin_config.py` → plugin-specific configuration (Python constants)

Initial plugins:
- `fall_detector` → image-based fall detection
- `help_audio` → audio-based help request detection

---

### local_system/routines

Standalone loops for continuous capture.

- `routines_audio.py` → continuously records audio segments and keeps a rolling local buffer.
- `routines_images.py` → periodically captures images and keeps a rolling local buffer.
- `routines_detection.py` → runs detections using the enabled local plugins.
- `routines_verification.py` → periodically sends health pings to the Cloud to confirm the device is online.

---

## cloud-system/ (Cloud System – Cloud Runtime)

The `cloud-system/` directory contains the **Cloud System**, responsible for high-level and computationally intensive processing, persistence, and external communications.

---

### cloud-system/config/system_config.py

Centralized configuration for the Cloud System (Python constants).
Includes, among others:
- API authentication and secrets
- Data persistence toggles (e.g., `STORE_DETECTION_IN_DB`)
- MongoDB Atlas connection settings
- Detection encryption settings (Fernet)
- Communication settings (e.g., email provider)
- AI/LLM settings
- GDPR/privacy-related toggles

---

### cloud-system/core/

Contains the core runtime logic of the Cloud System.

#### cloud-system/core/api.py
FastAPI application that exposes endpoints for evidence ingestion and verification.
Runs via `uvicorn` in the service configuration.

#### cloud-system/core/db.py
MongoDB helpers for creating clients and accessing the database/collections.

#### cloud-system/core/crypto.py
Utilities for optional detection encryption/decryption using Fernet.

#### cloud-system/core/ai_plugin_loader.py
Dynamic loader for AI plugins with a standardized interface.

#### cloud-system/core/communication_plugin_loader.py
Dynamic loader for communication plugins (e.g., email, future channels).

---

### cloud-system/plugins/

Each AI plugin is a standalone module loaded in plug-and-play mode.

#### cloud-system/plugins/ai_multimodal/
- `index.py` → standardized AI plugin entry point (multimodal support)
- `plugin_config.py` → plugin-specific settings (e.g., model keys, parameters)

---

### cloud-system/communication_plugins/

Communication plugins triggered by cloud routines when alerts occur.

#### cloud-system/communication_plugins/email_notifier/
- `index.py` → email sending implementation (e.g., SendGrid)
- `plugin_config.py` → provider keys and template settings

---

### cloud-system/routines

Standalone loops for cloud-side processing and health checks.

- `routines_ai.py` → scans `temp_cloud_storage/`, invokes AI plugins, conditionally persists alerts to MongoDB (when enabled), conditionally triggers communications (when enabled), and moves processed data to `temp_cloud_storage_processed/`.
- `routines_verification.py` → periodic verification/health routine for the cloud layer.

---

### cloud-system/temp_cloud_storage/ and cloud-system/temp_cloud_storage_processed/

Ephemeral storage used by cloud routines.
- `temp_cloud_storage/` → incoming evidence to be processed by AI routines
- `temp_cloud_storage_processed/` → evidence moved here after processing

---

### cloud-system/logs/

Holds runtime artifacts like PID files and logs (e.g., `api.pid`).

---

### cloud-system/requirements.txt

Principal Python dependencies for the Cloud System (FastAPI, Uvicorn, MongoDB client, cryptography, LLM/AI SDKs, email provider, multipart, etc.).

---

## General Conventions

- All code is mainly written in Python.
- Local System configuration is done using `.py` files (constants).
- Only plugins enabled in `system_config.py` are executed locally.
- The Local System operates autonomously and can forward data or events to the Cloud System when required.

---
