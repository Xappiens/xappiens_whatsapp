# 🔥 Sincronización Automática al Conectar WhatsApp

## 📱 **¿Qué sucede cuando conectas una sesión?**

### **Paso 1: Usuario Escanea QR**
```
Usuario abre WhatsApp Session en el CRM
    ↓
Escanea el código QR con su teléfono
    ↓
WhatsApp se conecta exitosamente
```

### **Paso 2: Webhook Automático** 🔔
```
Baileys/Inbox Hub detecta la conexión
    ↓
Envía webhook: session.connected
    ↓
POST https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook
```

### **Paso 3: Actualización de Estado** ✅
```
Webhook handler recibe el evento
    ↓
Actualiza WhatsApp Session:
  - status = "Connected"
  - is_connected = 1
  - phone_number = "34657032985"
```

### **Paso 4: 🚀 SINCRONIZACIÓN AUTOMÁTICA EN BACKGROUND**
```
Se detecta que la sesión está "Connected"
    ↓
Se dispara automáticamente:
frappe.enqueue(
    "xappiens_whatsapp.api.sync.sync_session_complete",
    session_name=session
)
    ↓
Se ejecuta en cola "default" con timeout de 10 minutos
```

### **Paso 5: Importación Masiva de Datos** 📥
```
┌─────────────────────────────────────┐
│  SINCRONIZACIÓN EN BACKGROUND       │
├─────────────────────────────────────┤
│                                     │
│  1️⃣ Contactos (hasta 1000)         │
│     GET /api/contacts/{sessionId}   │
│     → Crear/actualizar en Frappe    │
│     → Descargar avatares           │
│                                     │
│  2️⃣ Chats (hasta 100)               │
│     GET /api/messages/{sessionId}/chats │
│     → Crear conversaciones          │
│     → Vincular con contactos        │
│                                     │
│  3️⃣ Mensajes (50 por chat, 20 chats)│
│     GET /api/messages/{sessionId}/{chatId} │
│     → Crear mensajes históricos     │
│     → Actualizar último mensaje     │
│                                     │
│  4️⃣ Estadísticas                    │
│     → total_contacts                │
│     → total_conversations           │
│     → total_messages                │
│                                     │
└─────────────────────────────────────┘
```

### **Paso 6: Usuario Ve Sus Datos** 👀
```
Sincronización completada
    ↓
Usuario refresca la página (o se actualiza automáticamente)
    ↓
Ve:
  ✅ Todos sus contactos importados
  ✅ Todas sus conversaciones activas
  ✅ Mensajes recientes de cada conversación
  ✅ Estadísticas actualizadas
    ↓
¡Listo para empezar a trabajar! 🎉
```

---

## ⏱️ **TIEMPOS ESTIMADOS**

| Cantidad de Datos | Tiempo Aproximado |
|------------------|-------------------|
| 50 contactos, 10 chats | 10-15 segundos |
| 200 contactos, 30 chats | 30-45 segundos |
| 500 contactos, 50 chats | 1-2 minutos |
| 1000 contactos, 100 chats | 2-4 minutos |

**Nota:** La sincronización se ejecuta en background, el usuario no tiene que esperar.

---

## 🔄 **SINCRONIZACIONES POSTERIORES**

### **Mensajes Nuevos (Tiempo Real)** ⚡
```
Llega mensaje nuevo
    ↓
Webhook: message.received
    ↓
Se crea automáticamente en Frappe
    ↓
Usuario lo ve inmediatamente (sin sincronizar manualmente)
```

### **Sincronización Manual (Opcional)** 🔄
```javascript
// El usuario puede disparar sincronización manual cuando quiera
frappe.call({
    method: 'xappiens_whatsapp.api.sync.sync_session_complete',
    args: { session_name: frm.doc.name },
    callback: function(r) {
        console.log('Sincronización completada:', r.message);
    }
});
```

### **Sincronización Programada (Opcional)** ⏰
```python
# Puedes configurar un scheduled job en hooks.py
scheduler_events = {
    "hourly": [
        "xappiens_whatsapp.api.sync.auto_sync_all_sessions"
    ]
}

# Este job sincroniza todas las sesiones activas cada hora
```

---

## 📊 **MONITOREO DE SINCRONIZACIÓN**

