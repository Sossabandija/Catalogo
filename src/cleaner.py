"""
CLEANER.PY - Normalización y limpieza de datos
Responsabilidad: Estandarizar nombres, detectar patrones, limpiar ruido
Sin modificación destructiva: Todas las transformaciones son rastreables
Salida: DataFrame con columnas adicionales de metadatos y decisiones
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import yaml

logger = logging.getLogger(__name__)


@dataclass
class CleaningDecision:
    """Registro de decisión de limpieza (trazabilidad completa)"""
    original: str
    cleaned: str
    operations_applied: List[str]
    confidence: float
    notes: str = ""


class DataCleaner:
    """
    Limpia y normaliza datos de productos.
    - Elimina ruido sin perder información
    - Mantiene trazabilidad de todas las operaciones
    - Extrae patrones básicos (marca, medidas, material)
    """
    
    def __init__(self, rules_path: str = 'config/rules.yaml'):
        """
        Inicializa el cleaner con reglas deterministas.
        
        Args:
            rules_path: Path a archivo de reglas YAML
        """
        self.rules = self._load_rules(rules_path)
        logger.info(f"Reglas cargadas desde: {rules_path}")
    
    def _load_rules(self, rules_path: str) -> Dict:
        """
        Carga reglas desde YAML.
        
        Args:
            rules_path: Path al archivo de reglas
        
        Returns:
            Diccionario con reglas
        """
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Archivo de reglas no encontrado: {rules_path}")
            logger.warning("Usando reglas por defecto (mínimas)")
            return self._get_default_rules()
    
    def _get_default_rules(self) -> Dict:
        """Reglas por defecto si no se puede cargar config."""
        return {
            'families': {},
            'attributes': {},
            'noise_patterns': [],
            'variation_keywords': {}
        }
    
    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpia todo el DataFrame.
        
        Args:
            df: DataFrame original
        
        Returns:
            DataFrame con columnas de limpieza agregadas
        """
        logger.info(f"Iniciando limpieza de {len(df)} registros...")
        
        # Crear copia para no modificar original
        df_clean = df.copy()
        
        # Aplicar limpieza a columna Nombre (crítica)
        df_clean['Nombre_Original'] = df_clean['Nombre'].copy()
        df_clean['Nombre_Limpio'] = df_clean['Nombre'].apply(self.clean_name)
        df_clean['Limpieza_Notas'] = df_clean['Nombre'].apply(self._get_cleaning_notes)
        
        # Detectar palabras clave principales
        df_clean['Familia_Detectada'] = df_clean['Nombre_Limpio'].apply(self._detect_family)
        
        # Extraer marca (si existe)
        df_clean['Marca_Detectada'] = df_clean['Nombre'].apply(self._extract_brand)
        
        # Detectar si tiene potencial de variaciones
        df_clean['Tiene_Medidas'] = df_clean['Nombre'].apply(self._has_measurements)
        
        logger.info("✓ Limpieza completada")
        logger.info(f"  • Nombres únicos detectados: {df_clean['Nombre_Limpio'].nunique()}")
        logger.info(f"  • Familias detectadas: {df_clean['Familia_Detectada'].nunique()}")
        
        return df_clean
    
    def clean_name(self, name: str) -> str:
        """
        Limpia nombre del producto eliminando ruido.
        
        Operaciones:
        1. Convertir a uppercase (estándar)
        2. Normalizar espacios
        3. Eliminar caracteres especiales inútiles
        4. Remover ruido común (stock, disponible, etc.)
        
        Args:
            name: Nombre original
        
        Returns:
            Nombre limpio
        """
        if not isinstance(name, str) or pd.isna(name):
            return ""
        
        clean = str(name).strip()
        
        # 1. Uppercase (estándar de catálogos)
        clean = clean.upper()
        
        # 2. Normalizar espacios múltiples
        clean = re.sub(r'\s+', ' ', clean)
        
        # 3. Eliminar caracteres especiales inútiles
        clean = re.sub(r'[«»""•]', '', clean)
        
        # 4. Normalizar fracciones (1.1/8" -> 1 1/8")
        clean = re.sub(r'(\d)\.(\d/\d)', r'\1 \2', clean)
        
        # 5. Normalizar unidades: convertir a estándar
        clean = re.sub(r'(\d+)\s*"', r'\1"', clean)  # Quitar espacio antes de comilla
        clean = re.sub(r'pulgada(?:s)?', '"', clean, flags=re.IGNORECASE)
        clean = re.sub(r'mm\.', 'mm', clean, flags=re.IGNORECASE)
        
        # 6. Remover ruido explícito
        noise_words = ['STOCK', 'DISPONIBLE', 'OFERTA', 'PROMO', 'DESCUENTO', 
                      'CONSULTE', 'PRECIO ESPECIAL', 'BAJO PEDIDO']
        for word in noise_words:
            clean = re.sub(f'(?i){word}[\\s]?', '', clean)
        
        # 7. Trim final
        clean = clean.strip()
        
        return clean
    
    def _get_cleaning_notes(self, original: str) -> str:
        """
        Genera notas sobre qué se limpió.
        
        Args:
            original: Nombre original
        
        Returns:
            String con transformaciones realizadas
        """
        notes = []
        original_upper = str(original).upper()
        
        # Detectar caracteres especiales
        if re.search(r'[«»""•]', original):
            notes.append("caracteres_especiales")
        
        # Detectar espacios múltiples
        if re.search(r'\s{2,}', original):
            notes.append("espacios_multiples")
        
        # Detectar ruido
        if re.search(r'(?i)(stock|disponible|oferta|promo)', original):
            notes.append("ruido_inventario")
        
        # Detectar normalización de unidades
        if re.search(r'pulgada|mm\.', original, re.IGNORECASE):
            notes.append("unidades_normalizadas")
        
        if not notes:
            notes.append("sin_cambios")
        
        return ", ".join(notes)
    
    def _detect_family(self, clean_name: str) -> Optional[str]:
        """
        Detecta familia del producto por palabras clave.
        
        Args:
            clean_name: Nombre limpio
        
        Returns:
            Nombre de familia o None
        """
        if not clean_name:
            return None
        
        name_lower = clean_name.lower()
        
        for family_name, family_config in self.rules.get('families', {}).items():
            keywords = family_config.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in name_lower:
                    return family_name
        
        return None
    
    def _extract_brand(self, name: str) -> Optional[str]:
        """
        Extrae marca del nombre usando patrones.
        
        Heurística:
        - Primera palabra en CAPS seguida de palabra descriptiva
        - Palabras conocidas (TITAN, HEXAGON, etc.)
        
        Args:
            name: Nombre del producto
        
        Returns:
            Marca detectada o None
        """
        if not isinstance(name, str):
            return None
        
        name = str(name).strip()
        words = name.split()
        
        if not words:
            return None
        
        # Primera palabra (usualmente marca)
        first_word = words[0]
        
        # Validar que sea palabra (no número)
        if re.match(r'^[A-Z]{2,}$', first_word):
            # Adicionar segunda palabra si es pequeña (variante de marca)
            if len(words) > 1 and len(words[1]) < 8 and re.match(r'^[A-Z]+$', words[1]):
                return f"{first_word} {words[1]}"
            return first_word
        
        return None
    
    def _has_measurements(self, name: str) -> bool:
        """
        Detecta si el nombre contiene medidas/dimensiones.
        
        Señales:
        - Números seguidos de unidades (mm, ", cm, m)
        - Fracciones (1/4, 3/8)
        - Rangos (22-36)
        
        Args:
            name: Nombre del producto
        
        Returns:
            True si hay medidas detectadas
        """
        if not isinstance(name, str):
            return False
        
        # Patrones de medida
        measurement_patterns = [
            r'\d+\.?\d*\s*(?:mm|cm|m|"|pulg)',  # Números con unidades
            r'\d+\s*[/-]\s*\d+\s*"',             # Fracciones
            r'\d+\s*[-–]\s*\d+',                 # Rangos
            r'(?:x|X)\s*\d+',                    # Dimensiones múltiples
        ]
        
        for pattern in measurement_patterns:
            if re.search(pattern, name):
                return True
        
        return False
    
    def get_cleaning_summary(self, df_clean: pd.DataFrame) -> str:
        """
        Genera resumen de la limpieza realizada.
        
        Args:
            df_clean: DataFrame limpiado
        
        Returns:
            String con resumen
        """
        summary = """
        ╔════════════════════════════════════════╗
        ║        RESUMEN DE LIMPIEZA            ║
        ╚════════════════════════════════════════╝
        
        📊 Cambios detectados:
        """
        
        # Nombres cambiados
        changed = (df_clean['Nombre_Original'] != df_clean['Nombre_Limpio']).sum()
        summary += f"\n        • Registros modificados: {changed}"
        
        # Familias detectadas
        families = df_clean['Familia_Detectada'].value_counts()
        summary += f"\n        \n        📦 Familias detectadas ({len(families)}): "
        for family, count in families.head(5).items():
            summary += f"\n           • {family}: {count}"
        
        # Marcas detectadas
        brands = df_clean['Marca_Detectada'].value_counts()
        summary += f"\n        \n        🏷️  Marcas detectadas ({len(brands)}): "
        for brand, count in brands.head(5).items():
            summary += f"\n           • {brand}: {count}"
        
        # Registros con medidas
        with_measures = df_clean['Tiene_Medidas'].sum()
        summary += f"\n        \n        📏 Registros con medidas: {with_measures} ({with_measures/len(df_clean)*100:.1f}%)"
        
        return summary


# Función de conveniencia
def clean_products(df: pd.DataFrame, rules_path: str = 'config/rules.yaml') -> pd.DataFrame:
    """
    Limpia DataFrame de productos.
    
    Args:
        df: DataFrame original
        rules_path: Path a archivo de reglas
    
    Returns:
        DataFrame limpiado
    """
    cleaner = DataCleaner(rules_path)
    df_clean = cleaner.clean_dataframe(df)
    print(cleaner.get_cleaning_summary(df_clean))
    return df_clean
