param([switch]$ResumeVerified)
$ErrorActionPreference = 'Stop'
$workspacePath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$archivePath = [IO.Path]::GetFullPath((Join-Path $workspacePath 'local_archive/20261117_cleanup'))
$planFile = Join-Path $archivePath 'PLAN.json'
$plan = Get-Content -LiteralPath $planFile -Raw | ConvertFrom-Json
if ($plan.root -ne $workspacePath -or $plan.archive -ne $archivePath) { throw 'Archive plan root mismatch' }
$eventsFile = Join-Path $archivePath 'MOVES.jsonl'
$finished = @{}
if (Test-Path -LiteralPath $eventsFile) {
    if (-not $ResumeVerified) { throw 'Prior moves exist; inspect rather than automatically rerun' }
    foreach ($line in Get-Content -LiteralPath $eventsFile) {
        $event = $line | ConvertFrom-Json
        $finished[$event.source] = $event
    }
}
$done = 0
foreach ($item in $plan.moves) {
    $sourcePath = [IO.Path]::GetFullPath((Join-Path $workspacePath $item.source))
    $destinationPath = [IO.Path]::GetFullPath((Join-Path $workspacePath $item.destination))
    if ($finished.ContainsKey($item.source)) {
        if (-not (Test-Path -LiteralPath $destinationPath)) { throw 'Journal target missing' }
        if ($item.compatibilityJunction) {
            $link = Get-Item -LiteralPath $sourcePath -Force
            if ($link.LinkType -ne 'Junction' -or $link.Target -ne $destinationPath) { throw 'Journal junction differs' }
        } elseif (Test-Path -LiteralPath $sourcePath) { throw 'Journal source still exists' }
        $done++
        continue
    }
    # Resolve and check absolute source/target paths before every recursive directory move.
    $resolvedSource = (Resolve-Path -LiteralPath $sourcePath).ProviderPath
    if (-not $resolvedSource.StartsWith($workspacePath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Source escaped workspace' }
    if (-not $destinationPath.StartsWith($archivePath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination escaped archive' }
    if (Test-Path -LiteralPath $destinationPath) { throw "Destination collision: $($item.source)" }
    $entry = Get-Item -LiteralPath $sourcePath -Force
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Refusing to move an existing reparse point: $($item.source)" }
    $parent = Split-Path -Parent $destinationPath
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    Move-Item -LiteralPath $sourcePath -Destination $destinationPath
    if ($item.compatibilityJunction) {
        try { New-Item -ItemType Junction -Path $sourcePath -Target $destinationPath | Out-Null }
        catch {
            if (-not (Test-Path -LiteralPath $sourcePath)) { Move-Item -LiteralPath $destinationPath -Destination $sourcePath }
            throw
        }
    }
    [ordered]@{ source=$item.source; destination=$item.destination; compatibilityJunction=$item.compatibilityJunction; completedUtc=[DateTime]::UtcNow.ToString('o') } | ConvertTo-Json -Compress | Add-Content -LiteralPath $eventsFile -Encoding utf8
    $done++
    if ($done % 20 -eq 0) { Write-Output "Completed moves: $done" }
}
Write-Output "Completed all $done planned moves"
