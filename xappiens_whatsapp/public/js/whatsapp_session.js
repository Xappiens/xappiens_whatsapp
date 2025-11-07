/**
 * WhatsApp Session Management
 * Asistente para conectar nuevas sesiones de WhatsApp
 */

frappe.ui.form.on('WhatsApp Session', {
    refresh: function(frm) {
        // Agregar botones personalizados
        if (frm.doc.status === 'disconnected' || !frm.doc.status) {
            frm.add_custom_button(__('Conectar Sesión'), function() {
                show_connection_wizard(frm);
            }, __('Acciones'));
        } else if (frm.doc.status === 'connected') {
            frm.add_custom_button(__('Desconectar'), function() {
                disconnect_session(frm);
            }, __('Acciones'));

            frm.add_custom_button(__('Ver QR'), function() {
                show_qr_code(frm);
            }, __('Acciones'));
        }

        frm.add_custom_button(__('Estado'), function() {
            check_session_status(frm);
        }, __('Acciones'));
    }
});

// Vista de lista - Botones adicionales
frappe.listview_settings['WhatsApp Session'] = frappe.listview_settings['WhatsApp Session'] || {};

// Extender configuración existente o crear nueva
const existing_listview_onload = frappe.listview_settings['WhatsApp Session'].onload;
const existing_get_actions_menu_items = frappe.listview_settings['WhatsApp Session'].get_actions_menu_items;

frappe.listview_settings['WhatsApp Session'].onload = function(listview) {
    // Ejecutar onload existente si existe
    if (existing_listview_onload) {
        existing_listview_onload.call(this, listview);
    }

    // Botón para conectar nueva sesión
    listview.page.add_menu_item(__('Conectar Nueva Sesión'), function() {
        show_connection_wizard();
    });
};

// Agregar opción al menú de acciones masivas
frappe.listview_settings['WhatsApp Session'].get_actions_menu_items = function(listview) {
    const items = [];

    // Ejecutar get_actions_menu_items existente si existe
    if (existing_get_actions_menu_items) {
        items.push(...existing_get_actions_menu_items(listview));
    }

    // Agregar opción para eliminar sesión con documentos relacionados
    items.push({
        label: __('Eliminar Sesión y Documentos Relacionados'),
        action: function() {
            const selected = listview.get_checked_items(true);
            if (selected.length === 0) {
                frappe.msgprint({
                    title: __('Selecciona una sesión'),
                    message: __('Por favor, selecciona al menos una sesión para eliminar.'),
                    indicator: 'orange'
                });
                return;
            }

            if (selected.length > 1) {
                frappe.msgprint({
                    title: __('Solo una sesión a la vez'),
                    message: __('Por favor, selecciona solo una sesión para eliminar con sus documentos relacionados.'),
                    indicator: 'orange'
                });
                return;
            }

            const session_name = selected[0];

            // Obtener estadísticas antes de eliminar
            frappe.call({
                method: 'xappiens_whatsapp.xappiens_whatsapp.doctype.whatsapp_session.whatsapp_session.get_delete_stats',
                args: {
                    session_name: session_name
                },
                freeze: true,
                freeze_message: __('Obteniendo información de la sesión...'),
                callback: function(r) {
                    if (r.message && r.message.stats) {
                        const stats = r.message.stats;
                        let statsMessage = __('<strong>Se eliminarán los siguientes documentos:</strong><br><br>');
                        statsMessage += `• ${stats.contacts || 0} ${__('contactos')}<br>`;
                        statsMessage += `• ${stats.conversations || 0} ${__('conversaciones')}<br>`;
                        statsMessage += `• ${stats.messages || 0} ${__('mensajes')}<br>`;
                        statsMessage += `• ${stats.groups || 0} ${__('grupos')}<br>`;
                        statsMessage += `• ${stats.media_files || 0} ${__('archivos multimedia')}<br>`;
                        statsMessage += `• ${stats.analytics || 0} ${__('registros de analytics')}<br>`;
                        statsMessage += `• ${stats.activity_logs || 0} ${__('registros de actividad')}<br>`;
                        statsMessage += `• ${stats.webhook_logs || 0} ${__('registros de webhooks')}<br>`;
                        statsMessage += `• ${stats.labels || 0} ${__('etiquetas')}<br><br>`;
                        statsMessage += __('<strong>Esta acción no se puede deshacer.</strong>');

                        frappe.confirm(
                            statsMessage,
                            function() {
                                // Usuario confirmó
                                frappe.call({
                                    method: 'xappiens_whatsapp.xappiens_whatsapp.doctype.whatsapp_session.whatsapp_session.delete_session_with_related_docs',
                                    args: {
                                        session_name: session_name
                                    },
                                    freeze: true,
                                    freeze_message: __('Eliminando sesión y documentos relacionados...'),
                                    callback: function(r) {
                                        if (r.message && r.message.success) {
                                            frappe.show_alert({
                                                message: __('Sesión y documentos relacionados eliminados exitosamente'),
                                                indicator: 'green'
                                            }, 5);
                                            listview.refresh();
                                        } else {
                                            frappe.msgprint({
                                                title: __('Error'),
                                                message: r.message?.error || __('No se pudo eliminar la sesión'),
                                                indicator: 'red'
                                            });
                                        }
                                    },
                                    error: function(r) {
                                        frappe.msgprint({
                                            title: __('Error'),
                                            message: __('Ocurrió un error al eliminar la sesión. Revisa los logs para más detalles.'),
                                            indicator: 'red'
                                        });
                                    }
                                });
                            },
                            function() {
                                // Usuario canceló
                            }
                        );
                    } else {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('No se pudo obtener la información de la sesión'),
                            indicator: 'red'
                        });
                    }
                },
                error: function(r) {
                    frappe.msgprint({
                        title: __('Error'),
                        message: __('Ocurrió un error al obtener la información de la sesión'),
                        indicator: 'red'
                    });
                }
            });
        },
        standard: true
    });

    return items;
};

