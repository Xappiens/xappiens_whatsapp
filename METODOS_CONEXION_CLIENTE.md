# 🔌 MÉTODOS DE CONEXIÓN - CLIENTE FRAPPE

## 📋 RESUMEN

Este documento explica **exactamente** cómo el cliente Frappe está consumiendo la API de Inbox Hub para:
1. ✅ Generar sesiones y códigos QR
2. ✅ Verificar el estado de las sesiones
3. ✅ Enviar mensajes
4. ❌ Problema actual: Las sesiones se desconectan inesperadamente

---

## 🔐 1. AUTENTICACIÓN

### Endpoint usado:
```
POST https://api.inbox-hub.com/api/auth/login
```

### Headers:
```json
{
  "Content-Type": "application/json"
}
```

### Body:
```json
{
  "identifier": "apiwhatsapp@grupoatu.com",
  "password": "GrupoATU2025!WhatsApp"
}
```

### Respuesta esperada:
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": { ... }
  }
}
```

### Implementación en código:
📂 **Archivo:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/base.py`
📍 **Línea:** 68-87

```python
def _authenticate(self):
    """Obtiene token JWT del servidor."""
    if self.access_token and self.token_expiry:
        if datetime.now() < self.token_expiry:
            return self.access_token

    response = requests.post(
        f"{self.base_url}/api/auth/login",
        json={
            "identifier": self.email,
            "password": self.password
        },
        timeout=30
    )

    if response.status_code == 200:
        data = response.json().get("data", {})
        self.access_token = data.get("accessToken")
        # Token válido por 1 hora
        self.token_expiry = datetime.now() + timedelta(hours=1)
        return self.access_token
```

---

## 📱 2. CREAR NUEVA SESIÓN Y OBTENER QR

### Endpoint usado:
```
POST https://api.inbox-hub.com/api/sessions
```

### Headers:
```json
{
  "Authorization": "Bearer {JWT_TOKEN}",
  "X-API-Key": "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814",
  "Content-Type": "application/json"
}
```

### Body:
```json
{
  "sessionId": "prueba2_mgri15c2_9aa6i1",
  "webhookUrl": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook_event"
}
```

### Respuesta esperada:
```json
{
  "success": true,
  "message": "Sesión creada exitosamente",
  "data": {
    "sessionId": "prueba2_mgri15c2_9aa6i1",
    "status": "qr",
    "qrCode": "data:image/png;base64,iVBORw0KG...",
    "phoneNumber": null,
    "createdAt": "2025-10-15T04:30:00.000Z"
  }
}
```

### Implementación en código:
📂 **Archivo:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/base.py`
📍 **Línea:** 194-211

```python
def create_session(self, session_id: str, webhook_url: str = None) -> Dict[str, Any]:
    """
    Crea una nueva sesión de WhatsApp.

    Args:
        session_id: ID único para la sesión
        webhook_url: URL para recibir webhooks (opcional)

    Returns:
        Dict con datos de la sesión creada (incluyendo QR code)
    """
    data = {"sessionId": session_id}
    if webhook_url:
        data["webhookUrl"] = webhook_url

    return self.post("/api/sessions", data=data)
```

**📌 NOTA IMPORTANTE:** Después de llamar a este endpoint, Frappe:
1. Guarda el `qrCode` (base64) en el DocType `WhatsApp Session`
2. Lo muestra en la interfaz web para que el usuario lo escanee
3. **NO hace polling** del QR - espera recibir el webhook cuando la sesión se conecte

---

## 🔍 3. VERIFICAR ESTADO DE LA SESIÓN

### Método 1: Listar todas las sesiones (MÉTODO USADO ACTUALMENTE)

#### Endpoint usado:
```
GET https://api.inbox-hub.com/api/sessions
```

#### Headers:
```json
{
  "Authorization": "Bearer {JWT_TOKEN}",
  "X-API-Key": "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"
}
```

#### Respuesta esperada:
```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": 123,
        "sessionId": "prueba2_mgri15c2_9aa6i1",
        "status": "connected",
        "phoneNumber": "34657032985",
        "createdAt": "2025-10-15T04:30:00.000Z",
        "updatedAt": "2025-10-15T04:31:00.000Z"
      }
    ]
  }
}
```

#### Implementación en código:
📂 **Archivo:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/base.py`
📍 **Línea:** 228-238

