# Registro de decisiones

Cada decisión lleva su motivo, para no rediscutirla y para poder explicarla en la revisión.

| # | Decisión | Motivo |
|---|---|---|
| 1 | Django con templates y API JSON propia, sin DRF | Son cinco endpoints; DRF añadiría más de lo que aporta (requisito 20) |
| 2 | JavaScript con módulos ES y sin paso de compilación | Se valora el Vanilla y simplifica Docker y CI |
| 3 | Django 5.2 LTS con Python 3.13 | Versión con soporte largo y base estable para revisar |
| 4 | SQLite con volumen de Docker | El enunciado lo acepta y la persistencia queda garantizada |
| 5 | `ClientForm` como única fuente de validación | Evita duplicar reglas entre la API y otros puntos de entrada |
| 6 | Correo único sin distinguir mayúsculas, en la base de datos | Evita clientes duplicados aunque alguien salte la API, por ejemplo vía Admin |
| 7 | Login con sesiones de Django y API con 401 | Demo completa y validación real en el backend, sin tokens que guardar en el navegador |
| 8 | Cristal para enmarcar y superficies sólidas para leer | Conserva la identidad visual sin sacrificar la legibilidad de los datos |
| 9 | `<dialog>` nativo para los modales | Da foco, tecla Esc y capa superior sin código adicional |
| 10 | Datos pintados con `textContent` | Previene XSS con datos escritos por usuarios |
| 11 | Gráficos en SVG hechos a mano | Evita dependencias y demuestra dominio del frontend |
| 12 | Interfaz, documentación y commits en español; identificadores de código en inglés | Coherencia con el idioma del equipo y con los campos del modelo sugerido |
| 13 | Docs de trabajo en `docs/` | Muestran el proceso: primero el spec, luego el plan y al final el código |
| 14 | Plantillas y estáticos a nivel de proyecto | Los comparten `accounts` y `clients` |
| 15 | Bloqueo de login con la caché de Django y un solo proceso de Gunicorn | Sin dependencias extra; un proceso con hilos basta para SQLite y comparte la caché |
| 16 | Token CSRF en una etiqueta meta y cookie `HttpOnly` | JavaScript no necesita leer la cookie |
| 17 | Campo `search_text` normalizado | SQLite no ignora acentos ni mayúsculas fuera de ASCII; sin esto "jose" no encontraría a "José" |
| 18 | Tarjetas por debajo de 900 px en lugar de ocultar columnas | El enunciado exige mostrar los cinco datos y evita el desplazamiento horizontal |
| 19 | WhiteNoise con archivos comprimidos, sin nombres con hash | Los módulos ES usan rutas relativas y no hay un paso de compilación que las reescriba |
| 20 | Kanban sobre los 3 estados existentes, sin etapas nuevas | Da una vista útil sin cambiar el modelo ni complicar el alcance |
| 21 | `PATCH` solo para el estado, con su propio formulario | Mover una tarjeta no debe exigir ni reenviar los demás datos, y un prospecto de WhatsApp aún no tiene correo real |
| 22 | Arrastrar con HTML nativo y selector de estado en cada tarjeta | Arrastrar no funciona con teclado ni con el dedo; el selector cubre ambos casos sin librerías |
| 23 | El tablero pide una consulta por columna, con 50 clientes como máximo | Cada columna conoce su total real y la página no carga toda la cartera |
| 24 | Correo reservado `<número>@whatsapp.invalid` para prospectos de WhatsApp | Volver opcional el correo cambiaría su regla única y el formulario; `.invalid` nunca entrega correo y la API lo devuelve vacío |
| 25 | `whatsapp_id` único en lugar de un campo `source` | Un solo campo identifica al prospecto, evita duplicados por reintentos y también indica el origen |
| 26 | La simulación pasa por el mismo código del webhook | Lo que se muestra es el flujo real, y el secreto se queda en el servidor |
| 27 | El webhook responde 503 si no hay secreto | Sin clave no se puede verificar la firma, así que falla cerrado en vez de aceptar mensajes |
| 28 | El texto de los mensajes no se guarda | No hay bandeja de conversaciones, y así no se almacenan datos personales sin uso |