/**
 * Probar conexión con WhatsApp
 */
function test_whatsapp_connection(dialog) {
    const status_div = dialog.fields_dict.connection_status.$wrapper.find('#connection-status');

    status_div.html('<i class="fa fa-spinner fa-spin"></i> Probando conexión...');

    frappe.call({
        method: 'xappiens_whatsapp.api.session.test_connection',
                callback: function(r) {
                    // MOSTRAR DEBUG EN CONSOLA
                    console.log('🔍 DEBUG - Respuesta completa de test_connection:', r);
                    if (r.message && r.message.debug) {
                        console.log('🔍 DEBUG - Información detallada:', r.message.debug);
                    }

                    if (r.message && r.message.success) {
                        status_div.html(`
                            <i class="fa fa-check-circle text-success"></i> ${r.message.message}
                            <div class="alert alert-success mt-2">
                                <strong>¡Conexión exitosa!</strong> El servidor de WhatsApp está funcionando correctamente.
                            </div>
                        `);
                    } else {
                        const errorMsg = (r.message && r.message.error) ? r.message.error : 'Error desconocido';
                        status_div.html(`
                            <i class="fa fa-times text-danger"></i> Error: ${errorMsg}
                            <div class="alert alert-danger mt-2">
                                <strong>Problema de conexión:</strong> ${errorMsg}
                            </div>
                        `);
                    }
                },
        error: function(err) {
            console.log('❌ DEBUG - Error de conexión en test_connection:', err);
            status_div.html(`
                <i class="fa fa-times text-danger"></i> Error de conexión: ${err.message}
            `);
        }
    });
}

/**
 * Mostrar asistente de conexión
 */
