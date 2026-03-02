<?php
/**
 * OCR 辨識能力測試 - 上傳截圖
 * 比對辨識順序與預期字元集，回傳信任分數。
 */
header('Content-Type: application/json; charset=UTF-8');

$uploadDir = __DIR__ . '/uploads/';
$scriptPath = __DIR__ . '/scripts/ocr_test_analyze.py';
$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = file_exists($venvPython) ? $venvPython : 'python3';

// 未安裝 OCR 測試分析器時，直接回傳明確錯誤（避免依賴 /opt skill 目錄）
if (!file_exists($scriptPath)) {
    echo json_encode([
        'success' => false,
        'error' => 'OCR 測試分析器未啟用（缺少 scripts/ocr_test_analyze.py）',
    ], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => '僅支援 POST']);
    exit;
}

if (!isset($_FILES['image'])) {
    echo json_encode(['success' => false, 'error' => '請上傳圖片']);
    exit;
}
if ($_FILES['image']['error'] !== UPLOAD_ERR_OK) {
    echo json_encode(['success' => false, 'error' => '上傳失敗']);
    exit;
}

$tmpPath = $_FILES['image']['tmp_name'];
$ext = strtolower(pathinfo($_FILES['image']['name'], PATHINFO_EXTENSION)) ?: 'png';
if (!in_array($ext, ['png', 'jpg', 'jpeg', 'gif', 'webp'], true)) $ext = 'png';

$timestamp = date('YmdHis');
$random = bin2hex(random_bytes(4));
$savePath = $uploadDir . 'ocr_test_' . $timestamp . '_' . $random . '.' . $ext;

if (!is_dir($uploadDir)) @mkdir($uploadDir, 0777, true);
if (!is_writable($uploadDir)) $uploadDir = __DIR__ . '/';
$savePath = $uploadDir . 'ocr_test_' . $timestamp . '_' . $random . '.' . $ext;

if (!move_uploaded_file($tmpPath, $savePath)) {
    echo json_encode(['success' => false, 'error' => '儲存失敗']);
    exit;
}

$anchor = isset($_POST['anchor']) ? trim((string) $_POST['anchor']) : '';
$ocr = isset($_POST['ocr']) ? trim((string) $_POST['ocr']) : '';

$args = [escapeshellarg($scriptPath), escapeshellarg($savePath)];
if ($anchor !== '') {
    $args[] = '--anchor';
    $args[] = escapeshellarg($anchor);
}
if ($ocr !== '') {
    $args[] = '--ocr';
    $args[] = escapeshellarg(strtolower($ocr));
}
$command = escapeshellarg($pythonCmd) . ' ' . implode(' ', $args) . ' 2>&1';
$output = shell_exec($command);
$decoded = $output ? json_decode(trim($output), true) : null;

// Debug: add ocr param to response
if ($decoded && !empty($decoded['success'])) {
    $decoded['_debug_ocr_param'] = $ocr;
    echo json_encode($decoded, JSON_UNESCAPED_UNICODE);
} else {
    echo json_encode([
        'success' => true,
        'found' => false,
        'error' => 'OCR 無法執行或辨識',
        '_debug_ocr_param' => $ocr,
    ], JSON_UNESCAPED_UNICODE);
}
