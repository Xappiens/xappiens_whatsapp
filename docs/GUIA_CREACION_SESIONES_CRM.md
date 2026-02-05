# 📱 Guía: Crear Sesiones WhatsApp desde el CRM

**Para:** Programador del CRM de Grupo ATU
**Objetivo:** Integrar la creación y gestión de sesiones WhatsApp desde el CRM
**Fecha:** 14 de Octubre de 2025

---

## 🎯 **RESUMEN EJECUTIVO**

Como programador del CRM, necesitas poder:
1. **Crear nuevas sesiones WhatsApp** para diferentes números/clientes
2. **Obtener códigos QR** para conectar WhatsApp Web
3. **Monitorear el estado** de las conexiones
4. **Gestionar múltiples sesiones** simultáneamente

---

## 🔑 **CREDENCIALES NECESARIAS**

```javascript
const CONFIG = {
  baseURL: 'https://api.inbox-hub.com',
  email: 'apiwhatsapp@grupoatu.com',
  password: 'GrupoATU2025!WhatsApp',
  apiKey: 'prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814'
};
```

---

## 🚀 **FLUJO COMPLETO DE CREACIÓN DE SESIÓN**

### **PASO 1: Autenticación**
```javascript
async function authenticate() {
  const response = await fetch(`${CONFIG.baseURL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      identifier: CONFIG.email,
      password: CONFIG.password
    })
  });

  const data = await response.json();
  if (data.success) {
    return data.data.accessToken;
  }
  throw new Error('Error de autenticación: ' + data.message);
}
```

### **PASO 2: Crear Nueva Sesión WhatsApp**
```javascript
async function createWhatsAppSession(sessionName, phoneNumber = null) {
  const token = await authenticate();

  const response = await fetch(`${CONFIG.baseURL}/api/sessions`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-API-Key': CONFIG.apiKey,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      sessionId: sessionName,        // Ej: "cliente_001", "sucursal_madrid"
      phoneNumber: phoneNumber,      // Opcional: número esperado
      name: `Sesión ${sessionName}`, // Nombre descriptivo
      description: `Sesión WhatsApp para ${sessionName}`
    })
  });

  const data = await response.json();
  if (data.success) {
    return {
      sessionId: data.data.sessionId,
      dbId: data.data.id,
      status: data.data.status,
      qrCode: data.data.qrCode || null
    };
  }
  throw new Error('Error creando sesión: ' + data.message);
}
```

### **PASO 3: Obtener Código QR**
```javascript
async function getQRCode(sessionId) {
  const token = await authenticate();

  // IMPORTANTE: Las rutas de WhatsApp SOLO requieren API Key, NO JWT Token
  const response = await fetch(`${CONFIG.baseURL}/api/sessions/${sessionId}/qr`, {
    headers: {
      'X-API-Key': CONFIG.apiKey
    }
  });

  const data = await response.json();
  if (data.success) {
    return {
      qrCode: data.data.qrCode,           // Base64 del QR
      qrCodeDataURL: data.data.qrCode,    // Listo para <img src="">
      expiresAt: data.data.expiresAt,     // Cuándo expira
      status: data.data.status
    };
  }
  throw new Error('Error obteniendo QR: ' + data.message);
}
```

### **PASO 4: Monitorear Estado de Conexión**
```javascript
async function checkSessionStatus(sessionDbId) {
  // IMPORTANTE: Las rutas de WhatsApp SOLO requieren API Key, NO JWT Token
  const response = await fetch(`${CONFIG.baseURL}/api/sessions/${sessionDbId}/status`, {
    headers: {
      'X-API-Key': CONFIG.apiKey
    }
  });

  const data = await response.json();
  if (data.success) {
    return {
      sessionId: data.data.sessionId,
      status: data.data.status,           // 'pending', 'connected', 'disconnected', 'error'
      phoneNumber: data.data.phoneNumber, // Número conectado (si está conectado)
      isConnected: data.data.isConnected,
      hasQR: data.data.hasQR,
      lastActivity: data.data.lastActivity
    };
  }
  throw new Error('Error verificando estado: ' + data.message);
}
```

---

## 💻 **CLASE COMPLETA PARA EL CRM**

```javascript
class WhatsAppSessionManager {
  constructor() {
    this.baseURL = 'https://api.inbox-hub.com';
    this.email = 'apiwhatsapp@grupoatu.com';
    this.password = 'GrupoATU2025!WhatsApp';
    this.apiKey = 'prod_whatsapp_api_315d76a7e515903648fdf3e9ecfd7fc43e8495fd29f3053fda7df0d766c97814';
    this.accessToken = null;
    this.tokenExpiry = null;
  }

