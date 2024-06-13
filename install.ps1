param (
    [string]$repoUrl
)

# Define variables
$repoDir = $PSScriptRoot
$poetryInstallUrl = "https://install.python-poetry.org"

# Function to check if a command exists
function Command-Exists {
    param (
        [string]$command
    )
    $null -ne (Get-Command $command -ErrorAction SilentlyContinue)
}

# Clone the repository
Write-Output "Cloning the repository..."
if (-Not (Test-Path "$repoDir\invisible-hand")) {
    git clone $repoUrl "$repoDir\invisible-hand"
} else {
    Write-Output "Directory already exists. Skipping clone."
}

# Navigate to the repository directory
Set-Location "$repoDir\invisible-hand"

# Define possible locations
$possible_game_locations = @("C:\Program Files (x86)\Origin\Battlefield V\bfv.exe", "D:\Program Files (x86)\Origin\Battlefield V\bfv.exe", "D:\Program Files\Origin\Battlefield V\bfv.exe")
$possible_tesseract_locations = @("C:\Program Files\Tesseract-OCR\tesseract.exe", "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe", "D:\Tesseract-OCR\tesseract.exe")

# Function to find a file from a list of possible locations
function Find-File($possibleLocations) {
    foreach ($location in $possibleLocations) {
        if (Test-Path $location) {
            return $location
        }
    }
    return $null
}

# Prompt user for configuration values
$server_name = Read-Host "Enter server name"
$bot_name = Read-Host "Enter bot name"
$ping_threshold = Read-Host "Enter ping threshold"

# Find or prompt for game location
$game_location = Find-File $possible_game_locations
if (-not $game_location) {
    $game_location = Read-Host "Game location not found. Enter game location (with raw string prefix r'')"
} else {
    Write-Host "Game location found at: $game_location"
}

# Find or prompt for tesseract location
$tesseract_location = Find-File $possible_tesseract_locations
if (-not $tesseract_location) {
    $tesseract_location = Read-Host "Tesseract location not found. Enter tesseract location (with raw string prefix r'')"
} else {
    Write-Host "Tesseract location found at: $tesseract_location"
}

$DB_NAME = Read-Host "Enter DB name"
$DB_USER = Read-Host "Enter DB user"
$DB_PASSWORD = Read-Host "Enter DB password"
$DB_HOST = Read-Host "Enter DB host"
$DB_PORT = Read-Host "Enter DB port"

# Create the config.py file with user inputs
$configContent = @"
'''
This is the configuration file for server name, user name etc.
'''
server_name = "$server_name"
bot_name = "$bot_name"
ping_threshold = $ping_threshold
game_location = r"$game_location"
game_window_name = "Battlefield™ V"
tesseract_location = r"$tesseract_location"

DB_NAME = "$DB_NAME"
DB_USER = "$DB_USER"
DB_PASSWORD = "$DB_PASSWORD"
DB_HOST = "$DB_HOST"
DB_PORT = "$DB_PORT"
"@

# Write configuration to file
$configContent | Out-File -FilePath invisible-hand\config.py -Encoding utf8

# Check if Poetry is installed
if (-Not (Command-Exists "poetry")) {
    # Install Poetry
    Write-Output "Installing Poetry..."
    (Invoke-WebRequest -Uri $poetryInstallUrl -UseBasicParsing).Content | python -
    $env:Path += ";$env:USERPROFILE\.poetry\bin"
    # Refresh the environment
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
}

# Install dependencies
Write-Output "Installing dependencies with Poetry..."
poetry install --no-root

# Start the program
Write-Output "Starting the program..."
poetry run python src/invisible-hand/main.py