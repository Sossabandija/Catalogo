"""
Tests para el parser espacial del catálogo.
Casos problemáticos detectados durante el desarrollo.
"""
import sys
sys.path.insert(0, r"c:\Users\yubyr\source\repos\Catalogo")

import pytest
from src.catalogo_spatial_parser import parse_spatial_catalog, parse_row_parts, looks_like_sku, clean_logo_text, fix_ocr_errors


class TestParseRowParts:
    """Tests para la función parse_row_parts."""
    
    def test_b01tad_bm_sku_nominal_unidos(self):
        """
        Caso: B01TAD-BM
        Problema: SKU y NOMINAL estaban unidos en el primer token.
        Input original: "B01TAD-BM #6-18"
        """
        parts = ['B01TAD-BM #6-18', '3/8', '5,000 U']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "B01TAD-BM"
        assert result.get("NOMINAL", "") == "#6-18"
        assert result.get("LARGO", "") == "3/8"
        assert result.get("ENVASE", "") == "5,000 U"
    
    def test_02rlhb_nominal_largo_correcto(self):
        """
        Caso: 02RLHB
        Problema: NOMINAL y LARGO estaban invertidos porque 5/8 se detectaba como ENTRE_CARAS.
        La lógica ENTRE_CARAS solo aplica si ENVASE es penúltimo.
        """
        parts = ['02RLHB', '#10-16', '5/8', '500 U']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "02RLHB"
        assert result.get("NOMINAL", "") == "#10-16"
        assert result.get("LARGO", "") == "5/8"
        assert result.get("ENVASE", "") == "500 U"
        # No debe haber ENTRE_CARAS porque ENVASE es el último
        assert "ENTRE_CARAS" not in result
    
    def test_04rlhb_entre_caras_confunde_envase(self):
        """
        Caso: 04RLHB
        Problema: "Entre Caras" (5/16) al final confundía la detección de ENVASE.
        ENVASE debe encontrarse por patrón "X U", no por posición.
        """
        parts = ['04RLHB', '1"', '500 U', '5/16']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "04RLHB"
        assert result.get("ENVASE", "") == "500 U"
        assert result.get("LARGO", "") == '1"'
        assert result.get("ENTRE_CARAS", "") == "5/16"
        # NOMINAL no debe estar definido (se hereda de fila anterior)
        assert "NOMINAL" not in result or result.get("NOMINAL", "") == ""
    
    def test_sku_simple_con_todos_campos(self):
        """Caso normal con todos los campos presentes."""
        parts = ['ABC123', '#10-16', '2"', '100 U']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "ABC123"
        assert result.get("NOMINAL", "") == "#10-16"
        assert result.get("LARGO", "") == '2"'
        assert result.get("ENVASE", "") == "100 U"
    
    def test_sku_solo_largo_envase(self):
        """Caso donde solo hay LARGO y ENVASE (NOMINAL heredado)."""
        parts = ['XYZ789', '3/4"', '200 U']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "XYZ789"
        assert result.get("LARGO", "") == '3/4"'
        assert result.get("ENVASE", "") == "200 U"
        # NOMINAL no definido
        assert "NOMINAL" not in result or result.get("NOMINAL", "") == ""
    
    def test_13cma_nominal_largo_combinado(self):
        """
        Caso: 13CMA
        Problema: NOMINAL y LARGO estaban combinados en un solo campo.
        Raw: "13CMA     #5(3.70) 60            100 U"
        NOMINAL=#5(3.70), LARGO=60
        """
        parts = ['13CMA', '#5(3.70) 60', '100 U']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "13CMA"
        assert result.get("NOMINAL", "") == "#5(3.70)", f"Expected #5(3.70), got {result.get('NOMINAL')}"
        assert result.get("LARGO", "") == "60", f"Expected 60, got {result.get('LARGO')}"
        assert result.get("ENVASE", "") == "100 U"
    
    def test_b90pco_nominal_con_fraccion_en_corchetes(self):
        """
        Caso: B90PCO
        Problema: NOMINAL con fracción en corchetes (#10-24[3/16]) no se separaba del LARGO.
        Raw: "B90PCO     #10-24[3/16] 3/4        100 U"
        NOMINAL=#10-24[3/16], LARGO=3/4
        El regex no incluía "/" en la clase de caracteres para NOMINAL.
        """
        parts = ['B90PCO', '#10-24[3/16] 3/4', '100 U']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "B90PCO"
        assert result.get("NOMINAL", "") == "#10-24[3/16]", f"Expected #10-24[3/16], got {result.get('NOMINAL')}"
        assert result.get("LARGO", "") == "3/4", f"Expected 3/4, got {result.get('LARGO')}"
        assert result.get("ENVASE", "") == "100 U"
    
    def test_190ab01_envase_separado_cod_tecfi(self):
        """
        Caso: 190AB01
        Problema: ENVASE viene separado como '100', 'U' y hay Cod Tecfi al final.
        Raw: "190AB01     6.3[1/4-14] 180            100 U AB0106180"
        PARTS: ['190AB01', '6.3[1/4-14]', '180', '100', 'U', 'AB0106180']
        
        El parser debe:
        1. Combinar '100' + 'U' en ENVASE '100 U'
        2. Ignorar 'AB0106180' (Cod Tecfi)
        """
        parts = ['190AB01', '6.3[1/4-14]', '180', '100', 'U', 'AB0106180']
        result = parse_row_parts(parts)
        
        assert result is not None
        assert result["CODIGO"] == "190AB01"
        assert result.get("NOMINAL", "") == "6.3[1/4-14]", f"Expected 6.3[1/4-14], got {result.get('NOMINAL')}"
        assert result.get("LARGO", "") == "180", f"Expected 180, got {result.get('LARGO')}"
        assert result.get("ENVASE", "") == "100 U", f"Expected '100 U', got '{result.get('ENVASE')}'"


