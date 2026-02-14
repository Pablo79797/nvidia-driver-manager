#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVIDIA Driver Manager v1.1 - Graficzna wersja
Kompatybilna w 100% z Linuxem (Ubuntu/Kubuntu/Debian)

Środowiska graficzne:
- KDE/Plasma (Kubuntu) ✅
- GNOME (Ubuntu) ✅
- Xfce (Xubuntu, Linux Mint Xfce) ✅
- MATE (Linux Mint MATE) ✅
- Cinnamon (Linux Mint) ✅
- LXQt (Lubuntu) ✅
- Wszystkie inne z X11/Wayland ✅

PyQt/PySide działa uniwersalnie na wszystkich środowiskach graficznych Linuxa.
"""

import sys
import os
import subprocess
import tempfile
import threading
import queue
import json
import re
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QGroupBox, QMessageBox, QProgressBar,
        QTabWidget, QComboBox, QCheckBox, QLineEdit, QFileDialog, QSplitter,
        QMenuBar, QMenu, QFontDialog, QDialog, QListWidget, QListWidgetItem,
        QDialogButtonBox, QSizePolicy
    )
    from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QSettings
    from PySide6.QtGui import QFont, QTextCursor, QColor, QPalette, QIcon, QPixmap
    QT_LIB = "PySide6"
except ImportError:
    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QLabel, QTextEdit, QGroupBox, QMessageBox, QProgressBar,
            QTabWidget, QComboBox, QCheckBox, QLineEdit, QFileDialog, QSplitter,
        QMenuBar, QMenu, QFontDialog, QDialog, QListWidget, QListWidgetItem,
        QDialogButtonBox, QSizePolicy
        )
        from PyQt6.QtCore import Qt, QThread, pyqtSignal as Signal, QTimer, QSize, QSettings
        from PyQt6.QtGui import QFont, QTextCursor, QColor, QPalette, QIcon, QPixmap
        QT_LIB = "PyQt6"
    except ImportError:
        print("Błąd: Wymagany PySide6 lub PyQt6")
        print("Zainstaluj: pip install PySide6")
        sys.exit(1)


# ============================================================================
# KONFIGURACJA I ŚCIEŻKI
# ============================================================================

# Ścieżki: przy skompilowanej aplikacji. Nuitka onefile na Linuxie uruchamia z /tmp – logi/cache zawsze do HOME.
def _is_onefile_tmp():
    """Czy uruchomiono z katalogu tymczasowego onefile (Nuitka może nie ustawiać sys.frozen)."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        exe = Path(sys.executable).resolve()
        if "/tmp" in str(exe) and "onefile" in str(exe):
            return True
    except Exception:
        pass
    try:
        p = Path(__file__).resolve()
        if "/tmp" in str(p) and "onefile" in str(p):
            return True
    except Exception:
        pass
    return False

if getattr(sys, "frozen", False) or _is_onefile_tmp():
    _base = Path.home() / ".local" / "share" / "nvidia-driver-manager"
    if not sys.platform.startswith("linux"):
        _base = Path(sys.executable).resolve().parent
    # Opcjonalnie: zmienna NVIDIA_DRIVER_MANAGER_BASE wymusza katalog (np. wrapper)
    env_base = os.environ.get("NVIDIA_DRIVER_MANAGER_BASE", "").strip()
    if env_base and Path(env_base).is_dir():
        _base = Path(env_base).resolve()
    SCRIPT_DIR = _base
    LOG_DIR = _base / "logs"
    CACHE_DIR = _base / "cache"
    CACHE_STATE_DIR = CACHE_DIR / "state"
    ERROR_LOG_DIR = LOG_DIR / "errors"
    INSTALL_SCRIPT_DIR = _base / "install-on-reboot"
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        INSTALL_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        _base = Path.home() / ".local" / "share" / "nvidia-driver-manager"
        SCRIPT_DIR = _base
        LOG_DIR = _base / "logs"
        CACHE_DIR = _base / "cache"
        CACHE_STATE_DIR = CACHE_DIR / "state"
        ERROR_LOG_DIR = LOG_DIR / "errors"
        INSTALL_SCRIPT_DIR = _base / "install-on-reboot"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        INSTALL_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
else:
    SCRIPT_DIR = Path(__file__).parent.absolute()
    # Nuitka onefile bez sys.frozen: __file__ może być w /tmp/onefile_*
    if sys.platform.startswith("linux") and ("/tmp" in str(SCRIPT_DIR) and "onefile" in str(SCRIPT_DIR)):
        _base = Path.home() / ".local" / "share" / "nvidia-driver-manager"
        SCRIPT_DIR = _base
        LOG_DIR = _base / "logs"
        CACHE_DIR = _base / "cache"
        CACHE_STATE_DIR = CACHE_DIR / "state"
        ERROR_LOG_DIR = LOG_DIR / "errors"
        INSTALL_SCRIPT_DIR = _base / "install-on-reboot"
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        INSTALL_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    else:
        LOG_DIR = SCRIPT_DIR / "logs"
    CACHE_DIR = SCRIPT_DIR / "cache"
    CACHE_STATE_DIR = CACHE_DIR / "state"
    ERROR_LOG_DIR = LOG_DIR / "errors"
    INSTALL_SCRIPT_DIR = SCRIPT_DIR / "install-on-reboot"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    INSTALL_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)

CACHE_STATE_DIR.mkdir(parents=True, exist_ok=True)

# Katalog z modułem – tu Nuitka/PyInstaller wyekstrahowuje dołączone pliki (logo itd.)
BUNDLE_DIR = Path(__file__).resolve().parent

BACKUP_DIR = CACHE_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
MAX_BACKUPS = 10  # trzymaj tylko N najnowszych; starsze są usuwane przy nowym backupie
HISTORY_FILE = CACHE_STATE_DIR / "install_history.json"

