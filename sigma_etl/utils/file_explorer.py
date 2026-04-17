from pathlib import Path
from typing import List, Dict
import re

from core.config import ACTAS_DIRS, EXCLUDED_PREFIXES
from core.logger import logger

def is_excluded(filename: str) -> bool:
    """Verifica si el archivo debe ser excluido según su prefijo o nombre."""
    name_upper = filename.upper()
    for prefix in EXCLUDED_PREFIXES:
        if name_upper.startswith(prefix.upper()):
            return True
        # Particularidad para '6.29.Acta...'
        if prefix in filename:
            return True
    # Excluir PDFs
    if name_upper.endswith(".PDF"):
        return True
    return False

def extract_dedup_key(filename: str) -> str:
    """Extrae una clave base (Nº acta + fecha si es posible) para deduplicar.
       Si no se puede extraer algo confiable, retorna el nombre del archivo en lower."""
    # Extraer "ACTA XX" o similar para intentar agrupar
    match_acta = re.search(r'ACTA\s+(?:CF\s+)?(\d{1,3})', filename, re.IGNORECASE)
    match_fecha = re.search(r'DEL\s+(\d{1,2}-\d{1,2}-\d{2,4})', filename, re.IGNORECASE)
    
    if match_acta:
        key = f"ACTA_{match_acta.group(1).zfill(2)}"
        if match_fecha:
            key += f"_{match_fecha.group(1)}"
        return key
    return filename.lower()

def sort_duplicates(files: List[Path]) -> Path:
    """Dada una lista de archivos que parecen ser el mismo documento, 
       elige el mejor candidato (ej. el que dice 'DEF', o el que no tiene '(1)')."""
    if len(files) == 1:
        return files[0]
        
    def score(p: Path) -> int:
        name = p.name.upper()
        s = 0
        if "DEF" in name or "DEFINIT" in name:
            s += 10
        if "REV" in name:
            s += 5
        # Penaliza los que tienen (1), (2), etc.
        if re.search(r'\(\d\)', name):
            s -= 5
        return s

    return max(files, key=score)

def get_actas_files(base_dir: str) -> List[Path]:
    """Descubre, filtra y deduplica los archivos a procesar."""
    root_dir = Path(base_dir)
    all_files = []
    
    for dir_name in ACTAS_DIRS:
        target_dir = root_dir / dir_name
        if not target_dir.exists():
            logger.warning(f"El directorio {dir_name} no existe.")
            continue
            
        # Buscar .docx en la carpeta principal
        found = list(target_dir.glob("*.docx"))
        
        # Buscar también en subcarpeta "converted" si hay archivos .docx originados de .doc
        converted_dir = target_dir / "converted"
        if converted_dir.exists():
            found.extend(list(converted_dir.glob("*.docx")))
            
        all_files.extend(found)
        
    logger.info(f"Total archivos .docx encontrados (antes de filtros): {len(all_files)}")
    
    # Filtrar excluidos y agrupar para deduplicar
    grouped_files: Dict[str, List[Path]] = {}
    filtered_count = 0
    
    for file_path in all_files:
        if is_excluded(file_path.name):
            filtered_count += 1
            logger.debug(f"Excluyendo archivo: {file_path.name}")
            continue
            
        # Si es un reliquia oculta de Word (~$) ignorarlo
        if file_path.name.startswith("~$"):
            continue
            
        key = extract_dedup_key(file_path.stem)
        
        # Como los documentos están organizados en año, incluimos el año (nombre de la carpeta padre)
        # en la clave para no mezclar un "ACTA 01" de 2023 con uno de 2024
        # Nota: si viene de 'converted', el padre del padre es el año.
        year_folder = file_path.parent.name
        if year_folder == "converted":
            year_folder = file_path.parent.parent.name
            
        full_key = f"{year_folder}_{key}"
        
        if full_key not in grouped_files:
            grouped_files[full_key] = []
        grouped_files[full_key].append(file_path)
        
    logger.info(f"Archivos excluidos por regla de nombre: {filtered_count}")
    
    # Deduplicar
    final_files = []
    for key, duplicates in grouped_files.items():
        best_file = sort_duplicates(duplicates)
        final_files.append(best_file)
        if len(duplicates) > 1:
            logger.debug(f"Deduplicado {key}: {len(duplicates)} versiones -> elegida '{best_file.name}'")
            
    logger.info(f"Total de archivos a procesar tras filtro y deduplicación: {len(final_files)}")
    
    # Ordenar por año y nombre
    return sorted(final_files, key=lambda p: str(p))

if __name__ == "__main__":
    files = get_actas_files(str(Path(__file__).parent.parent))
    for f in files[:10]:
        print(f.relative_to(Path(__file__).parent.parent))
