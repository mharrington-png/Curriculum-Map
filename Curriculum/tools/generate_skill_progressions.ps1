param(
    [string]$OutputJson = 'generated/skill_progressions.json',
    [string]$OutputMarkdown = 'generated/SKILL_PROGRESSIONS.md',
    [string]$AuditMarkdown = 'data/audits/SKILL_PROGRESSION_AUDIT.md'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$courseOrder = @('M12', 'M21', 'M22', 'M31', 'M32', 'M39', 'M49')
$courseLabels = @{
    M12 = 'Math 12'; M21 = 'Math 21'; M22 = 'Math 22'
    M31 = 'Math 31'; M32 = 'Math 32'; M39 = 'Math 39'; M49 = 'Math 49'
}
$acceptedIncoming = @{
    'SK-ALG-CROSS-MULTIPLY' = 'Inherited from middle school'
    'SK-ALG-DISTRIBUTE' = 'Inherited from middle school'
    'SK-ALG-EXPRESSION-SIMPLIFY' = 'Inherited from middle school'
    'SK-ALG-LIKE-TERMS' = 'Inherited from middle school'
    'SK-NUM-PERCENT-CALCULATE' = 'Inherited from middle school'
    'SK-NUM-PERCENT-CHANGE' = 'Inherited from middle school'
    'SK-NUM-FRACTION-OPERATE' = 'Inherited from middle school'
    'SK-NUM-INTEGER-OPERATE' = 'Inherited from middle school'
    'SK-NUM-ORDER-OPERATIONS' = 'Inherited from middle school'
    'SK-NUM-PRIME-FACTOR' = 'Inherited from middle school'
    'SK-COORD-DISTANCE-AXIS' = 'Inherited horizontal/vertical coordinate distance'
    'SK-COORD-MIDPOINT' = 'Inherited from earlier mathematics'
}
$acceptedAlternateIntroductions = @(
    'SK-FUNC-DOMAIN-COMBINE', 'SK-FUNC-OPERATIONS', 'SK-MODEL-FAMILY-SELECT',
    'SK-POLY-END-BEHAVIOR', 'SK-POLY-MULTIPLICITY', 'SK-POLY-DEGREE-ZEROS',
    'SK-POLY-DEGREE-TURNING', 'SK-POLY-DEGREE-INFLECTION', 'SK-VAR-DIRECT',
    'SK-VAR-INVERSE', 'SK-VAR-POWER'
)

function Resolve-OutputPath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return Join-Path $root $Path
}

$skillDefinitions = @{}
Get-ChildItem (Join-Path $root 'skills') -Filter '*_SKILLS.md' | ForEach-Object {
    Get-Content -LiteralPath $_.FullName | ForEach-Object {
        if ($_ -match '^- \*\*(SK-[A-Z0-9-]+):\*\* (.+)$') {
            $skillDefinitions[$Matches[1]] = $Matches[2]
        }
    }
}

$occurrences = [System.Collections.Generic.List[object]]::new()
$objectiveLookup = @{}

foreach ($courseId in $courseOrder) {
    $fileStem = $courseId.ToLower().Replace('m', 'math')
    $courseFile = Join-Path $root "data/courses/$fileStem.yaml"
    $mappingFile = Join-Path $root "data/mappings/$($fileStem)_objective_skills.yaml"

    $currentUnit = $null
    $unitTitle = $null
    $unitPriority = $null
    Get-Content -LiteralPath $courseFile | ForEach-Object {
        if ($_ -match '^  - id: (M[0-9]+-[A-Z]+)$') {
            $currentUnit = $Matches[1]
            $unitTitle = ''
            $unitPriority = ''
        }
        elseif ($currentUnit -and $_ -match '^    title: (.+)$') {
            $unitTitle = $Matches[1]
        }
        elseif ($currentUnit -and $_ -match '^    priority: (review|required|extension)$') {
            $unitPriority = $Matches[1]
        }
        elseif ($currentUnit -and $_ -match '^      - \{id: (M[0-9]+-[A-Z]+-[0-9]{3}), statement: "(.+)"\}$') {
            $objectiveLookup[$Matches[1]] = [ordered]@{
                course_id = $courseId
                course = $courseLabels[$courseId]
                unit_id = $currentUnit
                unit_title = $unitTitle
                priority = $unitPriority
                objective_id = $Matches[1]
                objective = $Matches[2]
            }
        }
    }

    $currentObjective = $null
    Get-Content -LiteralPath $mappingFile | ForEach-Object {
        if ($_ -match '^  - objective_id: (M[0-9]+-[A-Z]+-[0-9]{3})$') {
            $currentObjective = $Matches[1]
        }
        elseif ($currentObjective -and $_ -match 'skill_id: (SK-[A-Z0-9-]+), relationship: ([a-z-]+), progression: ([a-z-]+)') {
            $objective = $objectiveLookup[$currentObjective]
            $occurrences.Add([pscustomobject][ordered]@{
                skill_id = $Matches[1]
                course_id = $objective.course_id
                course = $objective.course
                unit_id = $objective.unit_id
                unit_title = $objective.unit_title
                priority = $objective.priority
                objective_id = $objective.objective_id
                objective = $objective.objective
                relationship = $Matches[2]
                progression = $Matches[3]
            })
        }
    }
}

