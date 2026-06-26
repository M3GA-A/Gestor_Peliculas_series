# Gestor de Películas y Series

Este proyecto desarrolla una solución ligera para administrar una colección personal de películas y series mediante una interfaz web y una API REST. La aplicación está construida con FastAPI y utiliza un archivo JSON local como almacenamiento, lo que permite ejecutarla de forma sencilla sin depender de una base de datos externa.

## Estructura del proyecto

- **main.py**: implementa la API principal, los endpoints REST y la lógica de persistencia en el archivo JSON.
- **app.py**: incluye la interfaz web, el renderizado HTML/CSS y el montaje de la API en la ruta /api.
- **data.json**: almacena los registros de películas y series en formato JSON.
- **requirements.txt**: contiene las dependencias necesarias para ejecutar el proyecto.

## Tecnologías utilizadas

- **FastAPI** para la creación de la API y la documentación automática.
- **Uvicorn** como servidor ASGI para ejecutar la aplicación.
- **Pydantic** para la validación de modelos y datos de entrada.
- **HTML/CSS** para la interfaz de usuario.
- **JSON** como mecanismo de almacenamiento local.

## Requisitos previos

- Python 3.9 o superior
- pip

## Instalación

1. Acceder al directorio del proyecto:

```bash
cd /ruta/hasta/Gestor_Peliculas
```

2. Crear un entorno virtual (recomendado):

```bash
python3 -m venv venv
```

3. Activar el entorno virtual:

En macOS/Linux:

```bash
source venv/bin/activate
```

En Windows:

```bash
venv\Scripts\activate
```

4. Instalar las dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución

### Opción 1: ejecutar únicamente la API

```bash
uvicorn main:app --reload
```

Acceso disponible:

- Documentación interactiva: http://127.0.0.1:8000/docs

### Opción 2: ejecutar la interfaz web y la API

```bash
uvicorn app:app --reload
```

Accesos disponibles:

- Interfaz principal: http://127.0.0.1:8000
- Documentación de la API: http://127.0.0.1:8000/api/docs

## Funcionalidades principales

- Gestión de películas y series.
- Búsqueda y filtrado por título, director, plataforma, categoría y estado.
- Creación, edición y eliminación de registros.
- Validación de datos, incluyendo título, año, categoría, estado, puntuación, director, plataforma y duración.

## Consideraciones adicionales

- Los datos se almacenan en **data.json**.
- Si el archivo no existe, la aplicación lo gestiona como una colección vacía.
- No es necesario configurar una base de datos externa para utilizar el proyecto.