  // Autenticación con cache de token
  async authenticate() {
    // Si tenemos token válido, usarlo
    if (this.accessToken && this.tokenExpiry && new Date() < this.tokenExpiry) {
      return this.accessToken;
    }

    const response = await fetch(`${this.baseURL}/api/auth/login`, {
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
      // Token válido por 24h, renovar 1h antes
      this.tokenExpiry = new Date(Date.now() + 23 * 60 * 60 * 1000);
      return this.accessToken;
    }
    throw new Error('Error de autenticación: ' + data.message);
  }

  // Headers estándar
  async getHeaders(forWhatsApp = true) {
    // Para rutas de WhatsApp: SOLO API Key
    if (forWhatsApp) {
      return {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      };
    }
    // Para rutas de auth/organizaciones: JWT + API Key
    const token = await this.authenticate();
    return {
      'Authorization': `Bearer ${token}`,
      'X-API-Key': this.apiKey,
      'Content-Type': 'application/json'
    };
  }

  // Crear nueva sesión WhatsApp
  async createSession(sessionName, options = {}) {
    try {
      const headers = await this.getHeaders();

      const response = await fetch(`${this.baseURL}/api/sessions`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          sessionId: sessionName,
          phoneNumber: options.phoneNumber || null,
          name: options.name || `Sesión ${sessionName}`,
          description: options.description || `Sesión WhatsApp para ${sessionName}`
        })
      });

      const data = await response.json();
      if (data.success) {
        return {
          success: true,
          sessionId: data.data.sessionId,
          dbId: data.data.id,
          status: data.data.status,
          message: 'Sesión creada exitosamente'
        };
      }

