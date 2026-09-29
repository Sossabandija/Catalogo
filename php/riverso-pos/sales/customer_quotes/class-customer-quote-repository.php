<?php

declare(strict_types=1);

final class Riverso_POS_Customer_Quote_Repository {
    public function __construct(private Riverso_POS_Database $db) {
    }

    /**
     * @param array{status?: string} $filters
     * @return list<array<string, mixed>>
     */
    public function list_quotes(array $filters = []): array {
        $table = $this->quotes_table();
        $items = $this->items_table();
        $sql = 'SELECT q.*, (SELECT COUNT(*) FROM ' . $items . ' i WHERE i.quote_id = q.id) AS line_count
                FROM ' . $table . ' q';
        $params = [];
        if (!empty($filters['status'])) {
            $sql .= ' WHERE q.status = ?';
            $params[] = Riverso_POS_Quote_Status::normalize_legacy((string) $filters['status']);
        }
        $sql .= ' ORDER BY q.updated_at DESC, q.id DESC';
        $rows = $this->db->fetch_all($sql, $params);
        return array_map(fn (array $row): array => $this->present_summary($row), $rows);
    }

    /**
     * @return array<string, mixed>|null
     */
    public function find(int $id): ?array {
        $row = $this->db->fetch_one(
            'SELECT * FROM ' . $this->quotes_table() . ' WHERE id = ?',
            [$id]
        );
        if ($row === null) {
            return null;
        }
        $lines = $this->db->fetch_all(
            'SELECT * FROM ' . $this->items_table() . ' WHERE quote_id = ? ORDER BY sort_order ASC, id ASC',
            [$id]
        );
        return $this->present($row, $lines);
    }

    /**
     * @param array<string, mixed> $input
     * @return array<string, mixed>
     */
    public function save(array $input): array {
        if (!isset($input['lines']) || !is_array($input['lines'])) {
            throw new Riverso_POS_Quote_Exception('La cotización no incluye líneas.');
        }
        if (count($input['lines']) > 200) {
            throw new Riverso_POS_Quote_Exception('La cotización admite hasta 200 líneas.');
        }

        $id = isset($input['id']) && $input['id'] !== '' && $input['id'] !== null ? (int) $input['id'] : 0;
        $existing = $id > 0 ? $this->find($id) : null;
        if ($id > 0 && $existing === null) {
            throw new Riverso_POS_Quote_Exception('Cotización no encontrada.');
        }
        if ($existing !== null && $existing['status'] === Riverso_POS_Quote_Status::INVOICED) {
            throw new Riverso_POS_Quote_Exception('Una cotización facturada no se puede editar en este corte.');
        }

        $customer_name = $this->clip((string) ($input['customer_name'] ?? ''), 191);
        $customer_id = $input['customer_id'] ?? null;
        $customer_id = $customer_id === '' || $customer_id === null ? null : (int) $customer_id;
        if ($customer_id !== null && $customer_id <= 0) {
            $customer_id = null;
        }
        $quote_type = Riverso_POS_Quote_Type::normalize(isset($input['quote_type']) ? (string) $input['quote_type'] : null);
        $validity_days = $this->validity_days($input['validity_days'] ?? null);
        $validity_terms = $this->nullable_text($input['validity_terms'] ?? null, 2000);
        $notes = $this->nullable_text($input['notes'] ?? ($existing['notes'] ?? null), 5000) ?? '';

        $lines = [];
        foreach ($input['lines'] as $line) {
            if (!is_array($line)) {
                throw new Riverso_POS_Quote_Exception('Hay una línea de cotización inválida.');
            }
            $lines[] = $this->normalize_line($line);
        }
        $totals = Riverso_POS_Quote_Totals::calculate($lines);
        $now = gmdate('Y-m-d H:i:s');

        $saved_id = $this->db->transaction(function () use (
            $existing,
            $customer_id,
            $customer_name,
            $quote_type,
            $validity_days,
            $validity_terms,
            $notes,
            $totals,
            $now
        ): int {
            $header = [
                'customer_id' => $customer_id,
                'customer_name' => $customer_name,
                'quote_type' => $quote_type,
                'validity_days' => $validity_days,
                'validity_terms' => $validity_terms,
                'notes' => $notes,
                'total' => $totals['net_total'],
                'net_total' => $totals['net_total'],
                'discount_total' => $totals['discount_total'],
                'margin_percent' => $totals['margin_percent'],
                'profit_total' => $totals['profit_total'],
                'updated_at' => $now,
            ];
            if ($existing === null) {
                $header['quote_number'] = $this->next_number();
                $header['status'] = Riverso_POS_Quote_Status::DRAFT;
                $header['created_at'] = $now;
                $quote_id = $this->db->insert($this->quotes_table(), $header);
            } else {
                $quote_id = (int) $existing['id'];
                $this->db->update($this->quotes_table(), $header, 'id = ?', [$quote_id]);
                $this->db->execute('DELETE FROM ' . $this->items_table() . ' WHERE quote_id = ?', [$quote_id]);
            }
            foreach ($totals['lines'] as $line) {
                $this->db->insert($this->items_table(), [
                    'quote_id' => $quote_id,
                    'product_id' => $line['product_id'],
                    'sku' => $line['sku'],
                    'supplier_code' => $line['supplier_code'] !== '' ? $line['supplier_code'] : null,
                    'barcode' => $line['barcode'] !== '' ? $line['barcode'] : null,
                    'description' => $line['description'],
                    'quantity' => $line['quantity'],
                    'unit_price' => $line['unit_price'],
                    'unit_cost' => $line['unit_cost'],
                    'discount_amount' => $line['discount_amount'],
                    'line_total' => $line['line_net'],
                    'sort_order' => $line['sort_order'],
                ]);
            }
            return $quote_id;
        });

        $quote = $this->find($saved_id);
        if ($quote === null) {
            throw new Riverso_POS_Quote_Exception('No se pudo leer la cotización guardada.');
        }
        return $quote;
    }

