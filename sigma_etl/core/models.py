import dataclasses
from dataclasses import dataclass, field
from typing import List, Any

@dataclass
class SubPunto:
    numero: str          # "6.1", "6.2", etc.
    contenido: str       # Texto completo del sub-punto
    nota_comision: str   # Texto de "Nota de la Comisión de Mesa:"
    acuerdo: str         # Texto de "Acuerdo:"
    anexos: List[Any] = field(default_factory=list) # Tablas interlineadas estructuradas como dicts

    def to_dict(self):
        return dataclasses.asdict(self)

@dataclass
class ActaResult:
    archivo_origen: str  # Ruta relativa del archivo
    numero_acta: str 
    fecha_acta: str      # Normalizada a DD/MM/YYYY
    año: str             # Extraído de la ruta o fecha
    tipo: str            # "ORDINARIA", "EXTRAORDINARIA", etc. (inferido o default)
    metadata_fuente: str # "header" o "filename"
    sub_puntos: List[SubPunto] = field(default_factory=list)
    errores: List[str] = field(default_factory=list)

    @property
    def total_subpuntos(self) -> int:
        return len(self.sub_puntos)

    def to_dict(self):
        d = dataclasses.asdict(self)
        d['total_subpuntos'] = self.total_subpuntos
        return d