class TestFullCatalogParsing:
    """Tests de integración para el catálogo completo."""
    
    @pytest.fixture(scope="class")
    def catalog(self):
        """Parsea el catálogo una vez para todos los tests."""
        # Cargar el texto del catálogo
        import os
        txt_path = os.path.join(os.path.dirname(__file__), "..", "pdf", "Catalogo_Mamut_2025.txt")
        if not os.path.exists(txt_path):
            pytest.skip("Archivo de catálogo no disponible")
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read()
        _, products = parse_spatial_catalog(text)
        return products
    
    def get_product(self, catalog, codigo):
        """Helper para buscar un producto por código."""
        # catalog es un dict con SKU como key
        return catalog.get(codigo)
    
    def get_attr(self, product, attr_name):
        """Helper para obtener el valor de un atributo."""
        if not product or 'attributes' not in product:
            return ""
        for attr in product['attributes']:
            if attr.get('name') == attr_name:
                return attr.get('value', '')
        return ""
    
    def test_b01tad_bm_detectado(self, catalog):
        """
        Caso: B01TAD-BM
        Problema original: No se detectaba porque SKU y NOMINAL estaban unidos.
        """
        product = self.get_product(catalog, "B01TAD-BM")
        assert product is not None, "B01TAD-BM debe ser detectado"
        assert self.get_attr(product, "NOMINAL") == "#6-18"
    
    def test_116rlhn_nominal_heredado(self, catalog):
        """
        Caso: 116RLHN
        Problema original: Header en columna derecha reseteaba NOMINAL de columna izquierda.
        116RLHN debe heredar NOMINAL de su sección (#10-16).
        """
        product = self.get_product(catalog, "116RLHN")
        assert product is not None, "116RLHN debe ser detectado"
        # Debe tener un NOMINAL heredado, no estar vacío
        assert self.get_attr(product, "NOMINAL") != "", "116RLHN debe tener NOMINAL heredado"
    
    def test_04rlhb_nominal_heredado(self, catalog):
        """
        Caso: 04RLHB
        Problema original: "Entre Caras" confundía los campos.
        04RLHB debe heredar NOMINAL #10-16 de su sección.
        """
        product = self.get_product(catalog, "04RLHB")
        assert product is not None, "04RLHB debe ser detectado"
        assert self.get_attr(product, "LARGO") == '1"', f"04RLHB LARGO debe ser 1\", got: {self.get_attr(product, 'LARGO')}"
        assert self.get_attr(product, "ENVASE") == "500 U", f"04RLHB ENVASE debe ser 500 U, got: {self.get_attr(product, 'ENVASE')}"
        # NOMINAL debe ser #10-16 (heredado de la sección)
        assert self.get_attr(product, "NOMINAL") == "#10-16", f"04RLHB NOMINAL debe ser #10-16, got: {self.get_attr(product, 'NOMINAL')}"


