#!/usr/bin/env pwsh
# Build script for Vostok Vault — produces dist\VostokVault.exe
#
# Usage:
#   pwsh build.ps1
#   pwsh build.ps1 -Clean   # remove dist/ and build/ first

param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Set-Location $ProjectRoot

if ($Clean) {
    Write-Host "Cleaning previous build output..."
    Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
}

Write-Host "Building VostokVault.exe..."
uv run pyinstaller vostok-vault.spec --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed (exit code $LASTEXITCODE)"
    exit 1
}

$exe = Join-Path $ProjectRoot "dist\VostokVault.exe"
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "Build complete: dist\VostokVault.exe ($size MB)"
} else {
    Write-Error "Build finished but VostokVault.exe not found"
    exit 1
}