    /**
     * @return array<string, mixed>
     */
    public function transition(int $id, string $to): array {
        $quote = $this->find($id);
        if ($quote === null) {
            throw new Riverso_POS_Quote_Exception('Cotización no encontrada.');
        }
        $to = strtolower(trim($to));
        if (!Riverso_POS_Quote_Status::can_transition((string) $quote['status'], $to)) {
            throw new Riverso_POS_Quote_Exception('Solo se puede pasar entre Borrador y Lista. Facturada queda para más adelante.');
        }
        if ($quote['status'] !== $to) {
            $this->db->update($this->quotes_table(), [
                'status' => $to,
                'updated_at' => gmdate('Y-m-d H:i:s'),
            ], 'id = ?', [$id]);
        }
        $updated = $this->find($id);
        if ($updated === null) {
            throw new Riverso_POS_Quote_Exception('Cotización no encontrada.');
        }
        return $updated;
    }

    /**
     * @param array<string, mixed> $line
     * @return array<string, mixed>
     */
    private function normalize_line(array $line): array {
        $sku = $this->clip(trim((string) ($line['sku'] ?? '')), 64);
        if ($sku === '') {
            throw new Riverso_POS_Quote_Exception('Cada línea necesita un SKU.');
        }
        $quantity = round((float) ($line['quantity'] ?? 0), 3);
        if ($quantity <= 0) {
            throw new Riverso_POS_Quote_Exception('La cantidad debe ser mayor a cero.');
        }
        $price = round((float) ($line['unit_price'] ?? 0), 2);
        if ($price < 0) {
            throw new Riverso_POS_Quote_Exception('El precio no puede ser negativo.');
        }
        $product_id = $line['product_id'] ?? null;
        $product_id = $product_id === '' || $product_id === null ? null : (int) $product_id;
        if ($product_id !== null && $product_id <= 0) {
            $product_id = null;
        }
        $description = $this->clip(trim((string) ($line['description'] ?? '')), 500);
        if ($description === '') {
            $description = $sku;
        }
        $unit_cost = $line['unit_cost'] ?? null;
        if ($unit_cost === '') {
            $unit_cost = null;
        }
        return [
            'product_id' => $product_id,
            'sku' => $sku,
            'supplier_code' => $this->clip(trim((string) ($line['supplier_code'] ?? '')), 64),
            'barcode' => $this->clip(trim((string) ($line['barcode'] ?? '')), 64),
            'description' => $description,
            'quantity' => $quantity,
            'unit_price' => $price,
            'unit_cost' => $unit_cost === null ? null : round((float) $unit_cost, 2),
            'discount_amount' => round((float) ($line['discount_amount'] ?? 0), 2),
        ];
    }

    private function validity_days(mixed $value): ?int {
        if ($value === null || $value === '') {
            return null;
        }
        if (!is_numeric($value)) {
            throw new Riverso_POS_Quote_Exception('La validez debe indicarse en días.');
        }
        $days = (int) $value;
        if ($days < 0) {
            throw new Riverso_POS_Quote_Exception('La validez en días no puede ser negativa.');
        }
        if ($days > 3650) {
            throw new Riverso_POS_Quote_Exception('La validez no puede superar 3650 días.');
        }
        return $days;
    }

