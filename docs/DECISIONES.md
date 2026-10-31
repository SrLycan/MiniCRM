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
| 12 | Commits en inglés; interfaz y documentación en español | Sigue los ejemplos del enunciado y al público del producto |
| 13 | Docs de trabajo en `docs/` | Muestran el proceso: primero el spec, luego el plan y al final el código |
| 14 | Plantillas y estáticos a nivel de proyecto | Los comparten `accounts` y `clients` |
| 15 | Bloqueo de login con la caché de Django y un solo proceso de Gunicorn | Sin dependencias extra; un proceso con hilos basta para SQLite y comparte la caché |
| 16 | Token CSRF en una etiqueta meta y cookie `HttpOnly` | JavaScript no necesita leer la cookie |
