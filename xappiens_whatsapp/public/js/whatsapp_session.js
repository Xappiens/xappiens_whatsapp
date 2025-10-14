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

// Vista de lista - Botón para conectar nueva sesión
frappe.listview_settings['WhatsApp Session'] = {
    onload: function(listview) {
        listview.page.add_menu_item(__('Conectar Nueva Sesión'), function() {
            show_connection_wizard();
        });
    }
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
            if (r.message && r.message.success) {
                status_div.html('<i class="fa fa-check text-success"></i> Sesión creada exitosamente');

                // Mostrar QR code si está disponible
                if (r.message.qr_code) {
                    show_qr_in_dialog(r.message.qr_code, qr_container);
                } else {
                    // Si no hay QR, mostrar mensaje de espera
                    qr_container.html(`
                        <div class="qr-code-wrapper">
                            <h5>Esperando código QR...</h5>
                            <div class="text-center">
                                <i class="fa fa-spinner fa-spin fa-2x text-warning"></i>
            </div>
                            <p class="text-muted small mt-2">
                                El código QR se generará automáticamente en unos segundos
                            </p>
            </div>
                    `);
                    qr_container.show();
                }

                // Iniciar monitoreo de estado
                monitor_connection_status(values.session_id, status_div, dialog);

            } else {
                const errorMsg = (r.message && r.message.error) ? r.message.error : 'Error desconocido';
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
    const max_qr_attempts = 3;

    const check_interval = setInterval(() => {
        frappe.call({
            method: 'xappiens_whatsapp.api.session.get_session_status',
            args: { session_id: session_id },
            callback: function(r) {
                if (r.message && r.message.success) {
                    const data = r.message.data;
                    const status = data.status;

                    if (status === 'connected') {
                        status_div.html('<i class="fa fa-check-circle text-success"></i> ¡Conectado exitosamente!');
                        clearInterval(check_interval);

                        // Cerrar modal después de 2 segundos
                        setTimeout(() => {
                            dialog.hide();
                            frappe.set_route('List', 'WhatsApp Session');
                        }, 2000);

                    } else if (status === 'connecting' || status === 'qr_required') {
                        status_div.html('<i class="fa fa-spinner fa-spin text-warning"></i> Esperando conexión...');

                        // Intentar obtener QR code si no se ha mostrado aún
                        if (qr_attempts < max_qr_attempts) {
                            qr_attempts++;
                            get_qr_code_for_session(session_id, dialog);
                        }

                    } else if (status === 'error') {
                        status_div.html('<i class="fa fa-times text-danger"></i> Error en la conexión');
                        clearInterval(check_interval);
                    }
                }
            }
        });
    }, 3000); // Verificar cada 3 segundos

    // Limpiar intervalo después de 5 minutos
    setTimeout(() => {
        clearInterval(check_interval);
    }, 300000);
}

/**
 * Obtener QR code para la sesión
 */
function get_qr_code_for_session(session_id, dialog) {
                        frappe.call({
        method: 'xappiens_whatsapp.api.session.get_qr_code',
        args: { session_id: session_id },
                            callback: function(r) {
            if (r.message && r.message.success && r.message.qr_code) {
                const qr_container = dialog.fields_dict.qr_code_container.$wrapper.find('#qr-code-container');
                show_qr_in_dialog(r.message.qr_code, qr_container);
                                }
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
