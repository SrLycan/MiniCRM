# Spec: Tablero Kanban y WhatsApp simulado

Dos mejoras visibles sobre Órbita CRM, sin romper la simplicidad del proyecto base
descrito en `SPEC.md`.

**Fuera de alcance:** etapas nuevas de venta, bandeja de conversaciones e integración real
con Meta.

## Tablero Kanban

**Objetivo:** ver y mover la cartera por estado sin abrir el formulario.

- La página de clientes alterna entre **Tabla** y **Tablero**. La vista elegida se guarda
  en la URL con `view=board`.
- El tablero tiene una columna por cada estado actual: Prospecto, Cliente e Inactivo.
- Cada tarjeta muestra avatar, nombre, empresa, origen y acciones de editar y eliminar.
- La búsqueda funciona igual en ambas vistas. En el tablero se ocultan los filtros por
  estado, el orden y la paginación, porque las columnas ya cumplen esa función.
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

- [x] La vista se conserva al recargar y al compartir la URL.
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
- El texto del mensaje no se guarda, porque no hay bandeja de conversaciones.

**Correo:** WhatsApp no entrega correo y `Client.email` es obligatorio y único. El prospecto
recibe `<número>@whatsapp.invalid`, un dominio reservado que nunca entrega correo. La API lo
devuelve vacío, la interfaz muestra "Sin dato" y el formulario pide el correo real al editar.

**Simulación:** el botón "Simular mensaje de WhatsApp" llama a
`POST /api/clients/simulate-whatsapp/`, con sesión y CSRF. El servidor arma un mensaje con el
formato de Meta, lo firma y lo pasa por el mismo código del webhook. El secreto nunca llega
al navegador.

**Interfaz:** insignia "WhatsApp" en la tabla y en el tablero. El botón deja claro que es una
simulación y un toast confirma el prospecto creado.

### Criterios de aceptación

- [x] Una firma válida crea el prospecto con su insignia de origen.
- [x] Una firma incorrecta o ausente responde 403 y no crea nada.
- [x] El mismo número repetido no crea un duplicado.
- [x] Sin secreto configurado el webhook falla cerrado con 503.
- [x] Editar un prospecto de WhatsApp exige un correo real y conserva su origen.
- [x] Mover un prospecto de WhatsApp en el tablero funciona aunque no tenga correo real.
- [x] El botón crea un prospecto visible sin recargar, en ambas vistas.
