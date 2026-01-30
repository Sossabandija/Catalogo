"""
ATTRIBUTES.PY - Validación y Normalización de Atributos
Responsabilidad: Asegurar que atributos extraídos sean válidos y normalizados
Método: Comparar contra valores conocidos, detectar inconsistencias
Salida: DataFrame con atributos validados + flags de confianza
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
import yaml
from fractions import Fraction

logger = logging.getLogger(__name__)


@dataclass
class ValidatedAttribute:
    """Atributo validado y normalizado"""
    name: str
    original_value: str
    normalized_value: str
    is_valid: bool
    confidence: float
    notes: str = ""


class AttributeValidator:
    """
    Valida y normaliza atributos extraídos.
    - Compara contra valores comunes/estándares
    - Detecta inconsistencias
    - Normaliza unidades
    - Marca confianza de validación
    """
    
    def __init__(self, rules_path: str = 'config/rules.yaml'):
        """
        Inicializa validador.
        
        Args:
            rules_path: Path a archivo de reglas
        """
        self.rules = self._load_rules(rules_path)
        self._build_lookup_tables()
        logger.info("Validador de atributos inicializado")
    
    def _load_rules(self, rules_path: str) -> Dict:
        """Carga reglas desde YAML."""
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Reglas no encontradas: {rules_path}")
            return {}
    
    def _build_lookup_tables(self) -> None:
        """Construye tablas de búsqueda para validación."""
        
        # Diámetros comunes (en pulgadas y mm)
        self.valid_diameters = set()
        if 'ranges' in self.rules and 'diametro_comun' in self.rules['ranges']:
            self.valid_diameters.update(self.rules['ranges']['diametro_comun'])
        
        # Agregar estándares universales
        self.valid_diameters.update([
            '1/4"', '5/16"', '3/8"', '7/16"', '1/2"', '5/8"', '3/4"', '7/8"',
            '1"', '1 1/8"', '1 1/4"', '1 3/8"', '1 1/2"', '2"',
            '3mm', '4mm', '5mm', '6mm', '8mm', '10mm', '12mm', '16mm', '20mm',
            '25mm', '32mm', '40mm', '50mm'
        ])
        
        # Largos comunes
        self.valid_lengths = set()
        if 'ranges' in self.rules and 'largo_comun' in self.rules['ranges']:
            self.valid_lengths.update(self.rules['ranges']['largo_comun'])
        
        self.valid_lengths.update([
            '5cm', '10cm', '15cm', '20cm', '25cm', '30cm', '40cm', '50cm',
            '60cm', '75cm', '100cm', '1m', '1.5m', '2m', '2.5m', '3m', '5m',
            '10m', '25m', '50m'
        ])
        
        # Materiales válidos
        self.valid_materials = set()
        if 'attributes' in self.rules and 'material' in self.rules['attributes']:
            if 'keywords' in self.rules['attributes']['material']:
                self.valid_materials.update(
                    [k.lower() for k in self.rules['attributes']['material']['keywords']]
                )
        
        self.valid_materials.update([
            'acero', 'hierro', 'acero inoxidable', 'inox', 'cobre',
            'aluminio', 'bronce', 'latón', 'plástico', 'poliéster',
            'galvanizado', 'cromado', 'fosfatado', 'negro', 'blanco'
        ])
        
        # Acabados válidos
        self.valid_finishes = {
            'galvanizado', 'cromado', 'fosfatado', 'plateado', 'oxidado',
            'brillante', 'mate', 'satinado', 'natural'
        }
    
    def validate_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Valida todos los atributos en el DataFrame.
        
        Args:
            df: DataFrame con atributos extraídos
        
        Returns:
            DataFrame con columnas adicionales de validación
        """
        df = df.copy()
        
        logger.info(f"Validando atributos de {len(df)} registros...")
        
        # Obtener columnas de atributos
        attr_columns = [col for col in df.columns if col.startswith('Atributo_') 
                       and not col.endswith('_confianza') and not col.endswith('_cantidad')]
        
        # Validar cada atributo
        for attr_col in attr_columns:
            attr_name = attr_col.replace('Atributo_', '')
            
            # Crear columna de validación
            df[f'{attr_col}_validado'] = df[attr_col].apply(
                lambda x: self._validate_single_attribute(attr_name, x) if pd.notna(x) else None
            )
        
        logger.info("✓ Validación de atributos completada")
        
        return df
    
    def _validate_single_attribute(self, attr_name: str, value: str) -> Optional[Dict]:
        """
        Valida un atributo individual.
        
        Args:
            attr_name: Nombre del atributo
            value: Valor a validar
        
        Returns:
            Dict con {normalized, is_valid, confidence, notes}
        """
        if not value or pd.isna(value):
            return None
        
        value = str(value).strip()
        
        # Dispatch según tipo de atributo
        if attr_name == 'diametro':
            return self._validate_diameter(value)
        elif attr_name == 'largo':
            return self._validate_length(value)
        elif attr_name == 'grosor':
            return self._validate_thickness(value)
        elif attr_name == 'material':
            return self._validate_material(value)
        elif attr_name == 'acabado':
            return self._validate_finish(value)
        elif attr_name == 'marca':
            return self._validate_brand(value)
        elif attr_name == 'cantidad':
            return self._validate_quantity(value)
        else:
            # Atributo desconocido: pasar sin validar
            return {
                'normalized': value,
                'is_valid': None,
                'confidence': 0.5,
                'notes': 'Atributo desconocido'
            }
    
    def _validate_diameter(self, value: str) -> Dict:
        """Valida diámetro."""
        value_upper = value.upper()
        
        # Búsqueda directa en tabla
        for valid_d in self.valid_diameters:
            if valid_d.upper() == value_upper:
                return {
                    'normalized': valid_d,
                    'is_valid': True,
                    'confidence': 0.95,
                    'notes': 'Diámetro estándar validado'
                }
        
        # Búsqueda parcial (para variantes de escritura)
        if self._is_similar_diameter(value_upper):
            return {
                'normalized': value_upper,
                'is_valid': True,
                'confidence': 0.75,
                'notes': 'Diámetro válido (formato variante)'
            }
        
        # Número válido pero no en tabla estándar
        if re.match(r'^\d+(?:[.,]\d+)?(?:mm|")?$', value):
            return {
                'normalized': value,
                'is_valid': True,
                'confidence': 0.6,
                'notes': 'Valor numérico válido (no en estándares)'
            }
        
        return {
            'normalized': value,
            'is_valid': False,
            'confidence': 0.2,
            'notes': 'Diámetro inválido o ambiguo'
        }
    
    def _is_similar_diameter(self, value: str) -> bool:
        """Verifica si diámetro es similar a uno válido."""
        # Normalizar: 1/4" vs 1/4 vs 0.25"
        value = value.replace('"', '').replace('MM', '').strip()
        
        # Convertir fracciones a decimales para comparación
        if '/' in value:
            try:
                frac = Fraction(value)
                return 0 < float(frac) < 10  # Rango razonable
            except:
                pass
        
        # Número en mm
        try:
            num = float(value.replace(',', '.'))
            return (0 < num < 100)  # Rango razonable para mm
        except:
            pass
        
        return False
    
    def _validate_length(self, value: str) -> Dict:
        """Valida largo."""
        value_upper = value.upper()
        
        # Búsqueda directa
        for valid_l in self.valid_lengths:
            if valid_l.upper() == value_upper:
                return {
                    'normalized': valid_l,
                    'is_valid': True,
                    'confidence': 0.95,
                    'notes': 'Largo estándar validado'
                }
        
        # Normalizar unidades: 100mm = 10cm, etc.
        normalized = self._normalize_length(value)
        if normalized and normalized in self.valid_lengths:
            return {
                'normalized': normalized,
                'is_valid': True,
                'confidence': 0.85,
                'notes': 'Largo normalizado a estándar'
            }
        
        # Número válido pero no en tabla
        if re.match(r'^\d+(?:[.,]\d+)?(?:cm|m|mm)?$', value):
            return {
                'normalized': value,
                'is_valid': True,
                'confidence': 0.6,
                'notes': 'Valor numérico válido'
            }
        
        return {
            'normalized': value,
            'is_valid': False,
            'confidence': 0.2,
            'notes': 'Largo inválido o ambiguo'
        }
    
    def _normalize_length(self, value: str) -> Optional[str]:
        """Normaliza unidades de largo."""
        # Extraer número y unidad
        match = re.match(r'(\d+(?:[.,]\d+)?)\s*([a-z]+)?', value.lower())
        if not match:
            return None
        
        num_str, unit = match.groups()
        num = float(num_str.replace(',', '.'))
        
        # Convertir a cm
        if unit in ['mm', '']:
            num_cm = num / 10 if unit == 'mm' else num
        elif unit in ['m', 'metros']:
            num_cm = num * 100
        elif unit in ['cm', 'centímetro', 'centimetro']:
            num_cm = num
        else:
            return None
        
        # Redondear a valor cercano en tabla
        for valid_l in sorted(self.valid_lengths):
            match_num = re.match(r'(\d+(?:[.,]\d+)?)', valid_l)
            if match_num:
                valid_num = float(match_num.group(1))
                if abs(valid_num - num_cm) < 5:  # Tolerancia ±5cm
                    return valid_l
        
        return None
    
    def _validate_thickness(self, value: str) -> Dict:
        """Valida grosor."""
        # Similar a diámetro pero solo acepta mm
        if re.match(r'^\d+(?:[.,]\d+)?\s*mm$', value, re.IGNORECASE):
            return {
                'normalized': value.upper(),
                'is_valid': True,
                'confidence': 0.9,
                'notes': 'Grosor válido en mm'
            }
        
        return {
            'normalized': value,
            'is_valid': False,
            'confidence': 0.3,
            'notes': 'Grosor debe estar en mm'
        }
    
    def _validate_material(self, value: str) -> Dict:
        """Valida material."""
        value_lower = value.lower()
        
        # Búsqueda directa
        for valid_m in self.valid_materials:
            if valid_m == value_lower:
                return {
                    'normalized': valid_m,
                    'is_valid': True,
                    'confidence': 0.95,
                    'notes': 'Material estándar validado'
                }
        
        # Búsqueda parcial (contiene palabra clave)
        for valid_m in self.valid_materials:
            if valid_m in value_lower or value_lower in valid_m:
                return {
                    'normalized': valid_m,
                    'is_valid': True,
                    'confidence': 0.8,
                    'notes': f'Normalizado a: {valid_m}'
                }
        
        return {
            'normalized': value,
            'is_valid': False,
            'confidence': 0.3,
            'notes': 'Material no reconocido'
        }
    
    def _validate_finish(self, value: str) -> Dict:
        """Valida acabado."""
        value_lower = value.lower()
        
        if value_lower in self.valid_finishes:
            return {
                'normalized': value_lower,
                'is_valid': True,
                'confidence': 0.95,
                'notes': 'Acabado estándar'
            }
        
        return {
            'normalized': value,
            'is_valid': False,
            'confidence': 0.4,
            'notes': 'Acabado no estándar'
        }
    
    def _validate_brand(self, value: str) -> Dict:
        """Valida marca (muy permisiva)."""
        # Las marcas son variables, apenas validar formato
        if len(value) < 3:
            return {
                'normalized': value,
                'is_valid': False,
                'confidence': 0.3,
                'notes': 'Marca demasiado corta'
            }
        
        if re.match(r'^[A-Z][A-Z\d\s]+$', value):
            return {
                'normalized': value,
                'is_valid': True,
                'confidence': 0.85,
                'notes': 'Formato de marca válido'
            }
        
        return {
            'normalized': value.upper(),
            'is_valid': True,
            'confidence': 0.6,
            'notes': 'Marca normalizada'
        }
    
    def _validate_quantity(self, value: str) -> Dict:
        """Valida cantidad."""
        if re.match(r'^\d+$', str(value).strip()):
            num = int(value)
            if 1 <= num <= 10000:
                return {
                    'normalized': str(num),
                    'is_valid': True,
                    'confidence': 0.95,
                    'notes': 'Cantidad válida'
                }
        
        return {
            'normalized': value,
            'is_valid': False,
            'confidence': 0.2,
            'notes': 'Cantidad inválida'
        }
    
    def get_validation_summary(self, df: pd.DataFrame) -> str:
        """Genera resumen de validaciones."""
        attr_columns = [col for col in df.columns if col.endswith('_validado')]
        
        summary = """
        ╔════════════════════════════════════════╗
        ║    RESUMEN DE VALIDACIÓN DE ATRIBUTOS ║
        ╚════════════════════════════════════════╝
        
        📊 Estado de validación por atributo:
        """
        
        for col in attr_columns:
            attr_name = col.replace('Atributo_', '').replace('_validado', '')
            
            valid = 0
            invalid = 0
            unknown = 0
            
            for val in df[col]:
                if pd.isna(val) or val is None:
                    unknown += 1
                elif val.get('is_valid') is True:
                    valid += 1
                elif val.get('is_valid') is False:
                    invalid += 1
                else:
                    unknown += 1
            
            total = len(df)
            summary += f"\n        • {attr_name}:"
            summary += f"\n          ✓ Válidos: {valid} ({valid/total*100:.0f}%)"
            summary += f"\n          ✗ Inválidos: {invalid} ({invalid/total*100:.0f}%)"
            summary += f"\n          ? Desconocidos: {unknown}"
        
        return summary


# Función de conveniencia
def validate_attributes(df: pd.DataFrame, rules_path: str = 'config/rules.yaml') -> pd.DataFrame:
    """
    Valida atributos del DataFrame.
    
    Args:
        df: DataFrame con atributos extraídos
        rules_path: Path a archivo de reglas
    
    Returns:
        DataFrame con validaciones
    """
    validator = AttributeValidator(rules_path)
    df_validated = validator.validate_dataframe(df)
    print(validator.get_validation_summary(df_validated))
    return df_validated