# Tłumaczenia UI (język wybierany w menu Ustawienia → Język)
TRANSLATIONS = {
    "pl": {
        "window_title": "NVIDIA Driver Manager v1.1",
        "menu_settings": "Ustawienia",
        "menu_theme": "Motyw",
        "menu_language": "Język",
        "lang_pl": "Polski",
        "lang_en": "English",
        "menu_font": "Wybierz czcionkę...",
        "font_tooltip": "Zmień czcionkę w całym programie (menu, przyciski, logi)",
        "theme_light": "Jasny",
        "theme_dark": "Ciemny",
        "theme_light_tt": "Użyj jasnego motywu kolorystycznego",
        "theme_dark_tt": "Użyj ciemnego motywu kolorystycznego",
        "action_check_updates": "Sprawdzaj aktualizacje w tle",
        "action_check_updates_tt": "Włącza/wyłącza sprawdzanie nowych wersji sterownika w tle (po ok. 8 s)",
        "action_gpu_paused": "Wstrzymaj monitoring GPU",
        "action_gpu_paused_tt": "Wstrzymuje odświeżanie parametrów GPU (temperatura, VRAM itd.) co 2 s",
        "export_config": "Exportuj konfigurację...",
        "export_config_tt": "Zapisuje ustawienia (okno, czcionka, motyw, proporcje paneli) do pliku JSON.\nMożesz przenieść ten plik na inny komputer i zaimportować.",
        "import_config": "Importuj konfigurację...",
        "import_config_tt": "Wczytuje ustawienia z pliku JSON (wyeksportowanego wcześniej).\nZastąpi bieżące ustawienia okna, czcionki i motywu.",
        "save_settings": "Zapisz ustawienia",
        "save_settings_tt": "Zapisuje bieżący rozmiar i pozycję okna, proporcje paneli, język (bez zamykania programu).",
        "reset_settings": "Resetuj ustawienia",
        "reset_settings_tt": "Przywróć wszystkie ustawienia do domyślnych wartości",
        "about_action": "O programie",
        "about_action_tt": "Wyświetl informacje o aplikacji",
        "menu_tools": "Narzędzia",
        "tool_status": "Status",
        "tool_status_tt": "Wyświetla status sterownika NVIDIA (nvidia-smi, moduły, procesy)",
        "tool_diagnostic": "Diagnostyka",
        "tool_diagnostic_tt": "Uruchamia diagnostykę systemu (GPU, sterownik, moduły, logi)",
        "tool_deps": "Sprawdź i zainstaluj zależności",
        "tool_deps_tt": "Instaluje linux-headers, dkms, build-essential (potrzebne do instalacji)",
        "tool_history": "Historia instalacji",
        "tool_history_tt": "Pokazuje listę przeprowadzonych instalacji sterowników",
        "tool_refresh": "Odśwież informacje",
        "tool_refresh_tt": "Przeładowuje informacje o systemie i dostępnych wersjach sterowników",
        "tool_backup": "Lista backupów / Przywróć",
        "tool_backup_tt": "Zarządzaj backupami (max 10) – lista i przywracanie stanu sprzed instalacji",
        "tool_uninstall": "Usuń sterownik NVIDIA (przywróć nouveau)",
        "tool_uninstall_tt": "Odinstalowuje sterownik NVIDIA, przywraca nouveau. Bez instalacji NVK.",
        "tool_upgrade_repo": "Aktualizuj sterownik z repo",
        "tool_upgrade_repo_tt": "Aktualizuje zainstalowany sterownik z repozytorium (apt upgrade)",
        "reset_title": "Resetuj ustawienia",
        "reset_question": "Czy na pewno chcesz zresetować wszystkie ustawienia do domyślnych?",
        "reset_ok_title": "Ustawienia zresetowane",
        "reset_ok_text": "Ustawienia zostały zresetowane do domyślnych wartości.",
        "about_title": "O programie",
        "about_text": (
            "<h2>NVIDIA Driver Manager v1.1</h2>"
            "<p>Graficzna aplikacja do zarządzania sterownikami NVIDIA dla Linuxa.</p>"
            "<p><b>Funkcje:</b></p>"
            "<ul>"
            "<li>Instalacja NVK (Mesa/Wayland)</li>"
            "<li>Instalacja z repozytoriów</li>"
            "<li>Instalacja .run (Production, New Feature, Beta, Legacy)</li>"
            "<li>Diagnostyka systemu</li>"
            "<li>Status GPU i sterowników</li>"
            "<li>Sprawdzanie wymagań przed instalacją</li>"
            "<li>Szczegółowe raporty błędów</li>"
            "</ul>"
            "<p><b>Kompatybilność:</b></p>"
            "<p>Ubuntu, Kubuntu, Debian, Linux Mint i inne dystrybucje Linuxa.</p>"
            "<p>Wszystkie środowiska graficzne (KDE, GNOME, Xfce, MATE, Cinnamon, itp.)</p>"
        ),
        "tt_gpu_label": "Wykryta karta graficzna NVIDIA",
        "tt_driver_label": "Aktualnie zainstalowany sterownik",
        "tt_distro_label": "Wykryta dystrybucja Linuxa",
        "tt_kernel_label": "Wersja kernela (ważne przy NVK 6.0+ i DKMS)",
        "tt_nvk": "NVK (Mesa/Wayland)\n\nInstaluje open-source sterownik.\nUsuwa wszystkie sterowniki NVIDIA i DKMS.\nBrak CUDA.\nWymagany kernel 6.0+",
        "tt_repo": "NVIDIA z repo (przedostatnia)\n\nStabilna wersja.\nŁatwa aktualizacja przez apt.\nWymagany restart po instalacji.",
        "tt_repo_latest": "NVIDIA z repo (najnowsza)\n\nNajnowsze funkcje.\nŁatwa aktualizacja przez apt.\nWymagany restart po instalacji.",
        "tt_run_prod": "NVIDIA .run Production\n\nInstaluje stabilną wersję produkcyjną\n(seria 580.x)\nPobierana z serwera NVIDIA\nInstalacja nastąpi po restarcie",
        "tt_run_newf": "NVIDIA .run New Feature\n\nInstaluje wersję z nowymi funkcjami\n(seria 590.45+)\nPobierana z serwera NVIDIA\nInstalacja nastąpi po restarcie",
        "tt_run_beta": "NVIDIA .run Beta\n\nInstaluje wersję beta\n(seria 590.00-590.44)\nPobierana z serwera NVIDIA\nInstalacja nastąpi po restarcie",
        "tt_run_legacy": "NVIDIA .run Legacy\n\nInstaluje wersję legacy\n(seria 470.x)\nDla starszych kart graficznych\nInstalacja nastąpi po restarcie",
        "tt_run_prod_ver": "NVIDIA .run Production ({0})\n\nInstaluje stabilną wersję produkcyjną\n(seria 580.x)\nPobierana z serwera NVIDIA\nInstalacja nastąpi po restarcie",
        "tt_run_newf_ver": "NVIDIA .run New Feature ({0})\n\nInstaluje wersję z nowymi funkcjami\n(seria 590.45+)\nPobierana z serwera NVIDIA\nInstalacja nastąpi po restarcie",
        "tt_run_beta_ver": "NVIDIA .run Beta ({0})\n\nInstaluje wersję beta\n(seria 590.00-590.44)\nPobierana z serwera NVIDIA\nInstalacja nastąpi po restarcie",
        "tt_run_legacy_ver": "NVIDIA .run Legacy ({0})\n\nInstaluje wersję legacy\n(seria 470.x)\nDla starszych kart graficznych\nInstalacja nastąpi po restarcie",
        "tt_repo_ver": "NVIDIA z repo (przedostatnia) ({0})\n\nStabilna wersja.\nŁatwa aktualizacja przez apt.\nWymagany restart po instalacji.",
        "tt_repo_latest_ver": "NVIDIA z repo (najnowsza) ({0})\n\nNajnowsze funkcje.\nŁatwa aktualizacja przez apt.\nWymagany restart po instalacji.",
        "tt_clear_log": "Czyści wszystkie logi z panelu",
        "tt_save_log": "Zapisuje aktualne logi do pliku tekstowego",
        "tt_open_log_dir": "Otwiera folder z zapisanymi logami i raportami",
        "tt_restore_backup": "Reinstaluje pakiety z backupu (działa dla stanu z repo).",
        "group_info": "Informacje o systemie",
        "group_gpu_params": "Parametry GPU",
        "group_install": "Opcje instalacji",
        "group_logs": "Logi",
        "btn_clear_log": "Wyczyść logi",
        "btn_save_log": "Zapisz logi",
        "btn_open_log_dir": "Otwórz katalog logów",
        "status_ready": "Gotowy",
        "sys_gpu_fmt": "GPU: {0}",
        "sys_gpu_not_detected": "GPU: Nie wykryto",
        "sys_driver_fmt": "Sterownik: {0}",
        "sys_driver_opensource": " (open-source)",
        "sys_driver_nvidia": " (NVIDIA)",
        "sys_distro_fmt": "Dystrybucja: {0} ({1})",
        "sys_kernel_fmt": "Kernel: {0}",
        "sys_kernel_dash": "Kernel: —",
        "sys_detecting": "Wykrywanie...",
        "sys_distro_detecting": "Dystrybucja: Wykrywanie...",
        "gpu_temp_fmt": "Temperatura: {0} °C",
        "gpu_temp_na": "Temperatura: —",
        "gpu_usage_fmt": "Użycie GPU: {0} %",
        "gpu_usage_na": "Użycie GPU: —",
        "gpu_vram_fmt": "VRAM: {0} / {1} MiB",
        "gpu_vram_na": "VRAM: —",
        "gpu_power_fmt": "Pobór mocy: {0} W",
        "gpu_power_na": "Pobór mocy: —",
        "log_detecting_system": "Wykrywanie systemu...",
        "log_gpu_detected": "Wykryto GPU: {0}",
        "log_gpu_not_detected": "Nie wykryto GPU NVIDIA",
        "log_fetching_versions": "Pobieranie najnowszych wersji z serwera...",
        "log_system_info_loaded": "Informacje o systemie załadowane",
        "log_log_dir_info": "Logi, cache i skrypty instalacyjne: {0}",
        "log_installing_deps": "Instalowanie brakujących zależności: {0}",
        "log_update_repo_failed": "Aktualizacja repozytoriów nie powiodła się",
        "log_install_deps_failed": "Nie udało się zainstalować zależności",
        "log_deps_installed": "Zależności zainstalowane",
        "log_remove_nvidia_header": "=== USUWANIE STEROWNIKA NVIDIA (przywrócenie nouveau) ===",
        "log_cleaning_nvidia": "Czyszczenie artefaktów NVIDIA...",
        "log_nvidia_libs_visible": "Niektóre biblioteki NVIDIA nadal są widoczne",
        "log_nvidia_libs_cache_info": "W ldconfig nadal widoczne wpisy NVIDIA (cache); odświeży się po restarcie.",
        "log_config_nouveau": "Konfiguracja nouveau...",
        "log_nvidia_removed": "Sterownik NVIDIA usunięty. Nouveau włączony. Zalecany restart.",
        "log_no_driver_repo": "Nie wykryto sterownika NVIDIA z repo (nvidia-driver-XXX-open).",
        "log_updating_repo_pkg": "Aktualizacja sterownika z repo ({0})...",
        "log_driver_updated": "Sterownik {0} zaktualizowany. Zalecany restart.",
        "log_update_failed": "Aktualizacja nie powiodła się.",
        "log_no_network": "Brak połączenia z 8.8.8.8 – sieć może nie działać",
        "log_secure_boot": "Secure Boot jest włączony – instalacja DKMS/sterowników może się nie powieść.",
        "log_secure_boot_advice": "Wyłącz Secure Boot lub przygotuj podpisanie modułów (mokutil).",
        "log_error_code": "Błąd (kod: {0})",
        "log_install_nvk_header": "=== INSTALACJA NVK ===",
        "log_install_mesa_nvk": "Instalacja Mesa + NVK...",
        "log_nvk_install_error": "Błąd podczas instalacji pakietów NVK",
        "log_nvk_installed": "NVK zainstalowany pomyślnie",
        "log_reboot_notice": "System zostanie zrestartowany",
        "log_install_repo_header": "=== INSTALACJA Z REPO ({0}) ===",
        "log_cleaning": "Czyszczenie...",
        "log_updating_repos": "Aktualizacja repozytoriów...",
        "log_installing_pkg": "Instalacja {0}... (może potrwać kilka minut)",
        "log_driver_installed": "Sterownik {0} zainstalowany pomyślnie",
        "log_blocking_nouveau": "Blokowanie nouveau...",
        "log_install_pkg_error": "Błąd podczas instalacji {0}",
        "log_install_run_header": "=== INSTALACJA .RUN {0} ({1}) ===",
        "log_downloading_run": "Pobieranie pliku .run...",
        "log_download_run_failed": "Nie udało się pobrać pliku .run",
        "log_preparing_system": "Przygotowanie systemu...",
        "log_prepare_done_reboot": "Przygotowanie zakończone. Instalacja nastąpi po restarcie.",
        "log_downloaded": "Pobrano: {0}",
        "log_ldconfig_warning": "OSTRZEŻENIE: ldconfig nadal widzi biblioteki NVIDIA",
        "log_nvidia_pkgs_warning": "OSTRZEŻENIE: Nadal zainstalowane pakiety NVIDIA ({0} pakietów)",
        "log_nvidia_firmware_kept": "1 pakiet NVIDIA (nvidia-gpu-firmware) zostawiony dla NVK – to oczekiwane.",
        "log_ldconfig_firmware_ok": "ldconfig nadal pokazuje NVIDIA (firmware); normalne przy NVK.",
        "log_updating_initramfs": "Aktualizacja initramfs...",
        "log_font_changed": "Czcionka zmieniona na: {0} {1}pt",
        "log_theme_dark": "Ciemny",
        "log_theme_light": "Jasny",
        "log_theme_changed": "Motyw zmieniony na: {0}",
        "log_settings_reset": "Ustawienia zresetowane do domyślnych",
        "log_settings_saved": "Ustawienia zapisane",
        "log_error_report_saved": "Raport błędu zapisany: {0}",
        "log_error_report_failed": "Nie można zapisać raportu błędu: {0}",
        "log_sudo_ok": "✓ Uprawnienia sudo już aktywne (bez pytania o hasło)",
        "log_install_cancelled": "Instalacja anulowana - brak uprawnień sudo",
        "log_sudo_granted": "✓ Uprawnienia sudo uzyskane",
        "log_wrong_password": "Błędne hasło – spróbuj ponownie",
        "log_password_error": "Błąd sprawdzania hasła",
        "log_opening_terminal": "Otwarcie terminala do wpisania hasła...",
        "log_no_terminal": "✗ Nie znaleziono terminala ani okienka na hasło (zainstaluj zenity lub xterm)",
        "log_sudo_failed": "✗ Nie udało się uzyskać uprawnień sudo",
        "log_backup_created": "Backup utworzony: {0}",
        "log_backup_removed_old": "Usunięto najstarszy backup: {0}",
        "log_backup_create_failed": "Nie udało się utworzyć backupu: {0}",
        "log_backup_no_pkgs": "Backup nie zawiera pakietów do przywrócenia (np. był .run)",
        "log_restoring_backup": "Przywracanie pakietów z backupu...",
        "log_restored": "Przywrócono pakiety. Zalecany restart.",
        "log_restore_error": "Błąd przywracania: {0}",
        "log_linux_only": "Instalacja dostępna tylko na Linuxie",
        "log_linux_only_short": "Dostępne tylko na Linuxie",
        "log_checking_requirements": "Sprawdzanie wymagań przed instalacją...",
        "log_requirements_issues": "⚠ Wykryto problemy z wymaganiami:",
        "log_requirement_item": "  - {0}",
        "log_starting_nvk": "Rozpoczynam instalację NVK...",
        "log_nvk_done": "Instalacja NVK zakończona",
        "log_starting_repo": "Rozpoczynam instalację z repo ({0})...",
        "log_install_done_restart": "Instalacja zakończona. Wymagany restart.",
        "log_starting_run": "Rozpoczynam instalację .run {0} ({1})...",
        "log_prepare_done": "Przygotowanie zakończone. Instalacja nastąpi po restarcie.",
        "log_removing_nvidia": "Rozpoczynam usuwanie sterownika NVIDIA...",
        "log_no_driver_repo_short": "Nie wykryto sterownika z repo (nvidia-driver-XXX-open).",
        "log_updating_pkg": "Aktualizacja {0}...",
        "log_cannot_create_logdir": "Nie można utworzyć katalogu logów",
        "log_opening_dir": "Otwieranie katalogu: {0}",
        "log_cannot_open_dir": "Nie można otworzyć katalogu: {0}",
        "log_deps_linux_only": "Zależności dostępne tylko na Linuxie",
        "log_all_deps_installed": "Wszystkie zależności (linux-headers, dkms, build-essential) są zainstalowane.",
        "log_installing_missing": "Instalowanie brakujących: {0}",
        "log_deps_install_ok": "Zależności zainstalowane pomyślnie.",
        "log_deps_install_failed": "Nie udało się zainstalować zależności.",
        "log_deps_auto_install": "Brakujące wymagania (dkms, linux-headers, build-essential) zostaną doinstalowane przed instalacją.",
        "log_config_saved": "Konfiguracja zapisana: {0}",
        "log_config_save_error": "Błąd zapisu: {0}",
        "log_config_loaded": "Konfiguracja wczytana: {0}",
        "log_config_load_error": "Błąd wczytywania: {0}",
        "log_status_system": "Status systemu:",
        "log_checking_status": "Sprawdzanie statusu...",
        "log_inxi_installing": "inxi nie jest zainstalowane. Instalowanie...",
        "log_inxi_installed": "inxi zainstalowane. Sprawdzanie statusu...",
        "log_inxi_failed": "Nie udało się zainstalować inxi",
        "log_diag_linux_only": "Diagnostyka dostępna tylko na Linuxie",
        "log_running_diag": "Uruchamianie diagnostyki...",
        "log_diag_saved": "Diagnostyka zapisana: {0}",
        "log_diag_error": "Błąd podczas diagnostyki: {0}",
        "log_rebooting": "Restartowanie systemu...",
        "log_logs_saved": "Logi zapisane: {0}",
        "log_save_error": "Błąd zapisu: {0}",
        "log_unknown_install": "Nieznany typ instalacji",
        "log_error_exception": "Błąd: {0}",
        "btn_nvk_text": "1. NVK (Mesa/Wayland)",
        "btn_repo_fmt": "2. NVIDIA z repo ({0})",
        "btn_repo_latest_fmt": "3. NVIDIA z repo ({0})",
        "btn_run_prod_fmt": "4. NVIDIA .run Production ({0})",
        "btn_run_newf_fmt": "5. NVIDIA .run New Feature ({0})",
        "btn_run_beta_fmt": "6. NVIDIA .run Beta ({0})",
        "btn_run_legacy_fmt": "7. NVIDIA .run Legacy ({0})",
        "title_confirm": "Potwierdzenie",
        "msg_uninstall_confirm": "Usunąć sterownik NVIDIA i włączyć nouveau?\n\nZalecany restart po zakończeniu.",
        "title_nvk_kernel": "Kernel za stary dla NVK",
        "msg_nvk_kernel": "NVK wymaga kernela 6.0+. Twój kernel: {0} – instalacja może nie zadziałać.\n\nKontynuować?",
        "title_requirements": "Problemy z wymaganiami",
        "msg_requirements_continue": "Wykryto problemy z wymaganiami:\n\n{0}\n\nCzy chcesz kontynuować mimo to?",
        "title_update": "Aktualizacja",
        "msg_no_driver_repo_info": "Nie wykryto zainstalowanego sterownika NVIDIA z repozytorium.",
        "title_deps": "Zależności",
        "title_dnf5": "Szybszy menedżer pakietów (dnf5)",
        "msg_dnf5_offer": "dnf5 nie jest zainstalowany.\n\nZainstalować go dla szybszej pracy z repozytoriami?\n(Program będzie używał dnf5 zamiast dnf.)",
        "log_dnf5_installed": "dnf5 zainstalowany – będzie używany zamiast dnf.",
        "log_dnf5_failed": "Instalacja dnf5 nie powiodła się – używam dnf.",
        "msg_deps_all_installed": "Wszystkie wymagane pakiety są zainstalowane.",
        "msg_deps_installed_ok": "Brakujące pakiety zostały zainstalowane.",
        "msg_deps_install_failed": "Instalacja nie powiodła się. Sprawdź logi.",
        "title_backup": "Backup",
        "msg_backup_select": "Wybierz backup z listy.",
        "msg_backup_restored": "Przywracanie zakończone. Zalecany restart.",
        "msg_backup_failed": "Przywracanie nie powiodło się lub backup nie zawiera pakietów.",
        "title_install_in_progress": "Instalacja w toku",
        "msg_install_in_progress": "Instalacja sterownika jest w toku.\n\nPoczekaj na zakończenie instalacji, a potem zamknij aplikację.\nZamykanie w trakcie instalacji może spowodować awarię.",
        "msg_install_close_anyway": "Instalacja jest w toku.\n\nZamknąć program mimo to?\nInstalacja zostanie przerwana.",
        "title_sudo_required": "Wymagane uprawnienia administratora",
        "msg_sudo_ask": "Instalacja sterownika wymaga uprawnień administratora (sudo).\n\nCzy chcesz teraz podać hasło sudo?",
        "title_wrong_password": "Błędne hasło",
        "msg_wrong_password": "Hasło jest nieprawidłowe. Spróbuj ponownie.",
        "title_error": "Błąd",
        "msg_no_password_dialog": "Nie można wyświetlić okna na hasło.\nZainstaluj: zenity (sudo apt install zenity) lub xterm.",
        "title_wait_sudo": "Oczekiwanie na uprawnienia sudo",
        "msg_wait_sudo": "Otworzyło się okno terminala.\n\nWpisz tam hasło i naciśnij Enter.\n\nProgram sam sprawdzi uprawnienia.",
        "btn_cancel": "Anuluj",
        "title_sudo_error": "Błąd uprawnień",
        "msg_sudo_failed": "Nie udało się uzyskać uprawnień administratora.\nMożesz spróbować ponownie.",
        "title_restart": "Restart",
        "msg_restart_now": "Czy zrestartować system teraz?",
        "title_backup_dialog": "Backup – lista i przywracanie",
        "msg_backup_snapshots": "Snapshoty przed instalacją (data, sterownik → cel):",
        "msg_no_backups": "(brak backupów)",
        "btn_restore_backup": "Przywróć wybrany backup",
        "btn_close": "Zamknij",
        "title_export": "Export",
        "msg_export_ok": "Konfiguracja została zapisana.",
        "title_import": "Import",
        "msg_import_ok": "Konfiguracja została wczytana.",
        "pwd_dialog_label": "Wpisz hasło administratora (sudo):",
        "pwd_placeholder": "Hasło",
        "save_log_title": "Zapisz logi",
        "install_history_title": "Historia instalacji",
        "install_history_label": "Data, typ, wersja, sukces:",
    },
    "en": {
        "window_title": "NVIDIA Driver Manager v1.1",
        "menu_settings": "Settings",
        "menu_theme": "Theme",
        "menu_language": "Language",
        "lang_pl": "Polski",
        "lang_en": "English",
        "menu_font": "Choose font...",
        "font_tooltip": "Change font for the whole application (menus, buttons, logs)",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "theme_light_tt": "Use light colour theme",
        "theme_dark_tt": "Use dark colour theme",
        "action_check_updates": "Check for updates in background",
        "action_check_updates_tt": "Enable/disable checking for new driver versions in background (after ~8 s)",
        "action_gpu_paused": "Pause GPU monitoring",
        "action_gpu_paused_tt": "Pauses refreshing of GPU parameters (temperature, VRAM, etc.) every 2 s",
        "export_config": "Export configuration...",
        "export_config_tt": "Saves settings (window, font, theme, panel sizes) to a JSON file.\nYou can move this file to another computer and import it.",
        "import_config": "Import configuration...",
        "import_config_tt": "Loads settings from a JSON file (exported earlier).\nWill replace current window, font and theme settings.",
        "save_settings": "Save settings",
        "save_settings_tt": "Saves current window size and position, panel proportions, language (without closing the program).",
        "reset_settings": "Reset settings",
        "reset_settings_tt": "Restore all settings to default values",
        "about_action": "About",
        "about_action_tt": "Show application information",
        "menu_tools": "Tools",
        "tool_status": "Status",
        "tool_status_tt": "Shows NVIDIA driver status (nvidia-smi, modules, processes)",
        "tool_diagnostic": "Diagnostics",
        "tool_diagnostic_tt": "Runs system diagnostics (GPU, driver, modules, logs)",
        "tool_deps": "Check and install dependencies",
        "tool_deps_tt": "Installs linux-headers, dkms, build-essential (required for installation)",
        "tool_history": "Install history",
        "tool_history_tt": "Shows list of performed driver installations",
        "tool_refresh": "Refresh information",
        "tool_refresh_tt": "Reloads system info and available driver versions",
        "tool_backup": "Backup list / Restore",
        "tool_backup_tt": "Manage backups (max 10) – list and restore state before installation",
        "tool_uninstall": "Remove NVIDIA driver (restore nouveau)",
        "tool_uninstall_tt": "Uninstalls NVIDIA driver, restores nouveau. No NVK installation.",
        "tool_upgrade_repo": "Upgrade driver from repo",
        "tool_upgrade_repo_tt": "Upgrades installed driver from repository (apt upgrade)",
        "reset_title": "Reset settings",
        "reset_question": "Are you sure you want to reset all settings to default?",
        "reset_ok_title": "Settings reset",
        "reset_ok_text": "Settings have been reset to default values.",
        "about_title": "About",
        "about_text": (
            "<h2>NVIDIA Driver Manager v1.1</h2>"
            "<p>Graphical application for managing NVIDIA drivers on Linux.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>NVK installation (Mesa/Wayland)</li>"
            "<li>Installation from repositories</li>"
            "<li>.run installation (Production, New Feature, Beta, Legacy)</li>"
            "<li>System diagnostics</li>"
            "<li>GPU and driver status</li>"
            "<li>Pre-installation requirements check</li>"
            "<li>Detailed error reports</li>"
            "</ul>"
            "<p><b>Compatibility:</b></p>"
            "<p>Ubuntu, Kubuntu, Debian, Linux Mint and other Linux distributions.</p>"
            "<p>All desktop environments (KDE, GNOME, Xfce, MATE, Cinnamon, etc.)</p>"
        ),
        "tt_gpu_label": "Detected NVIDIA graphics card",
        "tt_driver_label": "Currently installed driver",
        "tt_distro_label": "Detected Linux distribution",
        "tt_kernel_label": "Kernel version (important for NVK 6.0+ and DKMS)",
        "tt_nvk": "NVK (Mesa/Wayland)\n\nInstalls open-source driver.\nRemoves all NVIDIA and DKMS drivers.\nNo CUDA.\nRequires kernel 6.0+",
        "tt_repo": "NVIDIA from repo (previous)\n\nStable version.\nEasy update via apt.\nRestart required after installation.",
        "tt_repo_latest": "NVIDIA from repo (latest)\n\nLatest features.\nEasy update via apt.\nRestart required after installation.",
        "tt_run_prod": "NVIDIA .run Production\n\nInstalls stable production version\n(580.x series)\nDownloaded from NVIDIA server\nInstallation after restart",
        "tt_run_newf": "NVIDIA .run New Feature\n\nInstalls version with new features\n(590.45+ series)\nDownloaded from NVIDIA server\nInstallation after restart",
        "tt_run_beta": "NVIDIA .run Beta\n\nInstalls beta version\n(590.00-590.44 series)\nDownloaded from NVIDIA server\nInstallation after restart",
        "tt_run_legacy": "NVIDIA .run Legacy\n\nInstalls legacy version\n(470.x series)\nFor older graphics cards\nInstallation after restart",
        "tt_run_prod_ver": "NVIDIA .run Production ({0})\n\nInstalls stable production version\n(580.x series)\nDownloaded from NVIDIA server\nInstallation after restart",
        "tt_run_newf_ver": "NVIDIA .run New Feature ({0})\n\nInstalls version with new features\n(590.45+ series)\nDownloaded from NVIDIA server\nInstallation after restart",
        "tt_run_beta_ver": "NVIDIA .run Beta ({0})\n\nInstalls beta version\n(590.00-590.44 series)\nDownloaded from NVIDIA server\nInstallation after restart",
        "tt_run_legacy_ver": "NVIDIA .run Legacy ({0})\n\nInstalls legacy version\n(470.x series)\nFor older graphics cards\nInstallation after restart",
        "tt_repo_ver": "NVIDIA from repo (previous) ({0})\n\nStable version.\nEasy update via apt.\nRestart required after installation.",
        "tt_repo_latest_ver": "NVIDIA from repo (latest) ({0})\n\nLatest features.\nEasy update via apt.\nRestart required after installation.",
        "tt_clear_log": "Clears all logs from the panel",
        "tt_save_log": "Saves current logs to a text file",
        "tt_open_log_dir": "Opens folder with saved logs and reports",
        "tt_restore_backup": "Reinstalls packages from backup (works for repo state).",
        "group_info": "System information",
        "group_gpu_params": "GPU parameters",
        "group_install": "Installation options",
        "group_logs": "Logs",
        "btn_clear_log": "Clear logs",
        "btn_save_log": "Save logs",
        "btn_open_log_dir": "Open log directory",
        "status_ready": "Ready",
        "sys_gpu_fmt": "GPU: {0}",
        "sys_gpu_not_detected": "GPU: Not detected",
        "sys_driver_fmt": "Driver: {0}",
        "sys_driver_opensource": " (open-source)",
        "sys_driver_nvidia": " (NVIDIA)",
        "sys_distro_fmt": "Distribution: {0} ({1})",
        "sys_kernel_fmt": "Kernel: {0}",
        "sys_kernel_dash": "Kernel: —",
        "sys_detecting": "Detecting...",
        "sys_distro_detecting": "Distribution: Detecting...",
        "gpu_temp_fmt": "Temperature: {0} °C",
        "gpu_temp_na": "Temperature: —",
        "gpu_usage_fmt": "GPU usage: {0} %",
        "gpu_usage_na": "GPU usage: —",
        "gpu_vram_fmt": "VRAM: {0} / {1} MiB",
        "gpu_vram_na": "VRAM: —",
        "gpu_power_fmt": "Power draw: {0} W",
        "gpu_power_na": "Power draw: —",
        "log_detecting_system": "Detecting system...",
        "log_gpu_detected": "GPU detected: {0}",
        "log_gpu_not_detected": "NVIDIA GPU not detected",
        "log_fetching_versions": "Fetching latest versions from server...",
        "log_system_info_loaded": "System information loaded",
        "log_log_dir_info": "Logs, cache and install scripts: {0}",
        "log_installing_deps": "Installing missing dependencies: {0}",
        "log_update_repo_failed": "Repository update failed",
        "log_install_deps_failed": "Failed to install dependencies",
        "log_deps_installed": "Dependencies installed",
        "log_remove_nvidia_header": "=== REMOVING NVIDIA DRIVER (restore nouveau) ===",
        "log_cleaning_nvidia": "Cleaning NVIDIA artifacts...",
        "log_nvidia_libs_visible": "Some NVIDIA libraries still visible",
        "log_nvidia_libs_cache_info": "ldconfig still shows NVIDIA entries (cache); will refresh after reboot.",
        "log_config_nouveau": "Configuring nouveau...",
        "log_nvidia_removed": "NVIDIA driver removed. Nouveau enabled. Restart recommended.",
        "log_no_driver_repo": "NVIDIA driver from repo not found (nvidia-driver-XXX-open).",
        "log_updating_repo_pkg": "Updating driver from repo ({0})...",
        "log_driver_updated": "Driver {0} updated. Restart recommended.",
        "log_update_failed": "Update failed.",
        "log_no_network": "No connection to 8.8.8.8 – network may be down",
        "log_secure_boot": "Secure Boot is enabled – DKMS/driver installation may fail.",
        "log_secure_boot_advice": "Disable Secure Boot or set up module signing (mokutil).",
        "log_error_code": "Error (code: {0})",
        "log_install_nvk_header": "=== NVK INSTALLATION ===",
        "log_install_mesa_nvk": "Installing Mesa + NVK...",
        "log_nvk_install_error": "Error installing NVK packages",
        "log_nvk_installed": "NVK installed successfully",
        "log_reboot_notice": "System will be restarted",
        "log_install_repo_header": "=== INSTALLING FROM REPO ({0}) ===",
        "log_cleaning": "Cleaning...",
        "log_updating_repos": "Updating repositories...",
        "log_installing_pkg": "Installing {0}... (may take a few minutes)",
        "log_driver_installed": "Driver {0} installed successfully",
        "log_blocking_nouveau": "Blocking nouveau...",
        "log_install_pkg_error": "Error installing {0}",
        "log_install_run_header": "=== INSTALLING .RUN {0} ({1}) ===",
        "log_downloading_run": "Downloading .run file...",
        "log_download_run_failed": "Failed to download .run file",
        "log_preparing_system": "Preparing system...",
        "log_prepare_done_reboot": "Preparation complete. Installation will run after restart.",
        "log_downloaded": "Downloaded: {0}",
        "log_ldconfig_warning": "WARNING: ldconfig still sees NVIDIA libraries",
        "log_nvidia_pkgs_warning": "WARNING: NVIDIA packages still installed ({0} packages)",
        "log_nvidia_firmware_kept": "1 NVIDIA package (nvidia-gpu-firmware) kept for NVK – expected.",
        "log_ldconfig_firmware_ok": "ldconfig still lists NVIDIA (firmware); normal for NVK.",
        "log_updating_initramfs": "Updating initramfs...",
        "log_font_changed": "Font changed to: {0} {1}pt",
        "log_theme_dark": "Dark",
        "log_theme_light": "Light",
        "log_theme_changed": "Theme changed to: {0}",
        "log_settings_reset": "Settings reset to default",
        "log_settings_saved": "Settings saved",
        "log_error_report_saved": "Error report saved: {0}",
        "log_error_report_failed": "Could not save error report: {0}",
        "log_sudo_ok": "✓ Sudo privileges already active (no password prompt)",
        "log_install_cancelled": "Installation cancelled - no sudo privileges",
        "log_sudo_granted": "✓ Sudo privileges granted",
        "log_wrong_password": "Wrong password – try again",
        "log_password_error": "Password check error",
        "log_opening_terminal": "Opening terminal for password...",
        "log_no_terminal": "✗ Terminal or password dialog not found (install zenity or xterm)",
        "log_sudo_failed": "✗ Failed to obtain sudo privileges",
        "log_backup_created": "Backup created: {0}",
        "log_backup_removed_old": "Removed oldest backup: {0}",
        "log_backup_create_failed": "Failed to create backup: {0}",
        "log_backup_no_pkgs": "Backup has no packages to restore (e.g. was .run)",
        "log_restoring_backup": "Restoring packages from backup...",
        "log_restored": "Packages restored. Restart recommended.",
        "log_restore_error": "Restore error: {0}",
        "log_linux_only": "Installation available on Linux only",
        "log_linux_only_short": "Linux only",
        "log_checking_requirements": "Checking requirements before installation...",
        "log_requirements_issues": "⚠ Requirements issues detected:",
        "log_requirement_item": "  - {0}",
        "log_starting_nvk": "Starting NVK installation...",
        "log_nvk_done": "NVK installation complete",
        "log_starting_repo": "Starting installation from repo ({0})...",
        "log_install_done_restart": "Installation complete. Restart required.",
        "log_starting_run": "Starting .run installation {0} ({1})...",
        "log_prepare_done": "Preparation complete. Installation will run after restart.",
        "log_removing_nvidia": "Removing NVIDIA driver...",
        "log_no_driver_repo_short": "Driver from repo not found (nvidia-driver-XXX-open).",
        "log_updating_pkg": "Updating {0}...",
        "log_cannot_create_logdir": "Cannot create log directory",
        "log_opening_dir": "Opening directory: {0}",
        "log_cannot_open_dir": "Cannot open directory: {0}",
        "log_deps_linux_only": "Dependencies available on Linux only",
        "log_all_deps_installed": "All dependencies (linux-headers, dkms, build-essential) are installed.",
        "log_installing_missing": "Installing missing: {0}",
        "log_deps_install_ok": "Dependencies installed successfully.",
        "log_deps_install_failed": "Failed to install dependencies.",
        "log_deps_auto_install": "Missing requirements (dkms, linux-headers, build-essential) will be installed before driver installation.",
        "log_config_saved": "Configuration saved: {0}",
        "log_config_save_error": "Save error: {0}",
        "log_config_loaded": "Configuration loaded: {0}",
        "log_config_load_error": "Load error: {0}",
        "log_status_system": "System status:",
        "log_checking_status": "Checking status...",
        "log_inxi_installing": "inxi not installed. Installing...",
        "log_inxi_installed": "inxi installed. Checking status...",
        "log_inxi_failed": "Failed to install inxi",
        "log_diag_linux_only": "Diagnostics available on Linux only",
        "log_running_diag": "Running diagnostics...",
        "log_diag_saved": "Diagnostics saved: {0}",
        "log_diag_error": "Diagnostics error: {0}",
        "log_rebooting": "Rebooting system...",
        "log_logs_saved": "Logs saved: {0}",
        "log_save_error": "Save error: {0}",
        "log_unknown_install": "Unknown installation type",
        "log_error_exception": "Error: {0}",
        "btn_nvk_text": "1. NVK (Mesa/Wayland)",
        "btn_repo_fmt": "2. NVIDIA from repo ({0})",
        "btn_repo_latest_fmt": "3. NVIDIA from repo ({0})",
        "btn_run_prod_fmt": "4. NVIDIA .run Production ({0})",
        "btn_run_newf_fmt": "5. NVIDIA .run New Feature ({0})",
        "btn_run_beta_fmt": "6. NVIDIA .run Beta ({0})",
        "btn_run_legacy_fmt": "7. NVIDIA .run Legacy ({0})",
        "title_confirm": "Confirmation",
        "msg_uninstall_confirm": "Remove NVIDIA driver and enable nouveau?\n\nRestart recommended after completion.",
        "title_nvk_kernel": "Kernel too old for NVK",
        "msg_nvk_kernel": "NVK requires kernel 6.0+. Your kernel: {0} – installation may fail.\n\nContinue?",
        "title_requirements": "Requirements issues",
        "msg_requirements_continue": "Requirements issues detected:\n\n{0}\n\nDo you want to continue anyway?",
        "title_update": "Update",
        "msg_no_driver_repo_info": "No installed NVIDIA driver from repository found.",
        "title_deps": "Dependencies",
        "title_dnf5": "Faster package manager (dnf5)",
        "msg_dnf5_offer": "dnf5 is not installed.\n\nInstall it for faster repository operations?\n(The program will use dnf5 instead of dnf.)",
        "log_dnf5_installed": "dnf5 installed – will be used instead of dnf.",
        "log_dnf5_failed": "dnf5 installation failed – using dnf.",
        "msg_deps_all_installed": "All required packages are installed.",
        "msg_deps_installed_ok": "Missing packages have been installed.",
        "msg_deps_install_failed": "Installation failed. Check the logs.",
        "title_backup": "Backup",
        "msg_backup_select": "Select a backup from the list.",
        "msg_backup_restored": "Restore complete. Restart recommended.",
        "msg_backup_failed": "Restore failed or backup contains no packages.",
        "title_install_in_progress": "Installation in progress",
        "msg_install_in_progress": "Driver installation is in progress.\n\nWait for installation to complete, then close the application.\nClosing during installation may cause a crash.",
        "msg_install_close_anyway": "Installation is in progress.\n\nClose the program anyway?\nInstallation will be interrupted.",
        "title_sudo_required": "Administrator privileges required",
        "msg_sudo_ask": "Driver installation requires administrator privileges (sudo).\n\nDo you want to enter your sudo password now?",
        "title_wrong_password": "Wrong password",
        "msg_wrong_password": "Password is incorrect. Try again.",
        "title_error": "Error",
        "msg_no_password_dialog": "Cannot show password dialog.\nInstall: zenity (sudo apt install zenity) or xterm.",
        "title_wait_sudo": "Waiting for sudo privileges",
        "msg_wait_sudo": "A terminal window has opened.\n\nEnter your password there and press Enter.\n\nThe program will check privileges automatically.",
        "btn_cancel": "Cancel",
        "title_sudo_error": "Privilege error",
        "msg_sudo_failed": "Failed to obtain administrator privileges.\nYou can try again.",
        "title_restart": "Restart",
        "msg_restart_now": "Restart the system now?",
        "title_backup_dialog": "Backup – list and restore",
        "msg_backup_snapshots": "Pre-installation snapshots (date, driver → target):",
        "msg_no_backups": "(no backups)",
        "btn_restore_backup": "Restore selected backup",
        "btn_close": "Close",
        "title_export": "Export",
        "msg_export_ok": "Configuration has been saved.",
        "title_import": "Import",
        "msg_import_ok": "Configuration has been loaded.",
        "pwd_dialog_label": "Enter administrator password (sudo):",
        "pwd_placeholder": "Password",
        "save_log_title": "Save logs",
        "install_history_title": "Install history",
        "install_history_label": "Date, type, version, success:",
    },
}


def _get_app_icon_path() -> Optional[Path]:
    """Ścieżka do ikony aplikacji: app_icon.* (onefile) lub *_icon.png obok programu."""
    # Onefile: ikona dołączona przez Nuitka obok binarki (katalog tymczasowy lub katalog z exe)
    if getattr(sys, "frozen", False) or _is_onefile_tmp():
        exe_dir = Path(sys.executable).resolve().parent
        for ext in (".png", ".ico"):
            p = exe_dir / f"app_icon{ext}"
            if p.exists():
                return p
    # Ikona obok skryptu / w katalogu programu
    for name in ("app_icon.png", "app_icon.ico", "nvidia_driver_manager_icon.png"):
        p = SCRIPT_DIR / name
        if p.exists():
            return p
    for p in SCRIPT_DIR.glob("*_icon.png"):
        if p.is_file():
            return p
    for p in SCRIPT_DIR.glob("*_icon.ico"):
        if p.is_file():
            return p
    return None


# Wykryj system operacyjny
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

if IS_LINUX:
    INSTALL_DIR = Path("/opt/nvidia-installer")
    SYSTEM_RUN_INSTALL_DIR = "/usr/local/lib/nvidia-run-install"
else:
    INSTALL_DIR = SCRIPT_DIR / "install"
    SYSTEM_RUN_INSTALL_DIR = ""

# Tryb demo dla Windows
DEMO_MODE = IS_WINDOWS

# Fallback wersje
PRODUCTION_VERSION = "580.126.09"
NEW_FEATURE_VERSION = "590.48.01"
BETA_VERSION = "575.54.14"
LEGACY_VERSION = "470.256.02"


def strip_ansi(text: str) -> str:
    """Usuwa kody ANSI (kolory/formatowanie) z tekstu – dla wyjścia inxi w skompilowanym programie (brak TTY)."""
    if not text:
        return text
    # ESC [ ... m (SGR) oraz inne sekwencje CSI
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# ============================================================================
# KLASA SYSTEMOWA - OPERACJE NA SYSTEMIE
# ============================================================================

