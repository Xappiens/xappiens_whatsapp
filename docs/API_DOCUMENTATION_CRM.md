# 📚 Documentación Completa de la API de WhatsApp para CRM

**Versión:** 1.0.0
**Fecha:** 2025-11-07
**Base URL:** `http://localhost:8084/api` (o la URL de producción)

---

## 🔐 Autenticación

Todas las peticiones requieren el header `X-API-Key` con tu API Key.

```bash
curl -H "X-API-Key: TU_API_KEY" ...
```

---

## 📱 SESIONES

### 1. Crear Sesión
**POST** `/api/sessions`

Crea una nueva sesión de WhatsApp. La sesión se conectará automáticamente y generará un QR code si es necesario.

**Body:**
```json
{
  "sessionId": "mi_sesion_123",
  "sessionName": "Mi Sesión",
  "phoneNumber": "34657032985",
  "webhookUrl": "https://tu-webhook.com/api/webhook",
  "webhookSecret": "tu_secreto_seguro",
  "webhookEvents": ["message", "message_status"]
}
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "id": 93,
    "sessionId": "mi_sesion_123",
    "status": "qr_code",
    "qrCode": "data:image/png;base64,..."
  }
}
```

---

### 2. Listar Sesiones
**GET** `/api/sessions?page=1&limit=20&status=connected`

Obtiene todas las sesiones con paginación y filtros opcionales.

**Query Parameters:**
- `page` (opcional): Número de página (default: 1)
- `limit` (opcional): Resultados por página (default: 20, max: 100)
- `status` (opcional): Filtrar por estado: `connected`, `disconnected`, `qr_code`, `connecting`

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": 93,
        "sessionId": "prueba23_mho8t3iz_ncbzkh",
        "sessionName": "prueba23",
        "status": "connected",
        "phoneNumber": "34657032985",
        "isConnected": true,
        "hasQR": false
      }
    ],
    "pagination": {
      "total": 1,
      "page": 1,
      "limit": 20,
      "pages": 1
    }
  }
}
```

---

### 3. Obtener Sesión Específica
**GET** `/api/sessions/{id}`

Obtiene información detallada de una sesión. Acepta tanto ID numérico como `sessionId` string.

**Ejemplos:**
- `/api/sessions/93` (ID numérico)
- `/api/sessions/prueba23_mho8t3iz_ncbzkh` (sessionId string)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "session": {
      "id": 93,
      "sessionId": "prueba23_mho8t3iz_ncbzkh",
      "sessionName": "prueba23",
      "status": "connected",
      "phoneNumber": "34657032985",
      "isConnected": true,
      "hasQR": false,
      "profile": {
        "name": "Abel Ramos",
        "about": "",
        "profilePictureUrl": "",
        "isBusiness": false
      }
    }
  }
}
```

---

### 4. Obtener Estado de Sesión
**GET** `/api/sessions/{id}/status`

**IMPORTANTE:** Este es el endpoint que debes usar para verificar el estado real de la sesión. Consulta directamente la instancia de Baileys en memoria (fuente de verdad).

**Ejemplos:**
- `/api/sessions/93/status`
- `/api/sessions/prueba23_mho8t3iz_ncbzkh/status`

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "id": 93,
    "sessionId": "prueba23_mho8t3iz_ncbzkh",
    "status": "connected",
    "phoneNumber": "34657032985",
    "lastActivity": "2025-11-07T04:25:04.479Z",
    "isConnected": true,
    "hasQR": false
  }
}
```

**Estados posibles:**
- `connected`: Sesión conectada y lista para enviar mensajes
- `disconnected`: Sesión desconectada
- `qr_code`: Esperando escaneo de QR
- `connecting`: Conectando...

---

### 5. Obtener QR Code
**GET** `/api/sessions/{id}/qr`

Obtiene el código QR de la sesión si está disponible (solo cuando la sesión está en estado `qr_code`).

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "qrCode": "data:image/png;base64,iVBORw0KG...",
    "sessionId": "prueba23_mho8t3iz_ncbzkh",
    "expiresAt": "2025-11-07T04:30:00.000Z",
    "status": "qr_code"
  }
}
```

