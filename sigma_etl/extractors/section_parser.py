from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
import re

from core.config import (
    REGEX_SECTION_6_HEADER, REGEX_SUBPUNTO_6, REGEX_SECTION_7_START,
    REGEX_NOTA_CM, REGEX_ACUERDO
)
from core.models import SubPunto
from core.logger import logger
from typing import List, Tuple

def iter_block_items(parent):
    """
    Produce un generador de objetos Paragraph y Table secuencialmente
    en el orden real en que aparecen en el documento.
    """
    if isinstance(parent, DocumentObject):
        parent_elm = parent.element.body
    elif hasattr(parent, '_p'):
        parent_elm = parent._p
    elif hasattr(parent, '_element'):
        parent_elm = parent._element
    else:
        parent_elm = parent

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

def format_table(matriz: List[List[str]]) -> list:
    """Intenta convertir una matriz en una lista de diccionarios (columnas fijas) o en un dict llave-valor."""
    if not matriz:
        return []
        
    num_cols = len(matriz[0]) if matriz[0] else 0
    # Es regular si todas las filas tienen > 1 columna y misma longitud
    is_regular_table = all(len(row) == num_cols for row in matriz) and num_cols > 1
    
    if is_regular_table:
        headers = matriz[0]
        data = []
        for row in matriz[1:]:
            row_dict = {}
            for i, val in enumerate(row):
                key = headers[i] if headers[i] else f"Columna_{i}"
                row_dict[key] = val
            data.append(row_dict)
        return data
        
    # Irregular / Clave-Valor (Ej: columnas puenteadas o vertical)
    grouped = {}
    for row in matriz:
        if not row: continue
        k = row[0] if row[0] else "Dato_sin_titulo"
        vals = row[1:]
        if k not in grouped: grouped[k] = []
        grouped[k].append(vals)

    data_dict = {}
    for k, list_of_vals in grouped.items():
        if len(list_of_vals) == 1:
            row_vals = list_of_vals[0]
            if not row_vals:
                data_dict[k] = ""
            elif len(row_vals) == 1:
                data_dict[k] = row_vals[0]
            else:
                data_dict[k] = row_vals
        else:
            # Múltiples filas para la misma clave.
            row_len = len(list_of_vals[0])
            # Si todas tienen la misma longitud y tiene sentido de subtítulos (>1 cols)
            if row_len > 1 and all(len(r) == row_len for r in list_of_vals):
                # Asumimos que la primera fila actúa como subtítulos
                subheaders = list_of_vals[0]
                sub_dict = {sh: [] for sh in subheaders}
                for r in list_of_vals[1:]:
                    for i, sh in enumerate(subheaders):
                        sub_dict[sh].append(r[i])
                data_dict[k] = sub_dict
            else:
                # Comportamiento general: mezclas de tamaños o lista simple
                if all(len(r) == 1 for r in list_of_vals):
                    data_dict[k] = [r[0] for r in list_of_vals]
                else:
                    data_dict[k] = list_of_vals
                    
    return [data_dict]


def parse_fake_table(lines: List[str], inherited_headers: List[str] = None) -> Tuple[list, list]:
    """Parsea una tabla manual (tabulaciones) asignando herencia de cabeceras."""
    result = {}
    current_title = "Dato_sin_titulo"
    current_headers = inherited_headers if inherited_headers else []

    for line in lines:
        parts = [p.strip() for p in line.split('\t') if p.strip()]
        if not parts: continue
        
        is_title = False
        if len(parts) == 1:
            text = parts[0]
            # Heurística para títulos (e.g. CDCH, Jurado Sugerido)
            if text.isupper() or (len(text.split()) <= 3 and not '(' in text):
                is_title = True

            if is_title:
                current_title = text
                if current_title not in result:
                    result[current_title] = {}
                    # Pre-llenar cabeceras previas
                    if current_headers:
                        for h in current_headers: result[current_title][h] = []
            else:
                if current_headers:
                    if current_title not in result: result[current_title] = {}
                    for idx, h in enumerate(current_headers):
                        if h not in result[current_title]: result[current_title][h] = []
                        if idx == 0: result[current_title][h].append(text)
                        else: result[current_title][h].append('')
                else:
                    if current_title not in result: result[current_title] = []
                    if isinstance(result[current_title], list): result[current_title].append(text)
        else:
            # Multi-columna
            if not current_headers:
                current_headers = parts
                if current_title not in result: result[current_title] = {}
                for h in current_headers: result[current_title][h] = []
            else:
                if parts == current_headers: continue
                if current_title not in result or not isinstance(result[current_title], dict):
                    result[current_title] = {}
                    
                for h in current_headers:
                    if h not in result[current_title]: result[current_title][h] = []
                
                for idx, h in enumerate(current_headers):
                    if idx < len(parts):
                        result[current_title][h].append(parts[idx])
                    else:
                        result[current_title][h].append('')

    return [result], current_headers


