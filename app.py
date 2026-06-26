#escape sirve para evitar inyecciones de código malicioso en los campos de texto, convirtiendo caracteres especiales en entidades HTML seguras.
from html import escape
#urlib.parse se utiliza para parsear los datos del formulario enviados en el cuerpo de la solicitud POST, y para codificar las cadenas al generar las imágenes SVG.
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

# Importamos el modelo de datos y las funciones auxiliares desde main.py para mantener el código organizado.
from main import (
    MediaItem,
    app as api_app,
    read_json,
    validate_unique_title_year,
    write_json,
)


app = FastAPI(title="Gestor de Películas y Series", version="1.0")

# Montamos la API dentro de la aplicación principal para tener la documentación de ambos en la misma interfaz.
def h(value) -> str:
    return escape("" if value is None else str(value), quote=True)

# Función auxiliar para marcar la opción seleccionada en los filtros.
def selected(value, current) -> str:
    return " selected" if value == current else ""

# Función auxiliar para marcar el checkbox como checked si el valor es verdadero.
def checked(value) -> str:
    return " checked" if value else ""

# Diccionario con las rutas de la API para mostrar en la documentación.
def poster_color(title: str) -> tuple[str, str, str]:
    colors = [
        ("#285e61", "#d8efe8", "#f8fbf8"),
        ("#4f5d75", "#dfe7f2", "#fbfcff"),
        ("#6f5e53", "#efe6dc", "#fffaf5"),
        ("#386641", "#e3f1dd", "#fbfef8"),
        ("#6b4f7a", "#eadff0", "#fefbff"),
    ]
    index = abs(sum(ord(char) for char in title)) % len(colors)
    return colors[index]

# Genera una imagen SVG en base al título y año del elemento, o devuelve la imagen personalizada si existe.
def poster_src(item: dict) -> str:
    if item.get("imagen"):
        return item["imagen"]

    dark, soft, paper = poster_color(item["titulo"])
    title = h(item["titulo"])[:34]
    year = h(item["anio"])
    kind = h(item["categoria"]).upper()
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 92 138">'
        f'<rect width="92" height="138" fill="{paper}"/>'
        f'<rect x="0" y="0" width="92" height="42" fill="{soft}"/>'
        f'<rect x="8" y="10" width="76" height="118" rx="6" fill="none" stroke="{dark}" stroke-opacity="0.34"/>'
        f'<text x="46" y="54" text-anchor="middle" font-family="Arial, sans-serif" font-size="8" fill="{dark}" font-weight="700">{kind}</text>'
        f'<text x="46" y="74" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="{dark}" font-weight="700">{title}</text>'
        f'<line x1="24" y1="92" x2="68" y2="92" stroke="{dark}" stroke-opacity="0.28"/>'
        f'<text x="46" y="111" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="{dark}" font-weight="700">{year}</text>'
        f'</svg>'
    )
    return f"data:image/svg+xml;charset=UTF-8,{quote(svg)}"

# Función auxiliar para asignar una clase CSS según el estado del elemento, usada para colorear la etiqueta de estado.
def status_class(status: str) -> str:
    return f"estado-{status.lower()}"

# Función auxiliar para comprobar si un elemento coincide con los filtros de búsqueda, categoría, estado y favorito.
def matches_filters(item: dict, search: str, categoria: str, estado: str, favorito: str) -> bool:
    text = f"{item['titulo']} {item['director']} {item['plataforma']}".lower()
    if search and search.lower() not in text:
        return False
    if categoria and item["categoria"] != categoria:
        return False
    if estado and item["estado"] != estado:
        return False
    if favorito and str(item["favorito"]).lower() != favorito:
        return False
    return True

# Función auxiliar para leer la base de datos desde el archivo JSON.
def format_error(error) -> str:
    if isinstance(error, HTTPException):
        return str(error.detail)
    if isinstance(error, ValidationError):
        return " · ".join(str(item["msg"]) for item in error.errors())
    return str(error)



# Valida que no exista otro elemento con el mismo título y año, excepto el que se está editando (si aplica).
async def get_form_data(request: Request) -> dict:
    body = await request.body()
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items()}

