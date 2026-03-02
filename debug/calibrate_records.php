<?php
header('Content-Type: application/json; charset=UTF-8');

$recordsDir = __DIR__ . '/calibrate_data/records/';
if (!is_dir($recordsDir)) {
    mkdir($recordsDir, 0755, true);
}

function sanitizeName($name) {
    return preg_replace('/[^a-zA-Z0-9_\-\x{4e00}-\x{9fff}]/u', '_', trim($name));
}

function getRecordPath($user, $platform) {
    global $recordsDir;
    return $recordsDir . sanitizeName($user) . '__' . sanitizeName($platform) . '.json';
}

$action = $_GET['action'] ?? '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    $action = $input['action'] ?? $action;

    switch ($action) {
        case 'save':
            $user = $input['user'] ?? '';
            $platform = $input['platform'] ?? '';
            $charWidths = $input['char_widths'] ?? [];
            if (!$user || !$platform) {
                echo json_encode(['success' => false, 'error' => '缺少 user 或 platform']);
                exit;
            }
            $path = getRecordPath($user, $platform);
            $existing = is_file($path) ? json_decode(file_get_contents($path), true) : [];
            $existingWidths = $existing['char_widths'] ?? [];
            $merged = array_merge($existingWidths, $charWidths);
            $record = [
                'user' => $user,
                'platform' => $platform,
                'char_widths' => $merged,
                'updated_at' => date('Y-m-d H:i:s'),
                'created_at' => $existing['created_at'] ?? date('Y-m-d H:i:s'),
            ];
            file_put_contents($path, json_encode($record, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
            echo json_encode(['success' => true, 'char_count' => count($merged)]);
            break;

        case 'delete':
            $user = $input['user'] ?? '';
            $platform = $input['platform'] ?? '';
            if (!$user || !$platform) {
                echo json_encode(['success' => false, 'error' => '缺少 user 或 platform']);
                exit;
            }
            $path = getRecordPath($user, $platform);
            if (is_file($path)) {
                unlink($path);
                echo json_encode(['success' => true]);
            } else {
                echo json_encode(['success' => false, 'error' => '紀錄不存在']);
            }
            break;

        default:
            echo json_encode(['success' => false, 'error' => 'Unknown POST action']);
            break;
    }
    exit;
}

switch ($action) {
    case 'load':
        $user = $_GET['user'] ?? '';
        $platform = $_GET['platform'] ?? '';
        if (!$user || !$platform) {
            echo json_encode(['success' => false, 'error' => '缺少 user 或 platform']);
            exit;
        }
        $path = getRecordPath($user, $platform);
        if (is_file($path)) {
            $record = json_decode(file_get_contents($path), true);
            echo json_encode(['success' => true, 'record' => $record]);
        } else {
            echo json_encode(['success' => false, 'error' => '無此紀錄']);
        }
        break;

    case 'list':
        $files = glob($recordsDir . '*.json');
        $records = [];
        foreach ($files as $f) {
            $data = json_decode(file_get_contents($f), true);
            if ($data) {
                $records[] = [
                    'user' => $data['user'] ?? '?',
                    'platform' => $data['platform'] ?? '?',
                    'char_count' => isset($data['char_widths']) ? count($data['char_widths']) : 0,
                    'updated_at' => $data['updated_at'] ?? '',
                ];
            }
        }
        echo json_encode(['success' => true, 'records' => $records]);
        break;

    default:
        echo json_encode(['success' => false, 'error' => 'Unknown action']);
        break;
}
