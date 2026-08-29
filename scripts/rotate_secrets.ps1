[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repositoryRoot ".env"

if (-not (Test-Path -LiteralPath $envPath -PathType Leaf)) {
    throw "Missing .env. Copy .env.example and configure it first."
}

function New-UrlSafeSecret([int]$ByteCount) {
    $bytes = [byte[]]::new($ByteCount)
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$lines = [System.IO.File]::ReadAllLines($envPath)
function Get-EnvValue([string]$Name) {
    $prefix = "$Name="
    $line = $lines | Where-Object { $_.StartsWith($prefix) } | Select-Object -First 1
    if ($null -eq $line) {
        throw "Required setting $Name is missing from .env."
    }
    return $line.Substring($prefix.Length)
}

$databaseUser = Get-EnvValue "POSTGRES_USER"
$databaseName = Get-EnvValue "POSTGRES_DB"
$databaseUrl = Get-EnvValue "DATABASE_URL"
$null = Get-EnvValue "POSTGRES_PASSWORD"
$null = Get-EnvValue "JWT_SECRET"
if ($databaseUser -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
    throw "POSTGRES_USER must be a simple PostgreSQL identifier for this script."
}
if ($databaseName -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
    throw "POSTGRES_DB must be a simple PostgreSQL identifier for this script."
}
if ($databaseUrl -notmatch '^(?<prefix>postgresql\+psycopg://[^:]+:)[^@]*(?<suffix>@.+)$') {
    throw "DATABASE_URL must use postgresql+psycopg://user:password@host/database."
}

$newDatabasePassword = New-UrlSafeSecret 48
$newJwtSecret = New-UrlSafeSecret 64
$newDatabaseUrl = $Matches.prefix + $newDatabasePassword + $Matches.suffix
$replacementValues = @{
    "POSTGRES_PASSWORD" = $newDatabasePassword
    "JWT_SECRET" = $newJwtSecret
    "DATABASE_URL" = $newDatabaseUrl
}
$updatedLines = foreach ($line in $lines) {
    $matched = $false
    foreach ($name in $replacementValues.Keys) {
        if ($line.StartsWith("$name=")) {
            "$name=$($replacementValues[$name])"
            $matched = $true
            break
        }
    }
    if (-not $matched) { $line }
}

$temporaryPath = "$envPath.rotation.tmp"
[System.IO.File]::WriteAllLines($temporaryPath, $updatedLines)
try {
    Push-Location $repositoryRoot
    try {
        $escapedPassword = $newDatabasePassword.Replace("'", "''")
        $sql = "ALTER ROLE `"$databaseUser`" WITH PASSWORD '$escapedPassword';"
        $sql | docker compose exec -T db psql --set ON_ERROR_STOP=1 --username $databaseUser --dbname $databaseName
        if ($LASTEXITCODE -ne 0) { throw "PostgreSQL rejected the role-password update." }
    }
    finally {
        Pop-Location
    }
    Move-Item -LiteralPath $temporaryPath -Destination $envPath -Force
}
finally {
    if (Test-Path -LiteralPath $temporaryPath) {
        Remove-Item -LiteralPath $temporaryPath -Force
    }
}

Write-Host "PostgreSQL and .env secrets were rotated without printing secret values."
Write-Host "Recreate the backend now: docker compose up -d --force-recreate backend"