      return {
        success: false,
        error: data.message || 'Error desconocido'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  // Obtener código QR
  async getQRCode(sessionId) {
    try {
      const headers = await this.getHeaders();
      delete headers['Content-Type']; // No necesario para GET

      const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/qr`, {
        headers
      });

      const data = await response.json();
      if (data.success) {
        return {
          success: true,
          qrCode: data.data.qrCode,
          expiresAt: data.data.expiresAt,
          status: data.data.status
        };
      }

      return {
        success: false,
        error: data.message || 'Error obteniendo QR'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  // Verificar estado de sesión
  async getSessionStatus(sessionDbId) {
    try {
      const headers = await this.getHeaders();
      delete headers['Content-Type'];

      const response = await fetch(`${this.baseURL}/api/sessions/${sessionDbId}/status`, {
        headers
      });

      const data = await response.json();
      if (data.success) {
        return {
          success: true,
          sessionId: data.data.sessionId,
          status: data.data.status,
          phoneNumber: data.data.phoneNumber,
          isConnected: data.data.isConnected,
          hasQR: data.data.hasQR,
          lastActivity: data.data.lastActivity
        };
      }

      return {
        success: false,
        error: data.message || 'Error verificando estado'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  // Listar todas las sesiones del usuario
  async listSessions() {
    try {
      const headers = await this.getHeaders();
      delete headers['Content-Type'];

      const response = await fetch(`${this.baseURL}/api/sessions`, {
        headers
      });

      const data = await response.json();
      if (data.success) {
        return {
          success: true,
          sessions: data.data.sessions || [],
          total: data.data.total || 0
        };
      }

      return {
        success: false,
        error: data.message || 'Error listando sesiones'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  // Conectar sesión (iniciar proceso QR)
  async connectSession(sessionId) {
    try {
      const headers = await this.getHeaders();

      const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/connect`, {
        method: 'POST',
        headers
      });

      const data = await response.json();
      if (data.success) {
        return {
          success: true,
          message: 'Proceso de conexión iniciado',
          sessionId: data.data.sessionId,
          status: data.data.status
        };
      }

      return {
        success: false,
        error: data.message || 'Error conectando sesión'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  // Desconectar sesión
  async disconnectSession(sessionId) {
    try {
      const headers = await this.getHeaders();

      const response = await fetch(`${this.baseURL}/api/sessions/${sessionId}/disconnect`, {
        method: 'POST',
        headers
      });

      const data = await response.json();
      if (data.success) {
        return {
          success: true,
          message: 'Sesión desconectada'
        };
      }

      return {
        success: false,
        error: data.message || 'Error desconectando sesión'
      };
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }
}
```

---

## 🎯 **CASOS DE USO PRÁCTICOS**

### **Caso 1: Crear Sesión para Cliente Nuevo**
```javascript
const sessionManager = new WhatsAppSessionManager();

async function setupClientWhatsApp(clientId, clientName, phoneNumber) {
  try {
    // 1. Crear sesión
    const sessionResult = await sessionManager.createSession(
      `cliente_${clientId}`,
      {
        name: `WhatsApp ${clientName}`,
        description: `Sesión WhatsApp para cliente ${clientName}`,
        phoneNumber: phoneNumber
      }
    );

    if (!sessionResult.success) {
      throw new Error(sessionResult.error);
    }

    console.log(`✅ Sesión creada: ${sessionResult.sessionId}`);

    // 2. Iniciar conexión
    const connectResult = await sessionManager.connectSession(sessionResult.sessionId);
    if (!connectResult.success) {
      throw new Error(connectResult.error);
    }

    // 3. Obtener QR
    const qrResult = await sessionManager.getQRCode(sessionResult.sessionId);
    if (!qrResult.success) {
      throw new Error(qrResult.error);
    }

    return {
      success: true,
      sessionId: sessionResult.sessionId,
      dbId: sessionResult.dbId,
      qrCode: qrResult.qrCode,
      message: 'Sesión lista. Escanea el QR con WhatsApp.'
    };

  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

// Uso
const result = await setupClientWhatsApp(12345, 'Empresa ABC', '34612345678');
if (result.success) {
  console.log('QR Code:', result.qrCode);
  // Mostrar QR al usuario para escanear
} else {
  console.error('Error:', result.error);
}
```

### **Caso 2: Monitorear Estado de Conexión**
```javascript
async function monitorSession(sessionDbId) {
  const sessionManager = new WhatsAppSessionManager();

  const checkStatus = async () => {
    const status = await sessionManager.getSessionStatus(sessionDbId);

    if (status.success) {
      console.log(`Estado: ${status.status}`);

      switch (status.status) {
        case 'connected':
          console.log(`✅ Conectado como: ${status.phoneNumber}`);
          return 'connected';

        case 'pending':
          console.log('⏳ Esperando escaneo de QR...');
          break;

        case 'disconnected':
          console.log('❌ Desconectado');
          return 'disconnected';

        case 'error':
          console.log('🚨 Error en la sesión');
          return 'error';
      }
    }

    return status.status;
  };

  // Monitorear cada 5 segundos
  const interval = setInterval(async () => {
    const currentStatus = await checkStatus();

    if (['connected', 'error', 'disconnected'].includes(currentStatus)) {
      clearInterval(interval);
      console.log('Monitoreo finalizado');
    }
  }, 5000);
}

// Uso
monitorSession(2); // ID de la sesión en BD
```

### **Caso 3: Gestión Masiva de Sesiones**
```javascript
async function manageMultipleSessions() {
  const sessionManager = new WhatsAppSessionManager();

  // Listar todas las sesiones
  const sessions = await sessionManager.listSessions();

  if (sessions.success) {
    console.log(`Total sesiones: ${sessions.total}`);

    for (const session of sessions.sessions) {
      console.log(`\n📱 Sesión: ${session.sessionId}`);
      console.log(`   Estado: ${session.status}`);
      console.log(`   Teléfono: ${session.phoneNumber || 'No conectado'}`);

      // Si está desconectada, intentar reconectar
      if (session.status === 'disconnected') {
        console.log('   🔄 Intentando reconectar...');
        const reconnect = await sessionManager.connectSession(session.sessionId);

        if (reconnect.success) {
          // Obtener nuevo QR
          const qr = await sessionManager.getQRCode(session.sessionId);
          if (qr.success) {
            console.log('   📱 Nuevo QR disponible');
            // Aquí podrías enviar el QR por email, mostrar en dashboard, etc.
          }
        }
      }
    }
  }
}

// Ejecutar cada hora
setInterval(manageMultipleSessions, 60 * 60 * 1000);
```

---

## 🔧 **INTEGRACIÓN CON TU CRM**

### **En tu Base de Datos CRM:**
```sql
-- Tabla para almacenar sesiones WhatsApp
CREATE TABLE whatsapp_sessions (
  id INT PRIMARY KEY AUTO_INCREMENT,
  client_id INT NOT NULL,
  session_id VARCHAR(100) NOT NULL,
  session_db_id INT NOT NULL,
  phone_number VARCHAR(20),
  status ENUM('pending', 'connected', 'disconnected', 'error') DEFAULT 'pending',
  qr_code TEXT,
  qr_expires_at DATETIME,
  connected_at DATETIME,
  last_check DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (client_id) REFERENCES clients(id),
  UNIQUE KEY unique_session (session_id)
);
```

### **En tu Código CRM (PHP ejemplo):**
```php
<?php
class CRMWhatsAppIntegration {
    private $sessionManager;
    private $db;

    public function __construct($database) {
        $this->sessionManager = new WhatsAppSessionManager();
        $this->db = $database;
    }

    public function createClientWhatsApp($clientId, $clientName, $phoneNumber) {
        // 1. Crear sesión en Inbox Hub
        $sessionId = "cliente_" . $clientId;
        $result = $this->sessionManager->createSession($sessionId, [
            'name' => "WhatsApp {$clientName}",
            'phoneNumber' => $phoneNumber
        ]);

        if ($result['success']) {
            // 2. Guardar en BD del CRM
            $stmt = $this->db->prepare("
                INSERT INTO whatsapp_sessions
                (client_id, session_id, session_db_id, phone_number, status)
                VALUES (?, ?, ?, ?, 'pending')
            ");
            $stmt->execute([
                $clientId,
                $result['sessionId'],
                $result['dbId'],
                $phoneNumber
            ]);

            // 3. Iniciar conexión y obtener QR
            $this->sessionManager->connectSession($result['sessionId']);
            $qr = $this->sessionManager->getQRCode($result['sessionId']);

            if ($qr['success']) {
                // 4. Actualizar QR en BD
                $stmt = $this->db->prepare("
                    UPDATE whatsapp_sessions
                    SET qr_code = ?, qr_expires_at = ?
                    WHERE session_id = ?
                ");
                $stmt->execute([
                    $qr['qrCode'],
                    $qr['expiresAt'],
                    $result['sessionId']
                ]);

                return [
                    'success' => true,
                    'qr_code' => $qr['qrCode'],
                    'session_id' => $result['sessionId']
                ];
            }
        }

        return ['success' => false, 'error' => $result['error']];
    }

    public function checkAllSessions() {
        $stmt = $this->db->query("
            SELECT * FROM whatsapp_sessions
            WHERE status IN ('pending', 'connected')
        ");

        while ($session = $stmt->fetch()) {
            $status = $this->sessionManager->getSessionStatus($session['session_db_id']);

            if ($status['success'] && $status['status'] !== $session['status']) {
                // Actualizar estado en CRM
                $updateStmt = $this->db->prepare("
                    UPDATE whatsapp_sessions
                    SET status = ?, phone_number = ?, last_check = NOW()
                    WHERE id = ?
                ");
                $updateStmt->execute([
                    $status['status'],
                    $status['phoneNumber'],
                    $session['id']
                ]);

                // Si se conectó, notificar
                if ($status['status'] === 'connected') {
                    $this->notifyConnectionSuccess($session['client_id'], $status['phoneNumber']);
                }
            }
        }
    }

    private function notifyConnectionSuccess($clientId, $phoneNumber) {
        // Enviar email, notificación push, etc.
        echo "✅ Cliente {$clientId} conectó WhatsApp: {$phoneNumber}\n";
    }
}

// Uso
$crm = new CRMWhatsAppIntegration($pdo);

// Crear sesión para cliente
$result = $crm->createClientWhatsApp(12345, 'Empresa ABC', '34612345678');
if ($result['success']) {
    echo "QR Code generado para cliente\n";
    // Mostrar QR en interfaz del CRM
}

// Verificar estados (ejecutar cada 30 segundos)
$crm->checkAllSessions();
?>
```

---

## 📊 **DASHBOARD PARA EL CRM**

### **HTML/JavaScript para mostrar QR:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Gestión WhatsApp - CRM</title>
    <style>
        .qr-container { text-align: center; margin: 20px; }
        .qr-code { max-width: 300px; border: 1px solid #ccc; }
        .status { padding: 10px; margin: 10px; border-radius: 5px; }
        .connected { background: #d4edda; color: #155724; }
        .pending { background: #fff3cd; color: #856404; }
        .error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>Gestión de Sesiones WhatsApp</h1>

    <div id="sessions-container">
        <!-- Las sesiones se cargarán aquí -->
    </div>

    <script>
        class CRMWhatsAppDashboard {
            constructor() {
                this.sessionManager = new WhatsAppSessionManager();
                this.container = document.getElementById('sessions-container');
                this.loadSessions();

                // Actualizar cada 10 segundos
                setInterval(() => this.loadSessions(), 10000);
            }

            async loadSessions() {
                const sessions = await this.sessionManager.listSessions();

                if (sessions.success) {
                    this.renderSessions(sessions.sessions);
                }
            }

            renderSessions(sessions) {
                this.container.innerHTML = '';

                sessions.forEach(session => {
                    const div = document.createElement('div');
                    div.className = `status ${session.status}`;

                    let content = `
                        <h3>📱 ${session.name || session.sessionId}</h3>
                        <p><strong>Estado:</strong> ${this.getStatusText(session.status)}</p>
                        <p><strong>Teléfono:</strong> ${session.phoneNumber || 'No conectado'}</p>
                    `;

                    if (session.status === 'pending') {
                        content += `
                            <div class="qr-container">
                                <p>Escanea este código QR con WhatsApp:</p>
                                <img src="data:image/png;base64,${session.qrCode}" class="qr-code" alt="QR Code">
                                <p><small>El QR expira automáticamente</small></p>
                            </div>
                        `;
                    }

                    if (session.status === 'disconnected') {
                        content += `
                            <button onclick="dashboard.reconnectSession('${session.sessionId}')">
                                🔄 Reconectar
                            </button>
                        `;
                    }

                    div.innerHTML = content;
                    this.container.appendChild(div);
                });
            }

            getStatusText(status) {
                const statusMap = {
                    'pending': '⏳ Esperando conexión',
                    'connected': '✅ Conectado',
                    'disconnected': '❌ Desconectado',
                    'error': '🚨 Error'
                };
                return statusMap[status] || status;
            }

            async reconnectSession(sessionId) {
                const result = await this.sessionManager.connectSession(sessionId);
                if (result.success) {
                    alert('Reconexión iniciada. Se generará un nuevo QR.');
                    this.loadSessions(); // Recargar para mostrar nuevo QR
                } else {
                    alert('Error al reconectar: ' + result.error);
                }
            }

            async createNewSession() {
                const clientName = prompt('Nombre del cliente:');
                const phoneNumber = prompt('Número de teléfono (opcional):');

                if (clientName) {
                    const sessionId = 'cliente_' + Date.now();
                    const result = await this.sessionManager.createSession(sessionId, {
                        name: `WhatsApp ${clientName}`,
                        phoneNumber: phoneNumber
                    });

                    if (result.success) {
                        await this.sessionManager.connectSession(result.sessionId);
                        this.loadSessions();
                        alert('Sesión creada. Escanea el QR para conectar.');
                    } else {
                        alert('Error: ' + result.error);
                    }
                }
            }
        }

        // Inicializar dashboard
        const dashboard = new CRMWhatsAppDashboard();
    </script>

    <button onclick="dashboard.createNewSession()" style="margin: 20px; padding: 10px 20px; font-size: 16px;">
        ➕ Crear Nueva Sesión WhatsApp
    </button>
</body>
</html>
```

---

## ⚠️ **CONSIDERACIONES IMPORTANTES**

### **🔒 Seguridad:**
- **NUNCA** hardcodees las credenciales en el código de producción
- Usa variables de entorno o configuración segura
- Implementa rate limiting en tu CRM
- Valida todos los inputs del usuario

### **📈 Rendimiento:**
- Cachea el token JWT (válido 24h)
- No hagas requests innecesarios al API
- Implementa retry logic para fallos de red
- Usa polling inteligente (no cada segundo)

### **🔄 Gestión de Estados:**
- Una sesión WhatsApp = Un número de teléfono
- No puedes tener el mismo número en múltiples sesiones
- Los QR codes expiran automáticamente
- Monitorea desconexiones y reconecta automáticamente

### **📱 Limitaciones de WhatsApp:**
- Máximo 4 dispositivos conectados por número
- WhatsApp puede desconectar sesiones inactivas
- Los QR codes son de un solo uso
- Respeta los límites de mensajes de WhatsApp

---

## 🆘 **TROUBLESHOOTING**

### **Error: "Session already exists"**
```javascript
// Verificar si existe antes de crear
const sessions = await sessionManager.listSessions();
const existing = sessions.sessions.find(s => s.sessionId === 'mi_sesion');
if (existing) {
  console.log('Sesión ya existe:', existing.sessionId);
} else {
  // Crear nueva sesión
}
```

### **Error: "QR Code expired"**
```javascript
// Regenerar QR
await sessionManager.connectSession(sessionId);
const newQR = await sessionManager.getQRCode(sessionId);
```

### **Error: "Authentication failed"**
```javascript
// Limpiar cache de token
sessionManager.accessToken = null;
sessionManager.tokenExpiry = null;
// El próximo request renovará el token automáticamente
```

---

## 📞 **SOPORTE TÉCNICO**

### **Documentación Relacionada:**
- `CREDENCIALES_CRM_GRUPOATU.md` - Credenciales completas
- `INTEGRACION_EXTERNA_CRM.md` - API técnica completa
- `EJEMPLOS_INTEGRACION_CRM.md` - Más casos de uso

### **Endpoints Clave:**
```
POST /api/sessions              # Crear sesión
POST /api/sessions/{id}/connect # Iniciar conexión
GET  /api/sessions/{id}/qr      # Obtener QR
GET  /api/sessions/{id}/status  # Estado de sesión
GET  /api/sessions              # Listar sesiones
```

### **Estados de Sesión:**
- `pending` - Esperando escaneo de QR
- `connected` - WhatsApp conectado y funcional
- `disconnected` - Desconectado (necesita reconexión)
- `error` - Error (revisar logs)

---

*Guía creada para el programador del CRM de Grupo ATU*
*Integración completa de gestión de sesiones WhatsApp*
*Fecha: 14 de Octubre de 2025*
