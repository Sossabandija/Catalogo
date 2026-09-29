<?php
/**
 * Totales de cabecera a partir de las líneas.
 * El descuento, el margen y la utilidad se calculan aunque la vista base
 * no muestre columnas avanzadas.
 */

declare(strict_types=1);

final class Riverso_POS_Quote_Totals {
    /**
     * @param list<array<string, mixed>> $lines
     * @return array{
     *   net_total: float,
     *   discount_total: float,
     *   profit_total: float|null,
     *   margin_percent: float|null,
     *   lines: list<array<string, mixed>>
     * }
     */
    public static function calculate(array $lines): array {
        $net = 0.0;
        $discounts = 0.0;
        $profit = 0.0;
        $profit_known = $lines !== [];
        $normalized = [];

        foreach (array_values($lines) as $index => $line) {
            $qty = round((float) ($line['quantity'] ?? 0), 3);
            $price = round((float) ($line['unit_price'] ?? 0), 2);
            $discount = round((float) ($line['discount_amount'] ?? 0), 2);
            if ($discount < 0) {
                $discount = 0.0;
            }
            $gross = round($qty * $price, 2);
            if ($discount > $gross) {
                $discount = $gross;
            }
            $line_net = round($gross - $discount, 2);
            $has_cost = array_key_exists('unit_cost', $line) && $line['unit_cost'] !== null && $line['unit_cost'] !== '';
            $unit_cost = $has_cost ? round((float) $line['unit_cost'], 2) : null;
            $line_profit = null;
            if ($unit_cost === null) {
                $profit_known = false;
            } else {
                $line_profit = round($line_net - round($qty * $unit_cost, 2), 2);
                $profit += $line_profit;
            }
            $net += $line_net;
            $discounts += $discount;
            $normalized[] = array_merge($line, [
                'quantity' => $qty,
                'unit_price' => $price,
                'discount_amount' => $discount,
                'unit_cost' => $unit_cost,
                'line_net' => $line_net,
                'line_profit' => $line_profit,
                'sort_order' => $index,
            ]);
        }

        $net = round($net, 2);
        $discounts = round($discounts, 2);
        $profit_total = $profit_known ? round($profit, 2) : null;
        $margin = null;
        if ($profit_total !== null) {
            $margin = $net > 0 ? round(($profit_total / $net) * 100, 2) : 0.0;
        }

        return [
            'net_total' => $net,
            'discount_total' => $discounts,
            'profit_total' => $profit_total,
            'margin_percent' => $margin,
            'lines' => $normalized,
        ];
    }
}
