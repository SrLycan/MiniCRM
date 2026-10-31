# Spec: Tablero Kanban y WhatsApp simulado

Mejoras visibles sobre Órbita CRM, sin romper la simplicidad del proyecto base descrito en
`SPEC.md`.

**Fuera de alcance:** etapas nuevas de venta e integración real con Meta.

## Tablero Kanban

**Objetivo:** ver y mover la cartera por estado sin abrir el formulario.

- El tablero es una página propia, `/tablero/`, debajo de Clientes en el menú.
- El tablero tiene una columna por cada estado actual: Prospecto, Cliente e Inactivo.
- Cada tarjeta muestra avatar, nombre, empresa, origen y acciones de editar y eliminar.
- Tiene su propio buscador. No lleva filtros por estado ni paginación, porque las columnas
  ya cumplen esa función.
- Cada columna muestra hasta 50 clientes y su total. Si hay más, avisa cuántos se muestran.

**Mover una tarjeta**

- Con ratón: arrastrar y soltar en otra columna.
- Con teclado o en pantalla táctil: el selector de estado de la tarjeta. Arrastrar con
  HTML nativo no funciona con el dedo, y el selector da la misma función sin dependencias.
- El cambio se ve al instante. Si el servidor lo rechaza, la tarjeta vuelve a su columna y
  aparece un toast de error.

**API**

| Método y ruta | Uso | Respuestas |
|---|---|---|
| `PATCH /api/clients/<id>/` | Cambiar solo el estado con `{ "status": "client" }` | 200, 400, 404 |
| `GET /api/clients/?page_size=` | Tamaño de página opcional, de 1 a 100 | 200 |

**Responsive:** tres columnas desde 900 px y una sola columna por debajo, sin
desplazamiento horizontal de 360 a 1920 px.

### Criterios de aceptación

- [x] Arrastrar una tarjeta cambia su estado y persiste al recargar.
- [x] El selector cambia el estado solo con teclado.
- [x] Un error del servidor devuelve la tarjeta a su columna y lo informa.
- [x] Editar y eliminar funcionan desde el tablero.
- [x] La búsqueda filtra las tres columnas.
- [x] Los estados de carga, vacío y error se ven bien en el tablero.

## WhatsApp simulado

**Objetivo:** mostrar cómo un mensaje entrante se convierte en un prospecto, con la misma
seguridad de un webhook real pero sin depender de Meta.

**Webhook:** `POST /api/webhooks/whatsapp/`

- No usa sesión ni CSRF: lo autentica la firma `X-Hub-Signature-256`, un HMAC SHA-256 del
  cuerpo crudo con `WHATSAPP_APP_SECRET`, comparado en tiempo constante.
- Acepta el formato de Meta, `entry[].changes[].value`, con `messages` y `contacts`.
- Ignora los eventos sin mensajes, como las confirmaciones de entrega.

| Situación | Respuesta |
|---|---|
| Mensaje válido, procesado o repetido | 200 |
| Firma ausente o incorrecta | 403 `INVALID_SIGNATURE` |
| Cuerpo que no es un objeto JSON | 400 `INVALID_JSON` |
| Secreto sin configurar | 503 `WEBHOOK_NOT_CONFIGURED` |

**Prospecto creado**

- Nombre tomado del perfil de WhatsApp, o `WhatsApp +<número>` si no sirve.
- Teléfono en formato internacional y estado `prospect`.
- El número queda en `whatsapp_id`, único en la base de datos. Un segundo mensaje del mismo
  número no crea otro prospecto, aunque luego se le haya puesto un correo real.
- Si el teléfono ya pertenece a un cliente, el mensaje se asocia a él y conserva sus datos.
  `0991234567`, `+593 99 123 4567` y `593991234567` cuentan como el mismo número.

**Correo:** WhatsApp no entrega correo y `Client.email` es obligatorio y único. El prospecto
recibe `<número>@whatsapp.invalid`, un dominio reservado que nunca entrega correo. La API lo
devuelve vacío, la interfaz muestra "Sin dato" y el formulario pide el correo real al editar.

**Simulación:** los botones de la pantalla de WhatsApp llaman al servidor con sesión y CSRF.
El servidor arma un mensaje con el formato de Meta, lo firma y lo pasa por el mismo código
del webhook. El secreto nunca llega al navegador.

**Chat:** apartado **WhatsApp** en el menú, con la lista de conversaciones y el chat.

- Cada mensaje se guarda en `WhatsAppMessage`. `wa_message_id` evita duplicar los reintentos
  de Meta, y al eliminar un cliente se eliminan sus mensajes.
- Responder guarda un mensaje saliente. Un aviso visible aclara que no se envía a WhatsApp.
- **Simular respuesta del cliente** hace entrar un mensaje por el webhook firmado.
- **Simular cliente nuevo** crea un prospecto con su primer mensaje y abre su chat.
- Tabla y tablero enlazan al chat de cada cliente con teléfono.
- En móvil la lista y el chat se muestran uno a la vez.

| Método y ruta | Uso |
|---|---|
| `GET /api/conversations/` | Conversaciones, de la más reciente a la más antigua |
| `GET /api/conversations/<id>/` | Datos del cliente y sus mensajes |
| `POST /api/conversations/<id>/messages/` | Responder, hasta 1000 caracteres |
| `POST /api/conversations/<id>/simulate-reply/` | Simular una respuesta del cliente |

### Criterios de aceptación

- [x] Una firma válida crea el prospecto con su insignia de origen.
- [x] Una firma incorrecta o ausente responde 403 y no crea nada.
- [x] El mismo número repetido no crea un duplicado.
- [x] Sin secreto configurado el webhook falla cerrado con 503.
- [x] Editar un prospecto de WhatsApp exige un correo real y conserva su origen.
- [x] Mover un prospecto de WhatsApp en el tablero funciona aunque no tenga correo real.
- [x] Un cliente registrado que escribe conserva su correo, empresa y estado.
- [x] Responder y simular una respuesta funcionan sin recargar y persisten.
- [x] El HTML escrito en un mensaje se muestra como texto.

## Deshacer al eliminar

**Objetivo:** recuperarse de un error sin perder la confirmación previa que exige el
enunciado.

- Al confirmar, el cliente desaparece de la vista y un toast ofrece **Deshacer** durante 6
  segundos. El foco pasa a ese botón para quien usa el teclado.
- El `DELETE` se envía cuando termina ese tiempo. Deshacer solo cancela el envío, así que el
  cliente conserva su `id` y su fecha de creación, sin papelera ni cambios en el modelo.
- Mientras el borrado está pendiente, el cliente no aparece en la tabla ni en el tablero,
  aunque se busque.
- Si la persona sale de la página antes de tiempo, el `DELETE` se envía con `keepalive`.
- Si el servidor rechaza el borrado, un toast lo informa y el cliente vuelve a la lista.

### Criterios de aceptación

- [x] Sigue pidiendo confirmación antes de eliminar.
- [x] Deshacer devuelve al cliente con sus mismos datos, en ambas vistas.
- [x] Sin Deshacer, el cliente se elimina de verdad al terminar el tiempo.
- [x] Salir de la página durante el tiempo de espera elimina al cliente.
- [x] Un error del servidor devuelve al cliente y se informa.
- [x] Varias eliminaciones seguidas se deshacen por separado.
