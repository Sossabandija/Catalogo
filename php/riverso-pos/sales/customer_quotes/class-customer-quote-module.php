<?php
/**
 * Cotizaciones de venta: CRUD AJAX y transición borrador ↔ lista (P0+P1+P1b).
 */

declare(strict_types=1);

final class Riverso_POS_Customer_Quote_Module {
    public function __construct(
        private Riverso_POS_Customer_Quote_Repository $quotes,
        private Riverso_POS_Catalog_Product_Lookup $catalog,
        private bool $enforce_auth = true
    ) {
    }

    public function register(): void {
        if (!function_exists('add_action')) {
            return;
        }
        add_action('admin_menu', [$this, 'register_menu']);
        add_action('wp_ajax_riverso_cq_list', [$this, 'ajax_list']);
        add_action('wp_ajax_riverso_cq_get', [$this, 'ajax_get']);
        add_action('wp_ajax_riverso_cq_save', [$this, 'ajax_save']);
        add_action('wp_ajax_riverso_cq_transition', [$this, 'ajax_transition']);
        add_action('wp_ajax_riverso_cq_search', [$this, 'ajax_search']);
    }

    public function register_menu(): void {
        add_menu_page(
            'Cotizaciones',
            'Cotizaciones',
            $this->menu_capability(),
            'riverso-cotizaciones',
            [$this, 'render_page'],
            'dashicons-media-spreadsheet',
            56
        );
    }

    public function render_page(): void {
        if (!$this->user_can()) {
            if (function_exists('wp_die')) {
                wp_die(esc_html('No tienes permiso para ver cotizaciones.'));
            }
            $this->fail('No tienes permiso para ver cotizaciones.', 403);
        }
        $ajax = function_exists('admin_url') ? admin_url('admin-ajax.php') : '';
        $nonce = function_exists('wp_create_nonce') ? wp_create_nonce('riverso_customer_quotes') : '';
        $assets = function_exists('plugins_url') ? plugins_url('assets', RIVERSO_POS_FILE) : '';
        $this->render([
            'ajaxUrl' => $ajax,
            'nonce' => $nonce,
            'assetBase' => $assets,
            'standalone' => false,
        ]);
    }

    /**
     * @param array<string, mixed> $config
     */
    public function render(array $config): void {
        $name = isset($config['currentUserName']) && is_string($config['currentUserName'])
            ? trim($config['currentUserName'])
            : '';
        if ($name === '') {
            $name = $this->current_user_name();
        }
        $config['currentUserName'] = $name;
        $config['actions'] = [
            'list' => 'riverso_cq_list',
            'get' => 'riverso_cq_get',
            'save' => 'riverso_cq_save',
            'transition' => 'riverso_cq_transition',
            'search' => 'riverso_cq_search',
        ];
        $riverso_cq = $config;
        include RIVERSO_POS_DIR . '/templates/customer-quotes/app.php';
    }

    public function dispatch_ajax(): void {
        $action = $this->post_string('action');
        match ($action) {
            'riverso_cq_list' => $this->ajax_list(),
            'riverso_cq_get' => $this->ajax_get(),
            'riverso_cq_save' => $this->ajax_save(),
            'riverso_cq_transition' => $this->ajax_transition(),
            'riverso_cq_search' => $this->ajax_search(),
            default => $this->fail('Acción desconocida.', 404),
        };
    }

    public function ajax_list(): void {
        $this->authorize();
        $status = $this->post_string('status');
        $quote_type = $this->post_string('quote_type');
        $date_from = $this->post_string('date_from');
        $date_to = $this->post_string('date_to');
        $filters = [];
        if ($status !== '' && $status !== 'all') {
            $filters['status'] = $status;
        }
        if ($quote_type !== '' && $quote_type !== 'all') {
            $filters['quote_type'] = $quote_type;
        }
        if ($date_from !== '' && preg_match('/^\d{4}-\d{2}-\d{2}$/', $date_from)) {
            $filters['date_from'] = $date_from;
        }
        if ($date_to !== '' && preg_match('/^\d{4}-\d{2}-\d{2}$/', $date_to)) {
            $filters['date_to'] = $date_to;
        }
        try {
            $this->ok(['quotes' => $this->quotes->list_quotes($filters)]);
        } catch (Riverso_POS_Quote_Exception $error) {
            $this->fail($error->getMessage());
        }
    }

