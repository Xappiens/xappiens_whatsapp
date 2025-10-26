// Copyright (c) 2025, Xappiens and contributors
// For license information, please see license.txt

frappe.ui.form.on("WhatsApp Session", {
	refresh(frm) {
		// Añadir botón de sincronización si la sesión está conectada
		if (frm.doc.is_connected && frm.doc.status === "Connected") {
			frm.add_custom_button(__("Sincronizar Ahora"), function() {
				frappe.confirm(
					__("¿Deseas sincronizar todos los datos de esta sesión? Esto incluirá contactos, conversaciones y mensajes."),
					function() {
						// Usuario confirmó
						frappe.call({
							method: "sync_all_data",
							doc: frm.doc,
							freeze: true,
							freeze_message: __("Iniciando sincronización..."),
							callback: function(r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: __("Sincronización iniciada en segundo plano"),
										indicator: "green"
									}, 5);

									// Recargar el documento después de unos segundos
									setTimeout(function() {
										frm.reload_doc();
									}, 3000);
								}
							},
							error: function(r) {
								frappe.msgprint({
									title: __("Error"),
									message: __("No se pudo iniciar la sincronización. Revisa los logs para más detalles."),
									indicator: "red"
								});
							}
						});
					},
					function() {
						// Usuario canceló
						frappe.show_alert({
							message: __("Sincronización cancelada"),
							indicator: "orange"
						}, 3);
					}
				);
			}, __("Acciones"));
		}

		// Información sobre la última sincronización
		if (frm.doc.last_sync) {
			frm.dashboard.add_comment(
				__("Última sincronización: {0}", [frappe.datetime.comment_when(frm.doc.last_sync)]),
				"blue",
				true
			);
		}
	}
});
