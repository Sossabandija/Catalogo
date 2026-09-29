<?php
/**
 * Fase 003: vendedor de la cotización.
 * La fecha de emisión sigue siendo created_at; el listado la expone como issued_at.
 */

declare(strict_types=1);

final class Riverso_POS_Phase_003_Quote_Header_Identity implements Riverso_POS_Migration_Phase {
    public function id(): string {
        return '003_quote_header_identity';
    }

    public function up(Riverso_POS_Database $db): void {
        $quotes = $db->table('customer_quotes');
        $this->add_column($db, $quotes, 'seller_id', 'bigint(20) unsigned NULL', 'integer NULL');
        $this->add_column($db, $quotes, 'seller_name', "varchar(191) NOT NULL DEFAULT ''", "text NOT NULL DEFAULT ''");
    }

    private function add_column(
        Riverso_POS_Database $db,
        string $table,
        string $column,
        string $mysql_def,
        string $sqlite_def
    ): void {
        $columns = $db->columns($table);
        if (in_array($column, $columns, true)) {
            return;
        }
        $definition = $db->dialect() === 'sqlite' ? $sqlite_def : $mysql_def;
        $db->exec('ALTER TABLE ' . $table . ' ADD COLUMN ' . $column . ' ' . $definition);
    }
}
