import json
from pathlib import Path
from typing import List, Dict

from core.models import ActaResult
from core.logger import logger

def clean_dict(data: dict) -> dict:
    """Función de ayuda para limpiar y estandarizar datos de los dataclasses dict."""
    # Convert keys to snake_case just in case they aren't, though they are in models
    return {k: v for k, v in data.items()}

def save_to_json(actas: List[ActaResult], output_dir: str = "output"):
    """
    Guarda los resultados estructurados en formato JSON (optimizado para PostgreSQL).
    Genera dos archivos:
    1. actas_extraidas.json - El JSON principal.
    2. errores.json - Reporte de los documentos fallidos o advertencias.
    """
    out_path = Path(output_dir)
    out_path.mkdir(exist_ok=True, parents=True)

    # 1. Armar datos principales
    actas_data = []
    lista_errores = []

    stats = {
        "escaneados": 0, # lo registraremos aprox con len(actas) y errores
        "exitosos": 0,
        "con_warnings": 0,
        "fallidos": 0
    }

    for acta in actas:
        stats["escaneados"] += 1
        actas_data.append(acta.to_dict())

        # Revisar errores
        if "FATAL" in acta.errores:
            stats["fallidos"] += 1
            lista_errores.append({
                "archivo": acta.archivo_origen,
                "gravedad": "FATAL",
                "mensajes": acta.errores
            })
        elif len(acta.errores) > 0:
            stats["con_warnings"] += 1
            lista_errores.append({
                "archivo": acta.archivo_origen,
                "gravedad": "WARNING",
                "mensajes": acta.errores
            })
        else:
            stats["exitosos"] += 1

    # Estructura principal optimizada
    payload_json = {
        "metadata_ejecucion": {
            "version_script": "1.0.0",
            "total_actas_procesadas": len(actas),
        },
        "actas": actas_data
    }

    reporte_errores = {
        "resumen": stats,
        "errores": lista_errores
    }

    # Escritura archivos
    main_file = out_path / "actas_extraidas.json"
    err_file = out_path / "errores.json"

    with open(main_file, "w", encoding="utf-8") as f:
        json.dump(payload_json, f, ensure_ascii=False, indent=2)
    
    with open(err_file, "w", encoding="utf-8") as f:
        json.dump(reporte_errores, f, ensure_ascii=False, indent=2)

    logger.info(f"Guardado exitoso JSON principal: {main_file}")
    logger.info(f"Guardado exitoso JSON de errores: {err_file}")
    logger.info(f"Resumen de Extracción: Exitosos: {stats['exitosos']} | Warnings: {stats['con_warnings']} | Fallidos: {stats['fallidos']}")
