# Однократный проход watchdog'а PG-эталона (вызывается планировщиком каждую минуту).
# Терminate запросов datname=imdb старше 660 c: параллельные COPY/EXPLAIN ANALYZE
# висят в IPC/BgworkerShutdown, statement_timeout срабатывает с опозданием.
$ErrorActionPreference = "SilentlyContinue"
$env:PGPASSWORD = $env:BENCH_PG_PWD
$log = "E:\pgdumps\watchdog.log"
$rows = @(& C:\pgsql\bin\psql.exe -U postgres -d imdb -A -t -q -c "SELECT pid, EXTRACT(EPOCH FROM now()-query_start)::int FROM pg_stat_activity WHERE datname='imdb' AND state='active' AND now()-query_start > interval '660 seconds'" 2>$null)
Add-Content $log "$(Get-Date -Format s) check: $($rows.Count) over-660s"
foreach ($r in $rows) {
    if ($r -match "^(\d+)\|") {
        $p = $Matches[1]
        & C:\pgsql\bin\psql.exe -U postgres -d imdb -A -t -q -c "SELECT pg_terminate_backend($p)" 2>$null | Out-Null
        Add-Content $log "$(Get-Date -Format s) terminated $p"
    }
}
