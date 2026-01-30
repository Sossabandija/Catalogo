"""
PATTERNS.PY - Extracción de patrones técnicos y atributos
Responsabilidad: Extraer atributos técnicos (diámetro, largo, material, etc.)
Método: Regex deterministas desde rules.yaml
Salida: Columnas con atributos extraídos + confianza de extracción
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ExtractedAttribute:
    """Atributo técnico extraído con metadatos"""
    name: str
    value: str
    unit: Optional[str] = None
    pattern_used: Optional[str] = None
    confidence: float = 1.0  # 0-1


class PatternExtractor:
    """
    Extrae atributos técnicos de nombres de productos.
    - Usa reglas deterministas (regex)
    - Rastreable: cada extracción registra qué patrón se usó
    - Evita ambigüedades: marca errores de interpretación
    """
    
    # Patrones universales (sin depender de config)
    UNIVERSAL_PATTERNS = {
        'diametro': [
            r'(\d+(?:[.,]\d+)?)\s*1/(\d+)\s*"',           # 1 1/8", 1 1/4"
            r'(\d+)/(\d+)\s*"',                            # 1/4", 3/8"
            r'(\d+(?:[.,]\d+)?)\s*(?:mm|mm\.)',           # 10mm, 2.5mm
            r'Ø\s*(\d+(?:[.,]\d+)?)',                     # Ø10, Ø12.5
        ],
        'largo': [
            r'(\d+(?:[.,]\d+)?)\s*(?:cm|cm\.)',           # 10cm, 12.5cm
            r'(\d+(?:[.,]\d+)?)\s*m(?:\D|$)',             # 5m, 2.5m (no "mm")
            r'largo\s*[:\s]*(\d+(?:[.,]\d+)?)',           # largo: 10
        ],
        'grosor': [
            r'(?:grosor|espesor|espesor)\s*[:\s]*(\d+(?:[.,]\d+)?)',
            r'(\d+(?:[.,]\d+)?)\s*mm\s*(?:grosor|espesor)',
        ],
        'material': [
            r'(?i)(acero|hierro|carbono|inox|inoxidable|cobre|aluminio|galvanizado)',
        ],
        'cantidad': [
            r'(?:pack|caja|bolsa|tubo|set|kit)\s*[:/=]?\s*(\d+)',
            r'(\d+)\s*(?:pz|pcs|unidades|metros)',
        ]
    }
    
    def __init__(self, rules_path: str = 'config/rules.yaml'):
        """
        Inicializa extractor de patrones.
        
        Args:
            rules_path: Path al archivo de reglas
        """
        self.rules = self._load_rules(rules_path)
        self._merge_patterns()
        logger.info("Extractor de patrones inicializado")
    
    def _load_rules(self, rules_path: str) -> Dict:
        """Carga reglas desde YAML."""
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Reglas no encontradas: {rules_path}")
            return {}
    
    def _merge_patterns(self) -> None:
        """Fusiona patrones de config con patrones universales."""
        self.patterns = {}
        
        # Primero agregar patrones universales
        for attr, regex_list in self.UNIVERSAL_PATTERNS.items():
            self.patterns[attr] = regex_list.copy()
        
        # Luego agregar/overwrite con los de config (si existen)
        if 'attributes' in self.rules:
            for attr_name, attr_config in self.rules['attributes'].items():
                if 'patterns' in attr_config:
                    if attr_name not in self.patterns:
                        self.patterns[attr_name] = []
                    self.patterns[attr_name].extend(attr_config['patterns'])
    
    def extract_all_attributes(self, product_name: str) -> Dict[str, List[ExtractedAttribute]]:
        """
        Extrae todos los atributos técnicos del nombre.
        
        Args:
            product_name: Nombre del producto
        
        Returns:
            Dict {nombre_atributo: [ExtractedAttribute]}
        """
        if not isinstance(product_name, str) or not product_name.strip():
            return {}
        
        results = {}
        product_name = str(product_name).upper()
        
        # Ejecutar cada extractor de atributo
        for attr_name, patterns in self.patterns.items():
            extracted = self._extract_attribute(product_name, attr_name, patterns)
            if extracted:
                results[attr_name] = extracted
        
        return results
    
    def _extract_attribute(self, text: str, attr_name: str, patterns: List[str]) -> List[ExtractedAttribute]:
        """
        Extrae un atributo específico usando múltiples patrones.
        
        Args:
            text: Texto donde buscar
            attr_name: Nombre del atributo
            patterns: Lista de regexes a probar
        
        Returns:
            Lista de atributos extraídos
        """
        extracted_values = set()  # Usar set para evitar duplicados
        results = []
        
        for pattern in patterns:
            try:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                
                for match in matches:
                    # Obtener valor (grupo 1, o grupos 1+2 si hay fracciones)
                    if match.lastindex == 1:
                        value = match.group(1)
                    elif match.lastindex == 2:
                        # Caso de fracciones: 1 1/8
                        value = f"{match.group(1)} {match.group(2)}/8\""
                    else:
                        continue
                    
                    # Evitar duplicados
                    if value not in extracted_values:
                        extracted_values.add(value)
                        
                        # Obtener unidad si existe en config
                        unit = self._get_unit_for_attribute(attr_name)
                        
                        results.append(ExtractedAttribute(
                            name=attr_name,
                            value=value,
                            unit=unit,
                            pattern_used=pattern,
                            confidence=0.95  # Regex con alta confianza
                        ))
            
            except re.error as e:
                logger.warning(f"Error en regex para {attr_name}: {str(e)}")
                continue
        
        return results
    
    def _get_unit_for_attribute(self, attr_name: str) -> Optional[str]:
        """Obtiene unidad estándar para atributo."""
        unit_map = {
            'diametro': 'pulgada/mm',
            'largo': 'cm/m',
            'grosor': 'mm',
            'peso': 'kg/g',
            'cantidad': 'unidades'
        }
        return unit_map.get(attr_name)
    
    def extract_to_dataframe(self, df: pd.DataFrame, name_column: str = 'Nombre_Limpio') -> pd.DataFrame:
        """
        Extrae atributos para todo el DataFrame.
        
        Args:
            df: DataFrame con productos
            name_column: Columna con nombres a procesar
        
        Returns:
            DataFrame original + columnas de atributos extraídos
        """
        df = df.copy()
        
        logger.info(f"Extrayendo atributos de {len(df)} registros...")
        
        # Estructuras para guardar resultados
        all_extracted = []
        
        for idx, row in df.iterrows():
            name = row.get(name_column, '')
            attributes = self.extract_all_attributes(name)
            all_extracted.append(attributes)
        
        # Procesar resultados y agregarlos al DataFrame
        df = self._flatten_attributes_to_columns(df, all_extracted)
        
        logger.info("✓ Extracción de atributos completada")
        
        return df
    
    def _flatten_attributes_to_columns(self, df: pd.DataFrame, 
                                      extracted_list: List[Dict]) -> pd.DataFrame:
        """
        Convierte lista de atributos extraídos en columnas del DataFrame.
        
        Args:
            df: DataFrame original
            extracted_list: Lista de dicts con atributos extraídos
        
        Returns:
            DataFrame con nuevas columnas
        """
        # Identificar todos los atributos únicos
        all_attributes = set()
        for extracted in extracted_list:
            all_attributes.update(extracted.keys())
        
        # Crear columnas para cada atributo
        for attr in sorted(all_attributes):
            df[f'Atributo_{attr}'] = None
            df[f'Atributo_{attr}_confianza'] = 0.0
            df[f'Atributo_{attr}_cantidad'] = 0
        
        # Llenar datos
        for idx, extracted in enumerate(extracted_list):
            for attr, values in extracted.items():
                if values:
                    # Valor principal (primer match)
                    df.at[idx, f'Atributo_{attr}'] = values[0].value
                    df.at[idx, f'Atributo_{attr}_confianza'] = values[0].confidence
                    df.at[idx, f'Atributo_{attr}_cantidad'] = len(values)
        
        return df
    
    def get_extraction_summary(self, df: pd.DataFrame) -> str:
        """
        Genera resumen de extracciones realizadas.
        
        Args:
            df: DataFrame con extracciones
        
        Returns:
            String con resumen
        """
        attr_columns = [col for col in df.columns if col.startswith('Atributo_') and col.endswith('_cantidad')]
        
        summary = """
        ╔════════════════════════════════════════╗
        ║   RESUMEN DE EXTRACCIÓN DE ATRIBUTOS   ║
        ╚════════════════════════════════════════╝
        
        📊 Atributos extraídos por categoría:
        """
        
        for col in attr_columns:
            attr_name = col.replace('Atributo_', '').replace('_cantidad', '')
            # Contar valores no nulos y no vacíos (funciona para strings)
            count = (df[col].notna() & (df[col].astype(str).str.strip() != '')).sum()
            pct = (count / len(df)) * 100 if len(df) > 0 else 0
            summary += f"\n        • {attr_name}: {count} ({pct:.1f}%)"
        
        return summary


# Funciones de conveniencia
def extract_attributes(df: pd.DataFrame, rules_path: str = 'config/rules.yaml') -> pd.DataFrame:
    """
    Extrae atributos técnicos de productos.
    
    Args:
        df: DataFrame con productos
        rules_path: Path a archivo de reglas
    
    Returns:
        DataFrame con atributos extraídos
    """
    extractor = PatternExtractor(rules_path)
    df_extracted = extractor.extract_to_dataframe(df)
    print(extractor.get_extraction_summary(df_extracted))
    return df_extracted


def normalize_measurement(value: str, target_unit: str = 'standard') -> Optional[str]:
    """
    Normaliza medidas a formato estándar.
    
    Args:
        value: Valor de medida
        target_unit: Unidad objetivo ('standard', 'metric', 'imperial')
    
    Returns:
        Valor normalizado o None
    """
    if not value:
        return None
    
    value = str(value).strip().upper()
    
    # Normalizar fracciones comunes
    fraction_map = {
        '1/4': '1/4"',
        '3/8': '3/8"',
        '1/2': '1/2"',
        '5/8': '5/8"',
        '3/4': '3/4"',
        '7/8': '7/8"',
        '1 1/4': '1 1/4"',
        '1 1/2': '1 1/2"',
    }
    
    for key, standard in fraction_map.items():
        if key in value:
            return standard
    
    return value
