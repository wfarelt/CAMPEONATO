# Campeonato - Tournament Management System

Sistema de gestión de torneos deportivos desarrollado con Django.

## 📋 Descripción

Aplicación web para administrar torneos deportivos, permitiendo gestionar equipos, jornadas, partidos, clasificaciones y estadísticas de los participantes.

## 🚀 Requisitos Previos

- Python 3.10+
- Django 5.1.4 (instalado desde `requirements.txt`)
- SQLite3

## 📦 Instalación

### 1. Clonar el repositorio
```bash
git clone <url-repositorio>
cd CAMPEONATO
```

### 2. Crear un entorno virtual
```bash
python -m venv venv
source venv/Scripts/activate  # En Windows
# En Linux/macOS:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecutar migraciones
```bash
python manage.py migrate
```

### 5. Crear usuario administrador
```bash
python manage.py createsuperuser
```

### 6. Ejecutar el servidor de desarrollo
```bash
python manage.py runserver
```

La aplicación estará disponible en `http://localhost:8000`

## 📁 Estructura del Proyecto

```
campeonato/
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── core/               # utilidades generales
│   │   ├── models.py
│   │   ├── choices.py
│   │   └── mixins.py
│   ├── users/              # usuarios, roles
│   │   ├── models.py
│   │   └── permissions.py
│   ├── teams/              # equipos y jugadores
│   │   ├── models.py
│   │   ├── services.py
│   │   └── selectors.py
│   ├── tournaments/        # torneos
│   │   ├── models.py
│   │   ├── services.py
│   │   └── fixtures.py
│   ├── matches/            # partidos
│   │   ├── models.py
│   │   ├── signals.py
│   │   ├── services.py
│   │   └── stats.py
│   ├── standings/          # tabla de posiciones
│   │   ├── services.py
│   │   └── selectors.py
│   ├── referees/           # arbitros
│   │   └── models.py
│   ├── fields/             # canchas
│   │   └── models.py
│   ├── payments/           # pagos de inscripcion
│   │   └── models.py
│   └── notifications/      # WhatsApp, email, push
├── tournament/             # modulo legacy de vistas/urls/templates (sin modelos activos)
├── templates/
├── static/
├── media/
├── requirements.txt
└── manage.py
```

## 🎯 Características Principales

- **Gestión de Equipos**: Crear y administrar equipos participantes
- **Jornadas**: Organizar el torneo en jornadas o fases
- **Partidos**: Registrar resultados de los encuentros
- **Clasificación**: Ver tabla de posiciones actualizada automáticamente
- **Estadísticas**: Datos detallados de rendimiento de equipos y jugadores
- **Admin Panel**: Panel administrativo para gestionar todos los datos

## 🔧 Configuración

Edita `config/settings.py` para ajustar:
- Base de datos
- Idioma y zona horaria
- Variables de entorno
- Aplicaciones instaladas

## 📊 Modelos Principales

- **Team**: Información de los equipos
- **Match**: Partidos jugados
- **Matchday**: Jornadas del torneo
- **Estadísticas y clasificaciones**

## 🛠️ Desarrollo

### Crear nuevas migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### Shell interactivo
```bash
python manage.py shell
```

### Ejecutar tests
```bash
python manage.py test
```

## 📝 Notas

- Las imágenes de logos de equipos se guardan en `media/team_logos/`
- Los estilos CSS están en `static/tournament/css/`
- Las plantillas HTML están en `tournament/templates/tournament/`
- Los modelos activos viven en `apps/*`; `tournament/models.py` funciona como wrapper de compatibilidad para imports antiguos

## 📧 Contacto y Soporte

Para reportar problemas o sugerencias, crear un issue en el repositorio.

## 🔐 Seguridad

- No almacenes contraseñas, claves ni otros secretos en este archivo o en el repositorio.
- Si una credencial publicada anteriormente aquí fue real o se reutilizó en algún entorno, cámbiala inmediatamente y revisa las cuentas afectadas.
- Configura `SECRET_KEY` y los demás valores sensibles mediante variables de entorno.

## 📄 Licencia

Este proyecto está bajo licencia [Especificar licencia].
