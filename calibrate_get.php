<?php
/**
 * ZenTable ASCII 校準資料取得
 *
 * ?id=xxx 回傳 calibration JSON，供 Skill fetch（方案 A 備援）
 */

header('Content-Type: application/json; charset=UTF-8');

$dataDir = '/var/www/html/zenTable/calibrate_data/';
$id = isset($_GET['id']) ? preg_replace('/[^a-zA-Z0-9_]/', '', $_GET['id']) : '';

if ($id === '') {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => '缺少 id 參數']);
    exit;
}

$path = $dataDir . $id . '.json';
if (!is_file($path)) {
    http_response_code(404);
    echo json_encode(['success' => false, 'error' => '校準資料不存在或已過期']);
    exit;
}

$calibration = json_decode(file_get_contents($path), true);
if (!is_array($calibration)) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => '資料格式錯誤']);
    exit;
}

echo json_encode($calibration, JSON_UNESCAPED_UNICODE);
