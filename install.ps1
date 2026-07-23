<#
.SYNOPSIS
    Install the cq-design skill into the Claude Code personal skills directory.

.DESCRIPTION
    Copies the skill into $env:CLAUDE_SKILLS_DIR\cq-design (default
    $HOME\.claude\skills\cq-design) and provisions its Python environment with
    'uv sync'. Use -Link to symlink the repo instead of copying, or -Uninstall
    to remove the installed skill.

.PARAMETER Dest
    Override the skills directory.

.PARAMETER Link
    Symlink the repo instead of copying.

.PARAMETER Uninstall
    Remove the installed skill and exit.

.EXAMPLE
    ./install.ps1
    ./install.ps1 -Link
    ./install.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [string]$Dest,
    [switch]$Link,
    [switch]$Uninstall,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) { Get-Help $PSCommandPath -Detailed; exit 0 }

$SkillName = "cq-design"
$RepoRoot = Split-Path -Parent (Resolve-Path $PSCommandPath)

$Excludes = @(
    ".claude", "info", "openspec", "tests", "src/.fossil", "src/_pycache_",
    ".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".cocoindex_code", ".sentrux", ".playwright-mcp",
    ".vscode", "build", "BUILD_PLAN.json", ".fossil", ".codegraph",
    "evals"
)

$SkillsDir = if ($Dest) { $Dest }
    elseif ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR }
    else { Join-Path $HOME ".claude\skills" }
$Destination = Join-Path $SkillsDir $SkillName

if ($Uninstall) {
    if (Test-Path $Destination) {
        Remove-Item -Recurse -Force $Destination
        Write-Host "Removed $Destination"
    } else {
        Write-Host "Nothing to remove at $Destination"
    }
    exit 0
}

# Preflight before touching the skills directory.
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "'uv' is not on PATH. Install it from https://docs.astral.sh/uv/ and re-run."
    exit 1
}

New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null

if ($Link) {
    if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
    try {
        New-Item -ItemType SymbolicLink -Path $Destination -Target $RepoRoot | Out-Null
    } catch {
        Write-Error "Failed to create symlink at $Destination. Enable Developer Mode or run as administrator. ($_)"
        exit 1
    }
    Write-Host "Linked $Destination -> $RepoRoot"
} else {
    if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Get-ChildItem -LiteralPath $RepoRoot -Force | Where-Object {
        $Excludes -notcontains $_.Name
    } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
    # Prune nested __pycache__ directories the top-level filter cannot catch.
    Get-ChildItem -LiteralPath $Destination -Recurse -Force -Directory -Filter "__pycache__" |
        ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
    Write-Host "Copied skill to $Destination"
}

Write-Host "Provisioning environment with 'uv sync'..."
uv sync --project $Destination
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. cq-design installed at $Destination"
