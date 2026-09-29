<?php

declare(strict_types=1);

define('RIVERSO_POS_DEV', true);
require dirname(__DIR__) . '/riverso-pos.php';

$failures = 0;

function check(bool $condition, string $message): void {
    global $failures;
    if ($condition) {
        echo "OK  {$message}\n";
        return;
    }
    $failures++;
    fwrite(STDERR, "FAIL {$message}\n");
}

function memory_db(): Riverso_POS_Pdo_Database {
    $pdo = new PDO('sqlite::memory:');
    return new Riverso_POS_Pdo_Database($pdo, 'wp_');
}

function catalog(): Riverso_POS_Catalog_Product_Lookup {
    $reader = new Riverso_POS_Memory_Catalog_Reader(require dirname(__DIR__) . '/dev/catalog-seed.php');
    return riverso_pos_catalog_lookup($reader);
}

echo "== estados ==\n";
check(Riverso_POS_Quote_Status::normalize_legacy('sent') === 'listed', 'sent → listed');
check(Riverso_POS_Quote_Status::normalize_legacy('viewed') === 'listed', 'viewed → listed');
check(Riverso_POS_Quote_Status::normalize_legacy('accepted') === 'listed', 'accepted → listed');
check(Riverso_POS_Quote_Status::normalize_legacy('rejected') === 'draft', 'rejected → draft');
check(Riverso_POS_Quote_Status::normalize_legacy('invoiced') === 'invoiced', 'invoiced se conserva');
check(Riverso_POS_Quote_Status::label('listed') === 'Lista', 'etiqueta Lista');
check(Riverso_POS_Quote_Status::label('draft') === 'Borrador', 'etiqueta Borrador');
check(Riverso_POS_Quote_Status::can_transition('draft', 'listed'), 'borrador → lista');
check(Riverso_POS_Quote_Status::can_transition('listed', 'draft'), 'lista → borrador');
check(!Riverso_POS_Quote_Status::can_transition('draft', 'invoiced'), 'no factura desde borrador');
check(!Riverso_POS_Quote_Status::can_transition('invoiced', 'listed'), 'facturada no vuelve a lista');
check(Riverso_POS_Quote_Type::label('referencia') === 'Referencia', 'etiqueta Referencia');

echo "== totales ==\n";
$totals = Riverso_POS_Quote_Totals::calculate([
    ['quantity' => 2, 'unit_price' => 1000, 'unit_cost' => 600, 'discount_amount' => 0],
]);
check($totals['net_total'] === 2000.0, 'neto 2000');
check($totals['profit_total'] === 800.0, 'utilidad 800');
check($totals['margin_percent'] === 40.0, 'margen 40');
$mixed = Riverso_POS_Quote_Totals::calculate([
    ['quantity' => 1, 'unit_price' => 1000, 'unit_cost' => 400],
    ['quantity' => 1, 'unit_price' => 500, 'unit_cost' => null],
]);
check($mixed['profit_total'] === null && $mixed['margin_percent'] === null, 'margen desconocido si falta costo');
$discounted = Riverso_POS_Quote_Totals::calculate([
    ['quantity' => 1, 'unit_price' => 1000, 'unit_cost' => 400, 'discount_amount' => 100],
]);
check($discounted['net_total'] === 900.0 && $discounted['discount_total'] === 100.0, 'descuento baja el neto');
$empty = Riverso_POS_Quote_Totals::calculate([]);
check($empty['net_total'] === 0.0 && $empty['margin_percent'] === null, 'cotización vacía sin margen');

echo "== migración ==\n";
$db = memory_db();
$phase1 = new Riverso_POS_Phase_001_Customer_Quotes_Base();
$phase2 = new Riverso_POS_Phase_002_Sale_Quote_Fields();
$phase1->up($db);
$quotes = $db->table('customer_quotes');
check($quotes === 'wp_riverso_customer_quotes', 'tabla con prefijo wp_riverso_');
check($db->table('customer_quote_items') === 'wp_riverso_customer_quote_items', 'tabla de líneas');
$now = '2020-05-01 10:00:00';
foreach (['sent', 'viewed', 'rejected', 'invoiced'] as $index => $status) {
    $db->insert($quotes, [
        'quote_number' => 'COT-2020-000' . ($index + 1),
        'customer_name' => 'Cliente legado',
        'status' => $status,
        'total' => 1500,
        'notes' => '',
        'created_at' => $now,
        'updated_at' => $now,
    ]);
}
$phase2->up($db);
$phase2->up($db);
$columns = $db->columns($quotes);
foreach (['customer_id', 'quote_type', 'validity_days', 'validity_terms', 'net_total', 'discount_total', 'margin_percent', 'profit_total'] as $column) {
    check(in_array($column, $columns, true), "columna {$column}");
}
$item_columns = $db->columns($db->table('customer_quote_items'));
foreach (['supplier_code', 'barcode', 'unit_cost', 'discount_amount'] as $column) {
    check(in_array($column, $item_columns, true), "columna de línea {$column}");
}
$mapped = [];
foreach ($db->fetch_all('SELECT status, net_total FROM ' . $quotes . ' ORDER BY id') as $row) {
    $mapped[$row['status']] = (float) $row['net_total'];
}
check(isset($mapped['listed'], $mapped['draft'], $mapped['invoiced']), 'estados legado remapeados');
check($mapped['listed'] === 1500.0, 'neto copia el total legado');
check(!isset($mapped['sent']) && !isset($mapped['viewed']), 'sent y viewed ya no quedan');

