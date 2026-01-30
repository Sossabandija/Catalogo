"""
Paquete de módulos del catálogo
"""

from src.loader import ExcelLoader, load_products_excel
from src.cleaner import DataCleaner, clean_products
from src.patterns import PatternExtractor, extract_attributes, normalize_measurement
from src.attributes import AttributeValidator, validate_attributes
from src.grouping import ProductGrouper, group_products
from src.review import ReviewFormatter, generate_master_format

__version__ = '0.2.0'
__author__ = 'Data Engineering Team'

__all__ = [
    'ExcelLoader',
    'load_products_excel',
    'DataCleaner',
    'clean_products',
    'PatternExtractor',
    'extract_attributes',
    'normalize_measurement',
    'AttributeValidator',
    'validate_attributes',
    'ProductGrouper',
    'group_products',
    'ReviewFormatter',
    'generate_master_format'
]
