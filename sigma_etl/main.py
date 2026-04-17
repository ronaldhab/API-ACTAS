import sys
import argparse
from pathlib import Path
from docx import Document
import traceback
import json

from core.logger import logger
from utils.file_explorer import get_actas_files
from extractors.metadata_extractor import extract_metadata
from extractors.section_parser import parse_section_6
from utils.output_formatter import save_to_json
from core.models import ActaResult
from utils.doc_converter import convert_doc_to_docx

def process_file(file_path: Path, base_dir: Path = None) -> ActaResult:
    """Procesa un archivo .docx individualmente."""
    if base_dir is None:
        base_dir = Path(__file__).parent.parent
    
    try:
        rel_path = str(file_path.relative_to(base_dir))
    except ValueError:
        # If the file is not under base_dir (e.g. arbitrary path), just use the file name or full path
        rel_path = str(file_path)
    
    acta_res = ActaResult(
        archivo_origen=rel_path,
        numero_acta="",
        fecha_acta="",
        año="",
        tipo="ORDINARIA",
        metadata_fuente="",
        sub_puntos=[],
        errores=[]
    )

    try:
        doc = Document(file_path)
    except Exception as e:
        logger.error(f"Error fatal abriendo {file_path.name}: {e}")
        acta_res.errores.append("FATAL: " + str(e))
        return acta_res

    # Fase: Extracción de Metadata
    meta = extract_metadata(doc, file_path)
    acta_res.numero_acta = meta["numero_acta"]
    acta_res.fecha_acta = meta["fecha_acta"]
    acta_res.año = meta["año"]
    acta_res.tipo = meta["tipo"]
    acta_res.metadata_fuente = meta["fuente"]

    # Fase: Extracción Sección 6
    sub_puntos, warnings = parse_section_6(doc, file_path.name)
    acta_res.sub_puntos = sub_puntos
    acta_res.errores.extend(warnings)

    return acta_res

def process_single_file(file_path_str: str, output_dir: str):
    """Procesa un archivo único introducido por línea de comandos."""
    file_path = Path(file_path_str)
    
    if not file_path.exists():
        logger.error(f"El archivo especificado no existe: {file_path_str}")
        sys.exit(1)
        
    if file_path.suffix.lower() == '.doc':
        logger.warning(f"Se proporcionó un archivo .doc: {file_path_str}. Se intentará convertir primero...")
        convert_doc_to_docx(str(file_path.parent))
        file_path = file_path.with_suffix('.docx')
        if not file_path.exists():
             logger.error("No se pudo convertir el archivo .doc a .docx.")
             sys.exit(1)

    if file_path.suffix.lower() != '.docx':
        logger.error(f"El archivo debe ser formato .docx: {file_path_str}")
        sys.exit(1)

    logger.info(f"Procesando archivo individual: {file_path.name}")
    try:
        acta = process_file(file_path)
        
        # Save output for just this file
        out_path = Path(output_dir)
        out_path.mkdir(exist_ok=True, parents=True)
        
        # Guardar en JSON individual
        output_file = out_path / f"{file_path.stem}_extraida.json"
        
        payload_json = {
            "metadata_ejecucion": {
                "version_script": "1.0.0",
                "archivo_origen": str(file_path)
            },
            "acta": acta.to_dict()
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload_json, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Procesamiento completado. Resultado guardado en: {output_file}")
        
    except Exception as e:
        logger.error(f"Excepción no capturada en {file_path.name}: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="SIGMA ETL - Extracción de Actas de Consejo")
    parser.add_argument("--file", type=str, help="Ruta a un archivo .docx específico para procesar de forma individual.")
    parser.add_argument("--output", type=str, default=str(Path(__file__).parent / "output"), help="Directorio de salida para los JSONs generados.")
    
    args = parser.parse_args()

    root_dir = str(Path(__file__).parent.parent)
    
    # Procesar archivo individual si se pasa por argumento
    if args.file:
        process_single_file(args.file, args.output)
        return

    logger.info("Iniciando Sigma ETL de Actas de Consejo en modo BATCH...")

    # Paso Previo: Convertir .doc a .docx
    logger.info("Fase 2: Conversión batch de archivos legacy (.doc)")
    convert_doc_to_docx(root_dir)

    # Descubrir archivos
    logger.info("Fase 3: Descubrimiento y filtrado de archivos.")
    archivos = get_actas_files(root_dir)

    if not archivos:
        logger.warning("No se encontraron archivos .docx para procesar. Finalizando.")
        sys.exit(0)

    # Procesar
    resultados = []
    logger.info(f"Fase 4 & 5: Procesando {len(archivos)} documentos...")
    
    for idx, filepath in enumerate(archivos, 1):
        logger.info(f"[{idx}/{len(archivos)}] Procesando: {filepath.name}")
        try:
            acta = process_file(filepath)
            resultados.append(acta)
        except Exception as e:
            logger.error(f"Excepción no capturada en {filepath.name}: {e}")
            logger.debug(traceback.format_exc())
            # Insert a fatal dummy to track it
            resultados.append(ActaResult(
                archivo_origen=str(filepath.relative_to(root_dir) if root_dir in str(filepath) else filepath),
                numero_acta="FATAL",
                fecha_acta="",
                año="",
                tipo="",
                metadata_fuente="",
                sub_puntos=[],
                errores=["FATAL_EXCEPTION_UNHANDLED: " + str(e)]
            ))

    # Guardar
    logger.info("Fase 6: Exportando resultados a JSON")
    save_to_json(resultados, output_dir=args.output)
    
    logger.info("Pipeline batch completado exitosamente.")

if __name__ == "__main__":
    main()
