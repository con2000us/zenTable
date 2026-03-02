<?php
/**
 * ZenTable ASCII 校準截圖上傳
 *
 * 接受 POST multipart/form-data 圖片，呼叫 calibrate_analyze.py，
 * 回傳 { success, calibration, short_url }
 */

// Debug: 確保輸出緩衝區正確
ob_implicit_flush(true);
ob_end_flush();

header('Content-Type: application/json; charset=UTF-8');
error_log("=== calibrate_upload.php START ===");
const DEBUG_OUTPUT_MAX = 30000;

/**
 * 從混合輸出中擷取第一個完整 JSON 物件字串。
 */
function extract_first_json_object(string $text): ?string
{
    $len = strlen($text);
    $start = -1;
    $depth = 0;
    $inString = false;
    $escaped = false;

    for ($i = 0; $i < $len; $i++) {
        $ch = $text[$i];

        if ($start < 0) {
            if ($ch === '{') {
                $start = $i;
                $depth = 1;
            }
            continue;
        }

        if ($inString) {
            if ($escaped) {
                $escaped = false;
                continue;
            }
            if ($ch === '\\') {
                $escaped = true;
                continue;
            }
            if ($ch === '"') {
                $inString = false;
            }
            continue;
        }

        if ($ch === '"') {
            $inString = true;
            continue;
        }
        if ($ch === '{') {
            $depth++;
            continue;
        }
        if ($ch === '}') {
            $depth--;
            if ($depth === 0) {
                return substr($text, $start, $i - $start + 1);
            }
        }
    }

    return null;
}

/**
 * 以 Unicode 字素切分字串（含旗幟/ZWJ 組合）。
 */
function split_graphemes(string $text): array
{
    if ($text === '') return [];
    if (preg_match_all('/\X/u', $text, $m)) return $m[0];
    $arr = preg_split('//u', $text, -1, PREG_SPLIT_NO_EMPTY);
    return is_array($arr) ? $arr : [];
}

/**
 * 將字素轉為 U+ key（多碼點以空白分隔）。
 */
function grapheme_to_uplus_key(string $g): string
{
    $chars = preg_split('//u', $g, -1, PREG_SPLIT_NO_EMPTY);
    if (!is_array($chars) || count($chars) === 0) return '';
    $parts = [];
    foreach ($chars as $ch) {
        $code = mb_ord($ch, 'UTF-8');
        if ($code === false) continue;
        $parts[] = 'U+' . strtoupper(str_pad(dechex($code), 4, '0', STR_PAD_LEFT));
    }
    return implode(' ', $parts);
}

$uploadDir = __DIR__ . '/uploads/';
$dataDir = '/var/www/html/zenTable/calibrate_data/';
$scriptPath = __DIR__ . '/calibrate_analyze.py';

$scheme = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on') ? 'https' : 'http';
$host = $_SERVER['HTTP_HOST'] ?? 'localhost';
$scriptDir = dirname($_SERVER['SCRIPT_NAME'] ?? '/zenTable/');
$baseUrl = rtrim($scheme . '://' . $host . $scriptDir, '/');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode(['success' => false, 'error' => '僅支援 POST']);
    exit;
}

$customChars = isset($_POST['custom_chars']) ? trim((string) $_POST['custom_chars']) : '';
$ocrBackend = isset($_POST['ocr']) ? trim((string) $_POST['ocr']) : '';
$pixelPattern = isset($_POST['pixel_pattern']) ? trim((string) $_POST['pixel_pattern']) : '';
$repeatCount = isset($_POST['repeat_count']) ? (int) $_POST['repeat_count'] : 5;
if ($repeatCount < 3) $repeatCount = 3;
if ($repeatCount > 20) $repeatCount = 20;

