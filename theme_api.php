<?php
/**
 * ZenTable Theme API
 * 讀取 themes 目錄：支援 theme_name.zip（新格式）與 theme_name/template.json（過渡）
 */

header('Content-Type: application/json');

// 固定使用本專案 themes（避免依賴外部 /opt skill 目錄）
$themesDir = __DIR__ . '/themes/';

$action = $_GET['action'] ?? $_POST['action'] ?? 'list';
$mode = $_GET['mode'] ?? $_POST['mode'] ?? 'css';  // css, pil, text
$themeName = $_GET['theme'] ?? $_POST['theme_name'] ?? '';

/** 從 zip 內讀取 template.json（支援根目錄或 mode/theme_name/template.json） */
function readTemplateFromZip($zipPath, $mode = null, $themeName = null) {
    $zip = new ZipArchive();
    if ($zip->open($zipPath, ZipArchive::RDONLY) !== true) return null;
    $candidates = ['template.json'];
    if ($mode && $themeName) {
        $candidates[] = $mode . '/' . $themeName . '/template.json';
    }
    for ($i = 0; $i < $zip->numFiles; $i++) {
        $entry = $zip->getNameIndex($i);
        if (preg_match('#(^|/)template\.json$#', $entry)) {
            $content = $zip->getFromName($entry);
            $zip->close();
            $data = json_decode($content, true);
            return (json_last_error() === JSON_ERROR_NONE && !empty($data)) ? $data : null;
        }
    }
    foreach ($candidates as $c) {
        $content = $zip->getFromName($c);
        if ($content !== false) {
            $zip->close();
            $data = json_decode($content, true);
            return (json_last_error() === JSON_ERROR_NONE && !empty($data)) ? $data : null;
        }
    }
    $zip->close();
    return null;
}

function applyStyleCompat($data) {
    if (isset($data['styles']) && !isset($data['styles']['.header']) && isset($data['styles']['title'])) {
        $data['styles']['.header'] = $data['styles']['title'];
    }
    if (isset($data['styles']) && !isset($data['styles']['.cell-header']) && isset($data['styles']['th'])) {
        $data['styles']['.cell-header'] = $data['styles']['th'];
    }
    if (isset($data['styles']) && !isset($data['styles']['.cell']) && isset($data['styles']['td'])) {
        $data['styles']['.cell'] = $data['styles']['td'];
    }
    return $data;
}

function loadThemeTemplate($themesDir, $mode, $themeName) {
    $modeDir = $themesDir . $mode . '/';
    $zipPath = $modeDir . $themeName . '.zip';
    $templatePath = $modeDir . $themeName . '/template.json';
    if (file_exists($zipPath)) {
        $data = readTemplateFromZip($zipPath, $mode, $themeName);
        return $data ? applyStyleCompat($data) : null;
    }
    if (file_exists($templatePath)) {
        $content = file_get_contents($templatePath);
        $data = json_decode($content, true);
        if (json_last_error() !== JSON_ERROR_NONE || empty($data)) return null;
        return applyStyleCompat($data);
    }
    return null;
}

function listThemes($themesDir, $mode) {
    $modeDir = $themesDir . $mode . '/';
    $themes = [];
    if (!is_dir($modeDir)) return $themes;
    $seen = [];
    foreach (scandir($modeDir) as $entry) {
        if ($entry === '.' || $entry === '..') continue;
        $path = $modeDir . $entry;
        $id = null;
        $data = null;
        $sourceType = null;
        if (preg_match('/\.zip$/i', $entry)) {
            $id = preg_replace('/\.zip$/i', '', $entry);
            $data = readTemplateFromZip($path, $mode, $id);
            $sourceType = 'zip';
        } elseif (is_dir($path) && file_exists($path . '/template.json')) {
            $id = $entry;
            $content = file_get_contents($path . '/template.json');
            $data = json_decode($content, true);
            $sourceType = 'json';
        }
        if ($id && $data && isset($data['name']) && !isset($seen[$id])) {
            $seen[$id] = true;
            $themes[] = [
                'id' => $id,
                'name' => $data['name'],
                'description' => $data['description'] ?? '',
                'version' => $data['version'] ?? '1.0.0',
                'tags' => $data['tags'] ?? [],
                'theme_color' => getThemeColor($data),
                'source_type' => $sourceType ?: 'unknown',
            ];
        }
    }
    return $themes;
}