function show_connection_wizard(frm = null) {
    let d = new frappe.ui.Dialog({
        title: __('Conectar Nueva Sesión WhatsApp'),
        size: 'large',
        fields: [
            {
                fieldtype: 'Section Break',
                label: __('Información de la Sesión')
            },
            {
                fieldname: 'session_name',
                fieldtype: 'Data',
                label: __('Nombre de la Sesión'),
                reqd: 1,
                placeholder: 'Ej: Ventas Principal, Soporte, Marketing...',
            change: function() {
                // Generar ID automáticamente basado en el nombre + timestamp + random
                const sessionName = this.get_value();
                if (sessionName) {
                    const timestamp = Date.now().toString(36); // Base36 timestamp
                    const random = Math.random().toString(36).substring(2, 8); // 6 chars random

                    const sessionId = sessionName
                        .toLowerCase()
                        .replace(/[^a-z0-9\s]/g, '') // Remover caracteres especiales
                        .replace(/\s+/g, '_') // Reemplazar espacios con guiones bajos
                        .substring(0, 20) + '_' + timestamp + '_' + random; // Limitar longitud base + sufijos

                    d.fields_dict.session_id.set_value(sessionId);
                }
            }
            },
            {
                fieldname: 'session_id',
                fieldtype: 'Data',
                label: __('ID de Sesión (Auto-generado)'),
                reqd: 1,
                read_only: 1,
                description: __('ID generado automáticamente basado en el nombre')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'description',
                fieldtype: 'Small Text',
                label: __('Descripción'),
                placeholder: 'Descripción opcional de la sesión...'
            },
            {
                fieldtype: 'Section Break',
                label: __('Proceso de Conexión')
            },
            {
                fieldname: 'connection_status',
                fieldtype: 'HTML',
                options: '<div id="connection-status" class="text-center"><i class="fa fa-spinner fa-spin"></i> Preparando conexión...</div>'
            },
            {
                fieldname: 'qr_code_container',
                fieldtype: 'HTML',
                options: '<div id="qr-code-container" class="text-center" style="display: none;"></div>'
            },
            {
                fieldname: 'instructions',
                fieldtype: 'HTML',
                options: get_connection_instructions()
            }
        ],
        primary_action_label: __('Crear Sesión'),
        primary_action: function(values) {
            create_new_session(values, d);
        },
        secondary_action_label: __('Probar Conexión'),
        secondary_action: function() {
            test_whatsapp_connection(d);
        }
    });

    // Generar ID único inicial
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    const initialId = 'sesion_' + timestamp + '_' + random;
    d.fields_dict.session_id.set_value(initialId);

    d.show();
}

/**
 * Crear nueva sesión en el servidor
 */
