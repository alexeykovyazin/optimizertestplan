# Watchdog PG-эталона: раз в 60 c ищет запросы datname=imdb старше 660 с
# (statement_timeout 300 c на параллельных COPY/EXPLAIN не срабатывает —
# лидер висит в BgworkerShutdown) и завершает их pg_terminate_backend.
# Лог: E:\pgdumps\watchdog.log. Работает до убийства процесса.
$ErrorActionPreference = "SilentlyContinue"
$env:PGPASSWORD = $env:BENCH_PG_PWD
$log = "E:\pgdumps\watchdog.log"
while ($true) {
    $rows = & C:\pgsql\bin\psql.exe -U postgres -d imdb -A -t -q -c "SELECT pid, EXTRACT(EPOCH FROM now()-query_start)::int FROM pg_stat_activity WHERE datname='imdb' AND state='active' AND now()-query_start > interval '660 seconds'" 2>$null
    foreach ($r in $rows) {
        if ($r -match "^(\d+)\|") {
            $pid2kill = $Matches[1]
            & C:\pgsql\bin\psql.exe -U postgres -d imdb -A -t -q -c "SELECT pg_terminate_backend($pid2kill)" 2>$null | Out-Null
            Add-Content $log "$(Get-Date -Format s) terminated $pid2kill"
        }
    }
    Start-Sleep -Seconds 60
}