---

### 6. Conectar Sesión
**POST** `/api/sessions/{id}/connect`

Inicia la conexión de una sesión. Si no tiene credenciales, generará un QR code.

**Respuesta:**
```json
{
  "success": true,
  "message": "Sesión iniciada, generando QR o reconectando...",
  "data": {
    "sessionId": "prueba23_mho8t3iz_ncbzkh",
    "status": "connecting"
  }
}
```

---

### 7. Desconectar Sesión
**POST** `/api/sessions/{id}/disconnect`

Desconecta una sesión de WhatsApp.

**Respuesta:**
```json
{
  "success": true,
  "message": "Sesión desconectada correctamente",
  "data": {
    "sessionId": "prueba23_mho8t3iz_ncbzkh",
    "status": "disconnected"
  }
}
```

---

### 8. Reiniciar Sesión
**POST** `/api/sessions/{id}/restart`

Reinicia una sesión (desconecta y vuelve a conectar).

---

### 9. Eliminar Sesión
**DELETE** `/api/sessions/{id}`

Elimina una sesión completamente (desconecta, elimina credenciales y datos).

---

### 10. Obtener Contactos de Sesión
**GET** `/api/sessions/{id}/contacts`

Obtiene los contactos de una sesión específica.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contacts": [],
    "total": 0,
    "source": "whatsapp"
  }
}
```

---

## 💬 MENSAJES

### 1. Enviar Mensaje de Texto
**POST** `/api/messages/{sessionId}/send`

Envía un mensaje de texto a un número de WhatsApp.

**Body:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": "Hola, este es un mensaje de prueba",
  "type": "text"
}
```

**Parámetros:**
- `to` (requerido): Número de WhatsApp con formato `{numero}@s.whatsapp.net` o solo el número (se formatea automáticamente)
- `message` (requerido): Texto del mensaje (máx 4096 caracteres)
- `type` (opcional): Tipo de mensaje, default: `"text"`

**Respuesta:**
```json
{
  "success": true,
  "message": "Mensaje enviado correctamente",
  "data": {
    "message": {
      "id": 10854,
      "whatsappMessageId": "3EB0DECC554F433B2DE158",
      "chatId": "34657032985@s.whatsapp.net",
      "fromMe": true,
      "body": "Hola, este es un mensaje de prueba",
      "type": "text",
      "status": "sent",
      "timestamp": "2025-11-07T04:25:04.479Z"
    }
  }
}
```

---

### 2. Enviar Imagen
**POST** `/api/messages/{sessionId}/send`

**Body:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "image": {
      "url": "https://ejemplo.com/imagen.jpg"
    },
    "caption": "Descripción de la imagen"
  },
  "type": "image"
}
```

**Alternativas para la imagen:**
- `url`: URL pública de la imagen (debe ser accesible públicamente)
- `path`: Ruta local del archivo en el servidor
- `buffer`: Buffer de la imagen (base64)
- `base64`: String base64 de la imagen

**Ejemplo con base64:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "image": {
      "base64": "iVBORw0KGgoAAAANSUhEUgAA...",
      "mimetype": "image/jpeg"
    },
    "caption": "Imagen desde base64"
  },
  "type": "image"
}
```

**⚠️ Nota:** Las imágenes deben ser accesibles públicamente si usas `url`. Para imágenes privadas, usa `base64` o `buffer`.

---

### 3. Enviar Video
**POST** `/api/messages/{sessionId}/send`

**Body:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "video": {
      "url": "https://ejemplo.com/video.mp4"
    },
    "caption": "Descripción del video"
  },
  "type": "video"
}
```

---

### 4. Enviar Audio
**POST** `/api/messages/{sessionId}/send`

**Body:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "audio": {
      "url": "https://ejemplo.com/audio.mp3"
    },
    "ptt": false
  },
  "type": "audio"
}
```

