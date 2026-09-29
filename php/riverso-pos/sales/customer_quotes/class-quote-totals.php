<?php
/**
 * Totales de cabecera a partir de las líneas.
 * El descuento, el margen y la utilidad se calculan aunque el modo avanzado
 * esté apagado y la vista base no muestre esas columnas.
 *
 * Dscto precio: porcentaje sobre el bruto (cantidad × precio).
 * Dscto margen: porcentaje del margen que queda después de ese descuento
 * (precio ya descontado menos costo). Sin costo, el dscto margen se guarda
 * pero no descuenta dinero.
 * Si ambos porcentajes quedan en 0, se respeta discount_amount (líneas anteriores).
 */

declare(strict_types=1);

final class Riverso_POS_Quote_Totals {
    public const LOW_MARGIN_PERCENT = 5.0;

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
            $price_rate = self::rate($line['price_discount'] ?? 0);
            $margin_rate = self::rate($line['margin_discount'] ?? 0);
            $gross = round($qty * $price, 2);
            $has_cost = array_key_exists('unit_cost', $line) && $line['unit_cost'] !== null && $line['unit_cost'] !== '';
            $unit_cost = $has_cost ? round((float) $line['unit_cost'], 2) : null;

            if ($price_rate > 0 || $margin_rate > 0) {
                $discount = self::discount_from_rates($gross, $qty, $unit_cost, $price_rate, $margin_rate);
            } else {
                $discount = round((float) ($line['discount_amount'] ?? 0), 2);
                if ($discount < 0) {
                    $discount = 0.0;
                }
                if ($discount > $gross) {
                    $discount = $gross;
                }
            }

            $line_net = round($gross - $discount, 2);
            $line_profit = null;
            $line_margin = null;
            if ($unit_cost === null) {
                $profit_known = false;
            } else {
                $line_profit = round($line_net - round($qty * $unit_cost, 2), 2);
                $line_margin = $line_net > 0 ? round(($line_profit / $line_net) * 100, 2) : 0.0;
                $profit += $line_profit;
            }
            $net += $line_net;
            $discounts += $discount;
            $normalized[] = array_merge($line, [
                'quantity' => $qty,
                'unit_price' => $price,
                'price_discount' => $price_rate,
                'margin_discount' => $margin_rate,
                'discount_amount' => $discount,
                'unit_cost' => $unit_cost,
                'line_net' => $line_net,
                'line_profit' => $line_profit,
                'line_margin_percent' => $line_margin,
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

    /**
     * Alarma visual. No bloquea pasar a lista.
     * - neg: utilidad negativa
     * - low: utilidad no negativa y margen menor a 5 %
     */
    public static function alarm(?float $profit, ?float $margin_percent): string {
        if ($profit === null) {
            return '';
        }
        if ($profit < 0) {
            return 'neg';
        }
        if ($margin_percent !== null && $margin_percent < self::LOW_MARGIN_PERCENT) {
            return 'low';
        }
        return '';
    }

    private static function rate(mixed $value): float {
        $rate = round((float) $value, 2);
        if ($rate < 0) {
            return 0.0;
        }
        if ($rate > 100) {
            return 100.0;
        }
        return $rate;
    }

    private static function discount_from_rates(
        float $gross,
        float $qty,
        ?float $unit_cost,
        float $price_rate,
        float $margin_rate
    ): float {
        $price_off = round($gross * $price_rate / 100, 2);
        $after = round($gross - $price_off, 2);
        $margin_off = 0.0;
        if ($unit_cost !== null && $margin_rate > 0) {
            $margin_base = round($after - round($qty * $unit_cost, 2), 2);
            if ($margin_base > 0) {
                $margin_off = round($margin_base * $margin_rate / 100, 2);
            }
        }
        $discount = round($price_off + $margin_off, 2);
        if ($discount < 0) {
            return 0.0;
        }
        if ($discount > $gross) {
            return $gross;
        }
        return $discount;
    }
}