def parse_section_6(doc: Document, filename: str) -> Tuple[List[SubPunto], List[str]]:
    """
    Implementa la máquina de estados para parsear la sección 6.
    Retorna una tupla (lista_de_subpuntos, lista_de_warnings)
    """
    state = "SEARCHING"
    result: List[SubPunto] = []
    current_subpunto = None
    warnings = []
    
    # Combinamos todos los bloques de contenido (párrafos normales y tablas) en orden
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            txt = block.text.strip()
            if not txt:
                # Ignorar saltos de línea vacíos extra
                if current_subpunto and state == "IN_SECTION_6":
                     current_subpunto.contenido += "\n" 
                continue
                
            if state == "SEARCHING":
                if REGEX_SECTION_6_HEADER.search(txt):
                    state = "IN_SECTION_6"
                    logger.debug(f"[{filename}] Inicio explícito Sección 6 detectado.")
                elif REGEX_SUBPUNTO_6.match(txt):
                    # Empieza directamente con un 6.x
                    state = "IN_SECTION_6"
                    logger.debug(f"[{filename}] Inicio implícito Sección 6 por subpunto.")
                    
                    # Procesar este primer subpunto
                    num_match = REGEX_SUBPUNTO_6.match(txt)
                    numero = num_match.group(1)
                    texto_restante = txt[num_match.end():].strip()
                    
                    current_subpunto = SubPunto(
                        numero=numero,
                        contenido=texto_restante,
                        nota_comision="",
                        acuerdo=""
                    )
                    
            elif state == "IN_SECTION_6":
                if REGEX_SECTION_7_START.match(txt):
                    # FIN - Cortar aquí
                    if current_subpunto:
                        result.append(current_subpunto)
                        current_subpunto = None
                    logger.debug(f"[{filename}] Fin de Sección 6 (detectado 7.x).")
                    break
                    
                elif REGEX_SUBPUNTO_6.match(txt):
                    # Nuevo subpunto
                    if current_subpunto:
                        result.append(current_subpunto)
                        
                    num_match = REGEX_SUBPUNTO_6.match(txt)
                    numero = num_match.group(1)
                    texto_restante = txt[num_match.end():].strip()
                    
                    current_subpunto = SubPunto(
                        numero=numero,
                        contenido=texto_restante,
                        nota_comision="",
                        acuerdo=""
                    )
                    
                elif REGEX_NOTA_CM.match(txt):
                    if current_subpunto:
                        match_nota = REGEX_NOTA_CM.match(txt)
                        if not current_subpunto.nota_comision:
                            current_subpunto.nota_comision = match_nota.group(1).strip()
                        else:
                            current_subpunto.nota_comision += " " + match_nota.group(1).strip()
                
                elif REGEX_ACUERDO.match(txt):
                    if current_subpunto:
                        match_acuerdo = REGEX_ACUERDO.match(txt)
                        if not current_subpunto.acuerdo:
                            current_subpunto.acuerdo = match_acuerdo.group(1).strip()
                        else:
                            current_subpunto.acuerdo += " " + match_acuerdo.group(1).strip()
                
                else:
                    # Texto que pertenece al subpunto actual
                    if current_subpunto:
                        current_subpunto.contenido += f"\n{txt}"
                        
        elif isinstance(block, Table):
            if state == "IN_SECTION_6" and current_subpunto:
                # Capturar formato de tabla entera como matriz bidimensional,
                # evitando duplicación de celdas combinadas (merged cells)
                matriz = []
                for row in block.rows:
                    uniq_cells = []
                    for cell in row.cells:
                        if cell._tc not in [u._tc for u in uniq_cells]:
                            uniq_cells.append(cell)
                    
                    fila = [cell.text.strip() for cell in uniq_cells]
                    matriz.append(fila)
                    
                # Aplicamos una transformación inteligente dict
                structured_dict = format_table(matriz)
                if structured_dict:
                    current_subpunto.anexos.append(structured_dict)

    # Si terminó el documento sin encontrar un 7.x
    if state == "IN_SECTION_6":
        if current_subpunto:
            result.append(current_subpunto)
        warnings.append("Fin de documento sin detectar sección 7 de forma explícita.")
        
    if state == "SEARCHING":
        warnings.append("Sección 6 no encontrada ni inicio de subpuntos 6.x.")
        
    # --- POST-PROCESAMIENTO ---
    # Detectar "fake tables" hechas con tabulaciones dentro del contenido
    for sp in result:
        if not sp.contenido: continue
        
        blocks = re.split(r'\n{2,}', sp.contenido.strip())
        new_contenido = []
        last_fake_headers = [] # Estado mantenido a lo largo de los bloques aislados
        
        for block in blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines: continue
            
            # Si el bloque entero simula una tabla usando tabs internamente (\t)
            if any('\t' in line for line in lines):
                structured_dict, last_fake_headers = parse_fake_table(lines, last_fake_headers)
                if structured_dict:
                    sp.anexos.extend(structured_dict)
            else:
                new_contenido.append(block)
                
        # Re-ensamblar contenido sin las tablas fake incrustadas
        sp.contenido = '\n\n'.join(new_contenido)
        
    return result, warnings