**Parámetros:**
- `ptt`: `true` para audio de voz (push-to-talk), `false` para música

---

### 5. Enviar Documento
**POST** `/api/messages/{sessionId}/send`

**Body:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "document": {
      "url": "https://ejemplo.com/documento.pdf",
      "fileName": "documento.pdf",
      "mimetype": "application/pdf"
    },
    "caption": "Descripción del documento"
  },
  "type": "document"
}
```

---

### 6. Enviar Ubicación
**POST** `/api/messages/{sessionId}/send`

**Body:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "location": {
      "degreesLatitude": 40.4168,
      "degreesLongitude": -3.7038,
      "name": "Madrid",
      "address": "Plaza Mayor, Madrid"
    }
  },
  "type": "location"
}
```

**Formato simplificado:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "lat": 40.4168,
    "lng": -3.7038,
    "name": "Madrid"
  },
  "type": "location"
}
```

---

### 7. Enviar Contacto
**POST** `/api/messages/{sessionId}/send`

**Body:**
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": {
    "contacts": {
      "displayName": "Juan Pérez",
      "contacts": [
        {
          "vcard": "BEGIN:VCARD\nVERSION:3.0\nFN:Juan Pérez\nTEL;TYPE=CELL:+34612345678\nEND:VCARD"
        }
      ]
    }
  },
  "type": "contact"
}
```

---

### 8. Obtener Mensajes
**GET** `/api/messages/{sessionId}?page=1&limit=50&chatId=34657032985@s.whatsapp.net&type=text&fromMe=false`

Obtiene mensajes de una sesión con filtros opcionales.

**Query Parameters:**
- `page` (opcional): Número de página
- `limit` (opcional): Resultados por página (max: 100)
- `chatId` (opcional): Filtrar por chat específico
- `type` (opcional): Filtrar por tipo: `text`, `image`, `video`, `audio`, `document`, `location`, `contact`, etc.
- `fromMe` (opcional): `true` para solo mensajes enviados, `false` para solo recibidos
- `startDate` (opcional): Fecha inicio (ISO 8601)
- `endDate` (opcional): Fecha fin (ISO 8601)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": 10854,
        "chatId": "34657032985@s.whatsapp.net",
        "fromMe": true,
        "body": "Test final - 05:25:04",
        "type": "text",
        "status": "sent",
        "timestamp": "2025-11-07T04:25:04.479Z",
        "mediaUrl": null,
        "hasReactions": false
      }
    ],
    "pagination": {
      "total": 1,
      "page": 1,
      "limit": 50,
      "pages": 1
    }
  }
}
```

---

### 9. Obtener Conversaciones/Chats
**GET** `/api/messages/{sessionId}/chats?page=1&limit=20`

Obtiene todas las conversaciones (chats) de una sesión.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "chats": [],
    "pagination": {
      "total": 0,
      "page": 1,
      "limit": 20,
      "pages": 0
    }
  }
}
```

---

### 10. Obtener Mensajes de un Chat Específico
**GET** `/api/messages/{sessionId}/{chatId}?page=1&limit=50`

Obtiene todos los mensajes de una conversación específica.

**Ejemplo:**
- `/api/messages/prueba23_mho8t3iz_ncbzkh/34657032985@s.whatsapp.net`

---

### 11. Marcar Mensajes como Leídos
**PUT** `/api/messages/{sessionId}/{chatId}/read`

Marca todos los mensajes de un chat como leídos.

---

### 12. Obtener Estadísticas de Mensajes
**GET** `/api/messages/{sessionId}/stats?startDate=2025-11-01&endDate=2025-11-07`

Obtiene estadísticas de mensajes en un rango de fechas.

---

### 13. Obtener Mensajes No Leídos
**GET** `/api/messages/unread`

Obtiene todos los mensajes no leídos de todas las sesiones.

---

## 👥 CONTACTOS

### 1. Obtener Contactos
**GET** `/api/contacts/{sessionId}?page=1&limit=50&search=nombre`

Obtiene los contactos de una sesión con paginación y búsqueda.

