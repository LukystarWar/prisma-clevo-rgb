# Keeps the keyboard LEDs (left/mid/right zones) smoothly cycling through the rainbow.
# Run by the "KeyboardColorCycle" scheduled task. See last-run.log for status/errors.
#
# Why this sends raw colors in a loop instead of selecting the firmware's built-in
# "Cycle" effect (command 103, value 0x33010000): that mode-select command was tested
# on this hardware (Kb_Type 6) and had no visible effect by itself. Writing an RGB
# value straight to each zone (same call ClevoCo's own app uses for SetColor) DOES
# work reliably, confirmed visually zone-by-zone, so this script does the animation
# itself instead of relying on the EC's own cycle mode.

$ErrorActionPreference = 'Stop'
$log = Join-Path $PSScriptRoot 'last-run.log'
function Write-Log([string]$m) { "$(Get-Date -Format s)  $m" | Out-File -FilePath $log -Append -Encoding utf8 }

$RGB_KB_TYPES = 2, 6, 22    # Clevo Kb_Type values handled by the RGBKB class
$ZONES = @(0x00, 0xF0, 0xF1)  # Left, Mid, Right part codes used by RGBKB::SetColor
$STEP_DEGREES = 1          # hue increment per tick
$TICK_MS = 55              # ~ (360/STEP_DEGREES)*TICK_MS ms per full rainbow revolution

$dll = 'C:\Program Files (x86)\ControlCenter\InsydeDCHU.dll'

Remove-Item $log -ErrorAction SilentlyContinue
try {
    if (-not (Test-Path $dll)) { throw "DLL not found: $dll" }

    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class ClevoKb {
    [DllImport("kernel32", SetLastError=true, CharSet=CharSet.Unicode)] public static extern IntPtr LoadLibraryW(string p);
    [DllImport("InsydeDCHU.dll")] static extern int GetDCHU_Data_Integer(int command, ref int data);
    [DllImport("InsydeDCHU.dll")] static extern int GetDCHU_Data_Buffer(int command, byte[] buffer);
    [DllImport("InsydeDCHU.dll")] static extern int SetDCHU_Data(int command, byte[] buffer, int length);
    public static int GetKbType() {
        int d = 90;
        GetDCHU_Data_Integer(70, ref d);
        byte[] b = new byte[4096];
        GetDCHU_Data_Buffer(13, b);
        return b[15];
    }
    public static void SetZoneColor(int zonePart, byte r, byte g, byte b) {
        uint colorVal = ((uint)b << 16) | ((uint)r << 8) | g;
        uint payload = ((uint)zonePart << 24) + colorVal;
        SetDCHU_Data(103, BitConverter.GetBytes(payload), 4);
    }
}
'@

    if ([ClevoKb]::LoadLibraryW($dll) -eq [IntPtr]::Zero) {
        throw "LoadLibrary failed, error $([Runtime.InteropServices.Marshal]::GetLastWin32Error())"
    }

    # Never send colors to a keyboard this effect was not written for.
    $type = [ClevoKb]::GetKbType()
    Write-Log "Keyboard type: $type"
    if ($RGB_KB_TYPES -notcontains $type) { throw "Unsupported keyboard type: $type. Nothing was sent." }

    Write-Log "Color cycle started."

    function Get-RgbFromHue([double]$h) {
        $h = $h % 360
        $x = 1 - [math]::Abs((($h / 60) % 2) - 1)
        switch ([int][math]::Floor($h / 60)) {
            0 { $r = 1;  $g = $x; $b = 0 }
            1 { $r = $x; $g = 1;  $b = 0 }
            2 { $r = 0;  $g = 1;  $b = $x }
            3 { $r = 0;  $g = $x; $b = 1 }
            4 { $r = $x; $g = 0;  $b = 1 }
            default { $r = 1; $g = 0; $b = $x }
        }
        return [byte[]]@([byte]([math]::Round($r * 255)), [byte]([math]::Round($g * 255)), [byte]([math]::Round($b * 255)))
    }

    $hue = 0.0
    while ($true) {
        $rgb = Get-RgbFromHue $hue
        foreach ($zone in $ZONES) { [ClevoKb]::SetZoneColor($zone, $rgb[0], $rgb[1], $rgb[2]) }
        $hue = ($hue + $STEP_DEGREES) % 360
        Start-Sleep -Milliseconds $TICK_MS
    }
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    exit 1
}
