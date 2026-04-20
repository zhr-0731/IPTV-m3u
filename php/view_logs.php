<?php
/**
 * IPTV M3U 日志 API - 简单时间戳校验
 * 用法: view_logs.php?t=1745152222
 * 时间戳需在服务器时间 ±300 秒内
 */

date_default_timezone_set('Asia/Shanghai');

// 允许的时间偏差（秒）
define('TIME_WINDOW', 300);

// 日志目录
$logs_dir = __DIR__ . '/../logs';

// 校验时间戳
if (!isset($_GET['t']) || !ctype_digit($_GET['t'])) {
    http_response_code(403);
    die('Forbidden');
}

$client_time = (int)$_GET['t'];
$server_time = time();

if (abs($server_time - $client_time) > TIME_WINDOW) {
    http_response_code(403);
    die('Forbidden');
}

// 获取最新日志文件
function get_latest_log($dir) {
    $latest_file = null;
    $latest_mtime = 0;
    if (is_dir($dir)) {
        $items = scandir($dir);
        foreach ($items as $item) {
            if ($item === '.' || $item === '..') continue;
            $path = $dir . '/' . $item;
            if (is_file($path) && pathinfo($item, PATHINFO_EXTENSION) === 'log') {
                $mtime = filemtime($path);
                if ($mtime > $latest_mtime) {
                    $latest_mtime = $mtime;
                    $latest_file = $path;
                }
            }
        }
    }
    return $latest_file;
}

$latest_log = get_latest_log($logs_dir);

if ($latest_log && is_readable($latest_log)) {
    header('Content-Type: text/plain; charset=utf-8');
    readfile($latest_log);
} else {
    header('Content-Type: text/plain; charset=utf-8');
    echo 'No log file found.';
}
