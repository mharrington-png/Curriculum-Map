param(
    [Parameter(Mandatory = $true)][string]$ObjectiveMarkdown,
    [Parameter(Mandatory = $true)][string]$CourseId,
    [Parameter(Mandatory = $true)][string]$CourseNumber,
    [Parameter(Mandatory = $true)][string]$CourseTitle,
    [Parameter(Mandatory = $true)][string]$SourcePath,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'

function Escape-YamlDoubleQuoted([string]$Text) {
    return $Text.Replace('\', '\\').Replace('"', '\"')
}

$units = [System.Collections.Generic.List[object]]::new()
$current = $null

Get-Content -LiteralPath $ObjectiveMarkdown | ForEach-Object {
    if ($_ -match '^## Review Objectives \(`([^`]+)`\)$') {
        $current = [ordered]@{ id = $Matches[1]; title = 'Review Content'; priority = 'review'; objectives = [System.Collections.Generic.List[object]]::new() }
        $units.Add($current)
    }
    elseif ($_ -match '^## Required Unit [0-9]+: (.+) \(`([^`]+)`\)$') {
        $current = [ordered]@{ id = $Matches[2]; title = $Matches[1]; priority = 'required'; objectives = [System.Collections.Generic.List[object]]::new() }
        $units.Add($current)
    }
    elseif ($_ -match '^## Unit [0-9]+: (.+) \(`([^`]+)`\)$') {
        $current = [ordered]@{ id = $Matches[2]; title = $Matches[1]; priority = 'required'; objectives = [System.Collections.Generic.List[object]]::new() }
        $units.Add($current)
    }
    elseif ($_ -match '^## Extension Unit [0-9]+: (.+) \(`([^`]+)`\)$') {
        $current = [ordered]@{ id = $Matches[2]; title = $Matches[1]; priority = 'extension'; objectives = [System.Collections.Generic.List[object]]::new() }
        $units.Add($current)
    }
    elseif ($_ -match '^## Extension Objectives \(`([^`]+)`\)$') {
        $current = [ordered]@{ id = $Matches[1]; title = 'Extension Content'; priority = 'extension'; objectives = [System.Collections.Generic.List[object]]::new() }
        $units.Add($current)
    }
    elseif ($current -and $_ -match '^- \*\*(M[0-9]+-[A-Z]+-[0-9]{3}):\*\* (.+)$') {
        $current.objectives.Add([ordered]@{ id = $Matches[1]; statement = $Matches[2] })
    }
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add('schema_version: 1')
$lines.Add('course:')
$lines.Add("  id: $CourseId")
$lines.Add("  number: $CourseNumber")
$lines.Add("  title: $CourseTitle")
$lines.Add('  status: draft')
$lines.Add("  source: $SourcePath")
$lines.Add('')
$lines.Add('units:')
foreach ($unit in $units) {
    $lines.Add("  - id: $($unit.id)")
    $lines.Add("    title: $($unit.title)")
    $lines.Add("    priority: $($unit.priority)")
    $lines.Add('    objectives:')
    foreach ($objective in $unit.objectives) {
        $statement = Escape-YamlDoubleQuoted $objective.statement
        $lines.Add("      - {id: $($objective.id), statement: `"$statement`"}")
    }
    $lines.Add('')
}

$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force $directory | Out-Null
[System.IO.File]::WriteAllLines($OutputPath, $lines, [System.Text.UTF8Encoding]::new($false))
