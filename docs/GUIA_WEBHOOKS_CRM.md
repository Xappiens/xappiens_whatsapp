# 🔗 Guía Completa de Webhooks - Integración CRM en Tiempo Real

**Fecha:** Octubre 2025
**Propósito:** Guía práctica para implementar recepción de mensajes WhatsApp en tiempo real via webhooks
**Para:** Integrador del CRM

---

## 🎯 **RESUMEN EJECUTIVO**

Esta guía te muestra **exactamente cómo** implementar la recepción de mensajes WhatsApp en tiempo real en tu CRM usando webhooks. Después de leer esta guía podrás:

- ✅ Configurar webhooks para recibir mensajes
- ✅ Validar la firma de seguridad de los webhooks
- ✅ Procesar mensajes entrantes en tiempo real
- ✅ Manejar todos los tipos de eventos de WhatsApp
- ✅ Implementar reintentos y manejo de errores

---

## 📋 **DOCUMENTOS NECESARIOS PARA EL INTEGRADOR**

Para completar la integración de WhatsApp con webhooks, el integrador necesita estos documentos **en este orden**:

### **1. Documentación Principal (OBLIGATORIO)**
- **`DOCUMENTACION_COMPLETA_BAILEYS.md`** - Documentación técnica completa de todos los endpoints
  - Sección: "Webhooks" (líneas 1088-1250)
  - Sección: "Autenticación" (líneas 27-216)
  - Sección: "Mensajes" (líneas 451-713)

### **2. Guía de Integración (OBLIGATORIO)**
- **`INTEGRACION_EXTERNA_CRM.md`** - Guía completa de integración con ejemplos de código
  - Sección: "Sistema de Webhooks" (líneas 200-400)
  - Sección: "Autenticación Permanente" (líneas 36-150)

### **3. Credenciales (OBLIGATORIO)**
- **`CREDENCIALES_CRM_GRUPOATU.md`** - Credenciales de acceso y API Key

### **4. Guía de Sesiones (RECOMENDADO)**
- **`GUIA_CREACION_SESIONES_CRM.md`** - Cómo crear y gestionar sesiones WhatsApp

### **5. Ejemplos Prácticos (ÚTIL)**
- **`EJEMPLOS_INTEGRACION_CRM.md`** - Casos de uso con código completo

---

## 🚀 **IMPLEMENTACIÓN PASO A PASO**

### **PASO 1: Configurar Webhook en la Sesión**

Al crear una sesión WhatsApp, configura el webhook URL:

**IMPORTANTE:** Las rutas de WhatsApp SOLO requieren API Key, NO JWT Token.

**API Key a usar:**
```
prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
```

```bash
POST https://api.inbox-hub.com/api/sessions
Headers:
  X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
  Content-Type: application/json

Body:
{
  "sessionId": "mi_sesion_crm",
  "sessionName": "Sesión CRM",
  "webhookUrl": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
  "webhookSecret": "mi_secreto_webhook_seguro",
  "webhookEvents": [
    "message.received",
    "message.sent",
    "message.ack",
    "session.connected",
    "session.disconnected",
    "session.qr"
  ]
}
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "id": 29,
    "sessionId": "mi_sesion_crm",
    "webhookUrl": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
    "status": "pending"
  }
}
```

### **PASO 2: Implementar Endpoint Receptor de Webhooks**

Crea un endpoint en tu CRM que reciba los webhooks:

#### **Python (Frappe Framework)**

