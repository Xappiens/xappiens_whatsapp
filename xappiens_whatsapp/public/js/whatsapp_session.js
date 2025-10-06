// Función helper para formatear mensajes de sincronización
function formatSyncMessage(result, type) {
    if (!result || !result.success) {
        return {
            title: __('Error de Sincronización'),
            message: `<div style="background: #fee; border: 1px solid #fcc; padding: 15px; border-radius: 5px;">
                <h4 style="color: #c33; margin: 0 0 10px 0;">❌ Error</h4>
                <p style="margin: 0; color: #666;">${result.error || 'Error desconocido'}</p>
            </div>`,
            indicator: 'red'
        };
    }

    let stats = '';
    let icon = '✅';

    if (type === 'contacts') {
        const created = result.created || 0;
        const updated = result.updated || 0;
        const total = result.total_from_server || 0;
        stats = `
            <div style="display: flex; gap: 20px; margin: 10px 0;">
                <div><strong>📊 Total del servidor:</strong> ${total}</div>
                <div><strong>🆕 Nuevos:</strong> ${created}</div>
                <div><strong>🔄 Actualizados:</strong> ${updated}</div>
            </div>
        `;
    } else if (type === 'conversations') {
        const created = result.created || 0;
        const updated = result.updated || 0;
        const total = result.total_from_server || 0;
        stats = `
            <div style="display: flex; gap: 20px; margin: 10px 0;">
                <div><strong>📊 Total del servidor:</strong> ${total}</div>
                <div><strong>🆕 Nuevos:</strong> ${created}</div>
                <div><strong>🔄 Actualizados:</strong> ${updated}</div>
            </div>
        `;
    } else if (type === 'messages') {
        const conversations = result.conversations_synced || 0;
        const totalMessages = result.total_messages || 0;
        stats = `
            <div style="display: flex; gap: 20px; margin: 10px 0;">
                <div><strong>💬 Conversaciones:</strong> ${conversations}</div>
                <div><strong>📨 Mensajes:</strong> ${totalMessages}</div>
            </div>
        `;
    } else if (type === 'all') {
        const sessionStatus = result.sync_status?.session_status;
        const contacts = result.sync_status?.contacts;
        const conversations = result.sync_status?.conversations;
        const messages = result.sync_status?.messages;

        stats = `
            <div style="margin: 10px 0;">
                <h4 style="margin: 0 0 10px 0; color: #2e7d32;">📊 Resumen de Sincronización</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
                        <strong>📞 Contactos:</strong><br>
                        ${contacts ? `Nuevos: ${contacts.created || 0} | Actualizados: ${contacts.updated || 0}` : 'No sincronizados'}
                    </div>
                    <div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
                        <strong>💬 Conversaciones:</strong><br>
                        ${conversations ? `Nuevas: ${conversations.created || 0} | Actualizadas: ${conversations.updated || 0}` : 'No sincronizadas'}
                    </div>
                </div>
            </div>
        `;
    }

    return {
        title: __('Sincronización Completada'),
        message: `<div style="background: #f0f8f0; border: 1px solid #4caf50; padding: 15px; border-radius: 5px;">
            <h4 style="color: #2e7d32; margin: 0 0 10px 0;">${icon} ¡Sincronización exitosa!</h4>
            ${stats}
            <p style="margin: 10px 0 0 0; color: #666; font-size: 12px;">
                Sincronizado el ${new Date().toLocaleString()}
            </p>
        </div>`,
        indicator: 'green'
    };
}

