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
    .bar { padding:10px 12px; border-bottom:1px solid #25314f; display:flex; gap:10px; align-items:center; background:#0f1830; flex-wrap:wrap; }
    .bar .title { font-weight:600; font-size:14px; }
    .msg { font-size:13px; color:#83f1b8; }
    .err { font-size:13px; color:#ff8b8b; }
    form { display:flex; flex:1; min-height:0; }
    textarea { flex:1; min-height:0; width:100%; border:0; outline:none; resize:none; padding:14px; font: var(--editor-font-size, 13px)/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background:#0b1020; color:#e6edf7; }
    .preview { flex:1; min-height:0; overflow:auto; padding:16px; background:#0b1020; color:#e6edf7; border:0; display:none; }
    .preview h1,.preview h2,.preview h3 { margin: 0.8em 0 0.4em; }
    .preview p { margin: 0.4em 0; }
    .preview code { background:#16213e; padding:2px 6px; border-radius:6px; }
    .preview pre { background:#16213e; padding:10px; border-radius:8px; overflow:auto; }
    .preview blockquote { border-left:3px solid #3b7cff; margin:8px 0; padding:2px 10px; color:#b9c7ea; }
    .mode-btn { background:#1d2b52; color:#cfe0ff; border:1px solid #2b3f77; border-radius:7px; padding:6px 10px; cursor:pointer; font-size:12px; }
    .mode-btn.active { background:#3b7cff; color:#fff; border-color:#3b7cff; }
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
      <button id="modeRaw" class="mode-btn active" type="button">Raw</button>
      <button id="modeView" class="mode-btn" type="button">View</button>
      <label for="fontSize" style="font-size:12px;color:#b9c7ea;">字體</label>
      <input id="fontSize" type="range" min="11" max="28" step="1" value="13" style="width:120px;" />
      <span id="fontSizeVal" style="font-size:12px;color:#b9c7ea;">13px</span>
      <div style="margin-left:auto"></div>
      <button form="editor" type="submit">Save</button>
      <?php endif; ?>
    </div>

    <?php if ($current): ?>
      <form id="editor" method="post">
        <input type="hidden" name="file" value="<?php echo htmlspecialchars($current, ENT_QUOTES, 'UTF-8'); ?>" />
        <textarea id="editorArea" name="content"><?php echo htmlspecialchars($currentContent, ENT_NOQUOTES, 'UTF-8'); ?></textarea>
        <div id="previewArea" class="preview"></div>
      </form>
    <?php else: ?>
      <div class="empty">No file available.</div>
    <?php endif; ?>
  </section>
</div>
<script>
(function () {
  const slider = document.getElementById('fontSize');
  const val = document.getElementById('fontSizeVal');
  const key = 'md_viewer_font_size_px';
  const modeKey = 'md_viewer_mode';
  const rawBtn = document.getElementById('modeRaw');
  const viewBtn = document.getElementById('modeView');
  const editor = document.getElementById('editorArea');
  const preview = document.getElementById('previewArea');
  if (!slider) return;

  const escapeHtml = (s) => s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const renderMd = (src) => {
    let t = escapeHtml(src || '');
    t = t.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    t = t.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
    t = t.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
    t = t.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');
    t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
    t = t.replace(/^>\s?(.+)$/gm, '<blockquote>$1</blockquote>');
    t = t.replace(/^(?:-\s.+(?:\n|$))+?/gm, (m) => {
      const items = m.trim().split(/\n/).map(x => x.replace(/^-\s/, '')).map(x => `<li>${x}</li>`).join('');
      return `<ul>${items}</ul>`;
    });
    t = t.replace(/\n{2,}/g, '</p><p>');
    if (!/^\s*<(h1|h2|h3|pre|ul|blockquote|p)/.test(t)) t = '<p>' + t + '</p>';
    t = t.replace(/<p>\s*<\/(h1|h2|h3|pre|ul|blockquote)>/g, '</$1>');
    t = t.replace(/<(h1|h2|h3|pre|ul|blockquote)>\s*<\/p>/g, '<$1>');
    return t;
  };

  const setMode = (mode) => {
    const isView = mode === 'view';
    if (editor) editor.style.display = isView ? 'none' : 'block';
    if (preview) {
      preview.style.display = isView ? 'block' : 'none';
      if (isView && editor) preview.innerHTML = renderMd(editor.value);
    }
    if (rawBtn) rawBtn.classList.toggle('active', !isView);
    if (viewBtn) viewBtn.classList.toggle('active', isView);
    try { localStorage.setItem(modeKey, isView ? 'view' : 'raw'); } catch (e) {}
  };

  const apply = (n) => {
    const px = Math.max(11, Math.min(28, parseInt(n || 13, 10)));
    document.documentElement.style.setProperty('--editor-font-size', px + 'px');
    slider.value = px;
    if (val) val.textContent = px + 'px';
    try { localStorage.setItem(key, String(px)); } catch (e) {}
  };

  let initial = 13;
  try {
    const saved = parseInt(localStorage.getItem(key) || '13', 10);
    if (!Number.isNaN(saved)) initial = saved;
  } catch (e) {}
  apply(initial);

  let mode = 'raw';
  try {
    const m = localStorage.getItem(modeKey);
    if (m === 'view' || m === 'raw') mode = m;
  } catch (e) {}
  setMode(mode);

  slider.addEventListener('input', (e) => apply(e.target.value));
  if (rawBtn) rawBtn.addEventListener('click', () => setMode('raw'));
  if (viewBtn) viewBtn.addEventListener('click', () => setMode('view'));
  if (editor) editor.addEventListener('input', () => {
    if (preview && preview.style.display !== 'none') preview.innerHTML = renderMd(editor.value);
  });
})();
</script>
</body>
</html>
