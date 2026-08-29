[CmdletBinding()]
param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $repositoryRoot "backups\db"
}
$resolvedOutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($resolvedOutputDirectory) | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
$fileName = "azari-$timestamp.sql"
$destination = Join-Path $resolvedOutputDirectory $fileName
$containerPath = "/tmp/azari-$timestamp.sql"

Push-Location $repositoryRoot
try {
    $databaseUserOutput = docker compose exec -T db printenv POSTGRES_USER
    if ($LASTEXITCODE -ne 0 -or $null -eq $databaseUserOutput) {
        throw "The PostgreSQL Compose service is not available."
    }
    $databaseNameOutput = docker compose exec -T db printenv POSTGRES_DB
    if ($LASTEXITCODE -ne 0 -or $null -eq $databaseNameOutput) {
        throw "The PostgreSQL Compose service is not available."
    }
    $databaseUser = $databaseUserOutput.Trim()
    $databaseName = $databaseNameOutput.Trim()
    docker compose exec -T db pg_dump --username $databaseUser --dbname $databaseName --format plain --no-owner --no-privileges --file $containerPath
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed." }
    docker compose cp "db:$containerPath" $destination
    if ($LASTEXITCODE -ne 0) { throw "Copying the backup from the container failed." }
}
finally {
    docker compose exec -T db rm -f $containerPath 2>$null
    Pop-Location
}

Write-Output $destination
