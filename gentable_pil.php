<?php
/**
 * ZenTable PIL 渲染 API - 支援額外參數
 */

header('Content-Type: application/json');

$uploadDir = __DIR__ . '/';
$scriptPath = __DIR__ . '/scripts/zeble_render.py';
$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = (file_exists($venvPython)) ? $venvPython : 'python3';
// doc/zeble_render.py 僅供參照，不參與執行

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => '僅支援 POST']);
    exit;
}

$jsonData = urldecode($_POST['data'] ?? '');
$theme = $_POST['theme'] ?? 'default_dark';

if (empty($jsonData)) {
    echo json_encode(['success' => false, 'error' => '缺少資料']);
    exit;
}

$tableData = json_decode($jsonData, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    echo json_encode(['success' => false, 'error' => 'JSON 錯誤']);
    exit;
}

$timestamp = date('YmdHis');
$random = bin2hex(random_bytes(4));
$outputFile = "table_pil_{$timestamp}_{$random}.png";
$outputPath = $uploadDir . $outputFile;

// 寫入臨時輸入
$inputFile = $uploadDir . 'input_pil_' . $timestamp . '.json';

// 構建輸入數據（包含自定義參數）
$inputData = $tableData;
$inputData['_theme'] = $theme;

// 收集自定義參數
$customParams = [];
$paramWhitelist = [
    'bg_color', 'text_color', 'header_bg', 'header_text',
    'alt_row_color', 'border_color',
    'font_size', 'header_font_size', 'title_font_size', 'footer_font_size',
    'padding', 'cell_padding', 'row_height', 'header_height', 'title_height',
    'border_radius', 'border_width',
    'shadow_color', 'shadow_offset', 'shadow_blur', 'shadow_opacity',
    'title_padding', 'footer_padding', 'line_spacing',
    'cell_align', 'header_align',
    'font_family',
    'watermark_enabled', 'watermark_text', 'watermark_opacity'
];

foreach ($paramWhitelist as $param) {
    if (isset($_POST[$param])) {
        $value = $_POST[$param];
        // 處理數字類型
        if (in_array($param, ['font_size', 'header_font_size', 'title_font_size', 'footer_font_size',
                              'padding', 'cell_padding', 'row_height', 'header_height', 'title_height',
                              'border_radius', 'border_width', 'shadow_offset', 'shadow_blur'])) {
            $value = intval($value);
        } elseif (in_array($param, ['shadow_opacity', 'watermark_opacity', 'line_spacing'])) {
            $value = floatval($value);
        }
        $customParams[$param] = $value;
        $inputData[$param] = $value;
    }
}

file_put_contents($inputFile, json_encode($inputData, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));

// 分頁／排序（zeble_render.py --page, --per-page, --sort, --asc, --desc）
$page = isset($_POST['page']) ? (int) $_POST['page'] : 0;
$perPage = isset($_POST['per_page']) ? max(1, min(100, (int) $_POST['per_page'])) : 15;
$sort = isset($_POST['sort']) ? trim((string) $_POST['sort']) : '';
$sortOrder = (!empty($_POST['desc']) && $_POST['desc'] !== '0' && $_POST['desc'] !== 'false') ? '--desc' : '--asc';

if (!file_exists($scriptPath)) {
    echo json_encode(['success' => false, 'error' => 'zeble_render.py 不存在於本專案 scripts 目錄', 'path' => $scriptPath]);
    exit;
}
$pythonScript = $scriptPath;
$command = escapeshellarg($pythonCmd) . " " . escapeshellarg($pythonScript) . " " . escapeshellarg($inputFile) . " " . escapeshellarg($outputPath) . " --force-pil --theme-name " . escapeshellarg($theme);
if ($page > 0) $command .= " --page " . (int) $page;
if ($perPage !== 15) $command .= " --per-page " . (int) $perPage;
if ($sort !== '') $command .= " --sort " . escapeshellarg($sort) . " " . $sortOrder;
if (!empty($customParams)) {
    $paramsJson = json_encode($customParams);
    $command .= " --params " . escapeshellarg($paramsJson);
}
$width = isset($_POST['width']) ? (int) $_POST['width'] : 0;
if ($width > 0) $command .= " --width " . $width;
$scale = isset($_POST['scale']) ? (float) $_POST['scale'] : 1.0;
if ($scale > 0 && $scale != 1.0) $command .= " --scale " . max(0.1, min(5.0, $scale));
$command .= " 2>&1";

$output = shell_exec($command);

// 清理臨時檔案
if (file_exists($inputFile)) unlink($inputFile);

if (file_exists($outputPath)) {
    echo json_encode([
        'success' => true,
        'image' => '/zenTable/' . $outputFile,
        'mode' => 'pil',
        'params' => $customParams
    ]);
} else {
    echo json_encode(['success' => false, 'error' => '生成失敗', 'debug' => $output]);
}