**Query Parameters:**
- `page` (opcional): Número de página
- `limit` (opcional): Resultados por página (max: 100)
- `search` (opcional): Buscar por nombre o número

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contacts": [
      {
        "id": "34657032985@s.whatsapp.net",
        "name": "34657032985",
        "verifiedName": "34657032985",
        "notify": "34657032985",
        "imgUrl": null,
        "isUser": true,
        "isGroup": false,
        "isWAContact": true
      }
    ],
    "pagination": {
      "total": 1,
      "page": 1,
      "limit": 50,
      "pages": 1
    },
    "search": null
  }
}
```

---

### 2. Buscar Contacto por Número
**GET** `/api/contacts/{sessionId}/search/{phoneNumber}`

Busca un contacto específico por número de teléfono.

**Ejemplo:**
- `/api/contacts/prueba23_mho8t3iz_ncbzkh/search/34657032985`

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contact": {
      "id": "34657032985@s.whatsapp.net",
      "name": "34657032985",
      "verifiedName": "34657032985",
      "imgUrl": null,
      "isUser": true,
      "isGroup": false
    }
  }
}
```

---

### 3. Obtener Información de Contacto
**GET** `/api/contacts/{sessionId}/info/{contactId}`

Obtiene información detallada de un contacto específico.

**Ejemplo:**
- `/api/contacts/prueba23_mho8t3iz_ncbzkh/info/34657032985@s.whatsapp.net`

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contact": {
      "id": "34657032985@s.whatsapp.net",
      "name": "Abel Ramos",
      "verifiedName": "Abel Ramos",
      "imgUrl": null,
      "businessProfile": null,
      "status": null,
      "lastSeen": null
    }
  }
}
```

---

### 4. Obtener Estadísticas de Contactos
**GET** `/api/contacts/{sessionId}/stats`

Obtiene estadísticas de contactos de una sesión.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total": 2,
      "users": 2,
      "groups": 0,
      "wAContacts": 2,
      "withNames": 1,
      "withProfilePics": 0
    }
  }
}
```

---

## 🎯 GRUPOS

### 1. Obtener Grupos
**GET** `/api/groups/sessions/{sessionId}?page=1&limit=20`

Obtiene todos los grupos de una sesión.

---

### 2. Crear Grupo
**POST** `/api/groups/sessions/{sessionId}`

Crea un nuevo grupo de WhatsApp.

**Body:**
```json
{
  "subject": "Mi Grupo",
  "participants": ["34657032985@s.whatsapp.net"]
}
```

---

### 3. Obtener Detalles de Grupo
**GET** `/api/groups/sessions/{sessionId}/groups/{groupId}`

Obtiene información detallada de un grupo.

---

### 4. Actualizar Grupo
**PUT** `/api/groups/sessions/{sessionId}/groups/{groupId}`

Actualiza información del grupo (nombre, descripción, etc.).

---

### 5. Agregar Participante
**POST** `/api/groups/sessions/{sessionId}/groups/{groupId}/participants`

Agrega un participante al grupo.

**Body:**
```json
{
  "participantId": "34657032985@s.whatsapp.net"
}
```

---

### 6. Remover Participante
**DELETE** `/api/groups/sessions/{sessionId}/groups/{groupId}/participants`

Remueve un participante del grupo.

**Body:**
```json
{
  "participantId": "34657032985@s.whatsapp.net"
}
```

---

### 7. Promover a Administrador
**POST** `/api/groups/sessions/{sessionId}/groups/{groupId}/promote`

Promueve un participante a administrador del grupo.

**Body:**
```json
{
  "participantId": "34657032985@s.whatsapp.net"
}
```

---

### 8. Generar Código de Invitación
**POST** `/api/groups/sessions/{sessionId}/groups/{groupId}/invite-code`

Genera un código de invitación para el grupo.

---

### 9. Unirse a Grupo con Código
**POST** `/api/groups/join-with-code`

Únete a un grupo usando un código de invitación.

