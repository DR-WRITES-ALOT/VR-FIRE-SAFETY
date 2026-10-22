<#
.SYNOPSIS
    Moves or copies this Unity project to a short path so Windows can import it.

.DESCRIPTION
    Unity resolves package files under <project>\Library\PackageCache\<package>@<hash>\...
    Some URP and Input System editor files are ~145 characters on their own. Windows
    refuses paths of 260 characters or more, so a project inside a deep folder (for
    example a double-unzipped copy in Downloads) throws DirectoryNotFoundException and
    "Asset import failed", and can crash the asset import worker.

    This script copies Assets, Packages, ProjectSettings, tools and README.md to a short
    destination (default C:\VR\FireSafety), skipping Library, Temp, obj, Logs and build,
    so the copy itself never touches a long path.

.EXAMPLE
    # copy to the default short path and print what to do next
    powershell -ExecutionPolicy Bypass -File tools\Fix-ProjectPath.ps1

.EXAMPLE
    # copy somewhere else
    powershell -ExecutionPolicy Bypass -File tools\Fix-ProjectPath.ps1 -Destination D:\VR\FireSafety

.EXAMPLE
    # copy, then delete the old folder (asks for confirmation)
    powershell -ExecutionPolicy Bypass -File tools\Fix-ProjectPath.ps1 -RemoveSource
#>

[CmdletBinding()]
param(
    [string]$Destination = "C:\VR\FireSafety",
    [switch]$RemoveSource
)

$ErrorActionPreference = "Stop"

# The project root is the folder above this script.
$Source = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $Source "Assets")) -or -not (Test-Path (Join-Path $Source "ProjectSettings"))) {
    throw "Could not find Assets/ and ProjectSettings/ in '$Source'. Run this script from inside the project."
}

Write-Host ""
Write-Host "Source      : $Source ($($Source.Length) characters)"
Write-Host "Destination : $Destination ($($Destination.Length) characters)"
Write-Host ""

if ($Destination.Length -gt 60) {
    Write-Warning "The destination is still fairly long. Something like C:\VR\FireSafety is ideal."
}
if (Test-Path $Destination) {
    $existing = Get-ChildItem $Destination -Force | Select-Object -First 1
    if ($existing) { throw "'$Destination' already exists and is not empty. Choose another -Destination." }
}

New-Item -ItemType Directory -Path $Destination -Force | Out-Null

# robocopy returns 0-7 on success, 8+ on failure.
$robocopyArgs = @($Source, $Destination, "/E", "/NFL", "/NDL", "/NJH", "/NJS",
                  "/XD", "Library", "Temp", "obj", "Logs", "build", ".git", ".vs", ".idea",
                  "/XF", "*.csproj", "*.sln")
Write-Host "Copying project files (Library and caches are skipped)..."
& robocopy @robocopyArgs | Out-Null
$code = $LASTEXITCODE
if ($code -ge 8) { throw "robocopy failed with exit code $code." }

$required = @("Assets", "Packages", "ProjectSettings")
foreach ($folder in $required) {
    if (-not (Test-Path (Join-Path $Destination $folder))) {
        throw "Copy finished but '$folder' is missing from the destination."
    }
}
if (-not (Test-Path (Join-Path $Destination "Assets\Scenes\FireSafetyTrainer.unity"))) {
    throw "Copy finished but the training scene is missing from the destination."
}

$worstCase = $Destination.Length + 145
Write-Host ""
Write-Host "Copied. Longest package path from the new location: about $worstCase characters (limit 260)." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Close Unity completely."
Write-Host "  2. Open the project at: $Destination"
Write-Host "  3. If you opened the new location before and it failed, delete '$Destination\Library' first."
Write-Host "  4. Open Assets/Scenes/FireSafetyTrainer.unity and press Play."
Write-Host ""

if ($RemoveSource) {
    Write-Host "The old folder can now be deleted:" -ForegroundColor Yellow
    Write-Host "  $Source"
    $answer = Read-Host "Delete it now? Type YES to confirm"
    if ($answer -eq "YES") {
        Remove-Item -LiteralPath $Source -Recurse -Force
        Write-Host "Deleted the old folder." -ForegroundColor Green
    } else {
        Write-Host "Left the old folder in place."
    }
}