if (!isset($_FILES['image'])) {
    echo json_encode(['success' => false, 'error' => '請上傳圖片 (multipart/form-data, field: image)']);
    exit;
}
$err = $_FILES['image']['error'];
if ($err !== UPLOAD_ERR_OK) {
    $errMsg = [
        UPLOAD_ERR_INI_SIZE => '檔案超過 php.ini 限制',
        UPLOAD_ERR_FORM_SIZE => '檔案超過表單限制',
        UPLOAD_ERR_PARTIAL => '僅部分上傳',
        UPLOAD_ERR_NO_FILE => '未選擇檔案',
        UPLOAD_ERR_NO_TMP_DIR => '缺少暫存目錄',
        UPLOAD_ERR_CANT_WRITE => '無法寫入',
        UPLOAD_ERR_EXTENSION => '擴充套件阻止上傳',
    ];
    echo json_encode(['success' => false, 'error' => $errMsg[$err] ?? "上傳錯誤 ($err)"]);
    exit;
}

$tmpPath = $_FILES['image']['tmp_name'];
if (!is_uploaded_file($tmpPath)) {
    echo json_encode(['success' => false, 'error' => '無效的上傳檔案']);
    exit;
}
$ext = strtolower(pathinfo($_FILES['image']['name'], PATHINFO_EXTENSION)) ?: 'png';
if (!in_array($ext, ['png', 'jpg', 'jpeg', 'gif', 'webp'], true)) {
    $ext = 'png';
}

$timestamp = date('YmdHis');
$random = bin2hex(random_bytes(4));
$baseName = 'calibrate_' . $timestamp . '_' . $random . '.' . $ext;
$uploadDir = __DIR__ . '/uploads/';
if (!is_dir($uploadDir)) {
    @mkdir($uploadDir, 0777, true);
}
if (!is_dir($uploadDir) || !is_writable($uploadDir)) {
    $uploadDir = __DIR__ . '/';
}
$savePath = $uploadDir . $baseName;
if (!move_uploaded_file($tmpPath, $savePath)) {
    echo json_encode(['success' => false, 'error' => '儲存失敗（請確認 uploads/ 目錄存在且可寫入）']);
    exit;
}

if (!file_exists($scriptPath)) {
    unlink($savePath);
    echo json_encode(['success' => false, 'error' => 'calibrate_analyze.py 不存在']);
    exit;
}

$calId = $timestamp . '_' . $random;
$customArg = $customChars !== '' ? ' --custom-chars ' . escapeshellarg($customChars) : '';
$ocrArg = '';
if ($ocrBackend !== '' && in_array(strtolower($ocrBackend), ['tesseract', 'rapidocr', 'none'], true)) {
    $ocrArg = ' --ocr ' . escapeshellarg(strtolower($ocrBackend));
}
$patternArg = '';
if ($ocrBackend === 'none' && $pixelPattern !== '') {
    $patternArg = ' --pixel-pattern ' . escapeshellarg($pixelPattern);
}
$endPatternArg = '';
if ($ocrBackend === 'none' && isset($_POST['pixel_end_pattern']) && $_POST['pixel_end_pattern'] !== '') {
    $endPatternArg = ' --pixel-end-pattern ' . escapeshellarg(trim($_POST['pixel_end_pattern']));
}
$findStartPointArg = '';
$useStartpointPipelineArg = '';
$testCharsArg = '';
$testCharGroupsArg = '';
$testCharsCountArg = '';
$charsPerLineArg = '';
$repeatCountArg = ' --repeat-count ' . escapeshellarg((string)$repeatCount);
$debug_log = [];
$debug_log[] = "POST find_start_point: " . (isset($_POST['find_start_point']) ? $_POST['find_start_point'] : 'not set');
$debug_log[] = "POST pixel_pattern: " . (isset($_POST['pixel_pattern']) ? $_POST['pixel_pattern'] : 'not set');
$debug_log[] = "POST pixel_end_pattern: " . (isset($_POST['pixel_end_pattern']) ? $_POST['pixel_end_pattern'] : 'not set');
if (isset($_POST['find_start_point']) && $_POST['find_start_point'] === '1') {
    $findStartPointArg = ' --find-start-point';
    $debug_log[] = "findStartPointArg set to: " . $findStartPointArg;
    $debug_log[] = "repeatCountArg: " . $repeatCount;
}
if (
    isset($_POST['use_startpoint_pipeline']) &&
    $_POST['use_startpoint_pipeline'] === '1' &&
    $ocrBackend === 'none'
) {
    $useStartpointPipelineArg = ' --use-startpoint-pipeline';
    $debug_log[] = "useStartpointPipelineArg set to: " . $useStartpointPipelineArg;
}

