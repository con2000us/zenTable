<?php
/**
 * ZenTable ASCII 渲染 API
 */

header('Content-Type: application/json');

$uploadDir = __DIR__ . '/';
$scriptPath = __DIR__ . '/scripts/zentable_render.py';
$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = (file_exists($venvPython)) ? $venvPython : 'python3';
// doc/zentable_renderer.py 僅供參照，不參與執行

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => '僅支援 POST']);
    exit;
}

$jsonData = urldecode($_POST['data'] ?? '');
$theme = $_POST['theme'] ?? 'default';

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

// 寫入臨時輸入
$inputFile = $uploadDir . 'input_ascii_' . $timestamp . '.json';
file_put_contents($inputFile, $jsonData);

$page = isset($_POST['page']) ? (int) $_POST['page'] : 0;
$perPage = isset($_POST['per_page']) ? max(1, min(100, (int) $_POST['per_page'])) : 15;
$sort = isset($_POST['sort']) ? trim((string) $_POST['sort']) : '';
$sortOrder = (!empty($_POST['desc']) && $_POST['desc'] !== '0' && $_POST['desc'] !== 'false') ? '--desc' : '--asc';

// ASCII 即時參數（style, padding, align, header_align, 自訂框線字元）
$asciiParams = [];
if (isset($_POST['style'])) $asciiParams['style'] = trim((string) $_POST['style']);
if (isset($_POST['padding'])) $asciiParams['padding'] = (int) $_POST['padding'];
if (isset($_POST['align'])) $asciiParams['align'] = trim((string) $_POST['align']);
if (isset($_POST['header_align'])) $asciiParams['header_align'] = trim((string) $_POST['header_align']);
if (isset($_POST['border_mode'])) $asciiParams['border_mode'] = trim((string) $_POST['border_mode']);
if (isset($_POST['row_interval'])) $asciiParams['row_interval'] = max(1, min(20, (int) $_POST['row_interval']));
if (isset($_POST['col_interval'])) $asciiParams['col_interval'] = max(1, min(10, (int) $_POST['col_interval']));
if (isset($_POST['cell_pad_left'])) $asciiParams['cell_pad_left'] = max(0, min(8, (int) $_POST['cell_pad_left']));
if (isset($_POST['cell_pad_right'])) $asciiParams['cell_pad_right'] = max(0, min(8, (int) $_POST['cell_pad_right']));
if (isset($_POST['grid_config']) && $_POST['grid_config'] !== '') {
    $gc = trim((string) $_POST['grid_config']);
    if (json_decode($gc) !== null) $asciiParams['grid_config'] = $gc;
}
foreach (['tl','tr','bl','br','h','v','header','row','footer'] as $k) {
    if (isset($_POST['box_' . $k]) && $_POST['box_' . $k] !== '') {
        $asciiParams['box_' . $k] = mb_substr(trim((string) $_POST['box_' . $k]), 0, 1);
    }
}
$asciiDebug = !empty($_POST['ascii_debug']) && $_POST['ascii_debug'] !== '0' && $_POST['ascii_debug'] !== 'false';
if ($asciiDebug) {
    $asciiParams['ascii_debug'] = true;
}

// stage1 PIL 可視化（僅 ASCII debug）
if ($asciiDebug) {
    $stage1PilPreview = !empty($_POST['stage1_pil_preview']) && $_POST['stage1_pil_preview'] !== '0' && $_POST['stage1_pil_preview'] !== 'false';
    if ($stage1PilPreview) {
        $asciiParams['stage1_pil_preview'] = true;
        $unitPx = isset($_POST['stage1_unit_px']) ? (int) $_POST['stage1_unit_px'] : 10;
        $unitPx = max(5, min(30, $unitPx));
        $asciiParams['stage1_unit_px'] = $unitPx;
    }
}

$outputFile = $asciiDebug ? "table_ascii_debug_{$timestamp}_{$random}.json" : "table_ascii_{$timestamp}_{$random}.txt";
$outputPath = $uploadDir . $outputFile;

// 校準參數（可選）
$calibration = isset($_POST['calibration']) ? trim((string) $_POST['calibration']) : '';

if (!file_exists($scriptPath)) {
    echo json_encode(['success' => false, 'error' => 'zentable_renderer.py 不存在於本專案 scripts 目錄', 'path' => $scriptPath]);
    exit;
}
$pythonScript = $scriptPath;
$command = escapeshellarg($pythonCmd) . " " . escapeshellarg($pythonScript) . " " . escapeshellarg($inputFile) . " dummy.png --force-ascii --output-ascii " . escapeshellarg($outputPath) . " --theme-name " . escapeshellarg($theme);
if ($page > 0) $command .= " --page " . (int) $page;
if ($perPage !== 15) $command .= " --per-page " . (int) $perPage;
if ($sort !== '') $command .= " --sort " . escapeshellarg($sort) . " " . $sortOrder;
if (!empty($asciiParams)) $command .= " --params " . escapeshellarg(json_encode($asciiParams));
if ($calibration !== '') $command .= " --calibration " . escapeshellarg($calibration);
$command .= " 2>&1";

$output = shell_exec($command);

// 清理
if (file_exists($inputFile)) unlink($inputFile);

if (file_exists($outputPath)) {
    $content = file_get_contents($outputPath);
    if ($asciiDebug) {
        $parsed = json_decode($content, true);
        if (is_array($parsed)) {
            echo json_encode([
                'success' => true,
                'text' => $parsed['text'] ?? $content,
                'stage1' => $parsed['stage1'] ?? '',
                'stage2' => $parsed['stage2'] ?? '',
                'stage3_details' => $parsed['stage3_details'] ?? null,
                'stage1_pil_image' => $parsed['stage1_pil_image'] ?? null,
                'stage1_pil_warning' => $parsed['stage1_pil_warning'] ?? null,
                // keep /zenTable path for deployment compatibility
                'file' => '/zenTable/' . $outputFile,
                'mode' => 'ascii',
                'debug' => true
            ]);
        } else {
            echo json_encode(['success' => true, 'text' => $content, 'stage1' => '', 'stage2' => '', 'mode' => 'ascii', 'debug' => true]);
        }
    } else {
        echo json_encode([
            'success' => true,
            'text' => $content,
            // keep /zenTable path for deployment compatibility
            'file' => '/zenTable/' . $outputFile,
            'mode' => 'ascii'
        ]);
    }
} else {
    echo json_encode(['success' => false, 'error' => '生成失敗', 'debug' => $output]);
}