```python
import frappe
import hmac
import hashlib
import json
from frappe import _

@frappe.whitelist(allow_guest=True, csrf_token=False, methods=['POST'])
def handle_webhook():
    """
    Endpoint para recibir webhooks de Inbox Hub
    URL: /api/method/xappiens_whatsapp.api.webhook.handle_webhook
    """

    # 1. Obtener headers
    headers = frappe.request.headers
    signature = headers.get('X-Webhook-Signature', '')
    event_type = headers.get('X-Webhook-Event', '')
    session_id = headers.get('X-Webhook-Session', '')
    timestamp = headers.get('X-Webhook-Timestamp', '')

    # 2. Obtener payload
    payload = frappe.request.get_data(as_text=True)
    body = json.loads(payload) if payload else {}

    # 3. Validar firma HMAC
    webhook_secret = frappe.conf.get('inbox_hub_webhook_secret') or 'mi_secreto_webhook_seguro'

    if not verify_webhook_signature(payload, signature, webhook_secret):
        frappe.log_error(f"Firma inválida: {signature}", "Webhook Security")
        return {"success": False, "error": "Invalid signature"}

    # 4. Procesar evento según tipo
    try:
        event = body.get('event')
        data = body.get('data', {})
        session_id = body.get('sessionId')

        if event == 'message.received':
            handle_message_received(session_id, data)
        elif event == 'message.sent':
            handle_message_sent(session_id, data)
        elif event == 'message.ack':
            handle_message_ack(session_id, data)
        elif event == 'session.connected':
            handle_session_connected(session_id, data)
        elif event == 'session.disconnected':
            handle_session_disconnected(session_id, data)
        elif event == 'session.qr':
            handle_session_qr(session_id, data)
        else:
            frappe.log_error(f"Evento no manejado: {event}", "Webhook Handler")

        return {"success": True, "received": True}

    except Exception as e:
        frappe.log_error(f"Error procesando webhook: {str(e)}", "Webhook Handler")
        return {"success": False, "error": str(e)}


def verify_webhook_signature(payload, signature, secret):
    """
    Verifica la firma HMAC del webhook
    """
    if not signature or not secret:
        return False

    # Remover prefijo 'sha256=' si existe
    if signature.startswith('sha256='):
        signature = signature[7:]

    # Calcular firma esperada
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Comparar de forma segura
    return hmac.compare_digest(signature, expected_signature)


def handle_message_received(session_id, data):
    """
    Procesar mensaje recibido
    """
    message_id = data.get('id', {}).get('_serialized', '')
    from_number = data.get('from', '')
    body = data.get('body', '')
    timestamp = data.get('timestamp', 0)
    has_media = data.get('hasMedia', False)

    # Buscar o crear contacto
    contact = frappe.get_doc({
        "doctype": "WhatsApp Contact",
        "whatsapp_id": from_number,
        "session_id": session_id
    })

    if not frappe.db.exists("WhatsApp Contact", {"whatsapp_id": from_number}):
        contact.insert()

    # Crear mensaje
    message = frappe.get_doc({
        "doctype": "WhatsApp Message",
        "session_id": session_id,
        "contact": contact.name,
        "from_me": False,
        "message_id": message_id,
        "body": body,
        "timestamp": timestamp,
        "has_media": has_media,
        "status": "received"
    })
    message.insert()

    # Notificar a usuarios conectados vía WebSocket si es necesario
    frappe.publish_realtime(
        'whatsapp_message_received',
        {
            'session_id': session_id,
            'contact': from_number,
            'message': body
        }
    )

    frappe.logger().info(f"Mensaje recibido de {from_number}: {body}")


def handle_message_sent(session_id, data):
    """
    Procesar mensaje enviado (confirmación)
    """
    message_id = data.get('id', {}).get('_serialized', '')

    # Actualizar estado del mensaje en BD
    frappe.db.set_value(
        "WhatsApp Message",
        {"message_id": message_id},
        "status",
        "sent"
    )

    frappe.db.commit()


def handle_message_ack(session_id, data):
    """
    Procesar confirmación de mensaje (leído/entregado)
    """
    message_id = data.get('messageId', '')
    ack = data.get('ack', 0)  # 0=pending, 1=server, 2=delivered, 3=read

    status_map = {
        0: "pending",
        1: "server",
        2: "delivered",
        3: "read"
    }

    status = status_map.get(ack, "pending")

    frappe.db.set_value(
        "WhatsApp Message",
        {"message_id": message_id},
        "status",
        status
    )

    frappe.db.commit()


def handle_session_connected(session_id, data):
    """
    Procesar conexión de sesión
    """
    phone_number = data.get('phoneNumber', '')

    # Actualizar estado de sesión
    frappe.db.set_value(
        "WhatsApp Session",
        {"session_id": session_id},
        {
            "status": "Connected",
            "is_connected": 1,
            "phone_number": phone_number
        }
    )

    frappe.db.commit()

    frappe.logger().info(f"Sesión {session_id} conectada: {phone_number}")


def handle_session_disconnected(session_id, data):
    """
    Procesar desconexión de sesión
    """
    reason = data.get('reason', 'unknown')

    # Actualizar estado de sesión
    frappe.db.set_value(
        "WhatsApp Session",
        {"session_id": session_id},
        {
            "status": "Disconnected",
            "is_connected": 0
        }
    )

    frappe.db.commit()

    frappe.logger().warning(f"Sesión {session_id} desconectada: {reason}")


def handle_session_qr(session_id, data):
    """
    Procesar nuevo código QR
    """
    qr_code = data.get('qrCode', '')

    # Actualizar QR en sesión
    frappe.db.set_value(
        "WhatsApp Session",
        {"session_id": session_id},
        {
            "qr_code": qr_code,
            "status": "QR Code"
        }
    )

    frappe.db.commit()

    # Notificar vía WebSocket para mostrar QR en tiempo real
    frappe.publish_realtime(
        'whatsapp_qr_generated',
        {
            'session_id': session_id,
            'qr_code': qr_code
        }
    )
```

