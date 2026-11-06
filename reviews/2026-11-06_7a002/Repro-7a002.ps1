<#
.SYNOPSIS
    Reproduces the slow plan of the CEB query 7a_002 on the IMDb database.

.DESCRIPTION
    THE PROBLEM
    -----------
    On the build of the branch v5.0-impr-opt-fix the CEB query 7a_002 runs
    about 40 seconds. The builds of run 4 and run 5 ran it in about 6 seconds.
    The result of the query is the same (COUNT = 7986).

    The cause is a too low estimate of two kinds of filters:

      1. The "numeric text" filter on MOVIE_INFO_IDX.INFO:
             (info = '' OR info SIMILAR TO '...') AND CAST(info AS DOUBLE PRECISION) <= ...
         The optimizer expects that about 1/3 of the rows match.
         In fact almost all rows match.

      2. The filter KT.KIND IN ('episode', 'movie').
         The optimizer expects 2 of 7 kinds, so 2/7 of the titles.
         In fact these 2 kinds have most of the titles.

    With these low estimates the join order that starts from MOVIE_INFO_IDX
    (alias MII1) looks cheap, and the optimizer selects it. The join order
    that starts from NAME (alias N) is about 5 times faster.

    WHAT THE SCRIPT DOES
    --------------------
      Step 1. Connects to the database and shows the server version.
      Step 2. For each filter, compares the optimizer estimate with the real
              number of rows.
      Step 3. Shows the join order that the optimizer selects for 7a_002.
      Step 4. Runs 7a_002 in two ways and compares the time:
                a) with the plan of the optimizer;
                b) with a forced plan (PLAN clause) that starts from NAME.
      At the end the script shows "PROBLEM REPRODUCED" or
      "PROBLEM NOT REPRODUCED".

    The script runs about 2-3 minutes.

    EXIT CODES
    ----------
      0 - the problem is not reproduced (the optimizer plan is fast);
      1 - the problem is reproduced (the optimizer plan is slow);
      2 - an error occurred (no connection, wrong database, timeout, ...).

    HOW TO CHANGE THE SCRIPT
    ------------------------
      - Another server, database or isql: change the values in the param()
        block below, or give them on the command line (see the examples).
      - Another filter to check in step 2: add an item to $FilterChecks.
      - Another forced plan for step 4: change $ForcedPlan.

    REQUIREMENTS
    ------------
      - Windows PowerShell 5.1 or PowerShell 7.
      - isql.exe of Firebird 5.
      - The IMDb database of the CEB test (tables TITLE, NAME, CAST_INFO, ...).
      - Step 2 needs a build that can show the estimated number of rows in
        the EXPLAIN plan (HQbird with ShowExplainCardinality). The script
        turns this on for its own connection. On other builds step 2 shows
        "no estimate" and the other steps still work.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Repro-7a002.ps1

    Runs the script with the default values (the bench server on dellg15).

.EXAMPLE
    .\Repro-7a002.ps1 -Server "localhost/3050" -Database "D:\data\imdb.fdb" -RunsPerQuery 1

    Runs the script against another server and database, each query only once.
#>

param(
    # Full path to isql.exe.
    [string] $IsqlPath = "E:\fb50-impropt\isql.exe",

    # Server and port in the Firebird format "host/port".
    [string] $Server = "localhost/3056",

    # Path to the database file on the server.
    [string] $Database = "E:\fbdata\impropt_work\imdb_fb5.fdb",

    # User name and password for the connection.
    [string] $User = "SYSDBA",
    [string] $Password = "masterkey",

    # How many times to run each query in step 4. The script uses the fastest
    # run. The first run often reads the data from the disk, so it is slower.
    [int] $RunsPerQuery = 2,

    # Stop isql if one call runs longer than this number of seconds.
    [int] $TimeoutSeconds = 300,

    # The problem is "reproduced" when the optimizer plan is at least this
    # many times slower than the forced plan.
    [double] $SlowFactor = 2.0,

    # An estimate is "wrong" when the real number of rows is at least this
    # many times bigger (or smaller) than the estimate.
    [double] $BadEstimateFactor = 2.0
)