```python
def get_sessions(self) -> Dict[str, Any]:
    """
    Lista todas las sesiones del usuario.

    Returns:
        Dict con lista de sesiones
    """
    return self.get("/api/sessions")
```

**📌 USO EN SINCRONIZACIÓN:**

Cuando se ejecuta la sincronización (manual o automática), hacemos esto:

📂 **Archivo:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/sync.py`
📍 **Línea:** 124-158

```python
# Paso 1: Obtener estado REAL desde el servidor Baileys
sessions_response = client.get_sessions()
if sessions_response.get("success"):
    sessions = sessions_response.get("data", {}).get("sessions", [])

    # Buscar nuestra sesión específica
    session_info = None
    for s in sessions:
        if s.get("sessionId") == session.session_id:
            session_info = s
            break

    if session_info:
        # Actualizar estado en Frappe según lo que dice Baileys
        baileys_status = session_info.get("status", "").lower()
        baileys_phone = session_info.get("phoneNumber")

        # Mapeo de estados
        status_map = {
            "connected": ("Connected", True),
            "qr": ("Disconnected", False),
            "disconnected": ("Disconnected", False),
            "connecting": ("Connecting", False)
        }

        frappe_status, is_connected = status_map.get(
            baileys_status,
            ("Disconnected", False)
        )

        # Actualizar en base de datos
        frappe.db.set_value("WhatsApp Session", session.name, {
            "status": frappe_status,
            "is_connected": is_connected,
            "phone_number": baileys_phone
        }, update_modified=False)
```

---

### Método 2: Verificar estado de UNA sesión específica (NO LO USAMOS)

#### Endpoint (según documentación):
```
GET https://api.inbox-hub.com/api/sessions/:sessionId/status
```

**❌ PROBLEMA:** Este endpoint requiere el `id` numérico de la base de datos (ej: `123`), no el `sessionId` (ej: `"prueba2_mgri15c2_9aa6i1"`).

**✅ SOLUCIÓN ACTUAL:** En lugar de usar este endpoint, listamos TODAS las sesiones con `GET /api/sessions` y luego filtramos por `sessionId`.

---

## 📤 4. ENVIAR MENSAJE

### Endpoint usado:
```
POST https://api.inbox-hub.com/api/messages/:sessionId/send
```

Ejemplo:
```
POST https://api.inbox-hub.com/api/messages/prueba2_mgri15c2_9aa6i1/send
```

### Headers:
```json
{
  "Authorization": "Bearer {JWT_TOKEN}",
  "X-API-Key": "prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814",
  "Content-Type": "application/json"
}
```

### Body (intento 1 - sin formato):
```json
{
  "to": "34657032985",
  "message": "Hola! Mensaje de prueba",
  "type": "text"
}
```

**❌ RESULTADO:** Error 400 - `"Message.whatsappMessageId cannot be null, Message.from cannot be null"`

### Body (intento 2 - con formato WhatsApp):
```json
{
  "to": "34657032985@s.whatsapp.net",
  "message": "Hola! Mensaje de prueba",
  "type": "text"
}
```

**❌ RESULTADO:** Error 400 - `"Datos de entrada inválidos"`

### Implementación en código:
📂 **Archivo:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/base.py`
📍 **Línea:** 362-381

```python
def send_message(self, to: str, message: str, message_type: str = "text") -> Dict[str, Any]:
    """
    Envía un mensaje de texto.

    Args:
        to: Número de teléfono destino
        message: Contenido del mensaje
        message_type: Tipo de mensaje (default: "text")

    Returns:
        Dict con resultado del envío
    """
    data = {
        "to": to,
        "message": message,
        "type": message_type
    }

    return self.post(f"/api/messages/{self.session_id}/send", data=data, use_session_id=False)
```

