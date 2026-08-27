[CmdletBinding()]
param(
    [string]$CertificateSubject = "CN=Student Learning Map Builder Internal Publisher",
    [ValidateRange(1, 10)]
    [int]$ValidYears = 5,
    [string]$ApplicationDirectory
)

$ErrorActionPreference = "Stop"

$curriculumRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $ApplicationDirectory) {
    $ApplicationDirectory = Join-Path $curriculumRoot "output\apps\student-learning-map-builder\Student Learning Map Builder"
}

$applicationDirectoryPath = (Resolve-Path -LiteralPath $ApplicationDirectory).Path
$executable = Join-Path $applicationDirectoryPath "Student Learning Map Builder.exe"
$publicCertificate = Join-Path $applicationDirectoryPath "Student Learning Map Builder Publisher.cer"

if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "The packaged application was not found at $executable. Build it before signing."
}

$codeSigningOid = "1.3.6.1.5.5.7.3.3"
$now = Get-Date
$certificate = Get-ChildItem Cert:\CurrentUser\My |
    Where-Object {
        $_.Subject -eq $CertificateSubject -and
        $_.HasPrivateKey -and
        $_.NotAfter -gt $now -and
        $_.EnhancedKeyUsageList.ObjectId -contains $codeSigningOid
    } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if (-not $certificate) {
    $certificate = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $CertificateSubject `
        -FriendlyName "Student Learning Map Builder Internal Code Signing" `
        -CertStoreLocation Cert:\CurrentUser\My `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -HashAlgorithm SHA256 `
        -KeyExportPolicy NonExportable `
        -NotAfter $now.AddYears($ValidYears)

    Write-Host "Created internal code-signing certificate $($certificate.Thumbprint)."
}
else {
    Write-Host "Using internal code-signing certificate $($certificate.Thumbprint)."
}

Export-Certificate -Cert $certificate -FilePath $publicCertificate -Force | Out-Null

$signature = Set-AuthenticodeSignature `
    -LiteralPath $executable `
    -Certificate $certificate `
    -HashAlgorithm SHA256

if (-not $signature.SignerCertificate -or $signature.SignerCertificate.Thumbprint -ne $certificate.Thumbprint) {
    throw "The executable does not contain the expected signature."
}

Write-Host "Signed $executable"
Write-Host "Exported public certificate to $publicCertificate"
if ($signature.Status -ne "Valid") {
    Write-Warning "The signature is present but is not trusted on this computer. This is expected until IT explicitly deploys the public certificate."
}
Write-Host "Certificate expires $($certificate.NotAfter.ToString('yyyy-MM-dd'))."
