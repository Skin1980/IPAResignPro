# ⚡ IPAResign Pro

**Deep recursive iOS IPA re-signing utility with automatic device detection & 1-click installation for macOS.**

![macOS Support](https://img.shields.io/badge/macOS-12.0%2B-blue?logo=apple)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)

---

## 🌟 Overview

**IPAResign Pro** is a modern macOS desktop tool designed to cleanly re-sign iOS `.ipa` packages using your personal or team Apple Developer certificates and provisioning profiles.

Unlike standard sideloading utilities that only re-sign the top-level app executable, **IPAResign Pro** performs a **full recursive deep signing** of all nested components:
- Embedded Dynamic Libraries (`.dylib`)
- Embedded Frameworks (`.framework`)
- App Extensions (`.appex`, Widgets, Share, Notification Services)
- WatchKit / Companion Apps
- PlugIns & Helper Executables

This deep signing architecture prevents Apple's runtime integrity check failures (such as the dreaded *"Unable to verify app / Impossibile verificare l'integrità"* error on iOS 16+ / 17+ / 18+).

---

## ✨ Features

- **🚀 1-Click Device Detection & Direct Installation**:
  - Automatically identifies connected iPhones and iPads (USB wired or wireless).
  - Deploys and installs the newly signed `.ipa` directly to your physical iOS device via Apple's native `devicectl` toolchain.
- **🔍 Zero-Config Certificate & Profile Discovery**:
  - Instantly scans the macOS Keychain for valid Apple Developer code-signing identities.
  - Automatically parses and lists Xcode's cached and active Provisioning Profiles (from `~/Library/MobileDevice/Provisioning Profiles` and Xcode `DerivedData`).
- **🛡️ Clean Entitlements Matching**:
  - Extracts the exact entitlements from your provisioning profile (`application-identifier`, `team-identifier`, `get-task-allow`, Keychain Access Groups).
  - Injects proper entitlements and updates `CFBundleIdentifier` in `Info.plist` to match your profile (supports both Wildcard `*` and explicit App IDs).
- **🖥️ Sleek Native Desktop Window**:
  - Runs in a clean, self-contained desktop window powered by Apple's native WebKit (`WKWebView`).
  - Real-time live log stream showing each step of the unzipping, recursive codesigning, repackaging, and installation process.
- **🔒 100% Privacy & Portability**:
  - No personal data, developer accounts, certificates, or team IDs are hardcoded in the source code or binary.
  - Safe to use across multiple Mac computers.

---

## 📦 Download Standalone App

You can download the pre-compiled, standalone macOS app bundle directly:

👉 **[Scarica IPAResignPro_Standalone_Mac.zip (v1.0.0)](https://github.com/Skin1980/IPAResignPro/releases/download/v1.0.0/IPAResignPro_Standalone_Mac.zip)**

1. Extract the `.zip` archive.
2. Drag `IPAResignPro.app` to your `Applications` or `Desktop` folder.
3. Double-click to launch!

> **Note**: On the first launch, if macOS Gatekeeper prompts an alert, right-click the app and choose **Open**.

---

## 🛠️ Requirements

- **macOS**: 12.0 (Monterey), 13.0 (Ventura), 14.0 (Sonoma), 15.0 (Sequoia) or newer (Apple Silicon & Intel supported).
- **Xcode / Command Line Tools**: Make sure Xcode Command Line Tools are installed:
  ```bash
  xcode-select --install
  ```
- **Apple Developer Account**: A free or paid Apple Developer certificate installed in your macOS Keychain.

---

## 💻 Running from Source

If you prefer to run the utility directly from source:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Skin1980/IPAResignPro.git
   cd IPAResignPro
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Desktop Application:**
   ```bash
   python3 standalone_app/run_webkit.py
   ```

Alternatively, to run the local web server version in your browser:
```bash
python3 gui_app.py
```
Then navigate to `http://127.0.0.1:5050`.

---

## 🔨 Building the Standalone `.app`

To compile the standalone macOS `.app` bundle from source:

```bash
./build.sh
```

The resulting `IPAResignPro.app` and `IPAResignPro_Standalone_Mac.zip` will be generated inside the `dist/` directory.

---

## 🍎 Alternative AppleScript Droplet

For users who prefer a minimal drag-and-drop tool without any Python dependencies:
- A pure AppleScript droplet source is included in [`IPAResignPro.applescript`](IPAResignPro.applescript).
- Compile it with:
  ```bash
  osacompile -o IPAResignDroplet.app IPAResignPro.applescript
  ```
- You can drop any `.ipa` file onto `IPAResignDroplet.app` to re-sign it through native Cocoa prompt dialogs.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
