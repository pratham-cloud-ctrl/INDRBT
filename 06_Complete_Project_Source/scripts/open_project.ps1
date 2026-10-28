param(
    [ValidateSet('Home', 'Viewer', 'FreeCAD', 'PCB')]
    [string]$View = 'Home',
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path

function Find-FreeCAD {
    $command = Get-Command FreeCAD.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $uninstallRoots = @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($registryRoot in $uninstallRoots) {
        foreach ($entry in Get-ItemProperty -Path $registryRoot -ErrorAction SilentlyContinue) {
            if ($entry.DisplayName -like 'FreeCAD*') {
                if ($entry.InstallLocation) {
                    $candidate = Join-Path $entry.InstallLocation 'bin\FreeCAD.exe'
                    if (Test-Path -LiteralPath $candidate) { return $candidate }
                }
                if ($entry.DisplayIcon) {
                    $candidate = ($entry.DisplayIcon -replace ',\d+$', '').Trim('"')
                    if (Test-Path -LiteralPath $candidate) { return $candidate }
                }
            }
        }
    }
    throw 'FreeCAD was not found. Open 01_CAD_Models\FreeCAD\indrbt_home.FCStd through FreeCAD File > Open.'
}

function Find-Browser {
    $candidates = @(
        (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw 'Chrome or Edge was not found. Open START_HERE.html in your web browser.'
}

function Find-PCBEditor {
    $command = Get-Command pcbnew.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $uninstallRoots = @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($registryRoot in $uninstallRoots) {
        foreach ($entry in Get-ItemProperty -Path $registryRoot -ErrorAction SilentlyContinue) {
            if ($entry.DisplayName -like 'KiCad*' -and $entry.InstallLocation) {
                $candidate = Join-Path $entry.InstallLocation 'bin\pcbnew.exe'
                if (Test-Path -LiteralPath $candidate) { return $candidate }
            }
        }
    }
    throw 'KiCad PCB Editor was not found. Open 04_Electronics\joint_interface.kicad_pcb through KiCad.'
}

try {
    if ($View -eq 'PCB') {
        $application = Find-PCBEditor
        $document = Join-Path $projectRoot '04_Electronics\joint_interface.kicad_pcb'
    } elseif ($View -eq 'FreeCAD') {
        $application = Find-FreeCAD
        $document = Join-Path $projectRoot '01_CAD_Models\FreeCAD\indrbt_home.FCStd'
    } else {
        $application = Find-Browser
        $relative = if ($View -eq 'Viewer') { '02_Simulation_and_Animation\Interactive_3D_Viewer.html' } else { 'START_HERE.html' }
        $document = Join-Path $projectRoot $relative
    }
    if (-not (Test-Path -LiteralPath $document)) { throw "Project file is missing: $document" }
    if ($CheckOnly) {
        @{ view = $View; application = $application; document = $document; status = 'PASS' } | ConvertTo-Json -Compress
    } else {
        Start-Process -FilePath $application -ArgumentList ('"' + $document + '"')
    }
} catch {
    Write-Host $_.Exception.Message
    if (-not $CheckOnly) { Read-Host 'Press Enter to close' }
    exit 1
}