# Stop the script at the first error instead of continuing with bad data.
$ErrorActionPreference = "Stop"


# ===========================================================================
# QUERIES
# ===========================================================================

# The CEB query 7a_002. The text is the same as in the test, only split into
# lines. Do not change the order of the conditions: the order can change the
# plan that the optimizer selects.
#
# @' ... '@ is a "here-string" in single quotes: PowerShell does not change
# anything inside it, so the SQL text can have quotes and $ signs.
$Query7a002 = @'
SELECT COUNT(*)
FROM title AS t,
     movie_info AS mi1,
     kind_type AS kt,
     info_type AS it1,
     info_type AS it3,
     info_type AS it4,
     movie_info_idx AS mii1,
     movie_info_idx AS mii2,
     movie_keyword AS mk,
     keyword AS k,
     aka_name AS an,
     name AS n,
     info_type AS it5,
     person_info AS pi1,
     cast_info AS ci,
     role_type AS rt
WHERE t.id = mi1.movie_id
  AND t.id = ci.movie_id
  AND t.id = mii1.movie_id
  AND t.id = mii2.movie_id
  AND t.id = mk.movie_id
  AND mk.keyword_id = k.id
  AND mi1.info_type_id = it1.id
  AND mii1.info_type_id = it3.id
  AND mii2.info_type_id = it4.id
  AND t.kind_id = kt.id
  AND (kt.kind IN ('episode','movie'))
  AND (t.production_year <= 1990)
  AND (t.production_year >= 1950)
  AND (mi1.info IN ('30','60'))
  AND (it1.id IN ('1'))
  AND it3.id = '100'
  AND it4.id = '101'
  AND ((mii2.info = '' OR mii2.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND CAST(mii2.info AS DOUBLE PRECISION) <= 7.0)
  AND ((mii2.info = '' OR mii2.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND 3.0 <= CAST(mii2.info AS DOUBLE PRECISION))
  AND ((mii1.info = '' OR mii1.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND 0.0 <= CAST(mii1.info AS DOUBLE PRECISION))
  AND ((mii1.info = '' OR mii1.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND CAST(mii1.info AS DOUBLE PRECISION) <= 10000.0)
  AND n.id = ci.person_id
  AND ci.person_id = pi1.person_id
  AND it5.id = pi1.info_type_id
  AND n.id = pi1.person_id
  AND n.id = an.person_id
  AND rt.id = ci.role_id
  AND (n.gender IN ('f'))
  AND (n.name_pcode_nf IN ('A4253','A5242','B6165','J3261','K6235','M6252','S2525'))
  AND (ci.note IS NULL)
  AND (rt.role IN ('actress'))
  AND (it5.id IN ('25'))
'@

# The correct result of 7a_002 on the CEB IMDb database.
$ExpectedCount = 7986

# A forced plan for step 4. It is similar to the plan of run 4:
#   - start from NAME (N) and join AKA_NAME, PERSON_INFO, CAST_INFO, TITLE,
#     MOVIE_KEYWORD and the small tables by indexes (nested loop joins);
#   - then join MOVIE_INFO_IDX (MII2, MII1) and MOVIE_INFO (MI1) by hash joins.
# The index names are the names in the CEB IMDb database. If your database
# has other index names, change them here.
$ForcedPlan = @'
PLAN HASH (HASH (HASH (JOIN (N NATURAL,
                             AN INDEX (PERSON_ID_AKA_NAME),
                             PI1 INDEX (PERSON_ID_PERSON_INFO),
                             IT5 INDEX (INFO_TYPE_PK),
                             CI INDEX (PERSON_ID_CAST_INFO),
                             RT INDEX (ROLE_TYPE_PK),
                             T INDEX (TITLE_PK),
                             KT INDEX (KIND_TYPE_PK),
                             MK INDEX (MOVIE_ID_MOVIE_KEYWORD),
                             K INDEX (KEYWORD_PK),
                             IT1 INDEX (INFO_TYPE_PK),
                             IT3 INDEX (INFO_TYPE_PK),
                             IT4 INDEX (INFO_TYPE_PK)),
                       MII2 INDEX (INFO_TYPE_ID_MOVIE_INFO_IDX)),
                 MII1 INDEX (INFO_TYPE_ID_MOVIE_INFO_IDX)),
           MI1 INDEX (INFO_TYPE_ID_MOVIE_INFO))
'@

# The filters to check in step 2. Each item has:
#   Name - a short name for the report;
#   Sql  - a SELECT COUNT(*) query with this filter only (no ";" at the end).
# The script compares the estimate of the optimizer for this query with the
# real COUNT(*). To add a check, copy one item and change Name and Sql.
$FilterChecks = @(
    @{
        Name = "MII1: info_type_id = 100"
        Sql  = "SELECT COUNT(*) FROM movie_info_idx mii1 WHERE mii1.info_type_id = 100"
    },
    @{
        Name = "MII1: + numeric text 0..10000"
        Sql  = @'
SELECT COUNT(*) FROM movie_info_idx mii1
WHERE mii1.info_type_id = 100
  AND ((mii1.info = '' OR mii1.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND 0.0 <= CAST(mii1.info AS DOUBLE PRECISION))
  AND ((mii1.info = '' OR mii1.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND CAST(mii1.info AS DOUBLE PRECISION) <= 10000.0)
'@
    },
    @{
        Name = "MII2: info_type_id = 101"
        Sql  = "SELECT COUNT(*) FROM movie_info_idx mii2 WHERE mii2.info_type_id = 101"
    },
    @{
        Name = "MII2: + numeric text 3..7"
        Sql  = @'
SELECT COUNT(*) FROM movie_info_idx mii2
WHERE mii2.info_type_id = 101
  AND ((mii2.info = '' OR mii2.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND CAST(mii2.info AS DOUBLE PRECISION) <= 7.0)
  AND ((mii2.info = '' OR mii2.info SIMILAR TO '(0|[1-9][0-9]*)([.][0-9]+)?') AND 3.0 <= CAST(mii2.info AS DOUBLE PRECISION))
'@
    },
    @{
        Name = "T: production_year 1950..1990"
        Sql  = "SELECT COUNT(*) FROM title t WHERE t.production_year <= 1990 AND t.production_year >= 1950"
    },
    @{
        Name = "T x KT: + kind episode, movie"
        Sql  = @'
SELECT COUNT(*) FROM title t, kind_type kt
WHERE t.kind_id = kt.id
  AND kt.kind IN ('episode','movie')
  AND t.production_year <= 1990 AND t.production_year >= 1950
'@
    },
    @{
        Name = "N: gender f + 7 name codes"
        Sql  = "SELECT COUNT(*) FROM name n WHERE n.gender IN ('f') AND n.name_pcode_nf IN ('A4253','A5242','B6165','J3261','K6235','M6252','S2525')"
    }
)


# ===========================================================================
# HELPER FUNCTIONS
# ===========================================================================

function Write-Step {
    # Shows a header for a step, for example "Step 1. Connection".
    param([string] $Title)

    $line = "=" * 70
    Write-Host ""
    Write-Host $line -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host $line -ForegroundColor Cyan
}


function ConvertTo-Number {
    # Converts a number from the isql output to [double].
    # isql always writes numbers with a dot (7.853). A Russian Windows uses a
    # comma as the decimal separator, so we must use the "invariant" culture.
    param([string] $Text)

    return [double]::Parse($Text, [System.Globalization.CultureInfo]::InvariantCulture)
}


function Format-Number {
    # Formats a number for the report: 1234567.8 -> "1,234,568".
    param(
        [double] $Value,
        [int] $Decimals = 0
    )

    return $Value.ToString("N$Decimals", [System.Globalization.CultureInfo]::InvariantCulture)
}


function Invoke-Isql {
    # Runs SQL text with isql.exe and returns all isql output as one string.
    # Stops isql if it runs longer than $TimeoutSeconds.
    # Throws an error if isql reports an error.
    param([string] $SqlText)

    # isql reads the SQL from a file, so we write the text to a temporary file.
    # We write UTF-8 without BOM: isql does not expect a BOM at the start.
    $sqlFile = [System.IO.Path]::GetTempFileName()
    $outFile = $sqlFile + ".out"
    $errFile = $sqlFile + ".err"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($sqlFile, $SqlText, $utf8NoBom)

    # The isql command line:
    #   -b         stop at the first error and return a non-zero exit code;
    #   -ch UTF8   the character set of the connection;
    #   -i FILE    read the SQL from the file;
    #   the last argument is the connection string "host/port:database".
    $arguments = @(
        "-b",
        "-user", $User,
        "-password", $Password,
        "-ch", "UTF8",
        "-i", "`"$sqlFile`"",
        "`"$($Server):$Database`""
    )

    try {
        $process = Start-Process -FilePath $IsqlPath -ArgumentList $arguments `
            -NoNewWindow -PassThru `
            -RedirectStandardOutput $outFile -RedirectStandardError $errFile

        # Read the process handle now. Without this line Windows PowerShell 5.1
        # sometimes cannot give the exit code after the process ends.
        $null = $process.Handle

        $finished = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $finished) {
            # Note: this stops only isql. The server can continue the query
            # for some time.
            Stop-Process -Id $process.Id -Force
            throw "isql did not finish in $TimeoutSeconds seconds and was stopped. Use a bigger -TimeoutSeconds."
        }

        # isql writes the results to the standard output and the errors
        # (and some messages) to the error output. We join both.
        $output = [System.IO.File]::ReadAllText($outFile) + [System.IO.File]::ReadAllText($errFile)

        if ($process.ExitCode -ne 0) {
            throw "isql failed with exit code $($process.ExitCode):`n$output"
        }

        return $output
    }
    finally {
        # Always delete the temporary files, also after an error.
        Remove-Item -Path $sqlFile, $outFile, $errFile -ErrorAction SilentlyContinue
    }
}


function Get-EstimatedRows {
    # Returns the optimizer estimate of the number of rows for a
    # SELECT COUNT(*) query, or $null if the server does not show estimates.
    #
    # The query is only prepared (SET PLANONLY), not executed. With
    # SHOW_EXPLAIN_CARDINALITY the EXPLAIN plan has "(rows=N)" on each line:
    #     Select Expression
    #         -> Aggregate (rows=1.00)
    #             -> Filter (rows=148634.03)       <- this is the estimate we need
    #                 -> Table "MOVIE_INFO_IDX" ...
    # The first "rows=" is the aggregate (always 1). The second "rows=" is the
    # number of rows that go into COUNT(*).
    param([string] $SqlText)

    $header = @'
SET LIST ON;
SELECT RDB$SET_CONTEXT('USER_SESSION', 'SHOW_EXPLAIN_CARDINALITY', 'TRUE') FROM RDB$DATABASE;
SET PLANONLY ON;
SET EXPLAIN ON;
'@
    $output = Invoke-Isql -SqlText ($header + "`n" + $SqlText + ";")

    $found = [regex]::Matches($output, '\(rows=([0-9.eE+-]+)\)')
    if ($found.Count -lt 2) {
        return $null
    }
    return ConvertTo-Number $found[1].Groups[1].Value
}


function Measure-Query {
    # Runs a SELECT COUNT(*) query and returns an object with two values:
    #   Seconds - the elapsed time that isql shows (SET STATS ON);
    #   Count   - the result of COUNT(*).
    param([string] $SqlText)

    # SET LIST ON shows the result as "COUNT   7986" (name and value on one line).
    $output = Invoke-Isql -SqlText ("SET LIST ON;`nSET STATS ON;`n" + $SqlText + ";")

    $countMatch = [regex]::Match($output, 'COUNT\s+(\d+)')
    $timeMatch = [regex]::Match($output, 'Elapsed time\s*=\s*([0-9.]+)')
    if (-not $countMatch.Success -or -not $timeMatch.Success) {
        throw "Cannot find COUNT or 'Elapsed time' in the isql output:`n$output"
    }

    return [PSCustomObject]@{
        Seconds = ConvertTo-Number $timeMatch.Groups[1].Value
        Count   = [long] $countMatch.Groups[1].Value
    }
}


function Measure-QueryBest {
    # Runs a query $RunsPerQuery times, shows each run and returns the fastest run.
    param(
        [string] $Title,
        [string] $SqlText
    )

    Write-Host ""
    Write-Host $Title -ForegroundColor White
    $best = $null
    for ($run = 1; $run -le $RunsPerQuery; $run++) {
        $result = Measure-Query -SqlText $SqlText
        Write-Host ("  run {0}: {1} s, COUNT = {2}" -f $run, (Format-Number $result.Seconds 1), $result.Count)

        if ($result.Count -ne $ExpectedCount) {
            Write-Host "  WARNING: COUNT must be $ExpectedCount. Is this the CEB IMDb database?" -ForegroundColor Yellow
        }
        if ($null -eq $best -or $result.Seconds -lt $best.Seconds) {
            $best = $result
        }
    }
    return $best
}


# ===========================================================================
# MAIN PART
# ===========================================================================

try {
    Write-Host "Reproduction of the slow plan of the CEB query 7a_002"
    Write-Host "Server:   $Server"
    Write-Host "Database: $Database"
    Write-Host "Started:  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') (the script runs about 2-3 minutes)"

    if (-not (Test-Path -Path $IsqlPath)) {
        throw "isql.exe is not found: $IsqlPath. Give the correct path with -IsqlPath."
    }

    # -----------------------------------------------------------------------
    Write-Step "Step 1. Connection and server version"
    # -----------------------------------------------------------------------

    $output = Invoke-Isql -SqlText @'
SET LIST ON;
SELECT RDB$GET_CONTEXT('SYSTEM', 'ENGINE_VERSION') AS ENGINE_VERSION,
       (SELECT COUNT(*) FROM RDB$RELATIONS WHERE RDB$RELATION_NAME = 'MOVIE_INFO_IDX') AS IMDB_TABLES
FROM RDB$DATABASE;
'@
    $version = [regex]::Match($output, 'ENGINE_VERSION\s+(\S+)').Groups[1].Value
    $imdbTables = [regex]::Match($output, 'IMDB_TABLES\s+(\d+)').Groups[1].Value

    Write-Host "Engine version: $version"
    if ($imdbTables -ne "1") {
        throw "The database has no table MOVIE_INFO_IDX. This is not the IMDb database of the CEB test."
    }
    Write-Host "The IMDb tables are found."

    # -----------------------------------------------------------------------
    Write-Step "Step 2. Optimizer estimates and real numbers of rows"
    # -----------------------------------------------------------------------

    $report = @()
    $wrongEstimates = 0
    foreach ($check in $FilterChecks) {
        Write-Host "  checking: $($check.Name)"
        $estimate = Get-EstimatedRows -SqlText $check.Sql
        $real = (Measure-Query -SqlText $check.Sql).Count

        if ($null -eq $estimate) {
            $estimateText = "-"
            $ratioText = "-"
            $verdict = "no estimate"
        }
        else {
            # Real / Estimate: 1.0 is a perfect estimate, 3.0 means that the
            # real number of rows is 3 times bigger than the estimate.
            $ratio = $real / [Math]::Max($estimate, 1.0)
            $estimateText = Format-Number $estimate
            $ratioText = Format-Number $ratio 2

            if ($ratio -ge $BadEstimateFactor) {
                $verdict = "TOO LOW"
                $wrongEstimates++
            }
            elseif ($ratio -le (1.0 / $BadEstimateFactor)) {
                $verdict = "TOO HIGH"
                $wrongEstimates++
            }
            else {
                $verdict = "ok"
            }
        }

        $report += [PSCustomObject]@{
            "Filter"          = $check.Name
            "Estimate"        = $estimateText
            "Real rows"       = Format-Number $real
            "Real / Estimate" = $ratioText
            "Verdict"         = $verdict
        }
    }

    $report | Format-Table -AutoSize | Out-Host
    Write-Host "Wrong estimates (factor $BadEstimateFactor or more): $wrongEstimates"

    # -----------------------------------------------------------------------
    Write-Step "Step 3. Join order that the optimizer selects"
    # -----------------------------------------------------------------------

    # SET PLANONLY ON only prepares the query and shows the plan.
    $output = Invoke-Isql -SqlText ("SET PLANONLY ON;`n" + $Query7a002 + ";")
    $plan = [regex]::Match($output, 'PLAN .*').Value
    Write-Host $plan
    Write-Host ""

    # Each table in the plan is written as "ALIAS NATURAL" or "ALIAS INDEX (...)".
    # The order of these aliases in the plan text is the join order.
    $joinOrder = @()
    foreach ($match in [regex]::Matches($plan, '([A-Z][A-Z0-9_]*) (NATURAL|INDEX)')) {
        $joinOrder += $match.Groups[1].Value
    }
    Write-Host ("Join order: " + ($joinOrder -join " > "))

    $positionMii1 = [array]::IndexOf($joinOrder, "MII1")
    $positionName = [array]::IndexOf($joinOrder, "N")
    if ($positionMii1 -ge 0 -and $positionName -ge 0 -and $positionMii1 -lt $positionName) {
        Write-Host "The join reads MOVIE_INFO_IDX (MII1) before NAME (N): this is the slow order." -ForegroundColor Yellow
    }
    else {
        Write-Host "The join reads NAME (N) before MOVIE_INFO_IDX (MII1): this is the fast order." -ForegroundColor Green
    }

    # -----------------------------------------------------------------------
    Write-Step "Step 4. Run time: optimizer plan and forced plan"
    # -----------------------------------------------------------------------

    $optimizerRun = Measure-QueryBest -Title "a) Plan of the optimizer:" -SqlText $Query7a002
    $forcedRun = Measure-QueryBest -Title "b) Forced plan (starts from NAME):" -SqlText ($Query7a002 + "`n" + $ForcedPlan)

    # -----------------------------------------------------------------------
    Write-Step "Result"
    # -----------------------------------------------------------------------

    $slowdown = $optimizerRun.Seconds / [Math]::Max($forcedRun.Seconds, 0.001)

    Write-Host ("Plan of the optimizer: {0,7} s" -f (Format-Number $optimizerRun.Seconds 1))
    Write-Host ("Forced plan:           {0,7} s" -f (Format-Number $forcedRun.Seconds 1))
    Write-Host ("The plan of the optimizer is {0} times slower." -f (Format-Number $slowdown 1))
    Write-Host ""

    if ($slowdown -ge $SlowFactor) {
        Write-Host "PROBLEM REPRODUCED" -ForegroundColor Red
        Write-Host "The optimizer plan is $SlowFactor or more times slower than the forced plan."
        exit 1
    }
    else {
        Write-Host "PROBLEM NOT REPRODUCED" -ForegroundColor Green
        Write-Host "The optimizer plan is less than $SlowFactor times slower than the forced plan."
        exit 0
    }
}
catch {
    Write-Host ""
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 2
}
