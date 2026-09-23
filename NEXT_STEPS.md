# Meet IQ - Next Steps & Architecture

We have successfully rebuilt the core AI engine and prepped the frontend for a production mobile app. Below is the split architecture guide on how to develop and deploy this locally.

## The Architecture
- **The Brain (This Workstation):** Handles the Python FastAPI backend, `faster-whisper`, `ffmpeg` acoustic normalization, and all heavy ML pipeline scripts.
- **The Face (Your Laptop):** Handles the Flutter frontend. You will run the app on your laptop to compile it to an iOS/Android device.

---

## 1. Setting up the Backend (On the Workstation)
Keep the backend running on this powerful workstation.
1. Activate the environment:
   ```bash
   source .venv/bin/activate
   ```
2. Start the API Server (bind it to all IPs so your laptop can reach it):
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Find the Workstation IP:**
   Run `hostname -I` on this machine. Note the IP address (e.g., `192.168.1.50`).

---

## 2. Setting up the Mobile App (On Your Laptop)
1. **Clone this Repository** to your local laptop (or download the ZIP).
2. **Install Flutter SDK** on your laptop (https://docs.flutter.dev/get-started/install).
3. **Open the Flutter Project:**
   Open the `flutter_frontend/` directory in VS Code or Android Studio on your laptop.
4. **Link the Backend:**
   Open `lib/services/api_service.dart` and change `baseUrl` to your workstation's IP:
   ```dart
   static const String baseUrl = 'http://192.168.1.50:8000'; // Workstation IP
   ```
5. **Run the App:**
   Connect your iPhone/Android via USB (or use a simulator) and run:
   ```bash
   flutter run
   ```

## 3. What we accomplished today (For Patent/Journal)
- Ripped out all cloud integrations to guarantee a **100% offline, privacy-first pipeline**.
- Added **Decision Traceability**: AI extracts decisions/action items and programmatically links them directly to the acoustic timestamp.
- Added **Live Browser Recording**: Web users can record directly, and the backend utilizes `ffmpeg` for automatic loudnorm (acoustic normalization) so dictaphone audio is crystal clear.
- Added **Flutter Architecture**: Scaffolded the mobile application to prepare for iOS/Android native deployment.
