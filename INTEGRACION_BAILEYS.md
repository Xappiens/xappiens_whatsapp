# 🔗 Integración WhatsApp con Baileys/Inbox Hub

**Fecha:** 15 de Octubre de 2025
**App:** xappiens_whatsapp
**Sistema:** Baileys/Inbox Hub API

---

## 📋 **RESUMEN**

Se ha actualizado completamente la app `xappiens_whatsapp` para conectarse con el nuevo sistema de WhatsApp basado en Baileys a través de Inbox Hub API.

### ✅ **Cambios Implementados:**

1. **✅ base.py** - Cliente API con autenticación JWT + API Key
2. **✅ sync.py** - Sincronización completa de contactos, chats y mensajes
3. **✅ webhook.py** - Sistema de webhooks para mensajes en tiempo real
4. **✅ Métodos específicos** - Endpoints para todas las operaciones de Baileys
5. **✅ Sincronización automática** - Al conectar una sesión se sincronizan automáticamente todos los datos

---

## 🔥 **CARACTERÍSTICAS PRINCIPALES**

### **1. Sincronización Automática al Conectar**
Cuando una sesión de WhatsApp se conecta exitosamente:
- ✅ Se dispara automáticamente la sincronización completa en background
- ✅ Se importan todos los contactos
- ✅ Se importan todos los chats/conversaciones
- ✅ Se importan los mensajes recientes (últimos 50 por chat, 20 chats)
- ✅ El usuario puede empezar a trabajar inmediatamente

### **2. Webhooks en Tiempo Real**
- ✅ Mensajes entrantes se crean automáticamente
- ✅ Estados de mensajes se actualizan en tiempo real
- ✅ Cambios en sesión se reflejan instantáneamente
- ✅ La UI se actualiza sin necesidad de refrescar

### **3. API Completa de Baileys**
- ✅ Envío de mensajes
- ✅ Obtención de contactos con búsqueda
- ✅ Gestión de chats/conversaciones
- ✅ Obtención de mensajes con paginación
- ✅ Marcar mensajes como leídos

---

## 🔑 **CONFIGURACIÓN INICIAL**

### **1. Configurar WhatsApp Settings**

Navega a: **WhatsApp Settings** (DocType Single)

Configura los siguientes campos:

```
✅ Enabled: Marcado
✅ API Base URL: https://api.inbox-hub.com
✅ API Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
✅ API Email: apiwhatsapp@grupoatu.com
✅ API Password: GrupoATU2025!WhatsApp
✅ API Timeout: 30 (segundos)
✅ API Retry Attempts: 3
✅ Webhook Secret: (tu_secret_para_validar_webhooks)
```

### **2. Configurar Webhook en Inbox Hub**

#### **A. URL del Webhook:**
```
https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook
```

#### **B. Eventos a Suscribir:**
- `message.received` - Mensaje recibido
- `message.sent` - Mensaje enviado
- `message.delivered` - Mensaje entregado
- `message.read` - Mensaje leído
- `message.failed` - Mensaje fallido
- `session.connected` - Sesión conectada
- `session.disconnected` - Sesión desconectada
- `session.qr` - Nuevo código QR
- `contact.updated` - Contacto actualizado
- `chat.archived` - Chat archivado
- `chat.unarchived` - Chat desarchivado

#### **C. Configurar en Inbox Hub:**

```bash
# Opción 1: Usando curl
curl -X POST https://api.inbox-hub.com/api/webhooks \
  -H "Authorization: Bearer {JWT_TOKEN}" \
  -H "X-API-Key: {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CRM Grupo ATU Webhook",
    "url": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
    "method": "POST",
    "events": [
      "message.received",
      "message.sent",
      "message.delivered",
      "message.read",
      "session.connected",
      "session.disconnected",
      "session.qr"
    ],
    "secret": "tu_webhook_secret_aqui"
  }'
```