# Convierte los datos del formulario en un objeto MediaItem, manejando los tipos y valores por defecto.
def parse_form_item(form, item_id=None) -> MediaItem:
    puntuacion = form.get("puntuacion", "").strip()
    imagen = form.get("imagen", "").strip()
    return MediaItem(
        id=item_id,
        titulo=form.get("titulo", ""),
        anio=int(form.get("anio", 0)),
        categoria=form.get("categoria", ""),
        estado=form.get("estado", ""),
        puntuacion=int(puntuacion) if puntuacion else None,
        director=form.get("director", ""),
        plataforma=form.get("plataforma", ""),
        duracion=int(form.get("duracion", 0)),
        imagen=imagen or None,
        favorito=form.get("favorito") == "true",
    )

# Función auxiliar para generar un diccionario con valores vacíos, usado para limpiar el formulario.
def empty_form() -> dict:
    return {
        "id": "",
        "titulo": "",
        "anio": "",
        "categoria": "Película",
        "estado": "Pendiente",
        "puntuacion": "",
        "director": "",
        "plataforma": "",
        "duracion": "",
        "imagen": "",
        "favorito": False,
    }

# Función auxiliar para normalizar los datos leídos del JSON, asegurando que tengan todas las claves necesarias y valores por defecto.
def item_to_form(item: dict) -> dict:
    return {
        "id": item.get("id", ""),
        "titulo": item.get("titulo", ""),
        "anio": item.get("anio", ""),
        "categoria": item.get("categoria", "Película"),
        "estado": item.get("estado", "Pendiente"),
        "puntuacion": item.get("puntuacion") or "",
        "director": item.get("director", ""),
        "plataforma": item.get("plataforma", ""),
        "duracion": item.get("duracion", ""),
        "imagen": item.get("imagen") or "",
        "favorito": item.get("favorito", False),
    }

# Función auxiliar para leer el JSON y devolver una lista de diccionarios normalizados.
def render_rows(items: list[dict]) -> str:
    if not items:
        return '<tr><td class="empty" colspan="6">No hay resultados</td></tr>'

    rows = []
    for item in items:
        score = item["puntuacion"] if item["puntuacion"] is not None else "Sin valorar"
        favorite = "Sí" if item["favorito"] else "No"
        rows.append(
            f"""
            <tr>
              <td>
                <div class="media-summary">
                  <div class="poster-thumb"><img src="{h(poster_src(item))}" alt="Portada de {h(item['titulo'])}"></div>
                  <div>
                    <div class="title-cell">{h(item['titulo'])}</div>
                    <div class="media-meta">
                      <span>{h(item['anio'])}</span>
                      <span>{h(item['director'])}</span>
                      <span>{h(item['plataforma'])}</span>
                    </div>
                  </div>
                </div>
              </td>
              <td><span class="badge">{h(item['categoria'])}</span></td>
              <td><span class="badge {status_class(item['estado'])}">{h(item['estado'])}</span></td>
              <td>{h(score)}</td>
              <td>{favorite}</td>
              <td>
                <div class="actions">
                  <a class="btn-secondary" href="/?edit_id={item['id']}">Editar</a>
                  <form method="post" action="/items/{item['id']}/delete"><button class="btn-danger" type="submit">Eliminar</button></form>
                </div>
              </td>
            </tr>
            """
        )
    return "".join(rows)

