<?php
/**
 * ZenTable 圖片生成 API
 * 呼叫 zentable.py 將 JSON 資料轉為圖片
 */

header('Content-Type: application/json');

$uploadDir = __DIR__ . '/';
$workspaceZeble = __DIR__ . '/scripts/';
$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = (file_exists($venvPython)) ? $venvPython : 'python3';

// 檢查請求方法
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => '僅支援 POST 方法']);
    exit;
}

// 獲取資料
$jsonData = $_POST['data'] ?? '';
$theme = $_POST['theme'] ?? 'dark';

// 處理 URL 解碼
$jsonData = urldecode($jsonData);

if (empty($jsonData)) {
    echo json_encode(['success' => false, 'error' => '缺少資料參數']);
    exit;
}

// 驗證 JSON 格式
$tableData = json_decode($jsonData, true);
if (json_last_error() !== JSON_ERROR_NONE) {
    echo json_encode(['success' => false, 'error' => 'JSON 格式錯誤: ' . json_last_error_msg()]);
    exit;
}

// 生成唯一檔名
$timestamp = date('YmdHis');
$random = bin2hex(random_bytes(4));
$outputFile = "table_{$timestamp}_{$random}.png";
$outputPath = $uploadDir . $outputFile;

// 轉換資料為 zentable.py 所需的格式
$inputData = [
    'title' => $tableData['title'] ?? '',
    'headers' => $tableData['headers'] ?? [],
    'rows' => $tableData['rows'] ?? [],
    'theme' => $theme
];

// 寫入臨時輸入檔案
$inputFile = $uploadDir . 'input_' . $timestamp . '.json';
file_put_contents($inputFile, json_encode($inputData, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));

// 呼叫 zentable.py
$validThemes = ['dark', 'light', 'cyberpunk', 'forest', 'ocean', 'sunset', 'rose', 'midnight'];
$themeParam = in_array($theme, $validThemes) ? '--' . $theme : '--dark';
$command = sprintf(
    'cd %s && %s zentable.py %s %s %s',
    escapeshellarg($workspaceZeble),
    escapeshellarg($pythonCmd),
    escapeshellarg($inputFile),
    escapeshellarg($outputPath),
    escapeshellarg($themeParam)
);

// 執行並記錄輸出
$output = shell_exec($command . ' 2>&1');

// 除錯：寫入日誌
$debugLog = sprintf(
    "[%s]\nCommand: %s\nJSON Input: %s\nOutput: %s\n\n",
    date('Y-m-d H:i:s'),
    $command,
    substr($jsonData, 0, 500),
    $output
);
file_put_contents('/tmp/zentable_debug.log', $debugLog, FILE_APPEND);

// 清理臨時檔案
if (file_exists($inputFile)) {
    unlink($inputFile);
}

// 檢查結果
if (file_exists($outputPath)) {
    // keep /zenTable path for deployment compatibility
    $imageUrl = '/zenTable/' . $outputFile;
    echo json_encode([
        'success' => true,
        'image' => $imageUrl,
        'message' => '表格生成成功'
    ]);
} else {
    echo json_encode([
        'success' => false,
        'error' => '圖片生成失敗',
        'debug' => $output
    ]);
}
