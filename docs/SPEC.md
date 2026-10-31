# Spec: Mini CRM de Clientes

Desafío técnico para la vacante de Desarrollador/a de Software Junior en CEO Marketing.
Fecha límite de trabajo: sábado 31 de octubre de 2026, 23:59.

## Objetivo

Una aplicación pequeña, entendible y bien terminada para gestionar clientes. La nota
prioriza el frontend (55 %), así que el esfuerzo se concentra en diseño, responsive y
JavaScript Vanilla, sobre un backend Django simple y correcto.

**Fuera de alcance:** roles y permisos por usuario, registro público, multiempresa,
despliegue a producción, importación o exportación de datos, y cualquier librería de
frontend.

## Arquitectura

```
Navegador                         Django
templates + CSS + JS Vanilla  ──► clients/views.py (páginas y API JSON)
         ▲                                │  valida con ClientForm
         └──── fetch + JSON ◄─────────────┤
                                     models.py ──► SQLite
                                     admin.py
```

- **Django 5.2 LTS, Python 3.13, SQLite.** Sin DRF: cinco endpoints no lo justifican.
- **Páginas servidas por Django y datos por `fetch`:** cumple la separación de models,
  views, urls, templates y static, y permite interacciones sin recargar.
- **`ClientForm` es la única fuente de validación** para la API, y `ClientAdmin` aplica
  las mismas reglas del modelo.
- **JavaScript con módulos ES nativos**, sin paso de compilación.
- **Login con sesiones de Django:** todas las páginas y la API exigen sesión, validada
  siempre en el backend. Una página sin sesión redirige al login y la API responde 401.

### Estructura

```
config/                      settings, urls, wsgi
docker/                      script de arranque del contenedor
accounts/                    login con bloqueo por intentos fallidos
clients/
  models.py  forms.py  views.py  urls.py  admin.py  serializers.py
  management/commands/seed_demo.py
  tests/
templates/                   base, app, parciales, login, panel y clientes
static/css/                  tokens, ambiente, componentes y páginas
static/js/                   core, ui, features y pages
tests/js/                    pruebas de funciones puras con node:test
docs/                        SPEC, PLAN, DECISIONES, capturas
.github/workflows/ci.yml
Dockerfile  docker-compose.yml  .env.example  requirements.txt  README.md
```

## Modelo `Client`

| Campo | Tipo | Reglas |
|---|---|---|
| `name` | CharField(120) | Obligatorio, sin espacios sobrantes, al menos 2 caracteres |
| `company` | CharField(120) | Opcional |
| `email` | EmailField | Obligatorio, en minúsculas, único sin distinguir mayúsculas |
| `phone` | CharField(20) | Opcional; dígitos con `+`, espacios o guiones; de 7 a 15 dígitos |
| `status` | TextChoices | `prospect`, `client`, `inactive`; por defecto `prospect` |
| `created_at` / `updated_at` | DateTimeField | Automáticos |

Las reglas críticas también viven en la base de datos: `UniqueConstraint(Lower("email"))`
y `CheckConstraint` sobre `status`. Hay índices en `status` y `created_at`.

## API JSON

| Método y ruta | Uso | Respuestas |
|---|---|---|
| `GET /api/clients/?q=&status=&sort=&page=` | Listar, buscar, filtrar, ordenar, paginar | 200 |
| `POST /api/clients/` | Crear | 201, 400 |
| `GET /api/clients/<id>/` | Consultar uno | 200, 404 |
| `PUT /api/clients/<id>/` | Actualizar | 200, 400, 404 |
| `DELETE /api/clients/<id>/` | Eliminar | 204, 404 |
| `GET /api/clients/stats/` | Totales por estado, altas de 6 semanas y últimos clientes | 200 |

Todas las rutas responden 401 sin sesión.

Los errores tienen siempre esta forma, con un código estable:

```json
{ "code": "VALIDATION_ERROR", "message": "Revisa los campos marcados.", "errors": { "email": ["..."] } }
```

La API usa CSRF de Django con la cabecera `X-CSRFToken`. `q` busca por nombre o empresa
sin distinguir mayúsculas ni acentos. `sort` acepta una lista cerrada de columnas. La paginación es
de 10 clientes por página.

## Autenticación

