# 📡 Configuración de Webhooks para Mensajes en Tiempo Real

## ✅ Estado Actual

El sistema de recepción de mensajes en tiempo real ya está **completamente implementado**:

### Backend (Python)
- ✅ Endpoint de webhook: `xappiens_whatsapp.api.webhook.handle_webhook`
- ✅ Procesamiento de mensajes: `_handle_message_received()`
- ✅ Publicación de eventos realtime: `frappe.publish_realtime()`
- ✅ Creación automática de documentos: WhatsApp Message, WhatsApp Conversation

### Frontend (Vue.js)
- ✅ Socket.IO inicializado en `WhatsAppUnified.vue`
- ✅ Listeners configurados para `whatsapp_message` y `whatsapp_message_received`
- ✅ Handler `handleIncomingMessage()` para procesar mensajes
- ✅ Actualización automática de la UI en tiempo real

---

## 🔧 Pasos para Configurar el Webhook

### 1. Verificar Configuración en WhatsApp Settings

Ir a **WhatsApp Settings** y verificar:

```
✅ webhook_url: https://tu-dominio.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook
✅ webhook_secret: (tu_secret_para_validar_firmas)
```

### 2. Configurar Webhook en la Sesión Existente

Si ya tienes una sesión iniciada, necesitas configurar el webhook en Baileys/Inbox Hub.

#### Opción A: Usando el método Python (Recomendado)

```python
import frappe

# Obtener el session_id de tu sesión
session_doc = frappe.get_doc("WhatsApp Session", "NOMBRE_DE_TU_SESION")
session_id = session_doc.session_id

# Actualizar webhook
result = frappe.call(
    "xappiens_whatsapp.api.session.update_session_webhook",
    session_id=session_id
)

print(result)
```

#### Opción B: Usando la API directamente

```bash
curl -X PUT https://api.inbox-hub.com/api/sessions/{session_db_id}/webhook \
  -H "X-API-Key: {TU_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "webhookUrl": "https://tu-dominio.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
    "webhookSecret": "tu_webhook_secret"
  }'
```

**Nota:** Necesitas el `session_db_id` (número) no el `session_id` (string). Puedes obtenerlo del DocType WhatsApp Session.

### 3. Verificar que el Webhook Esté Configurado

El webhook debe estar configurado en Baileys/Inbox Hub para que envíe eventos cuando:
- Se recibe un mensaje (`message.received`)
- Se envía un mensaje (`message.sent`)
- Cambia el estado de un mensaje (`message.delivered`, `message.read`)
- Cambia el estado de la sesión (`session.connected`, `session.disconnected`)

---

## 🔍 Verificación del Sistema

### 1. Verificar Endpoint de Webhook

El endpoint debe ser accesible públicamente:
```
https://tu-dominio.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook
```

### 2. Verificar Socket.IO en el Frontend

Abrir la consola del navegador en WhatsApp Unified y verificar:
```
✅ Socket conectado, listeners activos
✅ Listeners de tiempo real registrados para: whatsapp_message_received, whatsapp_message
```

### 3. Probar Recepción de Mensajes

1. Envía un mensaje de prueba desde otro número de WhatsApp a tu sesión
2. Verifica en la consola del navegador que aparezca:
   ```
   📨 Mensaje recibido en tiempo real (webhook): {...}
   🔔 [EVENTO] whatsapp_message_received recibido: {...}
   ```
3. El mensaje debe aparecer automáticamente en la ventana de mensajes

---

## 📋 Flujo Completo de Recepción de Mensajes

```
1. Baileys recibe mensaje de WhatsApp
   ↓
2. Baileys envía webhook POST a Frappe
   URL: /api/method/xappiens_whatsapp.api.webhook.handle_webhook
   Headers: X-Webhook-Event: message.received
   ↓
3. handle_webhook() valida firma y procesa evento
   ↓
4. _handle_message_received() procesa el mensaje:
   - Crea WhatsApp Message en la BD
   - Crea/actualiza WhatsApp Conversation
   - Crea/actualiza WhatsApp Contact
   ↓
5. Publica evento realtime:
   frappe.publish_realtime("whatsapp_message", payload, user="*")
   frappe.publish_realtime("whatsapp_message_received", payload, user="*")
   ↓
6. Socket.IO en el frontend recibe el evento
   ↓
7. handleIncomingMessage() procesa el payload:
   - Agrega mensaje a currentConversation.value.messages
   - Actualiza lista de contactos
   - Actualiza contadores de no leídos
   - Scroll automático al final
   ↓
8. UI se actualiza automáticamente ✨
```

---

## 🐛 Troubleshooting

### El mensaje no aparece en tiempo real

1. **Verificar que el webhook esté configurado en Baileys:**
   - Usar `update_session_webhook()` para configurarlo
   - Verificar en los logs de Baileys que el webhook se esté enviando

2. **Verificar logs de Frappe:**
   ```bash
   tail -f logs/web.log | grep webhook
   ```

3. **Verificar Socket.IO:**
   - Abrir consola del navegador
   - Verificar que el socket esté conectado
   - Verificar que los listeners estén registrados

4. **Verificar formato del payload:**
   - El webhook debe enviar el formato esperado
   - Verificar que `phone_number` esté normalizado correctamente

### El webhook no se está recibiendo

1. **Verificar que la URL sea accesible públicamente**
2. **Verificar firewall/WAF:** Las IPs 170.83.242.18 y 170.83.242.19 deben estar permitidas
3. **Verificar logs de Baileys** para ver si hay errores al enviar el webhook

### Los mensajes aparecen duplicados

- El sistema tiene protección contra duplicados
- Verificar que `message_id` sea único en el payload
- Verificar que no se estén procesando webhooks múltiples veces

---

## 📝 Notas Importantes

1. **El webhook debe configurarse por sesión** - Cada sesión necesita su propia configuración de webhook
2. **La URL del webhook debe ser HTTPS** - Baileys requiere HTTPS para webhooks
3. **El webhook secret es opcional** pero recomendado para seguridad
4. **Los eventos se publican a todos los usuarios** (`user="*"`) para que todos vean los mensajes en tiempo real

---

## 🚀 Próximos Pasos

1. ✅ Configurar webhook en la sesión existente usando `update_session_webhook()`
2. ✅ Probar enviando un mensaje de prueba
3. ✅ Verificar que aparezca en tiempo real en la UI
4. ✅ Verificar logs si hay algún problema