function create_new_session(values, dialog) {
    const status_div = dialog.fields_dict.connection_status.$wrapper.find('#connection-status');
    const qr_container = dialog.fields_dict.qr_code_container.$wrapper.find('#qr-code-container');

    // Mostrar estado de creación
    status_div.html('<i class="fa fa-spinner fa-spin"></i> Creando sesión en el servidor...');

    frappe.call({
        method: 'xappiens_whatsapp.api.session.create_session',
        args: {
            session_id: values.session_id,
            session_name: values.session_name,
            description: values.description || ''
        },
        callback: function(r) {
            // MOSTRAR DEBUG EN CONSOLA
            console.log('🔍 DEBUG - Respuesta completa de create_session:', r);
            if (r.message) {
                console.log('🔍 DEBUG - Mensaje:', r.message);
                if (r.message.debug) {
                    console.log('🔍 DEBUG - Información detallada:', r.message.debug);
                    // Mostrar campos específicos importantes
                    console.log('🔍 DEBUG - Connect Status:', r.message.debug.connect_response_status);
                    console.log('🔍 DEBUG - Connect Exception:', r.message.debug.connect_exception);
                    console.log('🔍 DEBUG - Connect Endpoint:', r.message.debug.connect_endpoint);
                }
            }

            if (r.message && r.message.success) {
                // Mostrar mensaje con información del estado del QR
                let statusMessage = '<i class="fa fa-check text-success"></i> ' + (r.message.message || 'Sesión creada exitosamente');

                if (r.message.qr_error) {
                    statusMessage += '<br><small class="text-warning">⚠️ ' + r.message.qr_error + '</small>';
                }

                status_div.html(statusMessage);

                // Mostrar QR code si está disponible
                if (r.message.qr_code) {
                    show_qr_in_dialog(r.message.qr_code, qr_container);
                } else {
                    // Si no hay QR, mostrar mensaje de espera con información adicional
                    let waitMessage = 'El código QR se generará automáticamente en unos segundos';
                    if (r.message.qr_error) {
                        if (r.message.qr_error.includes('QR_GENERATION_ERROR')) {
                            waitMessage = 'El servidor de Baileys está generando el QR. Esto puede tardar unos momentos.';
                        } else {
                            waitMessage = 'Esperando que el servidor genere el QR. ' + r.message.qr_error;
                        }
                    }

                    qr_container.html(`
                        <div class="qr-code-wrapper">
                            <h5>Esperando código QR...</h5>
                            <div class="text-center">
                                <i class="fa fa-spinner fa-spin fa-2x text-warning"></i>
                            </div>
                            <p class="text-muted small mt-2">
                                ${waitMessage}
                            </p>
                            <div class="alert alert-info small mt-2">
                                <i class="fa fa-info-circle"></i>
                                <strong>Nota:</strong> El sistema seguirá intentando obtener el QR automáticamente.
                                Si después de 2 minutos no aparece, verifica los logs del servidor de Baileys.
                            </div>
                        </div>
                    `);
                    qr_container.show();
                }

                // Iniciar monitoreo de estado
                monitor_connection_status(values.session_id, status_div, dialog);

            } else {
                const errorMsg = (r.message && r.message.error) ? r.message.error : 'Error desconocido';
                console.log('❌ DEBUG - Error en create_session:', errorMsg);
                status_div.html(`<i class="fa fa-times text-danger"></i> Error: ${errorMsg}`);

                // Mostrar detalles del error
                if (errorMsg.includes('Token') || errorMsg.includes('token')) {
                    status_div.append(`
                        <div class="alert alert-warning mt-2">
                            <strong>Problema de autenticación:</strong> Verifica que las credenciales en WhatsApp Settings sean correctas.
            </div>
                    `);
                } else if (errorMsg.includes('Datos de entrada inválidos') || errorMsg.includes('VALIDATION_ERROR')) {
                    status_div.append(`
                        <div class="alert alert-danger mt-2">
                            <strong>Error de validación:</strong> Los datos enviados no cumplen con los requisitos del servidor.
                            <br><small>Verifica que el ID de sesión tenga entre 3-100 caracteres alfanuméricos, guiones bajos o guiones.</small>
                    </div>
                    `);
                }
            }
        },
        error: function(err) {
            console.log('❌ DEBUG - Error de conexión en create_session:', err);
            status_div.html(`<i class="fa fa-times text-danger"></i> Error de conexión: ${err.message}`);

            // Mostrar ayuda para errores de conexión
            status_div.append(`
                <div class="alert alert-info mt-2">
                    <strong>Sugerencias:</strong>
                    <ul class="mb-0">
                        <li>Verifica que el servidor de WhatsApp esté funcionando</li>
                        <li>Revisa la configuración de red</li>
                        <li>Intenta nuevamente en unos momentos</li>
                    </ul>
                </div>
            `);
        }
    });
}

/**
 * Mostrar QR code en el modal
 */
function show_qr_in_dialog(qr_code, container) {
    container.html(`
        <div class="qr-code-wrapper">
            <h5>Escanea este código QR con WhatsApp</h5>
            <div class="qr-code-image">
                <img src="data:image/png;base64,${qr_code}"
                     alt="QR Code"
                     style="max-width: 300px; border: 1px solid #ddd; border-radius: 8px;">
            </div>
            <p class="text-muted small mt-2">
                <i class="fa fa-info-circle"></i>
                Abre WhatsApp > Configuración > Dispositivos vinculados > Vincular un dispositivo
            </p>
                                        </div>
    `);
    container.show();
}

/**
 * Monitorear estado de conexión
 */