```python
# Opción 2: Usando Python
import frappe
from xappiens_whatsapp.api.base import WhatsAppAPIClient

client = WhatsAppAPIClient()

# Configurar webhook
response = client.post(
    "/api/webhooks",
    data={
        "name": "CRM Grupo ATU Webhook",
        "url": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
        "method": "POST",
        "events": [
            "message.received",
            "message.sent",
            "message.delivered",
            "message.read",
            "session.connected",
            "session.disconnected",
            "session.qr"
        ],
        "secret": frappe.get_single("WhatsApp Settings").get_password("webhook_secret")
    },
    use_session_id=False
)

print(response)
```

---

## 🚀 **USO DE LA INTEGRACIÓN**

### **1. Sincronización Completa de Sesión**

#### **Desde Python:**
```python
import frappe

# Sincronizar sesión específica
result = frappe.call(
    "xappiens_whatsapp.api.sync.sync_session_complete",
    session_name="TU_SESION_WHATSAPP"
)

print(result)
# {
#     "success": True,
#     "session": "nueva_sesion_wa",
#     "timestamp": "2025-10-15 10:30:00",
#     "contacts": {"processed": 150, "created": 100, "updated": 50, "errors": 0},
#     "chats": {"processed": 25, "created": 15, "updated": 10, "errors": 0},
#     "messages": {"processed": 500, "created": 400, "updated": 100, "errors": 0}
# }
```

#### **Desde la Consola de Frappe:**
```bash
cd /home/frappe/frappe-bench
bench --site crm.grupoatu.com console

>>> import frappe
>>> result = frappe.call("xappiens_whatsapp.api.sync.sync_session_complete", session_name="TU_SESION_WHATSAPP")
>>> print(result)
```

#### **Desde la UI del CRM:**
```javascript
// Agregar un botón en el DocType WhatsApp Session
frappe.call({
    method: 'xappiens_whatsapp.api.sync.sync_session_complete',
    args: {
        session_name: frm.doc.name
    },
    freeze: true,
    freeze_message: 'Sincronizando...',
    callback: function(r) {
        if (r.message && r.message.success) {
            frappe.show_alert({
                message: 'Sincronización completada',
                indicator: 'green'
            });
            console.log(r.message);
        } else {
            frappe.show_alert({
                message: 'Error en sincronización',
                indicator: 'red'
            });
        }
    }
});
```

### **2. Enviar Mensajes**

#### **Desde Python:**
```python
from xappiens_whatsapp.api.base import WhatsAppAPIClient

# Crear cliente
client = WhatsAppAPIClient(session_id="nueva_sesion_wa")

# Enviar mensaje
response = client.send_message(
    to="34612345678",
    message="¡Hola! Este es un mensaje de prueba desde el CRM"
)

print(response)
# {
#     "success": True,
#     "message": "Mensaje enviado exitosamente",
#     "data": {
#         "messageId": "3EB0C767D26A1B2E5F8A",
#         "to": "34612345678",
#         "status": "sent",
#         "timestamp": "2025-10-15T10:45:00.000Z"
#     }
# }
```

### **3. Obtener Contactos**

```python
client = WhatsAppAPIClient(session_id="nueva_sesion_wa")

# Obtener contactos
response = client.get_session_contacts(page=1, limit=100, search="Juan")

print(response)
# {
#     "success": True,
#     "data": {
#         "contacts": [
#             {
#                 "id": "34612345678@s.whatsapp.net",
#                 "name": "Juan Pérez",
#                 "phone": "34612345678",
#                 "isUser": True,
#                 "isGroup": False
#             }
#         ],
#         "total": 150,
#         "page": 1
#     }
# }
```

### **4. Obtener Chats/Conversaciones**

```python
client = WhatsAppAPIClient(session_id="nueva_sesion_wa")

# Obtener chats
response = client.get_session_chats(page=1, limit=20)

print(response)
# {
#     "success": True,
#     "data": {
#         "chats": [
#             {
#                 "chatId": "34612345678@s.whatsapp.net",
#                 "name": "Juan Pérez",
#                 "lastMessage": {
#                     "content": "Hola! ¿Cómo estás?",
#                     "timestamp": "2025-10-15T10:30:00.000Z",
#                     "fromMe": False
#                 },
#                 "unreadCount": 3,
#                 "isGroup": False
#             }
#         ]
#     }
# }
```