---

## 🔄 5. WEBHOOKS RECIBIDOS

### URL configurada:
```
https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook_event
```

### Eventos que esperamos recibir:

#### 5.1. Sesión conectada:
```json
{
  "event": "session.connected",
  "sessionId": "prueba2_mgri15c2_9aa6i1",
  "phoneNumber": "34657032985",
  "timestamp": "2025-10-15T04:31:00.000Z"
}
```

**✅ QUÉ HACEMOS:** Actualizamos el estado en Frappe a "Connected" y `is_connected = true`

**⚠️ IMPORTANTE:** Hemos **DESHABILITADO** la sincronización automática al conectar porque causaba conflictos de conexión múltiple.

#### 5.2. Nuevo código QR:
```json
{
  "event": "session.qr",
  "sessionId": "prueba2_mgri15c2_9aa6i1",
  "qrCode": "data:image/png;base64,iVBORw0KG...",
  "timestamp": "2025-10-15T04:30:30.000Z"
}
```

**✅ QUÉ HACEMOS:** Publicamos el QR en tiempo real vía WebSocket para que el usuario lo vea sin refrescar la página.

#### 5.3. Sesión desconectada:
```json
{
  "event": "session.disconnected",
  "sessionId": "prueba2_mgri15c2_9aa6i1",
  "reason": "logout",
  "timestamp": "2025-10-15T04:45:00.000Z"
}
```

**✅ QUÉ HACEMOS:** Actualizamos el estado en Frappe a "Disconnected" y `is_connected = false`

