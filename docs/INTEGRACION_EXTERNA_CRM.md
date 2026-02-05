# 🔗 Integración Externa con CRM - Inbox Hub API

**Fecha:** 14 de Octubre de 2025
**Propósito:** Guía completa para conectar sistemas CRM externos con Inbox Hub

---

## 🎯 **RESUMEN DE INTEGRACIÓN**

### **¿Qué puedes hacer desde tu CRM?**
- ✅ **Enviar mensajes de WhatsApp** a contactos
- ✅ **Recibir mensajes** via webhooks
- ✅ **Gestionar contactos** y conversaciones
- ✅ **Obtener estado de sesiones** WhatsApp
- ✅ **Subir y gestionar archivos** multimedia
- ✅ **Crear y usar plantillas** de mensajes
- ✅ **Gestionar grupos** de WhatsApp
- ✅ **Acceder a estadísticas** y métricas

### **Arquitectura de Integración**
```
┌─────────────────┐    HTTPS/REST API    ┌─────────────────┐
│   Tu CRM        │ ◄─────────────────► │  Inbox Hub API  │
│   Externo       │    JWT + API Key     │  (Puerto 8084)  │
└─────────────────┘                      └─────────────────┘
                                                   │
                                                   ▼
                                         ┌─────────────────┐
                                         │   WhatsApp      │
                                         │   Sessions      │
                                         └─────────────────┘
```

---

## 🔐 **SISTEMA DE AUTENTICACIÓN**

### **Autenticación Simplificada para WhatsApp**
**IMPORTANTE:** Las rutas de WhatsApp (sessions, messages, contacts, groups, status, media) **SOLO requieren API Key**, NO requieren JWT Token.

Para acceder a los endpoints de WhatsApp necesitas:
1. **API Key** (header `X-API-Key`) - **SOLO ESTO es necesario para WhatsApp**

**Nota:** El JWT Token solo es necesario para rutas de autenticación (`/api/auth/*`) y organizaciones (`/api/organizations/*`).

### **1. Obtener JWT Token Permanente**

#### **Endpoint de Login**
```http
POST https://api.inbox-hub.com/api/auth/login
Content-Type: application/json

{
  "identifier": "tu_usuario@empresa.com",
  "password": "tu_password_seguro"
}
```

#### **Respuesta**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIs...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
    "expiresIn": "24h"
  }
}
```

#### **Renovación Automática de Token**
```javascript
// Ejemplo en JavaScript/Node.js
class InboxHubAuth {
  constructor(email, password, apiKey = 'prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814') {
    this.email = email;
    this.password = password;
    this.apiKey = apiKey; // API Key por defecto para WhatsApp
    this.accessToken = null;
    this.refreshToken = null;
  }