/** 從 template 取出主題色（供 Quick Theme 按鈕與圓點使用） */
function getThemeColor($data) {
    if (isset($data['theme_color']) && $data['theme_color'] !== '') {
        return trim($data['theme_color']);
    }
    $styles = $data['styles'] ?? [];
    $headerStyle = $styles['.header'] ?? $styles['.cell-header'] ?? $styles['title'] ?? $styles['th'] ?? '';
    if (preg_match('/color:\s*([^;]+)/', $headerStyle, $m)) {
        return trim($m[1]);
    }
    $params = $data['params'] ?? [];
    if (isset($params['header_text']) && $params['header_text'] !== '') {
        return trim($params['header_text']);
    }
    return '#e94560';
}

function convertCssTemplateToFrontend($template) {
    // Convert CSS template.json to frontend defaultThemes format
    $styles = $template['styles'] ?? [];
    
    // Parse body background
    $bodyStyle = $styles['body'] ?? '';
    preg_match('/background:\s*([^;]+)/', $bodyStyle, $matches);
    $bgColor = $matches[1] ?? '#1a1a2e';
    
    // Parse color
    preg_match('/color:\s*([^;]+)/', $bodyStyle, $matches);
    $textColor = $matches[1] ?? '#ffffff';
    
    // Parse header color
    $headerStyle = $styles['.header'] ?? '';
    preg_match('/color:\s*([^;]+)/', $headerStyle, $matches);
    $accentColor = $matches[1] ?? '#e94560';
    
    return [
        'name' => $template['name'] ?? 'Unknown',
        'bg' => trim($bgColor),
        'text' => trim($textColor),
        'accent' => trim($accentColor),
        'template' => $template
    ];
}