$progressions = [System.Collections.Generic.List[object]]::new()
foreach ($skillId in ($occurrences.skill_id | Sort-Object -Unique)) {
    $skillOccurrences = @($occurrences | Where-Object skill_id -eq $skillId | Sort-Object @{Expression = {$courseOrder.IndexOf($_.course_id)}}, objective_id)
    $introductions = @($skillOccurrences | Where-Object progression -eq 'introduce')
    $firstIntroduction = $introductions | Select-Object -First 1
    $inherited = $acceptedIncoming.ContainsKey($skillId)
    $progressions.Add([pscustomobject][ordered]@{
        skill_id = $skillId
        description = $skillDefinitions[$skillId]
        introduction_status = if ($firstIntroduction) { 'mapped' } elseif ($inherited) { 'inherited' } else { 'unresolved' }
        first_introduced_course = if ($firstIntroduction) { $firstIntroduction.course } else { $null }
        inherited_note = if ($inherited) { $acceptedIncoming[$skillId] } else { $null }
        courses = @($skillOccurrences.course | Select-Object -Unique)
        occurrences = $skillOccurrences
    })
}

$jsonPath = Resolve-OutputPath $OutputJson
$jsonDirectory = Split-Path -Parent $jsonPath
New-Item -ItemType Directory -Force $jsonDirectory | Out-Null
$progressions | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding utf8
$uiDataPath = Join-Path $root 'ui/public/data/skill_progressions.json'
if (Test-Path (Split-Path -Parent $uiDataPath)) {
    Copy-Item -LiteralPath $jsonPath -Destination $uiDataPath -Force
}

$roleLabels = @{ introduce = 'Introduce'; reinforce = 'Reinforce'; deepen = 'Deepen'; apply = 'Apply' }
$priorityLabels = @{ review = 'Review'; required = 'Required'; extension = 'Extension' }
$relationshipLabels = @{ prerequisite = 'Prerequisite'; required = 'Required'; 'method-dependent' = 'Method-dependent' }

$indexLines = [System.Collections.Generic.List[string]]::new()
$indexLines.Add('# Complete Skill Progressions')
$indexLines.Add('')
$indexLines.Add('Generated from the approved course and objective-to-skill YAML records. Select a skill heading to review every mapped occurrence across the course sequence.')
$indexLines.Add('')
$indexLines.Add('Legend: **I** Introduce, **R** Reinforce, **D** Deepen, **A** Apply.')
$indexLines.Add('')
foreach ($skill in $progressions) {
    $indexLines.Add("## $($skill.skill_id): $($skill.description)")
    $indexLines.Add('')
    if ($skill.introduction_status -eq 'mapped') {
        $indexLines.Add("First introduction: **$($skill.first_introduced_course)**")
    }
    elseif ($skill.introduction_status -eq 'inherited') {
        $indexLines.Add("First introduction: **Inherited** — $($skill.inherited_note)")
    }
    else {
        $indexLines.Add('First introduction: **Not yet identified**')
    }
    $indexLines.Add('')
    $indexLines.Add('| Course | Role | Priority | Relationship | Unit | Objective |')
    $indexLines.Add('|---|---|---|---|---|---|')
    foreach ($item in $skill.occurrences) {
        $role = $roleLabels[$item.progression]
        $indexLines.Add("| $($item.course) | $role | $($priorityLabels[$item.priority]) | $($relationshipLabels[$item.relationship]) | $($item.unit_title) | ``$($item.objective_id)`` — $($item.objective) |")
    }
    $indexLines.Add('')
}
$markdownPath = Resolve-OutputPath $OutputMarkdown
New-Item -ItemType Directory -Force (Split-Path -Parent $markdownPath) | Out-Null
[System.IO.File]::WriteAllLines($markdownPath, $indexLines, [System.Text.UTF8Encoding]::new($false))

