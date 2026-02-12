# NVIDIA Driver Manager v2.0

Graficzny menedżer sterowników NVIDIA dla Linuxa z pełnym wsparciem dla różnych środowisk graficznych.

## 🎯 Funkcje

- **Instalacja sterowników NVIDIA**
  - NVK (Mesa/Wayland) - open-source
  - Z repozytoriów (stabilna i najnowsza wersja)
  - Z plików .run (Production, New Feature, Beta, Legacy)
  
- **Zarządzanie sterownikami**
  - Sprawdzanie statusu GPU i sterownika
  - Diagnostyka systemu
  - Aktualizacja sterownika z repozytorium
  - Deinstalacja sterownika (przywrócenie nouveau)
  
- **Bezpieczeństwo i backup**
  - Automatyczne kopie zapasowe (max 10)
  - Przywracanie poprzedniej konfiguracji
  - Historia instalacji
  - Szczegółowe raporty błędów
  
- **Monitoring GPU**
  - Temperatura
  - Wykorzystanie GPU
  - Pamięć VRAM
  - Pobór mocy

- **Interfejs użytkownika**
  - Motywy: jasny i ciemny
  - Języki: polski i angielski
  - Konfigurowalna czcionka
  - Export/import ustawień

## 📋 Wymagania

### System
- Linux (Ubuntu, Kubuntu, Debian, Linux Mint)
- Karta graficzna NVIDIA
- Kernel 6.0+ (dla NVK)

### Zależności Python
- Python 3.6+
- PySide6 lub PyQt6

### Zależności systemowe (instalowane automatycznie)
- linux-headers
- dkms
- build-essential

## 🚀 Instalacja

### Instalacja zależności Python

```bash
# PySide6 (zalecane)
pip install PySide6

# lub PyQt6
pip install PyQt6
```

### Uruchomienie

```bash
python3 nvidia_driver_manager.py
```

Lub nadaj uprawnienia wykonywania:

```bash
chmod +x nvidia_driver_manager.py
./nvidia_driver_manager.py
```

## 🖥️ Kompatybilność środowisk graficznych

Program działa na wszystkich popularnych środowiskach graficznych:

- ✅ KDE/Plasma (Kubuntu)
- ✅ GNOME (Ubuntu)
- ✅ Xfce (Xubuntu, Linux Mint Xfce)
- ✅ MATE (Linux Mint MATE)
- ✅ Cinnamon (Linux Mint)
- ✅ LXQt (Lubuntu)
- ✅ Wszystkie inne z X11/Wayland

## 📝 Użytkowanie

1. **Sprawdzenie statusu GPU**
   - Menu: Narzędzia → Status
   - Wyświetla informacje o karcie graficznej i zainstalowanym sterowniku

2. **Instalacja sterownika**
   - Wybierz jedną z dostępnych opcji instalacji
   - Program automatycznie sprawdzi wymagania
   - Instalacja wymaga hasła sudo
   - Po zakończeniu zalecany jest restart systemu

3. **Diagnostyka**
   - Menu: Narzędzia → Diagnostyka
   - Kompleksowa analiza systemu i GPU
   - Automatyczny raport błędów

4. **Backup i przywracanie**
   - Menu: Narzędzia → Lista backupów / Przywróć
   - Program automatycznie tworzy backupy przed każdą instalacją
   - Możliwość przywrócenia poprzedniego stanu

## ⚙️ Struktura katalogów

Program tworzy następujące katalogi w `~/.local/share/nvidia-driver-manager/`:

- `logs/` - pliki logów
- `logs/errors/` - raporty błędów
- `cache/` - cache i stan aplikacji
- `cache/backups/` - kopie zapasowe
- `install-on-reboot/` - skrypty instalacyjne

## ⚠️ Uwagi

- **Secure Boot**: Jeśli jest włączony, instalacja modułów DKMS może wymagać podpisania lub wyłączenia Secure Boot
- **NVK**: Wymaga kernela 6.0+, usuwa sterowniki NVIDIA i DKMS, nie wspiera CUDA
- **Instalacja .run**: Instalacja następuje po restarcie systemu
- **Kopie zapasowe**: Przechowywanych jest maksymalnie 10 najnowszych backupów

## 🐛 Rozwiązywanie problemów

1. **Brak połączenia z internetem**
   - Program sprawdza połączenie z 8.8.8.8
   - Upewnij się, że masz dostęp do internetu

2. **Błąd instalacji pakietów**
   - Menu: Narzędzia → Sprawdź i zainstaluj zależności
   - Sprawdź logi w panelu lub w katalogu `logs/`

3. **Problemy z uprawnieniami sudo**
   - Program automatycznie otworzy terminal do wpisania hasła
   - Wymaga zainstalowanego zenity lub xterm

## 📄 Licencja

Program zarządzający sterownikami NVIDIA dla systemów Linux.

## 👨‍💻 Autor

NVIDIA Driver Manager v2.0
