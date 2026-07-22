param(
    [string]$PythonExecutable = "python"
)

$ErrorActionPreference = "Stop"

$curriculumRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workspaceRoot = (Resolve-Path (Join-Path $curriculumRoot "..")).Path
$builderScript = Join-Path $PSScriptRoot "unit_learning_map_builder.py"
$iconBuilder = Join-Path $PSScriptRoot "build_learning_map_builder_icon.py"
$iconPng = Join-Path $curriculumRoot "assets\student-learning-map-builder.png"
$iconIco = Join-Path $curriculumRoot "assets\student-learning-map-builder.ico"
$outputDirectory = Join-Path $curriculumRoot "output\apps\student-learning-map-builder"
$distributionDirectory = Join-Path $outputDirectory "Student Learning Map Builder"
$workDirectory = Join-Path $workspaceRoot "tmp\student-learning-map-builder-package"
$courseData = Join-Path $curriculumRoot "data\courses"
$skillData = Join-Path $curriculumRoot "generated\skill_progressions.json"
$instructions = Join-Path $curriculumRoot "docs\STUDENT_LEARNING_MAP_BUILDER.md"

New-Item -ItemType Directory -Force $outputDirectory | Out-Null
New-Item -ItemType Directory -Force $workDirectory | Out-Null

& $PythonExecutable $iconBuilder
if ($LASTEXITCODE -ne 0) {
    throw "The Student Learning Map Builder icon could not be created."
}

$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--windowed",
    "--name", "Student Learning Map Builder",
    "--icon", $iconIco,
    "--distpath", $outputDirectory,
    "--workpath", $workDirectory,
    "--specpath", $workDirectory,
    "--paths", $PSScriptRoot,
    "--add-data", "${courseData};Curriculum/data/courses",
    "--add-data", "${skillData};Curriculum/generated",
    "--add-data", "${iconPng};Curriculum/assets",
    $builderScript
)

& $PythonExecutable @arguments
if ($LASTEXITCODE -ne 0) {
    throw "The Student Learning Map Builder package could not be created."
}

Copy-Item -LiteralPath $instructions -Destination (Join-Path $distributionDirectory "README.md") -Force

$executable = Join-Path $distributionDirectory "Student Learning Map Builder.exe"
Write-Host "Created $executable"