  async login() {
    const response = await fetch('https://api.inbox-hub.com/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        identifier: this.email,
        password: this.password
      })
    });

    const data = await response.json();
    if (data.success) {
      this.accessToken = data.data.accessToken;
      this.refreshToken = data.data.refreshToken;

      // Renovar automáticamente antes de que expire
      setTimeout(() => this.renewToken(), 23 * 60 * 60 * 1000); // 23 horas
    }
    return data;
  }

  async renewToken() {
    // Implementar renovación con refreshToken
    return await this.login(); // Fallback: nuevo login
  }

  getHeaders(forWhatsApp = true) {
    // Para rutas de WhatsApp: SOLO API Key
    if (forWhatsApp) {
      return {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      };
    }
    // Para rutas de auth/organizaciones: JWT + API Key
    return {
      'Authorization': `Bearer ${this.accessToken}`,
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json'
    };
  }
}
```

### **2. API Key Permanente**
```bash
# API Key para rutas de WhatsApp
API_KEY="prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814"
```

**⚠️ IMPORTANTE:** Esta API Key es la que debes usar en todos los headers `X-API-Key` para las rutas de WhatsApp.

---

## 📱 **ENDPOINTS PRINCIPALES PARA CRM**

### **Base URL**
```
https://api.inbox-hub.com
```

### **Headers Requeridos para WhatsApp**

**IMPORTANTE:** Las rutas de WhatsApp SOLO requieren API Key, NO JWT Token.

```http
X-API-Key: prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814
Content-Type: application/json
```

**Nota:** El JWT Token solo es necesario para rutas de autenticación (`/api/auth/*`) y organizaciones (`/api/organizations/*`).

---

## 💬 **ENVÍO DE MENSAJES**

### **1. Enviar Mensaje Simple**
```http
POST /api/messages/{sessionId}/send
```

**Ejemplo:**
```json
{
  "to": "34612345678",
  "message": "Hola desde nuestro CRM! Tu pedido está listo."
}
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "messageId": "msg_12345",
    "status": "sent",
    "timestamp": "2025-10-14T10:30:00Z"
  }
}
```

### **2. Enviar Mensaje con Plantilla**
```http
POST /api/templates/{templateId}/use
```

**Ejemplo:**
```json
{
  "to": "34612345678",
  "variables": {
    "nombre": "Juan Pérez",
    "pedido": "#12345",
    "fecha": "15/10/2025"
  }
}
```

### **3. Enviar Mensaje Masivo**
```json
{
  "to": ["34612345678", "34687654321", "34611111111"],
  "message": "Promoción especial: 20% descuento hasta mañana!"
}
```

### **4. Enviar Archivo Multimedia**
```http
POST /api/media/sessions/{sessionId}/upload
Content-Type: multipart/form-data

# Luego enviar mensaje con el archivo
POST /api/messages/{sessionId}/send
{
  "to": "34612345678",
  "message": "Aquí tienes tu factura",
  "mediaId": "media_12345"
}
```

---

## 📞 **RECEPCIÓN DE MENSAJES (WEBHOOKS)**

### **Configurar Webhook en tu CRM**

#### **1. Crear Webhook**
```http
POST /api/webhooks/organizations/{organizationId}
```

```json
{
  "name": "CRM Integration Webhook",
  "url": "https://tu-crm.com/api/webhooks/inbox-hub",
  "events": ["message", "message_status", "session_status"],
  "secret": "tu_webhook_secret_seguro"
}
```

#### **2. Estructura del Webhook Recibido**
```json
{
  "event": "message",
  "timestamp": "2025-10-14T10:30:00Z",
  "sessionId": "session_crm_01",
  "data": {
    "messageId": "msg_67890",
    "from": "34612345678",
    "to": "session_crm_01",
    "message": "Hola, necesito información sobre mi pedido",
    "type": "text",
    "timestamp": "2025-10-14T10:30:00Z",
    "contact": {
      "name": "Juan Pérez",
      "phone": "34612345678"
    }
  }
}
```

#### **3. Verificar Webhook (Seguridad)**
```javascript
// Verificar firma del webhook
const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');

  return signature === `sha256=${expectedSignature}`;
}
```

---

## 👥 **GESTIÓN DE CONTACTOS**

### **1. Obtener Contactos**
```http
GET /api/contacts/{sessionId}?page=1&limit=50
```

### **2. Buscar Contacto**
```http
GET /api/contacts/{sessionId}/search/{phoneNumber}
```

### **3. Actualizar Contacto**
```http
PUT /api/contacts/{contactId}
```

```json
{
  "name": "Juan Pérez García",
  "tags": ["cliente_vip", "madrid"],
  "notes": "Cliente desde 2020, prefiere WhatsApp",
  "assignedToUserId": 5
}
```

---

## 📊 **ESTADO DE SESIONES**

### **1. Verificar Estado de Sesión**
```http
GET /api/sessions/{sessionId}/status
```

**Respuesta:**
```json
{
  "success": true,
  "data": {
    "sessionId": "session_crm_01",
    "status": "connected",
    "phoneNumber": "34612345678",
    "isConnected": true,
    "lastActivity": "2025-10-14T10:25:00Z"
  }
}
```

### **2. Listar Todas las Sesiones**
```http
GET /api/sessions?status=connected
```

---

## 📝 **PLANTILLAS DE MENSAJES**

### **1. Crear Plantilla**
```http
POST /api/templates/organizations/{organizationId}
```

```json
{
  "name": "Confirmación de Pedido",
  "category": "pedidos",
  "body": "Hola {{nombre}}, tu pedido {{pedido}} está confirmado para el {{fecha}}. ¡Gracias por tu compra!",
  "variables": ["nombre", "pedido", "fecha"],
  "isActive": true
}
```

### **2. Usar Plantilla**
```http
POST /api/templates/{templateId}/use
```

---

## 🔍 **EJEMPLOS DE INTEGRACIÓN POR LENGUAJE**

### **JavaScript/Node.js**
```javascript
class InboxHubCRM {
  constructor(apiKey, email, password) {
    this.baseURL = 'https://api.inbox-hub.com';
    this.auth = new InboxHubAuth(email, password, apiKey);
  }

  async init() {
    await this.auth.login();
  }

    async sendMessage(sessionId, to, message) {
    const response = await fetch(`${this.baseURL}/api/messages/${sessionId}/send`, {
      method: 'POST',
      headers: this.auth.getHeaders(true), // true = para WhatsApp (solo API Key)
      body: JSON.stringify({ to, message })
    });
    return await response.json();
  }

  async getContacts(sessionId, page = 1) {
    const response = await fetch(`${this.baseURL}/api/contacts/${sessionId}?page=${page}`, {
      headers: this.auth.getHeaders(true) // true = para WhatsApp (solo API Key)
    });
    return await response.json();
  }

  async getSessionStatus(sessionId) {
    const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/status`, {
      headers: this.auth.getHeaders(true) // true = para WhatsApp (solo API Key)
    });
    return await response.json();
  }
}

// Uso
const crm = new InboxHubCRM('tu_api_key', 'usuario@empresa.com', 'password');
await crm.init();

// Enviar mensaje
await crm.sendMessage('session_01', '34612345678', 'Hola desde el CRM!');
```

### **Python**
```python
import requests
import time
from datetime import datetime, timedelta

class InboxHubCRM:
    def __init__(self, api_key, email, password):
        self.base_url = 'https://api.inbox-hub.com'
        self.api_key = api_key
        self.email = email
        self.password = password
        self.access_token = None
        self.token_expires = None

    def login(self):
        response = requests.post(f'{self.base_url}/api/auth/login', json={
            'identifier': self.email,
            'password': self.password
        })

        if response.status_code == 200:
            data = response.json()
            self.access_token = data['data']['accessToken']
            self.token_expires = datetime.now() + timedelta(hours=23)
            return True
        return False

    def get_headers(self, for_whatsapp=True):
        if not self.access_token or datetime.now() >= self.token_expires:
            self.login()

        # Para rutas de WhatsApp: SOLO API Key
        if for_whatsapp:
            return {
                'X-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }
        # Para rutas de auth/organizaciones: JWT + API Key
        return {
            'Authorization': f'Bearer {self.access_token}',
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }

    def send_message(self, session_id, to, message):
        response = requests.post(
            f'{self.base_url}/api/messages/{session_id}/send',
            headers=self.get_headers(for_whatsapp=True), # Solo API Key para WhatsApp
            json={'to': to, 'message': message}
        )
        return response.json()

    def get_contacts(self, session_id, page=1):
        response = requests.get(
            f'{self.base_url}/api/contacts/{session_id}?page={page}',
            headers=self.get_headers(for_whatsapp=True) # Solo API Key para WhatsApp
        )
        return response.json()

# Uso
crm = InboxHubCRM('tu_api_key', 'usuario@empresa.com', 'password')
crm.login()

# Enviar mensaje
result = crm.send_message('session_01', '34612345678', 'Hola desde Python!')
```

### **PHP**
```php
<?php
class InboxHubCRM {
    private $baseURL = 'https://api.inbox-hub.com';
    private $apiKey;
    private $email;
    private $password;
    private $accessToken;
    private $tokenExpires;

    public function __construct($apiKey, $email, $password) {
        $this->apiKey = $apiKey;
        $this->email = $email;
        $this->password = $password;
    }

    public function login() {
        $response = $this->makeRequest('POST', '/api/auth/login', [
            'identifier' => $this->email,
            'password' => $this->password
        ]);

        if ($response['success']) {
            $this->accessToken = $response['data']['accessToken'];
            $this->tokenExpires = time() + (23 * 3600); // 23 horas
            return true;
        }
        return false;
    }

    private function getHeaders($forWhatsApp = true) {
        if (!$this->accessToken || time() >= $this->tokenExpires) {
            $this->login();
        }

        // Para rutas de WhatsApp: SOLO API Key
        if ($forWhatsApp) {
            return [
                'X-API-Key: ' . $this->apiKey,
                'Content-Type: application/json'
            ];
        }
        // Para rutas de auth/organizaciones: JWT + API Key
        return [
            'Authorization: Bearer ' . $this->accessToken,
            'X-API-Key: ' . $this->apiKey,
            'Content-Type: application/json'
        ];
    }

    public function sendMessage($sessionId, $to, $message) {
        return $this->makeRequest('POST', "/api/messages/{$sessionId}/send", [
            'to' => $to,
            'message' => $message
        ], true); // true = para WhatsApp (solo API Key)
    }

    private function makeRequest($method, $endpoint, $data = null) {
        $curl = curl_init();
        curl_setopt_array($curl, [
            CURLOPT_URL => $this->baseURL . $endpoint,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => $this->getHeaders(),
            CURLOPT_POSTFIELDS => $data ? json_encode($data) : null,
        ]);

        $response = curl_exec($curl);
        curl_close($curl);

        return json_decode($response, true);
    }
}

// Uso
$crm = new InboxHubCRM('tu_api_key', 'usuario@empresa.com', 'password');
$crm->login();

// Enviar mensaje
$result = $crm->sendMessage('session_01', '34612345678', 'Hola desde PHP!');
?>
```

---

## 🚨 **MANEJO DE ERRORES**

### **Códigos de Error Comunes**
```json
{
  "success": false,
  "error": "Token de acceso requerido",
  "code": "MISSING_TOKEN",
  "timestamp": "2025-10-14T10:30:00Z"
}
```

### **Errores Típicos y Soluciones**
| Código | Error | Solución |
|--------|-------|----------|
| `MISSING_API_KEY` | API Key no proporcionada | Incluir header `X-API-Key: [key]` (requerido para WhatsApp) |
| `INVALID_API_KEY` | API Key inválida | Verificar API Key con administrador |
| `MISSING_TOKEN` | JWT token no proporcionado | Solo necesario para `/api/auth/*` y `/api/organizations/*` |
| `INVALID_TOKEN` | JWT token inválido/expirado | Renovar token con `/api/auth/login` (solo si usas rutas que requieren JWT) |
| `SESSION_NOT_FOUND` | Sesión no existe | Verificar sessionId correcto |
| `SESSION_DISCONNECTED` | Sesión WhatsApp desconectada | Reconectar sesión o usar otra |
| `RATE_LIMIT_EXCEEDED` | Demasiadas peticiones | Esperar y reintentar con backoff |

### **Implementar Reintentos**
```javascript
async function retryRequest(requestFn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const result = await requestFn();
      if (result.success) return result;

      if (result.code === 'RATE_LIMIT_EXCEEDED') {
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
        continue;
      }

      throw new Error(result.error);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
}
```

---

## 📊 **LÍMITES Y CUOTAS**

### **Rate Limiting**
- **Autenticación:** 5 requests/15min por IP
- **General:** 100 requests/15min por usuario
- **WhatsApp:** 30 requests/min por sesión
- **Mensajes:** 10 mensajes/min por sesión

### **Límites de Datos**
- **Mensaje de texto:** 4096 caracteres
- **Archivo multimedia:** 50MB máximo
- **Contactos por página:** 100 máximo
- **Mensajes masivos:** 50 destinatarios máximo

---

## 🔒 **SEGURIDAD Y MEJORES PRÁCTICAS**

### **1. Almacenamiento Seguro**
```javascript
// ❌ MAL - No hardcodear credenciales
const apiKey = 'prod_whatsapp_api_123456789';

// ✅ BIEN - Usar variables de entorno
const apiKey = process.env.INBOX_HUB_API_KEY;
```

### **2. Validación de Webhooks**
```javascript
// Siempre verificar la firma del webhook
app.post('/webhook/inbox-hub', (req, res) => {
  const signature = req.headers['x-signature'];
  const payload = JSON.stringify(req.body);

  if (!verifyWebhook(payload, signature, process.env.WEBHOOK_SECRET)) {
    return res.status(401).send('Unauthorized');
  }

  // Procesar webhook...
});
```

### **3. Manejo de Tokens**
- ✅ Renovar tokens automáticamente
- ✅ Almacenar tokens de forma segura
- ✅ Implementar refresh token si está disponible
- ✅ Manejar expiración gracefully

---

## 📞 **SOPORTE Y CONTACTO**

### **Documentación Adicional**
- **API Completa:** `https://api.inbox-hub.com/api/docs`
- **Esquema de BD:** `/home/ubuntu/inbox-hub/backend/docs/DATABASE_SCHEMA.md`
- **Ejemplos:** `/home/ubuntu/inbox-hub/docs/api/examples/`

### **Testing de Integración**
```bash
# Health check
curl https://api.inbox-hub.com/health

# Test de autenticación
curl -X POST https://api.inbox-hub.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"test@empresa.com","password":"test_password"}'
```

### **Ambiente de Pruebas**
- **URL:** `https://staging-api.inbox-hub.com`
- **Datos de prueba:** Disponibles para testing
- **Rate limits:** Más permisivos para desarrollo

---

*Guía de integración externa actualizada el 14 de Octubre de 2025*
*Para conectar cualquier CRM o sistema externo con Inbox Hub de forma segura y eficiente*
