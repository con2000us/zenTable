<?php
/**
 * ZenTable ASCII 校準區塊輸出
 *
 * 產出校準用文字區塊，供使用者截圖後上傳分析。
 * 參數：custom_chars（可選），如 "字詞@" 指定需個別校準的字元
 */

header('Content-Type: text/plain; charset=UTF-8');

$customChars = isset($_GET['custom_chars']) ? trim((string) $_GET['custom_chars']) : '';
if ($customChars === '' && isset($_POST['custom_chars'])) {
    $customChars = trim((string) $_POST['custom_chars']);
}

$lines = [
    '[ZENT-BLE-MKR]',
    'R:██████████',
    'A:█0██1██a█',
    'C:█甲█',
    'B:█║██═██│█',
    'H:█ █',
    'F:口　口',
];

if ($customChars !== '') {
    $uParts = [];
    $len = mb_strlen($customChars);
    for ($i = 0; $i < $len; $i++) {
        $c = mb_substr($customChars, $i, 1);
        $uParts[] = '█' . $c . '█';
    }
    $lines[] = 'U:' . implode('', $uParts);
}

$lines[] = '[END]';

echo implode("\n", $lines);
