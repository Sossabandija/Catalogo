<?php
/**
 * Cotizaciones de venta: CRUD AJAX y transición borrador ↔ lista.
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
        $seller = $this->current_seller();
        if (isset($config['sellerName']) && is_string($config['sellerName']) && trim($config['sellerName']) !== '') {
            $seller['name'] = trim($config['sellerName']);
        }
        if (array_key_exists('sellerId', $config)) {
            $seller_id = $config['sellerId'];
            $seller['id'] = $seller_id === null || $seller_id === '' ? null : (int) $seller_id;
        }
        unset($config['sellerName'], $config['sellerId']);
        $config['seller'] = $seller;
        $config['today'] = Riverso_POS_Quote_Expiry::today();
        $config['printUrl'] = $this->print_url();
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
        $filters = [];
        $status = $this->post_string('status');
        if ($status !== '' && $status !== 'all') {
            $filters['status'] = $status;
        }
        $type = $this->post_string('quote_type');
        if ($type !== '' && $type !== 'all') {
            $filters['quote_type'] = $type;
        }
        $from = $this->post_string('date_from');
        if ($from !== '') {
            $filters['date_from'] = $from;
        }
        $to = $this->post_string('date_to');
        if ($to !== '') {
            $filters['date_to'] = $to;
        }
        try {
            $quotes = $this->quotes->list_quotes($filters);
        } catch (Riverso_POS_Quote_Exception $error) {
            $this->fail($error->getMessage());
        }
        $this->ok(['quotes' => $quotes]);
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
        $data = $this->apply_seller($data);
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

    /**
     * @param array<string, mixed> $data
     * @return array<string, mixed>
     */
    private function apply_seller(array $data): array {
        $name = trim((string) ($data['seller_name'] ?? ''));
        if ($name !== '') {
            $data['seller_name'] = $name;
            return $data;
        }
        $seller = $this->current_seller();
        if ($seller['name'] === '') {
            return $data;
        }
        $data['seller_name'] = $seller['name'];
        if (!isset($data['seller_id']) || $data['seller_id'] === '' || $data['seller_id'] === null) {
            $data['seller_id'] = $seller['id'];
        }
        return $data;
    }

    /**
     * @return array{id: int|null, name: string}
     */
    private function current_seller(): array {
        if (!function_exists('wp_get_current_user')) {
            return ['id' => null, 'name' => ''];
        }
        $user = wp_get_current_user();
        if (!is_object($user)) {
            return ['id' => null, 'name' => ''];
        }
        $id = isset($user->ID) ? (int) $user->ID : 0;
        $name = '';
        if (isset($user->display_name) && is_string($user->display_name)) {
            $name = trim($user->display_name);
        }
        if ($name === '' && isset($user->user_login) && is_string($user->user_login)) {
            $name = trim($user->user_login);
        }
        return [
            'id' => $id > 0 ? $id : null,
            'name' => $name,
        ];
    }

    /**
     * Este corte no trae motor PDF. Si Riverso publica una URL de impresión, se usa.
     */
    private function print_url(): string {
        if (function_exists('riverso_pos_quote_print_url')) {
            $url = riverso_pos_quote_print_url();
            if (is_string($url)) {
                return $url;
            }
        }
        if (function_exists('apply_filters')) {
            $filtered = apply_filters('riverso_pos_quote_print_url', '');
            if (is_string($filtered)) {
                return $filtered;
            }
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
