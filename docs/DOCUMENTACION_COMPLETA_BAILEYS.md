# 📚 Documentación Completa - Servidor Baileys WhatsApp API

**Versión:** 2.0.0
**URL Base:** `https://api.inbox-hub.com`
**Fecha:** Octubre 2025
**Última actualización:** Octubre 2025

---

## 📋 Índice

1. [Autenticación](#-autenticación)
2. [Sesiones WhatsApp](#-sesiones-whatsapp)
3. [Mensajes](#-mensajes)
4. [Contactos](#-contactos)
5. [Grupos](#-grupos)
6. [Estados WhatsApp](#-estados-whatsapp)
7. [Multimedia](#-multimedia)
8. [Plantillas de Mensajes](#-plantillas-de-mensajes)
9. [Webhooks](#-webhooks)
10. [Organizaciones](#-organizaciones)
11. [Auditoría](#-auditoría)
12. [Sistema y Salud](#-sistema-y-salud)

---

## 🔐 Autenticación

### Headers Requeridos

**IMPORTANTE:** Las rutas de WhatsApp (sessions, messages, contacts, groups, status, media) usan **SOLO API Key**, NO requieren JWT Token.

#### **Rutas de WhatsApp (Solo API Key):**
```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: application/json
```

**⚠️ NOTA:** Esta es la API Key que debes usar para todas las rutas de WhatsApp (sessions, messages, contacts, groups, status, media).

#### **Rutas de Autenticación y Organizaciones (JWT Token):**
```http
Authorization: Bearer {JWT_TOKEN}
Content-Type: application/json
```

#### **Rutas Públicas (Sin autenticación):**
- `/health`
- `/`
- `/api/auth/login`
- `/api/auth/register`
- `/api/webhooks/test/connectivity`
- `/api/webhooks/test/signature`

### Endpoints de Autenticación

#### **POST** `/api/auth/register`
Registrar nuevo usuario.

**Autenticación:** ❌ No requerida
**Rate Limit:** 5 requests/15min

**Body:**
```json
{
  "username": "string (3-50 chars, alphanumeric)",
  "email": "string (valid email)",
  "password": "string (min 6 chars, 1 upper, 1 lower, 1 number)",
  "firstName": "string (optional, max 100 chars)",
  "lastName": "string (optional, max 100 chars)",
  "phone": "string (optional, valid mobile)",
  "organizationName": "string (optional)"
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Usuario registrado correctamente",
  "data": {
    "user": {
      "id": 2,
      "username": "grupoatu",
      "email": "apiwhatsapp@grupoatu.com",
      "globalRole": "user",
      "isActive": true
    },
    "emailVerificationRequired": true
  }
}
```

#### **POST** `/api/auth/login`
Iniciar sesión y obtener tokens.

**Autenticación:** ❌ No requerida
**Rate Limit:** 5 requests/15min

**Body:**
```json
{
  "identifier": "string (email or username)",
  "password": "string"
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Login exitoso",
  "data": {
    "user": {
      "id": 2,
      "username": "grupoatu",
      "email": "apiwhatsapp@grupoatu.com",
      "role": "user"
    },
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": "24h"
  }
}
```

#### **POST** `/api/auth/refresh-token`
Renovar token de acceso.

**Autenticación:** ❌ No requerida

**Body:**
```json
{
  "refreshToken": "string"
}
```

#### **GET** `/api/auth/profile`
Obtener perfil del usuario actual.

**Autenticación:** ✅ JWT Token

#### **PUT** `/api/auth/profile`
Actualizar perfil del usuario.

**Autenticación:** ✅ JWT Token

#### **PUT** `/api/auth/change-password`
Cambiar contraseña.

**Autenticación:** ✅ JWT Token

**Body:**
```json
{
  "currentPassword": "string",
  "newPassword": "string (min 6 chars, 1 upper, 1 lower, 1 number)"
}
```

#### **POST** `/api/auth/logout`
Cerrar sesión.

**Autenticación:** ✅ JWT Token

#### **POST** `/api/auth/request-password-reset`
Solicitar restablecimiento de contraseña.

**Body:**
```json
{
  "email": "string (valid email)"
}
```

#### **POST** `/api/auth/reset-password`
Restablecer contraseña con token.

**Body:**
```json
{
  "token": "string",
  "newPassword": "string (min 6 chars, 1 upper, 1 lower, 1 number)"
}
```

---

## 📱 Sesiones WhatsApp

**Base Path:** `/api/sessions`
**Autenticación:** ✅ **SOLO API Key** (NO requiere JWT Token)
**Rate Limit:** 30 requests/min

**Headers requeridos:**
```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: application/json
```

### Convenciones de Identificación

- **`id`**: Identificador numérico interno de la sesión (usado en rutas `/api/sessions/{id}`)
- **`sessionId`**: Identificador alfanumérico Baileys (usado en rutas `/api/messages/{sessionId}`, `/api/contacts/{sessionId}`)

### Endpoints

#### **POST** `/api/sessions`
Crear nueva sesión WhatsApp.

**Body:**
```json
{
  "sessionId": "string (3-100 chars, alphanumeric + _ -)",
  "sessionName": "string (1-255 chars)",
  "phoneNumber": "string (optional, valid mobile)",
  "webhookUrl": "string (optional, valid URL)",
  "webhookSecret": "string (optional, 16-255 chars)",
  "webhookEvents": ["array of event names"]
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Sesión creada exitosamente",
  "data": {
    "id": 2,
    "sessionId": "nueva_sesion_wa",
    "sessionName": "Mi Sesión WhatsApp",
    "status": "pending",
    "phoneNumber": null,
    "qrCode": null,
    "createdAt": "2025-10-14T06:00:00.000Z"
  }
}
```

**Nota para integración con Frappe:**
- Incluir header `X-Frappe-Origin: true` o body `{"fromFrappe": true}`
- O usar `webhookUrl` que contenga "crm.grupoatu.com"

#### **GET** `/api/sessions`
Listar sesiones del usuario.

**Query Parameters:**
- `page`: number (optional, default: 1)
- `limit`: number (optional, default: 10, max: 100)
- `status`: string (optional: disconnected, connecting, connected, qr_code, error, rate_limited)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": 2,
        "sessionId": "nueva_sesion_wa",
        "sessionName": "Mi Sesión WhatsApp",
        "status": "connected",
        "phoneNumber": "34657032985",
        "lastActivity": "2025-10-14T06:30:00.000Z",
        "createdAt": "2025-10-14T06:00:00.000Z"
      }
    ],
    "pagination": {
      "total": 1,
      "page": 1,
      "limit": 10,
      "pages": 1
    }
  }
}
```

#### **GET** `/api/sessions/stats`
Estadísticas de sesiones del usuario.

#### **GET** `/api/sessions/:id`
Obtener detalles de una sesión específica (por ID numérico).

#### **GET** `/api/sessions/:id/qr`
Obtener código QR de una sesión (Base64).

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "qrCode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "sessionId": "nueva_sesion_wa",
    "expiresAt": "2025-10-14T06:35:00.000Z",
    "status": "pending"
  }
}
```

#### **GET** `/api/sessions/:id/status`
Obtener estado de una sesión (por ID numérico).

#### **GET** `/api/sessions/:sessionId/status`
Obtener estado de una sesión (por sessionId string).

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "sessionId": "nueva_sesion_wa",
    "status": "connected",
    "phoneNumber": "34657032985",
    "lastActivity": "2025-10-14T06:30:00.000Z",
    "isConnected": true,
    "hasQR": false
  }
}
```

#### **POST** `/api/sessions/:id/connect`
Iniciar proceso de conexión o regenerar QR.

**Respuesta:**
```json
{
  "success": true,
  "message": "Proceso de conexión iniciado",
  "data": {
    "sessionId": "nueva_sesion_wa",
    "status": "pending"
  }
}
```

#### **POST** `/api/sessions/:id/disconnect`
Desconectar una sesión.

#### **POST** `/api/sessions/:id/restart`
Reiniciar una sesión.

#### **DELETE** `/api/sessions/:id`
Eliminar una sesión.

#### **GET** `/api/sessions/:id/contacts`
Obtener contactos de una sesión (fallback desde BD).

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contacts": [...],
    "total": 150,
    "source": "whatsapp"
  }
}
```

#### **POST** `/api/sessions/:sessionId/sync`
Sincronización forzada completa de contactos y chats.

**Respuesta:**
```json
{
  "success": true,
  "message": "Sincronización forzada completada exitosamente",
  "data": {
    "sessionId": "nueva_sesion_wa",
    "contactsSynced": 150,
    "chatsSynced": 25,
    "timestamp": "2025-10-14T06:45:00.000Z"
  }
}
```

#### **POST** `/api/sessions/:sessionId/repair-conversations`
Reparar conversaciones faltantes (crea conversaciones para chats huérfanos).

**Respuesta:**
```json
{
  "success": true,
  "message": "Reparación completada: 5 conversaciones creadas",
  "data": {
    "sessionId": "nueva_sesion_wa",
    "repairedConversations": [...],
    "totalRepaired": 5,
    "timestamp": "2025-10-14T06:50:00.000Z"
  }
}
```

#### **POST** `/api/sessions/:id/frappe/configure`
Configurar integración con Frappe.

**Body:**
```json
{
  "sendToFrappe": true
}
```

#### **GET** `/api/sessions/:id/frappe/status`
Obtener estado de integración con Frappe.

#### **GET** `/api/sessions/frappe/sessions`
Obtener sesiones configuradas para Frappe.

---

## 💬 Mensajes

**Base Path:** `/api/messages`
**Autenticación:** ✅ **SOLO API Key** (NO requiere JWT Token)
**Rate Limit:** 10 messages/min

**Headers requeridos:**
```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: application/json
```

### Endpoints

#### **POST** `/api/messages/:sessionId/send`
Enviar mensaje por WhatsApp.

**Body:**
```json
{
  "to": "string (valid mobile phone or JID)",
  "message": "string (1-4096 chars)",
  "type": "string (optional, default: text)"
}
```

**Tipos de mensaje soportados:** `text`, `image`, `video`, `audio`, `document`, `sticker`, `location`, `contact`, `poll`, `reaction`, `ephemeral`, `other`

**Respuesta:**
```json
{
  "success": true,
  "message": "Mensaje enviado exitosamente",
  "data": {
    "messageId": "3EB0C767D26A1B2E5F8A",
    "to": "34612345678",
    "message": "Hola! Mensaje de prueba",
    "type": "text",
    "status": "sent",
    "timestamp": "2025-10-14T06:45:00.000Z"
  }
}
```

**Nota importante:** El campo `to` acepta:
- Número de teléfono sin formato: `"34612345678"`
- JID completo: `"34612345678@s.whatsapp.net"`

#### **GET** `/api/messages/:sessionId`
Listar mensajes de una sesión.

**Query Parameters:**
- `page`: number (optional, default: 1)
- `limit`: number (optional, default: 50, max: 100)
- `chatId`: string (optional, filter by chat)
- `type`: string (optional, filter by message type)
- `fromMe`: boolean (optional, filter sent/received)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": 1,
        "whatsappMessageId": "3EB0C767D26A1B2E5F8A",
        "chatId": "34612345678@s.whatsapp.net",
        "from": "34657032985@s.whatsapp.net",
        "to": "34612345678@s.whatsapp.net",
        "fromMe": true,
        "type": "text",
        "content": "Hola! Mensaje de prueba",
        "timestamp": "2025-10-14T06:45:00.000Z",
        "status": "delivered",
        "isRead": false
      }
    ],
    "pagination": {
      "total": 25,
      "page": 1,
      "limit": 50,
      "pages": 1
    }
  }
}
```

#### **GET** `/api/messages/:sessionId/chats`
Obtener lista de chats/conversaciones de una sesión.

**Query Parameters:**
- `page`: number (optional, default: 1)
- `limit`: number (optional, default: 20, max: 100)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "chats": [
      {
        "chatId": "34612345678@s.whatsapp.net",
        "name": "Juan Pérez",
        "contactName": "Juan Pérez",
        "isGroup": false,
        "lastMessage": {
          "body": "Hola! Mensaje de prueba",
          "timestamp": 1729443600,
          "fromMe": true
        },
        "unreadCount": 0,
        "messageCount": 25,
        "totalMessages": 25,
        "profilePicture": "https://..."
      }
    ],
    "pagination": {
      "total": 5,
      "page": 1,
      "limit": 20,
      "pages": 1
    }
  }
}
```

**Nota importante para Frappe CRM:**
Cada chat debe incluir obligatoriamente:
- `id._serialized` o `chatId` o `jid`
- `name` o `contactName`
- `isGroup`
- `lastMessage` (con `body`, `timestamp`, `fromMe`)
- `unreadCount`
- `messageCount` o `totalMessages`

#### **GET** `/api/messages/:sessionId/:chatId`
Obtener mensajes de un chat específico.

**Query Parameters:**
- `page`: number (optional, default: 1)
- `limit`: number (optional, default: 50, max: 100)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": 1,
        "whatsappMessageId": "3EB0C767D26A1B2E5F8A",
        "chatId": "34612345678@s.whatsapp.net",
        "content": "Hola! ¿Cómo estás?",
        "fromMe": false,
        "timestamp": "2025-10-14T06:44:00.000Z",
        "status": "received"
      }
    ],
    "pagination": {
      "total": 2,
      "page": 1,
      "limit": 50,
      "pages": 1
    },
    "chatInfo": {
      "chatId": "34612345678@s.whatsapp.net",
      "name": "Juan Pérez",
      "isGroup": false
    }
  }
}
```

#### **PUT** `/api/messages/:sessionId/:chatId/read`
Marcar mensajes como leídos.

**Respuesta:**
```json
{
  "success": true,
  "message": "Mensajes marcados como leídos",
  "data": {
    "markedCount": 3
  }
}
```

#### **GET** `/api/messages/:sessionId/stats`
Estadísticas de mensajes de una sesión.

**Query Parameters:**
- `startDate`: string (optional, ISO 8601 date)
- `endDate`: string (optional, ISO 8601 date)

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total": 150,
      "sent": 75,
      "received": 75,
      "byType": {
        "text": 120,
        "image": 20,
        "video": 5,
        "audio": 3,
        "document": 2
      },
      "byStatus": {
        "sent": 75,
        "delivered": 70,
        "read": 65,
        "failed": 0
      }
    }
  }
}
```