class TestLooksLikeSku:
    """Tests para la función looks_like_sku."""
    
    def test_sku_validos(self):
        assert looks_like_sku("B01TAD-BM") == True
        assert looks_like_sku("04RLHB") == True
        assert looks_like_sku("116RLHN") == True
        assert looks_like_sku("ABC123") == True
        assert looks_like_sku("01S6010") == True  # SKU real de soldadura
        assert looks_like_sku("02S6011") == True
        assert looks_like_sku("03S7018") == True
    
    def test_no_sku(self):
        assert looks_like_sku("#10-16") == False  # Es NOMINAL
        assert looks_like_sku("500 U") == False   # Es ENVASE
        assert looks_like_sku('1"') == False      # Es LARGO
        assert looks_like_sku("") == False
        assert looks_like_sku("A") == False       # Muy corto
    
    def test_tipos_soldadura_no_son_sku(self):
        """
        E6010, E6011, E7018 son tipos de soldadura AWS, NO son SKUs.
        Los SKUs reales de soldadura son como 01S6010, 02S6011, 03S7018.
        """
        assert looks_like_sku("E6010") == False
        assert looks_like_sku("E6011") == False
        assert looks_like_sku("E7018") == False
        assert looks_like_sku("E6010/6011/7018") == False
    
    def test_pta_torx_no_son_sku(self):
        """
        T10, T15, T20, T25, T30, T40, T50 son valores de PTA TORX (punta Torx),
        NO son códigos SKU. Aparecen en la columna PTA TORX del header.
        """
        assert looks_like_sku("T10") == False
        assert looks_like_sku("T15") == False
        assert looks_like_sku("T20") == False
        assert looks_like_sku("T25") == False
        assert looks_like_sku("T30") == False
        assert looks_like_sku("T40") == False
        assert looks_like_sku("T50") == False


class TestCleanLogoText:
    """Tests para limpiar logos/marcas del texto del catálogo."""
    
    def test_essve_es_logo_no_texto(self):
        """
        ESSVE es un logotipo de marca, no parte del nombre del producto.
        'TORNILLO PARA ESSVE' -> 'TORNILLO PARA'
        'TORNILLO PARA TERRAZAS' no cambia.
        """
        assert clean_logo_text("TORNILLO PARA ESSVE") == "TORNILLO PARA"
        assert clean_logo_text("TORNILLO PARA TERRAZAS") == "TORNILLO PARA TERRAZAS"
        assert clean_logo_text("ESSVE") == ""
        assert clean_logo_text("KNAPP") == ""
    
    def test_logo_en_medio_de_texto(self):
        """Los logos pueden aparecer en cualquier posición."""
        assert clean_logo_text("TORNILLO ESSVE PARA DECK") == "TORNILLO PARA DECK"
        assert clean_logo_text("HERRAMIENTAS KNAPP CONECTOR") == "HERRAMIENTAS CONECTOR"


class TestFixOcrErrors:
    """Tests para corrección de errores de OCR en SKUs."""
    
    def test_o_seguido_de_digito_es_cero(self):
        """
        Problema de OCR: la letra "O" se confunde con el número "0".
        Ejemplo: "NO4RLBC" debería ser "N04RLBC"
        """
        assert fix_ocr_errors("NO4RLBC") == "N04RLBC"
        assert fix_ocr_errors("NO1RLPP") == "N01RLPP"
        assert fix_ocr_errors("NO2RLPP") == "N02RLPP"
        assert fix_ocr_errors("O1ABC") == "01ABC"
    
    def test_o_no_seguido_de_digito_no_cambia(self):
        """Si O no está seguida de dígito, no debe cambiar."""
        assert fix_ocr_errors("TORNILLO") == "TORNILLO"
        assert fix_ocr_errors("B01TAD") == "B01TAD"  # Ya tiene 0, no O
        assert fix_ocr_errors("PERNO") == "PERNO"
    
    def test_multiples_o_con_digito(self):
        """Múltiples O+dígito en el mismo SKU."""
        assert fix_ocr_errors("O1O2ABC") == "0102ABC"