**Body:**
```json
{
  "sessionId": "prueba23_mho8t3iz_ncbzkh",
  "inviteCode": "ABC123DEF456"
}
```

---

## 📸 ESTADOS (Status)

### 1. Obtener Estados
**GET** `/api/status/sessions/{sessionId}?page=1&limit=20`

Obtiene los estados (historias) de una sesión.

---

### 2. Obtener Estados Activos
**GET** `/api/status/sessions/{sessionId}/active`

Obtiene solo los estados activos (no expirados).

---

### 3. Crear Estado
**POST** `/api/status/sessions/{sessionId}`

Crea un nuevo estado (historia).

**Body:**
```json
{
  "type": "image",
  "mediaUrl": "https://ejemplo.com/imagen.jpg",
  "caption": "Mi estado"
}
```

---

### 4. Ver Estado
**POST** `/api/status/sessions/{sessionId}/statuses/{statusId}/view`

Marca un estado como visto.

---

### 5. Agregar Reacción a Estado
**POST** `/api/status/sessions/{sessionId}/statuses/{statusId}/reactions`

Agrega una reacción a un estado.

**Body:**
```json
{
  "reaction": "👍"
}
```

---

### 6. Remover Reacción de Estado
**DELETE** `/api/status/sessions/{sessionId}/statuses/{statusId}/reactions`

Remueve una reacción de un estado.

---

## 📎 MEDIA

### 1. Obtener Archivos Multimedia
**GET** `/api/media/sessions/{sessionId}?page=1&limit=20`

Obtiene todos los archivos multimedia de una sesión.

---

### 2. Subir Archivo Multimedia
**POST** `/api/media/sessions/{sessionId}/upload`

Sube un archivo multimedia para usar en mensajes.

**Form Data:**
- `file`: Archivo a subir

---

### 3. Obtener Archivo Multimedia
**GET** `/api/media/{mediaFileId}`

Obtiene información de un archivo multimedia específico.

---

### 4. Descargar Archivo Multimedia
**GET** `/api/media/{mediaFileId}/download`

Descarga un archivo multimedia.

---

### 5. Eliminar Archivo Multimedia
**DELETE** `/api/media/{mediaFileId}`

Elimina un archivo multimedia.

---

## ⚠️ NOTAS IMPORTANTES

### Estado de Sesión
- **SIEMPRE** usa `/api/sessions/{id}/status` para verificar el estado real de la sesión
- El estado se lee directamente de la instancia de Baileys en memoria (fuente de verdad)
- NO confíes en el campo `status` de la base de datos
- **IMPORTANTE:** Los endpoints aceptan tanto ID numérico (`93`) como `sessionId` string (`prueba23_mho8t3iz_ncbzkh`)

### Formato de Números
- Los números deben incluir el código de país sin el `+`
- Formato completo: `{numero}@s.whatsapp.net`
- Ejemplo: `34657032985@s.whatsapp.net` o simplemente `34657032985`
- El sistema formatea automáticamente si solo envías el número

### Tipos de Mensaje Soportados y Probados
- ✅ `text`: Mensaje de texto (PROBADO ✓)
- ✅ `image`: Imagen con URL pública (PROBADO ✓)
- ✅ `location`: Ubicación (PROBADO ✓)
- ⚠️ `video`: Video (soportado, no probado)
- ⚠️ `audio`: Audio (soportado, no probado)
- ⚠️ `document`: Documento (soportado, no probado)
- ⚠️ `contact`: Contacto (soportado, no probado)
- ⚠️ `sticker`: Sticker (soportado, no probado)

### Errores Comunes
- `SESSION_NOT_CONNECTED`: La sesión no está conectada. Usa `/api/sessions/{id}/connect` primero
- `SESSION_NOT_FOUND`: La sesión no existe
- `MISSING_API_KEY`: Falta el header `X-API-Key`
- `VALIDATION_ERROR`: Datos de entrada inválidos (revisa el formato del mensaje)