#### **GET** `/api/messages/unread`
Obtener mensajes no leídos de todas las sesiones.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "unreadMessages": [
      {
        "sessionId": "nueva_sesion_wa",
        "chatId": "34612345678@s.whatsapp.net",
        "chatName": "Juan Pérez",
        "unreadCount": 3,
        "lastMessage": {
          "content": "¿Estás ahí?",
          "timestamp": "2025-10-14T06:50:00.000Z"
        }
      }
    ],
    "totalUnread": 3
  }
}
```

#### **DELETE** `/api/messages/:messageId`
Eliminar un mensaje específico.

#### **POST** `/api/messages/:messageId/retry`
Reintentar envío de mensaje fallido (máx. 3 intentos).

#### **POST** `/api/messages/:sessionId/transfer-chat`
Transferir chat(s) entre sesiones.

**Body:**
```json
{
  "fromSessionId": "string",
  "chatId": "string (optional, single chat)",
  "chatIds": ["array of chatIds (optional, multiple chats)"]
}
```

---

## 👥 Contactos

**Base Path:** `/api/contacts`
**Autenticación:** ✅ **SOLO API Key** (NO requiere JWT Token)
**Rate Limit:** 30 requests/min

**Headers requeridos:**
```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: application/json
```

### Endpoints

#### **GET** `/api/contacts/:sessionId`
Listar contactos de una sesión.

**Query Parameters:**
- `page`: number (optional, default: 1)
- `limit`: number (optional, default: 50, max: 100)
- `search`: string (optional, 1-100 chars) - Busca por nombre, verifiedName o id

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contacts": [
      {
        "id": "34612345678@s.whatsapp.net",
        "name": "Juan Pérez",
        "verifiedName": "Juan Pérez",
        "notify": "Juan",
        "imgUrl": "https://pps.whatsapp.net/v/...",
        "isUser": true,
        "isGroup": false,
        "isWAContact": true
      }
    ],
    "pagination": {
      "total": 150,
      "page": 1,
      "limit": 50,
      "pages": 3
    },
    "search": null
  }
}
```

