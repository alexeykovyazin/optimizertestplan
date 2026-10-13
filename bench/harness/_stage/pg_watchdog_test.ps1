$ErrorActionPreference = "Continue"
$env:PGPASSWORD = $env:BENCH_PG_PWD
$q = "SELECT pid, EXTRACT(EPOCH FROM now()-query_start)::int AS secs FROM pg_stat_activity WHERE datname='imdb' AND state='active' AND now()-query_start > interval '660 seconds'"
$rows = & C:\pgsql\bin\psql.exe -U postgres -d imdb -A -t -q -c $q
Write-Output "rows: [$rows]"
foreach ($r in $rows) {
    Write-Output "row=[$r] match=$($r -match '^(\d+)\|')"
    if ($r -match '^(\d+)\|') {
        $p = $Matches[1]
        Write-Output "would terminate $p"
    }
}