### **5. Obtener Mensajes de un Chat**

```python
client = WhatsAppAPIClient(session_id="nueva_sesion_wa")

# Obtener mensajes
response = client.get_chat_messages(
    chat_id="34612345678@s.whatsapp.net",
    page=1,
    limit=50
)

print(response)
```

---

## ⚙️ **MÉTODOS DISPONIBLES**

### **WhatsAppAPIClient (base.py)**

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `get_sessions()` | Listar sesiones | `page`, `limit`, `status` |
| `get_session_status()` | Estado de sesión | `session_db_id` |
| `get_session_contacts()` | Contactos de sesión | `page`, `limit`, `search` |
| `get_session_chats()` | Chats de sesión | `page`, `limit` |
| `get_chat_messages()` | Mensajes de chat | `chat_id`, `page`, `limit` |
| `send_message()` | Enviar mensaje | `to`, `message`, `type` |
| `mark_chat_as_read()` | Marcar como leído | `chat_id` |

### **Sincronización (sync.py)**

| Método | Descripción | Parámetros |
|--------|-------------|------------|
| `sync_session_complete()` | Sincronización completa | `session_name` |
| `_sync_contacts_baileys()` | Sincronizar contactos | `client`, `session` |
| `_sync_chats_baileys()` | Sincronizar chats | `client`, `session` |
| `_sync_messages_baileys()` | Sincronizar mensajes | `client`, `session` |

### **Webhooks (webhook.py)**

| Evento | Handler | Descripción |
|--------|---------|-------------|
| `message.received` | `_handle_message_received()` | Mensaje entrante |
| `message.sent` | `_handle_message_sent()` | Confirmación de envío |
| `message.delivered` | `_handle_message_status()` | Mensaje entregado |
| `message.read` | `_handle_message_status()` | Mensaje leído |
| `session.connected` | `_handle_session_status()` | Sesión conectada |
| `session.disconnected` | `_handle_session_status()` | Sesión desconectada |
| `session.qr` | `_handle_session_qr()` | Nuevo QR disponible |

---

## 🔄 **FLUJO DE SINCRONIZACIÓN**

### **🔥 SINCRONIZACIÓN AUTOMÁTICA AL CONECTAR**

```
1. Sesión se conecta en Baileys
   ↓
2. Inbox Hub envía webhook: session.connected
   ↓
3. Webhook handler actualiza estado de sesión en Frappe
   ↓
4. Se detecta que el estado es "Connected"
   ↓
5. 🚀 Se dispara automáticamente sync_session_complete() en background
   ↓
6. Se sincronizan contactos, chats y mensajes
   ↓
7. Usuario ve sus datos automáticamente ✅
```

### **📋 Sincronización Manual**

```
1. Usuario activa sincronización manualmente
   ↓
2. sync_session_complete() se ejecuta
   ↓
3. Se obtienen contactos desde Baileys → Se crean/actualizan en Frappe
   ↓
4. Se obtienen chats desde Baileys → Se crean/actualizan conversaciones
   ↓
5. Se obtienen mensajes de cada chat → Se crean/actualizan mensajes
   ↓
6. Se actualizan estadísticas de la sesión
   ↓
7. Sincronización completada ✅
```

---

## 📡 **FLUJO DE WEBHOOKS**

```
1. Evento ocurre en Baileys (ej: mensaje recibido)
   ↓
2. Inbox Hub envía webhook a: /api/method/xappiens_whatsapp.api.webhook.handle_webhook
   ↓
3. Se verifica la firma HMAC del webhook (seguridad)
   ↓
4. Se enruta al handler apropiado según el tipo de evento
   ↓
5. Se procesa el evento:
   - Mensaje recibido → Crear en WhatsApp Message
   - Estado de sesión → Actualizar WhatsApp Session
   - etc.
   ↓
6. Se publican eventos en tiempo real (frappe.publish_realtime)
   ↓
7. La UI se actualiza automáticamente
```

---

## 🔧 **COMANDOS ÚTILES**

### **Rebuild de la App:**
```bash
cd /home/frappe/frappe-bench
bench build --app xappiens_whatsapp
bench restart
```