**Nota:** Si la sesión no está conectada, devuelve contactos desde la base de datos.

#### **GET** `/api/contacts/:sessionId/search/:phoneNumber`
Buscar contacto específico por número.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contact": {
      "id": "34612345678@s.whatsapp.net",
      "name": "Juan Pérez",
      "verifiedName": "Juan Pérez",
      "notify": "Juan",
      "imgUrl": "https://pps.whatsapp.net/v/...",
      "isUser": true,
      "isGroup": false,
      "isWAContact": true
    }
  }
}
```

Si no se encuentra:
```json
{
  "success": true,
  "data": {
    "contact": null,
    "message": "Contacto no encontrado"
  }
}
```

#### **GET** `/api/contacts/:sessionId/info/:contactId`
Obtener información detallada de un contacto.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "contact": {
      "id": "34612345678@s.whatsapp.net",
      "name": "Juan Pérez",
      "verifiedName": "Juan Pérez",
      "notify": "Juan",
      "imgUrl": "https://pps.whatsapp.net/v/...",
      "isUser": true,
      "isGroup": false,
      "isWAContact": true,
      "businessProfile": {
        "description": "Empresa de tecnología",
        "website": "https://example.com",
        "email": "info@example.com"
      },
      "status": "Disponible",
      "lastSeen": "2025-10-14T06:30:00.000Z"
    }
  }
}
```