function monitor_connection_status(session_id, status_div, dialog) {
    let qr_attempts = 0;
    const max_qr_attempts = 10; // Reducido para evitar rate limiting
    let qr_check_interval = null;
    let qr_found = false;
    let is_connected = false;
    let qr_rate_limited = false; // Flag para detectar rate limiting en QR
    let qr_delay = 5000; // Delay inicial para obtener QR

    // Función para cerrar el modal cuando se conecta
    const handle_connection_success = function() {
        if (is_connected) return; // Ya se procesó

        is_connected = true;
        status_div.html('<i class="fa fa-check-circle text-success"></i> ¡Conectado exitosamente!');

        // Limpiar intervalos
        if (qr_check_interval) clearInterval(qr_check_interval);

        // Cerrar modal después de 2 segundos
        setTimeout(() => {
            dialog.hide();
            frappe.show_alert({
                message: __('Sesión conectada exitosamente'),
                indicator: 'green'
            });
            frappe.set_route('List', 'WhatsApp Session');
        }, 2000);
    };

    // Función para intentar obtener QR
    const try_get_qr = function() {
        if (qr_found || is_connected || qr_rate_limited) return; // Ya se encontró el QR, está conectado, o hay rate limiting

        const qr_container = dialog.fields_dict.qr_code_container.$wrapper.find('#qr-code-container');

        // Solo intentar si no hay QR mostrado aún
        if (!qr_container.find('img').length && qr_attempts < max_qr_attempts) {
            qr_attempts++;
            get_qr_code_for_session(session_id, dialog, function(rate_limited) {
                if (rate_limited) {
                    qr_rate_limited = true;
                    qr_delay = Math.min(qr_delay * 2, 30000); // Aumentar delay hasta 30 segundos
                    console.log(`⏸️ Rate limiting detectado en QR. Aumentando delay a ${qr_delay/1000}s`);

                    // Reiniciar intervalo con nuevo delay
                    if (qr_check_interval) clearInterval(qr_check_interval);
                    setTimeout(() => {
                        qr_rate_limited = false; // Reintentar después del delay
                        qr_check_interval = setInterval(try_get_qr, qr_delay);
                    }, qr_delay);
                } else if (qr_container.find('img').length) {
                    qr_found = true;
                    if (qr_check_interval) {
                        clearInterval(qr_check_interval);
                        qr_check_interval = null;
                    }
                }
            });

            // Verificar si se encontró el QR después de la llamada
            setTimeout(() => {
                if (qr_container.find('img').length) {
                    qr_found = true;
                    if (qr_check_interval) {
                        clearInterval(qr_check_interval);
                        qr_check_interval = null;
                    }
                }
            }, 500);
        }
    };

    // Intentar obtener QR inmediatamente y luego cada 5 segundos (reducido para evitar rate limiting)
    try_get_qr();
    qr_check_interval = setInterval(try_get_qr, qr_delay); // Reducido de 2 a 5 segundos

    // Escuchar eventos realtime del webhook cuando se conecta
    console.log('🔔 Registrando listeners de eventos realtime para sesión:', session_id);

    frappe.realtime.on('whatsapp_session_status', function(data) {
        console.log('📡 Evento realtime whatsapp_session_status recibido:', data);
        // Priorizar isConnected sobre status para determinar conexión real
        const isConnected = data.isConnected === true || data.connected === true;
        if (data.session && isConnected) {
            console.log('🔍 Verificando si es la sesión correcta...');
            // Verificar que sea la sesión correcta
            frappe.call({
                method: 'xappiens_whatsapp.api.session.get_session_status',
                args: { session_id: session_id },
                callback: function(r) {
                    console.log('📊 Estado de sesión después de evento:', r.message);
                    if (r.message && r.message.success) {
                        const session_data = r.message.data;
                        // Priorizar isConnected (fuente de verdad) sobre status
                        if (session_data.isConnected === true || session_data.is_connected === true) {
                            console.log('✅ Sesión conectada detectada por webhook realtime (isConnected=true)');
                            handle_connection_success();
                        }
                    }
                }
            });
        }
    });

    frappe.realtime.on('whatsapp_session_connected', function(data) {
        console.log('📡 Evento realtime whatsapp_session_connected recibido:', data);
        if (data.session) {
            console.log('✅ Sesión conectada detectada por evento whatsapp_session_connected');
            handle_connection_success();
        }
    });

    // Verificar estado de conexión cada 5 segundos (reducido para evitar rate limiting)
    let check_count = 0;
    let current_delay = 5000; // Delay inicial de 5 segundos
    let consecutive_errors = 0;
    let check_interval = null;

    const perform_status_check = function() {
        if (is_connected) {
            if (check_interval) clearInterval(check_interval);
            return;
        }

        check_count++;
        console.log(`🔄 Verificando estado de conexión (intento ${check_count})...`);

        frappe.call({
            method: 'xappiens_whatsapp.api.session.get_session_status',
            args: { session_id: session_id },
            callback: function(r) {
                console.log(`📊 Respuesta de get_session_status (intento ${check_count}):`, r.message);

                if (r.message && r.message.success) {
                    consecutive_errors = 0; // Resetear contador de errores
                    current_delay = 5000; // Resetear delay a 5 segundos

                    const data = r.message.data;
                    const status = (data.status || '').toLowerCase();
                    // IMPORTANTE: isConnected es la fuente de verdad (estado REAL desde memoria)
                    const isConnected = data.isConnected === true || data.is_connected === true;

                    console.log('🔍 Datos de estado:', {
                        status: status,
                        isConnected: isConnected,
                        is_connected: data.is_connected,
                        status_frappe: data.status_frappe,
                        hasQR: data.hasQR
                    });

                    // PRIORIZAR isConnected sobre status para determinar conexión real
                    // Si isConnected es false, la sesión NO está conectada realmente,
                    // independientemente del valor de status
                    const statusLower = (status || '').toLowerCase();
                    const isReallyConnected = isConnected === true; // Solo confiar en isConnected

                    if (isReallyConnected) {
                        console.log('✅✅✅ SESIÓN CONECTADA DETECTADA POR POLLING');
                        if (check_interval) clearInterval(check_interval);
                        handle_connection_success();
                    } else if (statusLower === 'connecting' ||
                               statusLower === 'qr_code' ||
                               statusLower === 'qr_required' ||
                               statusLower === 'qr' ||
                               statusLower === 'pending') {
                        // Verificar si necesita mostrar QR
                        if ((statusLower === 'qr_code' || statusLower === 'qr_required' || statusLower === 'qr') && data.hasQR) {
                            status_div.html('<i class="fa fa-qrcode text-info"></i> Esperando escaneo de QR...');
                        } else {
                            status_div.html('<i class="fa fa-spinner fa-spin text-warning"></i> Esperando conexión...');
                        }
                        console.log(`⏳ Estado actual: ${statusLower} (isConnected: ${isConnected}) - Continuando monitoreo...`);

                    } else if (statusLower === 'disconnected' || (!isConnected && statusLower !== 'connecting')) {
                        // Sesión desconectada - puede necesitar reconexión
                        status_div.html('<i class="fa fa-times text-danger"></i> Sesión desconectada');
                        console.log(`❌ Sesión desconectada (status: ${statusLower}, isConnected: ${isConnected})`);

                        // Si debería estar conectada pero está desconectada, podría necesitar reconexión
                        // (esto se manejaría en otro lugar, por ahora solo detenemos el monitoreo)
                        if (check_interval) clearInterval(check_interval);
                        if (qr_check_interval) clearInterval(qr_check_interval);
                    } else if (statusLower === 'error') {
                        status_div.html('<i class="fa fa-times text-danger"></i> Error en la conexión');
                        console.log('❌ Error detectado en la conexión');
                        if (check_interval) clearInterval(check_interval);
                        if (qr_check_interval) clearInterval(qr_check_interval);
                    }
                } else {
                    consecutive_errors++;
                    const errorMsg = r.message?.error || 'Error desconocido';
                    console.log(`⚠️ Error obteniendo estado (${consecutive_errors} consecutivos):`, errorMsg);

                    // Si hay rate limiting (429), aumentar el delay significativamente
                    if (errorMsg.includes('429') || errorMsg.includes('Demasiadas solicitudes') || errorMsg.includes('rate limit')) {
                        current_delay = Math.min(current_delay * 2, 30000); // Máximo 30 segundos
                        console.log(`⏸️ Rate limiting detectado. Aumentando delay a ${current_delay/1000}s`);
                        status_div.html(`<i class="fa fa-clock-o text-warning"></i> Demasiadas solicitudes. Esperando ${current_delay/1000}s antes de reintentar...`);

                        // Reiniciar intervalo con nuevo delay
                        if (check_interval) clearInterval(check_interval);
                        setTimeout(() => {
                            check_interval = setInterval(perform_status_check, current_delay);
                        }, current_delay);
                        return; // Salir de esta iteración
                    }
                }
            },
            error: function(err) {
                consecutive_errors++;
                const errMsg = err.message || JSON.stringify(err);
                console.log(`❌ Error en llamada get_session_status (${consecutive_errors} consecutivos):`, errMsg);

                // Si hay muchos errores consecutivos o rate limiting, aumentar delay
                if (consecutive_errors >= 3 || errMsg.includes('429')) {
                    current_delay = Math.min(current_delay * 1.5, 30000);
                    console.log(`⏸️ Muchos errores. Aumentando delay a ${current_delay/1000}s`);

                    if (check_interval) clearInterval(check_interval);
                    setTimeout(() => {
                        check_interval = setInterval(perform_status_check, current_delay);
                    }, current_delay);
                }
            }
        });
    };

    // Iniciar verificación de estado
    perform_status_check(); // Primera verificación inmediata
    check_interval = setInterval(perform_status_check, current_delay); // Luego cada 5 segundos

    // Limpiar intervalos después de 5 minutos
    setTimeout(() => {
        if (!is_connected) {
            clearInterval(check_interval);
            if (qr_check_interval) clearInterval(qr_check_interval);
        }
    }, 300000);
}

