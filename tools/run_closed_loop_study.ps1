param(
    [ValidateSet('Check','Execute','Analyze')][string]$Action = 'Check',
    [string]$Python = '',
    [string]$LaunchConfig = 'research/closed_loop_v1/formal-launch.json'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (!$Python) { $Python = Join-Path $env:USERPROFILE 'AppData/Local/Programs/Python/Python312/python.exe' }
if (!(Test-Path -LiteralPath $Python)) { throw 'Supply -Python with the project Python interpreter.' }
$env:PYTHONUTF8 = '1'
Push-Location $projectRoot
try {
    $config = Get-Content -LiteralPath $LaunchConfig -Raw | ConvertFrom-Json
    $bundle = Join-Path $projectRoot $config.bundle
    $projects = @($config.runtimeProjects | ForEach-Object { Join-Path $projectRoot $_ })
    $outputs = @($config.outputs | ForEach-Object { Join-Path $projectRoot $_ })
    $proofPath = Join-Path $projectRoot $config.unityPreflight
    & $Python tools/closed_loop_release.py check --bundle $bundle --projects @projects
    if ($LASTEXITCODE -ne 0) { throw 'Source or evidence verification failed.' }
    $proof = Get-Content -LiteralPath $proofPath -Raw | ConvertFrom-Json
    $locked = Get-Content -LiteralPath (Join-Path $bundle 'lock.json') -Raw | ConvertFrom-Json
    if (!$proof.passed -or $proof.lockID -ne $locked.lockID -or $proof.cases -ne 76 -or $proof.remoteRequests -ne 0 -or $proof.simulationSteps -ne 0 -or $proof.formalJobsClaimed -ne 0) { throw 'Actual Unity zero-step proof is missing or mismatched.' }
    if ($Action -eq 'Execute') {
        & $Python tools/closed_loop_release.py execute --bundle $bundle --projects @projects --outputs @outputs --preflight $proofPath --execute-final
        if ($LASTEXITCODE -ne 0) { throw 'Campaign stopped. Preserve records; no automatic rerun or rescue.' }
    } elseif ($Action -eq 'Analyze') {
        $analysis = Join-Path $projectRoot $config.analysis
        & $Python tools/closed_loop_study.py analyze @outputs --output $analysis --bundle $bundle
        if ($LASTEXITCODE -ne 0) { throw 'Complete final matrix/analysis verification failed.' }
        & $Python tools/closed_loop_report.py $analysis
        if ($LASTEXITCODE -ne 0) { throw 'Report failed; validated raw evidence remains preserved.' }
    } else { Write-Output 'Check completed. No simulation steps or API requests were executed.' }
} finally { Pop-Location }
