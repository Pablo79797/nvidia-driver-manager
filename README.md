# NVIDIA Driver Manager v1.0

A graphical NVIDIA driver manager for Linux with full support for multiple desktop environments.

> 🇵🇱 [Polska wersja README](README_PL.md)

![Platform](https://img.shields.io/badge/platform-Linux-blue)
![Python](https://img.shields.io/badge/python-3.6+-green)
![License](https://img.shields.io/badge/license-open--source-brightgreen)

---

## ✨ Features

### Driver Installation
- **NVK (Mesa/Wayland)** — open-source NVIDIA driver
- **From repositories** — stable and latest versions
- **From .run files** — Production, New Feature, Beta, and Legacy releases

### Driver Management
- Check GPU and driver status
- System diagnostics
- Update driver from repository
- Uninstall driver (restores nouveau)

### Safety & Backup
- Automatic backups before every installation (up to 10 kept)
- Restore previous configuration
- Installation history log
- Detailed error reports

### GPU Monitoring
- Temperature
- GPU usage
- VRAM usage
- Power consumption

### User Interface
- Light and dark theme
- Polish and English language support
- Configurable font size
- Export/import settings

---

## 📋 Requirements

### System
- Linux — Ubuntu, Kubuntu, Debian, Linux Mint, Fedora
- NVIDIA graphics card
- Kernel 6.0+ (required for NVK)

### Python Dependencies
- Python 3.6+
- PySide6 or PyQt6

### System Dependencies (installed automatically when needed)
- **Debian/Ubuntu:** linux-headers, dkms, build-essential
- **Fedora:** kernel-devel, dracut (no dkms; uses akmod for repo driver)

---

## 🚀 Installation

### 1. Install Python dependencies

```bash
# PySide6 (recommended)
pip install PySide6

# or PyQt6
pip install PyQt6
```

### 2. Run the application

```bash
python3 nvidia_driver_manager.py
```

Or make the file executable first:

```bash
chmod +x nvidia_driver_manager.py
./nvidia_driver_manager.py
```

---

## 🖥️ Desktop Environment Compatibility

| Environment | Status |
|---|---|
| KDE/Plasma (Kubuntu) | ✅ Supported |
| GNOME (Ubuntu) | ✅ Supported |
| Xfce (Xubuntu, Linux Mint Xfce) | ✅ Supported |
| MATE (Linux Mint MATE) | ✅ Supported |
| Cinnamon (Linux Mint) | ✅ Supported |
| LXQt (Lubuntu) | ✅ Supported |
| Any other X11/Wayland | ✅ Supported |

---

## 📝 Usage

### Check GPU Status
Go to **Tools → Status** to display information about your graphics card and currently installed driver.

### Install a Driver
1. Choose one of the available installation options.
2. The application will automatically check requirements.
3. Installation requires your sudo password.
4. A system restart is recommended after installation.

### Diagnostics
Go to **Tools → Diagnostics** for a full system and GPU analysis with automatic error reporting.

### Backup & Restore
Go to **Tools → Backup List / Restore** to manage backups. The application automatically creates a backup before every installation, and you can restore any previous state at any time.

---

## ⚙️ Directory Structure

The application creates the following directories under `~/.local/share/nvidia-driver-manager/`:

```
~/.local/share/nvidia-driver-manager/
├── logs/               # Application logs
│   └── errors/         # Error reports
├── cache/              # App state and cache
│   └── backups/        # Configuration backups
└── install-on-reboot/  # Post-reboot install scripts (copy used at boot: /usr/local/lib/nvidia-run-install/)
```

---

## ⚠️ Important Notes

- **Secure Boot**: If enabled, DKMS module installation may require signing or disabling Secure Boot.
- **NVK**: Requires kernel 6.0+. Removes NVIDIA proprietary drivers and DKMS. Does **not** support CUDA.
- **.run installation**: The installation is applied after a system restart.
- **Backups**: A maximum of 10 most recent backups are kept.

---

## 🐧 Fedora

- **NVK:** Initramfs (dracut) is built *after* installing Mesa and firmware so that GSP firmware is included (required for RTX 50 / Blackwell with nouveau). When switching from a .run driver to NVK, the app removes leftover NVIDIA kernel modules and libraries to avoid a black screen after reboot.
- **.run install:** The install script is copied to `/usr/local/lib/nvidia-run-install/` and run from there at boot so SELinux does not block it. Log: `/var/log/nvidia-run-install.log`.
- **Tools → Status:** If `inxi` is missing, it is installed via `dnf install -y inxi`.

## 🐛 Troubleshooting

**No internet connection**
The app checks connectivity via 8.8.8.8. Make sure you have internet access before installing drivers.

**Package installation error**
Go to **Tools → Check and Install Dependencies**, and check the logs in the log panel or in the `logs/` directory.

**sudo permission error**
The app automatically opens a terminal for password entry. Make sure `zenity` or `xterm` is installed.

**Older or laptop NVIDIA GPUs**
This application was tested on Kubuntu 25.10 with a modern GPU. Older or laptop GPU support depends on driver availability in your distribution's repositories. If you test it on older hardware, feel free to open an issue with your results — your feedback helps improve compatibility!

---

## 🤝 Contributing

Issues and pull requests are welcome! If you test the app on a distribution or hardware not listed here, please open an issue to share your results.

---

## 👨‍💻 Author

Created by a Linux enthusiast who wanted a simple, clean way to manage NVIDIA drivers without touching the terminal every time.

---

## 📄 License

This project is open source. See [LICENSE](LICENSE) for details.# nvidia-driver-manager

## ℹ️ Project Status

This project is developed as a hobby, with no guarantee of regular updates.
Bug reports and suggestions are welcome in the Issues tab, however response 
time may be irregular. This project is provided free of charge for the community.