/**
 * Obtener QR code para la sesión
 */
function get_qr_code_for_session(session_id, dialog, callback) {
    frappe.call({
        method: 'xappiens_whatsapp.api.session.get_qr_code',
        args: { session_id: session_id },
        callback: function(r) {
            const qr_container = dialog.fields_dict.qr_code_container.$wrapper.find('#qr-code-container');
            let rate_limited = false;

            if (r.message && r.message.success && r.message.qr_code) {
                // QR disponible, mostrarlo
                console.log('✅ QR obtenido exitosamente');
                show_qr_in_dialog(r.message.qr_code, qr_container);
                if (callback) callback(false); // No hay rate limiting
                return true;
            } else if (r.message && r.message.error) {
                // Error obteniendo QR, mostrar mensaje informativo pero continuar intentando
                const errorMsg = r.message.error;
                console.log(`⚠️ QR no disponible aún (intento): ${errorMsg}`);

                // Detectar rate limiting (429)
                if (errorMsg.includes('429') || errorMsg.includes('Demasiadas solicitudes') || errorMsg.includes('rate limit')) {
                    rate_limited = true;
                    console.log('⏸️ Rate limiting detectado en get_qr_code');

                    // Mostrar mensaje específico de rate limiting
                    if (!qr_container.find('img').length) {
                        qr_container.html(`
                            <div class="qr-code-wrapper">
                                <h5>Esperando código QR...</h5>
                                <div class="text-center">
                                    <i class="fa fa-clock-o fa-2x text-warning"></i>
                                </div>
                                <p class="text-warning small mt-2">
                                    <i class="fa fa-exclamation-triangle"></i>
                                    Demasiadas solicitudes. Esperando antes de reintentar...
                                </p>
                                <p class="text-muted small">
                                    El sistema esperará unos segundos antes de intentar obtener el QR nuevamente.
                                </p>
                            </div>
                        `);
                    }

                    if (callback) callback(true); // Hay rate limiting
                    return false;
                }

                // Solo actualizar el mensaje si no hay QR mostrado aún
                if (!qr_container.find('img').length) {
                    qr_container.html(`
                        <div class="qr-code-wrapper">
                            <h5>Esperando código QR...</h5>
                            <div class="text-center">
                                <i class="fa fa-spinner fa-spin fa-2x text-warning"></i>
                            </div>
                            <p class="text-muted small mt-2">
                                ${errorMsg.includes('QR_GENERATION_ERROR')
                                    ? 'El servidor de Baileys está generando el QR. Esto puede tardar unos momentos.'
                                    : 'Esperando que el servidor genere el QR...'}
                            </p>
                            <p class="text-muted small">
                                <i class="fa fa-info-circle"></i> El sistema seguirá intentando automáticamente...
                            </p>
                        </div>
                    `);
                }

                if (callback) callback(false); // No hay rate limiting
            }
            return false;
        },
        error: function(err) {
            console.log('❌ Error obteniendo QR:', err);
            const errMsg = err.message || JSON.stringify(err);

            // Detectar rate limiting en el error
            if (errMsg.includes('429') || errMsg.includes('Demasiadas solicitudes')) {
                if (callback) callback(true); // Hay rate limiting
            } else {
                if (callback) callback(false); // No hay rate limiting
            }
            return false;
        }
    });
}

