# 🔍 Análisis y Correcciones - Conexión de Sesiones WhatsApp

**Fecha:** 2025-11-06
**Problema:** Las nuevas sesiones de WhatsApp no se conectan correctamente - Error al obtener QR

---

## 🚨 PROBLEMAS IDENTIFICADOS

### **Problema 1: `session_db_id` no se guardaba al crear sesión**
**Ubicación:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/session.py` - función `create_session()`

**Descripción:**
- Cuando se creaba una nueva sesión, el código obtenía el `session_db_id` (ID numérico) del servidor de Baileys
- Sin embargo, este ID **NO se guardaba** en el documento de Frappe
- Solo se guardaban: `session_id`, `session_name`, `description`, `status`, `is_connected`, `is_active`

**Impacto:**
- Sin `session_db_id`, las llamadas posteriores al servidor fallaban porque el endpoint requiere el ID numérico

---

### **Problema 2: `get_qr_code()` usaba `session_id` en lugar de `session_db_id`**
**Ubicación:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/session.py` - función `get_qr_code()`

**Descripción:**
- La función recibía `session_id` (string) como parámetro
- Lo usaba directamente en la URL del endpoint: `/api/sessions/{session_id}/qr`
- **PERO** el endpoint del servidor de Baileys requiere el `session_db_id` (ID numérico), no el string

**Impacto:**
- Error 404 o 500 al intentar obtener el QR
- El servidor no encontraba la sesión porque se usaba el ID incorrecto

---

### **Problema 3: `disconnect_session()` también usaba `session_id` incorrectamente**
**Ubicación:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/session.py` - función `disconnect_session()`

**Descripción:**
- Similar al problema anterior, usaba `session_id` directamente en la URL
- El endpoint requiere `session_db_id`

**Impacto:**
- No se podía desconectar sesiones correctamente

---

### **Problema 4: `get_session_status()` no actualizaba `session_db_id` si venía del servidor**
**Ubicación:** `apps/xappiens_whatsapp/xappiens_whatsapp/api/session.py` - función `get_session_status()`

**Descripción:**
- La función ya usaba `session_db_id` correctamente para llamar al endpoint
- Pero si el servidor devolvía el ID en la respuesta y no estaba guardado localmente, no se actualizaba

**Impacto:**
- Sesiones existentes sin `session_db_id` no se podían usar correctamente

---

## ✅ CORRECCIONES APLICADAS

### **Corrección 1: Guardar `session_db_id` al crear sesión**
```python
# ANTES:
session_doc = frappe.get_doc({
    "doctype": "WhatsApp Session",
    "session_id": session_id,
    "session_name": session_name,
    # ... otros campos ...
    # ❌ FALTABA: session_db_id
})

# DESPUÉS:
session_doc = frappe.get_doc({
    "doctype": "WhatsApp Session",
    "session_id": session_id,
    "session_name": session_name,
    # ... otros campos ...
    "session_db_id": session_id_created  # ✅ CRÍTICO: Guardar el ID numérico
})
```

**Mejora adicional:**
- Ahora también actualiza sesiones existentes si no tienen `session_db_id`
- Manejo mejorado de errores con logging

---

### **Corrección 2: Resolver `session_db_id` en `get_qr_code()`**
```python
# ANTES:
response = requests.get(
    f"{api_base_url}/api/sessions/{session_id}/qr",  # ❌ Usa session_id directamente
    ...
)

# DESPUÉS:
# ✅ Resolver session_db_id desde session_id
session_doc = _resolve_session_doc(session_id)
session_identifier = session_doc.session_db_id if session_doc.session_db_id else session_doc.session_id

response = requests.get(
    f"{api_base_url}/api/sessions/{session_identifier}/qr",  # ✅ Usa session_db_id
    ...
)
```

---

### **Corrección 3: Resolver `session_db_id` en `disconnect_session()`**
```python
# ANTES:
response = requests.delete(
    f"{api_base_url}/api/sessions/{session_id}",  # ❌ Usa session_id directamente
    ...
)

# DESPUÉS:
# ✅ Resolver session_db_id desde session_id
session_doc = _resolve_session_doc(session_id)
session_identifier = session_doc.session_db_id if session_doc.session_db_id else session_doc.session_id

response = requests.delete(
    f"{api_base_url}/api/sessions/{session_identifier}",  # ✅ Usa session_db_id
    headers={
        "X-API-Key": settings.get('api_key'),  # ✅ También agregado header de autenticación
        ...
    }
)
```

---

### **Corrección 4: Actualizar `session_db_id` en `get_session_status()`**
```python
# ANTES:
session_doc.status = frappe_status
session_doc.is_connected = 1 if data.get('isConnected') else 0
# ❌ No se actualizaba session_db_id si venía del servidor

