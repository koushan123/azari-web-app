[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupPath,
    [Parameter(Mandatory = $true)]
    [string]$TargetDatabase
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$resolvedBackup = (Resolve-Path -LiteralPath $BackupPath).Path
if ($TargetDatabase -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
    throw "TargetDatabase must be a simple PostgreSQL identifier."
}

Push-Location $repositoryRoot
try {
    $databaseUserOutput = docker compose exec -T db printenv POSTGRES_USER
    if ($LASTEXITCODE -ne 0 -or $null -eq $databaseUserOutput) {
        throw "The PostgreSQL Compose service is not available."
    }
    $primaryDatabaseOutput = docker compose exec -T db printenv POSTGRES_DB
    if ($LASTEXITCODE -ne 0 -or $null -eq $primaryDatabaseOutput) {
        throw "The PostgreSQL Compose service is not available."
    }
    $databaseUser = $databaseUserOutput.Trim()
    $primaryDatabase = $primaryDatabaseOutput.Trim()
    if ($TargetDatabase -eq $primaryDatabase) {
        throw "Refusing to restore over the active database. Restore into a new database first."
    }

    $existing = docker compose exec -T db psql --username $databaseUser --dbname $primaryDatabase --tuples-only --no-align --command "SELECT 1 FROM pg_database WHERE datname = '$TargetDatabase'"
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect PostgreSQL databases." }
    if ($null -ne $existing -and $existing.Trim() -eq "1") {
        throw "Target database '$TargetDatabase' already exists."
    }

    $containerPath = "/tmp/azari-restore-$TargetDatabase.sql"
    docker compose cp $resolvedBackup "db:$containerPath"
    if ($LASTEXITCODE -ne 0) { throw "Copying the backup into the container failed." }
    try {
        docker compose exec -T db createdb --username $databaseUser $TargetDatabase
        if ($LASTEXITCODE -ne 0) { throw "Creating target database failed." }
        docker compose exec -T db psql --username $databaseUser --dbname $TargetDatabase --set ON_ERROR_STOP=1 --single-transaction --file $containerPath
        if ($LASTEXITCODE -ne 0) { throw "Restoring the backup failed; the target was left for inspection." }
    }
    finally {
        docker compose exec -T db rm -f $containerPath 2>$null
    }
}
finally {
    Pop-Location
}

Write-Host "Restore completed into disposable/new database '$TargetDatabase'."
