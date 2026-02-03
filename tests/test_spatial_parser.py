"""
Tests para el parser espacial del catálogo.
Casos problemáticos detectados durante el desarrollo.
"""
import sys
sys.path.insert(0, r"c:\Users\yubyr\source\repos\Catalogo")

import pytest
from src.catalogo_spatial_parser import parse_spatial_catalog, parse_row_parts, looks_like_sku


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
    
    def test_no_sku(self):
        assert looks_like_sku("#10-16") == False  # Es NOMINAL
        assert looks_like_sku("500 U") == False   # Es ENVASE
        assert looks_like_sku('1"') == False      # Es LARGO
        assert looks_like_sku("") == False
        assert looks_like_sku("A") == False       # Muy corto


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