// 測試字元相關參數在一般模式與找起點模式都可使用（pixel 校準需要）
if (isset($_POST['test_chars']) && $_POST['test_chars'] !== '') {
    $testCharsArg = ' --test-chars ' . escapeshellarg($_POST['test_chars']);
    $debug_log[] = "testCharsArg: " . $_POST['test_chars'];
}
if (isset($_POST['test_char_groups']) && $_POST['test_char_groups'] !== '') {
    $testCharGroupsArg = ' --test-char-groups ' . escapeshellarg($_POST['test_char_groups']);
    $debug_log[] = "testCharGroupsArg: " . $_POST['test_char_groups'];
}
if (isset($_POST['test_chars_count']) && $_POST['test_chars_count'] !== '') {
    $testCharsCountArg = ' --test-chars-count ' . escapeshellarg($_POST['test_chars_count']);
    $debug_log[] = "testCharsCountArg: " . $_POST['test_chars_count'];
}
if (isset($_POST['chars_per_line']) && $_POST['chars_per_line'] !== '') {
    $charsPerLineArg = ' --chars-per-line ' . escapeshellarg($_POST['chars_per_line']);
    $debug_log[] = "charsPerLineArg: " . $_POST['chars_per_line'];
}
$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = (file_exists($venvPython)) ? $venvPython : 'python3';
$command = escapeshellarg($pythonCmd) . ' ' . escapeshellarg($scriptPath) . ' ' . escapeshellarg($savePath) . $customArg . $ocrArg . $patternArg . $endPatternArg . $findStartPointArg . $useStartpointPipelineArg . $testCharsArg . $testCharGroupsArg . $testCharsCountArg . $charsPerLineArg . $repeatCountArg . ' 2>&1';
$output = shell_exec($command);

$result = null;
$debug_log[] = "Python output lines count: " . (isset($output) ? count(explode("\n", $output)) : 0);
$debug_log[] = "Python output (first 200): " . (isset($output) ? substr($output, 0, 200) : 'empty');
if ($output) {
    // 1) 先嘗試整段直接 decode（Python 若只輸出 JSON 會成功）
    $decoded = json_decode(trim($output), true);
    if (json_last_error() === JSON_ERROR_NONE && isset($decoded['success'])) {
        $result = $decoded;
        $debug_log[] = "Direct JSON decode: OK";
    } else {
        $debug_log[] = "Direct JSON decode: FAIL: " . json_last_error_msg();

        // 2) 從混合輸出中擷取第一個完整 JSON 物件
        $jsonChunk = extract_first_json_object($output);
        if ($jsonChunk !== null) {
            $decoded = json_decode($jsonChunk, true);
            if (json_last_error() === JSON_ERROR_NONE && isset($decoded['success'])) {
                $result = $decoded;
                $debug_log[] = "Extracted JSON decode: OK";
            } else {
                $debug_log[] = "Extracted JSON decode: FAIL: " . json_last_error_msg();
            }
        } else {
            $debug_log[] = "Extracted JSON decode: FAIL: no JSON object found";
        }
    }
}

// 如果是找起點模式，直接回傳結果
$debug_log[] = "findStartPointArg: '$findStartPointArg', result: " . ($result ? 'OK' : 'NULL');
if ($findStartPointArg !== '') {
    if ($result && isset($result['success']) && $result['success'] === true) {
        $response = [
            'success' => true,
            'start_point' => $result,
            'debug_output' => implode("\n", $debug_log) . "\n---OUTPUT---\n" . substr((string)$output, 0, DEBUG_OUTPUT_MAX),
        ];
        echo json_encode($response, JSON_UNESCAPED_UNICODE);
        exit;
    }

    // 找起點模式必須回傳明確失敗，避免誤落入一般 calibration 回傳格式
    $detailError = '';
    if (is_array($result) && isset($result['error'])) {
        $detailError = (string)$result['error'];
    }
    $detailLogs = '';
    if (is_array($result) && isset($result['debug_logs']) && is_array($result['debug_logs'])) {
        $detailLogs = implode("\n", $result['debug_logs']);
    }
    $response = [
        'success' => false,
        'error' => $detailError !== '' ? ('找起點失敗: ' . $detailError) : '找起點模式解析失敗',
        'start_point' => is_array($result) ? $result : null,
        'debug_output' => implode("\n", $debug_log)
            . ($detailLogs !== '' ? ("\n---DETAIL DEBUG LOGS---\n" . $detailLogs) : '')
            . "\n---OUTPUT---\n" . substr((string)$output, 0, DEBUG_OUTPUT_MAX),
    ];
    echo json_encode($response, JSON_UNESCAPED_UNICODE);
    exit;
}