### Endpoints Probados y Funcionales
✅ **Sesiones:**
- GET `/api/sessions/{id}/status` - Obtener estado
- GET `/api/sessions/{id}` - Obtener sesión
- GET `/api/sessions` - Listar sesiones
- GET `/api/sessions/{id}/contacts` - Obtener contactos

✅ **Mensajes:**
- POST `/api/messages/{sessionId}/send` - Enviar texto (PROBADO ✓)
- POST `/api/messages/{sessionId}/send` - Enviar imagen (PROBADO ✓)
- POST `/api/messages/{sessionId}/send` - Enviar ubicación (PROBADO ✓)
- GET `/api/messages/{sessionId}` - Obtener mensajes (PROBADO ✓)
- GET `/api/messages/{sessionId}/chats` - Obtener chats (PROBADO ✓)

✅ **Contactos:**
- GET `/api/contacts/{sessionId}` - Obtener contactos (PROBADO)

---

## 🔄 WEBHOOKS - RECEPCIÓN DE MENSAJES EN TIEMPO REAL

### 📥 Cómo Recibir Mensajes del Servidor de Baileys

El servidor de Baileys envía automáticamente **todos los mensajes recibidos** a tu CRM mediante webhooks en tiempo real. Esto permite que el CRM muestre los mensajes entrantes instantáneamente.

---

### ⚙️ Configuración Inicial

#### Opción 1: Configuración Automática al Crear Sesión

Al crear una sesión desde el CRM, incluye uno de estos indicadores para activar automáticamente el envío de webhooks:

**Ejemplo de creación de sesión con webhooks activados:**

```bash
POST /api/sessions
Headers:
  X-API-Key: TU_API_KEY
  X-Frappe-Origin: true  # Opcional pero recomendado
Content-Type: application/json

Body:
{
  "sessionId": "mi_sesion_crm_123",
  "sessionName": "Cliente ABC",
  "phoneNumber": "34657032985",
  "fromFrappe": true  # Activa automáticamente sendToFrappe
}
```

**O usando el header:**
```bash
Headers:
  X-Frappe-Origin: true
```

**O con webhookUrl de Frappe:**
```json
{
  "sessionId": "mi_sesion_crm_123",
  "webhookUrl": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
  "fromFrappe": true
}
```

#### Opción 2: Configuración Manual Después de Crear

Si ya tienes una sesión creada, puedes activar/desactivar el envío de webhooks:

**POST** `/api/sessions/{id}/frappe/configure`

**Body:**
```json
{
  "sendToFrappe": true
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Integración con Frappe activada para la sesión",
  "data": {
    "sessionId": "mi_sesion_crm_123",
    "sendToFrappe": true
  }
}
```

---

### 📨 Formato del Webhook

Cuando llega un mensaje nuevo a cualquier sesión configurada con `sendToFrappe: true`, el servidor envía un POST a la URL configurada en `FRAPPE_WEBHOOK_URL`.

**URL del Webhook:** `https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook`

**Headers enviados:**
```
Content-Type: application/json
X-Webhook-Event: message.received
X-Webhook-Session: {sessionId}
X-Webhook-Signature: sha256={firma_hmac}  # Si está configurado FRAPPE_WEBHOOK_SECRET
```

**Body del Webhook (JSON):**

```json
{
  "event": "message.received",
  "data": {
    "sessionId": "prueba23_mho8t3iz_ncbzkh",
    "session_db_id": 93,
    "message": {
      "whatsappMessageId": "3EB0DECC554F433B2DE158",
      "content": "Hola, este es un mensaje recibido",
      "chatId": "34657032985@s.whatsapp.net",
      "from": "34657032985@s.whatsapp.net",
      "to": "prueba23_mho8t3iz_ncbzkh",
      "timestamp": 1699332304,
      "type": "text",
      "has_attachment": false,
      "media": null
    }
  }
}
```

---

### 📎 Mensajes con Adjuntos

Cuando el mensaje incluye un archivo adjunto (imagen, video, audio, documento), el formato incluye información adicional:

