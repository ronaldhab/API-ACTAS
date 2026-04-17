import logging
import os

def setup_logger(log_file="output/etl.log") -> logging.Logger:
    """Configura y retorna el logger principal para el ETL."""
    
    # Asegurar que el directorio del log existe
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    logger = logging.getLogger("sigma_etl")
    logger.setLevel(logging.DEBUG)

    # Si ya tiene handlers, limpiarlos (para no duplicar en repetidas ejecuciones en REPL)
    if logger.handlers:
        logger.handlers.clear()

    # Formateador
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Handler para consola (Nivel INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Handler para archivo (Nivel DEBUG)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Instancia global del logger para ser importada por otros módulos
logger = setup_logger()