// 打包流程模式：若 analyzer 回報失敗，不可回退到預設 calibration
if ($useStartpointPipelineArg !== '') {
    if (!$result || !isset($result['success']) || $result['success'] !== true || !isset($result['calibration'])) {
        $detailError = '';
        if (is_array($result) && isset($result['error'])) {
            $detailError = (string)$result['error'];
        }
        $response = [
            'success' => false,
            'error' => $detailError !== '' ? ('打包流程失敗: ' . $detailError) : '打包流程解析失敗',
            'debug_output' => implode("\n", $debug_log) . "\n---OUTPUT---\n" . substr((string)$output, 0, DEBUG_OUTPUT_MAX),
        ];
        if (is_array($result) && !empty($result['pixel_debug_logs'])) {
            $response['pixel_debug_logs'] = $result['pixel_debug_logs'];
        }
        if (is_array($result) && isset($result['calibration_steps_summary']) && (string)$result['calibration_steps_summary'] !== '') {
            $response['calibration_steps_summary'] = $result['calibration_steps_summary'];
        }
        echo json_encode($response, JSON_UNESCAPED_UNICODE);
        exit;
    }
}

if (!$result) {
    error_log("calibrate_upload: Python output: " . substr($output, 0, 500));
}

$calibrationSource = 'analyzed';
$calibrationMessage = 'calibration generated by analyzer';
if (!$result || !isset($result['calibration'])) {
    $calibrationSource = 'fallback_default';
    $calibrationMessage = 'analyzer did not return calibration; using default fallback values';
    $calibration = [
        'ascii' => 1.0,
        'cjk' => 2.0,
        'box' => 1.0,
        'half_space' => 1.0,
        'full_space' => 2.0,
    ];
    if ($customChars !== '') {
        $calibration['custom'] = [];
        foreach (split_graphemes($customChars) as $g) {
            if (trim($g) === '') continue;
            $k = grapheme_to_uplus_key($g);
            if ($k !== '') $calibration['custom'][$k] = 2.0;
        }
    }
} else {
    $calibration = $result['calibration'];
}

// 儲存 calibration 供 short_url 取得
if (!is_dir($dataDir)) {
    mkdir($dataDir, 0755, true);
}
file_put_contents($dataDir . $calId . '.json', json_encode($calibration, JSON_UNESCAPED_UNICODE));

$shortUrl = $baseUrl . '/calibrate_get.php?id=' . $calId;

$response = [
    'success' => true,
    'calibration' => $calibration,
    'calibration_source' => $calibrationSource,
    'calibration_message' => $calibrationMessage,
    'short_url' => $shortUrl,
    'debug_output' => $output ? substr((string)$output, 0, DEBUG_OUTPUT_MAX) : '',
];
if ($result) {
    if (isset($result['pixel_per_unit'])) $response['pixel_per_unit'] = $result['pixel_per_unit'];
    if (!empty($result['ocr_lines'])) $response['ocr_lines'] = $result['ocr_lines'];
    if (!empty($result['char_measurements'])) $response['char_measurements'] = $result['char_measurements'];
    if (!empty($result['pixel_debug_logs'])) $response['pixel_debug_logs'] = $result['pixel_debug_logs'];
    if (isset($result['calibration_steps_summary']) && (string)$result['calibration_steps_summary'] !== '') {
        $response['calibration_steps_summary'] = $result['calibration_steps_summary'];
    }
}
echo json_encode($response, JSON_UNESCAPED_UNICODE);