#### **JavaScript/Node.js (Express)**

```javascript
const express = require('express');
const crypto = require('crypto');
const router = express.Router();

// Configuración
const WEBHOOK_SECRET = process.env.INBOX_HUB_WEBHOOK_SECRET || 'mi_secreto_webhook_seguro';

// Endpoint para recibir webhooks
router.post('/webhook/whatsapp', express.raw({ type: 'application/json' }), (req, res) => {
  try {
    // 1. Obtener headers
    const signature = req.headers['x-webhook-signature'] || '';
    const eventType = req.headers['x-webhook-event'] || '';
    const sessionId = req.headers['x-webhook-session'] || '';
    const timestamp = req.headers['x-webhook-timestamp'] || '';

    // 2. Obtener payload
    const payload = req.body.toString();
    const body = JSON.parse(payload);

    // 3. Validar firma
    if (!verifyWebhookSignature(payload, signature, WEBHOOK_SECRET)) {
      console.error('❌ Firma inválida:', signature);
      return res.status(401).json({ success: false, error: 'Invalid signature' });
    }

    // 4. Procesar evento
    const event = body.event;
    const data = body.data;
    const session_id = body.sessionId;

    switch (event) {
      case 'message.received':
        handleMessageReceived(session_id, data);
        break;
      case 'message.sent':
        handleMessageSent(session_id, data);
        break;
      case 'message.ack':
        handleMessageAck(session_id, data);
        break;
      case 'session.connected':
        handleSessionConnected(session_id, data);
        break;
      case 'session.disconnected':
        handleSessionDisconnected(session_id, data);
        break;
      case 'session.qr':
        handleSessionQR(session_id, data);
        break;
      default:
        console.warn(`⚠️ Evento no manejado: ${event}`);
    }

    // 5. Responder rápidamente (200 OK)
    res.status(200).json({ success: true, received: true });

  } catch (error) {
    console.error('❌ Error procesando webhook:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Función para verificar firma HMAC
function verifyWebhookSignature(payload, signature, secret) {
  if (!signature || !secret) return false;

  // Remover prefijo 'sha256=' si existe
  const receivedSignature = signature.replace('sha256=', '');

  // Calcular firma esperada
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  // Comparar de forma segura
  return crypto.timingSafeEqual(
    Buffer.from(receivedSignature),
    Buffer.from(expectedSignature)
  );
}

// Handlers de eventos
function handleMessageReceived(sessionId, data) {
  console.log('💬 Mensaje recibido:', {
    from: data.from,
    body: data.body,
    timestamp: data.timestamp
  });

  // Guardar en base de datos
  // ... tu lógica de guardado

  // Notificar a usuarios vía WebSocket
  // ... tu lógica de notificación
}

function handleMessageSent(sessionId, data) {
  console.log('✅ Mensaje enviado:', data.id);
  // Actualizar estado en BD
}

function handleMessageAck(sessionId, data) {
  console.log('📨 Confirmación:', {
    messageId: data.messageId,
    ack: data.ack
  });
  // Actualizar estado en BD
}

function handleSessionConnected(sessionId, data) {
  console.log('🟢 Sesión conectada:', data.phoneNumber);
  // Actualizar estado en BD
}

function handleSessionDisconnected(sessionId, data) {
  console.log('🔴 Sesión desconectada:', data.reason);
  // Actualizar estado en BD
}

function handleSessionQR(sessionId, data) {
  console.log('📱 Nuevo QR generado');
  // Guardar QR y notificar a usuarios
}

module.exports = router;
```