switch ($action) {
    case 'list':
        $themes = listThemes($themesDir, $mode);
        echo json_encode(['success' => true, 'themes' => $themes, 'mode' => $mode]);
        break;
        
    case 'load':
        if (empty($themeName)) {
            echo json_encode(['success' => false, 'error' => 'Missing theme parameter']);
            exit;
        }
        $template = loadThemeTemplate($themesDir, $mode, $themeName);
        if ($template) {
            // 如果是 CSS 模式，同時返回前端格式
            if ($mode === 'css') {
                $frontendFormat = convertCssTemplateToFrontend($template);
                echo json_encode([
                    'success' => true,
                    'template' => $template,
                    'frontend' => $frontendFormat,
                    'mode' => $mode
                ]);
            } else {
                echo json_encode(['success' => true, 'template' => $template, 'mode' => $mode]);
            }
        } else {
            echo json_encode(['success' => false, 'error' => 'Theme not found: ' . $themeName]);
        }
        break;
        
    case 'list-all-modes':
        $allThemes = [];
        foreach (['css', 'pil', 'text'] as $m) {
            $allThemes[$m] = listThemes($themesDir, $m);
        }
        echo json_encode(['success' => true, 'themes' => $allThemes]);
        break;
    
    case 'save':
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            echo json_encode(['success' => false, 'error' => 'POST only']);
            exit;
        }
        $themeJson = $_POST['theme_json'] ?? '';
        if (empty($themeName) || empty($themeJson)) {
            echo json_encode(['success' => false, 'error' => 'Missing theme_name or theme_json']);
            exit;
        }
        $themeName = preg_replace('/[^a-zA-Z0-9_-]/', '', $themeName);
        if (!in_array($mode, ['css', 'pil', 'text'])) {
            echo json_encode(['success' => false, 'error' => 'Invalid mode']);
            exit;
        }
        $modeDir = $themesDir . $mode . '/';
        $zipPath = $modeDir . $themeName . '.zip';
        $data = json_decode($themeJson, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            echo json_encode(['success' => false, 'error' => 'Invalid JSON']);
            exit;
        }
        if (!@is_dir($modeDir)) @mkdir($modeDir, 0755, true);
        $zip = new ZipArchive();
        if ($zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
            echo json_encode(['success' => false, 'error' => 'Could not create theme zip']);
            exit;
        }
        $zip->addFromString('template.json', json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        $zip->close();
        echo json_encode(['success' => true, 'path' => $mode . '/' . $themeName . '.zip']);
        break;

    case 'delete':
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            echo json_encode(['success' => false, 'error' => 'POST only']);
            exit;
        }
        $themeName = preg_replace('/[^a-zA-Z0-9_-]/', '', $_POST['theme'] ?? $_GET['theme'] ?? '');
        if (empty($themeName) || !in_array($mode, ['css', 'pil', 'text'])) {
            echo json_encode(['success' => false, 'error' => 'Missing theme or invalid mode']);
            exit;
        }
        $zipPath = $themesDir . $mode . '/' . $themeName . '.zip';
        $themeDir = $themesDir . $mode . '/' . $themeName . '/';
        $deleted = false;
        if (file_exists($zipPath) && @unlink($zipPath)) $deleted = true;
        if (is_dir($themeDir)) {
            foreach (glob($themeDir . '*') as $f) { if (is_file($f)) @unlink($f); }
            if (@rmdir($themeDir)) $deleted = true;
        }
        echo $deleted ? json_encode(['success' => true]) : json_encode(['success' => false, 'error' => 'Theme not found or could not delete']);
        break;

    case 'export-all':
        $zipName = 'themes_full_' . date('YmdHis') . '.zip';
        $zipPath = sys_get_temp_dir() . '/' . $zipName;
        $zip = new ZipArchive();
        if ($zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
            echo json_encode(['success' => false, 'error' => 'Could not create ZIP']);
            exit;
        }
        foreach (['css', 'pil', 'text'] as $m) {
            $modeDir = $themesDir . $m . '/';
            if (!is_dir($modeDir)) continue;
            foreach (scandir($modeDir) as $entry) {
                if ($entry === '.' || $entry === '..') continue;
                $fullPath = $modeDir . $entry;
                if (preg_match('/\.zip$/i', $entry)) {
                    $zip->addFile($fullPath, $m . '/' . $entry);
                } elseif (is_dir($fullPath) && file_exists($fullPath . '/template.json')) {
                    $themeZip = sys_get_temp_dir() . '/zt_' . uniqid() . '.zip';
                    $tz = new ZipArchive();
                    if ($tz->open($themeZip, ZipArchive::CREATE | ZipArchive::OVERWRITE) === true) {
                        $tz->addFile($fullPath . '/template.json', 'template.json');
                        $tz->close();
                        $zip->addFile($themeZip, $m . '/' . $entry . '.zip');
                        @unlink($themeZip);
                    }
                }
            }
        }
        $zip->close();
        if (file_exists($zipPath)) {
            header('Content-Type: application/zip');
            header('Content-Disposition: attachment; filename="' . $zipName . '"');
            header('Content-Length: ' . filesize($zipPath));
            readfile($zipPath);
            @unlink($zipPath);
            exit;
        }
        echo json_encode(['success' => false, 'error' => 'ZIP creation failed']);
        break;

    case 'import':
        if ($_SERVER['REQUEST_METHOD'] !== 'POST' || empty($_FILES['zip_file']['tmp_name'])) {
            echo json_encode(['success' => false, 'error' => 'POST with zip_file required']);
            exit;
        }
        $tmpZip = $_FILES['zip_file']['tmp_name'];
        $upFilename = $_FILES['zip_file']['name'] ?? '';
        $themeNameFromFile = preg_replace('/\.zip$/i', '', $upFilename);
        $themeNameFromFile = preg_replace('/[^a-zA-Z0-9_-]/', '', $themeNameFromFile) ?: 'imported_' . date('His');
        $modeParam = $_POST['mode'] ?? '';
        $data = readTemplateFromZip($tmpZip);
        if (!$data) {
            echo json_encode(['success' => false, 'error' => 'Invalid or empty theme zip (no valid template.json)']);
            exit;
        }
        $mode = in_array($modeParam, ['css', 'pil', 'text']) ? $modeParam : (isset($data['type']) && in_array($data['type'], ['css', 'pil', 'text']) ? $data['type'] : 'css');
        $themeName = preg_replace('/[^a-zA-Z0-9_-]/', '', $_POST['theme_name'] ?? $themeNameFromFile) ?: $themeNameFromFile;
        $modeDir = $themesDir . $mode . '/';
        if (!@is_dir($modeDir)) @mkdir($modeDir, 0755, true);
        $zipPath = $modeDir . $themeName . '.zip';
        $zip = new ZipArchive();
        if ($zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
            echo json_encode(['success' => false, 'error' => 'Could not write theme zip']);
            exit;
        }
        $zip->addFromString('template.json', json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        $zip->close();
        echo json_encode(['success' => true, 'imported' => 1, 'theme' => $themeName, 'mode' => $mode]);
        break;
        
    default:
        echo json_encode(['success' => false, 'error' => 'Unknown action']);
}
