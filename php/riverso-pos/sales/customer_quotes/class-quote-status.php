<?php
/**
 * Estados de cotización de venta.
 *
 * El esbozo anterior usaba draft / sent / viewed / accepted / rejected.
 * El plan de cotizaciones solo opera borrador ↔ lista en este corte.
 * Facturada queda reservada y no tiene transición.
 *
 * Mapeo legado → plan:
 * - draft, borrador, rejected, expired, cancelled → draft (Borrador)
 * - sent, viewed, accepted, approved, lista, listed → listed (Lista)
 * - invoiced, billed, facturada → invoiced (Facturada)
 */

declare(strict_types=1);

final class Riverso_POS_Quote_Status {
    public const DRAFT = 'draft';
    public const LISTED = 'listed';
    public const INVOICED = 'invoiced';

    public static function label(string $status): string {
        return match (self::normalize_legacy($status)) {
            self::LISTED => 'Lista',
            self::INVOICED => 'Facturada',
            default => 'Borrador',
        };
    }

    public static function normalize_legacy(string $status): string {
        $status = strtolower(trim($status));
        $map = [
            'draft' => self::DRAFT,
            'borrador' => self::DRAFT,
            'rejected' => self::DRAFT,
            'expired' => self::DRAFT,
            'cancelled' => self::DRAFT,
            'canceled' => self::DRAFT,
            'sent' => self::LISTED,
            'viewed' => self::LISTED,
            'accepted' => self::LISTED,
            'approved' => self::LISTED,
            'lista' => self::LISTED,
            'listed' => self::LISTED,
            'invoiced' => self::INVOICED,
            'billed' => self::INVOICED,
            'facturada' => self::INVOICED,
        ];
        return $map[$status] ?? self::DRAFT;
    }

    public static function can_transition(string $from, string $to): bool {
        $from = self::normalize_legacy($from);
        $to = strtolower(trim($to));
        if (!in_array($to, [self::DRAFT, self::LISTED, self::INVOICED], true)) {
            return false;
        }
        if ($from === $to) {
            return true;
        }
        return ($from === self::DRAFT && $to === self::LISTED)
            || ($from === self::LISTED && $to === self::DRAFT);
    }

    /**
     * @return list<string>
     */
    public static function allowed_targets(string $status): array {
        $status = self::normalize_legacy($status);
        return match ($status) {
            self::DRAFT => [self::LISTED],
            self::LISTED => [self::DRAFT],
            default => [],
        };
    }

    public static function transition_label(string $target): string {
        return match ($target) {
            self::LISTED => 'Pasar a lista',
            self::DRAFT => 'Volver a borrador',
            default => '',
        };
    }
}

final class Riverso_POS_Quote_Type {
    public const VENTA = 'venta';
    public const REFERENCIA = 'referencia';

    public static function label(string $type): string {
        return $type === self::REFERENCIA ? 'Referencia' : 'Venta';
    }

    public static function normalize(?string $type): string {
        $type = strtolower(trim((string) $type));
        if ($type === '' || $type === self::VENTA) {
            return self::VENTA;
        }
        if ($type === self::REFERENCIA) {
            return self::REFERENCIA;
        }
        throw new Riverso_POS_Quote_Exception('El tipo de cotización debe ser venta o referencia.');
    }
}
