param(
    [Parameter(Mandatory = $true)]
    [string]$CourseId,

    [Parameter(Mandatory = $true)]
    [string]$CourseData,

    [Parameter(Mandatory = $true)]
    [string]$MappingData,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

$skills = @{}
Get-ChildItem (Join-Path $root 'skills') -Filter '*_SKILLS.md' | ForEach-Object {
    Get-Content -LiteralPath $_.FullName | ForEach-Object {
        if ($_ -match '^- \*\*(SK-[A-Z0-9-]+):\*\* (.+)$') {
            $skills[$Matches[1]] = $Matches[2]
        }
    }
}

$units = [ordered]@{}
$currentUnit = $null
$pendingUnit = $null
Get-Content -LiteralPath $CourseData | ForEach-Object {
    if ($_ -match '^  - id: (M[0-9]+-[A-Z]+)$') {
        $pendingUnit = $Matches[1]
        $units[$pendingUnit] = [ordered]@{ title = ''; priority = ''; objectives = @() }
        $currentUnit = $pendingUnit
    }
    elseif ($currentUnit -and $_ -match '^    title: (.+)$') {
        $units[$currentUnit].title = $Matches[1]
    }
    elseif ($currentUnit -and $_ -match '^    priority: (.+)$') {
        $units[$currentUnit].priority = $Matches[1]
    }
    elseif ($currentUnit -and $_ -match '^      - \{id: (M[0-9]+-[A-Z]+-[0-9]{3}), statement: "(.+)"\}$') {
        $units[$currentUnit].objectives += [ordered]@{ id = $Matches[1]; statement = $Matches[2] }
    }
}

$mappings = @{}
$currentObjective = $null
Get-Content -LiteralPath $MappingData | ForEach-Object {
    if ($_ -match '^  - objective_id: (M[0-9]+-[A-Z]+-[0-9]{3})$') {
        $currentObjective = $Matches[1]
        $mappings[$currentObjective] = @()
    }
    elseif ($currentObjective -and $_ -match 'skill_id: (SK-[A-Z0-9-]+), relationship: ([a-z-]+), progression: ([a-z-]+)') {
        $mappings[$currentObjective] += [ordered]@{
            skill_id = $Matches[1]
            relationship = $Matches[2]
            progression = $Matches[3]
        }
    }
}

$relationshipLabels = @{
    'prerequisite' = 'Prerequisite'
    'required' = 'Required'
    'method-dependent' = 'Method-dependent'
}
$progressionLabels = @{
    'introduce' = 'Introduce'
    'reinforce' = 'Reinforce'
    'deepen' = 'Deepen'
    'apply' = 'Apply'
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("# $CourseId Objective-to-Skill Mapping Review")
$lines.Add('')
$lines.Add('This teacher-facing view combines each learning objective with the supporting skills currently mapped to it. The YAML files remain the structured source; this document is generated for review.')
$lines.Add('')
$lines.Add('## How to Read the Mapping')
$lines.Add('')
$lines.Add('- **Prerequisite:** Students should bring this skill into the objective.')
$lines.Add('- **Required:** The skill is inherent in successfully meeting the objective.')
$lines.Add('- **Method-dependent:** The skill is needed for one accepted method, but not every method.')
$lines.Add('- **Introduce:** First sustained instruction in this course sequence.')
$lines.Add('- **Reinforce:** Revisit at comparable depth.')
$lines.Add('- **Deepen:** Add complexity, interpretation, representation, or independence.')
$lines.Add('- **Apply:** Use an established skill as a tool inside a new objective.')
$lines.Add('')

foreach ($unitId in $units.Keys) {
    $unit = $units[$unitId]
    $priority = (Get-Culture).TextInfo.ToTitleCase($unit.priority)
    $lines.Add("## $priority - $($unit.title)")
    $lines.Add('')
    foreach ($objective in $unit.objectives) {
        $lines.Add("### $($objective.statement)")
        $lines.Add('')
        $lines.Add("Objective ID: ``$($objective.id)``")
        $lines.Add('')
        $lines.Add('| Supporting skill | Relationship | Course role | Skill ID |')
        $lines.Add('|---|---|---|---|')
        foreach ($mapping in $mappings[$objective.id]) {
            $description = $skills[$mapping.skill_id]
            if (-not $description) { $description = '[Missing skill definition]' }
            $lines.Add("| $description | $($relationshipLabels[$mapping.relationship]) | $($progressionLabels[$mapping.progression]) | ``$($mapping.skill_id)`` |")
        }
        $lines.Add('')
    }
}

$outputDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force $outputDirectory | Out-Null
[System.IO.File]::WriteAllLines($OutputPath, $lines, [System.Text.UTF8Encoding]::new($false))
