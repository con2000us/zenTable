<?php
/**
 * OCR 辨識能力測試 - 產生字元集
 * 回傳 { success, chars }，字元集已存於 skill 本地。
 */
header('Content-Type: application/json; charset=UTF-8');

$chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz甲║═│ 口';
$dataPath = __DIR__ . '/ocr_test_chars.json';

$dir = dirname($dataPath);
if (is_dir($dir) && is_writable($dir)) {
    file_put_contents($dataPath, json_encode(['chars' => $chars], JSON_UNESCAPED_UNICODE));
}

echo json_encode(['success' => true, 'chars' => $chars], JSON_UNESCAPED_UNICODE);
