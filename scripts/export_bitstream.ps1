# scripts/export_bitstream.ps1
# Copies latest Vivado outputs into their tracked locations.
# Run from repo root: .\scripts\export_bitstream.ps1

$repo    = Split-Path $PSScriptRoot -Parent
$proj    = "$repo\vivado\proj\ntt_accel"
$impl    = "$proj\ntt_accel.runs\impl_1"
$hwh     = "$proj\ntt_accel.gen\sources_1\bd\ntt_bd\hw_handoff"
$dest    = "$repo\bitstream"

$copies = @(
    @{ Src = "$impl\ntt_bd_wrapper.bit"; Dst = "$dest\ntt_bd.bit" },
    @{ Src = "$hwh\ntt_bd.hwh";          Dst = "$dest\ntt_bd.hwh" },
    @{ Src = "$proj\ntt_bd.tcl";         Dst = "$repo\vivado\ntt_bd.tcl" }
)

foreach ($f in $copies) {
    if (-not (Test-Path $f.Src)) {
        Write-Error "Not found: $($f.Src)"; exit 1
    }
    Copy-Item $f.Src $f.Dst -Force
    Write-Host "Copied: $(Split-Path $f.Src -Leaf) -> bitstream\"
}

Write-Host "Done."
