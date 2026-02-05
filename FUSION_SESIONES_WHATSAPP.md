# 🔄 Fusión de Sesiones de WhatsApp

## 📋 **Descripción General**

La funcionalidad de fusión de sesiones permite combinar dos sesiones de WhatsApp en una sola, transfiriendo todos los datos relacionados (contactos, conversaciones, mensajes, etc.) de una sesión origen a una sesión destino.

Esta funcionalidad es útil cuando:
- Tienes sesiones duplicadas del mismo número de teléfono
- Quieres consolidar datos de múltiples sesiones de prueba
- Necesitas limpiar sesiones obsoletas manteniendo sus datos

## 🚀 **Cómo Usar la Funcionalidad**

### **Método 1: Desde la Vista de Lista**

1. Ve a **WhatsApp Session** → **Lista**
2. Haz clic en el menú **⋮** → **Fusionar Sesiones**
3. Selecciona la **Sesión Origen** (será eliminada)
4. Selecciona la **Sesión Destino** (recibirá los datos)
5. Revisa la **Vista Previa** automática
6. Marca la casilla de confirmación
7. Haz clic en **Fusionar Sesiones**

### **Método 2: Desde un Formulario Individual**

1. Abre cualquier **WhatsApp Session**
2. Haz clic en **Acciones** → **Fusionar con Otra Sesión**
3. La sesión actual se pre-selecciona como origen
4. Selecciona la **Sesión Destino**
5. Sigue los pasos 5-7 del método anterior

### **Método 3: Usando la Funcionalidad de Renombrado de Frappe**

1. Abre la **Sesión Origen** que quieres fusionar
2. Haz clic en **Menú** → **Renombrar**
3. Escribe el **nombre exacto** de la sesión destino
4. **Marca la casilla "Fusionar con existente"**
5. Haz clic en **Renombrar**

## 📊 **Vista Previa de la Fusión**

Antes de ejecutar la fusión, el sistema muestra:

### **Información de las Sesiones:**
- **Sesión Origen**: Nombre, estado, número de teléfono
- **Sesión Destino**: Nombre, estado, número de teléfono

### **Estadísticas de Datos:**
- 👥 **Contactos** a transferir
- 💬 **Conversaciones** a transferir
- 📨 **Mensajes** a transferir
- 📎 **Archivos Media** a transferir

### **Conflictos Detectados:**
- **Contactos duplicados** (mismo número de teléfono)
- **Conversaciones duplicadas** (mismo chat_id)

## ⚙️ **Proceso de Fusión**

### **1. Validaciones Previas**
```
✅ Ambas sesiones existen
✅ No son la misma sesión
✅ Sesión origen no está conectada activamente
⚠️  Advertencia si sesión destino está conectada
```

### **2. Transferencia de Datos**
```
📊 Estadísticas numéricas se suman
📞 Contactos se transfieren (duplicados se fusionan)
💬 Conversaciones se transfieren (duplicadas se fusionan)
📨 Mensajes se reasignan a nuevas conversaciones
📎 Archivos media se transfieren
📈 Analytics y logs se transfieren
👥 Usuarios asignados se combinan
```

### **3. Resolución de Conflictos**

#### **Contactos Duplicados:**
- Se mantiene el contacto de la sesión destino
- Los mensajes del contacto origen se reasignan
- El contacto duplicado se elimina

#### **Conversaciones Duplicadas:**
- Se mantiene la conversación de la sesión destino
- Los mensajes se transfieren a la conversación destino
- Los contadores se suman (total_messages, unread_count)
- Se mantiene el último mensaje más reciente
- La conversación duplicada se elimina

### **4. Finalización**
```
🗑️  Sesión origen se elimina
💾 Sesión destino se actualiza con nuevos totales
📝 Se agrega comentario de fusión
🔄 Cache se limpia
✅ Confirmación al usuario
```

## 🛡️ **Validaciones y Restricciones**

### **Validaciones Automáticas:**
- ❌ No se puede fusionar una sesión consigo misma
- ❌ No se puede fusionar si la sesión origen está conectada
- ❌ No se pueden fusionar sesiones con el mismo `session_id`
- ✅ Ambas sesiones deben existir

### **Advertencias:**
- ⚠️ Si la sesión destino está conectada (se permite pero se advierte)
- ⚠️ Operación irreversible

## 📁 **Archivos Técnicos**

### **Backend:**
```
apps/xappiens_whatsapp/xappiens_whatsapp/doctype/whatsapp_session/
├── whatsapp_session.py              # Hooks before_rename/after_rename
├── whatsapp_session_merge.py        # Lógica de fusión
└── whatsapp_session.json           # Configuración DocType
```

### **Frontend:**
```
apps/xappiens_whatsapp/xappiens_whatsapp/public/js/
├── whatsapp_session.js              # Funcionalidad base
└── whatsapp_session_merge.js        # UI de fusión
```

## 🔧 **APIs Disponibles**

### **Vista Previa de Fusión:**
```python
frappe.call({
    method: 'xappiens_whatsapp...get_session_merge_preview',
    args: {old_session: 'SES001', new_session: 'SES002'}
})
```

### **Validar Fusión:**
```python
frappe.call({
    method: 'xappiens_whatsapp...validate_session_merge',
    args: {old_session: 'SES001', new_session: 'SES002'}
})
```

### **Ejecutar Fusión:**
```python
frappe.call({
    method: 'xappiens_whatsapp...execute_session_merge',
    args: {old_session: 'SES001', new_session: 'SES002'}
})
```

## 🚨 **Consideraciones Importantes**

### **Antes de Fusionar:**
1. **Haz un backup** de la base de datos
2. **Desconecta** la sesión origen si está activa
3. **Revisa** la vista previa cuidadosamente
4. **Confirma** que entiendes que es irreversible

### **Durante la Fusión:**
- El proceso puede tomar **varios minutos** con muchos datos
- **No interrumpas** el proceso una vez iniciado
- La sesión destino puede **seguir funcionando** normalmente

### **Después de la Fusión:**
- La sesión origen **ya no existe**
- Todos los datos están en la sesión destino
- Los **IDs internos** de mensajes/conversaciones pueden cambiar
- Las **estadísticas** se actualizan automáticamente

## 🔍 **Troubleshooting**

### **Errores Comunes:**

**"Sesión está conectada"**
- Desconecta la sesión origen antes de fusionar

**"Session ID duplicado"**
- Las sesiones tienen el mismo session_id, no se pueden fusionar

**"Timeout durante fusión"**
- Muchos datos, ejecutar en horario de menor carga

**"Error de permisos"**
- Verificar permisos de usuario en WhatsApp Session

### **Recuperación:**
Si algo sale mal durante la fusión:
1. Restaurar desde backup de base de datos
2. Revisar logs de error en Frappe
3. Contactar soporte técnico

## 📈 **Beneficios**

✅ **Consolidación** de datos dispersos
✅ **Limpieza** de sesiones duplicadas
✅ **Mantenimiento** simplificado
✅ **Resolución automática** de conflictos
✅ **Preservación** de historial completo
✅ **Interfaz intuitiva** y segura

---

> **⚠️ Importante**: Esta funcionalidad modifica datos permanentemente. Siempre haz un backup antes de fusionar sesiones importantes.
