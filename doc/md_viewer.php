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

function collect_doc_files(string $root, bool $includeJson = false): array {
    $files = [];
    $it = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($root, FilesystemIterator::SKIP_DOTS)
    );
    foreach ($it as $f) {
        if (!$f->isFile()) continue;
        $name = $f->getFilename();
        $isMd = preg_match('/\.md$/i', $name);
        $isJson = $includeJson && preg_match('/\.json$/i', $name);
        if ($isMd || $isJson) {
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

function load_focus_list(string $focusFile): array {
    $focusSet = [];
    if (!file_exists($focusFile)) return $focusSet;
    $rawFocus = @file_get_contents($focusFile);
    $arr = json_decode($rawFocus ?: '[]', true);
    if (!is_array($arr)) return $focusSet;
    foreach ($arr as $f) {
        if (!is_string($f)) continue;
        $f = str_replace('\\', '/', trim($f));
        if ($f !== '') $focusSet[$f] = true;
    }
    return $focusSet;
}

function save_focus_list(string $focusFile, array $focusSet): bool {
    $list = array_keys($focusSet);
    sort($list, SORT_NATURAL | SORT_FLAG_CASE);
    $json = json_encode(array_values($list), JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
    if ($json === false) return false;
    return @file_put_contents($focusFile, $json . "\n") !== false;
}

$message = '';
$error = '';
$focusFile = $docRoot . DIRECTORY_SEPARATOR . 'md_focus.json';
$focusSet = load_focus_list($focusFile);

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';

    if ($action === 'focus_add' || $action === 'focus_remove') {
        $rel = str_replace('\\', '/', trim((string)($_POST['file'] ?? '')));
        $isValid = $rel !== '' && preg_match('/\.(md|json)$/i', $rel);
        if ($isValid) {
            if ($action === 'focus_add') $focusSet[$rel] = true;
            if ($action === 'focus_remove') unset($focusSet[$rel]);
            $ok = save_focus_list($focusFile, $focusSet);
            if (!$ok) $error = 'Focus update failed';
        } else {
            $error = 'Invalid file path';
        }

        if (isset($_POST['ajax']) && $_POST['ajax'] === '1') {
            header('Content-Type: application/json; charset=utf-8');
            echo json_encode([
                'ok' => $error === '',
                'error' => $error,
                'focus' => array_keys($focusSet),
            ], JSON_UNESCAPED_UNICODE);
            exit;
        }
    } else {
        $rel = $_POST['file'] ?? '';
        $content = $_POST['content'] ?? '';
        $abs = safe_abs_from_rel($rel, $docRoot);
        if ($abs === null || !preg_match('/\.(md|json)$/i', $rel)) {
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
}

$includeJson = isset($_GET['showJson']) && $_GET['showJson'] === '1';
$all = collect_doc_files($docRoot, $includeJson);
$list = array_map(fn($p) => rel_path($p, $docRoot), $all);

$current = $_GET['file'] ?? ($_POST['file'] ?? ($list[0] ?? ''));
$currentAbs = safe_abs_from_rel($current, $docRoot);
$currentContent = '';
if ($currentAbs && file_exists($currentAbs) && preg_match('/\.(md|json)$/i', $current)) {
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
    .file.focus { outline:1px solid #f6c453; background:#2c2a14; color:#ffe6a3; }
    #fileTree { font-size: 13px; }
    #fileTree .jstree-anchor { color:#c9d7f2; }
    #fileTree .focus-node > .jstree-anchor { color:#ffe6a3 !important; font-weight: 700; }
    #fileTree .active-node > .jstree-anchor { color:#ffffff !important; background:#243a74; border-radius:6px; }
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
    .focus-block { margin-bottom:10px; padding:8px; border:1px solid #2b3f77; border-radius:10px; background:#111d3b; }
    .focus-title { font-size:12px; font-weight:700; color:#d7e2ff; margin-bottom:6px; }
    .focus-list { display:flex; flex-direction:column; gap:6px; }
    .focus-item { display:flex; align-items:center; gap:6px; }
    .focus-link { flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .focus-remove { background:#3a2230; border:1px solid #6a324d; color:#ffb8c9; border-radius:6px; padding:2px 7px; font-size:11px; cursor:pointer; }
    .ctx-menu { position:fixed; display:none; z-index:9999; background:#111d3b; border:1px solid #2f4b8f; border-radius:8px; padding:4px; min-width:170px; box-shadow:0 8px 30px rgba(0,0,0,.35); }
    .ctx-menu button { width:100%; text-align:left; background:transparent; border:0; color:#d7e2ff; padding:8px 10px; border-radius:6px; font-size:12px; }
    .ctx-menu button:hover { background:#1f315f; }
    .empty { padding:16px; color:#9bb0de; }
  </style>
</head>
<body>
<div class="wrap">
  <aside class="sidebar">
    <h2>Docs Files (doc/)</h2>
    <div style="margin-bottom:8px;font-size:12px;">
      <?php if ($includeJson): ?>
        <a class="file" style="display:inline-block;padding:4px 8px;" href="?file=<?php echo urlencode($current); ?>">僅顯示 .md</a>
      <?php else: ?>
        <a class="file" style="display:inline-block;padding:4px 8px;" href="?showJson=1&file=<?php echo urlencode($current ?: 'md_focus.json'); ?>">顯示 .md + .json</a>
      <?php endif; ?>
    </div>
    <div class="focus-block">
      <div class="focus-title">Highlighted files</div>
      <div id="focusQuickList" class="focus-list"></div>
    </div>
    <?php if (!$list): ?>
      <div class="empty">No markdown/json files found.</div>
    <?php else: ?>
      <div id="fileTree"></div>
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
<div id="fileCtxMenu" class="ctx-menu"><button id="ctxAddHighlight" type="button">將此檔案高亮</button></div>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/jstree@3.3.17/dist/themes/default/style.min.css" />
<script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jstree@3.3.17/dist/jstree.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js"></script>
<script>
(function () {
  const fileList = <?php echo json_encode(array_values($list), JSON_UNESCAPED_UNICODE); ?>;
  const focusSet = <?php echo json_encode(array_keys($focusSet), JSON_UNESCAPED_UNICODE); ?>;
  const currentFile = <?php echo json_encode($current, JSON_UNESCAPED_UNICODE); ?>;
  const includeJson = <?php echo $includeJson ? 'true' : 'false'; ?>;
  const focusListEl = document.getElementById('focusQuickList');
  const ctxMenu = document.getElementById('fileCtxMenu');
  const ctxAddBtn = document.getElementById('ctxAddHighlight');
  let ctxTargetFile = null;
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
    const text = src || '';
    if (window.markdownit) {
      try {
        const md = window.markdownit({ html: false, linkify: true, breaks: true });
        return md.render(text);
      } catch (e) {}
    }
    // fallback (very basic)
    const esc = (s) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    return '<pre>' + esc(text) + '</pre>';
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

  const focusLookup = new Set(focusSet || []);

  const postFocusAction = async (action, file) => {
    const body = new URLSearchParams();
    body.set('action', action);
    body.set('file', file);
    body.set('ajax', '1');
    const res = await fetch(window.location.pathname + window.location.search, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
      body: body.toString(),
      credentials: 'same-origin'
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'focus update failed');
    focusLookup.clear();
    (data.focus || []).forEach((f) => focusLookup.add(f));
    renderFocusList();
    refreshTreeFocusStyles();
  };

  const renderFocusList = () => {
    if (!focusListEl) return;
    const items = Array.from(focusLookup).sort((a, b) => a.localeCompare(b, 'zh-Hant'));
    if (!items.length) {
      focusListEl.innerHTML = '<div style="font-size:12px;color:#9bb0de;">（目前沒有）</div>';
      return;
    }
    focusListEl.innerHTML = items.map((f) => {
      const href = '?file=' + encodeURIComponent(f) + (includeJson ? '&showJson=1' : '');
      return '<div class="focus-item">'
        + '<a class="file focus-link" href="' + href + '" title="' + escapeHtml(f) + '">' + escapeHtml(f) + '</a>'
        + '<button class="focus-remove" type="button" data-file="' + encodeURIComponent(f) + '">移除</button>'
        + '</div>';
    }).join('');
  };

  const refreshTreeFocusStyles = () => {
    if (!window.jQuery) return;
    const tree = window.jQuery('#fileTree').jstree(true);
    if (!tree) return;
    (fileList || []).forEach((f) => {
      const node = tree.get_node('file:' + f, true);
      if (!node || !node.length) return;
      node.removeClass('focus-node');
      if (focusLookup.has(f)) node.addClass('focus-node');
    });
  };

  renderFocusList();

  let mode = 'raw';
  try {
    const m = localStorage.getItem(modeKey);
    if (m === 'view' || m === 'raw') mode = m;
  } catch (e) {}
  setMode(mode);

  // left tree navigation (jstree)
  const treeEl = document.getElementById('fileTree');
  if (treeEl && window.jQuery && fileList.length) {
    const nodes = [];
    const dirSet = new Set(['#']);

    const ensureDir = (path) => {
      if (!path || dirSet.has(path)) return;
      const parts = path.split('/');
      let cur = '';
      for (const p of parts) {
        cur = cur ? (cur + '/' + p) : p;
        if (!dirSet.has(cur)) {
          const parent = cur.includes('/') ? cur.substring(0, cur.lastIndexOf('/')) : '#';
          nodes.push({ id: 'dir:' + cur, parent: parent === '#' ? '#' : ('dir:' + parent), text: p, icon: 'jstree-folder' });
          dirSet.add(cur);
        }
      }
    };

    fileList.forEach((f) => {
      const parentPath = f.includes('/') ? f.substring(0, f.lastIndexOf('/')) : '';
      ensureDir(parentPath);
      const parent = parentPath ? ('dir:' + parentPath) : '#';
      const name = f.includes('/') ? f.substring(f.lastIndexOf('/') + 1) : f;
      const classes = [];
      if (focusLookup.has(f)) classes.push('focus-node');
      if (f === currentFile) classes.push('active-node');
      nodes.push({ id: 'file:' + f, parent, text: name, icon: 'jstree-file', li_attr: { class: classes.join(' ') } });
    });

    window.jQuery(treeEl)
      .on('select_node.jstree', function (_e, data) {
        const id = String(data.node.id || '');
        if (!id.startsWith('file:')) return;
        const file = id.slice(5);
        const u = new URL(window.location.href);
        u.searchParams.set('file', file);
        if (includeJson) u.searchParams.set('showJson', '1');
        else u.searchParams.delete('showJson');
        window.location.href = u.toString();
      })
      .on('ready.jstree', function () {
        this.jstree(true).open_all();
      })
      .on('contextmenu', '.jstree-anchor', function (e) {
        const nodeEl = e.currentTarget.parentElement;
        const nodeId = nodeEl ? nodeEl.id : '';
        if (!nodeId || !nodeId.startsWith('file:')) return;
        e.preventDefault();
        ctxTargetFile = nodeId.slice(5);
        if (!ctxMenu) return;
        ctxMenu.style.left = e.clientX + 'px';
        ctxMenu.style.top = e.clientY + 'px';
        ctxMenu.style.display = 'block';
      })
      .jstree({
        core: { data: nodes, multiple: false, themes: { dots: true, icons: true } },
        plugins: ['wholerow']
      });
  }

  if (focusListEl) {
    focusListEl.addEventListener('click', async (e) => {
      const btn = e.target.closest('button.focus-remove');
      if (!btn) return;
      const f = decodeURIComponent(btn.getAttribute('data-file') || '');
      if (!f) return;
      try { await postFocusAction('focus_remove', f); } catch (err) { alert('移除高亮失敗：' + err.message); }
    });
  }

  if (ctxAddBtn) {
    ctxAddBtn.addEventListener('click', async () => {
      if (!ctxTargetFile) return;
      try { await postFocusAction('focus_add', ctxTargetFile); }
      catch (err) { alert('新增高亮失敗：' + err.message); }
      if (ctxMenu) ctxMenu.style.display = 'none';
      ctxTargetFile = null;
    });
  }

  document.addEventListener('click', () => {
    if (ctxMenu) ctxMenu.style.display = 'none';
    ctxTargetFile = null;
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && ctxMenu) {
      ctxMenu.style.display = 'none';
      ctxTargetFile = null;
    }
  });

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