$unresolved = @($progressions | Where-Object introduction_status -eq 'unresolved')
$usedBeforeIntroduction = @()
$duplicateIntroductions = @()
$extensionDependencies = @()
$singleCourse = @($progressions | Where-Object { $_.courses.Count -eq 1 })
$broadDefinitions = @($progressions | Where-Object { $_.description -match '\b(and|or)\b' -and ($_.description -split '\s+').Count -gt 13 })

foreach ($skill in $progressions) {
    $introCourses = @($skill.occurrences | Where-Object progression -eq 'introduce' | Select-Object -ExpandProperty course_id -Unique)
    if (-not $acceptedIncoming.ContainsKey($skill.skill_id) -and $introCourses.Count -gt 0) {
        $firstIntroIndex = ($introCourses | ForEach-Object { $courseOrder.IndexOf($_) } | Measure-Object -Minimum).Minimum
        $earlierUses = @($skill.occurrences | Where-Object { $courseOrder.IndexOf($_.course_id) -lt $firstIntroIndex })
        if ($earlierUses.Count -gt 0) {
            $usedBeforeIntroduction += [pscustomobject]@{ skill = $skill; earlier = $earlierUses }
        }
    }
    $isAcceptedM39M49Route = $acceptedAlternateIntroductions -contains $skill.skill_id -and
        $introCourses.Count -eq 2 -and $introCourses -contains 'M39' -and $introCourses -contains 'M49'
    if ($introCourses.Count -gt 1 -and -not $isAcceptedM39M49Route) {
        $duplicateIntroductions += [pscustomobject]@{ skill = $skill; courses = $introCourses }
    }

    $introOccurrences = @($skill.occurrences | Where-Object progression -eq 'introduce')
    if ($introOccurrences.Count -gt 0 -and @($introOccurrences | Where-Object priority -ne 'extension').Count -eq 0) {
        $firstIntroIndex = ($introOccurrences | ForEach-Object { $courseOrder.IndexOf($_.course_id) } | Measure-Object -Minimum).Minimum
        $nonExtensionInstruction = @($skill.occurrences | Where-Object {
            $_.priority -ne 'extension' -and $_.relationship -eq 'required' -and
            $_.progression -in @('introduce', 'reinforce', 'deepen')
        })
        if ($nonExtensionInstruction.Count -eq 0) {
            $laterRequired = @($skill.occurrences | Where-Object {
                $courseOrder.IndexOf($_.course_id) -gt $firstIntroIndex -and $_.priority -ne 'extension' -and
                ($_.relationship -eq 'prerequisite' -or $_.progression -eq 'apply')
            })
            if ($laterRequired.Count -gt 0) {
                $extensionDependencies += [pscustomobject]@{ skill = $skill; later = $laterRequired }
            }
        }
    }
}

