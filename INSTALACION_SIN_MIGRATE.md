# 📘 INSTALACIÓN SIN MIGRATE - XAPPIENS WHATSAPP

## 🎯 **OBJETIVO**

Instalar y crear las tablas de DocTypes de **Xappiens WhatsApp** **SIN usar `bench migrate`**.

---

## 🔍 **¿QUÉ HACE MIGRATE?**

Cuando ejecutas `bench migrate`, Frappe realiza:

1. ✅ **Carga DocTypes** desde archivos JSON
2. ✅ **Crea/actualiza tablas** en la base de datos
3. ✅ **Ejecuta patches** (actualizaciones de datos)
4. ✅ **Sincroniza esquemas** de todas las apps
5. ✅ **Rebuilds** varios componentes

---

## 🎯 **¿QUÉ HACE NUESTRO MÉTODO?**

Nuestro script `install_doctypes.py` realiza **SOLO** los pasos 1 y 2:

1. ✅ **Carga DocTypes** usando `frappe.reload_doc()`
2. ✅ **Crea tablas** automáticamente
3. ❌ **NO ejecuta patches** de otras apps
4. ❌ **NO sincroniza** otras apps
5. ❌ **NO rebuilds** innecesarios

---

## 📋 **COMANDOS DISPONIBLES**

### **1. Instalar todos los DocTypes**
```bash
bench --site crm.grupoatu.com execute xappiens_whatsapp.install_doctypes.install_all_doctypes
```

**¿Qué hace?**
- Lee los 17 archivos JSON de DocTypes
- Crea cada DocType en la base de datos
- Crea las 17 tablas correspondientes
- Muestra progreso detallado
- Genera reporte final

**Tiempo estimado:** 30-60 segundos

---

### **2. Verificar instalación**
```bash
bench --site crm.grupoatu.com execute xappiens_whatsapp.install_doctypes.verify_installation
```

**¿Qué hace?**
- Verifica que los 17 DocTypes existan
- Verifica que las 17 tablas existan
- Muestra un reporte completo
- Identifica DocTypes faltantes

**Tiempo estimado:** 5-10 segundos

---

### **3. Desinstalar todos los DocTypes** ⚠️ PELIGROSO
```bash
bench --site crm.grupoatu.com execute xappiens_whatsapp.install_doctypes.uninstall_all_doctypes
```

**¿Qué hace?**
- Elimina los 17 DocTypes
- Elimina las 17 tablas
- **ELIMINA TODOS LOS DATOS**

**⚠️ ADVERTENCIA:** Esta operación es irreversible.

---

## 🔧 **PROCESO TÉCNICO DETALLADO**

### **Función: `frappe.reload_doc()`**

```python
frappe.reload_doc(
    module="xappiens_whatsapp",    # Nombre del módulo
    dt="doctype",                   # Tipo (siempre "doctype")
    dn="whatsapp_session",          # Nombre de carpeta del DocType
    force=True                      # Forzar recarga
)
```

**Lo que hace internamente:**

1. **Lee el archivo JSON**
   ```
   apps/xappiens_whatsapp/xappiens_whatsapp/doctype/whatsapp_session/whatsapp_session.json
   ```

2. **Crea/actualiza el DocType**
   ```sql
   INSERT INTO `tabDocType` (...) VALUES (...)
   ON DUPLICATE KEY UPDATE ...
   ```

3. **Sincroniza la tabla**
   ```sql
   CREATE TABLE IF NOT EXISTS `tabWhatsApp Session` (
       `name` VARCHAR(140) NOT NULL,
       `session_id` VARCHAR(140),
       ...
   )
   ```

4. **Crea índices**
   ```sql
   CREATE INDEX idx_session_id ON `tabWhatsApp Session` (`session_id`);
   CREATE INDEX idx_status ON `tabWhatsApp Session` (`status`);
   ...
   ```

---

## 📊 **ORDEN DE CARGA DE DOCTYPES**

Los DocTypes se cargan en orden de dependencias:

### **Fase 1: Child Tables** (sin dependencias)
```
1. WhatsApp Session User
2. WhatsApp Message Media
3. WhatsApp Group Participant
4. WhatsApp AI Conversation Log
```

### **Fase 2: DocTypes Base** (sin referencias)
```
5. WhatsApp Settings
6. WhatsApp Label
```

### **Fase 3: DocTypes Principales**
```
7.  WhatsApp Session
8.  WhatsApp Contact
9.  WhatsApp Group
10. WhatsApp Conversation
11. WhatsApp Message
12. WhatsApp Media File
```

### **Fase 4: DocTypes Auxiliares**
```
13. WhatsApp AI Agent
14. WhatsApp Analytics
15. WhatsApp Activity Log
16. WhatsApp Webhook Config
17. WhatsApp Webhook Log
```

---

## 🎯 **VENTAJAS DE ESTE MÉTODO**

### **✅ Ventajas:**

1. **Control granular** - Instala solo lo necesario
2. **Más rápido** - No ejecuta migraciones de otras apps
3. **Menos riesgo** - No toca otras apps instaladas
4. **Debugging fácil** - Errores más claros
5. **Reversible** - Fácil de desinstalar

### **⚠️ Consideraciones:**

1. **No ejecuta patches** - Si los hubiera
2. **Orden manual** - Debes respetar dependencias
3. **Sin validaciones extras** - Solo las del DocType

---

## 📝 **EJEMPLO DE SALIDA**

### **Instalación exitosa:**

