import os
import subprocess
from pathlib import Path
import shutil
from typing import List

from core.config import ACTAS_DIRS
from core.logger import logger

def get_libreoffice_path() -> str:
    """Intenta encontrar el ejecutable de LibreOffice en el sistema."""
    # En Windows comúnmente está en alguna de estas rutas:
    possible_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "soffice"  # Si está en el PATH
    ]
    
    for path in possible_paths:
        try:
            # Pasa un comando simple para ver si existe y responde
            result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return path
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            continue
    return None

def convert_doc_to_docx(base_dir: str) -> None:
    """Encuentra archivos .doc en un directorio y los convierte a .docx."""
    lo_path = get_libreoffice_path()
    if not lo_path:
        logger.error("No se encontró LibreOffice (soffice). Saltando conversión de .doc.")
        return

    # Usar cwd en el padre del proyecto para resolver rutas relativas
    root_dir = Path(__file__).parent.parent
    
    for dir_name in ACTAS_DIRS:
        target_dir = root_dir / dir_name
        if not target_dir.exists():
            continue
            
        doc_files = list(target_dir.glob("*.doc"))
        if not doc_files:
            continue
            
        logger.info(f"Encontrados {len(doc_files)} archivos .doc en {dir_name}. Iniciando conversión...")
        
        # Crear subcarpeta 'converted'
        converted_dir = target_dir / "converted"
        converted_dir.mkdir(exist_ok=True)
        
        for doc_file in doc_files:
            target_docx = converted_dir / (doc_file.stem + ".docx")
            if target_docx.exists():
                logger.debug(f"Saltando conversión, archivo ya existe: {target_docx.name}")
                continue
                
            logger.info(f"Convirtiendo: {doc_file.name}")
            try:
                # soffice --headless --convert-to docx --outdir <dir> <file>
                result = subprocess.run(
                    [
                        lo_path, 
                        "--headless", 
                        "--convert-to", 
                        "docx", 
                        "--outdir", 
                        str(converted_dir), 
                        str(doc_file)
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.debug(f"Conversión exitosa: {target_docx.name}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Error convirtiendo {doc_file.name}: {e.stderr}")
            except Exception as e:
                logger.error(f"Excepción inesperada convirtiendo {doc_file.name}: {str(e)}")

if __name__ == "__main__":
    convert_doc_to_docx(str(Path(__file__).parent.parent))