/**
 * Desconectar sesión
 */
function disconnect_session(frm) {
                frappe.confirm(
                    __('¿Estás seguro de que quieres desconectar esta sesión?'),
                    function() {
                        frappe.call({
                method: 'xappiens_whatsapp.api.session.disconnect_session',
                args: { session_id: frm.doc.session_id },
                            callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Sesión desconectada'),
                            indicator: 'green'
                                    });
                                    frm.reload_doc();
                    } else {
                        frappe.msgprint(__('Error al desconectar: ') + (r.message?.error || 'Error desconocido'));
                                }
                            }
                        });
                    }
                );
}

/**
 * Mostrar QR code existente
 */
function show_qr_code(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Código QR de la Sesión'),
        size: 'medium',
        fields: [
            {
                fieldname: 'qr_display',
                fieldtype: 'HTML',
                options: '<div id="qr-display" class="text-center"></div>'
            }
        ]
    });

    // Obtener QR code actual
                frappe.call({
        method: 'xappiens_whatsapp.api.session.get_qr_code',
        args: { session_id: frm.doc.session_id },
                    callback: function(r) {
            if (r.message && r.message.success) {
                const qr_container = d.fields_dict.qr_display.$wrapper.find('#qr-display');
                qr_container.html(`
                    <img src="data:image/png;base64,${r.message.qr_code}"
                         alt="QR Code"
                         style="max-width: 300px; border: 1px solid #ddd; border-radius: 8px;">
                    <p class="text-muted small mt-2">
                        <i class="fa fa-info-circle"></i>
                        Escanea este código con WhatsApp para reconectar
                    </p>
                `);
                            } else {
                d.fields_dict.qr_display.$wrapper.find('#qr-display').html(
                    '<p class="text-danger">No se pudo obtener el código QR</p>'
                );
                        }
                    }
                });

    d.show();
}