# Función principal para renderizar la página HTML, aplicando los filtros, mostrando mensajes de éxito o error, y manejando el estado de edición.
def render_page(
    *,
    search: str = "",
    categoria: str = "",
    estado: str = "",
    favorito: str = "",
    edit_id: int | None = None,
    message: str = "",
    error: str = "",
    form_values: dict | None = None,
) -> str:
    db = read_json()
    visible = [item for item in db if matches_filters(item, search, categoria, estado, favorito)]

    editing_item = None
    if edit_id is not None:
        editing_item = next((item for item in db if item["id"] == edit_id), None)

    if form_values is not None:
        values = empty_form()
        values.update(form_values)
        values["favorito"] = form_values.get("favorito") == "true"
    elif editing_item:
        values = item_to_form(editing_item)
    else: 
        values = empty_form()

    form_action = f"/items/{edit_id}" if editing_item else "/items"
    form_title = f"Editar #{edit_id}" if editing_item else "Nuevo elemento"
    submit_text = "Actualizar" if editing_item else "Guardar"
    second_action = '<a class="btn-secondary" href="/">Cancelar</a>' if editing_item else '<a class="btn-secondary" href="/">Limpiar</a>'

    alert_html = ""
    if message:
        alert_html = f'<div class="alert success">{h(message)}</div>'
    if error:
        alert_html = f'<div class="alert error">{h(error)}</div>'

    return f"""
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>🎬Gestor de Películas y Series🎬</title>
  <style>
    :root {{ color-scheme: light; --bg: #f6f7f4; --panel: #ffffff; --text: #1c2522; --muted: #68736f; --line: #dfe4df; --accent: #167c80; --accent-dark: #0f5f63; --danger: #b42318; --warning: #b7791f; --ok: #2f7d4f; --shadow: 0 12px 30px rgba(28, 37, 34, 0.08); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--text); }}
    button, input, select {{ font: inherit; }}
    button, .btn-secondary {{ border: 0; border-radius: 6px; cursor: pointer; min-height: 38px; padding: 0 14px; font-weight: 700; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; }}
    .page {{ min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }}
    .topbar {{ background: #ffffff; border-bottom: 1px solid var(--line); }}
    .topbar-inner {{ width: min(1480px, calc(100% - 32px)); margin: 0 auto; min-height: 74px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }}
    h1 {{ margin: 0; font-size: 1.45rem; line-height: 1.1; }}
    .meta {{ color: var(--muted); font-size: 0.92rem; margin-top: 5px; }}
    .doc-link {{ min-height: 40px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; border: 1px solid rgba(22, 124, 128, 0.28); border-radius: 6px; background: #eaf5f4; color: var(--accent-dark); padding: 0 14px; text-decoration: none; font-size: 0.92rem; font-weight: 850; white-space: nowrap; box-shadow: 0 6px 16px rgba(22, 124, 128, 0.12); }}
    .doc-link::before {{ content: "↗"; font-size: 0.95rem; line-height: 1; }}
    .doc-link:hover {{ border-color: rgba(22, 124, 128, 0.42); background: #d9eeee; }}
    .main {{ width: min(1480px, calc(100% - 32px)); margin: 24px auto; display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; }}
    .toolbar, .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); }}
    .toolbar {{ padding: 14px; display: grid; grid-template-columns: 1.2fr repeat(3, minmax(130px, 0.65fr)) auto; gap: 10px; margin-bottom: 14px; align-items: end; }}
    .field {{ display: grid; gap: 6px; }}
    label {{ color: var(--muted); font-size: 0.78rem; font-weight: 800; text-transform: uppercase; }}
    input, select {{ width: 100%; min-height: 38px; border: 1px solid var(--line); border-radius: 6px; background: #fff; color: var(--text); padding: 8px 10px; outline: none; }}
    input:focus, select:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px rgba(22, 124, 128, 0.14); }}
    .panel-head {{ min-height: 58px; padding: 14px 16px; border-bottom: 1px solid var(--line); display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
    .panel-title {{ font-size: 1rem; font-weight: 900; }}
    .count {{ color: var(--muted); font-size: 0.9rem; font-weight: 700; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; min-width: 1080px; table-layout: fixed; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 14px 14px; text-align: left; vertical-align: middle; font-size: 0.94rem; }}
    th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; background: #fbfcfa; }}
    .title-col {{ width: 42%; }}
    th:nth-child(2), td:nth-child(2) {{ width: 12%; }}
    th:nth-child(3), td:nth-child(3) {{ width: 15%; }}
    th:nth-child(4), td:nth-child(4) {{ width: 13%; padding-left: 22px; }}
    th:nth-child(5), td:nth-child(5) {{ width: 9%; }}
    th:nth-child(6), td:nth-child(6) {{ width: 21%; }}
    .media-summary {{ display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 14px; align-items: center; min-width: 0; }}
    .poster-thumb {{ width: 64px; aspect-ratio: 2 / 3; border-radius: 5px; overflow: hidden; background: #eef3f1; border: 1px solid rgba(28, 37, 34, 0.12); box-shadow: 0 5px 12px rgba(28, 37, 34, 0.12); }}
    .poster-thumb img {{ width: 100%; height: 100%; display: block; object-fit: cover; }}
    .title-cell {{ font-weight: 900; line-height: 1.25; overflow-wrap: break-word; }}
    .media-meta {{ display: grid; gap: 2px; margin-top: 6px; color: var(--muted); font-size: 0.84rem; line-height: 1.3; }}
    .media-meta span {{ display: block; overflow-wrap: break-word; }}
    .media-meta span:first-child {{ color: var(--text); font-weight: 750; }}
    .badge {{ display: inline-flex; align-items: center; min-height: 24px; border-radius: 999px; padding: 0 9px; font-size: 0.78rem; font-weight: 850; background: #edf2f2; color: #285e61; white-space: nowrap; }}
    .badge.estado-completado {{ background: #e8f4ed; color: var(--ok); }}
    .badge.estado-viendo {{ background: #fff4df; color: var(--warning); }}
    .badge.estado-pendiente {{ background: #edf2f7; color: #4a5568; }}
    .actions {{ display: flex; gap: 10px; justify-content: flex-end; }}
    .actions form {{ margin: 0; }}
    .btn-primary {{ background: var(--accent); color: white; }}
    .btn-primary:hover {{ background: var(--accent-dark); }}
    .btn-secondary {{ background: #e8ece9; color: var(--text); }}
    .btn-secondary:hover {{ background: #dbe2dd; }}
    .btn-danger {{ background: #fee4e2; color: var(--danger); }}
    .btn-danger:hover {{ background: #fecdca; }}
    .form-panel {{ position: sticky; top: 18px; padding: 16px; }}
    .form-grid {{ display: grid; gap: 12px; margin-top: 14px; }}
    .row-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .check-row {{ display: flex; align-items: center; gap: 10px; min-height: 38px; color: var(--text); font-size: 0.95rem; text-transform: none; }}
    .check-row input {{ width: 18px; min-height: 18px; }}
    .form-actions {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 4px; }}
    .alert {{ margin-bottom: 14px; padding: 10px 12px; border-radius: 6px; font-weight: 750; }}
    .alert.success {{ background: #e8f4ed; color: var(--ok); }}
    .alert.error {{ background: #fee4e2; color: var(--danger); }}
    .empty {{ padding: 28px 16px; color: var(--muted); text-align: center; font-weight: 700; }}
    @media (max-width: 1180px) {{ .main {{ grid-template-columns: 1fr; }} .form-panel {{ position: static; }} .toolbar {{ grid-template-columns: 1fr 1fr; }} }}
    @media (max-width: 620px) {{ .topbar-inner {{ align-items: flex-start; flex-direction: column; padding: 16px 0; }} .main {{ width: min(100% - 20px, 1180px); margin-top: 14px; }} .toolbar, .row-2, .form-actions {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="page">
    <header class="topbar"><div class="topbar-inner"><div><h1>Gestor de Películas y Series🎬</h1><div class="meta">Películas y series guardadas</div></div><a class="doc-link" href="/api/docs">API docs</a></div></header>
    <main class="main">
      <section>
        {alert_html}
        <form class="toolbar" method="get" action="/">
          <div class="field"><label for="search">Buscar</label><input id="search" name="search" type="search" value="{h(search)}" placeholder="Título, director o plataforma"></div>
          <div class="field"><label for="categoria">Categoría</label><select id="categoria" name="categoria"><option value="">Todas</option><option value="Película"{selected('Película', categoria)}>Película</option><option value="Serie"{selected('Serie', categoria)}>Serie</option></select></div>
          <div class="field"><label for="estado">Estado</label><select id="estado" name="estado"><option value="">Todos</option><option value="Pendiente"{selected('Pendiente', estado)}>Pendiente</option><option value="Viendo"{selected('Viendo', estado)}>Viendo</option><option value="Completado"{selected('Completado', estado)}>Completado</option></select></div>
          <div class="field"><label for="favorito">Favorito</label><select id="favorito" name="favorito"><option value="">Todos</option><option value="true"{selected('true', favorito)}>Sí</option><option value="false"{selected('false', favorito)}>No</option></select></div>
          <button class="btn-primary" type="submit">Filtrar</button>
        </form>
        <div class="panel list-panel"><div class="panel-head"><div class="panel-title">Colección</div><div class="count">{len(visible)} elemento{'s' if len(visible) != 1 else ''}</div></div><div class="table-wrap"><table><thead><tr><th class="title-col">Título</th><th>Categoría</th><th>Estado</th><th>Puntuación</th><th>Favorito</th><th></th></tr></thead><tbody>{render_rows(visible)}</tbody></table></div></div>
      </section>
      <aside class="panel form-panel">
        <div class="panel-title">{h(form_title)}</div>
        <form class="form-grid" method="post" action="{form_action}">
          <div class="field"><label for="titulo-form">Título</label><input id="titulo-form" name="titulo" value="{h(values['titulo'])}" required></div>
          <div class="row-2"><div class="field"><label for="anio-form">Año</label><input id="anio-form" name="anio" type="number" min="1900" value="{h(values['anio'])}" required></div><div class="field"><label for="duracion-form">Duración</label><input id="duracion-form" name="duracion" type="number" min="1" value="{h(values['duracion'])}" required></div></div>
          <div class="row-2"><div class="field"><label for="categoria-form">Categoría</label><select id="categoria-form" name="categoria" required><option value="Película"{selected('Película', values['categoria'])}>Película</option><option value="Serie"{selected('Serie', values['categoria'])}>Serie</option></select></div><div class="field"><label for="estado-form">Estado</label><select id="estado-form" name="estado" required><option value="Pendiente"{selected('Pendiente', values['estado'])}>Pendiente</option><option value="Viendo"{selected('Viendo', values['estado'])}>Viendo</option><option value="Completado"{selected('Completado', values['estado'])}>Completado</option></select></div></div>
          <div class="field"><label for="puntuacion-form">Puntuación</label><input id="puntuacion-form" name="puntuacion" type="number" min="1" max="10" value="{h(values['puntuacion'])}" placeholder="Vacía si está pendiente"></div>
          <div class="field"><label for="director-form">Director</label><input id="director-form" name="director" value="{h(values['director'])}" required></div>
          <div class="field"><label for="plataforma-form">Plataforma</label><input id="plataforma-form" name="plataforma" value="{h(values['plataforma'])}" required></div>
          <div class="field"><label for="imagen-form">Imagen URL</label><input id="imagen-form" name="imagen" value="{h(values['imagen'])}" placeholder="Opcional"></div>
          <label class="check-row"><input name="favorito" type="checkbox" value="true"{checked(values['favorito'])}> Favorito</label>
          <div class="form-actions"><button class="btn-primary" type="submit">{submit_text}</button>{second_action}</div>
        </form>
      </aside>
    </main>
  </div>
</body>
</html>
    """

