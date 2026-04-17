import re
from pathlib import Path
from docx import Document

from core.config import (
    REGEX_ACTA_NUM_HEADER, REGEX_FECHA_HEADER,
    REGEX_ACTA_NUM_FILENAME, REGEX_FECHA_FILENAME
)
from core.logger import logger

def normalizar_fecha(fecha_str: str) -> str:
    """Normaliza una fecha al formato DD/MM/YYYY"""
    if not fecha_str:
        return "NO_ENCONTRADA"
    
    # Reemplazar guiones por slashes
    fecha_str = fecha_str.replace("-", "/")
    
    # Manejar formatos cortos de año (ej. 11/04/23 -> 11/04/2023)
    partes = fecha_str.split("/")
    if len(partes) == 3:
        if len(partes[2]) == 2:
            año = int(partes[2])
            # Asumimos siglo 21 (20xx) - un heurístico simple que sirve para este dataset
            partes[2] = f"20{año:02d}"
        
        # padding para dd y mm
        partes[0] = partes[0].zfill(2)
        partes[1] = partes[1].zfill(2)
        return "/".join(partes)
    
    return fecha_str

def extract_metadata(doc: Document, file_path: Path) -> dict:
    """
    Extrae metadata (Nº de acta y fecha) intentando primero en los headers
    del documento, y luego cayendo en un fallback parseando el nombre del archivo.
    """
    num_acta = None
    fecha_acta = None
    fuente = "desconocida"
    
    # 1. Intentar en los headers
    header_text_concat = ""
    for section in doc.sections:
        if section.header:
            for p in section.header.paragraphs:
                txt = p.text.strip()
                if txt:
                    header_text_concat += txt + " "
                    
    if header_text_concat.strip():
        match_num = REGEX_ACTA_NUM_HEADER.search(header_text_concat)
        if match_num:
            num_acta = match_num.group(1).zfill(2)
            fuente = "header"
            
        match_fecha = REGEX_FECHA_HEADER.search(header_text_concat)
        if match_fecha:
            fecha_acta = match_fecha.group(1)
            fuente = "header"

    # 2. Fallback: nombre del archivo
    if not num_acta or not fecha_acta:
        filename = file_path.name
        
        if not num_acta:
            match_num = REGEX_ACTA_NUM_FILENAME.search(filename)
            if match_num:
                num_acta = match_num.group(1).zfill(2)
                if fuente == "desconocida":
                    fuente = "filename"
                else:
                    fuente += "+filename"
                    
        if not fecha_acta:
            match_fecha = REGEX_FECHA_FILENAME.search(filename)
            if match_fecha:
                fecha_acta = match_fecha.group(1)
                if "filename" not in fuente:
                    fuente = "filename" if fuente == "desconocida" else fuente + "+filename"

    if not num_acta:
        num_acta = "DESCONOCIDO"
        logger.warning(f"No se pudo extraer número de acta para {file_path.name}")
        
    if not fecha_acta:
        fecha_acta = "NO_ENCONTRADA"
        logger.warning(f"No se pudo extraer fecha para {file_path.name}")

    # Determinar año base (usando nombre de directorio principal si todo falla)
    año = "DESC"
    if fecha_acta != "NO_ENCONTRADA":
        norm_fecha = normalizar_fecha(fecha_acta)
        año = norm_fecha.split("/")[-1]
    else:
        # Fallback de año por directorio
        parent_dir = file_path.parent.name
        if parent_dir == "converted":
            parent_dir = file_path.parent.parent.parent.name # ej. CF 2022
        elif parent_dir == "actas":
            parent_dir = file_path.parent.parent.name
            
        match_yr = re.search(r'\d{4}', parent_dir)
        if match_yr:
            año = match_yr.group(0)

    # El tipo se puede inferir vagamente del nombre si dice EXT o EXTRAORDINARIA
    tipo = "ORDINARIA"
    fname_upper = file_path.name.upper()
    if "EXT" in fname_upper or "EXTRA" in fname_upper:
        tipo = "EXTRAORDINARIA"
    elif "VIRTUAL" in fname_upper:
        tipo = "VIRTUAL"

    return {
        "numero_acta": num_acta,
        "fecha_acta": normalizar_fecha(fecha_acta),
        "año": año,
        "fuente": fuente,
        "tipo": tipo
    }