### **PASO 3: Configurar Webhook en la Organización (Opcional pero Recomendado)**

Para gestionar webhooks de forma más avanzada, puedes crear un webhook a nivel de organización:

**NOTA:** Las rutas de webhooks a nivel de organización pueden requerir JWT Token si están protegidas.

```bash
POST https://api.inbox-hub.com/api/webhooks/organizations/{organizationId}
Headers:
  X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
  Content-Type: application/json
  # Si la ruta requiere JWT, agregar:
  # Authorization: Bearer {JWT_TOKEN}

Body:
{
  "name": "Webhook CRM Principal",
  "url": "https://crm.grupoatu.com/api/method/xappiens_whatsapp.api.webhook.handle_webhook",
  "events": [
    "message.received",
    "message.sent",
    "message.ack",
    "session.connected",
    "session.disconnected",
    "session.qr",
    "conversation.created",
    "conversation.updated"
  ],
  "headers": {
    "Authorization": "Bearer tu_token_interno"
  },
  "retryConfig": {
    "attempts": 3,
    "delay": 1000
  },
  "timeout": 30000,
  "secret": "mi_secreto_webhook_seguro"
}
```

---

## 📨 **FORMATO DE WEBHOOKS RECIBIDOS**

### **1. Mensaje Recibido (`message.received`)**

```json
{
  "event": "message.received",
  "sessionId": "mi_sesion_crm",
  "data": {
    "id": {
      "fromMe": false,
      "remote": "34612345678@c.us",
      "id": "3EB0250462D167CE4A3F0D",
      "_serialized": "false_34612345678@c.us_3EB0250462D167CE4A3F0D_in"
    },
    "body": "Hola, ¿cómo estás?",
    "type": "chat",
    "timestamp": 1729443600,
    "from": "34612345678@c.us",
    "to": "34657032985@c.us",
    "fromMe": false,
    "hasMedia": false,
    "isForwarded": false,
    "isStarred": false,
    "isStatus": false,
    "quotedMsgId": null
  },
  "timestamp": "2025-10-14T06:30:00.000Z"
}
```

### **2. Mensaje Enviado (`message.sent`)**

```json
{
  "event": "message.sent",
  "sessionId": "mi_sesion_crm",
  "data": {
    "id": {
      "fromMe": true,
      "remote": "34612345678@c.us",
      "id": "3EB0250462D167CE4A3F0E",
      "_serialized": "true_34612345678@c.us_3EB0250462D167CE4A3F0E_out"
    },
    "body": "Respuesta automática",
    "timestamp": 1729443610,
    "from": "34657032985@c.us",
    "to": "34612345678@c.us",
    "fromMe": true
  },
  "timestamp": "2025-10-14T06:30:10.000Z"
}
```

