# NVIDIA Driver Manager v2.0

Graficzny menedżer sterowników NVIDIA dla Linuxa z pełnym wsparciem dla różnych środowisk graficznych.

> 🇬🇧 [English README](README.md)

![Platforma](https://img.shields.io/badge/platforma-Linux-blue)
![Python](https://img.shields.io/badge/python-3.6+-green)
![Licencja](https://img.shields.io/badge/licencja-open--source-brightgreen)

---

## ✨ Funkcje

### Instalacja sterowników
- **NVK (Mesa/Wayland)** — otwartoźródłowy sterownik NVIDIA
- **Z repozytoriów** — wersja stabilna i najnowsza
- **Z plików .run** — Production, New Feature, Beta oraz Legacy

### Zarządzanie sterownikami
- Sprawdzanie statusu GPU i sterownika
- Diagnostyka systemu
- Aktualizacja sterownika z repozytorium
- Deinstalacja sterownika (przywrócenie nouveau)

### Bezpieczeństwo i backup
- Automatyczne kopie zapasowe przed każdą instalacją (max 10)
- Przywracanie poprzedniej konfiguracji
- Historia instalacji
- Szczegółowe raporty błędów

### Monitoring GPU
- Temperatura
- Wykorzystanie GPU
- Pamięć VRAM
- Pobór mocy

### Interfejs użytkownika
- Motyw jasny i ciemny
- Obsługa języka polskiego i angielskiego
- Konfigurowalna czcionka
- Export/import ustawień

---

## 📋 Wymagania

### System
- Linux — Ubuntu, Kubuntu, Debian, Linux Mint
- Karta graficzna NVIDIA
- Kernel 6.0+ (wymagany dla NVK)

### Zależności Python
- Python 3.6+
- PySide6 lub PyQt6

### Zależności systemowe (instalowane automatycznie)
- linux-headers
- dkms
- build-essential

---

## 🚀 Instalacja

### 1. Zainstaluj zależności Python

```bash
# PySide6 (zalecane)
pip install PySide6

# lub PyQt6
pip install PyQt6
```

### 2. Uruchom aplikację

```bash
python3 nvidia_driver_manager.py
```

Lub nadaj plikowi uprawnienia wykonywania:

```bash
chmod +x nvidia_driver_manager.py
./nvidia_driver_manager.py
```

---

## 🖥️ Kompatybilność środowisk graficznych

| Środowisko | Status |
|---|---|
| KDE/Plasma (Kubuntu) | ✅ Wspierane |
| GNOME (Ubuntu) | ✅ Wspierane |
| Xfce (Xubuntu, Linux Mint Xfce) | ✅ Wspierane |
| MATE (Linux Mint MATE) | ✅ Wspierane |
| Cinnamon (Linux Mint) | ✅ Wspierane |
| LXQt (Lubuntu) | ✅ Wspierane |
| Inne z X11/Wayland | ✅ Wspierane |

---

## 📝 Użytkowanie

### Sprawdzenie statusu GPU
Przejdź do **Narzędzia → Status** aby wyświetlić informacje o karcie graficznej i zainstalowanym sterowniku.

### Instalacja sterownika
1. Wybierz jedną z dostępnych opcji instalacji.
2. Program automatycznie sprawdzi wymagania.
3. Instalacja wymaga hasła sudo.
4. Po zakończeniu zalecany jest restart systemu.

### Diagnostyka
Przejdź do **Narzędzia → Diagnostyka** aby przeprowadzić kompleksową analizę systemu i GPU z automatycznym raportem błędów.

### Backup i przywracanie
Przejdź do **Narzędzia → Lista backupów / Przywróć** aby zarządzać kopiami zapasowymi. Program automatycznie tworzy backup przed każdą instalacją — możesz przywrócić poprzedni stan w dowolnym momencie.

---

## ⚙️ Struktura katalogów

Program tworzy następujące katalogi w `~/.local/share/nvidia-driver-manager/`:

```
~/.local/share/nvidia-driver-manager/
├── logs/               # Pliki logów
│   └── errors/         # Raporty błędów
├── cache/              # Stan aplikacji i cache
│   └── backups/        # Kopie zapasowe konfiguracji
└── install-on-reboot/  # Skrypty instalacyjne po restarcie
```

---

## ⚠️ Uwagi

- **Secure Boot**: Jeśli jest włączony, instalacja modułów DKMS może wymagać podpisania lub wyłączenia Secure Boot.
- **NVK**: Wymaga kernela 6.0+. Usuwa sterowniki NVIDIA i DKMS. **Nie wspiera CUDA.**
- **Instalacja .run**: Instalacja następuje po restarcie systemu.
- **Kopie zapasowe**: Przechowywanych jest maksymalnie 10 najnowszych backupów.

---

## 🐛 Rozwiązywanie problemów

**Brak połączenia z internetem**
Program sprawdza połączenie z 8.8.8.8. Upewnij się że masz dostęp do internetu przed instalacją sterowników.

**Błąd instalacji pakietów**
Przejdź do **Narzędzia → Sprawdź i zainstaluj zależności** i sprawdź logi w panelu lub w katalogu `logs/`.

**Problemy z uprawnieniami sudo**
Program automatycznie otworzy terminal do wpisania hasła. Upewnij się że masz zainstalowane `zenity` lub `xterm`.

**Starsze karty GPU i karty laptopowe**
Program był testowany na Kubuntu 25.10 z nowoczesną kartą graficzną. Wsparcie dla starszych i laptopowych kart NVIDIA zależy od dostępności sterowników w repozytoriach Twojej dystrybucji. Jeśli testujesz na starszym sprzęcie — otwórz issue i podziel się wynikami. Twój feedback pomaga poprawić kompatybilność!

---

## 🤝 Współpraca

Zgłoszenia błędów i pull requesty są mile widziane! Jeśli testujesz aplikację na dystrybucji lub sprzęcie którego tu nie ma — otwórz issue i podziel się wynikami.

---

## 👨‍💻 Autor

Stworzony przez entuzjastę Linuxa który chciał mieć prosty i przejrzysty sposób na zarządzanie sterownikami NVIDIA bez wchodzenia do terminala za każdym razem.

---

## 📄 Licencja

Projekt jest open source. Szczegóły w pliku [LICENSE](LICENSE).
