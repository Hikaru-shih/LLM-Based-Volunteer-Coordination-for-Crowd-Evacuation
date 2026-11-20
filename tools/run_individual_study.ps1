param(
    [ValidateSet('Check','Execute','Analyze')][string]$Action = 'Check',
    [string]$Python = '',
    [string]$LaunchConfig = 'research/individual_agent_v1/formal-v3-launch.json',
    [string]$Unity = 'C:/Program Files/Unity/Hub/Editor/6000.0.59f2/Editor/Unity.exe'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
if (!$Python) {
    $installedPython = Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($installedPython) { $Python = $installedPython.Source }
    else { $Python = Join-Path $env:USERPROFILE 'AppData/Local/Programs/Python/Python312/python.exe' }
}
if (!(Test-Path -LiteralPath $Python)) { throw 'Supply -Python with a Python interpreter containing the project dependencies.' }
$env:PYTHONUTF8 = '1'
Push-Location $projectRoot
try {
    $config = Get-Content -LiteralPath $LaunchConfig -Raw | ConvertFrom-Json
    $bundle = Join-Path $projectRoot $config.bundle
    $runtime = Join-Path $projectRoot $config.runtimeProject
    $output = Join-Path $projectRoot $config.output
    & $Python tools/individual_readiness.py --bundle $bundle --root $projectRoot --project-root $runtime
    if ($LASTEXITCODE -ne 0) { throw 'Readiness failed. No execution or analysis started.' }
    $proof = Get-Content -LiteralPath $config.unityPreflight -Raw | ConvertFrom-Json
    $locked = Get-Content -LiteralPath (Join-Path $bundle 'lock.json') -Raw | ConvertFrom-Json
    if (!$proof.passed -or $proof.lockID -ne $locked.lockID -or $proof.remoteRequests -ne 0) { throw 'Actual Unity preflight evidence does not match this study.' }
    if ($Action -eq 'Analyze') {
        $progress = Get-Content -LiteralPath (Join-Path $output 'progress.json') -Raw | ConvertFrom-Json
        if ($progress.outcome -ne 'completed') { throw 'Formal collection is incomplete; preserve and review it before final analysis.' }
        $analysis = Join-Path $projectRoot $config.analysis
        & $Python tools/individual_analysis.py $output --output $analysis --records-root (Join-Path $projectRoot 'experiment_records')
        if ($LASTEXITCODE -ne 0) { throw 'Analysis failed; original records remain saved.' }
        & $Python tools/individual_study_design.py (Join-Path $bundle 'design.json') --primary-report $analysis --output (Join-Path $analysis 'primary-contrast.json')
        if ($LASTEXITCODE -ne 0) { throw 'Primary contrast failed; inspect the saved analysis.' }
    } else {
        $driverArgs = @('tools/run_formal_sampling.py','--bundle',$bundle,'--project-root',$runtime,'--output',$output,'--unity',$Unity,'--credential-root',$projectRoot,'--records-root',(Join-Path $projectRoot 'experiment_records'))
        if ($Action -eq 'Execute') { $driverArgs += '--execute' }
        & $Python @driverArgs
        if ($LASTEXITCODE -ne 0) { throw 'Driver stopped. Inspect its logs before resuming.' }
    }
} finally { Pop-Location }
