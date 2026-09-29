<?php
/**
 * Plugin Name: Riverso POS
 * Description: Cotizaciones de venta del punto de venta Riverso. Este corte cubre borrador y lista.
 * Version: 0.1.0
 * Author: Riverso
 * Text Domain: riverso-pos
 * Requires at least: 6.0
 * Requires PHP: 8.0
 */

declare(strict_types=1);

if (!defined('ABSPATH') && !defined('RIVERSO_POS_DEV')) {
    exit;
}

define('RIVERSO_POS_VERSION', '0.1.0');
define('RIVERSO_POS_FILE', __FILE__);
define('RIVERSO_POS_DIR', __DIR__);

require_once __DIR__ . '/includes/load.php';

if (function_exists('register_activation_hook')) {
    register_activation_hook(__FILE__, 'riverso_pos_install');
}

if (function_exists('add_action')) {
    add_action('plugins_loaded', 'riverso_pos_boot');
}

function riverso_pos_install(): void {
    riverso_pos_migration_runner()->migrate();
    if (function_exists('update_option')) {
        update_option('riverso_pos_db_version', RIVERSO_POS_VERSION);
    }
}

function riverso_pos_boot(): void {
    $installed = function_exists('get_option') ? get_option('riverso_pos_db_version') : null;
    if ($installed !== RIVERSO_POS_VERSION) {
        riverso_pos_migration_runner()->migrate();
        if (function_exists('update_option')) {
            update_option('riverso_pos_db_version', RIVERSO_POS_VERSION);
        }
    }
    (new Riverso_POS_Customer_Quotes_Portal(riverso_pos_customer_quote_module()))->register();
}
