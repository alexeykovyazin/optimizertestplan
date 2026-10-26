# Сторож прогона HASH-корпуса на dellg15 (schtasks, каждые 3 минуты).
# Логика: (1) если измерено >= 239 — пометить завершение и отключить задачу;
# (2) если есть python-процесс hash_supervisor/hash_imdb_ab — всё здорово;
# (3) иначе запустить супервизор заново (он сам резюмится по CSV).
$Log = 'E:\results\hash_watchdog2.log'
$Csv = 'E:\results\hash_imdb_ab3.csv'
$Expected = 239
$Py = 'C:\Users\ak\AppData\Local\Programs\Python\Python313\python.exe'

function Log($m) {
    Add-Content -Path $Log -Value ("{0} {1}" -f (Get-Date -Format 'MM-dd HH:mm:ss'), $m)
}

try {
    $done = 0
    if (Test-Path $Csv) {
        Import-Csv $Csv | Where-Object { $_.kind -eq 'measured' } |
            ForEach-Object { $done++ }
    }
} catch {
    Log "csv read failed: $($_.Exception.Message) (продолжаем как есть)"
    $done = 0
}

if ($done -ge $Expected) {
    Log "RUN COMPLETE ($done/$Expected) - отключаю задачу hash_watchdog"
    schtasks /change /tn hash_watchdog2 /disable 2>$null | Out-Null
    exit
}

$procs = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'hash_supervisor|hash_imdb_ab' })

if ($procs.Count -gt 0) {
    Log "healthy: $done/$Expected, процессов: $($procs.Count)"
    exit
}

Log "RESTART: процесс раннера не найден, done=$done/$Expected - стартую супервизор"
$env:FB_CLIENT_DIR = 'C:\HQbird\Firebird50'
$p = Start-Process -FilePath $Py `
    -ArgumentList '-u', 'E:\fbdata\hash_supervisor.py', '--out', $Csv `
    -WorkingDirectory 'E:\fbdata' -WindowStyle Hidden `
    -RedirectStandardOutput 'E:\results\hash_run_watchdog.log' `
    -RedirectStandardError 'E:\results\hash_run_watchdog.err.log' `
    -PassThru
Log "supervisor запущен, pid=$($p.Id)"
