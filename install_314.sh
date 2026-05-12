#!/usr/bin/env bash
# install_314.sh — instala dependencias para Python 3.14 en Arch Linux
set -e

echo "==> [1/4] Instalando dependencias del sistema para pygame..."
sudo pacman -S --needed --noconfirm sdl2 sdl2_image sdl2_mixer sdl2_ttf portmidi

echo "==> [2/4] Instalando paquetes principales (Python 3.14)..."
pip install -r requirements-314.txt

echo "==> [3/4] Instalando facenet-pytorch sin restricción de numpy..."
# facenet-pytorch 2.6.0 declara numpy<2.0 pero funciona con numpy 2.x.
# --no-deps evita que pip resuelva ese conflicto y sobreescriba numpy.
pip install --no-deps facenet-pytorch==2.6.0

echo "==> [4/4] Instalando setuptools/wheel (necesarios para compilar pygame)..."
pip install setuptools wheel

echo ""
echo "Instalación completada. Ejecuta para verificar:"
echo "  python manage.py check"
echo "  python manage.py migrate"
echo "  python manage.py runserver"