### Implementación:
📂 **Archivo:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/webhook.py`
📍 **Líneas:** 1-524 (completo)

---

## ❌ 6. PROBLEMA ACTUAL: SESIONES SE DESCONECTAN

### 🔴 Síntomas:
1. ✅ La sesión se crea correctamente
2. ✅ El QR se genera y muestra
3. ✅ El usuario escanea el QR
4. ✅ El webhook `session.connected` llega
5. ✅ El estado cambia a "Connected"
6. ❌ **Al intentar hacer cualquier operación (sincronizar contactos, enviar mensaje), la sesión se desconecta**

### 🔍 Diagnóstico realizado:

#### Prueba 1: Script de diagnóstico paso a paso
📂 **Archivo:** `apps/xappiens_whatsapp/diagnose_sync.py`

**Resultado:**
- ✅ Autenticación: OK
- ✅ Verificar estado inicial: `connected`
- ✅ Obtener contactos (200): OK
- ❌ Verificar estado después de contactos: `disconnected`
- ❌ **CONCLUSIÓN:** La petición `GET /api/contacts/:sessionId` causa la desconexión

#### Prueba 2: Obtener chats
**Resultado:**
- Error 500: `"column Message.isDeleted does not exist"`
- ❌ **CONCLUSIÓN:** Error en base de datos del servidor Baileys

#### Prueba 3: Enviar mensaje
**Resultado:**
- Error 400: Sesión ya está desconectada
- Error de validación en el payload

### 🎯 Causa identificada (según el equipo del servidor):

> **"Este error 'conflict' en WhatsApp indica que:**
> - Múltiples conexiones - El mismo número está conectado desde otro dispositivo/aplicación
> - Sesión duplicada - Hay otra instancia intentando usar la misma sesión
> - Conflicto de estado - WhatsApp detectó una inconsistencia"

### ✅ Medidas tomadas:

1. **✅ Deshabilitamos la sincronización automática al conectar**
   - Antes: Al recibir webhook `session.connected` → disparaba sincronización en background
   - Ahora: Solo actualiza el estado, NO sincroniza automáticamente
   - Código: `apps/xappiens_whatsapp/xappiens_whatsapp/api/webhook.py` líneas 367-389

2. **✅ Agregamos rate limiting en sincronización manual**
   - 1 segundo entre operaciones grandes (contactos → chats → mensajes)
   - 0.5 segundos entre mensajes individuales
   - Código: `apps/xappiens_whatsapp/xappiens_whatsapp/api/sync.py` líneas 600-603

3. **✅ Reducimos límites de peticiones**
   - Contactos: de 1000 a 200 por petición
   - Chats: de 100 a 50 por petición
   - Mensajes: solo 10 conversaciones más recientes

4. **✅ Verificamos estado ANTES de sincronizar**
   - Siempre consultamos `GET /api/sessions` antes de hacer cualquier operación
   - Actualizamos el estado local en Frappe según el servidor
   - Si está desconectado, no intentamos sincronizar

---

## 🔧 7. PRUEBAS ACTUALES

### Script de prueba de envío:
📂 **Archivo:** `apps/xappiens_whatsapp/send_message_test.py`

**Último resultado:**
```
✅ Autenticado correctamente
✅ Sesión encontrada
❌ Estado: disconnected
⚠️  El mensaje no se puede enviar porque la sesión está desconectada
```

**Estado actual:**
- Session ID: `prueba2_mgri15c2_9aa6i1`
- Estado: `disconnected`
- Teléfono: `34657032985`

---

## ❓ 8. PREGUNTAS PARA EL EQUIPO DEL SERVIDOR

### 8.1. Sobre la desconexión al obtener contactos:
**Pregunta:** ¿Por qué `GET /api/contacts/:sessionId` causa que la sesión se desconecte inmediatamente?

**Observación:** Según nuestros logs, la sesión pasa de `connected` a `disconnected` **inmediatamente después** de esta petición, aunque el endpoint responde con 200 OK y devuelve los contactos correctamente.

### 8.2. Sobre el error de base de datos:
**Pregunta:** ¿Cuándo se corregirá el error `"column Message.isDeleted does not exist"` en el endpoint `GET /api/messages/:sessionId/chats`?

**Observación:** Este error también causa desconexión de la sesión. Devuelve 500 Internal Server Error.

### 8.3. Sobre el envío de mensajes:
**Pregunta:** ¿Cuál es el formato correcto del campo `to` para enviar mensajes?

**Hemos probado:**
- ❌ `"34657032985"` → Error: "Message.whatsappMessageId cannot be null, Message.from cannot be null"
- ❌ `"34657032985@s.whatsapp.net"` → Error: "Datos de entrada inválidos"

**Documentación dice:**
```json
{
  "to": "string (valid mobile phone)",
  "message": "string (1-4096 chars)",
  "type": "string (optional, default: text)"
}
```

Pero parece que faltan campos requeridos que no están documentados.

### 8.4. Sobre múltiples conexiones:
**Pregunta:** ¿Cómo podemos evitar el "conflict" de múltiples conexiones si solo estamos haciendo UNA petición a la vez?

**Observación:**
- Ya deshabilitamos la sincronización automática
- Solo permitimos sincronización manual vía botón
- Verificamos el estado antes de cada operación
- Aun así, la sesión se desconecta al hacer la primera petición después de conectar

---

## 📝 9. LOGS Y EVIDENCIAS

### 9.1. Log completo de diagnóstico:
Ver archivo: `apps/xappiens_whatsapp/RESULTADOS_PRUEBA_API.md`

### 9.2. Código fuente completo:
- **Cliente API:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/base.py`
- **Sincronización:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/sync.py`
- **Webhooks:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/webhook.py`
- **Scripts de prueba:**
  - `apps/xappiens_whatsapp/send_message_test.py`
  - `apps/xappiens_whatsapp/check_session_status.py`
  - `apps/xappiens_whatsapp/diagnose_sync.py`

---

## 📞 CONTACTO

**Cliente:** Frappe CRM - Grupo ATU
**Desarrollador:** AI Assistant (vía Cursor)
**Credenciales API:**
- Email: `apiwhatsapp@grupoatu.com`
- API Key: `prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814`
- Webhook: `https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook_event`

---

**📅 Fecha:** 15 de Octubre, 2025
**🔖 Versión:** 1.0

