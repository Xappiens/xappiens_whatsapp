/**
 * WhatsApp Session Merge Functionality
 * Interfaz para fusionar sesiones de WhatsApp
 */

/**
 * Mostrar diálogo de fusión de sesiones
 */
function show_session_merge_dialog(current_session_name = null) {
    let d = new frappe.ui.Dialog({
        title: __('Fusionar Sesiones de WhatsApp'),
        size: 'large',
        fields: [
            {
                fieldtype: 'Section Break',
                label: __('Seleccionar Sesiones')
            },
            {
                fieldname: 'old_session',
                fieldtype: 'Link',
                label: __('Sesión Origen (será eliminada)'),
                options: 'WhatsApp Session',
                reqd: 1,
                description: __('Sesión que será fusionada y eliminada'),
                get_query: function() {
                    return {
                        filters: {
                            'name': ['!=', d.get_value('new_session') || '']
                        }
                    };
                }
            },
            {
                fieldname: 'new_session',
                fieldtype: 'Link',
                label: __('Sesión Destino (recibirá los datos)'),
                options: 'WhatsApp Session',
                reqd: 1,
                description: __('Sesión que recibirá todos los datos fusionados'),
                get_query: function() {
                    return {
                        filters: {
                            'name': ['!=', d.get_value('old_session') || '']
                        }
                    };
                }
            },
            {
                fieldtype: 'Section Break',
                label: __('Vista Previa de la Fusión')
            },
            {
                fieldname: 'preview_section',
                fieldtype: 'HTML',
                options: '<div id="merge-preview" class="text-center text-muted">Selecciona ambas sesiones para ver la vista previa</div>'
            },
            {
                fieldtype: 'Section Break',
                label: __('Confirmación')
            },
            {
                fieldname: 'confirmation',
                fieldtype: 'Check',
                label: __('Entiendo que esta operación no se puede deshacer'),
                description: __('La sesión origen será eliminada permanentemente')
            }
        ],
        primary_action_label: __('Fusionar Sesiones'),
        primary_action: function(values) {
            if (!values.confirmation) {
                frappe.msgprint(__('Debes confirmar que entiendes que la operación no se puede deshacer'));
                return;
            }
            execute_session_merge(values.old_session, values.new_session, d);
        },
        secondary_action_label: __('Vista Previa'),
        secondary_action: function() {
            const values = d.get_values();
            if (values.old_session && values.new_session) {
                load_merge_preview(values.old_session, values.new_session, d);
            } else {
                frappe.msgprint(__('Selecciona ambas sesiones primero'));
            }
        }
    });

    // Pre-llenar sesión actual si se proporciona
    if (current_session_name) {
        d.fields_dict.old_session.set_value(current_session_name);
    }

    // Actualizar vista previa cuando cambien las sesiones
    d.fields_dict.old_session.$input.on('change', function() {
        update_preview_if_both_selected(d);
    });

    d.fields_dict.new_session.$input.on('change', function() {
        update_preview_if_both_selected(d);
    });

    d.show();
}

/**
 * Actualizar vista previa si ambas sesiones están seleccionadas
 */
function update_preview_if_both_selected(dialog) {
    const values = dialog.get_values();
    if (values.old_session && values.new_session) {
        load_merge_preview(values.old_session, values.new_session, dialog);
    }
}

/**
 * Cargar vista previa de la fusión
 */
function load_merge_preview(old_session, new_session, dialog) {
    const preview_div = dialog.fields_dict.preview_section.$wrapper.find('#merge-preview');

    preview_div.html('<i class="fa fa-spinner fa-spin"></i> Cargando vista previa...');

    frappe.call({
        method: 'xappiens_whatsapp.xappiens_whatsapp.doctype.whatsapp_session.whatsapp_session_simple_merge.get_simple_merge_preview',
        args: {
            old_session: old_session,
            new_session: new_session
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                const data = r.message;
                preview_div.html(generate_preview_html(data));
            } else {
                const error = r.message?.error || 'Error desconocido';
                preview_div.html(`<div class="alert alert-danger">${error}</div>`);
            }
        },
        error: function(err) {
            preview_div.html(`<div class="alert alert-danger">Error de conexión: ${err.message}</div>`);
        }
    });
}

/**
 * Generar HTML para la vista previa
 */