class SystemManager:
    """Zarządza operacjami systemowymi i wykrywaniem"""
    
    def __init__(self):
        self.demo_mode = DEMO_MODE
        self.distro_name = "Unknown"
        self.distro_family = "unknown"
        self.nvidia_arch = self._detect_arch()
        self.gpu_present = False
        self.gpu_model = ""
        self.current_driver = "brak"
        self._fedora_repo_version_cache = None  # po pierwszym wywołaniu: "" lub "570.144"
        self._dnf_cmd: Optional[str] = None  # "dnf5" lub "dnf" (Fedora)

    def get_dnf_cmd(self) -> str:
        """Na Fedorze zwraca dnf5 jeśli jest dostępny (szybszy), inaczej dnf."""
        if self.distro_family != "fedora":
            return "dnf"
        if self._dnf_cmd is not None:
            return self._dnf_cmd
        if self.demo_mode:
            self._dnf_cmd = "dnf"
            return self._dnf_cmd
        rc = self.run_command(["which", "dnf5"], sudo=False, timeout=2)[0]
        self._dnf_cmd = "dnf5" if rc == 0 else "dnf"
        return self._dnf_cmd

    def _detect_arch(self) -> str:
        """Wykrywa architekturę systemu"""
        if self.demo_mode:
            return "Linux-x86_64"
        try:
            arch = os.uname().machine
            if arch == "x86_64":
                return "Linux-x86_64"
            elif arch == "aarch64":
                return "Linux-aarch64"
            else:
                return f"Linux-{arch}"
        except:
            return "Linux-x86_64"  # Fallback
    
    def detect_distro(self):
        """Wykrywa dystrybucję Linuxa"""
        if self.demo_mode:
            self.distro_name = "Windows"
            self.distro_family = "windows"
            return
        
        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.startswith("ID="):
                        distro_id = line.split("=")[1].strip().strip('"')
                        if distro_id in ["ubuntu", "kubuntu", "lubuntu", "xubuntu", 
                                        "pop", "linuxmint", "zorin", "elementary", "neon"]:
                            self.distro_family = "ubuntu"
                        elif distro_id == "debian":
                            self.distro_family = "debian"
                        elif distro_id in ["fedora", "rhel", "centos", "rocky", "alma"]:
                            self.distro_family = "fedora"
                        else:
                            self.distro_family = "other"
                    elif line.startswith("NAME="):
                        self.distro_name = line.split("=")[1].strip().strip('"')
        except:
            self.distro_family = "unknown"
            self.distro_name = "Unknown"
    
    def check_gpu(self):
        """Sprawdza obecność GPU NVIDIA"""
        if self.demo_mode:
            self.gpu_present = True
            self.gpu_model = "NVIDIA GeForce RTX 3060"
            return
        
        try:
            result = self.run_command(["lspci"], sudo=True)
            if result[0] == 0:
                for line in result[1].split("\n"):
                    if "nvidia" in line.lower() and ("vga" in line.lower() or 
                                                     "3d" in line.lower() or 
                                                     "display" in line.lower()):
                        self.gpu_present = True
                        self.gpu_model = line.split(":")[-1].strip()
                        return
            # Fallback bez sudo
            result = self.run_command(["lspci"], sudo=False)
            if result[0] == 0:
                for line in result[1].split("\n"):
                    if "nvidia" in line.lower() and ("vga" in line.lower() or 
                                                     "3d" in line.lower() or 
                                                     "display" in line.lower()):
                        self.gpu_present = True
                        self.gpu_model = line.split(":")[-1].strip()
                        return
        except:
            pass
        self.gpu_present = False
        self.gpu_model = ""
    
    def get_current_driver(self) -> str:
        """Zwraca aktualnie zainstalowany sterownik"""
        if self.demo_mode:
            return "550.90.07"
        
        # Sprawdź nvidia-smi
        result = self.run_command(["nvidia-smi", "--query-gpu=driver_version", 
                                   "--format=csv,noheader"], sudo=False)
        if result[0] == 0 and result[1].strip() and result[1].strip() != "N/A":
            return result[1].strip().split("\n")[0]
        
        # Sprawdź nouveau
        try:
            with open("/proc/modules", "r") as f:
                if "nouveau" in f.read():
                    return "nouveau"
        except:
            pass
        
        return "brak"
    
    def run_command(self, cmd: List[str], sudo: bool = False,
                    timeout: int = 300,
                    sudo_password: Optional[str] = None) -> Tuple[int, str, str]:
        """Wykonuje komendę systemową. Gdy sudo=True i podano sudo_password, używa sudo -S (stdin) – potrzebne m.in. przy sudo-rs, gdzie cache nie jest współdzielony z procesami potomnymi."""
        if self.demo_mode:
            return (0, f"Komenda: {' '.join(cmd)}", "")
        
        if sudo:
            if sudo_password is not None:
                cmd = ["sudo", "-S"] + list(cmd)
            else:
                cmd = ["sudo"] + list(cmd)
        
        try:
            kwargs = dict(
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if sudo and sudo_password is not None:
                kwargs["input"] = (sudo_password + "\n")
            process = subprocess.run(cmd, **kwargs)
            return (process.returncode, process.stdout or "", process.stderr or "")
        except subprocess.TimeoutExpired:
            return (124, "", "Timeout")
        except Exception as e:
            return (1, "", str(e))
    
    def check_secure_boot(self) -> bool:
        """Sprawdza czy Secure Boot jest włączony"""
        result = self.run_command(["mokutil", "--sb-state"], sudo=False)
        if result[0] == 0:
            return "enabled" in result[1].lower()
        return False
    
    def fetch_versions(self) -> Dict[str, str]:
        """Pobiera najnowsze wersje z serwera NVIDIA"""
        versions = {
            "production": PRODUCTION_VERSION,
            "new_feature": NEW_FEATURE_VERSION,
            "beta": BETA_VERSION,
            "legacy": LEGACY_VERSION
        }
        
        if self.demo_mode:
            return versions  # W trybie demo zwracamy fallback wersje
        
        url = f"https://download.nvidia.com/XFree86/{self.nvidia_arch}/"
        
        # Spróbuj pobrać przez curl lub wget
        for tool in ["curl", "wget"]:
            result = self.run_command([tool, "-s", url], sudo=False, timeout=10)
            if result[0] == 0 and result[1]:
                content = result[1]
                
                # Parsuj wersje
                # Production: 580.x
                prod_match = re.findall(r"58[0-9]\.[0-9]+\.[0-9]+/", content)
                if prod_match:
                    versions["production"] = sorted(prod_match, 
                    key=lambda x: [int(i) for i in x.rstrip("/").split(".")])[-1].rstrip("/")
                
                # New Feature: 590.45+
                newf_match = re.findall(r"590\.(?:4[5-9]|[5-9][0-9]|[0-9]{3,})\.[0-9]+/", content)
                if newf_match:
                    versions["new_feature"] = sorted(newf_match,
                    key=lambda x: [int(i) for i in x.rstrip("/").split(".")])[-1].rstrip("/")
                
                # Beta: 590.00-590.44
                beta_match = re.findall(r"590\.(?:[0-3][0-9]|4[0-4])\.[0-9]+/", content)
                if beta_match:
                    versions["beta"] = sorted(beta_match,
                    key=lambda x: [int(i) for i in x.rstrip("/").split(".")])[-1].rstrip("/")
                
                # Legacy: 470.x
                legacy_match = re.findall(r"470\.[0-9]+\.[0-9]+/", content)
                if legacy_match:
                    versions["legacy"] = sorted(legacy_match,
                    key=lambda x: [int(i) for i in x.rstrip("/").split(".")])[-1].rstrip("/")
                
                break
        
        return versions
    
    def highest_repo_driver(self) -> str:
        """Znajduje przedostatnią najwyższą wersję w repo"""
        if self.demo_mode:
            return "580.126.09"
        
        if self.distro_family == "fedora":
            ver = self._fedora_repo_driver_version()
            return ver if ver else "580"
        
        available = []
        for v in [610, 600, 590, 580, 550, 535, 525, 515]:
            result = self.run_command(["apt-cache", "show", f"nvidia-driver-{v}-open"], 
                                     sudo=False)
            if result[0] == 0:
                for line in result[1].split("\n"):
                    if line.startswith("Version:"):
                        version = line.split(":")[1].strip().split("-")[0]
                        available.append((v, version))
                        break
        
        if len(available) >= 2:
            return available[1][1] if "." in available[1][1] else str(available[1][0])
        elif len(available) == 1:
            return available[0][1] if "." in available[0][1] else str(available[0][0])
        return "580"
    
    def _fedora_repo_driver_version(self) -> str:
        """Wersja akmod-nvidia z repo (Fedora/RPM Fusion). Zwraca np. 570.144 lub pusty string. Wynik cache'owany (jedno wywołanie dnf przy starcie)."""
        if self._fedora_repo_version_cache is not None:
            return self._fedora_repo_version_cache
        dnf = self.get_dnf_cmd()
        result = self.run_command(
            ["env", "DNF_FRONTEND=noninteractive", dnf, "list", "available", "akmod-nvidia", "-q"],
            sudo=False, timeout=60
        )
        ver = ""
        if result[0] == 0 and result[1]:
            for line in result[1].split("\n"):
                if "akmod-nvidia" in line and ".x86_64" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        ver = parts[1].split("-")[0]
                        if "." in ver:
                            break
                    ver = ""
                    break
        self._fedora_repo_version_cache = ver
        return ver
    
    def highest_repo_driver_latest(self) -> str:
        """Znajduje najwyższą wersję w repo"""
        if self.demo_mode:
            return "590.48.01"
        
        if self.distro_family == "fedora":
            ver = self._fedora_repo_driver_version()
            return ver if ver else "580"
        
        for v in [610, 600, 590, 580, 550, 535, 525, 515]:
            result = self.run_command(["apt-cache", "show", f"nvidia-driver-{v}-open"], 
                                     sudo=False)
            if result[0] == 0:
                for line in result[1].split("\n"):
                    if line.startswith("Version:"):
                        version = line.split(":")[1].strip().split("-")[0]
                        return version if "." in version else str(v)
        return "580"

    def get_missing_dependency_packages(self, install_type: str) -> List[str]:
        """Zwraca listę brakujących pakietów (linux-headers, dkms, build-essential) dla repo/run."""
        if self.demo_mode or install_type not in ("repo", "run"):
            return []
        missing = []
        if self.distro_family == "fedora":
            result = self.run_command(["rpm", "-q", "kernel-devel"], sudo=False)
            if result[0] != 0:
                missing.append("kernel-devel")
            result = self.run_command(["rpm", "-q", "gcc"], sudo=False)
            if result[0] != 0:
                missing.append("gcc")
            return missing
        try:
            kernel = os.uname().release
        except Exception:
            kernel = "unknown"
        result = self.run_command(["dpkg", "-l", f"linux-headers-{kernel}"], sudo=False)
        if result[0] != 0:
            missing.append(f"linux-headers-{kernel}")
        result = self.run_command(["dpkg", "-l", "dkms"], sudo=False)
        if result[0] != 0:
            missing.append("dkms")
        result = self.run_command(["dpkg", "-l", "build-essential"], sudo=False)
        if result[0] != 0:
            missing.append("build-essential")
        return missing

    def get_installed_nvidia_packages(self) -> List[str]:
        """Zwraca listę zainstalowanych pakietów NVIDIA (do backupu)."""
        if self.demo_mode:
            return []
        if self.distro_family == "fedora":
            result = self.run_command(["rpm", "-qa"], sudo=False)
            if result[0] != 0:
                return []
            packages = []
            for line in result[1].split("\n"):
                if line and ("nvidia" in line.lower() or "akmod-nvidia" in line):
                    pkg = line.strip()
                    if "nvidia-gpu-firmware" in pkg:
                        continue
                    packages.append(pkg)
            return packages
        result = self.run_command(["dpkg", "-l"], sudo=False)
        if result[0] != 0:
            return []
        packages = []
        for line in result[1].split("\n"):
            if line.startswith("ii") and ("nvidia" in line.lower() or
                                          "libnvidia" in line.lower() or
                                          "linux-modules-nvidia" in line.lower()):
                pkg = line.split()[1]
                packages.append(pkg)
        return packages

    def get_installed_nvidia_driver_package(self) -> Optional[str]:
        """Zwraca nazwę pakietu sterownika z repo (nvidia-driver-XXX-open / akmod-nvidia) jeśli zainstalowany."""
        if self.demo_mode:
            return None
        if self.distro_family == "fedora":
            result = self.run_command(["rpm", "-q", "akmod-nvidia"], sudo=False)
            if result[0] == 0 and result[1].strip():
                return "akmod-nvidia"
            return None
        result = self.run_command(["dpkg", "-l"], sudo=False)
        if result[0] != 0:
            return None
        for line in result[1].split("\n"):
            if line.startswith("ii") and "nvidia-driver-" in line and "-open" in line:
                return line.split()[1]
        return None


# ============================================================================
# WĄTEK WYKONYWANIA KOMEND
# ============================================================================

class CommandThread(QThread):
    """Wątek do wykonywania długotrwałych operacji"""
    output = Signal(str)  # Emituje linie wyjścia
    finished = Signal(int)  # Emituje kod wyjścia
    error = Signal(str)  # Emituje błędy
    
    def __init__(self, cmd: List[str], sudo: bool = False):
        super().__init__()
        self.cmd = cmd
        self.sudo = sudo
    
    def run(self):
        if self.sudo:
            cmd = ["sudo"] + self.cmd
        else:
            cmd = self.cmd
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in iter(process.stdout.readline, ''):
                if line:
                    self.output.emit(line.rstrip())
            
            process.wait()
            self.finished.emit(process.returncode)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(1)


# ============================================================================
# WĄTEK POBRANIA WERSJI REPO (FEDORA – bez blokowania GUI)
# ============================================================================

class FetchFedoraRepoThread(QThread):
    """Pobiera wersję akmod-nvidia w tle; na Fedorze dnf może długo trwać."""
    version_ready = Signal(str)

    def __init__(self, system):
        super().__init__()
        self.system = system

    def run(self):
        ver = self.system._fedora_repo_driver_version()
        self.version_ready.emit(ver if ver else "580")


# ============================================================================
# WĄTEK INSTALACJI
# ============================================================================

class InstallationThread(QThread):
    """Wątek do wykonywania instalacji sterowników"""
    output = Signal(str, str)  # (message, level)
    finished = Signal(int)  # kod wyjścia
    ask_restart = Signal()  # pyta o restart
    progress = Signal(int)  # 0–100, szacowany postęp instalacji (testowo)
    
    def __init__(self, window, install_type: str, params: Dict):
        super().__init__()
        self.window = window
        self.system = window.system
        self.install_type = install_type
        self.params = params
        self.restart_needed = False
    
    def _ensure_dependencies(self):
        """Sprawdza i doinstalowuje linux-headers, dkms, build-essential (Debian) lub kernel-devel, gcc (Fedora) przed instalacją repo/run."""
        missing = self.system.get_missing_dependency_packages(self.install_type)
        if not missing:
            return True
        self.log(self.window._tr("log_installing_deps").format(", ".join(missing)), "INFO")
        if self.system.distro_family == "fedora":
            rc, _ = self.run_cmd([self.system.get_dnf_cmd(), "install", "-y"] + missing, sudo=True, silent=True)
        else:
            rc, _ = self.run_cmd(["apt-get", "update", "-y"], sudo=True, silent=True)
            if rc != 0:
                self.log(self.window._tr("log_update_repo_failed"), "WARN")
            rc, _ = self.run_cmd(["apt-get", "install", "-y"] + missing, sudo=True, silent=True)
        if rc != 0:
            self.log(self.window._tr("log_install_deps_failed"), "ERROR")
            return False
        self.log(self.window._tr("log_deps_installed"), "SUCCESS")
        return True

    def install_uninstall(self):
        """Usuwa sterownik NVIDIA i przywraca nouveau (bez instalacji NVK)."""
        if self.system.demo_mode:
            self.output.emit(self.window._tr("log_linux_only_short"), "WARN")
            self.finished.emit(0)
            return
        self.log(self.window._tr("log_remove_nvidia_header"), "INFO")
        self.progress.emit(15)
        self.log(self.window._tr("log_cleaning_nvidia"), "INFO")
        self.clean_nvidia_artifacts()
        self.purge_nvidia_packages()
        self.remove_dkms_modules()
        self.remove_nvidia_configs()
        self.remove_nvidia_libraries()
        self.progress.emit(50)
        if not self.verify_nvidia_removal():
            self.log(self.window._tr("log_nvidia_libs_visible"), "WARN")
        self.log(self.window._tr("log_config_nouveau"), "INFO")
        self.configure_nouveau_for_nvk()
        self.rebuild_initramfs()
        self.progress.emit(100)
        self.log(self.window._tr("log_nvidia_removed"), "SUCCESS")
        self.restart_needed = True
        self.ask_restart.emit()
        self.finished.emit(0)

    def install_upgrade_repo(self):
        """Aktualizuje sterownik NVIDIA z repo (apt/dnf update + upgrade pakietu)."""
        if self.system.demo_mode:
            self.output.emit(self.window._tr("log_linux_only_short"), "WARN")
            self.finished.emit(0)
            return
        pkg = self.system.get_installed_nvidia_driver_package()
        if not pkg:
            self.log(self.window._tr("log_no_driver_repo"), "WARN")
            self.finished.emit(0)
            return
        self.log(self.window._tr("log_updating_repo_pkg").format(pkg), "INFO")
        self.progress.emit(20)
        self._ensure_network()
        if self.system.distro_family == "fedora":
            rc, _ = self.run_cmd([self.system.get_dnf_cmd(), "upgrade", "-y", pkg], sudo=True, silent=True)
        else:
            rc, _ = self.run_cmd(["apt-get", "update", "-y"], sudo=True, silent=True)
            if rc != 0:
                self.log(self.window._tr("log_update_repo_failed"), "ERROR")
                self.finished.emit(1)
                return
            rc, _ = self.run_cmd(["apt-get", "install", "--only-upgrade", "-y", pkg], sudo=True, silent=True)
        if rc == 0:
            self.progress.emit(100)
            self.log(self.window._tr("log_driver_updated").format(pkg), "SUCCESS")
            self.restart_needed = True
            self.ask_restart.emit()
            self.finished.emit(0)
        else:
            self.log(self.window._tr("log_update_failed"), "ERROR")
            self.finished.emit(1)

    def run(self):
        """Główna metoda wątku"""
        try:
            if self.install_type == "nvk":
                self.install_nvk()
            elif self.install_type == "uninstall":
                self.install_uninstall()
            elif self.install_type == "repo":
                if not self._ensure_dependencies():
                    self.finished.emit(1)
                    return
                self.install_repo()
            elif self.install_type == "run":
                if not self._ensure_dependencies():
                    self.finished.emit(1)
                    return
                self.install_nvidia_run()
            elif self.install_type == "upgrade_repo":
                self.install_upgrade_repo()
            else:
                self.output.emit(self.window._tr("log_unknown_install"), "ERROR")
                self.finished.emit(1)
        except Exception as e:
            self.output.emit(self.window._tr("log_error_exception").format(str(e)), "ERROR")
            
            # Zbierz szczegółowy raport błędu
            try:
                report = self.window.collect_error_report(str(e), f"InstallationThread: {self.install_type}")
                error_file = self.window.save_error_report(report)
                if error_file:
                    self.output.emit(self.window._tr("log_error_report_saved").format(error_file), "INFO")
            except:
                pass
            
            self.finished.emit(1)
    
    def log(self, message: str, level: str = "INFO"):
        """Wysyła wiadomość do głównego okna"""
        self.output.emit(message, level)

    def _ensure_network(self):
        """Sprawdza sieć (jak ensure_network w driver-manager-v2.sh) – tylko ostrzeżenie."""
        rc, _ = self.run_cmd(["ping", "-c", "1", "-W", "2", "8.8.8.8"], sudo=False, silent=True, timeout=5)
        if rc != 0:
            self.log(self.window._tr("log_no_network"), "WARN")

    def _check_secure_boot(self):
        """Ostrzeżenie jeśli Secure Boot włączony (jak check_secure_boot w .sh)."""
        rc, out = self.run_cmd(["mokutil", "--sb-state"], sudo=False, silent=True, timeout=5)
        if rc == 0 and out and "enabled" in (out or "").lower():
            self.log(self.window._tr("log_secure_boot"), "WARN")
            self.log(self.window._tr("log_secure_boot_advice"), "WARN")
    
    def _ensure_build_requirements(self) -> bool:
        """Sprawdza dkms, linux-headers, build-essential (Debian) lub kernel-devel, gcc (Fedora); doinstalowuje brakujące. Zwraca True jeśli ok."""
        if self.system.distro_family == "fedora":
            to_install = []
            rc, _ = self.run_cmd(["rpm", "-q", "kernel-devel"], sudo=False, silent=True)
            if rc != 0:
                to_install.append("kernel-devel")
            rc, _ = self.run_cmd(["rpm", "-q", "gcc"], sudo=False, silent=True)
            if rc != 0:
                to_install.append("gcc")
            if not to_install:
                return True
            self.log(self.window._tr("log_installing_missing").format(", ".join(to_install)), "INFO")
            rc, _ = self.run_cmd([self.system.get_dnf_cmd(), "install", "-y"] + to_install, sudo=True, silent=True, timeout=300)
            if rc != 0:
                self.log(self.window._tr("log_deps_install_failed"), "ERROR")
                return False
            self.log(self.window._tr("log_deps_install_ok"), "SUCCESS")
            return True
        try:
            kernel = os.uname().release
        except Exception:
            kernel = "unknown"
        to_install = []
        rc, _ = self.run_cmd(["which", "dkms"], sudo=False, silent=True)
        if rc != 0:
            to_install.append("dkms")
        rc, _ = self.run_cmd(["dpkg", "-l", f"linux-headers-{kernel}"], sudo=False, silent=True)
        if rc != 0:
            to_install.append(f"linux-headers-{kernel}")
        rc, _ = self.run_cmd(["dpkg", "-l", "build-essential"], sudo=False, silent=True)
        if rc != 0:
            to_install.append("build-essential")
        if not to_install:
            return True
        self.log(self.window._tr("log_installing_missing").format(", ".join(to_install)), "INFO")
        rc, _ = self.run_cmd(["apt-get", "update", "-y"], sudo=True, silent=True, timeout=120)
        if rc != 0:
            self.log(self.window._tr("log_update_repo_failed"), "ERROR")
            return False
        rc, _ = self.run_cmd(["apt-get", "install", "-y"] + to_install, sudo=True, silent=True, timeout=300)
        if rc != 0:
            self.log(self.window._tr("log_deps_install_failed"), "ERROR")
            return False
        self.log(self.window._tr("log_deps_install_ok"), "SUCCESS")
        return True
    
    def run_cmd(self, cmd: List[str], sudo: bool = False, 
                timeout: int = 300, silent: bool = False,
                ignore_missing_unit: bool = False,
                ignore_stderr_contains: Optional[str] = None) -> Tuple[int, str]:
        """Wykonuje komendę i loguje wynik.
        ignore_missing_unit: nie traktuj jako błąd gdy systemctl zwraca „unit not loaded”/„does not exist”.
        ignore_stderr_contains: nie traktuj jako błąd gdy stderr zawiera ten tekst (np. DKMS „not located in the DKMS tree”)."""
        sudo_password = self.params.get("sudo_password")
        result = self.system.run_command(cmd, sudo=sudo, timeout=timeout, sudo_password=sudo_password)
        rc, stdout, stderr = result[0], result[1], result[2] or ""
        
        if rc == 0:
            return rc, stdout
        
        if ignore_missing_unit and ("not loaded" in stderr or "does not exist" in stderr):
            return 0, stdout
        if ignore_stderr_contains and ignore_stderr_contains in stderr:
            return 0, stdout
        
        self.log(self.window._tr("log_error_code").format(rc), "ERROR")
        if stderr:
            for line in stderr.split("\n"):
                if line.strip():
                    self.log(f"  {line}", "ERROR")
        
        return rc, stdout
    
    def install_nvk(self):
        """Instaluje NVK"""
        if self.system.demo_mode:
            self.output.emit(self.window._tr("log_linux_only"), "WARN")
            self.finished.emit(0)
            return
        
        self.log(self.window._tr("log_install_nvk_header"), "INFO")
        self.progress.emit(5)
        # Czyszczenie (kolejność jak w driver-manager-v2.sh)
        self.log(self.window._tr("log_cleaning_nvidia"), "INFO")
        self.clean_nvidia_artifacts()
        self.purge_nvidia_packages()
        self.remove_dkms_modules()
        self.remove_nvidia_configs()
        self.remove_nvidia_libraries()
        if not self.verify_nvidia_removal():
            if self.system.distro_family == "fedora":
                self.log(self.window._tr("log_nvidia_libs_cache_info"), "INFO")
            else:
                self.log(self.window._tr("log_nvidia_libs_visible"), "WARN")
        self.progress.emit(20)
        # Konfiguracja nouveau
        self.log(self.window._tr("log_config_nouveau"), "INFO")
        self.configure_nouveau_for_nvk()
        self.progress.emit(30)
        # Instalacja pakietów
        self.log(self.window._tr("log_install_mesa_nvk"), "INFO")
        if not self.install_nvk_packages():
            self.log(self.window._tr("log_nvk_install_error"), "ERROR")
            self.finished.emit(1)
            return
        self.progress.emit(55)
        # Na Fedorze: dracut dopiero po instalacji pakietów (firmware GSP musi być w systemie przed budową initramfs)
        if self.system.distro_family == "fedora":
            self.rebuild_initramfs()
        # Reinstalacja środowiska graficznego – tylko na Debian/Ubuntu (na Fedorze pomijamy, żeby nie nadpisać działającej konfiguracji z czystej instalacji)
        if self.system.distro_family != "fedora":
            self.reinstall_plasma_and_mesa()
            self.configure_sddm_for_wayland()
        self.progress.emit(75)
        # Weryfikacja
        self.verify_nvk_installation()
        self.progress.emit(90)
        self.log(self.window._tr("log_nvk_installed"), "SUCCESS")
        self.log(self.window._tr("log_reboot_notice"), "INFO")
        self._create_nvk_reboot_service()
        self.progress.emit(100)
        self.restart_needed = True
        self.ask_restart.emit()
        self.finished.emit(0)
    
    def _create_nvk_reboot_service(self):
        """Tworzy serwis drugiego restartu dla NVK (jak w driver-manager-v2.sh)."""
        service_path = "/etc/systemd/system/nvk-check-reboot.service"
        content = """[Unit]
Description=NVK check and reboot if needed
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'sleep 10; if lsmod | grep -q nvidia; then echo "Resztki NVIDIA wykryte - drugi restart..."; reboot; fi; systemctl disable nvk-check-reboot.service || true'
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
"""
        tmp = Path("/tmp/nvk-check-reboot.service")
        with open(tmp, "w") as f:
            f.write(content)
        self.run_cmd(["cp", str(tmp), service_path], sudo=True, silent=True)
        self.run_cmd(["systemctl", "daemon-reload"], sudo=True, silent=True)
        self.run_cmd(["systemctl", "enable", "nvk-check-reboot.service"], sudo=True, silent=True)
        try:
            tmp.unlink()
        except OSError:
            pass
    
    def install_repo(self):
        """Instaluje z repo (zgodnie z driver-manager-v2.sh: ensure_network, check_secure_boot, clean, headers, PPA, update, install)"""
        if self.system.demo_mode:
            self.output.emit(self.window._tr("log_linux_only"), "WARN")
            self.finished.emit(0)
            return
        
        version = self.params.get("version", "580")
        package = self.params.get("package", "nvidia-driver-580-open")
        
        self.log(self.window._tr("log_install_repo_header").format(version), "INFO")
        if not self._ensure_build_requirements():
            self.finished.emit(1)
            return
        self._ensure_network()
        self._check_secure_boot()
        
        if self.system.distro_family == "fedora":
            self.progress.emit(5)
            self.log(self.window._tr("log_cleaning"), "INFO")
            self.clean_nvidia_artifacts()
            self.remove_dkms_modules()
            self.purge_nvidia_packages()
            dnf = self.system.get_dnf_cmd()
            self.run_cmd([dnf, "install", "-y", "kernel-devel"], sudo=True, silent=True)
            self.progress.emit(25)
            self.log(self.window._tr("log_updating_repos"), "INFO")
            self.run_cmd([dnf, "makecache", "-q"], sudo=True, silent=True)
            rc_rpmfusion, _ = self.run_cmd(["rpm", "-q", "rpmfusion-nonfree-release"], sudo=False, silent=True)
            if rc_rpmfusion != 0:
                self.log("RPM Fusion nonfree: instalacja repozytorium...", "INFO")
                res = self.system.run_command(["rpm", "-E", "%{fedora}"], sudo=False)
                ver = res[1].strip() if res[0] == 0 and res[1] else ""
                if ver and ver.isdigit():
                    rpmfusion_url = f"https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{ver}.noarch.rpm"
                else:
                    res = self.system.run_command(["rpm", "-E", "%{rhel}"], sudo=False)
                    rhel_ver = res[1].strip() if res[0] == 0 and res[1] else "9"
                    rpmfusion_url = f"https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-{rhel_ver}.noarch.rpm"
                self.run_cmd([dnf, "install", "-y", rpmfusion_url], sudo=True, silent=True)
            self.progress.emit(40)
            self.log(self.window._tr("log_installing_pkg").format("akmod-nvidia"), "INFO")
            rc, _ = self.run_cmd([dnf, "install", "-y", "akmod-nvidia", "xorg-x11-drv-nvidia", "xorg-x11-drv-nvidia-cuda"], sudo=True, silent=True)
            if rc == 0:
                self.progress.emit(75)
                self.log(self.window._tr("log_driver_installed").format("akmod-nvidia"), "SUCCESS")
                self.log(self.window._tr("log_blocking_nouveau"), "INFO")
                self.block_nouveau()
                self.rebuild_initramfs()
                self.progress.emit(100)
                self.restart_needed = True
                self.ask_restart.emit()
                self.finished.emit(0)
            else:
                self.finished.emit(1)
            return
        
        # Czyszczenie (kolejność jak w .sh)
        self.progress.emit(10)
        self.log(self.window._tr("log_cleaning"), "INFO")
        self.clean_nvidia_artifacts()
        self.remove_dkms_modules()
        self.purge_nvidia_packages()
        self.progress.emit(25)
        # Instalacja headers (ensure_headers)
        try:
            kernel = os.uname().release
        except:
            kernel = "unknown"
        self.run_cmd(["apt-get", "install", "-y", f"linux-headers-{kernel}"], 
                    sudo=True, silent=True)
        
        # Usuń PPA kisak
        self.run_cmd(["add-apt-repository", "-r", "-y", "ppa:kisak/kisak-mesa"], 
                    sudo=True, silent=True)
        
        # Update i instalacja
        self.log(self.window._tr("log_updating_repos"), "INFO")
        self.run_cmd(["apt-get", "update", "-y"], sudo=True, silent=True)
        self.progress.emit(50)
        self.log(self.window._tr("log_installing_pkg").format(package), "INFO")
        rc, _ = self.run_cmd(["apt-get", "install", "-y", package], sudo=True, silent=True)
        
        if rc == 0:
            self.progress.emit(85)
            self.log(self.window._tr("log_driver_installed").format(package), "SUCCESS")
            self.log(self.window._tr("log_blocking_nouveau"), "INFO")
            self.block_nouveau()
            self.rebuild_initramfs()
            self.progress.emit(100)
            self.restart_needed = True
            self.ask_restart.emit()
            self.finished.emit(0)
        else:
            self.log(self.window._tr("log_install_pkg_error").format(package), "ERROR")
            self.finished.emit(1)
    
    def install_nvidia_run(self):
        """Instaluje sterownik .run"""
        if self.system.demo_mode:
            self.output.emit(self.window._tr("log_linux_only"), "WARN")
            self.finished.emit(0)
            return
        
        version = self.params.get("version", PRODUCTION_VERSION)
        label = self.params.get("label", "Production")
        
        self.log(self.window._tr("log_install_run_header").format(label, version), "INFO")
        self.progress.emit(5)
        if not self._ensure_build_requirements():
            self.finished.emit(1)
            return
        
        # Pobierz plik
        run_file = CACHE_DIR / f"NVIDIA-{version}.run"
        if not run_file.exists() or run_file.stat().st_size < 50000000:
            self.log(self.window._tr("log_downloading_run"), "INFO")
            if not self.download_nvidia_run(version):
                self.log(self.window._tr("log_download_run_failed"), "ERROR")
                self.finished.emit(1)
                return
        self.progress.emit(20)
        # Przygotowanie
        self.log(self.window._tr("log_preparing_system"), "INFO")
        self.clean_nvidia_artifacts()
        self.remove_dkms_modules()
        self.purge_nvidia_packages()
        self.progress.emit(40)
        # Blokowanie nouveau
        self.block_nouveau()
        self.rebuild_initramfs()
        self.progress.emit(55)
        # Kopiuj plik
        system_run = INSTALL_DIR / f"NVIDIA-{version}.run"
        self.run_cmd(["mkdir", "-p", str(INSTALL_DIR)], sudo=True, silent=True)
        self.run_cmd(["cp", str(run_file), str(system_run)], sudo=True)
        self.run_cmd(["chmod", "755", str(system_run)], sudo=True)
        self.progress.emit(75)
        # Generuj skrypt instalacyjny (log w /var/log przy starcie – SELinux i brak user dir)
        self.generate_install_script(version, label, system_run, log_file="/var/log/nvidia-run-install.log")
        # Skrypt w katalogu systemowym – żeby SELinux nie blokował wykonania przy starcie
        if IS_LINUX and SYSTEM_RUN_INSTALL_DIR:
            self.run_cmd(["mkdir", "-p", SYSTEM_RUN_INSTALL_DIR], sudo=True, silent=True)
            self.run_cmd(["cp", str(INSTALL_SCRIPT_DIR / "run-install-v2.sh"), f"{SYSTEM_RUN_INSTALL_DIR}/run-install-v2.sh"], sudo=True, silent=True)
            self.run_cmd(["chmod", "+x", f"{SYSTEM_RUN_INSTALL_DIR}/run-install-v2.sh"], sudo=True, silent=True)
            if self.system.distro_family == "fedora":
                self.run_cmd(["restorecon", "-v", f"{SYSTEM_RUN_INSTALL_DIR}/run-install-v2.sh"], sudo=True, silent=True)
        # Generuj systemd service
        self.generate_systemd_service()
        self.progress.emit(100)
        self.log(self.window._tr("log_prepare_done_reboot"), "SUCCESS")
        self.restart_needed = True
        self.ask_restart.emit()
        self.finished.emit(0)
    
    def download_nvidia_run(self, version: str) -> bool:
        """Pobiera plik .run"""
        url = f"https://us.download.nvidia.com/XFree86/{self.system.nvidia_arch}/{version}/NVIDIA-{self.system.nvidia_arch}-{version}.run"
        out_file = CACHE_DIR / f"NVIDIA-{version}.run"
        
        for tool in ["wget", "curl"]:
            if tool == "wget":
                cmd = ["wget", "-O", str(out_file), url, "--progress=dot:giga"]
            else:
                cmd = ["curl", "-L", "-o", str(out_file), url, "--progress-bar"]
            
            rc, _ = self.run_cmd(cmd, sudo=False, timeout=600)
            if rc == 0 and out_file.exists() and out_file.stat().st_size > 50000000:
                self.log(self.window._tr("log_downloaded").format(out_file), "SUCCESS")
                return True
        
        return False
    
    def clean_nvidia_artifacts(self):
        """Czyści artefakty NVIDIA (zgodnie z driver-manager-v2.sh)"""
        configs = [
            "/etc/modprobe.d/blacklist-nouveau.conf",
            "/etc/modprobe.d/nvidia*.conf",
            "/etc/modprobe.d/disable-nvidia.conf",
            "/etc/X11/xorg.conf",
            "/etc/X11/xorg.conf.nvidia-xconfig-original",
        ]
        for cfg in configs:
            self.run_cmd(["rm", "-f", cfg], sudo=True, silent=True)
        # Dodatkowe ścieżki jak w skrypcie .sh (globy przez sh -c)
        self.run_cmd(["sh", "-c", "rm -f /etc/ld.so.conf.d/*nvidia*"], sudo=True, silent=True)
        self.run_cmd(["sh", "-c", "rm -f /etc/X11/xorg.conf.d/*nvidia*"], sudo=True, silent=True)
        self.run_cmd(["sh", "-c", "rm -f /usr/share/X11/xorg.conf.d/*nvidia*"], sudo=True, silent=True)
        
        # Systemd services (brak usługi = OK, nie przerywamy)
        services = ["nvidia-persistenced", "nvidia-powerd", "nvidia-suspend", 
                   "nvidia-resume", "nvidia-hibernate", "nvidia-driver-install", "nvidia-run-install", "nvk-install"]
        for svc in services:
            self.run_cmd(["systemctl", "stop", f"{svc}.service"], sudo=True, silent=True, ignore_missing_unit=True)
            self.run_cmd(["systemctl", "disable", f"{svc}.service"], sudo=True, silent=True, ignore_missing_unit=True)
            self.run_cmd(["rm", "-f", f"/etc/systemd/system/{svc}.service"], sudo=True, silent=True)
        
        self.run_cmd(["systemctl", "daemon-reload"], sudo=True, silent=True)
        self.run_cmd(["ldconfig"], sudo=True, silent=True)
    
    def remove_dkms_modules(self):
        """Usuwa moduły DKMS (brak modułu w DKMS = OK, nie przerywamy). Na Fedorze brak dkms – usuwa tylko moduły nvidia z .run z /lib/modules."""
        try:
            kernel = os.uname().release
        except Exception:
            kernel = "unknown"
        if self.system.distro_family == "fedora":
            # Fedora: .run instaluje moduły do /lib/modules/$kernel – usuń je przy przejściu na NVK
            self.run_cmd(["find", f"/lib/modules/{kernel}", "-name", "nvidia*.ko*", "-delete"], sudo=True, silent=True)
            self.run_cmd(["depmod", "-a"], sudo=True, silent=True)
            return
        rc, output = self.run_cmd(["dkms", "status"], sudo=False, silent=True)
        if rc == 0:
            for line in output.split("\n"):
                if "nvidia" in line.lower():
                    entry = line.split(",")[0].strip()
                    if entry:
                        self.run_cmd(
                            ["dkms", "remove", entry, "--all"],
                            sudo=True,
                            silent=True,
                            ignore_stderr_contains="not located in the DKMS tree",
                        )
        
        self.run_cmd(["rm", "-rf", "/var/lib/dkms/nvidia*", "/usr/src/nvidia*", "/usr/src/NVIDIA*"], 
                    sudo=True, silent=True)
        self.run_cmd(["find", f"/lib/modules/{kernel}", "-name", "nvidia*.ko*", 
                     "!", "-path", "*/updates/dkms/*", "-delete"], sudo=True, silent=True)
        self.run_cmd(["depmod", "-a"], sudo=True, silent=True)
    
    def purge_nvidia_packages(self):
        """Usuwa pakiety NVIDIA"""
        if self.system.distro_family == "fedora":
            packages = self.system.get_installed_nvidia_packages()
            if packages:
                self.run_cmd([self.system.get_dnf_cmd(), "remove", "-y"] + packages, sudo=True, silent=True)
            return
        rc, output = self.run_cmd(["dpkg", "-l"], sudo=False, silent=True)
        if rc == 0:
            packages = []
            for line in output.split("\n"):
                if line.startswith("ii") and ("nvidia" in line.lower() or 
                                             "libnvidia" in line.lower() or
                                             "linux-modules-nvidia" in line.lower()):
                    pkg = line.split()[1]
                    packages.append(pkg)
            
            if packages:
                self.run_cmd(["apt-get", "remove", "--purge", "-y"] + packages, 
                           sudo=True, silent=True)
                self.run_cmd(["apt-get", "autoremove", "--purge", "-y"], sudo=True, silent=True)
    
    def remove_nvidia_configs(self):
        """Usuwa konfiguracje NVIDIA (zgodnie z driver-manager-v2.sh)"""
        configs = [
            "/etc/modprobe.d/nvidia*.conf",
            "/etc/modprobe.d/blacklist-nouveau.conf",
            "/etc/modprobe.d/disable-nvidia.conf",
            "/etc/X11/xorg.conf",
            "/etc/X11/xorg.conf.nvidia-xconfig-original",
        ]
        for cfg in configs:
            self.run_cmd(["rm", "-f", cfg], sudo=True, silent=True)
        self.run_cmd(["sh", "-c", "rm -f /etc/ld.so.conf.d/*nvidia*"], sudo=True, silent=True)
        self.run_cmd(["sh", "-c", "rm -f /etc/X11/xorg.conf.d/*nvidia*"], sudo=True, silent=True)
        self.run_cmd(["sh", "-c", "rm -f /usr/share/X11/xorg.conf.d/*nvidia*"], sudo=True, silent=True)

    def remove_nvidia_libraries(self):
        """Usuwa biblioteki NVIDIA (zgodnie z driver-manager-v2.sh – pełna lista). Na Fedorze także /usr/lib64 (instalator .run)."""
        paths_rf = [
            "/usr/lib/x86_64-linux-gnu/libnvidia*",
            "/usr/lib/i386-linux-gnu/libnvidia*",
            "/usr/lib32/libnvidia*",
            "/usr/lib/nvidia*",
            "/usr/lib32/nvidia*",
            "/lib/x86_64-linux-gnu/libnvidia*",
            "/lib/i386-linux-gnu/libnvidia*",
        ]
        if self.system.distro_family == "fedora":
            paths_rf.extend(["/usr/lib64/libnvidia*", "/usr/lib64/nvidia*"])
        for path in paths_rf:
            self.run_cmd(["rm", "-rf", path], sudo=True, silent=True)
        paths_f = [
            "/lib/x86_64-linux-gnu/*nvidia*.so*",
            "/lib/i386-linux-gnu/*nvidia*.so*",
            "/usr/lib/x86_64-linux-gnu/*nvidia*.so*",
            "/usr/lib/i386-linux-gnu/*nvidia*.so*",
            "/lib/x86_64-linux-gnu/libvdpau_nvidia*",
            "/lib/i386-linux-gnu/libvdpau_nvidia*",
            "/usr/lib/x86_64-linux-gnu/vdpau/libvdpau_nvidia*",
            "/usr/lib/i386-linux-gnu/vdpau/libvdpau_nvidia*",
            "/lib/libGL.so*",
            "/lib/libEGL.so*",
            "/lib/libGLX.so*",
            "/lib/libGLES*.so*",
            "/usr/bin/nvidia*",
            "/usr/sbin/nvidia*",
        ]
        if self.system.distro_family == "fedora":
            paths_f.extend(["/usr/lib64/*nvidia*.so*", "/usr/lib64/libvdpau_nvidia*"])
        for path in paths_f:
            self.run_cmd(["sh", "-c", f"rm -f {path}"], sudo=True, silent=True)
        self.run_cmd(["ldconfig"], sudo=True, silent=True)

    def verify_nvidia_removal(self) -> bool:
        """Weryfikuje usunięcie NVIDIA (ldconfig) – jak w .sh. Zwraca True jeśli OK."""
        self.run_cmd(["ldconfig"], sudo=True, silent=True)
        rc, output = self.run_cmd(["ldconfig", "-p"], sudo=False, silent=True)
        if rc == 0 and "nvidia" in (output or "").lower():
            self.log(self.window._tr("log_ldconfig_warning"), "WARN")
            return False
        return True
    
    def configure_nouveau_for_nvk(self):
        """Konfiguruje nouveau dla NVK"""
        self.run_cmd(["rm", "-f", "/etc/modprobe.d/blacklist-nouveau.conf"], sudo=True, silent=True)
        
        nouveau_conf = "/etc/modprobe.d/nouveau.conf"
        content = "# generated by nvidia-manager-v2 (NVK)\noptions nouveau modeset=1\n"
        # Zapis przez Python
        tmp_file = Path("/tmp/nouveau_conf.txt")
        with open(tmp_file, "w") as f:
            f.write(content)
        self.run_cmd(["cp", str(tmp_file), nouveau_conf], sudo=True, silent=True)
        tmp_file.unlink()
        
        # Dodaj nouveau do initramfs-tools/modules (jak w .sh – z hasłem sudo)
        # grep -q zwraca 1 gdy nie znajdzie – to oczekiwane, nie loguj jako błąd
        modules_file = "/etc/initramfs-tools/modules"
        if Path(modules_file).exists():
            rc = self.system.run_command(["grep", "-q", "^nouveau$", modules_file], sudo=False)[0]
            if rc != 0:
                self.run_cmd(["sh", "-c", f"echo nouveau >> {modules_file}"], sudo=True, silent=True)
        
        # Na Fedorze dracut wywołujemy po instalacji pakietów (z firmware), żeby initramfs zawierał GSP
        if self.system.distro_family != "fedora":
            self.rebuild_initramfs()
    
    def install_nvk_packages(self) -> bool:
        """Instaluje pakiety NVK (Debian/Ubuntu: apt + PPA; Fedora: dnf)"""
        if self.system.distro_family == "fedora":
            packages = [
                "nvidia-gpu-firmware",
                "mesa-vulkan-drivers",
                "mesa-dri-drivers",
                "mesa-libEGL",
                "mesa-libGL",
                "vulkan-tools",
                "xorg-x11-drv-nouveau",
                "glx-utils",
            ]
            rc, _ = self.run_cmd([self.system.get_dnf_cmd(), "install", "-y"] + packages, sudo=True, timeout=3600)
            return rc == 0
        # Debian/Ubuntu
        self.run_cmd(["add-apt-repository", "-y", "ppa:kisak/kisak-mesa"], sudo=True, silent=True)
        self.run_cmd(["apt-get", "update", "-y"], sudo=True, silent=True)
        self.run_cmd(["dpkg", "--add-architecture", "i386"], sudo=True, silent=True)
        self.run_cmd(["apt-get", "update", "-y"], sudo=True, silent=True)
        packages = [
            "mesa-vulkan-drivers",
            "libgl1-mesa-dri",
            "libegl-mesa0",
            "libgles2",
            "libglx-mesa0",
            "mesa-utils",
            "vulkan-tools",
            "xserver-xorg-video-nouveau",
        ]
        rc, _ = self.run_cmd(["apt-get", "install", "-y"] + packages, sudo=True)
        return rc == 0
    
    def reinstall_plasma_and_mesa(self):
        """Reinstaluje środowisko graficzne i Mesa (Plasma, Cinnamon, MATE, Xfce, GNOME). Debian: apt, Fedora: dnf."""
        if self.system.distro_family == "fedora":
            rc, output = self.run_cmd(["rpm", "-qa"], sudo=False, silent=True)
            if rc == 0 and output:
                dnf = self.system.get_dnf_cmd()
                if "plasma-workspace" in output:
                    self.run_cmd([dnf, "reinstall", "-y",
                                "sddm", "plasma-workspace", "kwin-wayland",
                                "qt6-qtbase", "qt6-qtwayland"], sudo=True, silent=True)
                elif "cinnamon" in output:
                    self.run_cmd([dnf, "reinstall", "-y",
                                "cinnamon", "cinnamon-desktop-environment",
                                "qt6-qtbase", "qt6-qtwayland"], sudo=True, silent=True)
                elif "mate-desktop" in output:
                    self.run_cmd([dnf, "reinstall", "-y",
                                "mate-desktop-environment",
                                "qt6-qtbase", "qt6-qtwayland"], sudo=True, silent=True)
                elif "xfce4-session" in output:
                    self.run_cmd([dnf, "reinstall", "-y",
                                "xfce4-session", "qt6-qtbase", "qt6-qtwayland"], sudo=True, silent=True)
                elif "gnome-shell" in output:
                    self.run_cmd([dnf, "reinstall", "-y",
                                "gnome-shell", "gnome-session",
                                "qt6-qtbase", "qt6-qtwayland"], sudo=True, silent=True)
            self.run_cmd([self.system.get_dnf_cmd(), "reinstall", "-y",
                        "mesa-dri-drivers", "mesa-libEGL", "mesa-libGL"], sudo=True, silent=True)
            return
        rc, output = self.run_cmd(["dpkg", "-l"], sudo=False, silent=True)
        if rc == 0:
            if "plasma-workspace" in output:
                self.run_cmd(["apt-get", "install", "-y", "--reinstall",
                            "sddm", "plasma-workspace", "kwin-wayland",
                            "libqt6opengl6", "qt6-qpa-plugins"], sudo=True, silent=True)
            elif "cinnamon" in output:
                self.run_cmd(["apt-get", "install", "-y", "--reinstall",
                            "cinnamon", "cinnamon-desktop-environment",
                            "libqt6opengl6", "qt6-qpa-plugins"], sudo=True, silent=True)
            elif "mate-desktop" in output:
                self.run_cmd(["apt-get", "install", "-y", "--reinstall",
                            "mate-desktop-environment", "mate-desktop-environment-core",
                            "libqt6opengl6", "qt6-qpa-plugins"], sudo=True, silent=True)
            elif "xfce4" in output:
                self.run_cmd(["apt-get", "install", "-y", "--reinstall",
                            "xfce4", "xfce4-session",
                            "libqt6opengl6", "qt6-qpa-plugins"], sudo=True, silent=True)
            elif "gnome-shell" in output:
                self.run_cmd(["apt-get", "install", "-y", "--reinstall",
                            "gnome-shell", "gnome-session",
                            "libqt6opengl6", "qt6-qpa-plugins"], sudo=True, silent=True)
        self.run_cmd(["apt-get", "install", "-y", "--reinstall",
                    "libgl1-mesa-dri", "libegl-mesa0", "libgles2", "libglx-mesa0"],
                   sudo=True, silent=True)
    
    def configure_sddm_for_wayland(self):
        """Konfiguruje SDDM dla Wayland (jak w .sh – backup i usunięcie Session=plasma.desktop)"""
        sddm_conf = "/etc/sddm.conf"
        if Path(sddm_conf).exists():
            self.run_cmd(["cp", sddm_conf, f"{sddm_conf}.bak.{int(datetime.now().timestamp())}"],
                        sudo=True, silent=True)
            self.run_cmd(["sed", "-i", "/Session=plasma.desktop/d", sddm_conf], sudo=True, silent=True)
    
    def verify_nvk_installation(self):
        """Weryfikuje instalację NVK (sprawdzenie pakietów NVIDIA i ldconfig). Debian: dpkg, Fedora: rpm. Na Fedorze 1 pakiet (firmware) i ldconfig → INFO zamiast WARN."""
        if self.system.distro_family == "fedora":
            rc, output = self.run_cmd(["rpm", "-qa"], sudo=False, silent=True)
            if rc == 0 and output:
                nvidia_lines = [l for l in output.split("\n") if "nvidia" in l.lower()]
                if nvidia_lines:
                    if len(nvidia_lines) == 1 and "nvidia-gpu-firmware" in nvidia_lines[0].lower():
                        self.log(self.window._tr("log_nvidia_firmware_kept"), "INFO")
                    else:
                        self.log(self.window._tr("log_nvidia_pkgs_warning").format(len(nvidia_lines)), "WARN")
        else:
            rc, output = self.run_cmd(["dpkg", "-l"], sudo=False, silent=True)
            if rc == 0 and output:
                nvidia_lines = [l for l in output.split("\n") if l.startswith("ii") and "nvidia" in l.lower()]
                if nvidia_lines:
                    self.log(self.window._tr("log_nvidia_pkgs_warning").format(len(nvidia_lines)), "WARN")
        rc2, ld_out = self.run_cmd(["ldconfig", "-p"], sudo=False, silent=True)
        if rc2 == 0 and ld_out and "nvidia" in ld_out.lower():
            if self.system.distro_family == "fedora":
                self.log(self.window._tr("log_ldconfig_firmware_ok"), "INFO")
            else:
                self.log(self.window._tr("log_ldconfig_warning"), "WARN")
        self.run_cmd(["ldconfig"], sudo=True, silent=True)
    
    def block_nouveau(self):
        """Blokuje nouveau"""
        content = "blacklist nouveau\noptions nouveau modeset=0\n"
        tmp_file = Path("/tmp/blacklist_nouveau.txt")
        with open(tmp_file, "w") as f:
            f.write(content)
        self.run_cmd(["cp", str(tmp_file), "/etc/modprobe.d/blacklist-nouveau.conf"], sudo=True, silent=True)
        tmp_file.unlink()
    
    def rebuild_initramfs(self):
        """Przebudowuje initramfs (Debian/Ubuntu: update-initramfs, Fedora: dracut)"""
        self.log(self.window._tr("log_updating_initramfs"), "INFO")
        if self.system.distro_family == "fedora":
            self.run_cmd(["dracut", "--force"], sudo=True, silent=True)
        else:
            self.run_cmd(["update-initramfs", "-u", "-k", "all"], sudo=True, silent=True)
    
    def generate_install_script(self, version: str, label: str, run_file: Path, log_file: Optional[str] = None):
        """Generuje skrypt instalacyjny (Debian: 5-fazowy z DKMS; Fedora: bez DKMS, z dracut). log_file=None → LOG_DIR; przy instalacji na boot podaj np. /var/log/nvidia-run-install.log."""
        script_path = INSTALL_SCRIPT_DIR / "run-install-v2.sh"
        log_file_str = log_file if log_file is not None else str(LOG_DIR / "run-install-v2.log")
        run_file_str = str(run_file)

        if self.system.distro_family == "fedora":
            # Fedora: .run bez --dkms (instalator buduje moduł sam), potem dracut
            script_content = """#!/bin/bash
set -o pipefail

RUN_FILE="{run_file}"
VERSION="{version}"
LABEL="{label}"
LOG_FILE="{log_file}"

mkdir -p "$(dirname "$LOG_FILE")" || true

log() {{
  local msg="$1"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  local full_msg="[$timestamp] $msg"
  echo "$full_msg" >> "$LOG_FILE" 2>/dev/null || true
  echo "$full_msg"
}}

log "========================================="
log "NVIDIA DRIVER INSTALLATION (Fedora)"
log "========================================="
log "Wersja: $VERSION ($LABEL)"
log ""

if [ ! -f "$RUN_FILE" ]; then
  log "BŁĄD: Plik .run nie istnieje: $RUN_FILE"
  exit 1
fi

systemctl disable nvidia-run-install.service 2>/dev/null || true

log "FAZA 1: Przygotowanie..."
log_command() {{
  log "Wykonuję: $*"
  "$@" >> "$LOG_FILE" 2>&1
  local rc=$?
  [ $rc -ne 0 ] && log "BŁĄD (kod $rc): $*"
  return $rc
}}

log_command rm -f /etc/modprobe.d/blacklist-nouveau.conf /etc/modprobe.d/nvidia*.conf
for dm in sddm gdm lightdm; do log_command systemctl stop $dm 2>/dev/null || true; done
log_command modprobe -r nouveau 2>/dev/null || true

log ""
log "FAZA 2: Instalator NVIDIA (bez DKMS – budowa modułu wewnętrzna)..."
log_command "$RUN_FILE" --silent --no-questions --accept-license --disable-nouveau --run-nvidia-xconfig
install_exit=$?
log "Instalator zakończony z kodem: $install_exit"

kernel_ver=$(uname -r)
log_command depmod -a

log ""
log "FAZA 3: Konfiguracja..."
log_command bash -c 'echo "options nvidia-drm modeset=1 fbdev=1" | tee /etc/modprobe.d/nvidia-drm.conf > /dev/null'
log_command bash -c 'echo -e "blacklist nouveau\\noptions nouveau modeset=0" | tee /etc/modprobe.d/blacklist-nouveau.conf > /dev/null'

log "Aktualizacja initramfs (dracut)..."
log_command dracut --force

nvidia_modules=$(find /lib/modules/$kernel_ver -name "nvidia.ko*" 2>/dev/null | grep -v "i2c\\|forcedeth\\|typec\\|hid" | head -1)
if [ -z "$nvidia_modules" ]; then
  log "BŁĄD: Moduły NVIDIA nie są w kernelu"
  exit 1
fi
log "SUKCES: Moduły w: $nvidia_modules"

if [ -f /etc/X11/xorg.conf ]; then
  log_command cp /etc/X11/xorg.conf /etc/X11/xorg.conf.nvidia-boot-backup
  log_command rm -f /etc/X11/xorg.conf
fi

log_command systemctl disable nvidia-run-install.service 2>/dev/null || true
log "Restart za 5 sekund..."
sleep 5
reboot
""".format(run_file=run_file_str, version=version, label=label, log_file=log_file_str)
        else:
            # Debian/Ubuntu: pełny skrypt 5-fazowy z DKMS
            script_content = """#!/bin/bash
set -o pipefail

RUN_FILE="{run_file}"
VERSION="{version}"
LABEL="{label}"
LOG_FILE="{log_file}"

mkdir -p "$(dirname "$LOG_FILE")" || true

log() {{
  local msg="$1"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  local full_msg="[$timestamp] $msg"
  echo "$full_msg" >> "$LOG_FILE" 2>/dev/null || true
  echo "$full_msg"
}}

log "========================================="
log "NVIDIA DRIVER INSTALLATION v2"
log "========================================="
log "Wersja: $VERSION ($LABEL)"
log "Plik: $RUN_FILE"
log ""

if [ ! -f "$RUN_FILE" ]; then
  log "BŁĄD: Plik .run nie istnieje: $RUN_FILE"
  exit 1
fi

# Od razu wyłącz serwis, żeby przy następnym starcie nie uruchomił się ponownie (zapobiega zapętleniu)
log "Wyłączanie serwisu nvidia-run-install (jednorazowe uruchomienie)..."
systemctl disable nvidia-run-install.service 2>/dev/null || true

# FAZA 1: Przygotowanie
log "FAZA 1: Przygotowanie systemu..."
log_command() {{
  log "Wykonuję: $*"
  local output
  output=$("$@" >> "$LOG_FILE" 2>&1)
  local rc=$?
  if [ $rc -ne 0 ]; then
    log "BŁĄD (kod $rc): $*"
    [ -n "$output" ] && echo "$output" | while IFS= read -r line; do
      if ! echo "$line" | grep -qE "Unit.*not loaded|Unit.*does not exist"; then
        log "  $line"
      fi
    done
    return $rc
  fi
  return 0
}}

log_command rm -f /etc/modprobe.d/blacklist-nouveau.conf /etc/modprobe.d/nvidia*.conf
log_command sh -c 'systemctl stop display-manager 2>/dev/null || true'
for dm in sddm gdm3 gdm lightdm; do
  log_command sh -c "systemctl stop $dm 2>/dev/null || true"
done
log_command sh -c 'modprobe -r nouveau 2>/dev/null || true'

# FAZA 2: Instalacja
log ""
log "FAZA 2: Uruchamianie instalatora NVIDIA..."
log_command "$RUN_FILE" --silent --no-questions --accept-license --dkms --disable-nouveau --run-nvidia-xconfig
install_exit=$?
log "Instalator zakończony z kodem: $install_exit"

# FAZA 3: Weryfikacja i naprawa
log ""
log "FAZA 3: Weryfikacja instalacji..."

if [ ! -d "/usr/src/nvidia-$VERSION" ]; then
  log "Źródła nie są w /usr/src - wyodrębnianie..."
  extract_dir=$(mktemp -d)
  if "$RUN_FILE" --extract-only --target "$extract_dir" >> "$LOG_FILE" 2>&1; then
    if [ -f "$extract_dir/kernel-open/dkms.conf" ]; then
      log "Kopiowanie źródeł do /usr/src/nvidia-$VERSION..."
      log_command mkdir -p "/usr/src/nvidia-$VERSION"
      log_command cp -r "$extract_dir/kernel-open"/* "/usr/src/nvidia-$VERSION/"
      log_command rm -rf "$extract_dir"
      if ! dkms status 2>/dev/null | grep -q "nvidia/$VERSION"; then
        log "Rejestrowanie w DKMS..."
        log_command dkms add "/usr/src/nvidia-$VERSION"
      fi
    fi
  fi
fi

dkms_status=$(dkms status 2>/dev/null | grep nvidia | head -1)
if [ -z "$dkms_status" ]; then
  log "BŁĄD: Moduły nie są zarejestrowane w DKMS"
  log "Instalacja nie powiodła się"
  exit 1
fi

log "DKMS status: $dkms_status"
dkms_ver=$(echo "$dkms_status" | awk '{{print $2}}' | cut -d',' -f1)
kernel_ver=$(uname -r)

log "Sprawdzanie czy moduły są zbudowane..."
dkms_built=0
if [ -d "/var/lib/dkms/nvidia/$dkms_ver/$kernel_ver" ]; then
  arch=$(uname -m)
  if [ -f "/var/lib/dkms/nvidia/$dkms_ver/$kernel_ver/$arch/module/nvidia.ko" ] || \\
     [ -f "/var/lib/dkms/nvidia/$dkms_ver/$kernel_ver/$arch/module/nvidia.ko.xz" ] || \\
     [ -f "/var/lib/dkms/nvidia/$dkms_ver/$kernel_ver/x86_64/module/nvidia.ko" ] || \\
     [ -f "/var/lib/dkms/nvidia/$dkms_ver/$kernel_ver/x86_64/module/nvidia.ko.xz" ]; then
    dkms_built=1
    log "Moduły są zbudowane w DKMS"
  fi
fi

nvidia_modules=$(find /lib/modules/$kernel_ver -name "nvidia.ko*" 2>/dev/null | grep -v "i2c\\|forcedeth\\|typec\\|hid" | head -1)
if [ -z "$nvidia_modules" ]; then
  log "Moduły NIE są w kernelu - wymuszam budowanie..."
  if [ $dkms_built -eq 0 ]; then
    log "Budowanie modułów przez DKMS..."
    log_command dkms build "nvidia/$dkms_ver" -k "$kernel_ver"
    build_rc=$?
    if [ $build_rc -ne 0 ]; then
      log "BŁĄD podczas budowania modułów (kod: $build_rc)"
      log "Sprawdź czy linux-headers-$kernel_ver są zainstalowane"
      exit 1
    fi
  fi
  log "Instalowanie modułów do kernela..."
  log_command dkms install "nvidia/$dkms_ver" -k "$kernel_ver"
  install_rc=$?
  if [ $install_rc -ne 0 ]; then
    log "BŁĄD podczas instalacji modułów (kod: $install_rc)"
    exit 1
  fi
  sleep 2
  nvidia_modules=$(find /lib/modules/$kernel_ver -name "nvidia.ko*" 2>/dev/null | grep -v "i2c\\|forcedeth\\|typec\\|hid" | head -1)
  if [ -z "$nvidia_modules" ]; then
    log "BŁĄD: Moduły nadal nie są w kernelu po instalacji DKMS"
    exit 1
  fi
fi

log "Moduły są w kernelu: $nvidia_modules"

# FAZA 4: Konfiguracja
log ""
log "FAZA 4: Konfiguracja systemu..."
log_command bash -c 'echo "options nvidia-drm modeset=1 fbdev=1" | tee /etc/modprobe.d/nvidia-drm.conf > /dev/null'

# Blokowanie nouveau na kolejny start (w FAZIE 1 usunęliśmy blacklist; teraz go przywracamy)
log "Blokowanie nouveau na kolejny start..."
log_command bash -c 'echo -e "blacklist nouveau\\noptions nouveau modeset=0" | tee /etc/modprobe.d/blacklist-nouveau.conf > /dev/null'

log "Aktualizacja initramfs..."
if [ -f /etc/initramfs-tools/modules ]; then
  sed -i '/^nouveau$/d' /etc/initramfs-tools/modules 2>/dev/null || true
  for mod in nvidia nvidia_drm nvidia_modeset nvidia_uvm; do
    if ! grep -q "^$mod$" /etc/initramfs-tools/modules 2>/dev/null; then
      echo "$mod" >> /etc/initramfs-tools/modules
    fi
  done
fi
log_command update-initramfs -u -k all >/dev/null 2>&1 || true

# FAZA 5: Weryfikacja końcowa
log ""
log "FAZA 5: Weryfikacja końcowa..."
final_modules=$(find /lib/modules/$kernel_ver -name "nvidia.ko*" 2>/dev/null | grep -v "i2c\\|forcedeth\\|typec\\|hid" | head -1)
if [ -n "$final_modules" ]; then
  log "SUKCES: Moduły NVIDIA są zainstalowane"
  log "Lokalizacja: $final_modules"
else
  log "BŁĄD: Moduły NVIDIA nie są zainstalowane"
  exit 1
fi

log ""
log "========================================="
log "INSTALACJA ZAKOŃCZONA POMYŚLNIE"
log "========================================="
log ""

# xorg.conf z --run-nvidia-xconfig powstał przy starcie (bez monitora) i wymusza niską rozdzielczość.
# Usuwamy go, żeby po restarcie X/Wayland wykrył monitor i ustawił natywną rozdzielczość.
if [ -f /etc/X11/xorg.conf ]; then
  log "Kopia xorg.conf -> xorg.conf.nvidia-boot-backup (przywróć ręcznie jeśli potrzeba)"
  log_command cp /etc/X11/xorg.conf /etc/X11/xorg.conf.nvidia-boot-backup
  log_command rm -f /etc/X11/xorg.conf
  log "Usunięto xorg.conf – po restarcie rozdzielczość będzie wykryta automatycznie."
fi

log_command sh -c 'systemctl disable nvidia-run-install.service 2>/dev/null || true'
log "Restart systemu za 5 sekund..."
sleep 5
reboot
""".format(run_file=run_file_str, version=version, label=label, log_file=log_file_str)

        tmp_script = Path("/tmp/install_script.sh")
        with open(tmp_script, "w", encoding="utf-8") as f:
            f.write(script_content)
        self.run_cmd(["cp", str(tmp_script), str(script_path)], sudo=True, silent=True)
        self.run_cmd(["chmod", "+x", str(script_path)], sudo=True, silent=True)
        try:
            tmp_script.unlink()
        except OSError:
            pass

    def generate_systemd_service(self):
        """Generuje systemd service – ExecStart wskazuje skrypt w katalogu systemowym (SELinux)."""
        service_path = "/etc/systemd/system/nvidia-run-install.service"
        script_path = f"{SYSTEM_RUN_INSTALL_DIR}/run-install-v2.sh" if (IS_LINUX and SYSTEM_RUN_INSTALL_DIR) else str(INSTALL_SCRIPT_DIR / "run-install-v2.sh")
        
        service_content = f"""[Unit]
Description=NVIDIA run install on boot (v2)
DefaultDependencies=no
Before=display-manager.service
After=local-fs.target systemd-udev-settle.service
Wants=systemd-udev-settle.service

[Service]
Type=oneshot
ExecStart={script_path}
StandardOutput=tty
StandardError=tty
TTYPath=/dev/console
TTYReset=yes
TTYVHangup=yes
RemainAfterExit=no
TimeoutStartSec=900
User=root
Environment=HOME=/root

[Install]
WantedBy=multi-user.target
"""
        
        tmp_service = Path("/tmp/nvidia_service.service")
        with open(tmp_service, "w") as f:
            f.write(service_content)
        
        self.run_cmd(["cp", str(tmp_service), service_path], sudo=True, silent=True)
        self.run_cmd(["chmod", "644", service_path], sudo=True, silent=True)
        self.run_cmd(["systemctl", "daemon-reload"], sudo=True, silent=True)
        self.run_cmd(["systemctl", "enable", "nvidia-run-install.service"], sudo=True, silent=True)
        tmp_service.unlink()


# ============================================================================
# Etykieta logo – skalowanie z oknem
# ============================================================================

class ScalableLogoLabel(QLabel):
    """QLabel z logo – przy zmianie rozmiaru skaluje pixmapę, zachowując proporcje."""
    
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self._original = pixmap
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("padding: 8px;")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(80, 40)
        self._update_pixmap()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()
    
    def _update_pixmap(self):
        if self._original.isNull():
            return
        w = max(40, self.width() - 16)
        h = max(30, self.height() - 16)
        scaled = self._original.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        # Wycięcie środka, żeby wypełnić cały obszar (cover)
        if scaled.width() > w or scaled.height() > h:
            x = max(0, (scaled.width() - w) // 2)
            y = max(0, (scaled.height() - h) // 2)
            scaled = scaled.copy(x, y, w, h)
        self.setPixmap(scaled)


# ============================================================================
# GŁÓWNE OKNO APLIKACJI
# ============================================================================

class DriverManagerWindow(QMainWindow):
    """Główne okno aplikacji"""
    
    def __init__(self):
        super().__init__()
        self.system = SystemManager()
        self.versions = {}
        self.current_log_file = None
        self.settings = QSettings("NVIDIADriverManager", "DriverManager")
        self._lang = self.settings.value("language", "en", type=str)
        if self._lang not in TRANSLATIONS:
            self._lang = "en"
        self._install_thread = None  # wątek instalacji – czekamy na niego przy zamykaniu
        self._sudo_password = None  # hasło z okna Qt – przekazywane do wątku (sudo -S), czyszczone po zakończeniu
        self.init_ui()
        self.load_settings()
        self.load_system_info()
        # Sprawdzenie nowych wersji w tle (po 8 s)
        if not DEMO_MODE:
            QTimer.singleShot(8000, self._check_new_versions)
        # Monitoring GPU – odświeżanie co 2 s (można wstrzymać w menu Ustawienia)
        self._gpu_monitor_timer = QTimer(self)
        self._gpu_monitor_timer.timeout.connect(self._update_gpu_monitor)
        QTimer.singleShot(500, self._update_gpu_monitor)
        self._gpu_monitor_timer.start(2000)
        if self.settings.value("gpu_monitor_paused", False, type=bool):
            self._gpu_monitor_timer.stop()
            self._set_gpu_monitor_na()
    
    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle(self._tr("window_title"))
        self.setMinimumSize(900, 700)
        
        # Menu bar
        self.create_menu_bar()
        
        # Centralny widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Główny layout
        main_layout = QVBoxLayout(central_widget)
        
        # Splitter dla podziału na panele
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # Lewy panel - opcje
        left_panel = self.create_left_panel()
        self.splitter.addWidget(left_panel)
        
        # Prawy panel - logi
        right_panel = self.create_right_panel()
        self.splitter.addWidget(right_panel)
        
        # Ustaw proporcje (zostaną załadowane z ustawień jeśli istnieją)
        self.splitter.setSizes([400, 500])
        
        # Status bar: komunikat „Gotowy” po lewej; wyśrodkowana etykieta na informację o aktualizacji
        self.statusBar().showMessage(self._tr("status_ready"))
        self.status_update_label = QLabel("")
        self.status_update_label.setMinimumHeight(24)
        self.status_update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_update_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.statusBar().addWidget(QWidget(), 1)
        self.statusBar().addWidget(self.status_update_label, 1)
        self.statusBar().addWidget(QWidget(), 1)
        self.status_update_label.hide()
    
    def _set_status_update_message(self, text: str):
        """Ustawia lub czyści wyśrodkowany komunikat o aktualizacji w pasku statusu."""
        if not text:
            self.status_update_label.setText("")
            self.status_update_label.setStyleSheet("")
            self.status_update_label.hide()
            self.statusBar().showMessage(self._tr("status_ready"))
            return
        self.statusBar().showMessage("")
        self.status_update_label.setText(text)
        self.status_update_label.setStyleSheet(
            "background-color: #fff3cd; color: #856404; padding: 4px 12px; "
            "font-weight: bold; border-radius: 4px; border: 1px solid #ffc107;"
        )
        self.status_update_label.show()
    
    def _tr(self, key: str) -> str:
        """Zwraca tłumaczenie dla bieżącego języka."""
        return TRANSLATIONS.get(self._lang, TRANSLATIONS["en"]).get(key, key)
    
    def _set_language(self, lang: str):
        """Ustawia język UI i odświeża menu oraz panele."""
        if lang not in TRANSLATIONS or lang == self._lang:
            return
        self._lang = lang
        self.settings.setValue("language", lang)
        self.menuBar().clear()
        self.create_menu_bar()
        self.setWindowTitle(self._tr("window_title"))
        # Wyczyść komunikat o aktualizacji w środku paska statusu
        self._set_status_update_message("")
        # Odśwież panele po jednym cyklu event loop (żeby menu się zdążyło narysować)
        QTimer.singleShot(0, self._do_retranslate_and_refresh)
    
    def _do_retranslate_and_refresh(self):
        """Odświeża panele w nowym języku, czyści log i przeładowuje informacje (jak „Odśwież informacje”)."""
        self._retranslate_panels()
        # Wyczyść okno logów i przeładuj informacje – wtedy wszystkie komunikaty i etykiety są w nowym języku
        if hasattr(self, "log_text"):
            self.log_text.clear()
        self.load_system_info()
        # Wymuś przerysowanie
        self.update()
        QApplication.processEvents()
    
    def _retranslate_panels(self):
        """Odświeża tytuły grup, przyciski i status po zmianie języka."""
        if hasattr(self, "info_group"):
            self.info_group.setTitle(self._tr("group_info"))
        if hasattr(self, "gpu_monitor_group"):
            self.gpu_monitor_group.setTitle(self._tr("group_gpu_params"))
        if hasattr(self, "install_group"):
            self.install_group.setTitle(self._tr("group_install"))
        if hasattr(self, "log_group"):
            self.log_group.setTitle(self._tr("group_logs"))
        if hasattr(self, "btn_clear_log"):
            self.btn_clear_log.setText(self._tr("btn_clear_log"))
            self.btn_clear_log.setToolTip(self._tr("tt_clear_log"))
        if hasattr(self, "btn_save_log"):
            self.btn_save_log.setText(self._tr("btn_save_log"))
            self.btn_save_log.setToolTip(self._tr("tt_save_log"))
        if hasattr(self, "btn_open_log_dir"):
            self.btn_open_log_dir.setText(self._tr("btn_open_log_dir"))
            self.btn_open_log_dir.setToolTip(self._tr("tt_open_log_dir"))
        if hasattr(self, "statusBar"):
            self.statusBar().showMessage(self._tr("status_ready"))
        if hasattr(self, "distro_label") and hasattr(self, "system"):
            self._update_system_info_labels()
        if hasattr(self, "gpu_temp_label"):
            self._update_gpu_monitor()
        # Przyciski instalacji (NVK, repo, .run)
        if hasattr(self, "btn_nvk"):
            self.btn_nvk.setText(self._tr("btn_nvk_text"))
        if hasattr(self, "btn_repo") and getattr(self, "_repo_ver", None) is not None:
            self.btn_repo.setText(self._tr("btn_repo_fmt").format(self._repo_ver))
            self.btn_repo.setToolTip(self._tr("tt_repo_ver").format(self._repo_ver))
        if hasattr(self, "btn_repo_latest") and getattr(self, "_repo_latest", None) is not None:
            self.btn_repo_latest.setText(self._tr("btn_repo_latest_fmt").format(self._repo_latest))
            self.btn_repo_latest.setToolTip(self._tr("tt_repo_latest_ver").format(self._repo_latest))
        if hasattr(self, "versions") and self.versions:
            if hasattr(self, "btn_run_prod"):
                self.btn_run_prod.setText(self._tr("btn_run_prod_fmt").format(self.versions.get("production", "")))
                self.btn_run_prod.setToolTip(self._tr("tt_run_prod_ver").format(self.versions.get("production", "")))
            if hasattr(self, "btn_run_newf"):
                self.btn_run_newf.setText(self._tr("btn_run_newf_fmt").format(self.versions.get("new_feature", "")))
                self.btn_run_newf.setToolTip(self._tr("tt_run_newf_ver").format(self.versions.get("new_feature", "")))
            if hasattr(self, "btn_run_beta"):
                self.btn_run_beta.setText(self._tr("btn_run_beta_fmt").format(self.versions.get("beta", "")))
                self.btn_run_beta.setToolTip(self._tr("tt_run_beta_ver").format(self.versions.get("beta", "")))
            if hasattr(self, "btn_run_legacy"):
                self.btn_run_legacy.setText(self._tr("btn_run_legacy_fmt").format(self.versions.get("legacy", "")))
                self.btn_run_legacy.setToolTip(self._tr("tt_run_legacy_ver").format(self.versions.get("legacy", "")))
    
    def create_menu_bar(self):
        """Tworzy menu bar z ustawieniami"""
        menubar = self.menuBar()
        
        # Menu Ustawienia
        settings_menu = menubar.addMenu(self._tr("menu_settings"))
        settings_menu.setToolTipsVisible(True)
        
        # Wybór czcionki
        font_action = settings_menu.addAction(self._tr("menu_font"))
        font_action.triggered.connect(self.choose_font)
        font_action.setToolTip(self._tr("font_tooltip"))
        
        # Motyw kolorystyczny
        theme_menu = settings_menu.addMenu(self._tr("menu_theme"))
        light_action = theme_menu.addAction(self._tr("theme_light"))
        light_action.triggered.connect(lambda: self.set_theme("light"))
        light_action.setToolTip(self._tr("theme_light_tt"))
        
        dark_action = theme_menu.addAction(self._tr("theme_dark"))
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        dark_action.setToolTip(self._tr("theme_dark_tt"))
        
        # Język
        lang_menu = settings_menu.addMenu(self._tr("menu_language"))
        pl_action = lang_menu.addAction(self._tr("lang_pl"))
        pl_action.triggered.connect(lambda: self._set_language("pl"))
        en_action = lang_menu.addAction(self._tr("lang_en"))
        en_action.triggered.connect(lambda: self._set_language("en"))
        
        settings_menu.addSeparator()
        
        # Sprawdzaj aktualizacje w tle (zapisywane w ustawieniach) – domyślnie włączone
        self._action_check_updates = settings_menu.addAction(self._tr("action_check_updates"))
        self._action_check_updates.setCheckable(True)
        self._action_check_updates.setChecked(True)  # domyślnie zaznaczone (nadpisze load_settings jeśli brak klucza)
        self._action_check_updates.triggered.connect(self._toggle_check_updates)
        self._action_check_updates.setToolTip(self._tr("action_check_updates_tt"))
        
        # Wstrzymaj monitoring GPU (zapisywane w ustawieniach)
        self._action_gpu_monitor_paused = settings_menu.addAction(self._tr("action_gpu_paused"))
        self._action_gpu_monitor_paused.setCheckable(True)
        self._action_gpu_monitor_paused.triggered.connect(self._toggle_gpu_monitor)
        self._action_gpu_monitor_paused.setToolTip(self._tr("action_gpu_paused_tt"))
        
        settings_menu.addSeparator()
        
        # Export/Import konfiguracji
        export_action = settings_menu.addAction(self._tr("export_config"))
        export_action.triggered.connect(self.export_config)
        export_action.setToolTip(self._tr("export_config_tt"))
        import_action = settings_menu.addAction(self._tr("import_config"))
        import_action.triggered.connect(self.import_config)
        import_action.setToolTip(self._tr("import_config_tt"))
        
        save_action = settings_menu.addAction(self._tr("save_settings"))
        save_action.triggered.connect(self._save_settings_now)
        save_action.setToolTip(self._tr("save_settings_tt"))
        
        settings_menu.addSeparator()
        
        # Resetuj ustawienia
        reset_action = settings_menu.addAction(self._tr("reset_settings"))
        reset_action.triggered.connect(self.reset_settings)
        reset_action.setToolTip(self._tr("reset_settings_tt"))
        
        settings_menu.addSeparator()
        
        # Informacje
        about_action = settings_menu.addAction(self._tr("about_action"))
        about_action.triggered.connect(self.show_about)
        about_action.setToolTip(self._tr("about_action_tt"))
        
        # Menu Narzędzia
        tools_menu = menubar.addMenu(self._tr("menu_tools"))
        tools_menu.setToolTipsVisible(True)
        a8 = tools_menu.addAction(self._tr("tool_status"))
        a8.triggered.connect(self.show_status)
        a8.setToolTip(self._tr("tool_status_tt"))
        a9 = tools_menu.addAction(self._tr("tool_diagnostic"))
        a9.triggered.connect(self.run_diagnostic)
        a9.setToolTip(self._tr("tool_diagnostic_tt"))
        a10 = tools_menu.addAction(self._tr("tool_deps"))
        a10.triggered.connect(self.check_and_install_dependencies)
        a10.setToolTip(self._tr("tool_deps_tt"))
        a11 = tools_menu.addAction(self._tr("tool_history"))
        a11.triggered.connect(self.show_install_history)
        a11.setToolTip(self._tr("tool_history_tt"))
        a12 = tools_menu.addAction(self._tr("tool_refresh"))
        a12.triggered.connect(self.load_system_info)
        a12.setToolTip(self._tr("tool_refresh_tt"))
        a13 = tools_menu.addAction(self._tr("tool_backup"))
        a13.triggered.connect(self.show_backup_dialog)
        a13.setToolTip(self._tr("tool_backup_tt"))
        a14 = tools_menu.addAction(self._tr("tool_uninstall"))
        a14.triggered.connect(self.uninstall_nvidia_only)
        a14.setToolTip(self._tr("tool_uninstall_tt"))
        a15 = tools_menu.addAction(self._tr("tool_upgrade_repo"))
        a15.triggered.connect(self.upgrade_repo_driver)
        a15.setToolTip(self._tr("tool_upgrade_repo_tt"))
    
    def _toggle_check_updates(self):
        """Włącza/wyłącza sprawdzanie aktualizacji w tle (zapis w ustawieniach)."""
        on = self._action_check_updates.isChecked()
        self.settings.setValue("check_updates", on)
    
    def _toggle_gpu_monitor(self):
        """Wstrzymuje/wznawia monitoring GPU (zapis w ustawieniach)."""
        paused = self._action_gpu_monitor_paused.isChecked()
        self.settings.setValue("gpu_monitor_paused", paused)
        if hasattr(self, "_gpu_monitor_timer"):
            if paused:
                self._gpu_monitor_timer.stop()
                self._set_gpu_monitor_na()
            else:
                self._gpu_monitor_timer.start(2000)
                self._update_gpu_monitor()
    
    def load_settings(self):
        """Ładuje zapisane ustawienia"""
        # Rozmiar okna
        width = self.settings.value("window/width", 1200, type=int)
        height = self.settings.value("window/height", 800, type=int)
        self.resize(width, height)
        
        # Pozycja okna
        x = self.settings.value("window/x", -1, type=int)
        y = self.settings.value("window/y", -1, type=int)
        if x > 0 and y > 0:
            self.move(x, y)
        
        # Czcionka
        font_family = self.settings.value("font/family", "Ubuntu", type=str)
        font_size = self.settings.value("font/size", 12, type=int)
        font = QFont(font_family, font_size)
        self.apply_font(font)
        
        # Motyw
        theme = self.settings.value("theme/name", "light", type=str)
        self.set_theme(theme, apply_styles=True, silent=True)
        
        # Język (ładowany w __init__ przed create_menu_bar)
        _lang = self.settings.value("language", "en", type=str)
        if _lang in TRANSLATIONS and hasattr(self, "_lang"):
            self._lang = _lang
        
        # Proporcje splittera
        if hasattr(self, 'splitter'):
            left_size = self.settings.value("splitter/left", 400, type=int)
            right_size = self.settings.value("splitter/right", 500, type=int)
            self.splitter.setSizes([left_size, right_size])
        
        # Sprawdzaj aktualizacje w tle / Wstrzymaj monitoring GPU
        if hasattr(self, '_action_check_updates'):
            self._action_check_updates.setChecked(
                self.settings.value("check_updates", True, type=bool)
            )
        if hasattr(self, '_action_gpu_monitor_paused'):
            self._action_gpu_monitor_paused.setChecked(
                self.settings.value("gpu_monitor_paused", False, type=bool)
            )
    
    def save_settings(self):
        """Zapisuje ustawienia"""
        # Rozmiar okna
        size = self.size()
        self.settings.setValue("window/width", size.width())
        self.settings.setValue("window/height", size.height())
        
        # Pozycja okna
        pos = self.pos()
        self.settings.setValue("window/x", pos.x())
        self.settings.setValue("window/y", pos.y())
        
        # Proporcje splittera
        if hasattr(self, 'splitter'):
            sizes = self.splitter.sizes()
            if len(sizes) >= 2:
                self.settings.setValue("splitter/left", sizes[0])
                self.settings.setValue("splitter/right", sizes[1])
        
        # Czcionka (zapisana w apply_font)
        # Motyw (zapisany w set_theme)
        # Język
        if hasattr(self, "_lang"):
            self.settings.setValue("language", self._lang)
        # Sprawdzaj aktualizacje / Wstrzymaj monitoring GPU
        if hasattr(self, "_action_check_updates"):
            self.settings.setValue("check_updates", self._action_check_updates.isChecked())
        if hasattr(self, "_action_gpu_monitor_paused"):
            self.settings.setValue("gpu_monitor_paused", self._action_gpu_monitor_paused.isChecked())
    
    def _save_settings_now(self):
        """Zapisuje ustawienia od razu (wywołane z menu) i pokazuje potwierdzenie."""
        self.save_settings()
        self.statusBar().showMessage(self._tr("status_ready"))
        self.log(self._tr("log_settings_saved"), "INFO")
    
    def apply_font(self, font: QFont):
        """Stosuje czcionkę w całym programie (aplikacja, przyciski, etykiety, logi)."""
        app = QApplication.instance()
        if app is not None:
            app.setFont(font)
        if hasattr(self, 'log_text'):
            self.log_text.setFont(font)
        # Jawnie ustaw czcionkę na przyciskach i etykietach (StyleSheet może nadpisywać dziedziczenie)
        for name in (
            "gpu_label", "driver_label", "distro_label", "kernel_label",
            "btn_nvk", "btn_repo", "btn_repo_latest",
            "btn_run_prod", "btn_run_newf", "btn_run_beta", "btn_run_legacy",
            "btn_clear_log", "btn_save_log", "btn_open_log_dir",
        ):
            w = getattr(self, name, None)
            if w is not None and hasattr(w, "setFont"):
                w.setFont(font)
        self.settings.setValue("font/family", font.family())
        self.settings.setValue("font/size", font.pointSize())
        if hasattr(self, 'log'):
            self.log(self._tr("log_font_changed").format(font.family(), font.pointSize()), "INFO")
    
    def choose_font(self):
        """Otwiera dialog wyboru czcionki"""
        current_font = QFont(
            self.settings.value("font/family", "Ubuntu", type=str),
            self.settings.value("font/size", 12, type=int)
        )
        
        font, ok = QFontDialog.getFont(current_font, self, self._tr("menu_font"))
        if ok:
            self.apply_font(font)
    
    def set_theme(self, theme: str, apply_styles: bool = True, silent: bool = False):
        """Ustawia motyw kolorystyczny. Fusion + paleta = ten sam układ co jasny, tylko kolory."""
        self.settings.setValue("theme/name", theme)
        app = QApplication.instance()
        if app is None:
            return
        if theme == "dark":
            if apply_styles:
                app.setPalette(_dark_palette())
                self.setStyleSheet("")
        else:
            if apply_styles:
                app.setPalette(app.style().standardPalette())
                self.setStyleSheet("")
        if apply_styles and not silent:
            self.log(self._tr("log_theme_changed").format(self._tr("log_theme_dark") if theme == 'dark' else self._tr("log_theme_light")), "INFO")
    
    def reset_settings(self):
        """Resetuje ustawienia do domyślnych"""
        reply = QMessageBox.question(
            self,
            self._tr("reset_title"),
            self._tr("reset_question"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.clear()
            self._lang = "en"
            
            # Resetuj rozmiar okna
            self.resize(1200, 800)
            
            # Resetuj czcionkę
            default_font = QFont("Ubuntu", 12)
            self.apply_font(default_font)
            
            # Resetuj motyw
            self.set_theme("light")
            
            # Odśwież menu (język domyślny)
            self.menuBar().clear()
            self.create_menu_bar()
            self.setWindowTitle(self._tr("window_title"))
            
            self.log(self._tr("log_settings_reset"), "SUCCESS")
            QMessageBox.information(
                self,
                self._tr("reset_ok_title"),
                self._tr("reset_ok_text")
            )
    
    def show_about(self):
        """Pokazuje informacje o programie"""
        QMessageBox.about(
            self,
            self._tr("about_title"),
            self._tr("about_text")
        )
    
    def closeEvent(self, event):
        """Wywoływane przy zamykaniu okna – przy instalacji pyta czy zamknąć mimo to; czeka na wątek Fedora repo."""
        if self._install_thread is not None and self._install_thread.isRunning():
            reply = QMessageBox.question(
                self,
                self._tr("title_install_in_progress"),
                self._tr("msg_install_close_anyway"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        fedora_thread = getattr(self, "_fedora_repo_thread", None)
        if fedora_thread is not None and fedora_thread.isRunning():
            fedora_thread.wait(65000)
        self.save_settings()
        event.accept()
    
    def create_left_panel(self) -> QWidget:
        """Tworzy lewy panel z opcjami"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Informacje o systemie
        self.info_group = QGroupBox(self._tr("group_info"))
        info_layout = QVBoxLayout()
        
        self.gpu_label = QLabel(self._tr("sys_gpu_fmt").format(self._tr("sys_detecting")))
        self.gpu_label.setToolTip(self._tr("tt_gpu_label"))
        self.gpu_label.setStyleSheet("color: #76B900; font-weight: bold;")
        self.driver_label = QLabel(self._tr("sys_driver_fmt").format(self._tr("sys_detecting")))
        self.driver_label.setToolTip(self._tr("tt_driver_label"))
        self.driver_label.setStyleSheet("color: #E65100; font-weight: bold;")
        self.distro_label = QLabel(self._tr("sys_distro_detecting"))
        self.distro_label.setToolTip(self._tr("tt_distro_label"))
        self.distro_label.setStyleSheet("color: #AB47BC; font-weight: bold;")
        self.kernel_label = QLabel(self._tr("sys_kernel_fmt").format(self._tr("sys_detecting")))
        self.kernel_label.setToolTip(self._tr("tt_kernel_label"))
        self.kernel_label.setStyleSheet("color: #00838F; font-weight: bold;")
        
        info_layout.addWidget(self.gpu_label)
        info_layout.addWidget(self.driver_label)
        info_layout.addWidget(self.distro_label)
        info_layout.addWidget(self.kernel_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)
        
        # Parametry GPU – odświeżanie co 2 s (można wstrzymać w menu Ustawienia)
        self.gpu_monitor_group = QGroupBox(self._tr("group_gpu_params"))
        gpu_monitor_layout = QVBoxLayout()
        self.gpu_temp_label = QLabel(self._tr("gpu_temp_na"))
        self.gpu_usage_label = QLabel(self._tr("gpu_usage_na"))
        self.gpu_vram_label = QLabel(self._tr("gpu_vram_na"))
        self.gpu_power_label = QLabel(self._tr("gpu_power_na"))
        # Kolor i większa czcionka parametrów GPU
        gpu_params_style = "color: #00BCD4; font-weight: bold; font-size: 11pt;"
        for lbl in (self.gpu_temp_label, self.gpu_usage_label, self.gpu_vram_label, self.gpu_power_label):
            lbl.setStyleSheet(gpu_params_style)
        gpu_monitor_layout.addWidget(self.gpu_temp_label)
        gpu_monitor_layout.addWidget(self.gpu_usage_label)
        gpu_monitor_layout.addWidget(self.gpu_vram_label)
        gpu_monitor_layout.addWidget(self.gpu_power_label)
        self.gpu_monitor_group.setLayout(gpu_monitor_layout)
        layout.addWidget(self.gpu_monitor_group)
        
        # Opcje instalacji
        self.install_group = QGroupBox(self._tr("group_install"))
        install_layout = QVBoxLayout()
        
        # NVK
        self.btn_nvk = QPushButton(self._tr("btn_nvk_text"))
        self.btn_nvk.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: black; font-weight: bold; border-radius: 6px; "
            "border: 3px solid transparent; padding: 6px; } "
            "QPushButton:hover { background-color: #81C784; border: 3px solid #1B5E20; } "
            "QPushButton:pressed { background-color: #2E7D32; padding: 8px 4px 4px 8px; border: 3px solid #1B5E20; }"
        )
        self.btn_nvk.clicked.connect(self.install_nvk)
        install_layout.addWidget(self.btn_nvk)
        self.btn_nvk.setToolTip(self._tr("tt_nvk"))
        
        # Repo - przedostatnia
        self.btn_repo = QPushButton(self._tr("btn_repo_fmt").format("…"))
        self.btn_repo.setStyleSheet(
            "QPushButton { background-color: #FFC107; color: black; font-weight: bold; border-radius: 6px; "
            "border: 3px solid transparent; padding: 6px; } "
            "QPushButton:hover { background-color: #FFE082; border: 3px solid #E65100; } "
            "QPushButton:pressed { background-color: #FF8F00; padding: 8px 4px 4px 8px; border: 3px solid #E65100; }"
        )
        self.btn_repo.clicked.connect(self.install_repo)
        install_layout.addWidget(self.btn_repo)
        self.btn_repo.setToolTip(self._tr("tt_repo"))
        
        # Repo - najnowsza
        self.btn_repo_latest = QPushButton(self._tr("btn_repo_latest_fmt").format("…"))
        self.btn_repo_latest.setStyleSheet(
            "QPushButton { background-color: #FFC107; color: black; font-weight: bold; border-radius: 6px; "
            "border: 3px solid transparent; padding: 6px; } "
            "QPushButton:hover { background-color: #FFE082; border: 3px solid #E65100; } "
            "QPushButton:pressed { background-color: #FF8F00; padding: 8px 4px 4px 8px; border: 3px solid #E65100; }"
        )
        self.btn_repo_latest.clicked.connect(self.install_repo_latest)
        install_layout.addWidget(self.btn_repo_latest)
        self.btn_repo_latest.setToolTip(self._tr("tt_repo_latest"))
        
        # .run Production
        self.btn_run_prod = QPushButton(self._tr("btn_run_prod_fmt").format(PRODUCTION_VERSION))
        self.btn_run_prod.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: black; font-weight: bold; border-radius: 6px; "
            "border: 3px solid transparent; padding: 6px; } "
            "QPushButton:hover { background-color: #64B5F6; border: 3px solid #0D47A1; } "
            "QPushButton:pressed { background-color: #1565C0; padding: 8px 4px 4px 8px; border: 3px solid #0D47A1; }"
        )
        self.btn_run_prod.clicked.connect(lambda: self.install_nvidia_run("production"))
        install_layout.addWidget(self.btn_run_prod)
        self.btn_run_prod.setToolTip(self._tr("tt_run_prod"))
        
        # .run New Feature
        self.btn_run_newf = QPushButton(self._tr("btn_run_newf_fmt").format(NEW_FEATURE_VERSION))
        self.btn_run_newf.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: black; font-weight: bold; border-radius: 6px; "
            "border: 3px solid transparent; padding: 6px; } "
            "QPushButton:hover { background-color: #64B5F6; border: 3px solid #0D47A1; } "
            "QPushButton:pressed { background-color: #1565C0; padding: 8px 4px 4px 8px; border: 3px solid #0D47A1; }"
        )
        self.btn_run_newf.clicked.connect(lambda: self.install_nvidia_run("new_feature"))
        install_layout.addWidget(self.btn_run_newf)
        self.btn_run_newf.setToolTip(self._tr("tt_run_newf"))
        
        # .run Beta
        self.btn_run_beta = QPushButton(self._tr("btn_run_beta_fmt").format(BETA_VERSION))
        self.btn_run_beta.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: black; font-weight: bold; border-radius: 6px; "
            "border: 3px solid transparent; padding: 6px; } "
            "QPushButton:hover { background-color: #64B5F6; border: 3px solid #0D47A1; } "
            "QPushButton:pressed { background-color: #1565C0; padding: 8px 4px 4px 8px; border: 3px solid #0D47A1; }"
        )
        self.btn_run_beta.clicked.connect(lambda: self.install_nvidia_run("beta"))
        install_layout.addWidget(self.btn_run_beta)
        self.btn_run_beta.setToolTip(self._tr("tt_run_beta"))
        
        # .run Legacy
        self.btn_run_legacy = QPushButton(self._tr("btn_run_legacy_fmt").format(LEGACY_VERSION))
        self.btn_run_legacy.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: black; font-weight: bold; border-radius: 6px; "
            "border: 3px solid transparent; padding: 6px; } "
            "QPushButton:hover { background-color: #64B5F6; border: 3px solid #0D47A1; } "
            "QPushButton:pressed { background-color: #1565C0; padding: 8px 4px 4px 8px; border: 3px solid #0D47A1; }"
        )
        self.btn_run_legacy.clicked.connect(lambda: self.install_nvidia_run("legacy"))
        install_layout.addWidget(self.btn_run_legacy)
        self.btn_run_legacy.setToolTip(self._tr("tt_run_legacy"))
        
        self.install_group.setLayout(install_layout)
        layout.addWidget(self.install_group)
        
        # Logo NVIDIA z pliku – skaluje się z oknem i wypełnia miejsce
        # BUNDLE_DIR = katalog z wyekstrahowanymi plikami przy kompilacji (Nuitka/PyInstaller)
        logo_path = BUNDLE_DIR / "nvidia_logo.png" if (BUNDLE_DIR / "nvidia_logo.png").exists() else SCRIPT_DIR / "nvidia_logo.png"
        if logo_path.exists():
            pm = QPixmap(str(logo_path))
            if not pm.isNull():
                self.nvidia_logo_label = ScalableLogoLabel(pm)
                layout.addWidget(self.nvidia_logo_label, 1)
        
        layout.addStretch()
        
        return widget
    
    def create_right_panel(self) -> QWidget:
        """Tworzy prawy panel z logami"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logi
        self.log_group = QGroupBox(self._tr("group_logs"))
        self.log_group.setObjectName("logGroup")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Ubuntu", 12))
        log_layout.addWidget(self.log_text)
        
        # Odstęp między oknem logów a paskiem przycisków (jak na jasnym: pasek tła między logiem a przyciskami)
        log_layout.setSpacing(14)
        
        # Przyciski logów – w osobnym kontenerze (jak na jasnym: okno logów, pod nim pasek z przyciskami)
        log_buttons_widget = QWidget()
        log_buttons_widget.setObjectName("logButtonsBar")
        log_buttons = QHBoxLayout(log_buttons_widget)
        log_buttons.setContentsMargins(0, 10, 0, 6)
        self.btn_clear_log = QPushButton(self._tr("btn_clear_log"))
        self.btn_clear_log.clicked.connect(self.log_text.clear)
        self.btn_clear_log.setToolTip(self._tr("tt_clear_log"))
        log_buttons.addWidget(self.btn_clear_log)
        
        self.btn_save_log = QPushButton(self._tr("btn_save_log"))
        self.btn_save_log.clicked.connect(self.save_log)
        self.btn_save_log.setToolTip(self._tr("tt_save_log"))
        log_buttons.addWidget(self.btn_save_log)
        
        self.btn_open_log_dir = QPushButton(self._tr("btn_open_log_dir"))
        self.btn_open_log_dir.clicked.connect(self.open_log_dir)
        self.btn_open_log_dir.setToolTip(self._tr("tt_open_log_dir"))
        log_buttons.addWidget(self.btn_open_log_dir)
        
        log_layout.addWidget(log_buttons_widget)
        # Pasek postępu instalacji (testowo) – widoczny podczas instalacji
        self.install_progress_bar = QProgressBar()
        self.install_progress_bar.setMinimum(0)
        self.install_progress_bar.setMaximum(100)
        self.install_progress_bar.setValue(0)
        self.install_progress_bar.setTextVisible(True)
        self.install_progress_bar.setFormat("%p%")
        self.install_progress_bar.setVisible(False)
        log_layout.addWidget(self.install_progress_bar)
        
        self.log_group.setLayout(log_layout)
        layout.addWidget(self.log_group)
        
        return widget
    
    def start_log(self, name: str):
        """Rozpoczyna nowy log"""
        self.current_log_file = LOG_DIR / f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        try:
            self.current_log_file.touch()
        except:
            pass
    
    def collect_error_report(self, error_message: str, context: str = "") -> Dict:
        """Zbiera szczegółowe informacje o błędzie"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "context": context,
            "system": {
                "distro": self.system.distro_name,
                "distro_family": self.system.distro_family,
                "kernel": os.uname().release if not DEMO_MODE else "Unknown",
                "arch": self.system.nvidia_arch,
                "gpu": self.system.gpu_model if self.system.gpu_present else "Nie wykryto"
            },
            "driver": {
                "current": self.system.current_driver
            },
            "environment": {
                "python_version": sys.version,
                "qt_lib": QT_LIB
            }
        }
        
        # Dodaj dodatkowe informacje jeśli dostępne (na Fedorze brak dkms)
        if not DEMO_MODE and self.system.distro_family != "fedora":
            try:
                result = self.system.run_command(["dkms", "status"], sudo=False)
                if result[0] == 0:
                    report["dkms_status"] = result[1]
            except:
                pass
            
            try:
                # Załadowane moduły
                result = self.system.run_command(["lsmod"], sudo=False)
                if result[0] == 0:
                    nvidia_modules = [l for l in result[1].split("\n") if "nvidia" in l.lower()]
                    report["loaded_modules"] = nvidia_modules
            except:
                pass
        
        return report
    
    def save_error_report(self, report: Dict):
        """Zapisuje raport błędu do pliku"""
        error_dir = ERROR_LOG_DIR
        error_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        error_file = error_dir / f"error-report-{timestamp}.json"
        
        try:
            with open(error_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            self.log(self._tr("log_error_report_saved").format(error_file), "INFO")
            return str(error_file)
        except Exception as e:
            self.log(self._tr("log_error_report_failed").format(e), "ERROR")
            return None
    
    def log(self, message: str, level: str = "INFO"):
        """Dodaje wiadomość do logów"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = {
            "INFO": "ℹ",
            "SUCCESS": "✓",
            "WARN": "⚠",
            "ERROR": "✗",
            "DEBUG": "[DEBUG]"
        }.get(level, "")
        
        color = {
            "INFO": "#2196F3",
            "SUCCESS": "#4CAF50",
            "WARN": "#FFC107",
            "ERROR": "#F44336",
            "DEBUG": "#00BCD4"
        }.get(level, "#000000")
        
        formatted = f'<span style="color: {color};">[{timestamp}] [{level}] {prefix} {message}</span>'
        self.log_text.append(formatted)
        
        # Auto-scroll do końca
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_text.setTextCursor(cursor)
        
        # Zapis do pliku
        if self.current_log_file:
            try:
                with open(self.current_log_file, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] [{level}] {message}\n")
            except:
                pass
        
        # Automatyczne zbieranie raportów błędów
        if level == "ERROR":
            try:
                report = self.collect_error_report(message, "Log error")
                self.save_error_report(report)
            except:
                pass
    
    def _update_system_info_labels(self):
        """Ustawia etykiety informacji o systemie z aktualnych danych (używa _tr)."""
        self.distro_label.setText(self._tr("sys_distro_fmt").format(self.system.distro_name, self.system.distro_family))
        if self.system.gpu_present:
            self.gpu_label.setText(self._tr("sys_gpu_fmt").format(self.system.gpu_model))
        else:
            self.gpu_label.setText(self._tr("sys_gpu_not_detected"))
        driver_text = self._tr("sys_driver_fmt").format(self.system.current_driver)
        if self.system.current_driver == "nouveau":
            driver_text += self._tr("sys_driver_opensource")
        elif self.system.current_driver != "brak":
            driver_text += self._tr("sys_driver_nvidia")
        self.driver_label.setText(driver_text)
        try:
            kernel_ver = os.uname().release if not DEMO_MODE else "—"
            self.kernel_label.setText(self._tr("sys_kernel_fmt").format(kernel_ver))
        except Exception:
            self.kernel_label.setText(self._tr("sys_kernel_dash"))
    
    def load_system_info(self):
        """Ładuje informacje o systemie"""
        self._set_status_update_message("")
        self.log(self._tr("log_detecting_system"), "INFO")
        
        # Wykryj dystrybucję
        self.system.detect_distro()
        
        # Wykryj GPU
        self.system.check_gpu()
        if self.system.gpu_present:
            self.log(self._tr("log_gpu_detected").format(self.system.gpu_model), "SUCCESS")
        else:
            self.log(self._tr("log_gpu_not_detected"), "WARN")
        
        # Aktualny sterownik
        self.system.current_driver = self.system.get_current_driver()
        
        # Ustaw etykiety (z tłumaczeniami)
        self._update_system_info_labels()
        
        # Kernel (już ustawiony w _update_system_info_labels)
        
        # Pobierz wersje
        self.log(self._tr("log_fetching_versions"), "INFO")
        self.versions = self.system.fetch_versions()
        
        # Aktualizuj przyciski (zachowaj tooltips - wieloliniowy format)
        self.btn_run_prod.setText(self._tr("btn_run_prod_fmt").format(self.versions['production']))
        self.btn_run_prod.setToolTip(self._tr("tt_run_prod_ver").format(self.versions['production']))
        
        self.btn_run_newf.setText(self._tr("btn_run_newf_fmt").format(self.versions['new_feature']))
        self.btn_run_newf.setToolTip(self._tr("tt_run_newf_ver").format(self.versions['new_feature']))
        
        self.btn_run_beta.setText(self._tr("btn_run_beta_fmt").format(self.versions['beta']))
        self.btn_run_beta.setToolTip(self._tr("tt_run_beta_ver").format(self.versions['beta']))
        
        self.btn_run_legacy.setText(self._tr("btn_run_legacy_fmt").format(self.versions['legacy']))
        self.btn_run_legacy.setToolTip(self._tr("tt_run_legacy_ver").format(self.versions['legacy']))
        
        # Aktualizuj wersje repo (tekst przycisku i tooltip z nazwą + wersją jak w opcjach .run)
        if self.system.distro_family == "fedora":
            self._repo_ver = self._repo_latest = "580"
            self.btn_repo.setText(self._tr("btn_repo_fmt").format(self._repo_ver))
            self.btn_repo.setToolTip(self._tr("tt_repo_ver").format(self._repo_ver))
            self.btn_repo_latest.setText(self._tr("btn_repo_latest_fmt").format(self._repo_latest))
            self.btn_repo_latest.setToolTip(self._tr("tt_repo_latest_ver").format(self._repo_latest))
            self._fedora_repo_thread = FetchFedoraRepoThread(self.system)
            self._fedora_repo_thread.version_ready.connect(self._on_fedora_repo_version_ready)
            self._fedora_repo_thread.start()
        else:
            self._repo_ver = self.system.highest_repo_driver()
            self._repo_latest = self.system.highest_repo_driver_latest()
            self.btn_repo.setText(self._tr("btn_repo_fmt").format(self._repo_ver))
            self.btn_repo.setToolTip(self._tr("tt_repo_ver").format(self._repo_ver))
            self.btn_repo_latest.setText(self._tr("btn_repo_latest_fmt").format(self._repo_latest))
            self.btn_repo_latest.setToolTip(self._tr("tt_repo_latest_ver").format(self._repo_latest))
        
        self.log(self._tr("log_system_info_loaded"), "SUCCESS")
        if getattr(sys, "frozen", False):
            self.log(self._tr("log_log_dir_info").format(LOG_DIR.parent), "INFO")
        self.statusBar().showMessage(self._tr("status_ready"))

    def _on_install_progress(self, percent: int):
        """Aktualizuje pasek postępu instalacji (testowo)."""
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setVisible(True)
            self.install_progress_bar.setValue(percent)

    def _hide_install_progress_bar(self):
        """Ukrywa pasek postępu po zakończeniu instalacji."""
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setValue(0)
            self.install_progress_bar.setVisible(False)

    def _offer_install_dnf5(self) -> bool:
        """Na Fedorze: jeśli brak dnf5, pyta czy zainstalować (dla szybszej pracy). Zwraca True (kontynuuj)."""
        if self.system.distro_family != "fedora" or DEMO_MODE:
            return True
        if self.system.get_dnf_cmd() != "dnf":
            return True
        reply = QMessageBox.question(
            self,
            self._tr("title_dnf5"),
            self._tr("msg_dnf5_offer"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return True
        self.log(self._tr("log_installing_pkg").format("dnf5"), "INFO")
        rc, _, _ = self.system.run_command(
            ["dnf", "install", "-y", "dnf5"],
            sudo=True,
            timeout=120,
            sudo_password=getattr(self, "_sudo_password", None),
        )
        if rc == 0:
            self.system._dnf_cmd = "dnf5"
            self.log(self._tr("log_dnf5_installed"), "SUCCESS")
        else:
            self.log(self._tr("log_dnf5_failed"), "WARN")
        return True

    def _on_fedora_repo_version_ready(self, ver: str):
        """Aktualizuje wersje repo po zakończeniu pobrania w tle (tylko Fedora)."""
        self._repo_ver = self._repo_latest = ver
        self.btn_repo.setText(self._tr("btn_repo_fmt").format(self._repo_ver))
        self.btn_repo.setToolTip(self._tr("tt_repo_ver").format(self._repo_ver))
        self.btn_repo_latest.setText(self._tr("btn_repo_latest_fmt").format(self._repo_latest))
        self.btn_repo_latest.setToolTip(self._tr("tt_repo_latest_ver").format(self._repo_latest))
    
    def _get_sudo_askpass(self) -> Optional[str]:
        """Zwraca ścieżkę do programu askpass (okienko na hasło) dla sudo -A. None jeśli brak."""
        # zenity (GNOME) lub kdialog (KDE) – okienko na hasło (pełne ścieżki dla skompilowanej aplikacji)
        def try_askpass(path: str, is_zenity: bool) -> Optional[str]:
            if not path or not os.path.isfile(path):
                return None
            script = (
                f'#!/bin/sh\nexec "{path}" --password --title="Hasło sudo" "$@"\n'
                if is_zenity
                else f'#!/bin/sh\nexec "{path}" --password "Hasło sudo" "$@"\n'
            )
            try:
                fd, tmp = tempfile.mkstemp(prefix="sudo_askpass_", suffix=".sh")
                os.write(fd, script.encode())
                os.close(fd)
                os.chmod(tmp, 0o700)
                return tmp
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                return None

        for cmd, is_zenity in [("zenity", True), ("kdialog", False)]:
            path = None
            try:
                r = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    env={**os.environ, "PATH": "/usr/bin:/bin:" + os.environ.get("PATH", "")},
                )
                if r.returncode == 0 and r.stdout.strip():
                    path = r.stdout.strip()
            except Exception:
                pass
            if not path and cmd == "zenity":
                path = "/usr/bin/zenity" if os.path.isfile("/usr/bin/zenity") else None
            elif not path and cmd == "kdialog":
                path = "/usr/bin/kdialog" if os.path.isfile("/usr/bin/kdialog") else None
            if path:
                result = try_askpass(path, is_zenity)
                if result:
                    return result
        # Fallback: skrypt Python z tkinter (zwykle jest w systemie)
        try:
            r = subprocess.run(
                [sys.executable, "-c", "import tkinter"],
                capture_output=True,
                timeout=2,
            )
            if r.returncode != 0:
                return None
        except Exception:
            return None
        script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
try:
    import tkinter as tk
    from tkinter import simpledialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Hasło sudo:"
    p = simpledialog.askstring("Hasło sudo", prompt, show="*")
    if p:
        print(p, end="")
except Exception:
    pass
'''
        try:
            fd, tmp = tempfile.mkstemp(prefix="sudo_askpass_", suffix=".py")
            try:
                os.write(fd, script.encode())
                os.close(fd)
                os.chmod(tmp, 0o700)
                return tmp
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                return None
        except Exception:
            return None

    def _open_sudo_terminal(self) -> bool:
        """Otwiera terminal z poleceniem sudo -v (fallback gdy brak askpass). Pełne ścieżki i PATH dla skompilowanej aplikacji."""
        cmd_script = 'sudo -v && echo && echo "Uprawnienia uzyskane. Mozesz zamknac to okno." && read -p "Nacisnij Enter, aby zamknac..."'
        env = {**os.environ, "PATH": "/usr/bin:/bin:" + os.environ.get("PATH", "")}
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"
        # Pełne ścieżki – w skompilowanej aplikacji PATH bywa pusty
        terminals = [
            ("/usr/bin/gnome-terminal", ["--", "bash", "-c", cmd_script]),
            ("/usr/bin/konsole", ["-e", "bash", "-c", cmd_script]),
            ("/usr/bin/xfce4-terminal", ["-e", "bash -c " + repr(cmd_script)]),
            ("/usr/bin/xterm", ["-e", "bash -c " + repr(cmd_script)]),
            ("/usr/bin/mate-terminal", ["--command", "bash -c " + repr(cmd_script)]),
            ("gnome-terminal", ["--", "bash", "-c", cmd_script]),
            ("xterm", ["-e", "bash -c " + repr(cmd_script)]),
        ]
        for exe, args in terminals:
            if exe and not exe.startswith("/") and not os.path.isfile(exe):
                continue
            if exe.startswith("/") and not os.path.isfile(exe):
                continue
            try:
                subprocess.Popen(
                    [exe] + args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    env=env,
                )
                return True
            except (OSError, FileNotFoundError):
                continue
        return False

    def _ask_password_qt(self) -> Optional[str]:
        """Pokazuje okno Qt z polem hasła (działa w sesji użytkownika). Zwraca hasło lub None jeśli anulowano."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Hasło sudo")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(self._tr("pwd_dialog_label")))
        pwd_edit = QLineEdit()
        pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_edit.setPlaceholderText(self._tr("pwd_placeholder"))
        layout.addWidget(pwd_edit)
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton(self._tr("btn_cancel"))
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        pwd_edit.returnPressed.connect(dlg.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_ok)
        row.addWidget(btn_cancel)
        layout.addLayout(row)
        dlg.resize(360, 120)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return pwd_edit.text() or None
        return None

    def check_sudo(self) -> bool:
        """Sprawdza uprawnienia sudo i pyta o hasło jeśli potrzeba (okienko Qt, zenity lub terminal)."""
        if not IS_LINUX:
            return True
        
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True)
        if result.returncode == 0:
            self.log(self._tr("log_sudo_ok"), "INFO")
            return True
        
        reply = QMessageBox.question(
            self,
            self._tr("title_sudo_required"),
            self._tr("msg_sudo_ask"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.No:
            self.log(self._tr("log_install_cancelled"), "WARN")
            return False
        
        # 1. Okienko Qt w naszej aplikacji (zawsze widoczne, nie uruchamiane jako root)
        password = self._ask_password_qt()
        if password is not None:
            try:
                r = subprocess.run(
                    ["sudo", "-S", "-v"],
                    input=(password + "\n").encode(),
                    capture_output=True,
                    timeout=30,
                )
                if r.returncode == 0:
                    self.log(self._tr("log_sudo_granted"), "SUCCESS")
                    self._sudo_password = password  # przekaż do wątku instalacji (sudo-rs nie dzieli cache)
                    return True
                self.log(self._tr("log_wrong_password"), "WARN")
                QMessageBox.warning(self, self._tr("title_wrong_password"), self._tr("msg_wrong_password"))
                return False
            except (subprocess.TimeoutExpired, Exception):
                self.log(self._tr("log_password_error"), "WARN")
                return False
        # Anulowano – próbujemy zenity lub terminal
        
        # 2. Próba: zenity/kdialog (SUDO_ASKPASS – może nie działać gdy uruchamiane jako root)
        askpass_path = self._get_sudo_askpass()
        if askpass_path:
            try:
                env = {**os.environ, "SUDO_ASKPASS": askpass_path}
                r = subprocess.run(
                    ["sudo", "-A", "-v"],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                try:
                    os.unlink(askpass_path)
                except OSError:
                    pass
                if r.returncode == 0:
                    self.log(self._tr("log_sudo_granted"), "SUCCESS")
                    return True
            except (subprocess.TimeoutExpired, Exception):
                try:
                    os.unlink(askpass_path)
                except OSError:
                    pass
        
        # 3. Fallback: terminal
        self.log(self._tr("log_opening_terminal"), "INFO")
        if not self._open_sudo_terminal():
            self.log(self._tr("log_no_terminal"), "ERROR")
            QMessageBox.critical(
                self,
                self._tr("title_error"),
                self._tr("msg_no_password_dialog")
            )
            return False
        
        wait_dlg = QDialog(self)
        wait_dlg.setWindowTitle(self._tr("title_wait_sudo"))
        layout = QVBoxLayout(wait_dlg)
        layout.addWidget(QLabel(self._tr("msg_wait_sudo")))
        btn_cancel = QPushButton(self._tr("btn_cancel"))
        btn_cancel.clicked.connect(wait_dlg.reject)
        layout.addWidget(btn_cancel)
        poll_timer = QTimer(wait_dlg)
        timeout_timer = QTimer(wait_dlg)

        def on_poll():
            r = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                poll_timer.stop()
                timeout_timer.stop()
                wait_dlg.accept()

        def on_timeout():
            poll_timer.stop()
            wait_dlg.reject()

        poll_timer.timeout.connect(on_poll)
        poll_timer.start(1500)
        timeout_timer.singleShot(120 * 1000, lambda: (poll_timer.stop(), wait_dlg.reject()))
        if wait_dlg.exec() == QDialog.DialogCode.Accepted:
            self.log(self._tr("log_sudo_granted"), "SUCCESS")
            return True
        self.log(self._tr("log_sudo_failed"), "ERROR")
        QMessageBox.critical(
            self,
            self._tr("title_sudo_error"),
            self._tr("msg_sudo_failed")
        )
        return False
    
    def confirm_action(self, message: str) -> bool:
        """Pyta użytkownika o potwierdzenie"""
        reply = QMessageBox.question(
            self,
            self._tr("title_confirm"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def create_backup(self, install_type: str, target_version: str) -> Optional[Path]:
        """Tworzy snapshot stanu przed instalacją (sterownik, lista pakietów). Zwraca ścieżkę do pliku backupu lub None."""
        if DEMO_MODE:
            return None
        try:
            current_driver = self.system.get_current_driver()
            packages = self.system.get_installed_nvidia_packages()
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_id = f"backup-{stamp}"
            data = {
                "date": datetime.now().isoformat(),
                "backup_id": backup_id,
                "previous_driver": current_driver,
                "packages": packages,
                "install_about_to": install_type,
                "target_version": target_version,
            }
            path = BACKUP_DIR / f"{backup_id}.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log(self._tr("log_backup_created").format(path.name), "INFO")
            # Trzymaj tylko MAX_BACKUPS najnowszych; usuń najstarsze
            all_backups = sorted(BACKUP_DIR.glob("backup-*.json"))
            if len(all_backups) > MAX_BACKUPS:
                for old_path in all_backups[: len(all_backups) - MAX_BACKUPS]:
                    try:
                        old_path.unlink()
                        self.log(self._tr("log_backup_removed_old").format(old_path.name), "INFO")
                    except OSError:
                        pass
            return path
        except Exception as e:
            self.log(self._tr("log_backup_create_failed").format(e), "WARN")
            return None

    def list_backups(self) -> List[Dict]:
        """Zwraca listę backupów (posortowane od najnowszego)."""
        out = []
        if not BACKUP_DIR.exists():
            return out
        for p in sorted(BACKUP_DIR.glob("backup-*.json"), reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    d = json.load(f)
                d["_path"] = str(p)
                d["_filename"] = p.name
                out.append(d)
            except Exception:
                pass
        return out

    def restore_backup(self, backup_path: str) -> bool:
        """Przywraca stan z backupu (apt install zapisanych pakietów). Działa tylko dla backupów z repo."""
        if not self.check_sudo():
            return False
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            packages = data.get("packages", [])
            if not packages:
                self.log(self._tr("log_backup_no_pkgs"), "WARN")
                return False
            self.log(self._tr("log_restoring_backup"), "INFO")
            rc, _ = self._run_install_restore(packages)
            if rc == 0:
                self.log(self._tr("log_restored"), "SUCCESS")
                return True
            return False
        except Exception as e:
            self.log(self._tr("log_restore_error").format(e), "ERROR")
            return False

    def _run_install_restore(self, packages: List[str]) -> Tuple[int, str]:
        """Wykonuje apt install dla listy pakietów (w main thread – do użycia z dialogiem)."""
        if not packages:
            return 0, ""
        cmd = ["apt-get", "install", "-y"] + packages
        result = self.system.run_command(cmd, sudo=True, timeout=300,
                                        sudo_password=getattr(self, "_sudo_password", None))
        return result[0], result[1] or ""

    def append_install_history(self, install_type: str, version: str, success: bool = True):
        """Dodaje wpis do historii instalacji."""
        try:
            history = []
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            history.append({
                "date": datetime.now().isoformat(),
                "type": install_type,
                "version": version,
                "success": success,
            })
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def load_install_history(self) -> List[Dict]:
        """Ładuje historię instalacji."""
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    
    def check_requirements(self, install_type: str) -> tuple[bool, List[str]]:
        """Sprawdza wymagania przed instalacją"""
        issues = []
        
        if install_type == "nvk":
            # Sprawdź kernel
            try:
                kernel_major = int(os.uname().release.split(".")[0])
                if kernel_major < 6:
                    issues.append(f"Kernel {os.uname().release} - wymagany 6.0+ dla NVK")
            except:
                issues.append("Nie można sprawdzić wersji kernela")
            
            # Sprawdź czy nouveau jest dostępny
            result = self.system.run_command(["modinfo", "nouveau"], sudo=False)
            if result[0] != 0:
                issues.append("Moduł nouveau nie jest dostępny")
        
        elif install_type in ["repo", "run"]:
            if self.system.distro_family == "fedora":
                # Na Fedorze repo używa akmod, .run buduje moduł wewnętrznie – bez sprawdzania dkms/headers
                pass
            else:
                try:
                    kernel = os.uname().release
                except:
                    kernel = "unknown"
                result = self.system.run_command(["dpkg", "-l", f"linux-headers-{kernel}"], sudo=False)
                if result[0] != 0:
                    issues.append(f"Brak linux-headers-{kernel} - wymagane do kompilacji modułów")
                result = self.system.run_command(["which", "dkms"], sudo=False)
                if result[0] != 0:
                    issues.append("DKMS nie jest zainstalowany - wymagany do kompilacji modułów")
                result = self.system.run_command(["dpkg", "-l", "build-essential"], sudo=False)
                if result[0] != 0:
                    issues.append("build-essential nie jest zainstalowany - wymagany do kompilacji")
        
        return len(issues) == 0, issues
    
    def install_nvk(self):
        """Instaluje NVK"""
        if DEMO_MODE:
            self.log(self._tr("log_linux_only"), "WARN")
            return
        
        # Sprawdź uprawnienia sudo
        if not self.check_sudo():
            return
        
        # Ostrzeżenie: kernel za stary dla NVK
        try:
            kernel_ver = os.uname().release
            kernel_major = int(kernel_ver.split(".")[0])
            if kernel_major < 6:
                reply = QMessageBox.warning(
                    self,
                    self._tr("title_nvk_kernel"),
                    self._tr("msg_nvk_kernel").format(kernel_ver),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
        except Exception:
            pass
        
        # Sprawdź wymagania
        self.log(self._tr("log_checking_requirements"), "INFO")
        requirements_ok, issues = self.check_requirements("nvk")
        
        if not requirements_ok:
            self.log(self._tr("log_requirements_issues"), "WARN")
            for issue in issues:
                self.log(self._tr("log_requirement_item").format(issue), "WARN")
            
            reply = QMessageBox.warning(
                self,
                self._tr("title_requirements"),
                self._tr("msg_requirements_continue").format("\n".join(f"• {i}" for i in issues)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self._offer_install_dnf5()
        self.log(self._tr("log_starting_nvk"), "INFO")
        self.create_backup("nvk", "NVK")
        self.start_log("nvk")
        
        # Wątek instalacji
        thread = InstallationThread(self, "nvk", {"sudo_password": getattr(self, "_sudo_password", None)})
        self._install_thread = thread
        thread.output.connect(self.log)
        thread.ask_restart.connect(lambda: self.ask_restart())
        thread.progress.connect(self._on_install_progress)
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setValue(0)
            self.install_progress_bar.setVisible(True)
        def _on_nvk_finished(code):
            if code == 0:
                self.append_install_history("nvk", "NVK", success=True)
            self.log(self._tr("log_nvk_done"), "SUCCESS")
            self._install_thread = None
            self._sudo_password = None
            QTimer.singleShot(1500, self._hide_install_progress_bar)
        thread.finished.connect(_on_nvk_finished)
        thread.start()
    
    def install_repo(self):
        """Instaluje z repo (przedostatnia)"""
        if DEMO_MODE:
            self.log(self._tr("log_linux_only"), "WARN")
            return
        
        # Sprawdź uprawnienia sudo
        if not self.check_sudo():
            return
        
        # Sprawdź wymagania
        self.log(self._tr("log_checking_requirements"), "INFO")
        requirements_ok, issues = self.check_requirements("repo")
        
        if not requirements_ok:
            self.log(self._tr("log_deps_auto_install"), "INFO")
        
        self._offer_install_dnf5()
        ver = self.system.highest_repo_driver()
        ver_series = ver.split(".")[0] if "." in ver else ver
        pkg = f"nvidia-driver-{ver_series}-open"
        
        self.log(self._tr("log_starting_repo").format(ver), "INFO")
        self.create_backup("repo", ver)
        self.start_log("repo")
        
        thread = InstallationThread(self, "repo", {
            "version": ver,
            "package": pkg,
            "latest": False,
            "sudo_password": getattr(self, "_sudo_password", None),
        })
        self._install_thread = thread
        thread.output.connect(self.log)
        thread.ask_restart.connect(lambda: self.ask_restart())
        thread.progress.connect(self._on_install_progress)
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setValue(0)
            self.install_progress_bar.setVisible(True)
        def _on_repo_finished(code):
            if code == 0:
                self.append_install_history("repo", ver, success=True)
            self.log(self._tr("log_install_done_restart"), "SUCCESS")
            self._install_thread = None
            self._sudo_password = None
            QTimer.singleShot(1500, self._hide_install_progress_bar)
        thread.finished.connect(_on_repo_finished)
        thread.start()
    
    def install_repo_latest(self):
        """Instaluje z repo (najnowsza)"""
        if DEMO_MODE:
            self.log(self._tr("log_linux_only"), "WARN")
            return
        
        # Sprawdź uprawnienia sudo
        if not self.check_sudo():
            return
        
        # Sprawdź wymagania
        self.log(self._tr("log_checking_requirements"), "INFO")
        requirements_ok, issues = self.check_requirements("repo")
        
        if not requirements_ok:
            self.log(self._tr("log_deps_auto_install"), "INFO")
        
        self._offer_install_dnf5()
        ver = self.system.highest_repo_driver_latest()
        ver_series = ver.split(".")[0] if "." in ver else ver
        pkg = f"nvidia-driver-{ver_series}-open"
        
        self.log(self._tr("log_starting_repo").format(ver), "INFO")
        self.create_backup("repo", ver)
        self.start_log("repo-latest")
        
        thread = InstallationThread(self, "repo", {
            "version": ver,
            "package": pkg,
            "latest": True,
            "sudo_password": getattr(self, "_sudo_password", None),
        })
        self._install_thread = thread
        thread.output.connect(self.log)
        thread.ask_restart.connect(lambda: self.ask_restart())
        thread.progress.connect(self._on_install_progress)
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setValue(0)
            self.install_progress_bar.setVisible(True)
        def _on_repo_latest_finished(code):
            if code == 0:
                self.append_install_history("repo", ver, success=True)
            self.log(self._tr("log_install_done_restart"), "SUCCESS")
            self._install_thread = None
            self._sudo_password = None
            QTimer.singleShot(1500, self._hide_install_progress_bar)
        thread.finished.connect(_on_repo_latest_finished)
        thread.start()
    
    def install_nvidia_run(self, version_type: str):
        """Instaluje sterownik .run"""
        if DEMO_MODE:
            self.log(self._tr("log_linux_only"), "WARN")
            return
        
        # Sprawdź uprawnienia sudo
        if not self.check_sudo():
            return
        
        # Sprawdź wymagania
        self.log(self._tr("log_checking_requirements"), "INFO")
        requirements_ok, issues = self.check_requirements("run")
        
        if not requirements_ok:
            self.log(self._tr("log_deps_auto_install"), "INFO")
        
        version = self.versions.get(version_type, PRODUCTION_VERSION)
        label = {
            "production": "Production",
            "new_feature": "New Feature",
            "beta": "Beta",
            "legacy": "Legacy"
        }.get(version_type, "Production")
        
        self.log(self._tr("log_starting_run").format(label, version), "INFO")
        self.create_backup("run", version)
        self.start_log(f"run-v2-{version}")
        
        thread = InstallationThread(self, "run", {
            "version": version,
            "label": label,
            "version_type": version_type,
            "sudo_password": getattr(self, "_sudo_password", None),
        })
        self._install_thread = thread
        thread.output.connect(self.log)
        thread.ask_restart.connect(lambda: self.ask_restart())
        thread.progress.connect(self._on_install_progress)
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setValue(0)
            self.install_progress_bar.setVisible(True)
        def _on_run_finished(code):
            if code == 0:
                self.append_install_history("run", version, success=True)
            self.log(self._tr("log_prepare_done"), "SUCCESS")
            self._install_thread = None
            self._sudo_password = None
            QTimer.singleShot(1500, self._hide_install_progress_bar)
        thread.finished.connect(_on_run_finished)
        thread.start()
    
    def uninstall_nvidia_only(self):
        """Usuwa sterownik NVIDIA i przywraca nouveau (bez instalacji NVK)."""
        if DEMO_MODE:
            self.log(self._tr("log_linux_only_short"), "WARN")
            return
        if not self.check_sudo():
            return
        if not self.confirm_action(self._tr("msg_uninstall_confirm")):
            return
        self.log(self._tr("log_removing_nvidia"), "INFO")
        self.start_log("uninstall-nvidia")
        thread = InstallationThread(self, "uninstall", {"sudo_password": getattr(self, "_sudo_password", None)})
        self._install_thread = thread
        thread.output.connect(self.log)
        thread.ask_restart.connect(lambda: self.ask_restart())
        thread.progress.connect(self._on_install_progress)
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setValue(0)
            self.install_progress_bar.setVisible(True)
        def _on_finished(code):
            self._install_thread = None
            self._sudo_password = None
            QTimer.singleShot(1500, self._hide_install_progress_bar)
        thread.finished.connect(_on_finished)
        thread.start()
    
    def upgrade_repo_driver(self):
        """Aktualizuje sterownik NVIDIA z repo (apt update + upgrade)."""
        if DEMO_MODE:
            self.log(self._tr("log_linux_only_short"), "WARN")
            return
        pkg = self.system.get_installed_nvidia_driver_package()
        if not pkg:
            self.log(self._tr("log_no_driver_repo_short"), "WARN")
            QMessageBox.information(self, self._tr("title_update"), self._tr("msg_no_driver_repo_info"))
            return
        if not self.check_sudo():
            return
        self._offer_install_dnf5()
        self.log(self._tr("log_updating_pkg").format(pkg), "INFO")
        self.start_log("upgrade-repo")
        thread = InstallationThread(self, "upgrade_repo", {"sudo_password": getattr(self, "_sudo_password", None)})
        self._install_thread = thread
        thread.output.connect(self.log)
        thread.ask_restart.connect(lambda: self.ask_restart())
        thread.progress.connect(self._on_install_progress)
        if hasattr(self, "install_progress_bar"):
            self.install_progress_bar.setValue(0)
            self.install_progress_bar.setVisible(True)
        def _on_finished(code):
            self._install_thread = None
            self._sudo_password = None
            QTimer.singleShot(1500, self._hide_install_progress_bar)
        thread.finished.connect(_on_finished)
        thread.start()
    
    def _update_gpu_monitor(self):
        """Odświeża parametry GPU (temperatura, użycie, VRAM, pobór mocy) z nvidia-smi."""
        if DEMO_MODE:
            self.gpu_temp_label.setText(self._tr("gpu_temp_fmt").format("42"))
            self.gpu_usage_label.setText(self._tr("gpu_usage_fmt").format("5"))
            self.gpu_vram_label.setText(self._tr("gpu_vram_fmt").format("1024", "8192"))
            self.gpu_power_label.setText(self._tr("gpu_power_fmt").format("25.0"))
            return
        try:
            result = self.system.run_command([
                "nvidia-smi",
                "--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw",
                "--format=csv,noheader,nounits"
            ], sudo=False, timeout=5)
            if result[0] != 0 or not result[1].strip():
                self._set_gpu_monitor_na()
                return
            line = result[1].strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                self._set_gpu_monitor_na()
                return
            temp = parts[0] if parts[0] not in ("N/A", "") else "—"
            util = parts[1] if parts[1] not in ("N/A", "") else "—"
            mem_used = parts[2] if len(parts) > 2 and parts[2] not in ("N/A", "") else "—"
            mem_total = parts[3] if len(parts) > 3 and parts[3] not in ("N/A", "") else "—"
            power = parts[4] if len(parts) > 4 and parts[4] not in ("N/A", "") else "—"
            self.gpu_temp_label.setText(self._tr("gpu_temp_fmt").format(temp))
            self.gpu_usage_label.setText(self._tr("gpu_usage_fmt").format(util))
            self.gpu_vram_label.setText(self._tr("gpu_vram_fmt").format(mem_used, mem_total))
            self.gpu_power_label.setText(self._tr("gpu_power_fmt").format(power))
        except Exception:
            self._set_gpu_monitor_na()

    def _set_gpu_monitor_na(self):
        """Ustawia parametry GPU na „brak danych”."""
        self.gpu_temp_label.setText(self._tr("gpu_temp_na"))
        self.gpu_usage_label.setText(self._tr("gpu_usage_na"))
        self.gpu_vram_label.setText(self._tr("gpu_vram_na"))
        self.gpu_power_label.setText(self._tr("gpu_power_na"))

    def open_log_dir(self):
        """Otwiera katalog z logami w menedżerze plików."""
        path = LOG_DIR.resolve()
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.log(self._tr("log_cannot_create_logdir"), "ERROR")
                return
        try:
            subprocess.Popen(["xdg-open", str(path)], start_new_session=True)
            self.log(self._tr("log_opening_dir").format(path), "INFO")
        except Exception as e:
            self.log(self._tr("log_cannot_open_dir").format(e), "ERROR")
    
    def check_and_install_dependencies(self):
        """Sprawdza i doinstalowuje linux-headers, dkms, build-essential (Debian) lub kernel-devel, gcc (Fedora)."""
        if DEMO_MODE:
            self.log(self._tr("log_deps_linux_only"), "WARN")
            return
        missing = self.system.get_missing_dependency_packages("repo")
        if not missing:
            self.log(self._tr("log_all_deps_installed"), "SUCCESS")
            QMessageBox.information(self, self._tr("title_deps"), self._tr("msg_deps_all_installed"))
            return
        if not self.check_sudo():
            return
        self.log(self._tr("log_installing_missing").format(", ".join(missing)), "INFO")
        if self.system.distro_family == "fedora":
            rc, out = self.system.run_command(
                [self.system.get_dnf_cmd(), "install", "-y"] + missing, sudo=True, timeout=300,
                sudo_password=getattr(self, "_sudo_password", None))
        else:
            rc, _ = self.system.run_command(
                ["apt-get", "update", "-y"], sudo=True, timeout=120,
                sudo_password=getattr(self, "_sudo_password", None))
            if rc != 0:
                self.log(self._tr("log_update_repo_failed"), "WARN")
            rc, out = self.system.run_command(
                ["apt-get", "install", "-y"] + missing, sudo=True, timeout=300,
                sudo_password=getattr(self, "_sudo_password", None))
        if rc == 0:
            self.log(self._tr("log_deps_install_ok"), "SUCCESS")
            QMessageBox.information(self, self._tr("title_deps"), self._tr("msg_deps_installed_ok"))
        else:
            self.log(self._tr("log_deps_install_failed"), "ERROR")
            QMessageBox.warning(self, self._tr("title_deps"), self._tr("msg_deps_install_failed"))

    def show_backup_dialog(self):
        """Dialog z listą backupów i przyciskiem Przywróć."""
        backups = self.list_backups()
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("title_backup_dialog"))
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(self._tr("msg_backup_snapshots")))
        list_w = QListWidget()
        for b in backups:
            date_short = b.get("date", "")[:19].replace("T", " ")
            prev = b.get("previous_driver", "?")
            target = b.get("install_about_to", "?") + " " + str(b.get("target_version", ""))
            list_w.addItem(QListWidgetItem(f"{date_short}  |  {prev}  →  {target}"))
        if not backups:
            list_w.addItem(QListWidgetItem(self._tr("msg_no_backups")))
        list_w.setMinimumHeight(200)
        layout.addWidget(list_w)
        btn_restore = QPushButton(self._tr("btn_restore_backup"))
        btn_restore.setToolTip(self._tr("tt_restore_backup"))
        def do_restore():
            idx = list_w.currentRow()
            if idx < 0 or idx >= len(backups):
                QMessageBox.warning(dlg, self._tr("title_backup"), self._tr("msg_backup_select"))
                return
            path = backups[idx].get("_path", "")
            if not path:
                return
            dlg.accept()
            if self.restore_backup(path):
                QMessageBox.information(self, self._tr("title_backup"), self._tr("msg_backup_restored"))
            else:
                QMessageBox.warning(self, self._tr("title_backup"), self._tr("msg_backup_failed"))
        btn_restore.clicked.connect(do_restore)
        layout.addWidget(btn_restore)
        close_btn = QPushButton(self._tr("btn_close"))
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def show_install_history(self):
        """Dialog z historią instalacji."""
        history = self.load_install_history()
        dlg = QDialog(self)
        dlg.setWindowTitle(self._tr("install_history_title"))
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(self._tr("install_history_label")))
        list_w = QListWidget()
        for h in reversed(history):
            date_short = (h.get("date") or "")[:19].replace("T", " ")
            typ = h.get("type", "?")
            ver = h.get("version", "?")
            ok = "OK" if h.get("success", True) else "błąd"
            list_w.addItem(QListWidgetItem(f"{date_short}  |  {typ}  {ver}  |  {ok}"))
        if not history:
            list_w.addItem(QListWidgetItem("(brak wpisów)"))
        list_w.setMinimumHeight(250)
        layout.addWidget(list_w)
        close_btn = QPushButton("Zamknij")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)
        dlg.exec()

    def export_config(self):
        """Eksportuje ustawienia (okno, czcionka, motyw, splitter) do pliku JSON."""
        self.save_settings()
        data = {}
        for key in ["window/width", "window/height", "window/x", "window/y",
                    "font/family", "font/size", "theme/name",
                    "splitter/left", "splitter/right"]:
            val = self.settings.value(key)
            if val is not None:
                data[key] = val
        path, _ = QFileDialog.getSaveFileName(
            self, self._tr("title_export"),
            str(SCRIPT_DIR / "nvidia-driver-manager-config.json"),
            "JSON (*.json);;Wszystkie pliki (*)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.log(self._tr("log_config_saved").format(path), "SUCCESS")
                QMessageBox.information(self, self._tr("title_export"), self._tr("msg_export_ok"))
            except Exception as e:
                self.log(self._tr("log_config_save_error").format(e), "ERROR")
                QMessageBox.warning(self, self._tr("title_export"), str(e))

    def import_config(self):
        """Importuje ustawienia z pliku JSON."""
        path, _ = QFileDialog.getOpenFileName(
            self, self._tr("title_import"), str(SCRIPT_DIR),
            "JSON (*.json);;Wszystkie pliki (*)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, val in data.items():
                    self.settings.setValue(key, val)
                self.load_settings()
                self.log(self._tr("log_config_loaded").format(path), "SUCCESS")
                QMessageBox.information(self, self._tr("title_import"), self._tr("msg_import_ok"))
            except Exception as e:
                self.log(self._tr("log_config_load_error").format(e), "ERROR")
                QMessageBox.warning(self, self._tr("title_import"), str(e))

    def _check_new_versions(self):
        """Sprawdza w tle: aktualizacja z repo lub nowsza wersja .run; wyświetla komunikat wyśrodkowany w pasku statusu."""
        if DEMO_MODE or not self.settings.value("check_updates", True, type=bool):
            return
        self._set_status_update_message("")
        try:
            # 1. Sterownik z repo – czy apt ma aktualizację?
            pkg = self.system.get_installed_nvidia_driver_package()
            if pkg:
                rc, out = self.system.run_command(
                    ["apt", "list", "--upgradable"],
                    sudo=False,
                    timeout=15
                )
                if rc == 0 and out and pkg in out:
                    self._set_status_update_message(
                        "Dostępna aktualizacja sterownika z repo. Użyj przycisku 15. Aktualizuj sterownik z repo."
                    )
                    return
            # 2. Nowsza wersja .run z serwera NVIDIA?
            versions = self.system.fetch_versions()
            current = self.system.get_current_driver()
            if current in ("brak", "nouveau", ""):
                return
            def parse_ver(v):
                try:
                    parts = v.split(".")
                    return tuple(int(x) for x in parts[:3])
                except Exception:
                    return (0, 0, 0)
            cur_t = parse_ver(current)
            for name, ver in versions.items():
                if not ver:
                    continue
                t = parse_ver(ver)
                if t > cur_t:
                    self._set_status_update_message(
                        f"Dostępna nowa wersja sterownika .run: {ver} (np. {name}). Kliknij Odśwież."
                    )
                    return
        except Exception:
            pass
        self._set_status_update_message("")

    def show_status(self):
        """Pokazuje status systemu"""
        if DEMO_MODE:
            self.log(self._tr("log_status_system"), "INFO")
            self.log(self._tr("sys_gpu_fmt").format("NVIDIA GeForce RTX 3060"), "INFO")
            self.log(self._tr("sys_driver_fmt").format("550.90.07"), "INFO")
            self.log(self._tr("sys_distro_fmt").format("Windows", "N/A"), "INFO")
            return
        
        self.log(self._tr("log_checking_status"), "INFO")
        # -c 0 wyłącza kolory ANSI (w skompilowanym programie brak TTY → inxi i tak wysyła kody)
        result = self.system.run_command(["inxi", "-G", "-c", "0"], sudo=False)
        if result[0] == 0:
            self.log(self._tr("log_status_system"), "INFO")
            for line in result[1].split("\n"):
                if line.strip():
                    self.log(strip_ansi(line), "INFO")
        else:
            self.log(self._tr("log_inxi_installing"), "INFO")
            if self.system.distro_family == "fedora":
                install_cmd = ["sudo", self.system.get_dnf_cmd(), "install", "-y", "inxi"]
            else:
                install_cmd = ["sudo", "apt-get", "install", "-y", "inxi"]
            result = self.system.run_command(install_cmd, sudo=False)
            if result[0] == 0:
                self.log(self._tr("log_inxi_installed"), "SUCCESS")
                result = self.system.run_command(["inxi", "-G", "-c", "0"], sudo=False)
                if result[0] == 0:
                    self.log(self._tr("log_status_system"), "INFO")
                    for line in result[1].split("\n"):
                        if line.strip():
                            self.log(strip_ansi(line), "INFO")
            else:
                self.log(self._tr("log_inxi_failed"), "ERROR")
    
    def run_diagnostic(self):
        """Uruchamia diagnostykę"""
        if DEMO_MODE:
            self.log(self._tr("log_diag_linux_only"), "WARN")
            return
        
        self.log(self._tr("log_running_diag"), "INFO")
        diag_file = LOG_DIR / f"diagnostic-manual-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        
        try:
            with open(diag_file, "w", encoding="utf-8") as f:
                f.write(f"=== DIAGNOSTYKA: manual ===\n")
                f.write(f"Data: {datetime.now()}\n")
                try:
                    f.write(f"Kernel: {os.uname().release}\n\n")
                except:
                    f.write(f"Kernel: Unknown\n\n")
                
                # DKMS status
                f.write("=== DKMS STATUS ===\n")
                result = self.system.run_command(["dkms", "status"], sudo=False)
                if result[0] == 0:
                    nvidia_lines = [l for l in result[1].split("\n") if "nvidia" in l.lower()]
                    if nvidia_lines:
                        f.write("\n".join(nvidia_lines) + "\n")
                    else:
                        f.write("Brak modułów NVIDIA w DKMS\n")
                f.write("\n")
                
                # Moduły w kernelu
                f.write("=== MODUŁY W KERNELU ===\n")
                try:
                    kernel_ver = os.uname().release
                except:
                    kernel_ver = "Unknown"
                modules_path = Path(f"/lib/modules/{kernel_ver}")
                if modules_path.exists():
                    nvidia_modules = list(modules_path.rglob("nvidia.ko*"))
                    nvidia_modules = [str(m) for m in nvidia_modules if "i2c" not in str(m) and "forcedeth" not in str(m)]
                    if nvidia_modules:
                        f.write("\n".join(nvidia_modules) + "\n")
                    else:
                        f.write("Brak modułów NVIDIA w kernelu\n")
                f.write("\n")
                
                # Załadowane moduły
                f.write("=== ZAŁADOWANE MODUŁY ===\n")
                result = self.system.run_command(["lsmod"], sudo=False)
                if result[0] == 0:
                    nvidia_lines = [l for l in result[1].split("\n") if "nvidia" in l.lower() or "nouveau" in l.lower()]
                    if nvidia_lines:
                        f.write("\n".join(nvidia_lines) + "\n")
                    else:
                        f.write("Brak załadowanych modułów\n")
                f.write("\n")
                
                # Źródła w /usr/src
                f.write("=== ŹRÓDŁA W /usr/src ===\n")
                src_path = Path("/usr/src")
                if src_path.exists():
                    nvidia_src = [str(p) for p in src_path.iterdir() if "nvidia" in p.name.lower()]
                    if nvidia_src:
                        f.write("\n".join(nvidia_src) + "\n")
                    else:
                        f.write("Brak źródeł NVIDIA w /usr/src\n")
                f.write("\n")
            
            self.log(self._tr("log_diag_saved").format(diag_file), "SUCCESS")
        except Exception as e:
            self.log(self._tr("log_diag_error").format(e), "ERROR")
    
    def ask_restart(self):
        """Pyta użytkownika o restart"""
        reply = QMessageBox.question(
            self,
            self._tr("title_restart"),
            self._tr("msg_restart_now"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.log(self._tr("log_rebooting"), "INFO")
            self.system.run_command(
                ["reboot"],
                sudo=True,
                sudo_password=getattr(self, "_sudo_password", None),
            )
    
    def save_log(self):
        """Zapisuje logi do pliku"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("save_log_title"),
            str(LOG_DIR / f"log-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"),
            "Text Files (*.txt);;All Files (*)"
        )
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(self.log_text.toPlainText())
                self.log(self._tr("log_logs_saved").format(filename), "SUCCESS")
            except Exception as e:
                self.log(self._tr("log_config_save_error").format(e), "ERROR")


# ============================================================================
# MAIN
# ============================================================================

def _dark_palette():
    """Paleta ciemna – ten sam układ co Fusion jasny, tylko kolory ciemne."""
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    p.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Button, QColor(64, 64, 64))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Light, QColor(80, 80, 80))
    p.setColor(QPalette.ColorRole.Midlight, QColor(56, 56, 56))
    p.setColor(QPalette.ColorRole.Dark, QColor(35, 35, 35))
    p.setColor(QPalette.ColorRole.Mid, QColor(74, 74, 74))
    p.setColor(QPalette.ColorRole.Shadow, QColor(26, 26, 26))
    p.setColor(QPalette.ColorRole.Highlight, QColor(64, 64, 64))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(160, 160, 160))
    return p


def main():
    os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.services=false")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Ikona okna i paska zadań (zamiast domyślnej „karteczki”)
    icon_path = _get_app_icon_path()
    app_icon = None
    if icon_path:
        app_icon = QIcon(str(icon_path))
        if app_icon.isNull():
            app_icon = None
    if app_icon:
        app.setWindowIcon(app_icon)
    
    # Nie sprawdzamy sudo przy starcie - będzie sprawdzane przed każdą instalacją
    # Windows - bez sprawdzania sudo
    
    window = DriverManagerWindow()
    if app_icon:
        window.setWindowIcon(app_icon)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