#### **GET** `/api/contacts/:sessionId/stats`
Estadísticas de contactos de una sesión.

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "stats": {
      "total": 150,
      "users": 140,
      "groups": 10,
      "wAContacts": 145,
      "withNames": 130,
      "withProfilePics": 120
    }
  }
}
```

---

## 👥 Grupos

**Base Path:** `/api/groups`
**Autenticación:** ✅ **SOLO API Key** (NO requiere JWT Token)

**Headers requeridos:**
```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: application/json
```

### Endpoints

#### **GET** `/api/groups/sessions/:sessionId`
Listar grupos de una sesión.

**Query Parameters:**
- `page`: number (optional, default: 1)
- `limit`: number (optional, default: 20, max: 100)
- `search`: string (optional)
- `isActive`: boolean (optional)

#### **POST** `/api/groups/sessions/:sessionId`
Crear nuevo grupo.

**Body:**
```json
{
  "subject": "string (required)",
  "description": "string (optional)",
  "participants": ["array of phone numbers or JIDs (optional)"]
}
```

#### **GET** `/api/groups/sessions/:sessionId/stats`
Estadísticas de grupos de una sesión.

#### **GET** `/api/groups/sessions/:sessionId/groups/:groupId`
Obtener detalles de un grupo específico.

#### **PUT** `/api/groups/sessions/:sessionId/groups/:groupId`
Actualizar información del grupo (nombre, descripción).

**Body:**
```json
{
  "subject": "string (optional)",
  "description": "string (optional)"
}
```

#### **POST** `/api/groups/sessions/:sessionId/groups/:groupId/read`
Marcar mensajes del grupo como leídos.

#### **POST** `/api/groups/sessions/:sessionId/groups/:groupId/participants`
Agregar participante al grupo.

**Body:**
```json
{
  "participants": ["array of phone numbers or JIDs"],
  "isAdmin": false
}
```

#### **DELETE** `/api/groups/sessions/:sessionId/groups/:groupId/participants`
Remover participante del grupo.

**Body:**
```json
{
  "participants": ["array of phone numbers or JIDs"]
}
```

#### **POST** `/api/groups/sessions/:sessionId/groups/:groupId/promote`
Promover participante a administrador.

**Body:**
```json
{
  "participants": ["array of phone numbers or JIDs"]
}
```

#### **POST** `/api/groups/sessions/:sessionId/groups/:groupId/invite-code`
Generar código de invitación.

**Body:**
```json
{
  "expirationHours": 24
}
```

#### **POST** `/api/groups/join-with-code`
Unirse a grupo con código de invitación.

**Body:**
```json
{
  "inviteCode": "string"
}
```

---

## 📊 Estados WhatsApp

**Base Path:** `/api/status`
**Autenticación:** ✅ **SOLO API Key** (NO requiere JWT Token)

**Headers requeridos:**
```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: application/json
```

### Endpoints

#### **GET** `/api/status/sessions/:sessionId`
Listar estados de una sesión.

**Query Parameters:**
- `page`: number (optional)
- `limit`: number (optional)

#### **GET** `/api/status/sessions/:sessionId/active`
Obtener solo estados activos.

#### **POST** `/api/status/sessions/:sessionId`
Publicar nuevo estado.

**Body:**
```json
{
  "type": "text|image|video|audio|document",
  "content": "string (para tipo text)",
  "mediaUrl": "string (requerido para media types)",
  "caption": "string (optional)"
}
```

#### **GET** `/api/status/sessions/:sessionId/stats`
Estadísticas de estados.

#### **GET** `/api/status/sessions/:sessionId/search`
Buscar estados por query.

**Query Parameters:**
- `q`: string (required)

#### **GET** `/api/status/sessions/:sessionId/statuses/:statusId`
Obtener detalles de un estado específico.

#### **POST** `/api/status/sessions/:sessionId/statuses/:statusId/view`
Marcar estado como visto.

#### **POST** `/api/status/sessions/:sessionId/statuses/:statusId/archive`
Archivar estado.

#### **POST** `/api/status/sessions/:sessionId/statuses/:statusId/unarchive`
Desarchivar estado.

#### **POST** `/api/status/sessions/:sessionId/statuses/:statusId/reactions`
Agregar reacción a un estado.

**Body:**
```json
{
  "reaction": "👍"
}
```

#### **DELETE** `/api/status/sessions/:sessionId/statuses/:statusId/reactions`
Eliminar reacción.

---

## 📎 Multimedia

**Base Path:** `/api/media`
**Autenticación:** ✅ **SOLO API Key** (NO requiere JWT Token)
**Content-Type:** `multipart/form-data` para uploads

**Headers requeridos:**
```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: multipart/form-data (para uploads)
```

### Endpoints

#### **GET** `/api/media/sessions/:sessionId`
Listar archivos multimedia de una sesión.

**Query Parameters:**
- `page`: number (optional)
- `limit`: number (optional)
- `type`: string (optional: image, video, audio, document)

#### **POST** `/api/media/sessions/:sessionId/upload`
Subir archivo multimedia.

**Form Data:**
- `file`: File (required, max 100MB)
- `type`: string (optional: image, video, audio, document)

**Respuesta:**
```json
{
  "success": true,
  "message": "Archivo subido exitosamente",
  "data": {
    "fileId": "uuid-file-id",
    "filename": "imagen.jpg",
    "originalName": "mi-imagen.jpg",
    "mimeType": "image/jpeg",
    "size": 1024000,
    "url": "https://api.inbox-hub.com/api/media/files/uuid-file-id",
    "thumbnailUrl": "https://api.inbox-hub.com/api/media/thumbnails/uuid-file-id"
  }
}
```

**Formatos soportados:**
- Imágenes: JPEG, PNG, GIF, WebP
- Videos: MP4, AVI, MOV, WebM
- Documentos: PDF, DOC, DOCX, XLS, XLSX, TXT
- Audio: MP3, WAV, OGG, MPEG

#### **GET** `/api/media/sessions/:sessionId/stats`
Estadísticas de archivos multimedia.

#### **GET** `/api/media/sessions/:sessionId/search`
Buscar archivos por query.

**Query Parameters:**
- `q`: string (required)

#### **GET** `/api/media/:mediaFileId`
Obtener detalles de un archivo multimedia.

#### **GET** `/api/media/:mediaFileId/download`
Descargar archivo multimedia.

#### **DELETE** `/api/media/:mediaFileId`
Eliminar archivo multimedia.

---

## 📝 Plantillas de Mensajes

**Base Path:** `/api/templates`
**Autenticación:** ✅ JWT Token

### Endpoints

#### **GET** `/api/templates/organizations/:organizationId`
Listar plantillas de una organización.

**Query Parameters:**
- `page`: number (optional)
- `limit`: number (optional)

#### **GET** `/api/templates/organizations/:organizationId/active`
Listar plantillas aprobadas.

#### **GET** `/api/templates/organizations/:organizationId/pending`
Listar plantillas pendientes (requiere rol admin).

#### **POST** `/api/templates/organizations/:organizationId`
Crear nueva plantilla.

**Body:**
```json
{
  "name": "string (required)",
  "content": "string (required)",
  "variables": ["array of variable names (optional)"],
  "attachments": ["array (optional)"],
  "interactiveElements": ["array (optional)"]
}
```

#### **GET** `/api/templates/organizations/:organizationId/stats`
Estadísticas de plantillas.

#### **GET** `/api/templates/:templateId`
Obtener detalles de una plantilla.

#### **PUT** `/api/templates/:templateId`
Actualizar plantilla.

#### **POST** `/api/templates/:templateId/use`
Renderizar plantilla con variables.

**Body:**
```json
{
  "variables": {
    "name": "Juan Pérez"
  }
}
```

#### **POST** `/api/templates/:templateId/approve`
Aprobar plantilla (rol admin).

#### **POST** `/api/templates/:templateId/reject`
Rechazar plantilla.

**Body:**
```json
{
  "rejectionReason": "string"
}
```

#### **DELETE** `/api/templates/:templateId`
Eliminar plantilla.

---

## 🔗 Webhooks

**Base Path:** `/api/webhooks`
**Autenticación:** ✅ JWT Token (para configuración), ❌ No requerida (para recibir webhooks)

### Endpoints Públicos

#### **GET** `/api/webhooks/test/connectivity`
Test de conectividad (para Frappe).

**Respuesta:**
```json
{
  "success": true,
  "message": "Conectividad OK",
  "timestamp": "2025-10-14T06:00:00.000Z",
  "server": "Inbox Hub WhatsApp API",
  "version": "1.0.0"
}
```

#### **POST** `/api/webhooks/test/signature`
Test de firma HMAC (para Frappe).

### Endpoints de Configuración

#### **GET** `/api/webhooks/organizations/:organizationId`
Listar webhooks de una organización.

**Query Parameters:**
- `page`: number (optional)
- `limit`: number (optional)
- `isActive`: boolean (optional)
- `isPaused`: boolean (optional)

#### **POST** `/api/webhooks/organizations/:organizationId`
Crear nuevo webhook.

**Body:**
```json
{
  "name": "string (required)",
  "url": "string (required, valid URL)",
  "events": ["array of event names (required)"],
  "headers": {
    "Authorization": "Bearer token"
  },
  "retryConfig": {
    "attempts": 3,
    "delay": 1000
  },
  "timeout": 30000,
  "secret": "string (optional)"
}
```

**Eventos soportados:**
- `message.received` - Mensaje recibido
- `message.sent` - Mensaje enviado
- `message.ack` - Confirmación de mensaje
- `conversation.created` - Nueva conversación
- `conversation.updated` - Conversación actualizada
- `contact.created` - Nuevo contacto
- `contact.updated` - Contacto actualizado
- `session.connected` - Sesión conectada
- `session.disconnected` - Sesión desconectada
- `session.qr` - Nuevo código QR generado

#### **GET** `/api/webhooks/organizations/:organizationId/stats`
Estadísticas de entregas de webhooks.

#### **GET** `/api/webhooks/organizations/:organizationId/health`
Reporte de salud de webhooks (errores, reintentos, latencia).

#### **GET** `/api/webhooks/:webhookId`
Obtener detalles de un webhook.

#### **PUT** `/api/webhooks/:webhookId`
Actualizar configuración de webhook.

#### **POST** `/api/webhooks/:webhookId/toggle`
Activar o desactivar webhook.

#### **POST** `/api/webhooks/:webhookId/pause`
Pausar/reanudar webhook.

**Body:**
```json
{
  "pauseUntil": "2025-10-15T00:00:00.000Z"
}
```

#### **POST** `/api/webhooks/:webhookId/test`
Enviar evento de prueba.

**Body:**
```json
{
  "testPayload": {
    "event": "message.received",
    "data": {...}
  }
}
```

#### **DELETE** `/api/webhooks/:webhookId`
Eliminar webhook.

### Formato de Webhooks Recibidos

Los webhooks se envían con los siguientes headers:

```http
X-Webhook-Signature: sha256={firma_hmac}
X-Webhook-Event: {tipo_de_evento}
X-Webhook-Session: {sessionId}
X-Webhook-Timestamp: {timestamp}
```

**Ejemplo de payload:**

```json
{
  "event": "message.received",
  "sessionId": "nueva_sesion_wa",
  "data": {
    "id": {
      "fromMe": false,
      "remote": "34612345678@c.us",
      "id": "3EB0250462D167CE4A3F0D",
      "_serialized": "false_34612345678@c.us_3EB0250462D167CE4A3F0D_in"
    },
    "body": "Hola, ¿cómo estás?",
    "type": "chat",
    "timestamp": 1643284800,
    "from": "34612345678@c.us",
    "to": "nueva_sesion_wa@c.us",
    "fromMe": false,
    "hasMedia": false
  },
  "timestamp": "2025-10-14T06:30:00.000Z"
}
```

**Eventos de sesión:**

```json
{
  "event": "session.connected",
  "sessionId": "nueva_sesion_wa",
  "data": {
    "phoneNumber": "34657032985",
    "timestamp": "2025-10-14T06:30:00.000Z"
  }
}
```

```json
{
  "event": "session.qr",
  "sessionId": "nueva_sesion_wa",
  "data": {
    "qrCode": "data:image/png;base64,iVBORw0KG...",
    "expiresAt": "2025-10-14T06:35:00.000Z"
  }
}
```

---

## 🏢 Organizaciones

**Base Path:** `/api/organizations`
**Autenticación:** ✅ JWT Token

### Endpoints

#### **POST** `/api/organizations`
Crear nueva organización.

**Body:**
```json
{
  "name": "string (required)",
  "description": "string (optional)",
  "plan": "string (optional, default: free)"
}
```

#### **GET** `/api/organizations/my-organizations`
Listar organizaciones del usuario actual.

#### **GET** `/api/organizations/:organizationId`
Obtener detalles de una organización.

#### **PUT** `/api/organizations/:organizationId`
Actualizar organización (rol admin u owner).

#### **DELETE** `/api/organizations/:organizationId`
Eliminar organización (solo owner).

#### **GET** `/api/organizations/:organizationId/members`
Listar miembros de la organización.

**Query Parameters:**
- `page`: number (optional)
- `limit`: number (optional)

#### **POST** `/api/organizations/:organizationId/members/invite`
Invitar usuario a la organización.

**Body:**
```json
{
  "email": "string (required)",
  "role": "member|admin"
}
```

#### **PUT** `/api/organizations/:organizationId/members/:memberId/role`
Cambiar rol de miembro.

#### **DELETE** `/api/organizations/:organizationId/members/:memberId`
Remover miembro.

#### **GET** `/api/organizations/:organizationId/stats`
Estadísticas de la organización.

---

## 📋 Auditoría

**Base Path:** `/api/audit`
**Autenticación:** ✅ JWT Token (admin role required)

### Endpoints

#### **GET** `/api/audit/my-logs`
Logs de auditoría del usuario.

**Query Parameters:**
- `page`: number (optional, default: 1)
- `limit`: number (optional, default: 50, max: 100)
- `startDate`: string (optional, ISO 8601)
- `endDate`: string (optional, ISO 8601)

#### **GET** `/api/audit/organizations/:organizationId`
Logs de auditoría de una organización.

#### **GET** `/api/audit/organizations/:organizationId/search`
Búsqueda de logs.

**Query Parameters:**
- `q`: string (required)
- `page`: number (optional)
- `limit`: number (optional)

#### **GET** `/api/audit/organizations/:organizationId/critical`
Logs marcados como críticos.

#### **GET** `/api/audit/organizations/:organizationId/recent`
Últimos eventos.

#### **GET** `/api/audit/organizations/:organizationId/stats`
Estadísticas de auditoría.

#### **GET** `/api/audit/organizations/:organizationId/top-actions`
Acciones más frecuentes.

**Query Parameters:**
- `startDate`: string (optional)
- `endDate`: string (optional)

#### **GET** `/api/audit/organizations/:organizationId/export`
Exportación de logs.

#### **GET** `/api/audit/:logId`
Obtener detalles de un log específico.

---

## 🏥 Sistema y Salud

### Endpoints

#### **GET** `/health`
Health check del sistema.

**Autenticación:** ❌ No requerida

**Respuesta:**
```json
{
  "success": true,
  "message": "API funcionando correctamente",
  "timestamp": "2025-10-14T06:00:00.000Z",
  "version": "1.0.0",
  "environment": "production"
}
```

#### **GET** `/`
Información general del API.

**Autenticación:** ❌ No requerida

**Respuesta:**
```json
{
  "success": true,
  "message": "Inbox Hub API - Backend WhatsApp con Baileys",
  "version": "1.0.0",
  "documentation": "/api/docs",
  "health": "/health",
  "endpoints": {
    "auth": "/api/auth",
    "sessions": "/api/sessions",
    "messages": "/api/messages",
    "contacts": "/api/contacts",
    "webhooks": "/api/webhooks",
    "organizations": "/api/organizations",
    "groups": "/api/groups",
    "status": "/api/status",
    "media": "/api/media",
    "templates": "/api/templates",
    "audit": "/api/audit"
  }
}
```

---

## 📊 Rate Limits

| Endpoint Category | Rate Limit | Window |
|------------------|------------|---------|
| General | 100 requests | 15 minutes |
| Authentication | 5 requests | 15 minutes |
| WhatsApp Operations | 30 requests | 1 minute |
| Message Sending | 10 messages | 1 minute |

---

## 🚨 Códigos de Error

### Códigos HTTP

- `200` - OK
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `409` - Conflict
- `422` - Validation Error
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error

### Códigos de Error Personalizados

```json
{
  "success": false,
  "error": "Mensaje de error",
  "code": "ERROR_CODE",
  "details": {
    "field": "Detalle específico del error"
  }
}
```

**Códigos comunes:**
- `VALIDATION_ERROR` - Error de validación
- `AUTHENTICATION_FAILED` - Fallo de autenticación
- `AUTHORIZATION_FAILED` - Sin permisos
- `SESSION_NOT_FOUND` - Sesión no encontrada
- `SESSION_NOT_CONNECTED` - Sesión no conectada
- `RATE_LIMIT_EXCEEDED` - Límite de requests excedido
- `WHATSAPP_ERROR` - Error de WhatsApp/Baileys
- `INTERNAL_ERROR` - Error interno del servidor
- `CONTACT_NOT_FOUND` - Contacto no encontrado
- `MESSAGE_RATE_LIMIT_EXCEEDED` - Límite de mensajes excedido

---

## 🔧 Ejemplos de Uso

### Flujo Completo: Crear Sesión y Enviar Mensaje

```bash
# NOTA: Las rutas de WhatsApp SOLO requieren API Key, NO JWT Token
# El JWT Token solo es necesario para rutas de autenticación (/api/auth)

