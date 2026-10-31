# Plan de implementación

Flujo de Git: `main` estable, `develop` de integración y una rama `feature/*` por fase,
fusionada con `--no-ff`. Commits convencionales en inglés, como los ejemplos del enunciado.
Cada fase termina verificada antes de pasar a la siguiente.

## Fase 0: Base del repositorio

- [ ] `git init`, `main` y `develop`, `.gitignore`, `.env.example`, `requirements.txt`
- [ ] Proyecto Django `config`, app `clients`, configuración por variables de entorno

## Fase 1: Backend (`feature/client-model`, `feature/client-api`)

- [ ] Modelo `Client`, restricciones, migración y `ClientAdmin`
- [ ] `ClientForm` con normalización y mensajes en español
- [ ] API JSON con errores uniformes y estadísticas
- [ ] Comando `seed_demo` idempotente
- [ ] Pruebas de modelo, validaciones, API, CSRF, búsqueda, filtro, orden y paginación

## Fase 1.5: Autenticación (`feature/auth`)

- [ ] App `accounts`, login, logout y bloqueo por intentos
- [ ] Protección de páginas y API, usuario demo en `seed_demo`
- [ ] Pruebas de sesión, 401, redirección y bloqueo

## Fase 2: Sistema visual (`feature/design-system`)

- [ ] Tokens de color, tipografía, espacio y movimiento para ambos temas
- [ ] Fondo vivo, cristal en tres niveles, botones, campos, chips e insignias
- [ ] Plantilla base con navegación responsive, logo SVG y selector de tema
- [ ] Pantalla de login

## Fase 3: Vista de clientes (`feature/clients-ui`)

- [ ] Cliente `api.js` con CSRF y errores uniformes
- [ ] Tabla y tarjetas móviles, esqueletos y estados vacío y de error
- [ ] Búsqueda con debounce y cancelación, filtro, orden, paginación y estado en la URL
- [ ] Modal de crear y editar, validación, bloqueo al enviar y errores del backend
- [ ] Confirmación al eliminar y toasts

## Fase 4: Panel (`feature/dashboard`)

- [ ] KPIs con contador animado
- [ ] Anillo de estados y barras de altas en SVG, sin librerías
- [ ] Últimos clientes

## Fase 5: Docker y CI (`feature/docker`, `feature/ci`)

- [ ] `Dockerfile` con usuario no root, Gunicorn y WhiteNoise
- [ ] `docker-compose.yml` con volumen para SQLite, migraciones y datos demo al iniciar
- [ ] `.github/workflows/ci.yml` en push y pull request: Python, `check`,
      `makemigrations --check`, pruebas Django, pruebas JS y construcción de la imagen

## Fase 6: Pulido y entrega

- [ ] Revisión en navegador a 360, 768, 1024 y 1920 px en ambos temas
- [ ] Contraste, teclado, consola limpia y `prefers-reduced-motion`
- [ ] README completo y capturas en `docs/screenshots/`
- [ ] Instalación desde cero siguiendo solo el README
- [ ] Fusión a `main`, push y CI en verde
- [ ] Borrador del correo de entrega