- Formulario propio sobre `LoginView` de Django, con contraseñas hasheadas por Django.
- Cierre de sesión por POST, protegido con CSRF.
- Tras 5 intentos fallidos por usuario e IP, el login se bloquea 5 minutos y responde 429.
- `seed_demo` crea el usuario demo con credenciales leídas del entorno, nunca del código.
- El login muestra esas credenciales solo si `DEMO_LOGIN_HINT=true`.

## Interfaz

**Dirección visual: cristal por capas.** Parte del sistema de SS SWAP (fondo vivo animado,
luces, partículas, acento celeste, Sora y Outfit) y lo combina con superficies sólidas
donde se leen datos. La regla es simple: el cristal enmarca y el sólido se lee.

- Cristal: barra lateral, KPIs, tarjetas del panel y login.
- Superficie sólida: tabla, formularios y modales. Todo texto cumple contraste WCAG AA.
- En móvil, o sin `backdrop-filter`, el cristal pasa a un fondo casi opaco, sin destellos.
- Con `prefers-reduced-motion` se detienen las animaciones.
- El modo claro usa paneles blancos translúcidos sobre un fondo vivo claro.
- La identidad es propia: "Órbita CRM", con su logo en SVG. Los clientes son puntos en
  órbita, idea que se repite en el logo y en el gráfico por estado.

**Vistas**

- **Panel:** saludo, cuatro KPIs animados (total y cada estado), anillo SVG de distribución
  por estado, barras de altas por semana y últimos clientes.
- **Clientes:** buscador, filtro por estado en chips, tabla ordenable, paginación y botón
  de nuevo cliente.
- **Modal de crear o editar** y **diálogo de eliminación** con `<dialog>` nativo.
- **Navegación:** barra lateral en desktop, compacta en tablet e inferior en móvil.

**Responsive:** barra lateral desde 1024 px, riel de iconos de 640 a 1023 px y navegación
inferior por debajo de 640 px, probado hasta 360 px. Por debajo de 900 px cada fila de la
tabla se muestra como tarjeta, con todos sus datos y un selector de orden.

**Estados de interfaz:** carga con esqueletos, lista vacía, búsqueda sin resultados, error
de red con reintento, envío con botón bloqueado y foco visible.

**Accesibilidad y seguridad:** HTML semántico, teclado completo, foco atrapado en los
modales y devuelto al cerrar, toasts con `aria-live`. Los datos se pintan con
`textContent`, nunca con `innerHTML`, para evitar XSS.

## Criterios de aceptación

### Funcionales

- [ ] RF1 a RF4: crear, listar, editar y eliminar con confirmación, sin recargar.
- [ ] RF5: la búsqueda filtra por nombre o empresa mientras se escribe, con debounce, y
      una respuesta antigua nunca pisa a una nueva.
- [ ] RF6 y RF7: el filtro por los tres estados se combina con la búsqueda y el orden.
- [ ] RF8: los datos persisten al reiniciar, también en Docker.
- [ ] RF9: toda acción muestra un toast de éxito o error, y cada campo inválido muestra su
      mensaje, incluidos los que devuelve el backend, como correo duplicado.
- [ ] RF10: Django Admin permite listar, buscar, filtrar y editar clientes.
- [ ] Sin sesión no se ve ninguna página ni dato; la API responde 401.
- [ ] Credenciales incorrectas muestran un error claro y el sexto intento queda bloqueado.
- [ ] Búsqueda, filtro, orden y página se conservan en la URL.

### Calidad

- [ ] Sin desbordamiento horizontal de 360 a 1920 px.
- [ ] Sin errores en la consola del navegador.
- [ ] Texto con contraste AA en ambos temas.
- [ ] `python manage.py check`, `makemigrations --check` y las pruebas pasan.
- [ ] `docker compose up --build` deja la app funcional con datos demo.
- [ ] El CI pasa en GitHub: `check`, pruebas y construcción de la imagen.
- [ ] Ningún secreto en el repositorio; `.env` está ignorado.
- [ ] Se puede instalar y ejecutar siguiendo únicamente el README.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| El cristal resta legibilidad en la tabla | Superficie más densa y contraste verificado |
| `backdrop-filter` y animaciones pesan en móvil | Respaldo opaco y animación reducida |
| Fuerza bruta contra el login | Bloqueo temporal por usuario e IP |
| Python local distinto al de la imagen | Docker como vía principal y Python 3.13 fijado en CI |
| Plazo de un día | Plan por fases, con el flujo central terminado primero |