```json
{
  "event": "message.received",
  "data": {
    "sessionId": "prueba23_mho8t3iz_ncbzkh",
    "session_db_id": 93,
    "message": {
      "whatsappMessageId": "3EB0DECC554F433B2DE159",
      "content": "Mira esta imagen",
      "chatId": "34657032985@s.whatsapp.net",
      "from": "34657032985@s.whatsapp.net",
      "to": "prueba23_mho8t3iz_ncbzkh",
      "timestamp": 1699332400,
      "type": "image",
      "has_attachment": true,
      "media": {
        "filename": "imagen.jpg",
        "filesize": 245678,
        "mimetype": "image/jpeg",
        "url": "https://mmg.whatsapp.net/v/t62.7-24/..."
      }
    }
  }
}
```

**Tipos de mensaje soportados:**
- `text`: Mensaje de texto
- `image`: Imagen
- `video`: Video
- `audio`: Audio
- `document`: Documento
- `location`: Ubicación
- `contact`: Contacto
- `sticker`: Sticker

---

### 🔐 Seguridad - Verificación de Firma

El servidor incluye una firma HMAC-SHA256 en el header `X-Webhook-Signature` para verificar la autenticidad del webhook.

**Cómo verificar la firma en el CRM:**

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload_body, signature_header, secret):
    """
    Verifica que el webhook viene del servidor de Baileys

    Args:
        payload_body: Cuerpo del request (string o bytes)
        signature_header: Valor del header X-Webhook-Signature (ej: "sha256=abc123...")
        secret: FRAPPE_WEBHOOK_SECRET

    Returns:
        bool: True si la firma es válida
    """
    if not signature_header or not signature_header.startswith('sha256='):
        return False

    expected_signature = signature_header.replace('sha256=', '')

    if isinstance(payload_body, str):
        payload_body = payload_body.encode('utf-8')

    computed_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)
```

**Ejemplo de uso en Frappe:**

```python
import frappe
import hmac
import hashlib

@frappe.whitelist(allow_guest=True)
def handle_webhook():
    # Obtener el secreto desde configuración
    secret = frappe.conf.get('frappe_webhook_secret') or 'tu_secreto'

    # Obtener firma del header
    signature = frappe.request.headers.get('X-Webhook-Signature', '')

    # Obtener body del request
    payload = frappe.request.get_data(as_text=True)

    # Verificar firma
    if not verify_webhook_signature(payload, signature, secret):
        frappe.throw('Firma inválida', frappe.PermissionError)

    # Procesar webhook
    data = frappe.parse_json(payload)
    # ... procesar mensaje ...
```

---

### 📊 Campos del Mensaje

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `event` | string | Siempre `"message.received"` para mensajes entrantes |
| `data.sessionId` | string | ID de la sesión de WhatsApp (ej: `"prueba23_mho8t3iz_ncbzkh"`) |
| `data.session_db_id` | number | ID numérico de la sesión en la base de datos |
| `data.message.whatsappMessageId` | string | ID único del mensaje en WhatsApp |
| `data.message.content` | string | Contenido del mensaje (texto o descripción) |
| `data.message.chatId` | string | ID del chat (número con formato `{numero}@s.whatsapp.net`) |
| `data.message.from` | string | Número que envió el mensaje |
| `data.message.to` | string | Número que recibió el mensaje (tu sesión) |
| `data.message.timestamp` | number | Timestamp Unix (segundos desde 1970) |
| `data.message.type` | string | Tipo de mensaje (`text`, `image`, `video`, etc.) |
| `data.message.has_attachment` | boolean | `true` si el mensaje tiene archivo adjunto |
| `data.message.media` | object\|null | Información del archivo adjunto (si aplica) |
| `data.message.media.filename` | string | Nombre del archivo |
| `data.message.media.filesize` | number | Tamaño del archivo en bytes |
| `data.message.media.mimetype` | string | Tipo MIME del archivo |
| `data.message.media.url` | string | URL temporal del archivo (válida por tiempo limitado) |

---

### ⚠️ Comportamiento Importante

1. **Solo mensajes recibidos**: El servidor **SOLO** envía webhooks para mensajes **recibidos** (no para mensajes enviados desde el CRM).

2. **Tiempo real**: Los mensajes se envían inmediatamente cuando llegan, no hay delay.

3. **Mensajes históricos**: Los mensajes antiguos (al sincronizar) **NO** se envían como webhooks para evitar spam.

4. **Múltiples sesiones**: Cada sesión con `sendToFrappe: true` enviará webhooks a la misma URL. Identifica la sesión usando `data.sessionId`.

5. **Timeout**: El servidor espera respuesta del webhook por máximo 7 segundos. Si no responde, se registra un error pero el mensaje se guarda igualmente.

---

### 🔍 Verificar Estado de Integración

**GET** `/api/sessions/{id}/frappe/status`

Verifica si una sesión está configurada para enviar webhooks a Frappe.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "sessionId": "prueba23_mho8t3iz_ncbzkh",
    "sendToFrappe": true,
    "status": "connected",
    "sessionName": "prueba23"
  }
}
```