function generate_preview_html(data) {
    const stats = data.statistics;
    const conflicts = data.potential_conflicts || [];

    let html = `
        <div class="merge-preview">
            <div class="row">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-danger text-white">
                            <h6 class="mb-0"><i class="fa fa-arrow-right"></i> Sesión Origen (será eliminada)</h6>
                        </div>
                        <div class="card-body">
                            <strong>${data.old_session.session_name}</strong><br>
                            <small class="text-muted">${data.old_session.name}</small><br>
                            <span class="badge badge-${data.old_session.is_connected ? 'success' : 'secondary'}">
                                ${data.old_session.status}
                            </span>
                            ${data.old_session.phone_number ? `<br><small>📞 ${data.old_session.phone_number}</small>` : ''}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-success text-white">
                            <h6 class="mb-0"><i class="fa fa-arrow-left"></i> Sesión Destino (recibirá los datos)</h6>
                        </div>
                        <div class="card-body">
                            <strong>${data.new_session.session_name}</strong><br>
                            <small class="text-muted">${data.new_session.name}</small><br>
                            <span class="badge badge-${data.new_session.is_connected ? 'success' : 'secondary'}">
                                ${data.new_session.status}
                            </span>
                            ${data.new_session.phone_number ? `<br><small>📞 ${data.new_session.phone_number}</small>` : ''}
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-3">
                <h6>📊 Datos a Transferir:</h6>
                <div class="row">
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-primary">${stats.whatsapp_contact || 0}</div>
                            <small>Contactos</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-info">${stats.whatsapp_conversation || 0}</div>
                            <small>Conversaciones</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-warning">${stats.whatsapp_message || 0}</div>
                            <small>Mensajes</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <div class="h4 text-secondary">${stats.whatsapp_media_file || 0}</div>
                            <small>Archivos Media</small>
                        </div>
                    </div>
                </div>
            </div>`;

    if (conflicts.length > 0) {
        html += `
            <div class="mt-3">
                <div class="alert alert-warning">
                    <h6><i class="fa fa-exclamation-triangle"></i> Conflictos Detectados:</h6>
                    <ul class="mb-0">
                        ${conflicts.map(conflict => `<li>${conflict}</li>`).join('')}
                    </ul>
                    <small class="mt-2 d-block">Estos conflictos se resolverán automáticamente fusionando los datos duplicados.</small>
                </div>
            </div>`;
    }

    html += `
            <div class="mt-3">
                <div class="alert alert-info">
                    <strong><i class="fa fa-info-circle"></i> Importante:</strong><br>
                    ${data.warning}
                </div>
            </div>
        </div>`;

    return html;
}

/**
 * Ejecutar la fusión de sesiones
 */
function execute_session_merge(old_session, new_session, dialog) {
    // Mostrar confirmación final
    frappe.confirm(
        `¿Estás seguro de que quieres fusionar la sesión "${old_session}" con "${new_session}"?<br><br>
        <strong>Esta operación NO se puede deshacer.</strong><br>
        La sesión "${old_session}" será eliminada permanentemente.`,
        function() {
            // Mostrar progreso
            const progress_dialog = new frappe.ui.Dialog({
                title: __('Fusionando Sesiones'),
                fields: [
                    {
                        fieldname: 'progress_html',
                        fieldtype: 'HTML',
                        options: `
                            <div class="text-center">
                                <div class="progress mb-3">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated"
                                         role="progressbar" style="width: 100%"></div>
                                </div>
                                <p><i class="fa fa-spinner fa-spin"></i> Fusionando sesiones de WhatsApp...</p>
                                <small class="text-muted">Esta operación puede tomar varios minutos dependiendo de la cantidad de datos.</small>
                            </div>
                        `
                    }
                ]
            });
            progress_dialog.show();

            // Ejecutar fusión
            frappe.call({
                method: 'xappiens_whatsapp.xappiens_whatsapp.doctype.whatsapp_session.whatsapp_session_simple_merge.simple_merge_sessions',
                args: {
                    old_session: old_session,
                    new_session: new_session
                },
                callback: function(r) {
                    progress_dialog.hide();

                    if (r.message && r.message.success) {
                        dialog.hide();

                        // Mostrar resultado exitoso
                        frappe.msgprint({
                            title: __('Fusión Completada'),
                            message: `
                                <div class="alert alert-success">
                                    <strong>¡Fusión exitosa!</strong><br>
                                    ${r.message.message}
                                </div>
                                ${r.message.conflicts_handled && r.message.conflicts_handled.length > 0 ? `
                                <div class="mt-2">
                                    <strong>Conflictos resueltos:</strong>
                                    <ul>
                                        ${r.message.conflicts_handled.map(conflict => `<li>${conflict}</li>`).join('')}
                                    </ul>
                                </div>
                                ` : ''}
                            `,
                            indicator: 'green'
                        });

                        // Recargar la página actual si estamos en la lista de sesiones
                        if (window.location.pathname.includes('WhatsApp Session')) {
                            setTimeout(() => {
                                window.location.reload();
                            }, 2000);
                        }

                    } else {
                        const error = r.message?.error || 'Error desconocido durante la fusión';
                        frappe.msgprint({
                            title: __('Error en la Fusión'),
                            message: `<div class="alert alert-danger">${error}</div>`,
                            indicator: 'red'
                        });
                    }
                },
                error: function(err) {
                    progress_dialog.hide();
                    frappe.msgprint({
                        title: __('Error de Conexión'),
                        message: `<div class="alert alert-danger">Error de conexión: ${err.message}</div>`,
                        indicator: 'red'
                    });
                }
            });
        },
        function() {
            // Usuario canceló
            return;
        }
    );
}

// Extender la configuración existente de la vista de lista
$(document).ready(function() {
    // Esperar a que se cargue la configuración existente
    setTimeout(function() {
        if (frappe.listview_settings['WhatsApp Session']) {
            const existing_onload = frappe.listview_settings['WhatsApp Session'].onload;

            frappe.listview_settings['WhatsApp Session'].onload = function(listview) {
                // Ejecutar onload existente si existe
                if (existing_onload) {
                    existing_onload.call(this, listview);
                }

                // Agregar botón de fusión
                listview.page.add_menu_item(__('Fusionar Sesiones'), function() {
                    show_session_merge_dialog();
                });
            };
        }
    }, 100);
});

// Extender el formulario individual existente
$(document).ready(function() {
    // Agregar el botón de fusión al formulario
    frappe.ui.form.on('WhatsApp Session', {
        onload_post_render: function(frm) {
            // Agregar botón de fusión si no existe ya
            if (!frm.custom_buttons[__('Fusionar con Otra Sesión')]) {
                frm.add_custom_button(__('Fusionar con Otra Sesión'), function() {
                    show_session_merge_dialog(frm.doc.name);
                }, __('Acciones'));
            }
        }
    });
});
