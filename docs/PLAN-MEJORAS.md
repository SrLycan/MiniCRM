# Plan de las mejoras

Mismo flujo que `PLAN.md`: una rama `feature/*` por fase, fusionada a `develop` con
`--no-ff`, y commits en español por cada paso verificado.

## Fase 1: Tablero Kanban (`feature/kanban`)

- [ ] Spec y plan
- [ ] API: `PATCH` de estado y `page_size`, con pruebas
- [ ] Cliente de API y aviso de columna, con prueba de JS
- [ ] Marcado y estilos del tablero
- [ ] Vista de tablero con alternador, búsqueda y estados de interfaz
- [ ] Mover con selector, y arrastrar y soltar
- [ ] Verificación en navegador: desktop y 360 px

## Fase 2: WhatsApp simulado (`feature/whatsapp-simulado`)

- [ ] Campo `whatsapp_id`, migración y correo reservado
- [ ] Firma y lectura del mensaje, con pruebas
- [ ] Webhook con pruebas de firma, idempotencia y secreto ausente
- [ ] Simulación por API con pruebas
- [ ] Insignia de origen y botón en la interfaz
- [ ] Verificación en navegador

## Fase 3: Cierre

- [ ] `README.md` y `DECISIONES.md`
- [ ] Pruebas completas y CI en verde