$fresh = memory_db();
$runner = new Riverso_POS_Migration_Runner($fresh, riverso_pos_migrations());
$applied = $runner->migrate();
check($applied === ['001_customer_quotes_base', '002_sale_quote_fields'], 'runner aplica fase 001 y 002');
check($runner->migrate() === [], 'la migración es idempotente');

echo "== crud ==\n";
$repo = new Riverso_POS_Customer_Quote_Repository($fresh);
$saved = $repo->save([
    'customer_name' => '',
    'quote_type' => 'venta',
    'validity_days' => 10,
    'validity_terms' => 'Precios sujetos a stock.',
    'net_total' => 1,
    'lines' => [[
        'product_id' => 101,
        'sku' => 'B20TAD',
        'supplier_code' => '221',
        'barcode' => '7801111111111',
        'description' => 'Tornillo drywall rosca madera 6x1',
        'quantity' => 2,
        'unit_price' => 890,
        'unit_cost' => 510,
    ]],
]);
check(str_starts_with($saved['quote_number'], 'COT-' . gmdate('Y') . '-'), 'número de cotización');
check($saved['status'] === 'draft' && $saved['status_label'] === 'Borrador', 'nace en borrador');
check($saved['customer_name'] === '', 'cliente opcional');
check($saved['net_total'] === 1780.0, 'el servidor recalcula el neto');
check($saved['margin_percent'] === 42.7, 'margen de cabecera');
check($saved['lines'][0]['unit_price'] === 890.0, 'guarda el precio de línea');

$edited = $repo->save([
    'id' => $saved['id'],
    'customer_name' => 'Ana Pérez',
    'quote_type' => 'referencia',
    'validity_days' => 10,
    'lines' => [[
        'sku' => 'B20TAD',
        'description' => 'Tornillo drywall rosca madera 6x1',
        'quantity' => 3,
        'unit_price' => 1000,
        'unit_cost' => 510,
        'supplier_code' => '221',
        'barcode' => '7801111111111',
    ]],
]);
check($edited['quote_number'] === $saved['quote_number'], 'el número no cambia al editar');
check($edited['quote_type_label'] === 'Referencia', 'tipo referencia');
check($edited['net_total'] === 3000.0 && $edited['lines'][0]['quantity'] === 3.0, 'edita cantidad y precio');
check($edited['customer_name'] === 'Ana Pérez', 'guarda el cliente');

$listed = $repo->transition((int) $edited['id'], 'listed');
check($listed['status_label'] === 'Lista', 'pasa a lista');
$draft_again = $repo->transition((int) $edited['id'], 'draft');
check($draft_again['status'] === 'draft', 'vuelve a borrador');

$second = $repo->save([
    'customer_name' => 'Local',
    'quote_type' => 'venta',
    'lines' => [],
]);
check($second['quote_number'] !== $saved['quote_number'], 'correlativo siguiente');
$list = $repo->list_quotes();
check(count($list) === 2, 'la lista muestra las cotizaciones');
$by_number = [];
foreach ($list as $row) {
    $by_number[$row['quote_number']] = $row;
}
check($by_number[$saved['quote_number']]['line_count'] === 1, 'la lista cuenta las líneas');
check($by_number[$saved['quote_number']]['status_label'] === 'Borrador', 'la lista muestra Borrador');
check($by_number[$second['quote_number']]['customer_name'] === 'Local', 'la lista muestra el cliente');

$threw = false;
try {
    $repo->transition((int) $edited['id'], 'invoiced');
} catch (Riverso_POS_Quote_Exception $error) {
    $threw = str_contains($error->getMessage(), 'Facturada');
}
check($threw, 'rechaza pasar a facturada');

$fresh->update($fresh->table('customer_quotes'), ['status' => 'invoiced'], 'id = ?', [(int) $second['id']]);
$blocked = false;
try {
    $repo->save([
        'id' => $second['id'],
        'lines' => [],
    ]);
} catch (Riverso_POS_Quote_Exception $error) {
    $blocked = str_contains($error->getMessage(), 'facturada');
}
check($blocked, 'no edita una facturada');

$bad_qty = false;
try {
    $repo->save(['lines' => [['sku' => 'B20TAD', 'quantity' => 0, 'unit_price' => 10]]]);
} catch (Riverso_POS_Quote_Exception) {
    $bad_qty = true;
}
check($bad_qty, 'cantidad cero no se guarda');

echo "== catálogo ==\n";
$lookup = catalog();
check(count($lookup->search('B20TAD')) === 1 && $lookup->search('b20tad')[0]['sku'] === 'B20TAD', 'busca por SKU');
check($lookup->search('445')[0]['supplier_code'] === '445', 'busca por código proveedor');
check($lookup->search('7803333333333')[0]['sku'] === '20ATHN', 'busca por código de barras');
check($lookup->search('') === [], 'búsqueda vacía');
check($lookup->search('NO-EXISTE') === [], 'sin resultados');
check(Riverso_POS_Woo_Catalog_Reader::meta_keys_for('sku') === ['_sku'], 'SKU WooCommerce');
check(in_array('_global_unique_id', Riverso_POS_Woo_Catalog_Reader::meta_keys_for('barcode'), true), 'barras WooCommerce');
check(in_array('_supplier_sku', Riverso_POS_Woo_Catalog_Reader::meta_keys_for('supplier_code'), true), 'código proveedor WooCommerce');

echo "\n";
if ($failures > 0) {
    fwrite(STDERR, "{$failures} pruebas fallaron\n");
    exit(1);
}
echo "Todas las pruebas pasaron\n";
