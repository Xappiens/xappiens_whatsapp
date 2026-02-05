#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API para gestión de archivos multimedia de WhatsApp.
Maneja descarga, subida y procesamiento de medios.
"""

import frappe
import os
import requests
from frappe.utils import now, get_files_path
from frappe.utils.file_manager import save_file
from .base import WhatsAppAPIClient
from typing import Dict, Any, Optional
import mimetypes


@frappe.whitelist()
def download_media_from_message(session: str, message: str) -> Dict[str, Any]:
    """
    Descarga archivo multimedia desde WhatsApp API usando el ID del mensaje.

    Args:
        session: Nombre del documento WhatsApp Session
        message: Nombre del documento WhatsApp Message

    Returns:
        Dict con resultado de la descarga
    """
    try:
        # Obtener documentos
        message_doc = frappe.get_doc("WhatsApp Message", message)
        session_doc = frappe.get_doc("WhatsApp Session", session)

        if not message_doc.has_media:
            return {"success": False, "message": "El mensaje no tiene archivos multimedia"}

        if not session_doc.is_connected:
            return {"success": False, "message": "La sesión no está conectada"}

        # Usar API client para descargar
        client = WhatsAppAPIClient(session_doc.session_id)

        # Endpoint para descarga de medios
        response = client.get(f"/api/messages/{session_doc.session_id}/{message_doc.message_id}/media")

        if not response.get("success"):
            return {
                "success": False,
                "message": f"Error descargando desde API: {response.get('message', 'Error desconocido')}"
            }

        media_data = response.get("data", {})
        media_url = media_data.get("url") or media_data.get("media_url")

        if not media_url:
            return {"success": False, "message": "URL de descarga no disponible"}

        # Descargar archivo
        media_response = requests.get(media_url, timeout=30)
        media_response.raise_for_status()

        # Determinar nombre y tipo de archivo
        filename = media_data.get("filename") or f"media_{message_doc.message_id}"
        mimetype = media_data.get("mimetype") or "application/octet-stream"

        # Agregar extensión si no la tiene
        if not os.path.splitext(filename)[1]:
            extension = mimetypes.guess_extension(mimetype) or ".bin"
            filename += extension

        # Guardar archivo en Frappe
        file_doc = save_file(
            filename,
            media_response.content,
            "WhatsApp Message",
            message,
            is_private=0
        )

        # Actualizar mensaje con información del archivo
        if message_doc.media_items:
            # Actualizar item existente
            for item in message_doc.media_items:
                item.file = file_doc.file_url
                item.filename = filename
                item.filesize = len(media_response.content)
                item.mimetype = mimetype
                break
        else:
            # Crear nuevo item
            message_doc.append("media_items", {
                "media_type": _get_media_type_from_mimetype(mimetype),
                "file": file_doc.file_url,
                "filename": filename,
                "filesize": len(media_response.content),
                "mimetype": mimetype,
                "url": media_url
            })

        message_doc.save(ignore_permissions=True)

        return {
            "success": True,
            "message": "Archivo descargado exitosamente",
            "file_path": file_doc.file_url,
            "filename": filename,
            "filesize": len(media_response.content)
        }

    except Exception as e:
        frappe.log_error(f"Error downloading media: {str(e)}", "WhatsApp Media Download")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def download_media_api(session: str, message_id: str) -> Dict[str, Any]:
    """
    Descarga archivo multimedia usando el message_id de WhatsApp.

    Args:
        session: Nombre del documento WhatsApp Session
        message_id: ID del mensaje de WhatsApp

    Returns:
        Dict con resultado de la descarga
    """
    try:
        # Buscar mensaje por message_id
        message_name = frappe.db.get_value("WhatsApp Message", {
            "session": session,
            "message_id": message_id
        }, "name")

        if not message_name:
            return {"success": False, "message": "Mensaje no encontrado"}

        return download_media_from_message(session, message_name)

    except Exception as e:
        frappe.log_error(f"Error in download_media_api: {str(e)}", "WhatsApp Media API")
        return {"success": False, "message": str(e)}


@frappe.whitelist()
def upload_media_file(file_path: str, media_type: str = None) -> Dict[str, Any]:
    """
    Procesa un archivo subido para envío por WhatsApp.

    Args:
        file_path: Ruta del archivo en Frappe
        media_type: Tipo de media (opcional, se detecta automáticamente)

    Returns:
        Dict con información del archivo procesado
    """
    try:
        # Obtener información del archivo
        # Buscar por file_url o por name si file_path es un nombre de documento
        file_doc = None
        if file_path.startswith("/files/"):
            file_doc = frappe.get_doc("File", {"file_url": file_path})
        else:
            # Intentar obtener por nombre si es un nombre de documento
            if frappe.db.exists("File", file_path):
                file_doc = frappe.get_doc("File", file_path)

        if not file_doc:
            return {"success": False, "message": f"Archivo no encontrado: {file_path}"}

        # Obtener nombre del archivo para detectar tipo (más confiable para webp, etc.)
        file_name = getattr(file_doc, 'file_name', None) or getattr(file_doc, 'name', '')

        # Obtener content_type (priorizar detección desde nombre del archivo)
        # Esto es más confiable para formatos modernos como webp
        content_type = (
            _guess_mimetype_from_filename(file_name) or
            getattr(file_doc, 'content_type', None) or
            getattr(file_doc, 'mime_type', None) or
            'application/octet-stream'
        )

        # Log para debugging
        frappe.logger().info(f"File upload - name: {file_name}, content_type detected: {content_type}, media_type: {media_type}")

        # Determinar tipo de media
        if not media_type:
            media_type = _get_media_type_from_mimetype(content_type)
            frappe.logger().info(f"Media type determined: {media_type} from mimetype: {content_type}")

        # Validar tamaño según tipo
        max_sizes = {
            "image": 16 * 1024 * 1024,    # 16MB
            "video": 64 * 1024 * 1024,    # 64MB
            "audio": 16 * 1024 * 1024,    # 16MB
            "voice": 16 * 1024 * 1024,    # 16MB
            "document": 100 * 1024 * 1024, # 100MB
            "sticker": 1 * 1024 * 1024     # 1MB
        }

        max_size = max_sizes.get(media_type, 100 * 1024 * 1024)
        if file_doc.file_size and file_doc.file_size > max_size:
            return {
                "success": False,
                "message": f"Archivo demasiado grande. Máximo {max_size // (1024*1024)}MB para {media_type}"
            }

        return {
            "success": True,
            "file_path": file_path,
            "filename": file_doc.file_name or file_doc.name,
            "filesize": getattr(file_doc, 'file_size', None) or 0,
            "mimetype": content_type,
            "media_type": media_type
        }

    except Exception as e:
        frappe.log_error(f"Error processing uploaded file: {str(e)}", "WhatsApp Media Upload")
        return {"success": False, "message": str(e)}


def _guess_mimetype_from_filename(filename: str) -> Optional[str]:
    """
    Adivina el MIME type basado en la extensión del archivo.

    Args:
        filename: Nombre del archivo

    Returns:
        MIME type o None si no se puede determinar
    """
    if not filename:
        return None

    # Agregar tipos MIME comunes que pueden no estar en mimetypes estándar
    mimetypes.add_type('image/webp', '.webp')
    mimetypes.add_type('image/avif', '.avif')
    mimetypes.add_type('image/heic', '.heic')
    mimetypes.add_type('image/heif', '.heif')

    mimetype, _ = mimetypes.guess_type(filename)
    return mimetype


def _get_media_type_from_mimetype(mimetype: str) -> str:
    """
    Determina el tipo de media basado en el MIME type.

    Args:
        mimetype: MIME type del archivo

    Returns:
        Tipo de media para WhatsApp
    """
    if not mimetype:
        return "document"

    mimetype = mimetype.lower()

    # Imágenes (incluyendo webp, avif, etc.)
    if mimetype.startswith("image/"):
        return "image"
    # Videos
    elif mimetype.startswith("video/"):
        return "video"
    # Audio
    elif mimetype.startswith("audio/"):
        return "audio"
    # Documentos comunes
    elif mimetype in ["application/pdf", "text/plain", "application/msword",
                      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                      "application/vnd.ms-excel",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                      "application/vnd.ms-powerpoint",
                      "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
        return "document"
    # Por defecto, tratar como documento
    else:
        return "document"


@frappe.whitelist()
def get_media_info(message: str) -> Dict[str, Any]:
    """
    Obtiene información de los archivos multimedia de un mensaje.

    Args:
        message: Nombre del documento WhatsApp Message

    Returns:
        Dict con información de los medios
    """
    try:
        message_doc = frappe.get_doc("WhatsApp Message", message)

        if not message_doc.has_media:
            return {"success": False, "message": "El mensaje no tiene archivos multimedia"}

        media_list = []
        for item in message_doc.media_items:
            media_info = {
                "media_type": item.media_type,
                "filename": item.filename,
                "filesize": item.filesize,
                "mimetype": item.mimetype,
                "file_url": item.file,
                "thumbnail": item.thumbnail,
                "is_downloaded": bool(item.file)
            }
            media_list.append(media_info)

        return {
            "success": True,
            "media_count": len(media_list),
            "media_items": media_list
        }

    except Exception as e:
        frappe.log_error(f"Error getting media info: {str(e)}", "WhatsApp Media Info")
        return {"success": False, "message": str(e)}
