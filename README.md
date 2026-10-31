# Órbita CRM

Mini CRM de clientes hecho con Django y JavaScript Vanilla, como desafío técnico para la
vacante de Desarrollador/a de Software Junior en CEO Marketing.

[![CI](https://github.com/SrLycan/MiniCRM/actions/workflows/ci.yml/badge.svg)](https://github.com/SrLycan/MiniCRM/actions/workflows/ci.yml)

![Panel de Órbita CRM](docs/screenshots/panel-oscuro.png)

## Funciones

- Login con sesiones de Django y bloqueo temporal tras 5 intentos fallidos.
- Panel con métricas, distribución por estado y altas por semana, en SVG sin librerías.
- Crear, editar y eliminar clientes en modales, sin recargar la página.
- Búsqueda dinámica por nombre o empresa, sin distinguir mayúsculas ni acentos.
- Filtro por estado, orden por columnas y paginación, conservados en la URL.
- Tablero Kanban en su propio apartado: arrastrar con ratón, o selector con teclado y en móvil.
- Eliminar con confirmación y opción de deshacer durante 6 segundos.
- Chat de WhatsApp simulado: conversaciones por cliente, respuestas y webhook firmado.
- Validación inmediata en el navegador y validación definitiva en el backend.
- Mensajes toast, esqueletos de carga y estados vacío y de error con reintento.
- Modo claro por defecto y modo oscuro opcional, diseño responsive de 360 a 1920 px.
- Administración de clientes desde Django Admin.

## Requisitos

- **Con Docker (recomendado):** Docker con Docker Compose.
- **Sin Docker:** Python 3.13.

## Ejecutar con Docker

```bash
git clone https://github.com/SrLycan/MiniCRM.git
cd MiniCRM
cp .env.example .env
docker compose up --build
```

Abre <http://localhost:8000> e inicia sesión. Las migraciones y los datos demo se aplican
solos, y la base de datos se conserva en un volumen de Docker.

| Usuario | Contraseña |
|---|---|
| `demo` | `Orbita-Demo-2026` |

La misma cuenta entra a Django Admin en <http://localhost:8000/admin/>.

Para detener la aplicación usa `docker compose down`. Agrega `-v` si además quieres borrar
los datos.

## Ejecutar sin Docker

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Abre <http://127.0.0.1:8000> y usa las mismas credenciales.

## Pruebas

```bash
python manage.py check
python manage.py test     # backend
npm test                  # funciones de JavaScript; requiere Node.js 22 o superior
```

Cada push a `main` o `develop`, y cada pull request, ejecuta en GitHub Actions el `check`,
la revisión de migraciones, ambas pruebas y la construcción de la imagen Docker.

## Estructura

```
config/       Configuración de Django
accounts/     Login y bloqueo por intentos
clients/      Modelo, formulario, vistas, URLs, admin, datos demo y pruebas
templates/    Plantillas compartidas
static/css/   Tokens, fondo, estructura, componentes y páginas
static/js/    core (API y utilidades), ui, features y pages
tests/js/     Pruebas de JavaScript
docker/       Script de arranque del contenedor
docs/         Spec, plan, decisiones y capturas
```

## API

Todas las rutas exigen sesión y responden 401 sin ella, salvo el webhook.

| Método y ruta | Uso |
|---|---|
| `GET /api/clients/?q=&status=&sort=&page=&page_size=` | Listar, buscar, filtrar, ordenar y paginar |
| `POST /api/clients/` | Crear |
| `GET /api/clients/<id>/` | Consultar |
| `PUT /api/clients/<id>/` | Actualizar |
| `PATCH /api/clients/<id>/` | Cambiar solo el estado |
| `DELETE /api/clients/<id>/` | Eliminar |
| `GET /api/clients/stats/` | Métricas del panel |
| `POST /api/clients/simulate-whatsapp/` | Simular un cliente nuevo |
| `GET /api/conversations/` | Listar conversaciones |
| `GET /api/conversations/<id>/` | Consultar un chat |
| `POST /api/conversations/<id>/messages/` | Responder en el chat |
| `POST /api/conversations/<id>/simulate-reply/` | Simular una respuesta del cliente |
| `POST /api/webhooks/whatsapp/` | Recibir mensajes firmados con `X-Hub-Signature-256` |

## WhatsApp simulado

El apartado **WhatsApp** del menú muestra las conversaciones y permite responder. Como no hay
conexión con Meta, los mensajes se guardan en el CRM pero no llegan a un teléfono real, y la
pantalla lo avisa. Para probarlo:

1. **Simular cliente nuevo** crea un prospecto con su primer mensaje y abre su chat.
2. Escribe una respuesta y envíala.
3. **Simular respuesta del cliente** hace que te conteste.

También puedes abrir el chat de cualquier cliente con teléfono desde Clientes o Tablero.

Cada mensaje simulado se firma con `WHATSAPP_APP_SECRET` y entra por el mismo código del
webhook. Si el número ya pertenece a un cliente, el mensaje se le asocia y conserva sus
datos, aunque el teléfono esté escrito en otro formato. Si es nuevo, WhatsApp no entrega
correo ni empresa, así que aparecen vacíos hasta que alguien los complete.

Para probar el webhook directamente, con la aplicación corriendo y el secreto de
`.env.example`:

```bash
BODY='{"entry":[{"changes":[{"value":{"contacts":[{"profile":{"name":"Ana Ruiz"},"wa_id":"593991234567"}],"messages":[{"from":"593991234567"}]}}]}]}'
SECRET=solo-para-demo-local-reemplazar-en-cualquier-otro-entorno
SIGNATURE=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -r | cut -d' ' -f1)
curl -i http://localhost:8000/api/webhooks/whatsapp/ \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -d "$BODY"
```

## Decisiones técnicas

- **Sin frameworks de frontend ni DRF.** Módulos ES nativos y vistas de Django bastan para
  este alcance, y no hay paso de compilación.
- **El cristal enmarca, lo sólido se lee.** El glassmorphism va en navegación y métricas;
  la tabla, los formularios y los modales usan superficies sólidas con contraste AA.
- **Reglas críticas en la base de datos.** El correo único y los estados válidos también
  son restricciones de SQLite, y `ClientForm` traduce los errores a mensajes claros.
- **Seguridad.** CSRF en toda escritura, secretos por variables de entorno, datos pintados
  con `textContent` para evitar XSS, política CSP sin scripts en línea, límites de longitud
  y de tamaño, bloqueo del login por usuario e IP, también en Admin, y contenedor sin root.
  Para publicar la app, cambia todos los valores de `.env.example` y activa `DJANGO_HTTPS`.

El detalle está en [docs/SPEC.md](docs/SPEC.md), [docs/PLAN.md](docs/PLAN.md),
[docs/SPEC-MEJORAS.md](docs/SPEC-MEJORAS.md), [docs/PLAN-MEJORAS.md](docs/PLAN-MEJORAS.md) y
[docs/DECISIONES.md](docs/DECISIONES.md).

## Limitaciones conocidas

- Las credenciales de `.env.example` son solo para esta demo. Fuera de ella, cambia la
  clave secreta y la contraseña, y pon `DEMO_LOGIN_HINT=false`.
- El chat se actualiza con cada acción: un mensaje que entra por el webhook desde fuera se
  ve al recargar la página.
- En el tablero, arrastrar funciona con ratón; en pantallas táctiles se usa el selector.
- Las fuentes Sora y Outfit se cargan desde Google Fonts; sin internet se usa una fuente
  del sistema.

## Capturas

| Clientes | Modo claro | Móvil |
|---|---|---|
| ![Listado de clientes](docs/screenshots/clientes-oscuro.png) | ![Panel en modo claro](docs/screenshots/panel-claro.png) | ![Vista móvil](docs/screenshots/clientes-movil.png) |

## Uso de IA

Desarrollado con apoyo de Claude Code, por eso algunos commits lo incluyen como coautor.
El diseño de la solución se definió primero en un spec y un plan revisados por el autor.