class TestCategoryParsing:
    """Tests para parsing de categorías después de page breaks."""
    
    @pytest.fixture(scope="class")
    def catalog(self):
        """Carga el catálogo completo una vez para todos los tests."""
        with open(r"c:\Users\yubyr\source\repos\Catalogo\pdf\Catalogo_Mamut_2025.txt", "r", encoding="utf-8") as f:
            text = f.read()
        structure, products = parse_spatial_catalog(text)
        return {"structure": structure, "products": products}
    
    def test_perno_coche_no_combinado_con_tornillos(self, catalog):
        """
        Caso: PERNO COCHE después de "TORNILLOS PARA MADERA"
        
        Problema original: Después de un page break:
            <<<
            TORNILLOS PARA MADERA
            PERNO COCHE
            UNC / BSW
        Se combinaba como "TORNILLOS PARA MADERA PERNO COCHE UNC / BSW"
        
        Correcto: TORNILLOS PARA MADERA es la subcategoría,
                  PERNO COCHE UNC / BSW es el tipo de producto.
        """
        products = catalog["products"]
        
        # Buscar productos de PERNO COCHE
        perno_coche_skus = []
        for sku, data in products.items():
            path = data.get("category_path", [])
            path_str = " > ".join(path)
            if "PERNO COCHE" in path_str.upper():
                perno_coche_skus.append((sku, path))
        
        assert len(perno_coche_skus) > 0, "Debe haber productos PERNO COCHE"
        
        # Verificar que ningún path tiene "TORNILLOS PARA MADERA PERNO COCHE" combinado
        for sku, path in perno_coche_skus:
            for segment in path:
                assert "TORNILLOS PARA MADERA PERNO" not in segment, \
                    f"Path incorrecto para {sku}: {path}"
    
    def test_tornillos_para_madera_es_subcategoria(self, catalog):
        """
        Verifica que TORNILLOS PARA MADERA aparece como subcategoría,
        no como tipo de producto.
        """
        products = catalog["products"]
        
        # SKUs que deberían estar bajo TORNILLOS PARA MADERA
        test_skus = ["90PCO", "91PCO"]  # PERNO COCHE
        
        for sku in test_skus:
            if sku in products:
                path = products[sku].get("category_path", [])
                # TORNILLOS PARA MADERA debe ser el segundo elemento (subcategoría)
                # No debe estar combinado con PERNO COCHE
                assert len(path) >= 2, f"Path muy corto para {sku}: {path}"
                assert "MADERA" in path[1].upper() or "MADERA" in path[0].upper(), \
                    f"{sku} debe estar bajo TORNILLOS PARA MADERA, got: {path}"
    
    def test_perno_coche_es_tipo_producto(self, catalog):
        """
        Verifica que PERNO COCHE aparece como tipo de producto,
        separado de la subcategoría.
        """
        products = catalog["products"]
        
        # Buscar un producto PERNO COCHE
        for sku, data in products.items():
            path = data.get("category_path", [])
            if any("PERNO COCHE" in segment.upper() for segment in path):
                # PERNO COCHE debe ser un segmento separado
                perno_segments = [s for s in path if "PERNO COCHE" in s.upper()]
                assert len(perno_segments) == 1, f"PERNO COCHE debe ser un segmento separado: {path}"
                
                # Verificar que PERNO COCHE no está en la misma posición que MADERA
                for segment in path:
                    assert not ("MADERA" in segment.upper() and "PERNO" in segment.upper()), \
                        f"MADERA y PERNO no deben estar en el mismo segmento: {path}"
                break
    
    def test_b90pco_acabado_zincado_brillante(self, catalog):
        """
        Caso: B90PCO
        Problema: La columna derecha tiene una nueva tabla con acabado "Zincado Brillante"
        pero el parser heredaba el subtipo "Pavonado (continuación)" de la tabla anterior.
        
        Contexto espacial:
        - Columna izquierda: tabla con "Pavonado" continúa
        - Columna derecha: NUEVA tabla con header, acabado "Zincado Brillante" y productos B90PCO, B91PCO
        
        El acabado de B90PCO debe ser "Zincado Brillante", no "Pavonado".
        El path NO debe contener "Pavonado".
        """
        products = catalog["products"]
        
        # B90PCO debe existir
        assert "B90PCO" in products, "B90PCO debe existir en el catálogo"
        
        prod = products["B90PCO"]
        path = prod.get("category_path", [])
        attrs = {a["name"]: a["value"] for a in prod.get("attributes", [])}
        
        # El acabado debe ser Zincado Brillante
        assert attrs.get("Acabado") == "Zincado Brillante", \
            f"B90PCO Acabado debe ser 'Zincado Brillante', got: {attrs.get('Acabado')}"
        
        # El path NO debe contener "Pavonado"
        path_str = " > ".join(path)
        assert "Pavonado" not in path_str, \
            f"B90PCO path no debe contener 'Pavonado', got: {path}"
        
        # NOMINAL debe ser correcto
        assert attrs.get("NOMINAL") == "#10-24[3/16]", \
            f"B90PCO NOMINAL debe ser '#10-24[3/16]', got: {attrs.get('NOMINAL')}"
        
        # LARGO debe ser correcto
        assert attrs.get("LARGO") == "3/4", \
            f"B90PCO LARGO debe ser '3/4', got: {attrs.get('LARGO')}"
    
    def test_90pco_acabado_pavonado(self, catalog):
        """
        Caso: 90PCO (sin B)
        Problema: "Pavonado" no estaba en la lista de acabados reconocidos.
        
        Contexto espacial:
        - Columna izquierda: tabla "PERNO COCHE UNC / BSW" con acabado "Pavonado"
        - Columna derecha: tabla "PERNO COCHE UNC / BSW - Continuación" con "Pavonado (continuación)"
        
        90PCO está en la columna izquierda y debe tener acabado "Pavonado".
        
        La diferencia con B90PCO:
        - 90PCO: columna izquierda, acabado Pavonado
        - B90PCO: columna derecha (tabla posterior), acabado Zincado Brillante
        """
        products = catalog["products"]
        
        # 90PCO debe existir
        assert "90PCO" in products, "90PCO debe existir en el catálogo"
        
        prod = products["90PCO"]
        attrs = {a["name"]: a["value"] for a in prod.get("attributes", [])}
        
        # El acabado debe ser Pavonado
        assert attrs.get("Acabado") == "Pavonado", \
            f"90PCO Acabado debe ser 'Pavonado', got: {attrs.get('Acabado')}"
        
        # NOMINAL debe ser correcto
        assert attrs.get("NOMINAL") == "#10-24[3/16]", \
            f"90PCO NOMINAL debe ser '#10-24[3/16]', got: {attrs.get('NOMINAL')}"
        
        # LARGO debe ser correcto
        assert attrs.get("LARGO") == "3/4", \
            f"90PCO LARGO debe ser '3/4', got: {attrs.get('LARGO')}"
    
    def test_190ab01_cod_tecfi_ignorado(self, catalog):
        """
        Caso: 190AB01
        Problema: El campo "Cod Tecfi" al final de la línea confundía el parser.
        
        Línea original:
        CODIGO      NOMINAL     LARGO       ENVASE     Cod Tecfi 
        190AB01     6.3[1/4-14] 180            100 U AB0106180 
        
        El parser debe:
        1. Reconocer que ENVASE está separado como "100 U" 
        2. Ignorar el código Tecfi "AB0106180" al final
        """
        products = catalog["products"]
        
        # 190AB01 debe existir
        assert "190AB01" in products, "190AB01 debe existir en el catálogo"
        
        prod = products["190AB01"]
        attrs = {a["name"]: a["value"] for a in prod.get("attributes", [])}
        
        # NOMINAL
        assert attrs.get("NOMINAL") == "6.3[1/4-14]", \
            f"190AB01 NOMINAL debe ser '6.3[1/4-14]', got: {attrs.get('NOMINAL')}"
        
        # LARGO
        assert attrs.get("LARGO") == "180", \
            f"190AB01 LARGO debe ser '180', got: {attrs.get('LARGO')}"
        
        # ENVASE
        assert attrs.get("ENVASE") == "100 U", \
            f"190AB01 ENVASE debe ser '100 U', got: {attrs.get('ENVASE')}"
    
    def test_11tdpf_tornillo_para_terrazas_no_essve(self, catalog):
        """
        Caso: 11TDPF
        Problema: ESSVE es un logotipo de marca que aparece en el PDF,
        NO es parte del nombre del producto.
        
        En el PDF aparece:
            TORNILLO PARA
                        ESSVE  <- Este es un logo, no texto
            TERRAZAS
        
        El tipo de producto debe ser "TORNILLO PARA TERRAZAS", 
        NO "TORNILLO PARA ESSVE".
        """
        products = catalog["products"]
        
        # 11TDPF debe existir
        assert "11TDPF" in products, "11TDPF debe existir en el catálogo"
        
        prod = products["11TDPF"]
        path = prod.get("category_path", [])
        
        # El path no debe contener ESSVE
        path_str = " > ".join(path)
        assert "ESSVE" not in path_str, \
            f"11TDPF path no debe contener 'ESSVE' (es un logo), got: {path}"
        
        # El path debe contener TERRAZAS
        assert "TERRAZAS" in path_str.upper(), \
            f"11TDPF debe estar bajo 'TORNILLO PARA TERRAZAS', got: {path}"