### **Ver Estado en Tiempo Real:**
```python
import frappe

# En la consola de Frappe
session = frappe.get_doc("WhatsApp Session", "TU_SESION")

print(f"""
📊 ESTADO DE SINCRONIZACIÓN
═══════════════════════════
Sesión: {session.session_name}
Estado: {session.status}
Conectada: {"Sí" if session.is_connected else "No"}

📱 DATOS SINCRONIZADOS
═══════════════════════════
Contactos: {session.total_contacts or 0}
Conversaciones: {session.total_conversations or 0}
Mensajes: {session.total_messages_sent or 0}

⏰ ÚLTIMA SINCRONIZACIÓN
═══════════════════════════
{session.last_sync or "Nunca"}
""")
```

### **Ver Logs de Sincronización:**
```bash
# Logs del job en background
cd /home/frappe/frappe-bench
tail -f logs/frappe.log | grep "sync_session_complete"

# Logs de webhooks
tail -f logs/frappe.log | grep "webhook"

# Logs de errores
tail -f logs/web.error.log
```

---

## 🛡️ **MANEJO DE ERRORES**

### **¿Qué pasa si falla la sincronización automática?**

1. **Se registra el error en logs**
   ```
   Error en sincronización completa: [detalle del error]
   ```

2. **La sesión permanece conectada**
   - El usuario puede seguir usando WhatsApp
   - Los mensajes nuevos seguirán llegando vía webhook

3. **El usuario puede reintentar manualmente**
   ```javascript
   // Botón "Sincronizar Ahora" en la UI
   frappe.call({
       method: 'xappiens_whatsapp.api.sync.sync_session_complete',
       args: { session_name: frm.doc.name }
   });
   ```

---

## ✅ **VENTAJAS DE LA SINCRONIZACIÓN AUTOMÁTICA**

| Ventaja | Descripción |
|---------|-------------|
| 🚀 **Inmediata** | No hay que esperar ni hacer nada manualmente |
| 🎯 **Completa** | Importa contactos, chats y mensajes de una vez |
| 💪 **En Background** | No bloquea al usuario |
| 🔄 **Incremental** | Solo actualiza lo que cambió |
| 📊 **Estadísticas** | Actualiza contadores automáticamente |
| 🔔 **Notificaciones** | Publica eventos en tiempo real |

---

## 🎬 **EJEMPLO COMPLETO: PRIMERA CONEXIÓN**

```
🕐 10:00:00 - Usuario abre "Nueva Sesión" en el CRM
🕐 10:00:05 - Usuario escanea QR con su teléfono
🕐 10:00:10 - WhatsApp se conecta ✅

═════════════════════════════════════════════════════

🕐 10:00:11 - Webhook recibido: session.connected
🕐 10:00:11 - Estado actualizado: Connected
🕐 10:00:11 - 🔥 Sincronización automática iniciada

═════════════════════════════════════════════════════

🕐 10:00:15 - Importando contactos... (327 contactos)
🕐 10:00:45 - ✅ 327 contactos creados

🕐 10:00:46 - Importando chats... (45 conversaciones)
🕐 10:01:05 - ✅ 45 conversaciones creadas

🕐 10:01:06 - Importando mensajes... (20 chats × 50 mensajes)
🕐 10:02:30 - ✅ 985 mensajes importados

🕐 10:02:31 - Actualizando estadísticas...
🕐 10:02:32 - ✅ Sincronización completada

═════════════════════════════════════════════════════

🕐 10:02:33 - Usuario refresca → Ve todos sus datos ✅

Total: 2 minutos 33 segundos desde la conexión
```

---

## 📞 **PREGUNTAS FRECUENTES**

### **¿Puedo desactivar la sincronización automática?**
Sí, puedes comentar las líneas en `webhook.py`:
```python
# if frappe_status == "Connected":
#     frappe.enqueue("xappiens_whatsapp.api.sync.sync_session_complete", ...)
```

### **¿Se sincronizará cada vez que reconecte?**
Sí, cada vez que una sesión pase de cualquier estado a "Connected", se dispara la sincronización.

### **¿Qué pasa con los mensajes mientras se sincroniza?**
Los mensajes nuevos seguirán llegando vía webhook en tiempo real, independientemente de la sincronización en background.

### **¿Puedo cambiar los límites de sincronización?**
Sí, en `sync.py` puedes modificar:
- `limit=1000` para contactos
- `limit=100` para chats
- `limit=50` para mensajes por chat
- `limit=20` para cantidad de chats a sincronizar

---

*Documento actualizado el 15 de Octubre de 2025*
*Sincronización automática implementada en xappiens_whatsapp*