```
======================================================================
🚀 INSTALACIÓN DE DOCTYPES - XAPPIENS WHATSAPP
======================================================================

Módulo: Xappiens Whatsapp
App: xappiens_whatsapp
Total DocTypes: 17
Sitio: crm.grupoatu.com

----------------------------------------------------------------------

[1/17] Procesando: WhatsApp Session User...
   ✅ WhatsApp Session User - Creado exitosamente
   ✅ Tabla 'tabWhatsApp Session User' creada en la base de datos

[2/17] Procesando: WhatsApp Message Media...
   ✅ WhatsApp Message Media - Creado exitosamente
   ✅ Tabla 'tabWhatsApp Message Media' creada en la base de datos

...

[17/17] Procesando: WhatsApp Webhook Log...
   ✅ WhatsApp Webhook Log - Creado exitosamente
   ✅ Tabla 'tabWhatsApp Webhook Log' creada en la base de datos

======================================================================
📊 RESUMEN DE INSTALACIÓN
======================================================================

✅ DocTypes instalados exitosamente: 17/17
❌ Errores: 0/17

======================================================================
🎉 ¡INSTALACIÓN COMPLETADA CON ÉXITO!

Próximos pasos:
1. Reiniciar bench: bench restart
2. Limpiar cache: bench --site [sitio] clear-cache
3. Acceder a Frappe y buscar 'Xappiens Whatsapp' en el menú
======================================================================
```

---

## 🔍 **VERIFICACIÓN POST-INSTALACIÓN**

### **1. Verificar desde consola:**
```bash
bench --site crm.grupoatu.com console
```

```python
# Listar DocTypes instalados
frappe.get_all("DocType", filters={"module": "Xappiens Whatsapp"})

# Verificar tabla específica
frappe.db.table_exists("tabWhatsApp Session")

# Contar registros (debería ser 0 inicialmente)
frappe.db.count("WhatsApp Session")
```

### **2. Verificar desde interfaz:**
1. Acceder a Frappe desk
2. Buscar "Xappiens Whatsapp" en el buscador
3. Ver los 17 DocTypes listados
4. Intentar crear un registro de prueba

### **3. Verificar desde base de datos:**
```bash
bench --site crm.grupoatu.com mariadb
```

```sql
-- Ver DocTypes instalados
SELECT name, module FROM `tabDocType`
WHERE module = 'Xappiens Whatsapp'
ORDER BY name;

-- Ver tablas creadas
SHOW TABLES LIKE 'tabWhatsApp%';

-- Ver estructura de una tabla
DESCRIBE `tabWhatsApp Session`;

-- Ver índices creados
SHOW INDEX FROM `tabWhatsApp Session`;
```

---

## 🚨 **SOLUCIÓN DE PROBLEMAS**

### **Error: "DocType not found"**
```
Solución: El archivo JSON no existe o está corrupto
Verificar: ls apps/xappiens_whatsapp/xappiens_whatsapp/doctype/
```

### **Error: "Table already exists"**
```
Solución: Usar force=True en reload_doc
O: DROP TABLE `tabNombreDocType` y volver a ejecutar
```

### **Error: "Module not found"**
```
Solución: Verificar que la app esté instalada
Comando: bench --site [sitio] list-apps
```

### **Error: "Permission denied"**
```
Solución: Verificar permisos del usuario
Comando: bench --site [sitio] console
frappe.set_user("Administrator")
```

---

## 📚 **COMPARATIVA: MIGRATE vs RELOAD_DOC**

| Aspecto | `bench migrate` | `reload_doc()` |
|---------|----------------|----------------|
| **Velocidad** | Lento (todas las apps) | Rápido (solo lo necesario) |
| **Scope** | Todas las apps | Solo DocTypes específicos |
| **Patches** | ✅ Ejecuta todos | ❌ No ejecuta |
| **Sincronización** | ✅ Todo el schema | Solo DocTypes cargados |
| **Control** | Automático | Manual |
| **Riesgo** | Alto (toca todo) | Bajo (solo lo que cargas) |
| **Debugging** | Difícil | Fácil |
| **Reversible** | No | Sí |

---

## 🎓 **REFERENCIAS TÉCNICAS**

### **Funciones de Frappe utilizadas:**

1. **`frappe.reload_doc(module, dt, dn, force=True)`**
   - Documentación: https://frappeframework.com/docs/user/en/api/reload-doc
   - Ubicación: `frappe/modules/__init__.py`

2. **`frappe.db.exists(doctype, name)`**
   - Verifica si un documento existe
   - Ubicación: `frappe/database/database.py`

3. **`frappe.db.table_exists(table_name)`**
   - Verifica si una tabla existe en la BD
   - Ubicación: `frappe/database/database.py`

4. **`frappe.db.commit()`**
   - Confirma transacción en la BD
   - Ubicación: `frappe/database/database.py`

---

## ✅ **CHECKLIST DE INSTALACIÓN**

- [ ] App instalada: `bench --site [sitio] install-app xappiens_whatsapp`
- [ ] Build ejecutado: `bench build`
- [ ] Script de instalación creado: `install_doctypes.py`
- [ ] Documentación revisada: `INSTALACION_SIN_MIGRATE.md`
- [ ] Ejecutar instalación: `bench execute ...install_all_doctypes`
- [ ] Verificar instalación: `bench execute ...verify_installation`
- [ ] Limpiar cache: `bench --site [sitio] clear-cache`
- [ ] Reiniciar bench: `bench restart`
- [ ] Verificar en interfaz: Buscar "Xappiens Whatsapp"
- [ ] Crear registro de prueba: WhatsApp Session

---

## 🎉 **CONCLUSIÓN**

Este método te permite:
- ✅ Instalar DocTypes sin afectar otras apps
- ✅ Control total sobre el proceso
- ✅ Fácil debugging de errores
- ✅ Instalación más rápida y segura
- ✅ Reversible en cualquier momento

---

**Versión:** 1.0.0
**Fecha:** 2025-10-04
**Autor:** Xappiens
**App:** xappiens_whatsapp