### **3. Confirmación de Mensaje (`message.ack`)**

```json
{
  "event": "message.ack",
  "sessionId": "mi_sesion_crm",
  "data": {
    "messageId": "3EB0250462D167CE4A3F0D",
    "ack": 3,
    "timestamp": 1729443650
  },
  "timestamp": "2025-10-14T06:30:50.000Z"
}
```

**Códigos de ACK:**
- `0` = Pendiente
- `1` = Servidor (enviado al servidor)
- `2` = Entregado (delivered)
- `3` = Leído (read)

### **4. Sesión Conectada (`session.connected`)**

```json
{
  "event": "session.connected",
  "sessionId": "mi_sesion_crm",
  "data": {
    "phoneNumber": "34657032985",
    "timestamp": "2025-10-14T06:30:00.000Z"
  },
  "timestamp": "2025-10-14T06:30:00.000Z"
}
```

### **5. Sesión Desconectada (`session.disconnected`)**

```json
{
  "event": "session.disconnected",
  "sessionId": "mi_sesion_crm",
  "data": {
    "reason": "logout",
    "timestamp": "2025-10-14T06:45:00.000Z"
  },
  "timestamp": "2025-10-14T06:45:00.000Z"
}
```

### **6. Nuevo Código QR (`session.qr`)**

```json
{
  "event": "session.qr",
  "sessionId": "mi_sesion_crm",
  "data": {
    "qrCode": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "expiresAt": "2025-10-14T06:35:00.000Z"
  },
  "timestamp": "2025-10-14T06:30:00.000Z"
}
```

---

## 🔐 **SEGURIDAD DE WEBHOOKS**

### **Validación de Firma HMAC**

**IMPORTANTE:** Siempre valida la firma antes de procesar el webhook.

```python
def verify_webhook_signature(payload, signature, secret):
    """
    Verifica la firma HMAC del webhook

    Args:
        payload: Cuerpo del request (string)
        signature: Firma recibida en header X-Webhook-Signature
        secret: Secreto compartido configurado en la sesión

    Returns:
        bool: True si la firma es válida
    """
    if not signature or not secret:
        return False

    # Remover prefijo 'sha256=' si existe
    if signature.startswith('sha256='):
        signature = signature[7:]

    # Calcular firma esperada
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Comparar de forma segura (timing-safe)
    return hmac.compare_digest(signature, expected_signature)
```

### **Headers de Seguridad**

Los webhooks incluyen estos headers:

```http
X-Webhook-Signature: sha256={firma_hmac}
X-Webhook-Event: message.received
X-Webhook-Session: mi_sesion_crm
X-Webhook-Timestamp: 1729443600000
```

**Validación recomendada:**
1. Verificar que `X-Webhook-Signature` existe
2. Verificar que el timestamp no sea muy antiguo (>5 minutos)
3. Calcular y comparar la firma HMAC
4. Solo procesar si la firma es válida

---

## 🛠️ **TESTING Y DEBUGGING**

### **Test de Conectividad**

```bash
curl -X GET https://api.inbox-hub.com/api/webhooks/test/connectivity
```

### **Test de Firma HMAC**

```bash
curl -X POST https://api.inbox-hub.com/api/webhooks/test/signature \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Signature: sha256=tu_firma_aqui" \
  -H "X-Webhook-Event: message.received" \
  -H "X-Webhook-Session: mi_sesion_crm" \
  -d '{"event": "message.received", "data": {"test": true}}'
```

### **Enviar Webhook de Prueba**

```bash
POST https://api.inbox-hub.com/api/webhooks/{webhookId}/test
Headers:
  X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
  # Si la ruta requiere JWT, agregar:
  # Authorization: Bearer {JWT_TOKEN}

Body:
{
  "testPayload": {
    "event": "message.received",
    "sessionId": "mi_sesion_crm",
    "data": {
      "from": "34612345678@c.us",
      "body": "Mensaje de prueba",
      "timestamp": 1729443600
    }
  }
}
```

