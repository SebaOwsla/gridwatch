param(
    [Parameter(Mandatory = $true)]
    [string]$LocalAddress,
    [Parameter(Mandatory = $true)]
    [string]$RemoteSubnet
)

$ErrorActionPreference = 'Stop'
$ruleName = 'GridWatch-Demo-LAN-8080'
$resultPath = Join-Path $PSScriptRoot '.firewall-result.txt'

trap {
    ($_ | Out-String) | Set-Content -LiteralPath $resultPath -Encoding UTF8
    exit 1
}

if (-not (Get-NetIPAddress -AddressFamily IPv4 -IPAddress $LocalAddress -ErrorAction SilentlyContinue)) {
    throw "La IP $LocalAddress no está asignada a este equipo."
}

$existingRule = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if ($existingRule) {
    $existingPort = $existingRule | Get-NetFirewallPortFilter
    $existingAddress = $existingRule | Get-NetFirewallAddressFilter
    $existingLocalMatches = @($existingAddress.LocalAddress) | Where-Object {
        $_ -eq $LocalAddress -or $_ -eq "$LocalAddress-$LocalAddress"
    }
    if ($existingRule.Action -ne 'Allow' -or $existingPort.LocalPort -ne '8080' -or
        -not $existingLocalMatches -or $existingAddress.RemoteAddress -ne $RemoteSubnet) {
        $existingRule | Remove-NetFirewallRule
        $existingRule = $null
    }
}

if (-not $existingRule) {
    New-NetFirewallRule `
        -Name $ruleName `
        -DisplayName 'GridWatch Demo LAN (TCP 8080)' `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalAddress $LocalAddress `
        -LocalPort 8080 `
        -RemoteAddress $RemoteSubnet `
        -Profile Any | Out-Null
}

$rule = Get-NetFirewallRule -Name $ruleName
$port = $rule | Get-NetFirewallPortFilter
$address = $rule | Get-NetFirewallAddressFilter
$localMatches = @($address.LocalAddress) | Where-Object {
    $_ -eq $LocalAddress -or $_ -eq "$LocalAddress-$LocalAddress"
}
if ($rule.Action -ne 'Allow' -or $port.LocalPort -ne '8080' -or
    -not $localMatches -or $address.RemoteAddress -ne $RemoteSubnet) {
    throw 'La regla existente de GridWatch no coincide con la configuración solicitada.'
}

"Regla activa: TCP 8080 en $LocalAddress desde $RemoteSubnet" |
    Set-Content -LiteralPath $resultPath -Encoding UTF8
Write-Output "Regla activa: TCP 8080 en $LocalAddress desde $RemoteSubnet"