frappe.ui.form.on('WhatsApp Session', {
    refresh: function(frm) {
        // Solo mostrar botones si el documento está guardado
        if (!frm.is_new()) {
            // Grupo: Gestión de Sesión
            frm.add_custom_button(__('Check Status'), function() {
                frm.call('check_status')
                    .then(r => {
                        if (r.message) {
                            let message = '';
                            let indicator = r.message.success ? 'green' : 'red';

                            if (r.message.success) {
                                message = `
                                    <div style="padding: 15px;">
                                        <h4 style="color: #28a745; margin-bottom: 15px;">
                                            <i class="fa fa-check-circle"></i> Estado de la Sesión
                                        </h4>
                                        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                            <strong>Estado:</strong> <span style="color: #28a745;">${r.message.status || 'N/A'}</span><br>
                                            <strong>Conectado:</strong> <span style="color: ${r.message.is_connected ? '#28a745' : '#dc3545'};">${r.message.is_connected ? 'Sí' : 'No'}</span><br>
                                            <strong>Teléfono:</strong> ${r.message.phone_number || 'N/A'}<br>
                                            <strong>Estado API:</strong> <span style="color: #007bff;">${r.message.state || 'N/A'}</span>
                                        </div>
                                    </div>
                                `;
                            } else {
                                message = `
                                    <div style="padding: 15px;">
                                        <h4 style="color: #dc3545; margin-bottom: 15px;">
                                            <i class="fa fa-exclamation-triangle"></i> Error al verificar estado
                                        </h4>
                                        <div style="background: #f8d7da; padding: 10px; border-radius: 5px; color: #721c24;">
                                            ${r.message.error || 'Error desconocido'}
                                        </div>
                                    </div>
                                `;
                            }

                            frappe.msgprint({
                                title: __('Estado de la Sesión WhatsApp'),
                                message: message,
                                indicator: indicator
                            });
                            frm.reload_doc();
                        }
                    });
            }, __('Sesión'));

            frm.add_custom_button(__('Connect Session'), function() {
                frappe.confirm(
                    __('¿Deseas conectar esta sesión de WhatsApp?'),
                    function() {
                        frappe.call({
                            method: 'xappiens_whatsapp.xappiens_whatsapp.doctype.whatsapp_session.whatsapp_session.connect_session',
                            args: {
                                session_id: frm.doc.session_id
                            },
                            callback: function(r) {
                                if (r.message) {
                                    frappe.msgprint({
                                        title: __('Connect Session'),
                                        message: '<pre>' + JSON.stringify(r.message, null, 2) + '</pre>',
                                        indicator: r.message.success ? 'green' : 'red'
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Sesión'));

            frm.add_custom_button(__('Disconnect Session'), function() {
                frappe.confirm(
                    __('¿Estás seguro de que quieres desconectar esta sesión?'),
                    function() {
                        frappe.call({
                            method: 'xappiens_whatsapp.xappiens_whatsapp.doctype.whatsapp_session.whatsapp_session.disconnect_session',
                            args: {
                                session_id: frm.doc.session_id
                            },
                            callback: function(r) {
                                if (r.message) {
                                    frappe.msgprint({
                                        title: __('Disconnect Session'),
                                        message: '<pre>' + JSON.stringify(r.message, null, 2) + '</pre>',
                                        indicator: r.message.success ? 'green' : 'orange'
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __('Sesión'));

            frm.add_custom_button(__('Get QR Code'), function() {
                frappe.call({
                    method: 'xappiens_whatsapp.xappiens_whatsapp.doctype.whatsapp_session.whatsapp_session.get_qr_code',
                    args: {
                        session_id: frm.doc.session_id
                    },
                    callback: function(r) {
                        if (r.message) {
                            if (r.message.qr_code_image) {
                                frappe.msgprint({
                                    title: __('QR Code'),
                                    message: '<div style="text-align: center;"><img src="' + r.message.qr_code_image + '" alt="QR Code" style="max-width: 300px; height: auto;"></div>',
                                    indicator: 'blue'
                                });
                            } else {
                                frappe.msgprint({
                                    title: __('QR Code'),
                                    message: '<pre>' + JSON.stringify(r.message, null, 2) + '</pre>',
                                    indicator: r.message.success ? 'green' : 'red'
                                });
                            }
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Sesión'));

            // Grupo: Sincronización
            frm.add_custom_button(__('Sync All Data'), function() {
                frappe.confirm(
                    __('Esto sincronizará todos los contactos, conversaciones y mensajes. ¿Continuar?'),
                    function() {
                        frappe.show_alert({
                            message: __('Iniciando sincronización completa...'),
                            indicator: 'blue'
                        });
                        frm.call('sync_all_data')
                            .then(r => {
                                if (r.message) {
                                    const formatted = formatSyncMessage(r.message, 'all');
                                    frappe.msgprint(formatted);
                                    frm.reload_doc();
                                }
                            });
                    }
                );
            }, __('Sincronización'));

            frm.add_custom_button(__('Sync Contacts'), function() {
                frappe.show_alert({
                    message: __('Sincronizando contactos...'),
                    indicator: 'blue'
                });
                frm.call('sync_contacts')
                    .then(r => {
                        if (r.message) {
                            const formatted = formatSyncMessage(r.message, 'contacts');
                            frappe.msgprint(formatted);
                            frm.reload_doc();
                        }
                    });
            }, __('Sincronización'));

            frm.add_custom_button(__('Sync Conversations'), function() {
                frappe.show_alert({
                    message: __('Sincronizando conversaciones...'),
                    indicator: 'blue'
                });
                frm.call('sync_conversations')
                    .then(r => {
                        if (r.message) {
                            const formatted = formatSyncMessage(r.message, 'conversations');
                            frappe.msgprint(formatted);
                            frm.reload_doc();
                        }
                    });
            }, __('Sincronización'));

            frm.add_custom_button(__('Sync Messages'), function() {
                frappe.show_alert({
                    message: __('Sincronizando mensajes...'),
                    indicator: 'blue'
                });
                frm.call('sync_messages')
                    .then(r => {
                        if (r.message) {
                            const formatted = formatSyncMessage(r.message, 'messages');
                            frappe.msgprint(formatted);
                            frm.reload_doc();
                        }
                    });
            }, __('Sincronización'));

            frm.add_custom_button(__('Sync Groups'), function() {
                frappe.show_alert({
                    message: __('Sincronizando grupos...'),
                    indicator: 'blue'
                });
                frm.call('sync_groups')
                    .then(r => {
                        if (r.message) {
                            frappe.msgprint({
                                title: __('Sync Groups'),
                                message: '<pre>' + JSON.stringify(r.message, null, 2) + '</pre>',
                                indicator: r.message.success ? 'green' : 'red'
                            });
                            frm.reload_doc();
                        }
                    });
            }, __('Sincronización'));

            // Grupo: Vinculación con CRM
            frm.add_custom_button(__('Auto Link Contacts to Leads'), function() {
                frappe.confirm(
                    __('Esto vinculará automáticamente todos los contactos de WhatsApp con leads de CRM que tengan números de teléfono coincidentes. ¿Continuar?'),
                    function() {
                        frappe.show_alert({
                            message: __('Iniciando vinculación automática...'),
                            indicator: 'blue'
                        });
                        frappe.call({
                            method: 'xappiens_whatsapp.api.contacts_linking.bulk_auto_link_contacts',
                            callback: function(r) {
                                if (r.message) {
                                    let message = '';
                                    let indicator = r.message.success ? 'green' : 'red';

                                    if (r.message.success) {
                                        const stats = r.message.stats;
                                        message = `
                                            <div style="padding: 15px;">
                                                <h4 style="color: #28a745; margin-bottom: 15px;">
                                                    <i class="fa fa-link"></i> Vinculación Automática Completada
                                                </h4>
                                                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                                    <strong>Estadísticas:</strong><br>
                                                    • Total de contactos: ${stats.total_contacts}<br>
                                                    • Ya vinculados: ${stats.already_linked}<br>
                                                    • Nuevamente vinculados: ${stats.newly_linked}<br>
                                                    • Sin lead encontrado: ${stats.no_lead_found}<br>
                                                    • Errores: ${stats.errors}
                                                </div>
                                                <p style="margin: 0; color: #666;">
                                                    <i class="fa fa-info-circle"></i> ${r.message.message}
                                                </p>
                                            </div>
                                        `;
                                    } else {
                                        message = `
                                            <div style="padding: 15px;">
                                                <h4 style="color: #dc3545; margin-bottom: 15px;">
                                                    <i class="fa fa-exclamation-triangle"></i> Error en Vinculación
                                                </h4>
                                                <p style="margin: 0; color: #666;">
                                                    ${r.message.message}
                                                </p>
                                            </div>
                                        `;
                                    }

                                    frappe.msgprint({
                                        title: r.message.success ? 'Vinculación Exitosa' : 'Error en Vinculación',
                                        message: message,
                                        indicator: indicator
                                    });
                                }
                            }
                        });
                    }
                );
            }, __('CRM Integration'));
        }
    }
});
