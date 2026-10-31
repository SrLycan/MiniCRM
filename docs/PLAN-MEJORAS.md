# Plan de las mejoras

Mismo flujo que `PLAN.md`: una rama `feature/*` por fase, fusionada a `develop` con
`--no-ff`, y commits en español por cada paso verificado.

## Fase 1: Tablero Kanban (`feature/kanban`)

- [x] Spec y plan
- [x] API: `PATCH` de estado y `page_size`, con pruebas
- [x] Cliente de API y aviso de columna, con prueba de JS
- [x] Marcado y estilos del tablero
- [x] Vista de tablero con alternador, búsqueda y estados de interfaz
- [x] Mover con selector, y arrastrar y soltar
- [x] Verificación en navegador: desktop y 360 px

## Fase 2: WhatsApp simulado (`feature/whatsapp-simulado`)

- [x] Campo `whatsapp_id`, migración y correo reservado
- [x] Firma y lectura del mensaje, con pruebas
- [x] Webhook con pruebas de firma, idempotencia y secreto ausente
- [x] Simulación por API con pruebas
- [x] Insignia de origen y botón en la interfaz
- [x] Verificación en navegador

## Fase 3: Cierre

- [x] `README.md` y `DECISIONES.md`
- [x] Pruebas completas y CI en verde

## Fase 4: Deshacer al eliminar (`feature/deshacer-eliminar`)

- [x] Acciones aplazadas con pruebas de JS
- [x] Toast con acción
- [x] Eliminación aplazada, Deshacer y envío al salir
- [x] Verificación en navegador

## Fase 5: Seguridad (`feature/seguridad`)

- [x] Auditoría de archivos expuestos, cabeceras, historia de git, imagen y dependencias
- [x] Límites del login, bloqueo por IP y bloqueo en Admin
- [x] CSP sin scripts en línea, sesiones de 8 horas y límite de tamaño
- [x] Usuario demo sin permisos de superusuario

## Fase 6: Navegación y chat (`feature/tablero-propio`, `feature/chat-whatsapp`)

- [x] Tablero como página propia debajo de Clientes
- [x] Mensajes guardados y asociación por teléfono al cliente existente
- [x] API de conversaciones con pruebas
- [x] Pantalla de chat con respuesta y simulación
- [x] Verificación en navegador: desktop y 360 px