---

### 📝 Ejemplo Completo de Implementación en Frappe

```python
import frappe
import hmac
import hashlib
import json

@frappe.whitelist(allow_guest=True)
def handle_webhook():
    """
    Endpoint para recibir webhooks del servidor de Baileys
    """
    try:
        # 1. Verificar firma (seguridad)
        signature = frappe.request.headers.get('X-Webhook-Signature', '')
        session_id = frappe.request.headers.get('X-Webhook-Session', '')
        event_type = frappe.request.headers.get('X-Webhook-Event', '')

        payload = frappe.request.get_data(as_text=True)
        secret = frappe.conf.get('frappe_webhook_secret')

        if secret and not verify_signature(payload, signature, secret):
            frappe.throw('Firma inválida', frappe.PermissionError)

        # 2. Parsear datos
        data = frappe.parse_json(payload)

        # 3. Verificar que es un mensaje recibido
        if event_type != 'message.received':
            return {'success': True, 'message': 'Evento ignorado'}

        # 4. Extraer información del mensaje
        message_data = data.get('data', {}).get('message', {})
        session_id = data.get('data', {}).get('sessionId')

        # 5. Guardar mensaje en Frappe
        whatsapp_message = frappe.get_doc({
            'doctype': 'WhatsApp Message',
            'session_id': session_id,
            'whatsapp_message_id': message_data.get('whatsappMessageId'),
            'from': message_data.get('from'),
            'to': message_data.get('to'),
            'content': message_data.get('content'),
            'type': message_data.get('type'),
            'timestamp': message_data.get('timestamp'),
            'has_attachment': message_data.get('has_attachment', False),
            'media_url': message_data.get('media', {}).get('url') if message_data.get('has_attachment') else None
        })
        whatsapp_message.insert(ignore_permissions=True)

        # 6. Notificar en tiempo real (opcional)
        frappe.publish_realtime(
            'whatsapp_message_received',
            {
                'session_id': session_id,
                'message': message_data
            }
        )

        return {'success': True, 'message_id': whatsapp_message.name}

    except Exception as e:
        frappe.log_error(f'Error procesando webhook: {str(e)}')
        frappe.throw('Error procesando webhook', frappe.ValidationError)

def verify_signature(payload, signature_header, secret):
    """Verifica la firma HMAC del webhook"""
    if not signature_header or not signature_header.startswith('sha256='):
        return False

    expected_signature = signature_header.replace('sha256=', '')
    computed_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)
```

---

### 🧪 Probar Webhooks

Para probar que los webhooks funcionan:

1. **Crear una sesión con `sendToFrappe: true`**
2. **Enviar un mensaje de WhatsApp a esa sesión** desde otro número
3. **Verificar que el webhook llega al CRM** con el mensaje recibido

**Nota:** Los mensajes enviados desde el CRM usando `/api/messages/{sessionId}/send` **NO** generan webhooks (solo los recibidos).

---

## 📞 Soporte

Para más información o soporte, contacta al equipo de desarrollo.