---

## ⚠️ **MEJORES PRÁCTICAS**

### **1. Responder Rápido (200 OK)**

```javascript
// ✅ CORRECTO: Responder inmediatamente
app.post('/webhook', (req, res) => {
  // Procesar en background
  processWebhookAsync(req.body);

  // Responder rápidamente
  res.status(200).json({ success: true });
});

// ❌ INCORRECTO: Esperar procesamiento
app.post('/webhook', async (req, res) => {
  await processWebhook(req.body); // Puede tardar mucho
  res.status(200).json({ success: true });
});
```

### **2. Implementar Reintentos**

```python
def process_webhook_with_retry(data, max_retries=3):
    for attempt in range(max_retries):
        try:
            process_webhook(data)
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                frappe.log_error(f"Error después de {max_retries} intentos: {str(e)}")
                return False
            time.sleep(2 ** attempt)  # Exponential backoff
    return False
```

### **3. Logging Detallado**

```python
import logging

logger = logging.getLogger('webhook_handler')

def handle_message_received(session_id, data):
    logger.info(f"Mensaje recibido - Session: {session_id}, From: {data.get('from')}")

    try:
        # Procesar mensaje
        process_message(data)
        logger.info(f"Mensaje procesado exitosamente")
    except Exception as e:
        logger.error(f"Error procesando mensaje: {str(e)}", exc_info=True)
        raise
```

### **4. Manejo de Errores**

```javascript
function handleWebhook(req, res) {
  try {
    // Validar firma
    if (!verifySignature(req)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }

    // Procesar evento
    processEvent(req.body);

    // Responder éxito
    res.status(200).json({ success: true });

  } catch (error) {
    // Log error
    console.error('Webhook error:', error);

    // Responder error (pero el webhook fue recibido)
    res.status(500).json({
      success: false,
      error: 'Internal error',
      // NO exponer detalles internos
    });
  }
}
```

---

## 📊 **MONITOREO Y ESTADÍSTICAS**

### **Obtener Estadísticas de Webhooks**

```bash
GET https://api.inbox-hub.com/api/webhooks/organizations/{organizationId}/stats
Headers:
  X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
  # Si la ruta requiere JWT, agregar:
  # Authorization: Bearer {JWT_TOKEN}
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "totalDeliveries": 1500,
    "successfulDeliveries": 1480,
    "failedDeliveries": 20,
    "averageResponseTime": 250,
    "lastDelivery": "2025-10-14T06:30:00.000Z"
  }
}
```

### **Reporte de Salud**

```bash
GET https://api.inbox-hub.com/api/webhooks/organizations/{organizationId}/health
```

---

## ✅ **CHECKLIST DE IMPLEMENTACIÓN**

### **Antes de Producción:**

- [ ] Endpoint receptor de webhooks implementado
- [ ] Validación de firma HMAC implementada
- [ ] Manejo de todos los eventos necesarios
- [ ] Logging y monitoreo configurado
- [ ] Manejo de errores y reintentos
- [ ] Respuesta rápida (200 OK) sin bloquear
- [ ] Procesamiento asíncrono de mensajes
- [ ] Webhook URL accesible públicamente
- [ ] Webhook configurado en la sesión
- [ ] Pruebas de conectividad realizadas
- [ ] Pruebas de firma realizadas
- [ ] Pruebas de eventos realizadas

---

## 📞 **SOPORTE**

Si tienes problemas:

1. **Verificar conectividad:** `/api/webhooks/test/connectivity`
2. **Verificar firma:** `/api/webhooks/test/signature`
3. **Revisar logs:** Ver logs del servidor para errores
4. **Consultar documentación:** `DOCUMENTACION_COMPLETA_BAILEYS.md` sección Webhooks

---

*Guía completa de webhooks para integración CRM en tiempo real*
*Versión 1.0 - Octubre 2025*

