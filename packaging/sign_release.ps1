[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$CertificateThumbprint,

    [string]$TimestampServer = "http://timestamp.digicert.com",

    [string[]]$Files = @(
        "dist\QQNotebookExporter\QQNotebookExporter.exe",
        "release\QQNotebookExporter-Setup-0.1.0.exe"
    )
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$certificate = Get-Item "Cert:\CurrentUser\My\$CertificateThumbprint"
if (-not $certificate.HasPrivateKey) {
    throw "The code-signing certificate has no private key."
}
if ($certificate.EnhancedKeyUsageList.ObjectId.Value -notcontains "1.3.6.1.5.5.7.3.3") {
    throw "The certificate is not valid for code signing."
}

foreach ($relativePath in $Files) {
    $path = Join-Path $root $relativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Signing target does not exist: $path"
    }

    Write-Host "Signing $path"
    $result = Set-AuthenticodeSignature `
        -FilePath $path `
        -Certificate $certificate `
        -TimestampServer $TimestampServer
    if ($result.Status -notin @("Valid", "UnknownError", "NotTrusted")) {
        throw "Signing failed for ${path}: $($result.Status) $($result.StatusMessage)"
    }

    $verification = Get-AuthenticodeSignature -FilePath $path
    Write-Host "  Status: $($verification.Status)"
    Write-Host "  Signer: $($verification.SignerCertificate.Subject)"
    Write-Host "  Timestamp: $($verification.TimeStamperCertificate.NotBefore)"
}
