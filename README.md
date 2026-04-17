# Pipeline ETL de Actas de Consejo - SIGMA

Una herramienta desarrollada en Python para la automatización, procesamiento y extracción estructurada (ETL) de documentos institucionales (Actas de Consejo `.docx` y `.doc`). Este pipeline localiza documentos históricos o recientes, analiza su formato semántico de manera inteligente, agrupa anexos complejos en formatos *Key-Value* y emite toda la información lista para ser indexada en esquemas relacionales de una base de datos PostgreSQL mediante el backend de la Web App **SIGMA**.

## 🚀 Características Principales

1. **Escaneo de Directorios Dinámico**: Detecta automáticamente en el directorio base cualquier carpeta que inicie con `CF ` (por ejemplo, `CF 2024`, `CF 2025`, etc.) sin requerir configuraciones rígidas.
2. **Conversión Legacy Automática**: Emplea `LibreOffice` nativo interconectado por CLI para convertir en lote archivos bi-direccionales de la era `.doc` antigua al estándar moderno `.docx`.
3. **Máquina de Estado de Lectura**: Transita dinámicamente sobre la **Sección 6 (Comisión de Mesa)**, abstrayendo con limpieza subpuntos estructurados (6.1, 6.2, etc.), sus contenidos, y categorizando sus Acuerdos o Notas explícitas, parando de forma segura el bucle al impactar con la Sección 7.
4. **Escáner Deduplicador Inteligente**: Diferencia y excluye documentos en blanco (Asistencias, carpetas oficios) y compara colisiones de repetidos para preferir la "Versión Definitiva" de un acta sobre sus revisiones inconclusas.
5. **Agrupación Modular de Anexos / Tablas**: Parsea cualquier tabla adosada a un subpunto bajo formatos horizontales o verticales y esquematiza diccionarios JSON jerárquicos de forma desasistida, reconociendo agrupaciones como "Principales / Suplentes".
6. **Modos de Funcionamiento Múltiples**: Puede escanear de corrido múltiples años de directorios, o funcionar como API de línea de comando recibiendo un solo archivo para integrarse a arquitecturas de microservicios.

## 📦 Requisitos Previos

*   **Python 3.10+**
*   Librería externa **python-docx**
*   Tener instalado [**LibreOffice**](https://es.libreoffice.org/) localmente (Obligatorio únicamente si existen archivos `.doc` antiguos sin migrar en el pipeline).

## 🛠️ Instalación

1. Clona o sitúa este repositorio base (`sigma_etl`) en el directorio principal junto a tu árbol de carpetas de Actas.
2. Instala los requerimientos:
    ```bash
    pip install -r sigma_etl/requirements.txt
    ```

## ⚙️ Uso e Instrucciones

El programa puede operar en dos vertientes lógicas, controladas desde el orquestador principal `main.py`.

### Modo Batch (Masivo)
Detecta de manera dinámica y automática cualquier directorio que comience por 'CF' directamente sobre la raíz de ejecución, escanea las actas en sus raíces o subcarpetas (`actas`), hace conversión previa, filtra el ruido documental, extrae la información y emite un gran volumen JSON consolidado:

```bash
python sigma_etl/main.py
```
**Salida**: `sigma_etl/output/actas_extraidas.json` (consolidado) y reportes de error/excepciones.

### Modo API (Archivo Individual)
Apunta el mecanismo a un único y preciso archivo mediante el flag `--file`. Esto está optimizado para que arquitecturas backend o web apps soliciten lectura de forma unitaria:

```bash
python sigma_etl/main.py --file "C:\Rutas\absolutas\ACTA_ejemplo.docx"
```

Alternativamente puedes decirle en qué directorio colocar el archivo resultante:
```bash
python sigma_etl/main.py --file "ACTA_ejemplo.docx" --output "C:\Servidor\temporal"
```
**Salida**: El JSON se guardará como `%nombre_del_archivo%_extraida.json` en la ruta especificada o por defecto en `/output`.

## 📂 Arquitectura del Sistema

La herramienta aplica un diseño modular orientado a dominios (core, extractores, utilidades) para favorecer el mantenimiento y la escalabilidad de reglas documentales.

*   **`sigma_etl/main.py`**: Punto de entrada unificado y herramienta de línea de comandos (CLI). Orquesta la fase de descubrimiento, extracción, procesado de errores y serialización.

### 🧠 `core/` (Estructura y Lógica Múltiple)
*   `config.py`: Gestor central de configuración. Contiene el auto-descubrimiento dinámico de rutas analizando carpetas en la raíz local y el diccionario maestro de TODAS las expresiones regulares (Regex) de búsqueda y segmentación.
*   `logger.py`: Logger robusto configurado para emitir mensajes tanto por consola estándar como al archivo permanente `/output/etl.log`.
*   `models.py`: Modelos de Datos nativos basados en `dataclasses` que aseguran el contrato estricto de tipos de los objetos transaccionales (`SubPunto`, `ActaResult`).

### 🔎 `extractors/` (Motores de Recolección de Información)
*   `metadata_extractor.py`: Realiza analítica iterativa para hallar metadatos clave (Números de acta, fechas, identificadores) preferentemente desde el content-header o cuerpo, acudiendo a heurística sobre el nombre del archivo si hay defectos de redacción.
*   `section_parser.py`: El corazón absoluto del ciclo ETL. Funciona como una máquina de estados, recorriendo párrafos provenientes de MS Word (`python-docx`), interceptando la "Sección 6", emparejando tablas embebidas, detectando Acuerdos formalizados y mapeando jerarquías mediante expresiones regulares para construir el objeto final.

### 🛠️ `utils/` (Herramientas Auxiliares I/O)
*   `doc_converter.py`: Módulo que interactúa con la línea de comandos del Sistema Operativo para invocar procesos `soffice --headless` y lograr migrar en lote documentos binarios `.doc` viejos al formato comprimido `.docx` estructurable.
*   `file_explorer.py`: Subsistema de exploración recursiva. Diferencia tipos de documentos y aplica algoritmos de puntuación para deduplicar documentos que presentan distintas revisiones o duplicados mal nombrados (por ej. priorizando una versión que incluya "DEF").
*   `output_formatter.py`: Motor final que genera directorios si no existen y deposita los diccionarios extraídos con un formato limpio en JSON (`utf-8` y `ensure_ascii=False`) de forma transparente para Postgres.
