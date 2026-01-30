"""
LOADER.PY - Cargador de datos Excel
Responsabilidad: Leer el archivo Excel original sin modificarlo
Validaciones: Estructura básica, columnas requeridas
Salida: DataFrame con datos crudos listos para limpieza
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Tuple, Dict, List
import hashlib
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExcelLoader:
    """
    Carga archivos Excel de productos sin modificar el original.
    Valida estructura y genera checksums para auditabilidad.
    """
    
    # Columnas requeridas (mínimas)
    REQUIRED_COLUMNS = ['Nombre']
    
    # Columnas opcionales esperadas (pero se aceptan todas las columnas)
    OPTIONAL_COLUMNS = ['SKU', 'Marca', 'Precio', 'Stock', 'Descripción', 'Categoría', 
                        'Modelo', 'Unidad', 'Código de barras', 'Producto / Servicio',
                        'Costo neto', 'Venta: Precio neto', 'Venta: afecto/exento de IVA',
                        'Venta: Monto IVA', 'Venta: Código Impuesto específico', 
                        'Venta: Monto impuesto específico', 'Venta: Precio total',
                        'Stock mínimo', 'Descripción ecommerce', 'Seriales',
                        'Información Adicional 1', 'Información Adicional 2', 
                        'Información Adicional 3', 'Disponibilidad en: Bodega de Cajas',
                        'Disponibilidad en: Bodega general', 'Disponibilidad en: Otros productos']
    
    def __init__(self, input_path: str, output_base_dir: str = 'data'):
        """
        Inicializa el loader.
        
        Args:
            input_path: Ruta del archivo Excel original (solo lectura)
            output_base_dir: Directorio base para datos procesados
        """
        self.input_path = Path(input_path)
        self.output_base_dir = Path(output_base_dir)
        
        # Validar que el archivo exista
        if not self.input_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {self.input_path}")
        
        logger.info(f"Inicializando loader para: {self.input_path}")
    
    def load(self, sheet_name: int = 0) -> Tuple[pd.DataFrame, Dict]:
        """
        Carga el archivo Excel y retorna DataFrame + metadatos.
        
        Args:
            sheet_name: Nombre o índice de la hoja a cargar
        
        Returns:
            Tupla (DataFrame, metadatos)
        
        Raises:
            ValueError: Si faltan columnas requeridas
            Exception: Si hay error en lectura del archivo
        """
        try:
            logger.info(f"Leyendo Excel desde: {self.input_path}")
            
            # Leer Excel
            df = pd.read_excel(self.input_path, sheet_name=sheet_name)
            
            # Generar metadata
            metadata = self._generate_metadata(df)
            
            # Validar columnas requeridas
            self._validate_columns(df)
            
            logger.info(f"✓ Cargados {len(df)} registros")
            logger.info(f"✓ Columnas: {list(df.columns)}")
            logger.info(f"✓ Checksum: {metadata['checksum']}")
            
            return df, metadata
        
        except Exception as e:
            logger.error(f"Error cargando Excel: {str(e)}")
            raise
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        """
        Valida que existan columnas requeridas.
        
        Args:
            df: DataFrame a validar
        
        Raises:
            ValueError: Si faltan columnas requeridas
        """
        missing_cols = set(self.REQUIRED_COLUMNS) - set(df.columns)
        
        if missing_cols:
            msg = f"Columnas faltantes: {missing_cols}"
            logger.error(msg)
            raise ValueError(msg)
        
        # Advertencia si faltan columnas opcionales
        found_optional = set(self.OPTIONAL_COLUMNS) & set(df.columns)
        missing_optional = set(self.OPTIONAL_COLUMNS) - found_optional
        
        if missing_optional:
            logger.warning(f"Columnas opcionales no encontradas: {missing_optional}")
    
    def _generate_metadata(self, df: pd.DataFrame) -> Dict:
        """
        Genera metadatos del archivo para auditabilidad.
        
        Args:
            df: DataFrame cargado
        
        Returns:
            Diccionario con metadatos
        """
        # Checksum del archivo original
        with open(self.input_path, 'rb') as f:
            checksum = hashlib.md5(f.read()).hexdigest()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'file_path': str(self.input_path),
            'checksum': checksum,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'nulls_per_column': df.isnull().sum().to_dict(),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
    
    def save_raw_copy(self, df: pd.DataFrame) -> Path:
        """
        Guarda copia de los datos crudos para referencia (sin modificaciones).
        
        Args:
            df: DataFrame a guardar
        
        Returns:
            Path del archivo guardado
        """
        output_path = self.output_base_dir / 'raw' / f'raw_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"✓ Copia cruda guardada en: {output_path}")
        
        return output_path
    
    def save_metadata(self, metadata: Dict) -> Path:
        """
        Guarda metadatos en JSON para auditoría.
        
        Args:
            metadata: Diccionario de metadatos
        
        Returns:
            Path del archivo guardado
        """
        import json
        
        output_path = self.output_base_dir / 'raw' / f'metadata_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Metadatos guardados en: {output_path}")
        
        return output_path
    
    def get_data_summary(self, df: pd.DataFrame) -> str:
        """
        Genera resumen de los datos cargados.
        
        Args:
            df: DataFrame a analizar
        
        Returns:
            String con resumen
        """
        summary = f"""
        ╔════════════════════════════════════════╗
        ║      RESUMEN DE DATOS CARGADOS        ║
        ╚════════════════════════════════════════╝
        
        📊 Dimensiones:
           • Registros: {len(df)}
           • Columnas: {len(df.columns)}
        
        📋 Estructura:
           • Columnas: {', '.join(df.columns)}
        
        ⚠️  Valores nulos:
        """
        
        nulls = df.isnull().sum()
        for col, null_count in nulls[nulls > 0].items():
            pct = (null_count / len(df)) * 100
            summary += f"\n           • {col}: {null_count} ({pct:.1f}%)"
        
        if nulls.sum() == 0:
            summary += "\n           • Sin valores nulos ✓"
        
        return summary


# Función de conveniencia
def load_products_excel(input_path: str) -> Tuple[pd.DataFrame, Dict]:
    """
    Carga archivo Excel de productos.
    
    Args:
        input_path: Ruta del Excel original
    
    Returns:
        Tupla (DataFrame, metadatos)
    """
    loader = ExcelLoader(input_path)
    df, metadata = loader.load()
    
    # Guardar copias para auditoría
    loader.save_raw_copy(df)
    loader.save_metadata(metadata)
    
    print(loader.get_data_summary(df))
    
    return df, metadata
