param(
    [string]$PythonVersion = "3.10",
    [string]$RuntimePath,
    [switch]$DisableUvFallback,
    [switch]$SkipInstall,
    [switch]$InstallStructure,
    [switch]$InstallSurya,
    [switch]$InstallAll
)

$ErrorActionPreference = "Stop"
if (Get-Variable PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$SkillRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$AgentsSkillsRoot = Join-Path $HOME ".agents\skills"
if (Test-Path $AgentsSkillsRoot) {
    $resolvedAgentsSkillsRoot = (Resolve-Path $AgentsSkillsRoot).Path.TrimEnd('\')
    $normalizedSkillRoot = $SkillRoot.TrimEnd('\')
    if ($normalizedSkillRoot.Equals($resolvedAgentsSkillsRoot, [System.StringComparison]::OrdinalIgnoreCase) -or
        $normalizedSkillRoot.StartsWith("$resolvedAgentsSkillsRoot\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to set up a Codex skill under $resolvedAgentsSkillsRoot. Install under $HOME\.codex\skills instead."
    }
}

function Resolve-Runtime-Path {
    if ($RuntimePath) {
        return $RuntimePath
    }
    if ($env:MOONSHOTNOTE_OCR_RUNTIME) {
        return $env:MOONSHOTNOTE_OCR_RUNTIME
    }
    $relayHome = if ($env:MOONSHOT_RELAY_HOME) { $env:MOONSHOT_RELAY_HOME } else { Join-Path $HOME ".moonshot-relay" }
    return (Join-Path $relayHome "runtimes\moonshotnote-ocr-py312")
}

$VenvPath = Resolve-Runtime-Path
$VenvParent = Split-Path -Parent $VenvPath
if (-not (Test-Path $VenvParent)) {
    New-Item -ItemType Directory -Path $VenvParent -Force | Out-Null
}
Write-Host "Using shared OCR runtime at $VenvPath"

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE`: $FilePath $($Arguments -join ' ')"
    }
}

function Get-Python-Info {
    param(
        [string]$Exe,
        [string]$VersionArg
    )

    $code = "import json, platform, sys; print(json.dumps({'version': f'{sys.version_info.major}.{sys.version_info.minor}', 'arch': platform.architecture()[0], 'executable': sys.executable}))"
    try {
        if ($VersionArg) {
            $raw = & $Exe $VersionArg -c $code 2>$null
        } else {
            $raw = & $Exe -c $code 2>$null
        }
        if ($LASTEXITCODE -ne 0 -or -not $raw) {
            return $null
        }
        return $raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Resolve-Python {
    $versions = @($PythonVersion, "3.12", "3.11", "3.10") | Select-Object -Unique
    $candidates = @()
    foreach ($version in $versions) {
        $candidates += ,@("py", "-$version")
    }
    $candidates += ,@("python", $null)
    $candidates += ,@("python3", $null)

    foreach ($candidate in $candidates) {
        $exe = $candidate[0]
        $arg = $candidate[1]
        $info = Get-Python-Info -Exe $exe -VersionArg $arg
        if (-not $info) {
            continue
        }
        if ($info.arch -ne "64bit") {
            Write-Host "Skipping $($info.executable): OCR dependencies require 64-bit Python, found $($info.arch)."
            continue
        }
        if ($info.version -notin @("3.10", "3.11", "3.12")) {
            Write-Host "Skipping $($info.executable): expected Python 3.10, 3.11, or 3.12, found $($info.version)."
            continue
        }
        return @($exe, $arg, $info.executable, $info.version)
    }

    if (-not $DisableUvFallback -and (Get-Command uv -ErrorAction SilentlyContinue)) {
        foreach ($version in @("3.12", "3.11", "3.10")) {
            $found = (& uv python find --managed-python --no-project $version 2>$null | Select-Object -First 1)
            if (-not $found) {
                Write-Host "Installing Python $version with uv because no compatible system Python was found."
                Invoke-Checked -FilePath "uv" -Arguments @("python", "install", $version)
                $found = (& uv python find --managed-python --no-project $version 2>$null | Select-Object -First 1)
            }
            if ($found) {
                $info = Get-Python-Info -Exe $found -VersionArg $null
                if ($info -and $info.arch -eq "64bit" -and $info.version -in @("3.10", "3.11", "3.12")) {
                    return @($found, $null, $info.executable, $info.version)
                }
            }
        }
    }

    throw "No compatible Python found. Install 64-bit Python 3.10, 3.11, or 3.12, then rerun setup.ps1."
}

$python = Resolve-Python
$pythonExe = $python[0]
$pythonArg = $python[1]
$selectedPythonPath = $python[2]
$selectedPythonVersion = $python[3]

Write-Host "Using Python $selectedPythonVersion at $selectedPythonPath"

if (Test-Path $VenvPath) {
    $existingPython = Join-Path $VenvPath "Scripts\python.exe"
    $existingInfo = if (Test-Path $existingPython) { Get-Python-Info -Exe $existingPython -VersionArg $null } else { $null }
    if (-not $existingInfo -or $existingInfo.arch -ne "64bit" -or $existingInfo.version -notin @("3.10", "3.11", "3.12")) {
        Write-Host "Removing incompatible OCR virtual environment: $VenvPath"
        Remove-Item -LiteralPath $VenvPath -Recurse -Force
    }
}

if (-not (Test-Path $VenvPath)) {
    if ($pythonArg) {
        Invoke-Checked -FilePath $pythonExe -Arguments @($pythonArg, "-m", "venv", $VenvPath)
    } else {
        Invoke-Checked -FilePath $pythonExe -Arguments @("-m", "venv", $VenvPath)
    }
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment python was not created at $VenvPython"
}

Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")

if (-not $SkipInstall) {
    $requirements = Join-Path $PSScriptRoot "requirements.txt"
    Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--only-binary=:all:", "-r", $requirements)
    if ($InstallStructure -or $InstallAll) {
        $structureRequirements = Join-Path $PSScriptRoot "requirements-structure.txt"
        Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--only-binary=:all:", "-r", $structureRequirements)
    }
    if ($InstallSurya -or $InstallAll) {
        $suryaRequirements = Join-Path $PSScriptRoot "requirements-surya.txt"
        Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--only-binary=:all:", "-r", $suryaRequirements)
    }
}

Invoke-Checked -FilePath $VenvPython -Arguments @((Join-Path $PSScriptRoot "doctor.py"))
