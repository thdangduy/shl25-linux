# SHL25 native K34 v5 standalone BusyBox ash / USB serial automated test.
# Does not change Windows drivers or any device partition. Only sends
# textual commands to the owner's already-authorized SHL25 Linux serial.
$ErrorActionPreference = 'Stop'
$serial = '356594053328037'
$log = 'C:\Users\Admin\Downloads\SHL25-Linux-Lab\Sharp-Checkpoint-20261107\SHL25_NATIVE_K34_BUSYBOX_V5_SERIAL_TEST.txt'
$entries = New-Object System.Collections.Generic.List[string]
$port = $null
$passed = $false
function Save([string]$value) {
  $entries.Add($value)
  Write-Output $value
}
function ReadUntil([string]$pattern,[int]$seconds) {
  $rx = ''
  $until = [DateTime]::UtcNow.AddSeconds($seconds)
  while([DateTime]::UtcNow -lt $until) {
    $chunk = $port.ReadExisting()
    if($chunk){$rx += $chunk}
    if($rx -match $pattern){break}
    Start-Sleep -Milliseconds 110
  }
  return $rx
}
function SendAndExpect([string]$command,[string]$pattern,[int]$seconds) {
  $port.Write($command+[char]10)
  $reply=ReadUntil $pattern $seconds
  Save ('COMMAND='+$command)
  Save ('RESPONSE='+$reply)
  if($reply -notmatch $pattern) {
    throw ('HOST_SERIAL_EXPECTATION_FAILED command='+$command+' regex='+$pattern)
  }
}
try {
  $dev = Get-PnpDevice -PresentOnly -ErrorAction Stop |
    Where-Object { $_.InstanceId -match 'VID_18D1&PID_0002' -and
      $_.InstanceId -match 'MI_00' -and $_.FriendlyName -match 'COM\d+' -and
      $_.Status -eq 'OK' } | Select-Object -First 1
  if(!$dev) {throw 'SHL25_NATIVE_PID_0002_SERIAL_PORT_NOT_FOUND'}
  if($dev.InstanceId -notmatch 'VID_18D1&PID_0002'){throw 'WRONG_DEVICE'}
  $name = [regex]::Match($dev.FriendlyName,'COM\d+').Value
  if(!$name){throw 'MISSING_COM_NAME'}
  Save ('HOST_COM_PORT='+$name)
  Save ('HOST_PNP_ID='+$dev.InstanceId)
  $port = [System.IO.Ports.SerialPort]::new(
    $name, 115200, [System.IO.Ports.Parity]::None,
    8, [System.IO.Ports.StopBits]::One)
  $port.Handshake = [System.IO.Ports.Handshake]::None
  $port.DtrEnable = $true
  $port.RtsEnable = $true
  $port.ReadTimeout = 300
  $port.WriteTimeout = 800
  $port.Open()
  Start-Sleep -Milliseconds 160
  Save ('GREETING='+$port.ReadExisting())
  SendAndExpect 'info' 'SHL25 native PID1, Linux 3\.4\.0' 5
  SendAndExpect 'shell' 'shl25-k34#' 9
  SendAndExpect 'uname -a' 'Linux.+shl25-k34#' 8
  SendAndExpect 'pwd' '[/\r\n].*shl25-k34#' 5
  SendAndExpect 'ls /dev/graphics /dev/input' 'shl25-k34#' 6
  SendAndExpect 'cat /proc/meminfo | head -n 4' 'MemTotal:.+shl25-k34#' 8
  SendAndExpect 'exit' 'Back to SHL25 diagnostic console' 7
  SendAndExpect 'usb' 'CONFIGURED' 5
  Save 'SHL25_NATIVE_K34_BUSYBOX_SHELL_ROUNDTRIP_PASS'
  $passed = $true
} catch {
  Save ('SHL25_SHELL_TEST_FAILED '+$_.Exception.Message)
} finally {
  if($port){try{$port.Close();$port.Dispose()}catch{}}
  $entries | Out-File -LiteralPath $log -Encoding utf8
}
Write-Output ('RESULT='+$passed+' LOG='+$log)
if(!$passed){exit 2}
