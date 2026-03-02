<?php
/**
 * ZenTable Table Detect API
 * 呼叫 table_detect.py 分析文字是否需表格輸出
 */

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => 'POST only']);
    exit;
}

$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = (file_exists($venvPython)) ? $venvPython : 'python3';

$input = file_get_contents('php://input');
$body = json_decode($input, true);
$message = $body['message'] ?? $_POST['message'] ?? '';
$previousMessage = $body['previous_message'] ?? $_POST['previous_message'] ?? '';
$hasImage = $body['has_image'] ?? $_POST['has_image'] ?? false;
$previousHasImage = $body['previous_has_image'] ?? $_POST['previous_has_image'] ?? false;

// Fallback: infer image existence from array payloads.
if (!$hasImage && isset($body['images']) && is_array($body['images'])) {
    $hasImage = count($body['images']) > 0;
}
if (!$previousHasImage && isset($body['previous_images']) && is_array($body['previous_images'])) {
    $previousHasImage = count($body['previous_images']) > 0;
}

if ($message === '' && isset($_POST['message'])) {
    $message = $_POST['message'];
}

// 固定調用本專案 scripts（避免依賴外部 /opt skill 目錄）
$script = __DIR__ . '/scripts/table_detect.py';

if (!file_exists($script)) {
    echo json_encode([
        'success' => true,
        'needs_table' => false,
        'reason' => 'table_detect.py not found in project scripts/',
        'confidence' => 0
    ]);
    exit;
}

$payload = [
    'message' => $message,
    'previous_message' => $previousMessage,
    'has_image' => filter_var($hasImage, FILTER_VALIDATE_BOOLEAN),
    'previous_has_image' => filter_var($previousHasImage, FILTER_VALIDATE_BOOLEAN),
];
$payloadJson = json_encode($payload, JSON_UNESCAPED_UNICODE);
$escaped = escapeshellarg($payloadJson ?: json_encode(['message' => $message]));
$cmd = escapeshellarg($pythonCmd) . " " . escapeshellarg($script) . " " . $escaped . " 2>/dev/null";
$output = @shell_exec($cmd);

if ($output === null || $output === '') {
    echo json_encode([
        'success' => true,
        'needs_table' => false,
        'reason' => 'Script produced no output',
        'confidence' => 0
    ]);
    exit;
}

$result = @json_decode(trim($output), true);
if ($result === null) {
    echo json_encode([
        'success' => false,
        'error' => 'Invalid script output',
        'raw' => $output
    ]);
    exit;
}

echo json_encode([
    'success' => true,
    'needs_table' => $result['needs_table'] ?? false,
    'reason' => $result['reason'] ?? '',
    'confidence' => $result['confidence'] ?? 0,
    'zx_mode' => $result['zx_mode'] ?? false,
    'source_priority' => $result['source_priority'] ?? [],
    'selected_source' => $result['selected_source'] ?? '',
    'action' => $result['action'] ?? ''
]);
