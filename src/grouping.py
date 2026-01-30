"""
GROUPING.PY - Agrupación de Productos y Detección de Variaciones
Responsabilidad: Agrupar productos en padre + variaciones, generar SKU jerárquico
Método: Detectar producto padre, agrupar por atributos comunes
Salida: DataFrame estructurado con Tipo, SKU, SKU Parent
"""

import pandas as pd
import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ProductGroup:
    """Grupo de productos (padre + variaciones)"""
    parent_name: str
    parent_sku: str
    variations: List[Dict]  # Cada variación es {atributo: valor}
    type: str = "variable"  # "simple" o "variable"


class ProductGrouper:
    """
    Agrupa productos en padre + variaciones.
    - Detecta kits y surtidos (productos padre)
    - Agrupa variaciones por atributos comunes
    - Genera SKU jerárquicos
    - Valida estructura de variaciones
    """
    
    def __init__(self, rules_path: str = 'config/rules.yaml'):
        """
        Inicializa agrupador.
        
        Args:
            rules_path: Path a archivo de reglas
        """
        self.rules = self._load_rules(rules_path)
        self._build_grouping_config()
        logger.info("Agrupador de productos inicializado")
    
    def _load_rules(self, rules_path: str) -> Dict:
        """Carga reglas desde YAML."""
        try:
            with open(rules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Reglas no encontradas: {rules_path}")
            return {}
    
    def _build_grouping_config(self) -> None:
        """Construye configuración de agrupación."""
        
        # Keywords para detectar producto padre
        self.parent_keywords = set()
        if 'parent_product' in self.rules:
            for pattern in self.rules['parent_product'].get('patterns', []):
                # Extraer palabras de los patrones
                words = re.findall(r'\w+', pattern.lower())
                self.parent_keywords.update(words)
        
        self.parent_keywords.update([
            'kit', 'pack', 'surtido', 'variado', 'completo',
            'set', 'incluye', 'varios', 'mix'
        ])
        
        # Atributos que definen variaciones
        self.variation_attributes = set()
        if 'variation_keywords' in self.rules:
            for attr, keywords in self.rules['variation_keywords'].items():
                self.variation_attributes.add(attr)
    
    def group_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Agrupa productos y detecta padre/variaciones.
        
        Args:
            df: DataFrame con productos
        
        Returns:
            DataFrame con columnas Tipo, SKU, SKU_Parent
        """
        df = df.copy()
        
        logger.info(f"Agrupando {len(df)} productos...")
        
        # Preservar SKU original ANTES de sobrescribir
        if 'SKU_Origen' not in df.columns and 'SKU' in df.columns:
            df['SKU_Origen'] = df['SKU'].copy()
        
        # 1. Detectar productos padre
        df['Es_Padre_Potencial'] = df['Nombre_Limpio'].apply(self._is_potential_parent)
        
        # 2. Inicializar columnas de resultado
        df['Tipo'] = 'simple'  # Por defecto
        df['SKU_WooCommerce'] = ''  # Nuevo SKU para WooCommerce
        df['SKU_Parent'] = None
        
        # 3. Agrupar nombres similares
        df['Nombre_Base'] = df['Nombre_Limpio'].apply(self._extract_base_name)
        
        # 4. Procesar grupos - Detectar variaciones (múltiples productos con mismo nombre base)
        grouped = df.groupby('Nombre_Base')
        
        for base_name, group_df in grouped:
            group_indices = group_df.index.tolist()
            
            # Debug: mostrar lo que se encontró
            if len(group_df) > 1:
                logger.info(f"🔍 Grupo encontrado '{base_name}' con {len(group_df)} productos:")
                for idx in group_indices:
                    logger.info(f"   - {df.loc[idx, 'Nombre_Limpio']} (SKU: {df.loc[idx].get('SKU', '?')})")
            
            if len(group_df) > 1:
                # VARIACIONES DETECTADAS: Crear estructura padre-hijo
                # El primer producto es el padre (o el más genérico)
                parent_idx = group_indices[0]
                
                # Marcar padre como variable
                df.loc[parent_idx, 'Tipo'] = 'variable'
                
                # Generar SKU para padre (basado en nombre base sin medidas)
                parent_name = df.loc[parent_idx, 'Nombre_Limpio']
                
                # Usar SKU original si existe
                if 'SKU_Origen' in df.columns and pd.notna(df.loc[parent_idx, 'SKU_Origen']):
                    # Simplificar SKU original para usarlo como padre
                    parent_sku = str(df.loc[parent_idx, 'SKU_Origen']).strip()
                    # Remover sufijos que indiquen medidas
                    parent_sku = re.sub(r'-[A-Z0-9]+$', '', parent_sku)
                else:
                    parent_sku = self._generate_parent_sku(parent_name)
                
                df.loc[parent_idx, 'SKU_WooCommerce'] = parent_sku
                df.loc[parent_idx, 'SKU_Parent'] = None  # Padre no tiene padre
                
                # Procesar variaciones
                for i, var_idx in enumerate(group_indices[1:], start=1):
                    df.loc[var_idx, 'Tipo'] = 'variable'
                    df.loc[var_idx, 'SKU_Parent'] = parent_sku
                    
                    # Generar SKU único para variación usando SKU original
                    if 'SKU_Origen' in df.columns and pd.notna(df.loc[var_idx, 'SKU_Origen']):
                        var_sku = str(df.loc[var_idx, 'SKU_Origen']).strip()
                    else:
                        # Generar basado en atributos diferenciales
                        var_sku = self._generate_variation_sku(
                            parent_sku,
                            df.loc[var_idx, 'Nombre_Limpio'],
                            df.loc[var_idx]
                        )
                    
                    df.loc[var_idx, 'SKU_WooCommerce'] = var_sku
            
            else:
                # PRODUCTO SIMPLE
                idx = group_indices[0]
                df.loc[idx, 'Tipo'] = 'simple'
                
                # Usar SKU original si existe
                if 'SKU_Origen' in df.columns and pd.notna(df.loc[idx, 'SKU_Origen']):
                    df.loc[idx, 'SKU_WooCommerce'] = str(df.loc[idx, 'SKU_Origen']).strip()
                else:
                    df.loc[idx, 'SKU_WooCommerce'] = self._generate_simple_sku(
                        df.loc[idx, 'Nombre_Limpio']
                    )
        
        # 5. Asegurarse que cada producto tenga SKU_WooCommerce
        df.loc[df['SKU_WooCommerce'].isna() | (df['SKU_WooCommerce'] == ''), 'SKU_WooCommerce'] = df['Nombre_Limpio'].apply(
            self._generate_simple_sku
        )
        
        # Copiar SKU_WooCommerce a SKU para mantener compatibilidad
        df['SKU'] = df['SKU_WooCommerce']
        
        logger.info("✓ Agrupación completada")
        logger.info(f"  • Productos simples: {(df['Tipo'] == 'simple').sum()}")
        logger.info(f"  • Productos variables (padre): {((df['Tipo'] == 'variable') & (df['SKU_Parent'].isna())).sum()}")
        logger.info(f"  • Variaciones (hijo): {(df['SKU_Parent'].notna()).sum()}")
        
        return df
    
    def _is_potential_parent(self, name: str) -> bool:
        """
        Detecta si nombre sugiere ser producto padre.
        
        Args:
            name: Nombre limpio del producto
        
        Returns:
            True si es potencial padre
        """
        if not isinstance(name, str):
            return False
        
        name_lower = name.lower()
        
        # Buscar palabras clave de padre
        for keyword in self.parent_keywords:
            if keyword in name_lower:
                return True
        
        return False
    
    def _extract_base_name(self, name: str) -> str:
        """
        Extrae nombre base (sin medidas ni variantes específicas).
        
        Ej: "TORNILLO HEXAGONAL INOX M6 x 30mm" → "TORNILLO HEXAGONAL INOX"
        Ej: "ABRAZADERA 1/2 COBRE OMEGA" → "ABRAZADERA COBRE OMEGA"
        
        Args:
            name: Nombre completo
        
        Returns:
            Nombre base para agrupación
        """
        if not isinstance(name, str):
            return name
        
        base = name
        
        # Remover medidas M6, M8, etc (tamaños estándar)
        # Cubre: M6, M6x30, M6 x 30, M6 X 30MM, etc - case-insensitive
        base = re.sub(r'\s+M\d+(?:\s*[xX]\s*\d+(?:mm|MM)?)?', '', base)
        
        # Remover " X 30MM" y variantes (cuando M{número} fue removido pero quedó "X {medida}")
        base = re.sub(r'\s+[xX]\s+\d+(?:MM|mm)?(?:\s|$)', ' ', base)
        
        # Remover fracciones (1/2, 3/8, etc)
        base = re.sub(r'\s+\d+/\d+(?:["\'])?', '', base)
        
        # Remover medidas con unidades al final (30mm, 40mm, etc)
        base = re.sub(r'\s+\d+(?:mm|MM|cm|m|pulgada|pulg|")(?:\s|$)', ' ', base)
        
        # Remover rangos (22-36, etc)
        base = re.sub(r'\s+\d+-\d+\s*$', '', base)
        
        # Remover contenido en parénesis al final
        base = re.sub(r'\s*\([^)]*\)\s*$', '', base)
        
        # Remover números de modelo/referencia (HEX-M6-30, etc)
        base = re.sub(r'\s+[A-Z]+-[A-Z0-9-]+$', '', base)
        
        # Normalizar espacios múltiples
        base = re.sub(r'\s+', ' ', base).strip()
        
        return base if base else name
    
    def _find_parent_in_group(self, group_df: pd.DataFrame) -> Optional:
        """
        Encuentra el índice del producto padre en un grupo.
        
        Heurística:
        1. Si hay uno marcado como padre potencial → usarlo
        2. Si hay uno sin medidas → usarlo (probablemente padre)
        3. Usar el primero
        
        Args:
            group_df: DataFrame del grupo
        
        Returns:
            Índice del padre o None
        """
        # 1. Buscar potencial padre explícito
        potential = group_df[group_df['Es_Padre_Potencial']]
        if len(potential) > 0:
            return potential.index[0]
        
        # 2. Buscar sin medidas (más probable ser padre)
        without_measures = group_df[~group_df['Tiene_Medidas']]
        if len(without_measures) > 0:
            return without_measures.index[0]
        
        # 3. Por defecto: primero del grupo
        return group_df.index[0]
    
    def _generate_parent_sku(self, parent_name: str) -> str:
        """
        Genera SKU para producto padre.
        
        Formato: FAMILIA-MARCA-MODELO (e.g., ABR-TITAN-MINI)
        
        Args:
            parent_name: Nombre del padre
        
        Returns:
            SKU generado
        """
        words = parent_name.upper().split()
        
        # Tomar hasta 3 palabras significativas (no muy cortas)
        significant = [w for w in words if len(w) > 3][:3]
        
        # Si insuficientes, tomar más
        if len(significant) < 3:
            significant = words[:3]
        
        # Tomar primeras letras
        sku_parts = []
        for word in significant:
            if len(word) <= 4:
                sku_parts.append(word[:4])
            else:
                sku_parts.append(word[:3])
        
        sku = '-'.join(sku_parts)
        
        # Sanitizar
        sku = re.sub(r'[^A-Z0-9\-]', '', sku)
        sku = sku.strip('-')
        
        return sku if sku else f"PROD-{len(parent_name)}"
    
    def _generate_variation_sku(self, parent_sku: str, var_name: str, 
                               row: pd.Series) -> str:
        """
        Genera SKU para variación.
        
        Formato: PARENT-SKU + atributos (e.g., ABR-TITAN-MINI-1-4)
        
        Args:
            parent_sku: SKU del padre
            var_name: Nombre de la variación
            row: Fila del DataFrame con atributos
        
        Returns:
            SKU generado
        """
        sku_parts = [parent_sku]
        
        # Extraer atributos de variación
        attr_cols = [col for col in row.index if col.startswith('Atributo_')
                    and not col.endswith('_confianza') and not col.endswith('_cantidad')]
        
        for col in attr_cols:
            if pd.notna(row[col]):
                value = str(row[col]).upper()
                
                # Simplificar valor
                # 1/4" → 1-4, 10mm → 10, etc.
                value = re.sub(r'[^\w]', '', value)[:6]  # Max 6 chars
                
                if value:
                    sku_parts.append(value)
        
        sku = '-'.join(sku_parts)
        
        # Sanitizar
        sku = re.sub(r'[^A-Z0-9\-]', '', sku)
        sku = sku.strip('-')
        
        return sku if sku else parent_sku
    
    def _generate_simple_sku(self, product_name: str) -> str:
        """
        Genera SKU para producto simple.
        
        Formato: palabras clave + familia
        
        Args:
            product_name: Nombre del producto
        
        Returns:
            SKU generado
        """
        if not isinstance(product_name, str):
            return "PROD"
        
        words = product_name.upper().split()
        
        # Tomar primeras palabras significativas
        sku_parts = []
        for word in words[:3]:
            if len(word) > 2:
                sku_parts.append(word[:4])
        
        if not sku_parts:
            sku_parts = ['PROD']
        
        sku = '-'.join(sku_parts)
        
        # Sanitizar
        sku = re.sub(r'[^A-Z0-9\-]', '', sku)
        
        return sku.strip('-')
    
    def get_grouping_summary(self, df: pd.DataFrame) -> str:
        """Genera resumen de agrupación."""
        summary = """
        ╔════════════════════════════════════════╗
        ║     RESUMEN DE AGRUPACIÓN DE PRODUCTOS ║
        ╚════════════════════════════════════════╝
        
        📊 Estructura de productos:
        """
        
        simple_count = (df['Tipo'] == 'simple').sum()
        variable_count = (df['Tipo'] == 'variable').sum()
        variation_count = df['SKU_Parent'].notna().sum()
        parent_count = (df['Tipo'] == 'variable').sum() - variation_count
        
        summary += f"\n        • Productos simples: {simple_count}"
        summary += f"\n        • Productos variables (padre): {parent_count}"
        summary += f"\n        • Variaciones: {variation_count}"
        summary += f"\n        • Total: {len(df)}"
        
        # Mostrar SKU distribution
        unique_parents = df['SKU_Parent'].nunique()
        summary += f"\n        \n        🔗 Estructura jerárquica:"
        summary += f"\n        • Grupos padre únicos: {unique_parents}"
        
        # Top SKU parents
        parent_counts = df['SKU_Parent'].value_counts()
        summary += f"\n        • Top 5 grupos:"
        for parent, count in parent_counts.head(5).items():
            summary += f"\n          {parent}: {count} variaciones"
        
        return summary
    
    def validate_structure(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """
        Valida estructura de padre/variaciones.
        
        Args:
            df: DataFrame agrupado
        
        Returns:
            Dict con {errores: [...], advertencias: [...]}
        """
        issues = {'errores': [], 'advertencias': []}
        
        # 1. Validar SKU único
        duplicate_skus = df[df['SKU'].duplicated(keep=False)]
        if len(duplicate_skus) > 0:
            issues['errores'].append(f"SKU duplicados: {len(duplicate_skus)} registros")
        
        # 2. Validar variaciones sin padre
        orphan_variations = df[(df['SKU_Parent'].notna()) & 
                              (~df['SKU_Parent'].isin(df['SKU']))]
        if len(orphan_variations) > 0:
            issues['advertencias'].append(
                f"Variaciones sin padre: {len(orphan_variations)} registros"
            )
        
        # 3. Validar padres con solo una variación
        single_var_parents = df.groupby('SKU_Parent').size()
        single_var_parents = single_var_parents[single_var_parents == 1]
        if len(single_var_parents) > 0:
            issues['advertencias'].append(
                f"Padres con solo 1 variación: {len(single_var_parents)}"
            )
        
        return issues


# Función de conveniencia
def group_products(df: pd.DataFrame, rules_path: str = 'config/rules.yaml') -> pd.DataFrame:
    """
    Agrupa productos en padre + variaciones.
    
    Args:
        df: DataFrame con productos
        rules_path: Path a archivo de reglas
    
    Returns:
        DataFrame agrupado
    """
    grouper = ProductGrouper(rules_path)
    df_grouped = grouper.group_products(df)
    print(grouper.get_grouping_summary(df_grouped))
    
    # Validar estructura
    issues = grouper.validate_structure(df_grouped)
    if issues['errores']:
        logger.warning(f"⚠️ Errores detectados: {issues['errores']}")
    if issues['advertencias']:
        logger.info(f"ℹ️ Advertencias: {issues['advertencias']}")
    
    return df_grouped
