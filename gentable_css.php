<?php
header('Content-Type: application/json');
$uploadDir = __DIR__ . '/';
$scriptPath = __DIR__ . '/scripts/zeble_render.py';
$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = (file_exists($venvPython)) ? $venvPython : 'python3';
// doc/zeble_render.py 僅供參照，不參與執行
$jsonData = urldecode($_POST['data'] ?? '');
$theme = $_POST['theme'] ?? 'dark';
$themeJson = $_POST['theme_json'] ?? '';
$transparent = !empty($_POST['transparent']);  // 透空背景 PNG

// 若有 theme_json 則使用即時主題（含使用者編輯）；否則從 themes/ 載入

if (empty($jsonData)) { echo json_encode(['success' => false, 'error' => '缺少資料']); exit; }
$tableData = json_decode($jsonData, true);
if (json_last_error() !== JSON_ERROR_NONE) { echo json_encode(['success' => false, 'error' => 'JSON 錯誤']); exit; }

$timestamp = date('YmdHis');
$random = bin2hex(random_bytes(4));
$outputFile = "table_css_{$timestamp}_{$random}.png";
$outputPath = $uploadDir . $outputFile;
$inputFile = $uploadDir . 'input_css_' . $timestamp . '.json';
file_put_contents($inputFile, $jsonData);

$page = isset($_POST['page']) ? (int) $_POST['page'] : 0;
$perPage = isset($_POST['per_page']) ? max(1, min(100, (int) $_POST['per_page'])) : 15;
$sort = isset($_POST['sort']) ? trim((string) $_POST['sort']) : '';
$sortOrder = (!empty($_POST['desc']) && $_POST['desc'] !== '0' && $_POST['desc'] !== 'false') ? '--desc' : '--asc';

if (!file_exists($scriptPath)) {
    echo json_encode(['success' => false, 'error' => 'zeble_render.py 不存在於本專案 scripts 目錄', 'path' => $scriptPath]);
    exit;
}
$pythonScript = $scriptPath;
$themeArg = '';
$themeFile = null;
if (!empty($themeJson)) {
    $themeFile = $uploadDir . 'theme_css_' . $timestamp . '.json';
    if (file_put_contents($themeFile, $themeJson) !== false) {
        $themeArg = ' --theme ' . escapeshellarg($themeFile);
    } else {
        $themeFile = null;
    }
}
$command = "xvfb-run -a " . escapeshellarg($pythonCmd) . " " . escapeshellarg($pythonScript) . " " . escapeshellarg($inputFile) . " " . escapeshellarg($outputPath);
$command .= $themeArg ?: (" --theme-name " . escapeshellarg($theme));
if ($page > 0) $command .= " --page " . (int) $page;
if ($perPage !== 15) $command .= " --per-page " . (int) $perPage;
if ($sort !== '') $command .= " --sort " . escapeshellarg($sort) . " " . $sortOrder;
if ($transparent) {
    $command .= " --transparent";
}
$width = isset($_POST['width']) ? (int) $_POST['width'] : 0;
if ($width > 0) $command .= " --width " . $width;
$scale = isset($_POST['scale']) ? (float) $_POST['scale'] : 1.0;
if ($scale > 0 && $scale != 1.0) $command .= " --scale " . max(0.1, min(5.0, $scale));
$fillWidth = isset($_POST['fill_width']) ? trim((string) $_POST['fill_width']) : '';
if ($fillWidth && in_array($fillWidth, ['background', 'container', 'scale', 'no-shrink'])) $command .= " --fill-width " . escapeshellarg($fillWidth);
$bg = isset($_POST['bg']) ? trim((string) $_POST['bg']) : '';
if ($bg && !$transparent && preg_match('/^(transparent|theme|#[0-9A-Fa-f]{6})$/i', $bg)) $command .= " --bg " . escapeshellarg($bg);
$command .= " 2>&1";
$output = shell_exec($command);

if (file_exists($inputFile)) unlink($inputFile);
if ($themeFile && file_exists($themeFile)) @unlink($themeFile);
if (file_exists($outputPath)) {
    echo json_encode(['success' => true, 'image' => '/zenTable/' . $outputFile, 'mode' => 'css', 'theme' => $theme]);
} else {
    echo json_encode(['success' => false, 'error' => '生成失敗', 'debug' => $output, 'theme' => $theme]);
}
