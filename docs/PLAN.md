# Plan de implementación

Flujo de Git: `main` estable, `develop` de integración y una rama `feature/*` por fase,
fusionada con `--no-ff`. Commits convencionales en español desde la corrección de las pruebas JS.
Cada fase termina verificada antes de pasar a la siguiente.

## Fase 0: Base del repositorio

- [x] `git init`, `main` y `develop`, `.gitignore`, `.env.example`, `requirements.txt`
- [x] Proyecto Django `config`, app `clients`, configuración por variables de entorno

## Fase 1: Backend (`feature/client-model`, `feature/client-api`)

- [x] Modelo `Client`, restricciones, migración y `ClientAdmin`
- [x] `ClientForm` con normalización y mensajes en español
- [x] API JSON con errores uniformes y estadísticas
- [x] Comando `seed_demo` idempotente
- [x] Pruebas de modelo, validaciones, API, CSRF, búsqueda, filtro, orden y paginación

## Fase 1.5: Autenticación (`feature/auth`)

- [x] App `accounts`, login, logout y bloqueo por intentos
- [x] Protección de páginas y API, usuario demo en `seed_demo`
- [x] Pruebas de sesión, 401, redirección y bloqueo

## Fase 2: Sistema visual (`feature/design-system`)

- [x] Tokens de color, tipografía, espacio y movimiento para ambos temas
- [x] Fondo vivo, cristal en tres niveles, botones, campos, chips e insignias
- [x] Plantilla base con navegación responsive, logo SVG y selector de tema
- [x] Pantalla de login

## Fase 3: Vista de clientes (`feature/clients-ui`)

- [x] Cliente `api.js` con CSRF y errores uniformes
- [x] Tabla y tarjetas móviles, esqueletos y estados vacío y de error
- [x] Búsqueda con debounce y cancelación, filtro, orden, paginación y estado en la URL
- [x] Modal de crear y editar, validación, bloqueo al enviar y errores del backend
- [x] Confirmación al eliminar y toasts

## Fase 4: Panel (`feature/dashboard`)

- [x] KPIs con contador animado
- [x] Anillo de estados y barras de altas en SVG, sin librerías
- [x] Últimos clientes

## Fase 5: Docker y CI (`feature/docker`, `feature/ci`)

- [x] `Dockerfile` con usuario no root, Gunicorn y WhiteNoise
- [x] `docker-compose.yml` con volumen para SQLite, migraciones y datos demo al iniciar
- [x] `.github/workflows/ci.yml` en push y pull request: Python, `check`,
      `makemigrations --check`, pruebas Django, pruebas JS y construcción de la imagen

## Fase 6: Pulido y entrega

- [x] Revisión en navegador a 360, 768, 1024 y 1920 px en ambos temas
- [x] Contraste, teclado, consola limpia y `prefers-reduced-motion`
- [x] README completo y capturas en `docs/screenshots/`
- [x] Instalación desde cero siguiendo solo el README
- [x] Push y CI en verde
- [ ] Correo de entrega