# DESPUÉS:
# ✅ Actualizar session_db_id si viene del servidor y no está guardado
server_session_id = data.get('id')
if server_session_id and not session_doc.session_db_id:
    session_doc.session_db_id = server_session_id

session_doc.status = frappe_status
session_doc.is_connected = 1 if data.get('isConnected') else 0
```

---

## 📋 RESUMEN DE CAMBIOS

### **Archivos Modificados:**
1. `apps/xappiens_whatsapp/xappiens_whatsapp/api/session.py`

### **Funciones Corregidas:**
1. ✅ `create_session()` - Guarda `session_db_id` y actualiza sesiones existentes
2. ✅ `get_qr_code()` - Resuelve `session_db_id` antes de llamar al endpoint
3. ✅ `disconnect_session()` - Resuelve `session_db_id` y agrega autenticación
4. ✅ `get_session_status()` - Actualiza `session_db_id` si viene del servidor

---

## 🧪 PRUEBAS RECOMENDADAS

### **1. Crear Nueva Sesión**
```python
# Desde el CRM:
1. Ir a WhatsApp Session > Nuevo
2. Llenar nombre y descripción
3. Hacer clic en "Crear Sesión"
4. Verificar que:
   - La sesión se crea correctamente
   - El campo `session_db_id` se llena con el ID numérico
   - El QR se muestra (si está disponible)
```

### **2. Obtener QR de Sesión Existente**
```python
# Desde el CRM:
1. Abrir una sesión existente
2. Hacer clic en "Ver QR"
3. Verificar que:
   - Se obtiene el QR correctamente
   - No hay errores 404 o 500
```

### **3. Verificar Estado de Sesión**
```python
# Desde el CRM:
1. Abrir una sesión
2. Hacer clic en "Estado"
3. Verificar que:
   - El estado se actualiza correctamente
   - El `session_db_id` se guarda si no estaba presente
```

### **4. Desconectar Sesión**
```python
# Desde el CRM:
1. Abrir una sesión conectada
2. Hacer clic en "Desconectar"
3. Verificar que:
   - La sesión se desconecta correctamente
   - El estado se actualiza en Frappe
```

---

## 🔍 DIAGNÓSTICO ADICIONAL

Si después de estas correcciones el problema persiste, verificar:

### **1. Verificar que el servidor de Baileys esté funcionando**
```bash
# Conectarse por SSH al servidor de WhatsApp
ssh usuario@servidor-whatsapp

# Verificar logs del servidor
tail -f /ruta/logs/baileys.log

# Verificar que el proceso esté corriendo
ps aux | grep baileys
```

### **2. Verificar conectividad**
```bash
# Desde el servidor del CRM
curl -X GET "https://api.inbox-hub.com/api/sessions" \
  -H "X-API-Key: tu_api_key"

# Debe devolver lista de sesiones
```

### **3. Verificar configuración**
- ✅ API Key configurada correctamente en WhatsApp Settings
- ✅ API Base URL configurada correctamente
- ✅ Webhook URL configurada (si aplica)

### **4. Verificar sesiones existentes**
```python
# Desde la consola de Frappe
import frappe
sessions = frappe.get_all("WhatsApp Session", fields=["name", "session_id", "session_db_id"])
for s in sessions:
    print(f"{s.name}: session_id={s.session_id}, session_db_id={s.session_db_id}")
```

Si hay sesiones sin `session_db_id`, se pueden actualizar ejecutando `get_session_status()` para cada una.

---

## 📝 NOTAS IMPORTANTES

1. **Compatibilidad hacia atrás:** Las correcciones mantienen compatibilidad con sesiones existentes usando fallback a `session_id` si `session_db_id` no está disponible.

2. **Sesiones antiguas:** Las sesiones creadas antes de estas correcciones pueden no tener `session_db_id`. Se actualizarán automáticamente cuando se llame a `get_session_status()` o se pueden actualizar manualmente.

3. **Endpoint del servidor:** El servidor de Baileys requiere el ID numérico (`session_db_id`) para todos los endpoints de sesión. El `session_id` (string) solo se usa para identificación interna en Frappe.

---

## 🎯 CONCLUSIÓN

Los problemas principales eran:
1. ❌ No se guardaba `session_db_id` al crear sesiones
2. ❌ Se usaba `session_id` (string) en lugar de `session_db_id` (numérico) en los endpoints

**Todas las correcciones han sido aplicadas y el código ahora:**
- ✅ Guarda `session_db_id` correctamente
- ✅ Resuelve `session_db_id` antes de llamar a los endpoints
- ✅ Actualiza `session_db_id` si viene del servidor
- ✅ Maneja sesiones existentes sin `session_db_id`

**Próximos pasos:**
1. Probar el flujo completo de creación de sesión
2. Verificar que el QR se obtiene correctamente
3. Si persisten problemas, revisar logs del servidor de Baileys

