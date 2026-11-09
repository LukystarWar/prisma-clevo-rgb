$ErrorActionPreference = 'Stop'
$src = Join-Path $PSScriptRoot 'ColorCycle.ps1'
$dir = 'C:\Program Files\KeyboardColorCycle'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Copy-Item $src (Join-Path $dir 'ColorCycle.ps1') -Force

$xml = @'
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Keeps the keyboard LEDs cycling through colors continuously: starts at boot, at logon and after sleep, and keeps running in the background.</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger><Enabled>true</Enabled><Delay>PT20S</Delay></BootTrigger>
    <LogonTrigger><Enabled>true</Enabled><Delay>PT30S</Delay></LogonTrigger>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Delay>PT5S</Delay>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="System"&gt;&lt;Select Path="System"&gt;*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "C:\Program Files\KeyboardColorCycle\ColorCycle.ps1"</Arguments>
    </Exec>
  </Actions>
</Task>
'@
Register-ScheduledTask -TaskName 'KeyboardColorCycle' -Xml $xml -Force | Out-Null

# The script now loops forever (it IS the color-cycle effect), so unlike before we
# don't wait for it to finish - we just confirm it started and is still running.
Start-ScheduledTask -TaskName 'KeyboardColorCycle'
Start-Sleep -Seconds 8

$t = Get-ScheduledTask -TaskName 'KeyboardColorCycle'
$i = $t | Get-ScheduledTaskInfo
"Estado: $($t.State) | LastRun: $($i.LastRunTime) | LastResult: $($i.LastTaskResult)"
"Gatilhos: " + (($t.Triggers | ForEach-Object { $_.CimClass.CimClassName }) -join ', ')
"--- last-run.log ---"
Get-Content (Join-Path $dir 'last-run.log')
"--- permissoes da pasta ---"
(Get-Acl $dir).Access | Select-Object IdentityReference,FileSystemRights | Format-Table -AutoSize | Out-String -Width 120
