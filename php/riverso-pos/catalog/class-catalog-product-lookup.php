<?php
/**
 * Búsqueda de productos para la cotización.
 * La rápida usa SKU, código proveedor y código de barras.
 * La avanzada (lupa) suma la descripción y un alcance: todo, descripción o códigos.
 * No guarda una copia del catálogo.
 */

declare(strict_types=1);

final class Riverso_POS_Catalog_Product_Lookup {
    public function __construct(
        private Riverso_POS_Product_Lookup $products,
        private Riverso_POS_Barcode_Lookup $barcodes,
        private Riverso_POS_Supplier_Code_Lookup $suppliers,
        private Riverso_POS_Description_Lookup $descriptions
    ) {
    }

    /**
     * Búsqueda rápida: solo códigos. No consulta la descripción.
     *
     * @return list<array<string, mixed>>
     */
    public function search(string $query, int $limit = 20): array {
        return $this->collect(
            $query,
            $limit,
            $this->code_buckets($query, $limit),
            ['sku', 'supplier_code', 'barcode']
        );
    }

    /**
     * Búsqueda de la lupa.
     * scope: todo | descripcion | codigos (también acepta alias claros).
     *
     * @return list<array<string, mixed>>
     */
    public function search_advanced(string $query, string $scope = 'todo', int $limit = 20): array {
        $scope = self::normalize_scope($scope);
        $buckets = [];
        if ($scope !== 'codigos') {
            $buckets[] = $this->descriptions->search($query, $limit);
        }
        if ($scope !== 'descripcion') {
            array_push($buckets, ...$this->code_buckets($query, $limit));
        }
        return $this->collect($query, $limit, $buckets, self::fields_for_scope($scope));
    }

    public static function normalize_scope(string $scope): string {
        $scope = strtolower(trim($scope));
        $scope = strtr($scope, [
            'á' => 'a', 'é' => 'e', 'í' => 'i', 'ó' => 'o', 'ú' => 'u', 'ü' => 'u', 'ñ' => 'n',
        ]);
        return match ($scope) {
            'descripcion', 'description', 'desc' => 'descripcion',
            'codigos', 'codes', 'codigo', 'code' => 'codigos',
            default => 'todo',
        };
    }

    /**
     * @return list<string>
     */
    private static function fields_for_scope(string $scope): array {
        return match ($scope) {
            'descripcion' => ['description'],
            'codigos' => ['sku', 'supplier_code', 'barcode'],
            default => ['description', 'sku', 'supplier_code', 'barcode'],
        };
    }

    /**
     * @return list<list<array<string, mixed>>>
     */
    private function code_buckets(string $query, int $limit): array {
        return [
            $this->products->search($query, $limit),
            $this->suppliers->search($query, $limit),
            $this->barcodes->search($query, $limit),
        ];
    }

    /**
     * @param list<list<array<string, mixed>>> $buckets
     * @param list<string> $fields
     * @return list<array<string, mixed>>
     */
    private function collect(string $query, int $limit, array $buckets, array $fields): array {
        $query = trim($query);
        if ($query === '' || $limit <= 0) {
            return [];
        }
        $merged = [];
        foreach ($buckets as $rows) {
            foreach ($rows as $row) {
                $key = (string) ($row['product_id'] ?? '') . '|' . strtolower((string) ($row['sku'] ?? ''));
                $score = Riverso_POS_Catalog_Match::score($row, $fields, $query);
                if ($score === null) {
                    continue;
                }
                if (!isset($merged[$key]) || $score < $merged[$key]['_score']) {
                    $row['_score'] = $score;
                    $merged[$key] = $row;
                }
            }
        }
        $list = array_values($merged);
        usort($list, static fn (array $a, array $b): int => $a['_score'] <=> $b['_score']);
        foreach ($list as &$row) {
            unset($row['_score']);
        }
        unset($row);
        $list = array_slice($list, 0, $limit);
        if (function_exists('apply_filters')) {
            $filtered = apply_filters('riverso_catalog_search_products', $list, $query);
            if (is_array($filtered)) {
                $list = array_values($filtered);
            }
        }
        return $list;
    }
}