# 1. Crear sesión (SOLO API Key)
SESSION_RESPONSE=$(curl -s -X POST https://api.inbox-hub.com/api/sessions \
  -H "X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814" \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"mi_nueva_sesion","sessionName":"Mi Sesión de Prueba"}')

SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.data.id')

# 2. Conectar sesión (SOLO API Key)
curl -X POST https://api.inbox-hub.com/api/sessions/$SESSION_ID/connect \
  -H "X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"

# 3. Obtener QR (SOLO API Key)
curl -s https://api.inbox-hub.com/api/sessions/$SESSION_ID/qr \
  -H "X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814" \
  | jq -r '.data.qrCode' > qr_code.txt

# 4. Verificar estado (repetir hasta que sea 'connected') - SOLO API Key
curl -s https://api.inbox-hub.com/api/sessions/$SESSION_ID/status \
  -H "X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814" \
  | jq '.data.status'

# 5. Enviar mensaje (SOLO API Key)
curl -X POST https://api.inbox-hub.com/api/messages/mi_nueva_sesion/send \
  -H "X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814" \
  -H "Content-Type: application/json" \
  -d '{"to":"34612345678","message":"¡Hola desde el API!"}'
```

### Obtener Chats de una Sesión

```bash
curl -X GET "https://api.inbox-hub.com/api/messages/mi_nueva_sesion/chats?page=1&limit=50" \
  -H "X-API-Key: tu_api_key"
