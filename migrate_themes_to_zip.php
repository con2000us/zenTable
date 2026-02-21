#!/usr/bin/env php
<?php
/**
 * Migration: 將 themes/{mode}/{theme_name}/template.json 轉為 themes/{mode}/{theme_name}.zip
 * 用法: php migrate_themes_to_zip.php [--delete]
 * --delete: 轉換後刪除原有資料夾（預設僅建立 zip，保留原資料夾）
 */

$themesDir = __DIR__ . '/themes/';
$deleteAfter = in_array('--delete', $argv ?? []);
$skipped = 0;
$converted = 0;

foreach (['css', 'pil', 'text'] as $mode) {
    $modeDir = $themesDir . $mode . '/';
    if (!is_dir($modeDir)) continue;
    foreach (scandir($modeDir) as $entry) {
        if ($entry === '.' || $entry === '..') continue;
        $themeDir = $modeDir . $entry;
        if (!is_dir($themeDir)) continue;
        $templatePath = $themeDir . '/template.json';
        if (!file_exists($templatePath)) continue;
        $zipPath = $modeDir . $entry . '.zip';
        if (file_exists($zipPath)) {
            echo "Skip (zip exists): $mode/$entry";
            if ($deleteAfter) {
                @unlink($templatePath);
                @rmdir($themeDir);
                echo " - deleted folder";
            }
            echo "\n";
            $skipped++;
            continue;
        }
        $content = file_get_contents($templatePath);
        $data = json_decode($content, true);
        if (json_last_error() !== JSON_ERROR_NONE || empty($data)) {
            echo "Skip (invalid JSON): $mode/$entry\n";
            $skipped++;
            continue;
        }
        $zip = new ZipArchive();
        if ($zip->open($zipPath, ZipArchive::CREATE | ZipArchive::OVERWRITE) !== true) {
            echo "Failed to create zip: $mode/$entry.zip\n";
            continue;
        }
        $zip->addFromString('template.json', json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        $zip->close();
        echo "Converted: $mode/$entry -> $mode/$entry.zip\n";
        $converted++;
        if ($deleteAfter) {
            @unlink($templatePath);
            @rmdir($themeDir);
            echo "  Deleted folder: $mode/$entry/\n";
        }
    }
}

echo "\nDone. Converted: $converted, Skipped: $skipped\n";