$auditLines = [System.Collections.Generic.List[string]]::new()
$auditLines.Add('# Skill Progression Audit')
$auditLines.Add('')
$auditLines.Add('Generated automatically from the approved course and mapping records. Warnings require curriculum review; informational findings may be intentional.')
$auditLines.Add('')
$auditLines.Add('## Summary')
$auditLines.Add('')
$auditLines.Add("- Canonical skills used in mappings: $($progressions.Count)")
$auditLines.Add("- Skills without a mapped or accepted inherited introduction: $($unresolved.Count)")
$auditLines.Add("- Skills used in an earlier course than their recorded introduction: $($usedBeforeIntroduction.Count)")
$auditLines.Add("- Skills introduced in more than one course: $($duplicateIntroductions.Count)")
$auditLines.Add("- Skills introduced only in extension material and later assumed outside extension: $($extensionDependencies.Count)")
$auditLines.Add("- Skills appearing in only one course: $($singleCourse.Count)")
$auditLines.Add("- Broad-definition review candidates: $($broadDefinitions.Count)")
$auditLines.Add('')
$auditLines.Add('## Warning: Introduction Not Identified')
$auditLines.Add('')
if ($unresolved.Count -eq 0) { $auditLines.Add('None.') }
foreach ($skill in $unresolved) {
    $first = $skill.occurrences | Select-Object -First 1
    $auditLines.Add("- ``$($skill.skill_id)`` — $($skill.description) First appears in $($first.course) as **$($roleLabels[$first.progression])** for ``$($first.objective_id)``.")
}
$auditLines.Add('')
$auditLines.Add('## Warning: Used Before Recorded Introduction')
$auditLines.Add('')
if ($usedBeforeIntroduction.Count -eq 0) { $auditLines.Add('None.') }
foreach ($item in $usedBeforeIntroduction) {
    $earlier = @($item.earlier | ForEach-Object { "$($_.course) ``$($_.objective_id)`` ($($roleLabels[$_.progression]))" }) -join '; '
    $auditLines.Add("- ``$($item.skill.skill_id)`` — earlier use: $earlier; recorded introduction: $($item.skill.first_introduced_course).")
}
$auditLines.Add('')
$auditLines.Add('## Warning: Introduced in Multiple Courses')
$auditLines.Add('')
if ($duplicateIntroductions.Count -eq 0) { $auditLines.Add('None.') }
foreach ($item in $duplicateIntroductions) {
    $labels = @($item.courses | ForEach-Object { $courseLabels[$_] }) -join ', '
    $auditLines.Add("- ``$($item.skill.skill_id)`` — $labels")
}
$auditLines.Add('')
$auditLines.Add('## Warning: Extension Introduction Later Assumed')
$auditLines.Add('')
if ($extensionDependencies.Count -eq 0) { $auditLines.Add('None.') }
foreach ($item in $extensionDependencies) {
    $later = @($item.later | ForEach-Object { "$($_.course) ``$($_.objective_id)``" }) -join '; '
    $auditLines.Add("- ``$($item.skill.skill_id)`` — introduced only in extension; later used by $later.")
}
$auditLines.Add('')
$auditLines.Add('## Information: Accepted Incoming Skills')
$auditLines.Add('')
foreach ($skillId in ($acceptedIncoming.Keys | Sort-Object)) {
    $auditLines.Add("- ``$skillId`` — $($acceptedIncoming[$skillId])")
}
$auditLines.Add('')
$auditLines.Add('## Information: Accepted Alternate-Route Introductions')
$auditLines.Add('')
$auditLines.Add('Math 39 is optional between Math 32 and Math 49. These skills may be introduced in Math 39 for students who take it and independently introduced in Math 49 for students who do not.')
$auditLines.Add('')
foreach ($skillId in ($acceptedAlternateIntroductions | Sort-Object)) {
    $auditLines.Add("- ``$skillId`` — introduced in both Math 39 and Math 49")
}
$auditLines.Add('')
$auditLines.Add('## Information: Skills Appearing in Only One Course')
$auditLines.Add('')
$auditLines.Add('These may be appropriately course-specific. Review them when checking whether later courses should reinforce or apply the skill.')
$auditLines.Add('')
foreach ($skill in $singleCourse) {
    $auditLines.Add("- ``$($skill.skill_id)`` — $($skill.description) ($($skill.courses[0]))")
}
$auditLines.Add('')
$auditLines.Add('## Information: Broad-Definition Review Candidates')
$auditLines.Add('')
$auditLines.Add('Automatically identified from length and conjunctions; inclusion does not mean a definition is invalid.')
$auditLines.Add('')
if ($broadDefinitions.Count -eq 0) { $auditLines.Add('None.') }
foreach ($skill in $broadDefinitions) {
    $auditLines.Add("- ``$($skill.skill_id)`` — $($skill.description)")
}

$auditPath = Resolve-OutputPath $AuditMarkdown
New-Item -ItemType Directory -Force (Split-Path -Parent $auditPath) | Out-Null
[System.IO.File]::WriteAllLines($auditPath, $auditLines, [System.Text.UTF8Encoding]::new($false))

[pscustomobject]@{
    Skills = $progressions.Count
    Occurrences = $occurrences.Count
    UnresolvedIntroductions = $unresolved.Count
    UsedBeforeIntroduction = $usedBeforeIntroduction.Count
    DuplicateCourseIntroductions = $duplicateIntroductions.Count
    ExtensionDependencies = $extensionDependencies.Count
    SingleCourseSkills = $singleCourse.Count
    Json = $jsonPath
    Markdown = $markdownPath
    Audit = $auditPath
}
