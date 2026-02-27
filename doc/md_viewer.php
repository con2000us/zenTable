<?php
// Simple Markdown Viewer/Editor for /doc
// - Scan and list markdown files under this directory
// - View/edit/save content

header('Content-Type: text/html; charset=utf-8');

$docRoot = realpath(__DIR__);
if ($docRoot === false) {
    http_response_code(500);
    echo 'doc root not found';
    exit;
}

function rel_path(string $abs, string $root): string {
    $r = str_replace('\\', '/', $root);
    $a = str_replace('\\', '/', $abs);
    if (strpos($a, $r) === 0) {
        $p = ltrim(substr($a, strlen($r)), '/');
        return $p;
    }
    return basename($abs);
}

function collect_md_files(string $root): array {
    $files = [];
    $it = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS)
    );
    foreach ($it as $f) {
        if (!$f->isFile()) continue;
        $name = $f->getFilename();
        if (preg_match('/\.md$/i', $name)) {
            $files[] = $f->getPathname();
        }
    }
    sort($files, SORT_NATURAL | SORT_FLAG_CASE);
    return $files;
}

function safe_abs_from_rel(string $rel, string $root): ?string {
    $rel = str_replace('\\', '/', $rel);
    $rel = ltrim($rel, '/');
    if ($rel === '' || strpos($rel, "..") !== false) return null;
    $abs = realpath($root . DIRECTORY_SEPARATOR . $rel);
    if ($abs === false) {
        // allow non-existing only if parent is in root (for save existing usage we still validate below)
        $candidate = $root . DIRECTORY_SEPARATOR . $rel;
        $parent = realpath(dirname($candidate));
        if ($parent === false) return null;
        if (strpos($parent, $root) !== 0) return null;
        return $candidate;
    }
    if (strpos($abs, $root) !== 0) return null;
    return $abs;
}

$message = '';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $rel = $_POST['file'] ?? '';
    $content = $_POST['content'] ?? '';
    $abs = safe_abs_from_rel($rel, $docRoot);
    if ($abs === null || !preg_match('/\.md$/i', $rel)) {
        $error = 'Invalid file path';
    } elseif (!file_exists($abs)) {
        $error = 'File does not exist';
    } else {
        $ok = @file_put_contents($abs, $content);
        if ($ok === false) {
            $error = 'Save failed';
        } else {
            $message = 'Saved: ' . htmlspecialchars($rel, ENT_QUOTES, 'UTF-8');
        }
    }
}

$all = collect_md_files($docRoot);
$list = array_map(fn($p) => rel_path($p, $docRoot), $all);

$current = $_GET['file'] ?? ($_POST['file'] ?? ($list[0] ?? ''));
$currentAbs = safe_abs_from_rel($current, $docRoot);
$currentContent = '';
if ($currentAbs && file_exists($currentAbs) && preg_match('/\.md$/i', $current)) {
    $currentContent = file_get_contents($currentAbs) ?: '';
} else {
    if ($current !== '') $error = $error ?: 'File not found';
    $current = $list[0] ?? '';
    $currentAbs = $current ? safe_abs_from_rel($current, $docRoot) : null;
    if ($currentAbs && file_exists($currentAbs)) {
        $currentContent = file_get_contents($currentAbs) ?: '';
    }
}
?>
<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Doc Markdown Viewer</title>
  <style>
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background:#0b1020; color:#e6edf7; }
    .wrap { display:grid; grid-template-columns: 320px 1fr; height:100vh; }
    .sidebar { border-right:1px solid #25314f; overflow:auto; padding:12px; background:#0f1830; }
    .sidebar h2 { margin:6px 0 10px; font-size:15px; }
    .file { display:block; color:#b9c7ea; text-decoration:none; padding:6px 8px; border-radius:8px; margin:2px 0; font-size:13px; }
    .file:hover { background:#1a2850; }
    .file.active { background:#243a74; color:#fff; }
    .main { display:flex; flex-direction:column; min-width:0; }
    .bar { padding:10px 12px; border-bottom:1px solid #25314f; display:flex; gap:10px; align-items:center; background:#0f1830; }
    .bar .title { font-weight:600; font-size:14px; }
    .msg { font-size:13px; color:#83f1b8; }
    .err { font-size:13px; color:#ff8b8b; }
    form { display:flex; flex:1; min-height:0; }
    textarea { flex:1; min-height:0; width:100%; border:0; outline:none; resize:none; padding:14px; font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:#0b1020; color:#e6edf7; }
    button { background:#3b7cff; color:#fff; border:0; border-radius:8px; padding:8px 12px; cursor:pointer; font-weight:600; }
    button:hover { filter:brightness(1.05); }
    .empty { padding:16px; color:#9bb0de; }
  </style>
</head>
<body>
<div class="wrap">
  <aside class="sidebar">
    <h2>Markdown Files (doc/)</h2>
    <?php if (!$list): ?>
      <div class="empty">No markdown files found.</div>
    <?php else: ?>
      <?php foreach ($list as $f): ?>
        <a class="file <?php echo $f === $current ? 'active' : ''; ?>" href="?file=<?php echo urlencode($f); ?>"><?php echo htmlspecialchars($f, ENT_QUOTES, 'UTF-8'); ?></a>
      <?php endforeach; ?>
    <?php endif; ?>
  </aside>

  <section class="main">
    <div class="bar">
      <div class="title"><?php echo $current ? htmlspecialchars($current, ENT_QUOTES, 'UTF-8') : 'No file selected'; ?></div>
      <?php if ($message): ?><div class="msg"><?php echo $message; ?></div><?php endif; ?>
      <?php if ($error): ?><div class="err"><?php echo htmlspecialchars($error, ENT_QUOTES, 'UTF-8'); ?></div><?php endif; ?>
      <?php if ($current): ?>
      <div style="margin-left:auto"></div>
      <button form="editor" type="submit">Save</button>
      <?php endif; ?>
    </div>

    <?php if ($current): ?>
      <form id="editor" method="post">
        <input type="hidden" name="file" value="<?php echo htmlspecialchars($current, ENT_QUOTES, 'UTF-8'); ?>" />
        <textarea name="content"><?php echo htmlspecialchars($currentContent, ENT_NOQUOTES, 'UTF-8'); ?></textarea>
      </form>
    <?php else: ?>
      <div class="empty">No file available.</div>
    <?php endif; ?>
  </section>
</div>
</body>
</html>
