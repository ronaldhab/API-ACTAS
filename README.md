# Pipeline ETL de Actas de Consejo - SIGMA

Una herramienta desarrollada en Python para la automatización, procesamiento y extracción estructurada (ETL) de documentos institucionales (Actas de Consejo `.docx` y `.doc`). Este pipeline localiza documentos históricos o recientes, analiza su formato semántico de manera inteligente, agrupa anexos complejos en formatos *Key-Value* y emite toda la información lista para ser indexada en esquemas relacionales de una base de datos PostgreSQL mediante el backend de la Web App **SIGMA**.

## 🚀 Características Principales

1. **Conversión Legacy Automática**: Emplea `LibreOffice` nativo interconectado por CLI para convertir en lote archivos bi-direccionales de la era `.doc` antigua al estándar moderno `.docx`.
2. **Máquina de Estado de Lectura**: Transita dinámicamente sobre la **Sección 6 (Comisión de Mesa)**, abstrayendo con limpieza subpuntos estructurados (6.1, 6.2, etc.), sus contenidos, y categorizando sus Acuerdos o Notas explícitas, parando de forma segura el bucle al impactar con la Sección 7.
3. **Escáner Deduplicador Inteligente**: Diferencia y excluye documentos en blanco (Asistencias, carpetas oficios) y compara colisiones de repetidos para preferir la "Versión Definitiva" de un acta sobre sus revisiones inconclusas.
4. **Agrupación Modular de Anexos / Tablas**: Parsea cualquier tabla adosada a un subpunto bajo formatos horizontales o verticales y esquematiza diccionarios JSON jerárquicos de forma desasistida, reconociendo agrupaciones como "Principales / Suplentes".
5. **Modos de Funcionamiento Múltiples**: Puede escanear de corrido múltiples años de directorios, o funcionar como API de línea de comando recibiendo un solo archivo para integrarse a subidas web.

## 📦 Requisitos Previos

*   **Python 3.10+**
*   Librería externa **python-docx**
*   Tener instalado [**LibreOffice**](https://es.libreoffice.org/) localmente (Obligatorio únicamente si existen archivos `.doc` antiguos sin migrar en el pipeline).

## 🛠️ Instalación

1. Clona o sitúa este repositorio base (`sigma_etl`) en un directorio que comparta rama principal con tu carpeta persistente de Actas.
2. Instala los requerimientos:
    ```bash
    pip install -r requirements.txt
    ```

## ⚙️ Uso e Instrucciones

El programa puede operar en dos vertientes lógicas, controladas desde el orquestador principal `main.py`.

### Modo Batch (Masivo)
Lee recursivamente los directorios configurados (por defecto `CF 2022`, `CF 2023`, `CF 2024`, `Recursos`), hace conversión previa, los filtra, extrae todo y emite un gran volumen JSON consolidante:

```bash
python main.py
```
**Salida**: `output/actas_extraidas.json` (consolidado) y `output/errores.json` (reporte global de excepciones).

### Modo API (Archivo Individual)
Apunta el mecanismo a un único y preciso archivo mediante el flag `--file`. Esto está optimizado para que arquitecturas backend soliciten lectura instantánea al subir un documento:

```bash
python main.py --file "C:\Rutas\absolutas\ACTA_ejemplo.docx"
```

Alternativamente puedes decirle en qué directorio colocar el archivo resultante:
```bash
python main.py --file "ACTA_ejemplo.docx" --output "C:\Servidor\temporal\"
```
**Salida**: `%nombre_del_archivo%_extraida.json`.

## 📂 Arquitectura Explicada

*   `main.py`: Punto de entrada unificado y Orquestador de fases.
*   `config.py`: Gestor central de rutas globales y Diccionario maestro de TODAS las expresiones regulares (Regex) de búsqueda.
*   `logger_config.py`: Logger avanzado de operaciones exportado dualmente a consola y al archivo permanente `/output/etl.log`.
*   `models.py`: Estructuras de Datos robustas de tipado (`Dataclass`) validando el contrato de Salida de los objetos `SubPunto` y el reporte Final `ActaResult`.
*   `doc_converter.py`: Middleware que invoca `soffice --headless` agnóstico a SO.
*   `file_explorer.py`: Módulo iterativo de deduplicación de metadatos del file system.
*   `metadata_extractor.py`: Analítica de metadatos estáticos desde headers de docx o heurística de los nombres del archivo en caso de ser corrompidos.
*   `section_parser.py`: El corazón del Engine, iterador de secuencias XML / Blocks capturando Párrafos y Tablas, y traduciendo irregularidades relacionales a Diccionarios asimilables (`Anexos`).
*   `output_formatter.py`: Sanitizado y escritura serializada JSON amigable a Postgres.
