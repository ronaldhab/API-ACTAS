import re

import os

# Rutas base a escanear (relativas al directorio donde se ejecute main.py, que será SIGMA)
ACTAS_DIRS = []
base_path = "."
if os.path.exists(base_path):
    for folder in os.listdir(base_path):
        if folder.startswith("CF") and os.path.isdir(os.path.join(base_path, folder)):
            # Verificamos si existe el subdirectorio 'actas'
            if os.path.isdir(os.path.join(base_path, folder, "actas")):
                ACTAS_DIRS.append(f"{folder}/actas")
            else:
                ACTAS_DIRS.append(folder)

# Prefijos de archivos a EXCLUIR en file_explorer.py
EXCLUDED_PREFIXES = [
    "ASISTENCIA",
    "CCC-",
    "PERSONAL",
    "CEAP",
    "Oficios",
    "6.29" # E.g., 6.29.Acta de Defensa...
]

# Expresiones regulares pre-compiladas

# --- Detección del HEADER de la sección 6 ---
REGEX_SECTION_6_HEADER = re.compile(
    r'^(?:6\.\s+)?COMISI[OÓ]N\s+DE\s+MESA',
    re.IGNORECASE
)

# --- Detección de SUB-PUNTOS 6.x ---
# Ej: "6.1.", "6.1", "6.9.Comunicación", "6.51."
REGEX_SUBPUNTO_6 = re.compile(
    r'^(6\.\d{1,3})\.?\s*'
)

# --- Detección del INICIO de la sección 7 (FIN de sección 6) ---
# Ej: "7.", "7.1.", "7. CASOS DIFERIDOS", "7 CASOS DIFERIDOS"
REGEX_SECTION_7_START = re.compile(
    r'^(?:7\.(?:\s+|\d)|7\.?\s*CASOS\s+DIFERIDOS)',
    re.IGNORECASE
)

# --- Extracción de Nº de acta y fecha desde HEADER del documento ---
# Ej: "ACTA  No 14", "AGENDA  No. 09"
REGEX_ACTA_NUM_HEADER = re.compile(
    r'(?:ACTA|AGENDA)\s+No\.?\s*(\d{1,3})',
    re.IGNORECASE
)
# Ej: "DEL 12/07/2022"
REGEX_FECHA_HEADER = re.compile(
    r'DEL\s+(\d{1,2}/\d{1,2}/\d{4})',
    re.IGNORECASE
)

# --- Extracción de Nº de acta y fecha desde NOMBRE DE ARCHIVO ---
# Ej: "ACTA 01 DEL 16-01-2024.docx", "ACTA CF 14.docx"
REGEX_ACTA_NUM_FILENAME = re.compile(
    r'ACTA\s+(?:CF\s+)?(\d{1,3})',
    re.IGNORECASE
)
# Ej: "DEL 16-01-2024", "DEL 11-04-23"
REGEX_FECHA_FILENAME = re.compile(
    r'DEL\s+(\d{1,2}-\d{1,2}-\d{2,4})',
    re.IGNORECASE
)

# --- Detección de notas y acuerdos dentro de sub-puntos ---
REGEX_NOTA_CM = re.compile(
    r'^Nota\s+de\s+la\s+Comisi[oó]n\s+de\s+Mesa\s*:?\s*(.*)',
    re.IGNORECASE
)

REGEX_ACUERDO = re.compile(
    r'^Acuerdo\s*:?\s*(.*)',
    re.IGNORECASE
)