    private function nullable_text(mixed $value, int $max): ?string {
        $text = trim((string) ($value ?? ''));
        if ($text === '') {
            return null;
        }
        return $this->clip($text, $max);
    }

    private function clip(string $value, int $max): string {
        if (function_exists('mb_substr')) {
            return mb_substr($value, 0, $max, 'UTF-8');
        }
        return substr($value, 0, $max);
    }

    private function next_number(): string {
        $year = gmdate('Y');
        $prefix = 'COT-' . $year . '-';
        $row = $this->db->fetch_one(
            'SELECT quote_number FROM ' . $this->quotes_table() . ' WHERE quote_number LIKE ? ORDER BY id DESC LIMIT 1',
            [$prefix . '%']
        );
        $seq = 1;
        if ($row && preg_match('/(\d+)$/', (string) $row['quote_number'], $matches)) {
            $seq = (int) $matches[1] + 1;
        }
        return $prefix . str_pad((string) $seq, 4, '0', STR_PAD_LEFT);
    }

    /**
     * @param array<string, mixed> $row
     * @return array<string, mixed>
     */
    private function present_summary(array $row): array {
        $presented = $this->present($row, []);
        unset($presented['lines']);
        $presented['line_count'] = (int) ($row['line_count'] ?? 0);
        return $presented;
    }

    /**
     * @param array<string, mixed> $row
     * @param list<array<string, mixed>> $lines
     * @return array<string, mixed>
     */
    private function present(array $row, array $lines): array {
        $status = Riverso_POS_Quote_Status::normalize_legacy((string) ($row['status'] ?? 'draft'));
        $type = (string) ($row['quote_type'] ?? Riverso_POS_Quote_Type::VENTA);
        $targets = Riverso_POS_Quote_Status::allowed_targets($status);
        return [
            'id' => (int) $row['id'],
            'quote_number' => (string) $row['quote_number'],
            'customer_id' => $this->nullable_int($row['customer_id'] ?? null),
            'customer_name' => (string) ($row['customer_name'] ?? ''),
            'quote_type' => $type,
            'quote_type_label' => Riverso_POS_Quote_Type::label($type),
            'status' => $status,
            'status_label' => Riverso_POS_Quote_Status::label($status),
            'validity_days' => $this->nullable_int($row['validity_days'] ?? null),
            'validity_terms' => (string) ($row['validity_terms'] ?? ''),
            'net_total' => round((float) ($row['net_total'] ?? 0), 2),
            'discount_total' => round((float) ($row['discount_total'] ?? 0), 2),
            'margin_percent' => $this->nullable_float($row['margin_percent'] ?? null),
            'profit_total' => $this->nullable_float($row['profit_total'] ?? null),
            'notes' => (string) ($row['notes'] ?? ''),
            'created_at' => (string) ($row['created_at'] ?? ''),
            'updated_at' => (string) ($row['updated_at'] ?? ''),
            'editable' => $status !== Riverso_POS_Quote_Status::INVOICED,
            'allowed_transitions' => array_map(static function (string $target): array {
                return [
                    'status' => $target,
                    'label' => Riverso_POS_Quote_Status::transition_label($target),
                ];
            }, $targets),
            'lines' => array_map(fn (array $line): array => $this->present_line($line), $lines),
        ];
    }

    /**
     * @param array<string, mixed> $line
     * @return array<string, mixed>
     */
    private function present_line(array $line): array {
        return [
            'id' => (int) ($line['id'] ?? 0),
            'product_id' => $this->nullable_int($line['product_id'] ?? null),
            'sku' => (string) ($line['sku'] ?? ''),
            'supplier_code' => (string) ($line['supplier_code'] ?? ''),
            'barcode' => (string) ($line['barcode'] ?? ''),
            'description' => (string) ($line['description'] ?? ''),
            'quantity' => round((float) ($line['quantity'] ?? 0), 3),
            'unit_price' => round((float) ($line['unit_price'] ?? 0), 2),
            'unit_cost' => $this->nullable_float($line['unit_cost'] ?? null),
            'discount_amount' => round((float) ($line['discount_amount'] ?? 0), 2),
            'line_net' => round((float) ($line['line_total'] ?? 0), 2),
        ];
    }

    private function nullable_int(mixed $value): ?int {
        if ($value === null || $value === '') {
            return null;
        }
        return (int) $value;
    }

    private function nullable_float(mixed $value): ?float {
        if ($value === null || $value === '') {
            return null;
        }
        return round((float) $value, 2);
    }

    private function quotes_table(): string {
        return $this->db->table('customer_quotes');
    }

    private function items_table(): string {
        return $this->db->table('customer_quote_items');
    }
}
