<?php
/**
 * ZenTable 主題匯出 API
 * 將 Theme JSON 與相關資源打包成 ZIP
 */

header('Content-Type: application/json');

$uploadDir = '/var/www/html/zenTable/';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => '僅支援 POST']);
    exit;
}

$themeName = preg_replace('/[^a-zA-Z0-9_-]/', '', $_POST['theme_name'] ?? 'custom_theme');
$mode = $_POST['mode'] ?? 'css';  // css, pil, text
$themeJson = $_POST['theme_json'] ?? '';
$themeData = null;

if (!empty($themeJson)) {
    $themeData = json_decode($themeJson, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        echo json_encode(['success' => false, 'error' => '無效的 JSON']);
        exit;
    }
}

// PIL/ASCII 可由前端組裝好 JSON 傳入，或僅傳 theme_json（CSS）
if (!$themeData && $mode !== 'css') {
    echo json_encode(['success' => false, 'error' => '缺少 theme_json']);
    exit;
}

if ($mode === 'css' && !$themeData) {
    echo json_encode(['success' => false, 'error' => '缺少 theme_json']);
    exit;
}

$timestamp = date('YmdHis');
$zipName = "theme_{$themeName}_{$timestamp}.zip";
$zipPath = $uploadDir . $zipName;

$zip = new ZipArchive();
if ($zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== TRUE) {
    echo json_encode(['success' => false, 'error' => '無法建立 ZIP 檔案']);
    exit;
}

// zip 內容：template.json 置於根目錄（符合 themes/{mode}/{theme_name}.zip 格式）
$zip->addFromString('template.json', json_encode($themeData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

$readme = "ZenTable Theme: $themeName ($mode)\nCreated: " . date('Y-m-d H:i:s') . "\n\nUsage:\n1. Save as themes/$mode/$themeName.zip (or use Import ZIP in index.html)\n2. Run: python3 scripts/zeble_render.py data.json out.png --theme-name $themeName";
$zip->addFromString('README.txt', $readme);

$zip->close();

if (file_exists($zipPath)) {
    echo json_encode([
        'success' => true,
        'url' => '/zenTable/' . $zipName,
        'filename' => $zipName
    ]);
} else {
    echo json_encode(['success' => false, 'error' => 'ZIP 生成失敗']);
}
