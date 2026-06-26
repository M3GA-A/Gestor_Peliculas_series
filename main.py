import json
from datetime import date

# Path ayuda a construir rutas de archivos de forma segura.
from pathlib import Path

# Literal limita un campo a valores concretos. Optional indica que un campo puede ser None.
from typing import Literal, Optional

# FastAPI crea la API. HTTPException sirve para devolver errores HTTP.
# Query permite definir parámetros opcionales en la URL, como ?categoria=Serie.
from fastapi import FastAPI, HTTPException, Query

# BaseModel y Field vienen de Pydantic.
# field_validator valida campos individuales y model_validator valida reglas entre campos.
from pydantic import BaseModel, Field, StrictBool, field_validator, model_validator


# Ruta del archivo JSON que usaremos como base de datos.
# __file__ es la ruta de este main.py, así que data.json se busca en la misma carpeta.
JSON_FILE = Path(__file__).with_name("data.json")
CURRENT_YEAR = date.today().year


# Modelo principal de datos.
# Cada elemento del JSON debe tener esta estructura: película, serie, juego, etc.
class MediaItem(BaseModel):
    # El id es opcional al crear un elemento porque la API lo genera automáticamente.
    id: Optional[int] = None

    # Field permite añadir validaciones y ejemplos para Swagger (/docs).
    titulo: str = Field(..., min_length=1, examples=["Dune: Parte Dos"])

    # El año debe estar entre 1900 y el año actual.
    anio: int = Field(..., ge=1900, le=CURRENT_YEAR, examples=[2024])

    # Literal hace que solo se acepten estos valores exactos.
    categoria: Literal["Película", "Serie"] = Field(..., examples=["Película"])
    estado: Literal["Pendiente", "Viendo", "Completado"] = Field(
        ..., examples=["Pendiente"]
    )

    # La puntuación puede ser None si todavía no se ha valorado.
    # Si tiene valor, debe estar entre 1 y 10.
    puntuacion: Optional[int] = Field(None, ge=1, le=10, examples=[9])

    director: str = Field(..., min_length=1, examples=["Denis Villeneuve"])
    plataforma: str = Field(..., min_length=1, examples=["Cine"])
    duracion: int = Field(..., gt=0, examples=[166])

    # Campo opcional para guardar una URL o ruta de portada si se quiere usar una imagen real.
    imagen: Optional[str] = Field(None, examples=["https://ejemplo.com/portada.jpg"])

    # StrictBool exige que favorito sea true o false, no textos como "si" o "no".
    favorito: StrictBool = Field(False, examples=[True])

    # Esta validación limpia espacios al inicio/final y evita textos vacíos.
    @field_validator("titulo", "director", "plataforma")
    @classmethod
    def validar_texto_no_vacio(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Este campo no puede estar vacío")

        return value

    # Esta validación compara varios campos entre sí.
    @model_validator(mode="after")
    def validar_estado_y_puntuacion(self):
        if self.estado == "Pendiente" and self.puntuacion is not None:
            raise ValueError("Si el estado es Pendiente, la puntuación debe ser null")

        if self.estado == "Completado" and self.puntuacion is None:
            raise ValueError("Si el estado es Completado, la puntuación es obligatoria")

        return self


# Creamos la aplicación FastAPI.
# El título y la versión aparecen en la documentación automática /docs.
app = FastAPI(title="Gestor de Películas y Series", version="1.0")


# Normaliza cada registro leído desde data.json.
# Así evitamos problemas si algún dato antiguo usa "año" en vez de "anio".
def normalize_item(item: dict) -> dict:
    item = item.copy()

    # Algunos datos antiguos pueden venir con la clave "año".
    # La API trabaja con "anio" para evitar problemas con nombres de variables.
    if "anio" not in item and "año" in item:
        item["anio"] = item["año"]

    item.pop("año", None)
    return item


# Función auxiliar para leer todos los datos del JSON.
# Devuelve una lista de diccionarios: list[dict].
def read_json() -> list[dict]:
    # Si el archivo no existe, devolvemos una lista vacía para evitar errores.
    if not JSON_FILE.exists():
        return []

    # Abrimos el archivo en modo lectura con codificación UTF-8 para aceptar acentos.
    with JSON_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return [normalize_item(item) for item in data]


# Función auxiliar para guardar datos en el JSON.
# Recibe toda la lista actualizada y sobrescribe el archivo.
def write_json(data: list[dict]) -> None:
    with JSON_FILE.open("w", encoding="utf-8") as file:
        # indent=4 hace que el JSON quede bonito y legible.
        # ensure_ascii=False conserva caracteres como í, ñ, +, etc.
        json.dump(data, file, indent=4, ensure_ascii=False)


# Función auxiliar para buscar un elemento por id.
# La reutilizamos en GET por id y DELETE para no repetir código.
def find_item(db: list[dict], item_id: int) -> dict:
    for item in db:
        if item["id"] == item_id:
            return item

    # Si no encontramos el id, devolvemos error 404.
    raise HTTPException(status_code=404, detail="Elemento no encontrado")


# Comprueba que no exista otro elemento con el mismo título y año.
# exclude_id permite ignorar el propio elemento cuando hacemos PUT.
def validate_unique_title_year(
    db: list[dict], titulo: str, anio: int, exclude_id: Optional[int] = None
) -> None:
    normalized_title = titulo.strip().lower()

    for item in db:
        same_title = item["titulo"].strip().lower() == normalized_title
        same_year = item.get("anio") == anio
        same_item = exclude_id is not None and item["id"] == exclude_id

        if same_title and same_year and not same_item:
            raise HTTPException(
                status_code=400,
                detail="Ya existe un elemento con ese título y año",
            )


# GET / es una ruta simple para comprobar que la API está funcionando.
@app.get("/", tags=["Inicio"])
def inicio():
    return {
        "mensaje": "API funcionando",
        "docs": "/docs",
        "items": "/items",
    }


# GET /items devuelve todos los elementos.
# También permite filtrar desde la URL, por ejemplo:
# /items?categoria=Serie
# /items?estado=Viendo
# /items?favorito=true
@app.get("/items", tags=["Colección"])
def get_all_items(
    categoria: Optional[str] = Query(None, examples=["Serie"]),
    estado: Optional[str] = Query(None, examples=["Viendo"]),
    favorito: Optional[bool] = None,
):
    db = read_json()

    # Si categoria viene en la URL, filtramos solo los elementos de esa categoría.
    if categoria is not None:
        db = [item for item in db if item["categoria"].lower() == categoria.lower()]

    # Si estado viene en la URL, filtramos por ese estado.
    if estado is not None:
        db = [item for item in db if item["estado"].lower() == estado.lower()]

    # Si favorito viene en la URL, filtramos true o false.
    if favorito is not None:
        db = [item for item in db if item["favorito"] == favorito]

    return db


# GET /items/{item_id} devuelve un único elemento por su id.
# Ejemplo: /items/1
@app.get("/items/{item_id}", tags=["Colección"])
def get_item(item_id: int):
    db = read_json()
    return find_item(db, item_id)


# POST /items crea un elemento nuevo.
# FastAPI valida que el cuerpo de la petición tenga la estructura de MediaItem.
@app.post("/items", response_model=MediaItem, tags=["Colección"])
def create_item(item: MediaItem):
    db = read_json()
    validate_unique_title_year(db, item.titulo, item.anio)

    # Calculamos el siguiente id tomando el id más alto y sumando 1.
    # default=0 evita errores si la lista está vacía.
    new_id = max([element["id"] for element in db], default=0) + 1

    item.id = new_id

    # Convertimos el modelo Pydantic a diccionario antes de guardarlo en JSON.
    db.append(item.model_dump())
    write_json(db)

    return item


# PUT /items/{item_id} actualiza un elemento completo.
# El id se toma de la URL y el resto de datos vienen en el cuerpo de la petición.
@app.put("/items/{item_id}", response_model=MediaItem, tags=["Colección"])
def update_item(item_id: int, updated_item: MediaItem):
    db = read_json()
    find_item(db, item_id)
    validate_unique_title_year(db, updated_item.titulo, updated_item.anio, item_id)

    for index, item in enumerate(db):
        if item["id"] == item_id:
            # Mantenemos el id original para que no cambie aunque venga otro id en el body.
            updated_item.id = item_id
            db[index] = updated_item.model_dump()
            write_json(db)
            return updated_item

    raise HTTPException(status_code=404, detail="Elemento no encontrado")


# DELETE /items/{item_id} elimina un elemento por id.
@app.delete("/items/{item_id}", tags=["Colección"])
def delete_item(item_id: int):
    db = read_json()
    item = find_item(db, item_id)

    db.remove(item)
    write_json(db)

    return {"mensaje": "Elemento eliminado", "item": item}