# Endpoint principal que muestra la interfaz, aplicando los filtros y manejando el estado de edición.
@app.get("/", response_class=HTMLResponse, tags=["Interfaz"])
def interfaz(search: str = "", categoria: str = "", estado: str = "", favorito: str = "", edit_id: int | None = None, mensaje: str = ""):
    return render_page(search=search, categoria=categoria, estado=estado, favorito=favorito, edit_id=edit_id, message=mensaje)

# Endpoint para crear un nuevo elemento, validando los datos y asegurando que no haya duplicados por título y año.
@app.post("/items", response_class=HTMLResponse, tags=["Interfaz"])
async def crear_item(request: Request):
    form = await get_form_data(request)
    try:
        item = parse_form_item(form)
        db = read_json()
        validate_unique_title_year(db, item.titulo, item.anio)
        item.id = max([element["id"] for element in db], default=0) + 1
        db.append(item.model_dump())
        write_json(db)
    except (HTTPException, ValidationError, ValueError) as error:
        return render_page(error=format_error(error), form_values=dict(form))
    return RedirectResponse("/?mensaje=Elemento guardado correctamente", status_code=303)

# Endpoint para editar un elemento existente, validando los datos y asegurando que no haya duplicados por título y año (excepto el mismo elemento).
@app.post("/items/{item_id}", response_class=HTMLResponse, tags=["Interfaz"])
async def editar_item(item_id: int, request: Request):
    form = await get_form_data(request)
    try:
        updated_item = parse_form_item(form, item_id)
        db = read_json()
        validate_unique_title_year(db, updated_item.titulo, updated_item.anio, item_id)
        for index, item in enumerate(db):
            if item["id"] == item_id:
                db[index] = updated_item.model_dump()
                write_json(db)
                break
        else:
            raise HTTPException(status_code=404, detail="Elemento no encontrado")
    except (HTTPException, ValidationError, ValueError) as error:
        values = dict(form)
        values["id"] = item_id
        return render_page(error=format_error(error), edit_id=item_id, form_values=values)
    return RedirectResponse("/?mensaje=Cambios guardados correctamente", status_code=303)

# Endpoint para eliminar un elemento, redirigiendo a la página principal con un mensaje de éxito o error.
@app.post("/items/{item_id}/delete", tags=["Interfaz"])
def eliminar_item(item_id: int):
    db = read_json()
    item = next((element for element in db if element["id"] == item_id), None)
    if item is None:
        return RedirectResponse("/?mensaje=Elemento no encontrado", status_code=303)
    db.remove(item)
    write_json(db)
    return RedirectResponse("/?mensaje=Elemento eliminado correctamente", status_code=303)


# Montamos la API original dentro de /api.
# La interfaz queda en / y los endpoints de la API quedan en /api/items, /api/docs, etc.
app.mount("/api", api_app)