/**
 * Verificar estado de la sesión
 */
function check_session_status(frm) {
    frappe.call({
        method: 'xappiens_whatsapp.api.session.get_session_status',
        args: { session_id: frm.doc.session_id },
        callback: function(r) {
            if (r.message && r.message.success) {
                const data = r.message.data;

                // Mostrar mensaje con el estado actual
                frappe.msgprint({
                    title: __('Estado de la Sesión'),
                    message: `
                        <div class="session-status">
                            <p><strong>Estado:</strong> ${data.status}</p>
                            <p><strong>Conectado:</strong> ${data.is_connected ? 'Sí' : 'No'}</p>
                            <p><strong>Número:</strong> ${data.phone_number || 'No disponible'}</p>
                            <p><strong>Última actividad:</strong> ${data.last_activity || 'No disponible'}</p>
                        </div>
                    `,
                    indicator: data.is_connected ? 'green' : 'orange'
                });

                // Si la sesión está conectada, recargar la página después de 1 segundo
                if (data.is_connected) {
                    setTimeout(function() {
                        frappe.msgprint({
                            title: __('Sesión Conectada'),
                            message: __('La sesión está conectada. Recargando la página para mostrar el estado actualizado...'),
                            indicator: 'green'
                        });

                        // Recargar la página
                        window.location.reload();
                    }, 1500);
                }
            } else {
                frappe.msgprint(__('Error al obtener el estado: ') + (r.message?.error || 'Error desconocido'));
            }
        }
    });
}

/**
 * Obtener instrucciones de conexión
 */
function get_connection_instructions() {
    return `
        <div class="connection-instructions">
            <h6><i class="fa fa-mobile"></i> Instrucciones de Conexión:</h6>
            <ol class="small">
                <li>Abre WhatsApp en tu teléfono móvil</li>
                <li>Ve a <strong>Configuración</strong> (⚙️)</li>
                <li>Selecciona <strong>Dispositivos vinculados</strong></li>
                <li>Toca <strong>Vincular un dispositivo</strong></li>
                <li>Escanea el código QR que aparecerá aquí</li>
                <li>Espera a que se complete la conexión</li>
            </ol>
            <div class="alert alert-info small">
                <i class="fa fa-info-circle"></i>
                <strong>Nota:</strong> El código QR es válido por 2 minutos. Si expira, se generará uno nuevo automáticamente.
                                            </div>
                                            </div>
                                        `;
                                    }