    public function ajax_get(): void {
        $this->authorize();
        $id = (int) $this->post_string('id');
        $quote = $this->quotes->find($id);
        if ($quote === null) {
            $this->fail('Cotización no encontrada.', 404);
        }
        $this->ok(['quote' => $quote]);
    }

    public function ajax_save(): void {
        $this->authorize();
        $raw = $this->post_string('payload');
        $data = json_decode($raw, true);
        if (!is_array($data)) {
            $this->fail('No se pudo leer la cotización.');
        }
        try {
            $quote = $this->quotes->save($data);
        } catch (Riverso_POS_Quote_Exception $error) {
            $this->fail($error->getMessage());
        }
        $this->ok([
            'quote' => $quote,
            'message' => 'Cotización ' . $quote['quote_number'] . ' guardada.',
        ]);
    }

    public function ajax_transition(): void {
        $this->authorize();
        try {
            $quote = $this->quotes->transition((int) $this->post_string('id'), $this->post_string('status'));
        } catch (Riverso_POS_Quote_Exception $error) {
            $this->fail($error->getMessage());
        }
        $this->ok([
            'quote' => $quote,
            'message' => 'Estado actualizado a ' . $quote['status_label'] . '.',
        ]);
    }

    public function ajax_search(): void {
        $this->authorize();
        $query = $this->post_string('q');
        $this->ok(['products' => $this->catalog->search($query, 20)]);
    }

    private function current_user_name(): string {
        if (!function_exists('wp_get_current_user')) {
            return '';
        }
        $user = wp_get_current_user();
        if (!is_object($user)) {
            return '';
        }
        if (!empty($user->display_name)) {
            return (string) $user->display_name;
        }
        if (!empty($user->user_login)) {
            return (string) $user->user_login;
        }
        return '';
    }

    private function authorize(): void {
        if (!$this->enforce_auth) {
            return;
        }
        if (!function_exists('current_user_can') || !function_exists('wp_verify_nonce')) {
            return;
        }
        $nonce = $this->post_string('nonce');
        if (!$this->user_can() || !wp_verify_nonce($nonce, 'riverso_customer_quotes')) {
            $this->fail('No tienes permiso para cotizar.', 403);
        }
    }

    private function user_can(): bool {
        if (!function_exists('current_user_can')) {
            return true;
        }
        return current_user_can('manage_woocommerce') || current_user_can('manage_options');
    }

    private function menu_capability(): string {
        if (function_exists('current_user_can') && current_user_can('manage_woocommerce')) {
            return 'manage_woocommerce';
        }
        return 'manage_options';
    }

    private function post_string(string $key): string {
        if (!isset($_POST[$key])) {
            return '';
        }
        $value = $_POST[$key];
        if (function_exists('wp_unslash')) {
            $value = wp_unslash($value);
        }
        if (!is_string($value)) {
            return '';
        }
        return function_exists('sanitize_text_field') && $key !== 'payload'
            ? sanitize_text_field($value)
            : $value;
    }

    /**
     * @param array<string, mixed> $data
     */
    private function ok(array $data): void {
        $this->send(true, $data, 200);
    }

    private function fail(string $message, int $status = 400): void {
        $this->send(false, ['message' => $message], $status);
    }

    /**
     * @param array<string, mixed> $data
     */
    private function send(bool $success, array $data, int $status): void {
        if (!headers_sent()) {
            http_response_code($status);
            header('Content-Type: application/json; charset=utf-8');
        }
        $payload = $success
            ? ['success' => true, 'data' => $data]
            : ['success' => false, 'data' => $data];
        echo json_encode($payload, JSON_UNESCAPED_UNICODE);
        exit;
    }
}
