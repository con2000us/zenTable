<?php
header('Content-Type: application/json');

$venvPython = __DIR__ . '/venv/bin/python';
$pythonCmd = file_exists($venvPython) ? $venvPython : 'python3';
$projectRoot = __DIR__;

$action = $_POST['action'] ?? $_GET['action'] ?? '';

switch ($action) {
    case 'start':
        $port = intval($_POST['port'] ?? 8000);
        if ($port < 1024 || $port > 65535) $port = 8000;

        $pid = trim(shell_exec("lsof -ti tcp:$port 2>/dev/null") ?? '');
        if ($pid) {
            echo json_encode(['success' => false, 'error' => "Port $port already in use (PID: $pid)"]);
            exit;
        }

        $logFile = "$projectRoot/fastapi.log";
        $cmd = "cd " . escapeshellarg($projectRoot) . " && "
             . escapeshellarg($pythonCmd) . " -m uvicorn api.render_api:app"
             . " --host 0.0.0.0 --port $port"
             . " >> " . escapeshellarg($logFile) . " 2>&1 & echo $!";
        $newPid = trim(shell_exec($cmd) ?? '');
        if ($newPid && is_numeric($newPid)) {
            echo json_encode(['success' => true, 'pid' => (int)$newPid, 'port' => $port]);
        } else {
            echo json_encode(['success' => false, 'error' => 'Failed to start process']);
        }
        break;

    case 'stop':
        $port = intval($_POST['port'] ?? 8000);
        if ($port < 1024 || $port > 65535) $port = 8000;
        $pids = trim(shell_exec("lsof -ti tcp:$port 2>/dev/null") ?? '');
        if ($pids) {
            shell_exec("kill $pids 2>/dev/null");
            usleep(500000);
            $check = trim(shell_exec("lsof -ti tcp:$port 2>/dev/null") ?? '');
            if ($check) {
                shell_exec("kill -9 $check 2>/dev/null");
            }
            echo json_encode(['success' => true, 'message' => 'FastAPI stopped']);
        } else {
            echo json_encode(['success' => true, 'message' => 'No process found on port']);
        }
        break;

    case 'check_deps':
        $deps = ['fastapi', 'uvicorn', 'Pillow', 'numpy', 'pytesseract', 'rapidocr-onnxruntime'];
        $result = [];
        foreach ($deps as $dep) {
            $pipName = $dep;
            $importName = str_replace('-', '_', strtolower($dep));
            if ($dep === 'Pillow') $importName = 'PIL';
            $out = shell_exec(escapeshellarg($pythonCmd) . " -c \"import $importName; print(getattr($importName, '__version__', 'installed'))\" 2>&1");
            $out = trim($out ?? '');
            $installed = (strpos($out, 'Error') === false && strpos($out, 'No module') === false && $out !== '');
            $result[] = [
                'name' => $dep,
                'installed' => $installed,
                'version' => $installed ? $out : null
            ];
        }
        echo json_encode(['success' => true, 'deps' => $result]);
        break;

    default:
        echo json_encode(['success' => false, 'error' => 'Unknown action: ' . $action]);
        break;
}
