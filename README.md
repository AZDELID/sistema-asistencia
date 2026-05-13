# 🎯 Sistema de Control de Asistencia en Tiempo Real

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2.14-green?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue?logo=postgresql&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-red?logo=pytorch&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow)

Sistema biométrico de asistencia en tiempo real para instituciones y organizaciones. Reconoce al personal por **rostro** o **código QR**, registra entradas y salidas, genera carnés institucionales (fotochecks) en PNG y PDF, y ofrece importación histórica de asistencias desde Excel/CSV con reportes exportables.

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Características](#-características)
- [Tecnologías](#-tecnologías)
- [Inicio Rápido — Docker](#-inicio-rápido--docker)
- [Instalación Local](#-instalación-local)
- [Configuración](#-configuración)
- [Uso del Sistema](#-uso-del-sistema)
- [Importación de Asistencias](#-importación-de-asistencias)
- [Fotocheck / Carnés Institucionales](#-fotocheck--carnés-institucionales)
- [Reportes y Exportación](#-reportes-y-exportación)
- [Base de Datos PostgreSQL](#-base-de-datos-postgresql)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Referencia de URLs](#-referencia-de-urls)
- [API de Cámara](#-api-de-cámara)
- [Arquitectura](#-arquitectura)
- [Mejoras Recientes](#-mejoras-recientes)
- [Solución de Problemas](#-solución-de-problemas)
- [Licencia y Autor](#-licencia-y-autor)

---

## 📖 Descripción

El personal o alumnos se acercan al kiosco y son reconocidos automáticamente por rostro o código QR — sin entrada manual. El sistema:

- Registra **check-in** y **check-out** con prevención de duplicados multicapa
- Importa asistencias históricas desde archivos **Excel/CSV** de equipos biométricos
- Genera **carnés institucionales** (PNG + PDF imprimible) con foto circular, QR y datos del puesto
- Provee un **panel de administración** completo para gestionar personal, cámaras, registros y configuración
- Ofrece un **kiosco público** con UI dark glassmorphism, stream MJPEG y audio Web API

---

## ✨ Características

### Reconocimiento
- **Reconocimiento facial en tiempo real** — MTCNN + InceptionResnetV1 (embeddings 512-d, distancia L2)
- **Asistencia por código QR** — QR personal basado en UUID con logo institucional embebido
- **Modo híbrido** — rostro y QR operan simultáneamente; el primero en disparar registra la asistencia
- **Buffer de estabilidad temporal** — confirmación en 3 frames antes de registrar
- **Caché de embeddings robusta** — 1 embedding por persona; fotos corruptas se omiten con advertencia

### Asistencia
- **Check-in / Check-out automático** — primer escaneo = entrada, segundo (después de ventana configurable) = salida
- **Prevención de duplicados multicapa** — debounce de 10 s por persona, feedback "ya fue registrado" cada 5 s
- **Soporte multi-cámara** — webcam por índice o URL RTSP/HTTP
- **Umbrales configurables** — global + por cámara

### Gestión de Personal
- **Registro individual** — foto desde webcam o archivo, con generación inmediata de QR y fotocheck
- **Edición de perfiles** — actualización de nombre, DNI, cargo, área, horario, teléfono, email, clase
- **Importación masiva** — CSV o Excel con detección automática de columnas en español e inglés
- **Importación histórica** — asistencias de sistemas biométricos externos con mapeo inteligente
- **Placeholders automáticos** — DNIs no registrados generan un perfil "Desconocido" para no perder historial

### Reportes
- **Tabla de asistencias** — filtrable por nombre, área y rango de fechas
- **Exportar a Excel** — reporte oficial IESTP Paucartambo con formato por mes
- **Exportar a CSV** — descarga directa con todos los campos
- **Impresión** — CSS optimizado para impresión oculta la barra lateral y controles

### Fotocheck
- **Generación automática** en PNG (alta resolución) y PDF (imprimible)
- **Panel masivo** — regenera carnés para todo el personal desde `/credentials/`
- **QR con logo** — ERROR_CORRECT_H con logo institucional superpuesto al centro

---

## 🔧 Tecnologías

| Capa | Tecnología |
|------|-----------|
| Framework backend | Django 5.2.14 |
| Lenguaje | Python 3.14 |
| Detección facial | MTCNN (facenet-pytorch 2.6.0) |
| Embeddings faciales | InceptionResnetV1 — vggface2 pretrained |
| Framework ML | PyTorch 2.x |
| Visión por computadora | OpenCV 4.x |
| Generación QR | qrcode 8.x + Pillow 12 |
| Lectura QR | `cv2.QRCodeDetector` (sin dependencias extra) |
| Carné / PDF | Pillow 12 (overlay PNG) + ReportLab 4.x (PDF) |
| Streaming de video | MJPEG multipart sobre HTTP |
| Base de datos | PostgreSQL 17+ (producción) |
| Adaptador DB | psycopg2-binary 2.9 |
| Audio | Pygame (servidor) + Web Audio API (navegador) |
| Excel / importación | openpyxl |
| Frontend | Vanilla JS, CSS glassmorphism, Font Awesome |

---

## 🐳 Inicio Rápido — Docker

La forma más rápida de ejecutar el sistema sin instalar Python ni dependencias ML localmente.

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/install/) v2.20+
- Cámara conectada al host (opcional)

> **Aviso de tamaño:** La primera build descarga PyTorch (~1–2 GB) y otras librerías pesadas. Esperar 5–8 GB de imagen total y 10–20 minutos en la primera compilación.

### Pasos

```bash
# 1. Clonar y configurar
git clone git@github.com:Wil-1302/Sistema-de-control-de-asistencia.git
cd Sistema-de-control-de-asistencia
cp .env.example .env
# Editar .env: establecer DB_PASSWORD, SECRET_KEY

# 2. Construir e iniciar
docker compose up --build

# 3. Crear superusuario (admin)
docker compose exec web python manage.py createsuperuser

# 4. Abrir en el navegador
# http://localhost:8000/
```

### Habilitar cámara (Linux)

Editar `docker-compose.yml` y descomentar el bloque `devices`:

```yaml
devices:
  - /dev/video0:/dev/video0
```

```bash
sudo usermod -aG video $USER   # cerrar sesión y volver a entrar
docker compose down && docker compose up
```

### Comandos Docker útiles

```bash
docker compose logs -f                              # logs en vivo
docker compose down                                  # detener
docker compose build --no-cache                     # rebuild limpio
docker compose exec web python manage.py <comando>  # cualquier manage.py
docker compose exec web bash                         # shell dentro del contenedor
docker compose exec web python manage.py migrate    # aplicar migraciones
```

---

## 💻 Instalación Local

### 1. Clonar el repositorio

```bash
git clone git@github.com:Wil-1302/Sistema-de-control-de-asistencia.git
cd Sistema-de-control-de-asistencia
```

### 2. Crear y activar el entorno virtual

> ⚠️ El entorno virtual es `.venv/` (con punto), **no** `venv/`.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

**En Python 3.14 / Arch Linux (recomendado):**

```bash
bash install_314.sh
```

Este script:
1. Instala paquetes SDL2 del sistema vía `pacman`
2. Instala todos los paquetes Python desde `requirements-314.txt`
3. Instala `facenet-pytorch==2.6.0` con `--no-deps` (evita constraint falsa de `numpy<2.0`)
4. Compila Pygame desde fuente (no hay wheel para cp314)

> ❌ **No ejecutar** `pip install -r requirements.txt` en Python 3.14 — ese archivo apunta a versiones antiguas.

**En Python 3.12+ / otros sistemas:**

```bash
pip install -r requirements.txt
pip install --no-deps facenet-pytorch==2.6.0
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env según el entorno
```

### 5. Aplicar migraciones

```bash
python manage.py migrate
```

### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

### 7. Iniciar el servidor de desarrollo

```bash
python manage.py runserver
```

El kiosco está disponible en `http://127.0.0.1:8000/`.

---

## ⚙️ Configuración

### Variables de entorno (`.env`)

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `SECRET_KEY` | clave de dev insegura | Clave secreta Django — **cambiar en producción** |
| `DEBUG` | `True` | Poner `False` en producción |
| `ALLOWED_HOSTS` | `*` | Hosts permitidos separados por coma |
| `DB_NAME` | `ASISTENCIA_PERSONAL` | Nombre de la base de datos PostgreSQL |
| `DB_USER` | `postgres` | Usuario PostgreSQL |
| `DB_PASSWORD` | _(requerido)_ | Contraseña PostgreSQL |
| `DB_HOST` | `127.0.0.1` | Host PostgreSQL |
| `DB_PORT` | `5432` | Puerto PostgreSQL |
| `TIME_ZONE` | `America/Lima` | Zona horaria |
| `SDL_AUDIODRIVER` | _(sin definir)_ | Poner `dummy` en servidores sin audio |
| `SDL_VIDEODRIVER` | _(sin definir)_ | Poner `dummy` en servidores headless |

### Configuración del sistema (desde la UI)

Ir a **Configuración del sistema** (`/config/`) en el panel admin:

| Parámetro | Descripción |
|-----------|-------------|
| Reconocimiento facial habilitado | Activa/desactiva el reconocimiento facial globalmente |
| Asistencia por QR habilitada | Activa/desactiva la lectura de QR globalmente |
| Delay de check-out (min) | Minutos mínimos entre entrada y salida |
| Throttle de feedback duplicado (s) | Segundos entre mensajes "ya registrado" por persona |
| Umbral de reconocimiento global | Distancia L2 (0.1–1.0; menor = más estricto) |

### Configurar cámaras

1. Iniciar sesión como admin
2. Ir a **Camera Config** → **Add**
3. Ingresar nombre y fuente de cámara:
   - Webcam local: `0` (o `1`, `2` para cámaras adicionales)
   - IP camera: `rtsp://user:pass@192.168.1.100/stream`
   - HTTP MJPEG: `http://192.168.1.100:8080/video`
4. Opcionalmente establecer umbral de reconocimiento por cámara

---

## 🚀 Uso del Sistema

### Registro de personal (admin)

1. Iniciar sesión como admin
2. Ir a **Register** (`/capture_student/`)
3. Completar: nombre, DNI, email, teléfono, cargo, área, horario, clase/grupo
4. Capturar foto desde la webcam **o** subir un archivo de imagen
5. El sistema genera automáticamente: QR, recorte facial, carné PNG y PDF

### Edición de perfiles (admin)

1. Ir a **Students** (`/students/`)
2. Hacer clic en el perfil → **Edit** (`/students/<pk>/edit/`)
3. Actualizar cualquier campo: nombre, DNI, cargo, área, horario, email, teléfono, clase
4. Guardar — los cambios se reflejan inmediatamente

### Kiosco de asistencia (público)

1. Abrir `http://127.0.0.1:8000/` — redirige al kiosco
2. Presionar **Start Camera**
3. La persona mira a la cámara **o** muestra su QR
4. El sistema registra automáticamente:
   - **Primer escaneo del día** → Entrada registrada
   - **Después del delay configurado** → Salida registrada
   - **Ya marcado** → Tarjeta "Ya fue registrado" (sin duplicado en BD)

### Reporte de asistencias (admin)

1. Ir a **Attendance** (`/students/attendance/`)
2. Filtrar por nombre, área o rango de fechas
3. Exportar como **Reporte Oficial Excel** (formato IESTP por mes) o **CSV**
4. Imprimir la tabla filtrada directamente desde el navegador

---

## 📥 Importación de Asistencias

El módulo de importación acepta archivos **CSV** (UTF-8 o UTF-8 BOM) y **Excel (.xlsx)** y detecta automáticamente las columnas del archivo, incluyendo formatos de exportación de equipos biométricos.

### Columnas reconocidas

| Semántica | Aliases aceptados |
|-----------|------------------|
| DNI / código | `dni`, `cedula`, `documento`, `cod`, `nro documento` |
| Nombre | `nombre`, `name`, `apellidos y nombres`, `trabajador`, `colaborador` |
| Fecha | `fecha`, `date`, `dia`, `fecha acceso`, `fecha ingreso` |
| Hora entrada | `hora entrada`, `hora_entrada`, `time_in`, `checkin`, `entrada` |
| Hora salida | `hora salida`, `hora_salida`, `time_out`, `checkout`, `salida` |
| Fecha+hora | `fecha hora`, `datetime`, `timestamp`, `fecha_y_hora` |
| Email | `email`, `correo` |
| Cargo | `position`, `cargo`, `puesto` |
| Área | `area`, `área`, `departamento` |
| Horario | `work_schedule`, `horario`, `jornada` |

### Reglas de mapeo de tiempos

El sistema aplica estas reglas en orden estricto para evitar inversión de entrada/salida:

| Escenario del archivo | Resultado |
|----------------------|-----------|
| Una sola columna de tiempo/datetime | → `check_in_time` siempre |
| `hora entrada` con valor + `hora salida` con valor | → `check_in` y `check_out` respectivamente |
| `hora entrada` vacía + `hora salida` con valor | → promovido a `check_in_time` (nunca a salida) |
| Solo columna `hora salida` sin columna de entrada | → promovido a `check_in_time` |
| Sin ninguna hora válida en la fila | → fila omitida con advertencia |

> ✅ **Regla fundamental:** Si el archivo produce una sola hora (en cualquier columna), esa hora va a `check_in_time`. `check_out_time` solo se establece cuando hay dos tiempos reales distintos por fila.

### Manejo de DNI no registrado (placeholders)

Si el archivo trae un DNI que no existe en la base de datos:

- **Con nombre en el archivo** → Se crea el perfil completo y se guarda la asistencia.
- **Sin nombre en el archivo** → Se crea un perfil `Pendiente - DNI XXXXXXXX` que aparece como "Desconocido" en los reportes. Permite preservar el historial biométrico sin perder datos. Un segundo import del mismo DNI actualiza la asistencia sin crear duplicado.

### Logging de importación

Durante cada importación, el servidor imprime en consola el mapeo por fila:

```
INFO IMPORT fila 3 | DNI=12345678 | entrada=08:30:00 | salida=NULL | estado=Asistió [NUEVO]
INFO IMPORT fila 4 | DNI=87654321 | entrada=08:15:00 | salida=17:00:00 | estado=Completo
```

### Deduplicación

- Eventos con el mismo (DNI, fecha, hora, minuto, tipo) dentro del mismo archivo son ignorados.
- Si ya existe un registro para (persona, fecha), se actualiza: se guarda el `check_in` más temprano y el `check_out` más tardío del día.

### Flujo de importación histórica

```
Subir archivo
    │
    ├─► Detectar formato (CSV / XLSX)
    ├─► Mapear columnas (alias español/inglés)
    ├─► Por cada fila:
    │       ├─► Buscar persona por DNI
    │       │       ├─► Encontrada → usar perfil existente
    │       │       └─► No encontrada → crear perfil o placeholder
    │       ├─► Parsear fecha/hora → check_in o check_out
    │       └─► Guardar Attendance (crear o actualizar)
    └─► Redirigir al reporte filtrado por las fechas importadas
```

---

## 🪪 Fotocheck / Carnés Institucionales

El sistema genera carnés institucionales automáticamente para cada persona registrada.

### Especificaciones del carné

| Propiedad | Valor |
|-----------|-------|
| Imagen base | `plantilla.jpeg` (template IESTP Paucartambo) |
| Tamaño de salida | 1024 × 1536 px (portrait) |
| Tamaño de impresión | 86 × 129 mm a 300 DPI |
| Formatos | PNG (pantalla) + PDF (imprimible) |
| Corrección de error QR | ERROR_CORRECT_H (~30 % — soporta superposición del logo) |
| Detección facial | MTCNN recorte + máscara circular |

### Ubicación de assets

```
app1/static/app1/fotocheck_assets/
    plantilla.jpeg   ← template de fondo del carné (versionado en git)
    logo.png         ← logo institucional (embebido en el centro del QR)
```

### Generación individual

Desde el perfil de la persona: **Students** → perfil → **Credential** → botón **Regenerate**.

### Generación masiva

```bash
# Desde la UI
# /credentials/ → clic en "Generate All"

# Desde el shell Django
source .venv/bin/activate
python manage.py shell -c "
from app1.models import Student
from app1.fotocheck import generate_all_fotocheck_assets
for s in Student.objects.filter(image__isnull=False).exclude(image=''):
    r = generate_all_fotocheck_assets(s)
    print(s.name, r)
"

# Desde Docker
docker compose exec web python manage.py shell -c "
from app1.models import Student
from app1.fotocheck import generate_all_fotocheck_assets
for s in Student.objects.filter(image__isnull=False).exclude(image=''):
    generate_all_fotocheck_assets(s)
    print(s.name, 'OK')
"
```

### Imprimir a tamaño real (86 × 129 mm)

1. Descargar el **PDF** desde `/students/<pk>/credential/` → **Download PDF**
2. Abrir en cualquier visor PDF (Acrobat, Okular, Evince)
3. En el diálogo de impresión, establecer **escala al 100% / tamaño real**
4. El PDF está configurado a 86 × 129 mm a 300 DPI — imprime al tamaño correcto sin ajustes

---

## 📊 Reportes y Exportación

El reporte de asistencias en `/students/attendance/` soporta:

- **Búsqueda** por nombre o DNI
- **Filtro** por área/departamento
- **Rango de fechas** (desde / hasta)
- **Exportar a Excel** — Reporte oficial con formato por día del mes, sombreado de fines de semana y totales
- **Exportar a CSV** — Descarga directa, separado por comas, UTF-8
- **Impresión** — CSS optimizado oculta la barra lateral y controles

### Columnas del reporte

`Foto | DNI | Nombre | Cargo | Área | Horario | Fecha | Entrada | Salida | Duración | Estado`

### Estados de asistencia

| Estado | Condición |
|--------|-----------|
| ✅ Completo | `check_in_time` y `check_out_time` presentes |
| ✅ Asistió | Solo `check_in_time` presente |
| — | Sin registro de entrada |

---

## 🐘 Base de Datos PostgreSQL

El proyecto usa **PostgreSQL** por defecto con base de datos `ASISTENCIA_PERSONAL`.

### Configuración local (Arch Linux)

```bash
# Instalar e iniciar PostgreSQL
sudo pacman -S postgresql
sudo systemctl enable --now postgresql

# Crear base de datos
sudo -u postgres psql <<'SQL'
CREATE DATABASE "ASISTENCIA_PERSONAL";
SQL

# Aplicar migraciones
source .venv/bin/activate
python manage.py migrate
```

### Backup y restauración

```bash
# Backup
pg_dump -U postgres ASISTENCIA_PERSONAL > backup_asistencia.sql

# Restaurar
psql -U postgres ASISTENCIA_PERSONAL < backup_asistencia.sql
```

> **Trampa de migraciones (squash):** La base de código fue reiniciada en `0001_initial.py` después de que muchas migraciones ya habían sido aplicadas en PostgreSQL. Si `django_migrations` ya contiene `0001_initial` pero faltan columnas en las tablas, crear migraciones correctivas con operaciones `AddField` explícitas — **nunca** borrar filas de `django_migrations` ni recrear las tablas.

---

## 📁 Estructura del Proyecto

```
.
├── app1/                                   # Aplicación Django principal
│   ├── models.py                           # Student, Attendance, CameraConfiguration, SystemConfig
│   ├── views.py                            # Vistas + CameraManager (pipeline MJPEG + ML)
│   ├── fotocheck.py                        # Generador de carnés institucionales (PNG + PDF)
│   ├── utils.py                            # Generación de QR, lógica de registro de asistencia
│   ├── report_excel.py                     # Builder de reporte Excel oficial (openpyxl)
│   ├── report_template.py                  # CLI: rellenar plantilla Excel desde CSV biométrico
│   ├── urls.py                             # Patrones de URL de la app
│   ├── admin.py                            # Registro en el admin de Django
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   ├── 0002_add_missing_student_fields.py
│   │   └── 0003_add_systemconfig_table.py
│   ├── static/app1/fotocheck_assets/       # Assets del carné (versionados en git)
│   │   ├── plantilla.jpeg                  # Template de fondo del carné
│   │   └── logo.png                        # Logo institucional para el centro del QR
│   └── suc.wav                             # Sonido de éxito (Pygame en servidor)
├── Project101/                             # Paquete del proyecto Django
│   ├── settings.py                         # Configuración (BD, zona horaria, media)
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── templates/                              # Todos los templates HTML (nivel de proyecto)
│   ├── base.html                           # Layout compartido + CSS dark glassmorphism
│   ├── attendance_kiosk.html               # Kiosco público (MJPEG + overlay de eventos)
│   ├── capture_student.html                # Registro de personal (webcam + carga de archivo)
│   ├── student_list.html                   # Lista de personal con búsqueda y filtros
│   ├── student_detail.html                 # Detalle de persona con historial de asistencia
│   ├── student_edit.html                   # Formulario de edición de perfil
│   ├── student_attendance_list.html        # Reporte de asistencias con exportación
│   ├── import_students.html                # Importación masiva CSV/Excel
│   ├── credentials_list.html               # Panel de gestión masiva de fotochecks
│   ├── student_credential.html             # Vista previa y descarga del carné
│   └── system_config.html                  # Configuración del sistema (toggles iOS-style)
├── media/                                  # Archivos subidos (ignorados en git)
│   ├── students/                           # Fotos de personal
│   ├── qrcodes/                            # QR generados
│   ├── faces/                              # Recortes circulares de rostro
│   └── fotochecks/                         # PNG y PDF de carnés generados
├── Dockerfile                              # Imagen Python 3.14-slim con todas las deps
├── docker-compose.yml                      # Servicios web + PostgreSQL
├── entrypoint.sh                           # Esperar BD → migrate → runserver
├── .dockerignore
├── requirements.txt                        # Dependencias (referencia Python 3.12+)
├── requirements-314.txt                    # Dependencias (Python 3.14 / Arch Linux)
├── requirements-docker.txt                 # Dependencias (build Docker headless)
├── install_314.sh                          # Script de instalación local Python 3.14
├── manage.py
├── .env.example                            # Template de variables de entorno
└── CLAUDE.md                               # Instrucciones para Claude Code AI
```

---

## 🔗 Referencia de URLs

| URL | Método | Acceso | Descripción |
|-----|--------|--------|-------------|
| `/` | GET | Público | Redirección al kiosco |
| `/kiosk/` | GET | Público | Kiosco de asistencia |
| `/login/` | GET/POST | Público | Inicio de sesión |
| `/logout/` | GET | Auth | Cerrar sesión |
| `/capture_student/` | GET/POST | Admin | Registrar nueva persona |
| `/import/` | GET/POST | Admin | Importación masiva CSV/Excel |
| `/students/` | GET | Admin | Lista de personal |
| `/students/<pk>/` | GET | Admin | Detalle de persona |
| `/students/<pk>/edit/` | GET/POST | Admin | Editar perfil de persona |
| `/students/<pk>/authorize/` | POST | Admin | Activar/desactivar acceso facial+QR |
| `/students/<pk>/delete/` | GET/POST | Admin | Eliminar persona |
| `/students/<pk>/credential/` | GET | Admin | Vista previa carné imprimible |
| `/students/<pk>/fotocheck/png/` | GET | Admin | Descargar fotocheck PNG |
| `/students/<pk>/fotocheck/pdf/` | GET | Admin | Descargar fotocheck PDF |
| `/students/<pk>/fotocheck/regen/` | POST | Admin | Regenerar todos los assets del carné |
| `/students/<pk>/regenerate-qr/` | POST | Admin | Regenerar QR |
| `/students/<pk>/qr/` | GET | Admin | Descargar QR PNG |
| `/credentials/` | GET | Admin | Panel masivo de fotochecks |
| `/credentials/generate/` | POST | Admin | Regenerar carnés de todo el personal |
| `/students/attendance/` | GET | Admin | Reporte de asistencias |
| `/students/attendance/export/csv/` | GET | Admin | Exportar CSV |
| `/students/attendance/export/excel/` | GET | Admin | Exportar Excel oficial |
| `/config/` | GET/POST | Admin | Configuración del sistema |
| `/camera-config/` | GET/POST | Admin | Agregar cámara |
| `/camera-config/list/` | GET | Admin | Listar cámaras |
| `/camera-config/update/<pk>/` | GET/POST | Admin | Editar cámara |
| `/camera-config/delete/<pk>/` | POST | Admin | Eliminar cámara |
| `/camera/start/` | POST | Admin | Iniciar threads de cámara |
| `/camera/stop/` | POST | Admin | Detener todos los threads |
| `/camera/status/` | GET | Admin | JSON: `{running, error, logs[]}` |
| `/camera/stream/` | GET | Público | Stream MJPEG multipart |

---

## 📹 API de Cámara

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/camera/start/` | POST | Inicia threads de `CameraManager` |
| `/camera/stop/` | POST | Detiene todos los threads y libera capturas |
| `/camera/status/` | GET | JSON: `{running, error, logs[]}` — consultado cada 1 s |
| `/camera/stream/` | GET | Stream MJPEG para `<img src="...">` |

El array `logs[]` transporta eventos de asistencia (`checked_in`, `checked_out`, `already_done`, `qr_invalid`, `error`) que el frontend renderiza como tarjetas superpuestas.

---

## 🏗️ Arquitectura

### Pipeline ML (por frame)

```
cap.read() → frame (original, sin voltear)
    │
    ├─► _decode_qr(frame)              QR: resize→640px, gris → cv2.QRCodeDetector
    │         └─► _handle_qr()         debounce 10s por persona + escritura BD
    │
    ├─► _detect_and_encode(rgb)         MTCNN detect → InceptionResnetV1 embed
    │         └─► _recognize()          distancia L2 vs embeddings en caché
    │                   └─► _handle_face()  buffer 3 frames → escritura BD
    │
    └─► cv2.flip(frame, 1)             Voltear para mostrar (efecto espejo)
              └─► coordenadas bbox      remapeadas: mx = ancho - x
              └─► imencode → cola MJPEG
```

### Pipeline de fotocheck

```
generate_all_fotocheck_assets(student)
    │
    ├─► generate_qr_with_logo()        qrcode (ERROR_CORRECT_H) + logo.png → media/qrcodes/
    ├─► save_face_crop()               MTCNN recorte + máscara circular → media/faces/
    ├─► generate_fotocheck_png()       Abrir plantilla → pegar foto, texto, QR → media/fotochecks/
    └─► generate_fotocheck_pdf()       PNG → canvas ReportLab a 86×129 mm → media/fotochecks/
```

### Capas de prevención de duplicados

| Capa | Constante | Efecto |
|------|-----------|--------|
| Debounce por persona | `_COOLDOWN_SECONDS = 10` | Bloquea escrituras BD dentro de 10 s |
| Throttle de display | `_DISPLAY_THROTTLE = 5.0` | Feedback "ya registrado" máx. 1 vez cada 5 s |
| Ventana de check-out | `SystemConfig.checkout_delay_minutes` | Salida solo después de N minutos |
| Throttle frontend | `_ALREADY_DONE_MS = 12000` (JS) | Tarjeta de persona máx. 1 vez cada 12 s |

### Caché de embeddings

- Reconstruida cada 30 s (`_CACHE_TTL = 30.0`) o invalidada inmediatamente al cambiar un estudiante
- **1 embedding por persona** — fotos con múltiples rostros usan solo el primero (con advertencia)
- Fotos corruptas o ilegibles se omiten y se registran como warnings en los logs
- Verificación de integridad antes de cachear: `len(known_enc) == len(known_names)`

---

## 🆕 Mejoras Recientes

### Corrección crítica: inversión de entrada/salida en importación

**Problema:** Al importar archivos Excel con columnas `hora entrada` y `hora salida`, si una fila tenía la celda de entrada vacía y salida con valor, el tiempo se guardaba en `check_out_time` (columna SALIDA) en lugar de `check_in_time` (ENTRADA).

**Causa raíz:** La función `_parse_row_times()` en `app1/views.py` incluía la condición `and 'time_in' not in col_map` que bloqueaba la promoción cuando ambas columnas existían en el encabezado, aunque la celda de entrada estuviera vacía en la fila.

**Fix aplicado:** La promoción ahora es incondicional — si una fila produce `check_in=None` y `check_out≠None`, el tiempo se promueve siempre a `check_in_time`. Dos tiempos reales en la misma fila se respetan como entrada y salida sin cambios.

### Logging de mapeo por fila

El servidor registra en consola el resultado exacto de cada fila importada:
```
INFO IMPORT fila N | DNI=XXXXXXXX | entrada=HH:MM:SS | salida=NULL | estado=Asistió [NUEVO]
```

### Edición de perfiles de personal

Nueva vista `/students/<pk>/edit/` con formulario completo que permite actualizar todos los campos sin necesidad del panel `/admin/` de Django.

### Placeholders para historial biométrico

DNIs importados que no existen en la BD generan automáticamente un perfil temporal. Aparecen como "Desconocido" en los reportes y permiten preservar el historial completo sin pérdida de datos.

### Sistema de configuración singleton (`SystemConfig`)

Modelo singleton accesible vía `SystemConfig.get()` que centraliza todos los parámetros del sistema: umbrales de reconocimiento, delays de check-out, flags de habilitación de facial/QR.

---

## 🔧 Solución de Problemas

### La cámara no inicia

```
Error: Cannot open camera: <nombre>
```

- Verificar el índice/URL de la fuente en Camera Config
- Asegurarse de que ningún otro proceso tenga la cámara ocupada
- Para cámaras IP, probar la URL en VLC primero

### Rostro no reconocido

- Verificar que la persona esté **authorized=True** en el panel de admin
- La iluminación importa — luz frontal pareja funciona mejor
- Bajar el umbral de reconocimiento (ej. `0.6` → `0.5`)
- La caché de embeddings se actualiza cada 30 s — esperar después de autorizar una persona nueva
- Revisar logs de Django: `WARNING: No face detected in photo for student` — re-registrar con retrato individual claro

### Fotocheck PNG/PDF no generado

- Verificar que `media/fotochecks/` exista y sea escribible
- Ejecutar en el shell Django:
  ```python
  from app1.fotocheck import validate_assets
  print(validate_assets())   # debe retornar (True, 'Assets OK')
  ```
- Si faltan assets: copiar `plantilla.jpeg` y `logo.png` a `app1/static/app1/fotocheck_assets/`

### Error de conexión PostgreSQL

```
django.db.utils.OperationalError: connection refused
```

- Verificar que PostgreSQL esté corriendo: `systemctl status postgresql`
- Revisar valores en `.env`: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`
- En Docker: `docker compose logs db`

### Error de audio Pygame en servidor headless

```
pygame.error: No available audio device
```

Agregar al `.env`:
```
SDL_AUDIODRIVER=dummy
SDL_VIDEODRIVER=dummy
```

### Python 3.14 — sin wheel compatible

Ejecutar `bash install_314.sh` en lugar de `pip install -r requirements.txt`.

### Conflicto de numpy con facenet-pytorch

```bash
pip install --no-deps facenet-pytorch==2.6.0
```

### Trampa de migraciones (squash)

Si faltan columnas en las tablas pero `django_migrations` ya tiene `0001_initial`:

```bash
# Crear migración correctiva — NO borrar filas de django_migrations
python manage.py makemigrations app1 --name add_missing_fields
python manage.py migrate
```

### Docker — dispositivo de cámara no encontrado

```yaml
# En docker-compose.yml, comentar el bloque devices si no hay cámara:
# devices:
#   - /dev/video0:/dev/video0
```

### Docker — error OpenCV libGL

```bash
docker compose build --no-cache
```

### Error de codificación al importar CSV

Los archivos CSV deben estar en **UTF-8** o **UTF-8 BOM**. En Excel: "Guardar como → CSV UTF-8 (con BOM)".

---

## 📄 Licencia y Autor

Este proyecto está bajo licencia **MIT** — ver [LICENSE](LICENSE) para detalles.

**Wil-1302**
- GitHub: [@Wil-1302](https://github.com/Wil-1302)
- Email: travezanorodriguezjonh@gmail.com

---

*Construido con Django 5.2.14, PyTorch 2.x, OpenCV 4.x, ReportLab 4.x y Python 3.14.*
