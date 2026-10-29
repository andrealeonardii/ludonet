$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot "python\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Ambiente Python mancante. Esegui: python -m venv python\.venv"
}

$goCommand = Get-Command go.exe -ErrorAction SilentlyContinue
if ($goCommand) {
    $go = $goCommand.Source
} else {
    $go = Join-Path $env:LOCALAPPDATA "Programs\Go\go\bin\go.exe"
}
if (-not (Test-Path $go)) {
    throw "Go non trovato."
}

$gppCommand = Get-Command g++.exe -ErrorAction SilentlyContinue
if ($gppCommand) {
    $gpp = $gppCommand.Source
} else {
    $gppCandidates = @(
        "C:\msys64\ucrt64\bin\g++.exe",
        "C:\msys64\mingw64\bin\g++.exe"
    )
    $gpp = $gppCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $gpp) {
    $gpp = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages") -Filter "g++.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
}
if (-not $gpp) {
    throw "g++ non trovato."
}
$gppDirectory = Split-Path $gpp -Parent
if (($env:Path -split ';') -notcontains $gppDirectory) {
    $env:Path = "$gppDirectory;$env:Path"
}

$pythonPort = if ($env:NICKGAME_PY_PORT) { $env:NICKGAME_PY_PORT } else { "50010" }
$goPort = if ($env:NICKGAME_GO_PORT) { $env:NICKGAME_GO_PORT } else { "50011" }
if ($pythonPort -eq $goPort) {
    throw "Flask e Go devono usare due porte diverse."
}

$bindHost = if ($env:NICKGAME_HOST) { $env:NICKGAME_HOST } else { "0.0.0.0" }
$publicHost = $env:NICKGAME_PUBLIC_HOST
if (-not $publicHost) {
    $publicHost = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
        Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
        ForEach-Object { $_.IPv4Address.IPAddress } |
        Select-Object -First 1
}
if (-not $publicHost) {
    throw "Indirizzo IPv4 LAN non trovato. Imposta NICKGAME_PUBLIC_HOST manualmente."
}

$env:NICKGAME_GO_PORT = $goPort
$env:NICKGAME_GO_HOST = $bindHost
$env:NICKGAME_GO_HTTP_URL = "http://127.0.0.1:$goPort"
$env:NICKGAME_GO_WS_URL = "ws://${publicHost}:$goPort"

& $python -c @"
import socket
for value in ('$pythonPort', '$goPort'):
    try:
        port = int(value)
        with socket.socket() as connection:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            connection.bind(('$bindHost', port))
    except (OSError, ValueError, OverflowError):
        raise SystemExit(f'Porta {value} occupata o non valida.')
"@
if ($LASTEXITCODE -ne 0) {
    throw "Controllo delle porte fallito."
}

New-Item -ItemType Directory -Force -Path "cpp\build", "go\build" | Out-Null

& $gpp -std=c++17 -Wall -Wextra -Werror -O2 -static -static-libgcc -static-libstdc++ `
    "cpp\main.cpp" "cpp\economia.cpp" -o "cpp\build\nickgame-economia.exe"
if ($LASTEXITCODE -ne 0) {
    throw "Compilazione del modulo economia fallita."
}

& $gpp -std=c++17 -Wall -Wextra -Werror -O2 -static -static-libgcc -static-libstdc++ `
    "cpp\bot\main.cpp" "cpp\bot\rete_forza4.cpp" -o "cpp\build\nickgame-bot.exe"
if ($LASTEXITCODE -ne 0) {
    throw "Compilazione del bot fallita."
}

Push-Location "python"
try {
    & $python -c "import app"
    if ($LASTEXITCODE -ne 0) {
        throw "Inizializzazione Flask fallita."
    }
} finally {
    Pop-Location
}

Push-Location "go"
try {
    & $go build -o "build\nickgame-sync.exe" .
    if ($LASTEXITCODE -ne 0) {
        throw "Compilazione del servizio Go fallita."
    }
} finally {
    Pop-Location
}

$goProcess = $null
$flaskProcess = $null
try {
    $goProcess = Start-Process -FilePath (Join-Path $PSScriptRoot "go\build\nickgame-sync.exe") `
        -WorkingDirectory (Join-Path $PSScriptRoot "go") -PassThru

    $flaskArguments = @(
        "-m", "flask", "--app", "app", "run",
        "--host", $bindHost, "--port", $pythonPort, "--no-reload"
    )
    $flaskProcess = Start-Process -FilePath $python -ArgumentList $flaskArguments `
        -WorkingDirectory (Join-Path $PSScriptRoot "python") -PassThru

    Write-Host "Nickgame su questo PC: http://127.0.0.1:$pythonPort"
    Write-Host "Nickgame sulla Wi-Fi: http://${publicHost}:$pythonPort"
    Write-Host "Per fermare i server, chiudi questa finestra oppure esegui:"
    Write-Host "Stop-Process -Id $($goProcess.Id),$($flaskProcess.Id)"

    while (-not $goProcess.HasExited -and -not $flaskProcess.HasExited) {
        Start-Sleep -Milliseconds 500
        $goProcess.Refresh()
        $flaskProcess.Refresh()
    }
} finally {
    foreach ($process in @($goProcess, $flaskProcess)) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}
