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

$escaped = escapeshellarg($message);
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
    'confidence' => $result['confidence'] ?? 0
]);