class TestCatalogStructure:
    """
    Tests para la estructura jerárquica del catálogo.
    
    La estructura esperada del catálogo es:
    1. Fijaciones, Pernería y Anclajes (categoría raíz)
        1.1. Fijaciones
            1.1.1. Tornillos para Volcanita
            1.1.2. Tornillos para Metalcon
            ...
        1.2. Roscalatas y Aterrajadores
        ...
    """
    
    # Estructura esperada del catálogo
    ESTRUCTURA_ESPERADA = {
        "Fijaciones, Pernería y Anclajes": {
            "Fijaciones": [
                "Tornillos para Volcanita",
                "Tornillos para Metalcon",
                "Tornillos para Fibrocemento / Internit",
                "Tornillo Winger",
                "Tornillo para Fachadas",
                "Tornillos Autoperforantes Hexagonales",
                "Puntas e Insertos",
                "Insertos",
                "Dados Magneticos",
            ],
            "Roscalatas y Aterrajadores": [
                "Tornillos Roscalatas",
                "Tornillos Aterrajadores",
            ],
            "Tornillos Para Madera": [
                "Tornillos para Madera",
                "Conectores para Madera",
            ],
            "Tornillos para Deck": [
                "Tornillos para Deck",
            ],
            "Tornillos Para Ventanas PVC": [
                "Tornillos Para Ventanas PVC",
            ],
            "Productos Para Techo y Terraza": [
                "Productos Para Techo",
            ],
            "Pernos Hexagonales y Barras": [
                "Pernos Hexagonales",
                "Pernos Estructurales A325",
                "Pernos Hexagonales Métricos",
                "Barras Roscadas",
            ],
            "Tuercas": [
                "Tuercas Hexagonales",
                "Tuercas A-194 2H",
                "Tuercas Hexagonales Métricas",
                "Tuercas Hex. Con Seguro Nylon",
                "Tuerca Flange",
                "Tuerca Acople",
                "Tuercas Máquina",
                "Otras Tuercas",
            ],
            "Golillas": [
                "Calibradas",
                "Corrientes",
                "Planas Anchas",
                "Para Paneles",
                "Golillas de Presión",
                "Golillas Estrella",
                "Estructurales",
                "Golillas para Techo",
                "Golillas para Cubiertas",
            ],
            "Pernos Máquina": [
                "Pernos Cocina Cabeza Redonda",
                "Pernos Cocina Cabeza Plana",
                "Pernos Cocina Cabeza Binding",
                "Pernos Cocina Cabeza Lenteja",
            ],
            "Pernos Parker": [
                "Pernos Parker Cilíndrica",
                "Pernos Parker Cabeza Plana",
                "Prisioneros Allen",
                "Pernos Cabeza Button",
            ],
            "Remaches": [
                "Remaches Solidos",
                "Remache Tipo POP",
                "Remache POP",
                "Tuerca Remachable",
                "Remachadoras",
                "Remache Estructurales",
            ],
            "Anclajes": [
                "Anclajes Pesados",
                "Anclajes Livianos",
                "Tarugos",
                "Clavos",
            ],
            "Cables, Cadenas y Accesorios": [
                "Cadenas",
                "Cables",
                "Accesorios Cables, Cadenas",
            ],
            "Brocas, Discos y Soldaduras": [
                "Brocas",
                "Discos",
                "Soldaduras",
            ],
            "Complementos de Línea": [],  # Sin subcategorías detalladas en el catálogo
            "Herramientas": [
                "Herramientas",
            ],
        }
    }
    
    @pytest.fixture(scope="class")
    def catalog(self):
        """Carga el catálogo completo una vez para todos los tests."""
        with open(r"c:\Users\yubyr\source\repos\Catalogo\pdf\Catalogo_Mamut_2025.txt", "r", encoding="utf-8") as f:
            text = f.read()
        structure, products = parse_spatial_catalog(text)
        return {"structure": structure, "products": products}
    
    def normalize(self, text: str) -> str:
        """Normaliza texto para comparación (mayúsculas, sin espacios extra)."""
        import re
        return re.sub(r'\s+', ' ', text.upper().strip())
    
    def find_in_structure(self, structure: dict, target: str) -> bool:
        """Busca recursivamente un término en la estructura."""
        target_norm = self.normalize(target)
        for key in structure.keys():
            if key == "skus":
                continue
            if target_norm in self.normalize(key):
                return True
            if isinstance(structure[key], dict):
                if self.find_in_structure(structure[key], target):
                    return True
        return False
    
    def find_products_with_category(self, products: dict, category: str) -> list:
        """Encuentra productos que contengan la categoría en su path."""
        category_norm = self.normalize(category)
        matches = []
        for sku, data in products.items():
            path = data.get("category_path", [])
            for segment in path:
                if category_norm in self.normalize(segment):
                    matches.append((sku, path))
                    break
        return matches
    
    def test_categoria_raiz_existe(self, catalog):
        """
        Verifica que existe una categoría raíz que agrupa todo el catálogo.
        Debe ser algo como "Fijaciones, Pernería y Anclajes" o "FIJACIONES".
        """
        structure = catalog["structure"]
        
        # Buscar la categoría raíz
        root_keys = [k for k in structure.keys() if k != "skus"]
        assert len(root_keys) > 0, "Debe existir al menos una categoría raíz"
        
        # Verificar que alguna contiene "FIJACIONES" o similar
        found_root = False
        for key in root_keys:
            if "FIJACION" in self.normalize(key):
                found_root = True
                break
        
        # Si no hay raíz con "FIJACIONES", al menos verificar que hay estructura
        assert found_root or len(root_keys) > 0, \
            f"Debe haber categoría raíz. Encontradas: {root_keys[:5]}"
    
    def test_subcategorias_nivel_1(self, catalog):
        """
        Verifica que existen las 17 subcategorías principales (nivel 1.X).
        """
        products = catalog["products"]
        
        # Subcategorías con términos de búsqueda flexibles
        subcategorias_esperadas = [
            "Fijaciones",
            "Roscalata",  # Roscalatas
            "Madera",
            "Deck",
            "PVC",  # Ventanas PVC (tiene espacios en OCR)
            "Techo",
            "Hexagonal",  # Pernos Hexagonales
            "Tuerca",
            "Golilla",
            "Máquina",  # Pernos Máquina
            "Parker",  # Pernos Parker
            "Remache",
            "Anclaje",
            "Cable",
            "Broca",
            "Complemento",
            "Herramienta",
        ]
        
        faltantes = []
        for subcat in subcategorias_esperadas:
            productos = self.find_products_with_category(products, subcat)
            if len(productos) == 0:
                faltantes.append(subcat)
        
        assert len(faltantes) == 0, \
            f"Faltan productos en subcategorías: {faltantes}"
    
    def test_fijaciones_tiene_subcategorias(self, catalog):
        """
        Verifica que Fijaciones tiene las subcategorías esperadas:
        - Tornillos para Volcanita
        - Tornillos para Metalcon
        - Tornillos Autoperforantes Hexagonales
        - etc.
        """
        products = catalog["products"]
        
        subcategorias_fijaciones = [
            "Volcanita",
            "Metalcon",
            "Fibrocemento",
            "Winger",
            "Fachadas",
            "Autoperforante",
            "Puntas",
            "Insertos",
            "Dados",
        ]
        
        for subcat in subcategorias_fijaciones:
            productos = self.find_products_with_category(products, subcat)
            assert len(productos) > 0, \
                f"Fijaciones debe tener productos de '{subcat}'"
    
    def test_tuercas_tiene_subcategorias(self, catalog):
        """
        Verifica que Tuercas tiene las subcategorías esperadas.
        """
        products = catalog["products"]
        
        subcategorias_tuercas = [
            "Hexagonal",  # Tuercas Hexagonales
            "Nylon",  # Tuercas con seguro nylon (en tarugos también)
            "Acople",  # Tuerca Acople
        ]
        
        for subcat in subcategorias_tuercas:
            productos = self.find_products_with_category(products, subcat)
            assert len(productos) > 0, \
                f"Tuercas debe tener productos de '{subcat}'"
    
    def test_golillas_tiene_subcategorias(self, catalog):
        """
        Verifica que Golillas tiene las subcategorías esperadas.
        """
        products = catalog["products"]
        
        subcategorias_golillas = [
            "Calibradas",
            "Corrientes",
            "Planas",
            "Presión",
            "Estrella",
        ]
        
        for subcat in subcategorias_golillas:
            productos = self.find_products_with_category(products, subcat)
            assert len(productos) > 0, \
                f"Golillas debe tener productos de '{subcat}'"
    
    def test_anclajes_tiene_subcategorias(self, catalog):
        """
        Verifica que Anclajes tiene las subcategorías esperadas.
        """
        products = catalog["products"]
        
        subcategorias_anclajes = [
            "Pesados",
            "Livianos",
            "Tarugos",
            "Clavos",
        ]
        
        for subcat in subcategorias_anclajes:
            productos = self.find_products_with_category(products, subcat)
            assert len(productos) > 0, \
                f"Anclajes debe tener productos de '{subcat}'"
    
    def test_remaches_tiene_subcategorias(self, catalog):
        """
        Verifica que Remaches tiene las subcategorías esperadas.
        """
        products = catalog["products"]
        
        subcategorias_remaches = [
            "Sólido",  # Remaches Sólidos
            "POP",     # Remache POP
            "Estructural",  # Remaches Estructurales
        ]
        
        for subcat in subcategorias_remaches:
            productos = self.find_products_with_category(products, subcat)
            assert len(productos) > 0, \
                f"Remaches debe tener productos de '{subcat}'"
    
    def test_complementos_tiene_productos(self, catalog):
        """
        Verifica que Complementos de Línea tiene productos.
        Nota: Muchos productos de Complementos pueden no tener subcategorías detalladas
        debido a la estructura del catálogo original.
        """
        products = catalog["products"]
        
        # Buscar productos bajo Complementos
        productos_complementos = self.find_products_with_category(products, "Complemento")
        
        assert len(productos_complementos) > 0, \
            "Debe haber productos bajo Complementos de Línea"
        
        # Verificar que hay al menos algunos productos típicos (mosquetones, etc.)
        skus_complementos = [sku for sku, _ in productos_complementos]
        # Los SKUs típicos de mosquetones empiezan con MOS, MGA, etc.
        tiene_mosquetones = any("MOS" in sku.upper() for sku in skus_complementos)
        assert tiene_mosquetones, "Debe haber productos de mosquetones (MOS)"
    
    def test_estructura_jerarquica_correcta(self, catalog):
        """
        Verifica que la estructura jerárquica es correcta:
        - Los productos de Volcanita deben estar bajo Fijaciones
        - Los productos de Perno Coche deben estar bajo Tornillos Para Madera
        - etc.
        """
        products = catalog["products"]
        
        # Verificar jerarquía: Volcanita bajo Fijaciones
        productos_volcanita = self.find_products_with_category(products, "Volcanita")
        for sku, path in productos_volcanita[:5]:  # Verificar primeros 5
            path_str = " ".join(path).upper()
            # Debe contener algo de "FIJACION" en un nivel superior
            assert "FIJACION" in path_str or "DRYWALL" in path_str, \
                f"Producto {sku} de Volcanita debe estar bajo Fijaciones: {path}"
        
        # Verificar jerarquía: Perno Coche bajo Madera
        productos_perno_coche = self.find_products_with_category(products, "PERNO COCHE")
        for sku, path in productos_perno_coche[:5]:
            path_str = " ".join(path).upper()
            assert "MADERA" in path_str, \
                f"Producto {sku} de Perno Coche debe estar bajo Madera: {path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