### **Recargar Doctypes:**
```bash
bench --site crm.grupoatu.com reload-doctype "WhatsApp Settings"
bench --site crm.grupoatu.com reload-doctype "WhatsApp Session"
bench --site crm.grupoatu.com reload-doctype "WhatsApp Contact"
bench --site crm.grupoatu.com reload-doctype "WhatsApp Conversation"
bench --site crm.grupoatu.com reload-doctype "WhatsApp Message"
```

### **Limpiar Caché:**
```bash
bench --site crm.grupoatu.com clear-cache
```

### **Ver Logs:**
```bash
# Logs del servidor
tail -f /home/frappe/frappe-bench/logs/web.error.log

# Logs de Frappe
tail -f /home/frappe/frappe-bench/logs/frappe.log
```

---

## 🐛 **TROUBLESHOOTING**

### **Error: "Authentication failed"**
- Verificar credenciales en WhatsApp Settings
- Comprobar que `api_email` y `api_password` son correctos
- Verificar que `api_key` es válido

### **Error: "Session not connected"**
- Verificar que la sesión está conectada en Inbox Hub
- Ejecutar: `bench --site crm.grupoatu.com console`
  ```python
  from xappiens_whatsapp.api.base import WhatsAppAPIClient
  client = WhatsAppAPIClient("nueva_sesion_wa")
  status = client.get_session_status(2)  # 2 = DB ID de la sesión
  print(status)
  ```

### **Error: "Webhook signature verification failed"**
- Verificar que `webhook_secret` en WhatsApp Settings coincide con el configurado en Inbox Hub
- Si estás en desarrollo, puedes temporalmente desactivar la verificación

### **Mensajes no llegan en tiempo real**
- Verificar que el webhook está configurado correctamente en Inbox Hub
- Comprobar que la URL del webhook es accesible desde internet
- Ver logs de Frappe para errores del webhook

---

## 📊 **MONITOREO**

### **Ver Estado de Sincronización:**
```python
import frappe

session = frappe.get_doc("WhatsApp Session", "TU_SESION")

print(f"Contactos: {session.total_contacts}")
print(f"Conversaciones: {session.total_conversations}")
print(f"Mensajes: {session.total_messages_sent}")
print(f"Última sincronización: {session.last_sync}")
```

### **Ver Mensajes Recientes:**
```python
messages = frappe.get_all(
    "WhatsApp Message",
    filters={"session": "TU_SESION"},
    fields=["name", "content", "direction", "timestamp", "status"],
    order_by="timestamp desc",
    limit=10
)

for msg in messages:
    print(f"{msg.timestamp}: [{msg.direction}] {msg.content[:50]}... ({msg.status})")
```

---

## 📞 **SOPORTE**

### **Documentación Relacionada:**
- `DOC_COMPLETA_ENDPOINTS.md` - Endpoints completos de Inbox Hub
- `GUIA_CREACION_SESIONES.md` - Guía para crear sesiones
- `EJEMPLOS_INTEGRACION_CRM.md` - Ejemplos de casos de uso
- `CREDENCIALES_CRM_GRUPOATU.md` - Credenciales de acceso

### **Archivos Clave:**
- `/apps/xappiens_whatsapp/xappiens_whatsapp/api/base.py` - Cliente API
- `/apps/xappiens_whatsapp/xappiens_whatsapp/api/sync.py` - Sincronización
- `/apps/xappiens_whatsapp/xappiens_whatsapp/api/webhook.py` - Webhooks

---

## ✅ **CHECKLIST DE INTEGRACIÓN**

- [ ] WhatsApp Settings configurado con credenciales correctas
- [ ] Sesión de WhatsApp creada y conectada
- [ ] Webhook configurado en Inbox Hub
- [ ] Primera sincronización ejecutada exitosamente
- [ ] Mensajes de prueba enviados y recibidos
- [ ] Webhooks funcionando (mensajes llegan en tiempo real)
- [ ] UI actualizada para mostrar datos sincronizados

---

*Documento actualizado el 15 de Octubre de 2025*
*Integración completa con Baileys/Inbox Hub API*