```

### Sincronización Forzada

```bash
curl -X POST "https://api.inbox-hub.com/api/sessions/mi_nueva_sesion/sync" \
  -H "X-API-Key: tu_api_key"
```

### Reparar Conversaciones Faltantes

```bash
curl -X POST "https://api.inbox-hub.com/api/sessions/mi_nueva_sesion/repair-conversations" \
  -H "X-API-Key: tu_api_key"
```

---

## 📝 Notas Importantes

### Identificadores de Sesión

- **ID numérico (`id`)**: Se usa en rutas como `/api/sessions/:id`, `/api/groups/sessions/:id`
- **SessionId string (`sessionId`)**: Se usa en rutas como `/api/messages/:sessionId`, `/api/contacts/:sessionId`, `/api/sessions/:sessionId/status`

### Formato de Números de Teléfono

Los números deben incluir el prefijo internacional sin espacios:
- ✅ Correcto: `34612345678`
- ❌ Incorrecto: `346 12 34 56 78` o `+34 612 345 678`

### Formato de Chat IDs (JID)

- Para usuarios individuales: `{número}@s.whatsapp.net` o `{número}@c.us`
- Para grupos: `{id}@g.us`

### Paginación

Todos los endpoints que soportan paginación usan:
- `page`: número de página (>= 1, default: 1)
- `limit`: elementos por página (1-100, default varía por endpoint)

### Fechas

Formato ISO 8601: `YYYY-MM-DDTHH:mm:ss.sssZ`

Ejemplo: `2025-10-14T06:30:00.000Z`

---

## 🔒 Seguridad

### Autenticación

**IMPORTANTE:** Las rutas de WhatsApp (sessions, messages, contacts, groups, status, media) **SOLO requieren API Key**, NO JWT Token.

- **API Key**: Header `X-API-Key` requerido en todas las operaciones de WhatsApp
- **JWT Token**: Solo necesario para rutas de autenticación (`/api/auth/*`) y organizaciones (`/api/organizations/*`)
- **Refresh Token**: Usar `/api/auth/refresh-token` para renovar el access token (solo si usas rutas que requieren JWT)

### Webhooks

- Los webhooks incluyen firma HMAC en el header `X-Webhook-Signature`
- Formato: `sha256={firma_hmac}`
- Verificar siempre la firma antes de procesar el webhook

---

## 📞 Soporte

**Sistema:** Completamente funcional ✅
**Documentación:** Actualizada ✅
**API:** Todos los endpoints operativos ✅

---

*Documentación completa del servidor Baileys WhatsApp API*
*Versión 2.0.0 - Octubre 2025*
*Para uso del CRM de Grupo ATU y integradores externos*

