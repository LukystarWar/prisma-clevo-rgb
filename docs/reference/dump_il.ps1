param([string[]]$TypeNames, [string]$MethodFilter = '.')
$c = 'C:\Program Files\WindowsApps\CLEVOCO.LedKeyboardSetting_3.32.0.0_x64__6h6z29zh29qx0\CC'
[AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve({ param($s, $a) try { [Reflection.Assembly]::ReflectionOnlyLoad([AppDomain]::CurrentDomain.ApplyPolicy($a.Name)) } catch { $null } })
$asm = [Reflection.Assembly]::ReflectionOnlyLoadFrom("$c\LedKeyboardSetting.exe")
$mod = $asm.ManifestModule
try { $types = $asm.GetTypes() } catch [Reflection.ReflectionTypeLoadException] { $types = $_.Exception.Types | Where-Object { $_ } }

$one = @{}; $two = @{}
foreach ($f in [Reflection.Emit.OpCodes].GetFields('Public,Static')) {
    $op = $f.GetValue($null)
    $v = [uint16]([int]$op.Value -band 0xFFFF)
    if ($op.Size -eq 1) { $one[[byte]($v -band 0xFF)] = $op } else { $two[[byte]($v -band 0xFF)] = $op }
}

function Resolve-Token([int]$tok, $kind) {
    try {
        switch ($kind) {
            'InlineString' { return '"' + $mod.ResolveString($tok) + '"' }
            default {
                $m = $mod.ResolveMember($tok)
                return "$($m.DeclaringType.Name)::$($m.Name)"
            }
        }
    } catch { return ('tok_{0:X8}' -f $tok) }
}

function Dump-Method($m) {
    $body = $null
    try { $body = $m.GetMethodBody() } catch {}
    if (-not $body) { return }
    $il = $body.GetILAsByteArray()
    $ps = ''
    try { $ps = ($m.GetParameters() | ForEach-Object { "$($_.ParameterType.Name) $($_.Name)" }) -join ', ' } catch {}
    "`n## $($m.DeclaringType.Name)::$($m.Name)($ps)"
    $i = 0
    while ($i -lt $il.Length) {
        $start = $i
        $b = $il[$i]; $i++
        if ($b -eq 0xFE) { $op = $two[$il[$i]]; $i++ } else { $op = $one[$b] }
        if (-not $op) { "  {0:X4} ??" -f $start; continue }
        $arg = ''
        switch ($op.OperandType.ToString()) {
            'InlineNone' {}
            'ShortInlineBrTarget' { $d = [sbyte]([int]$il[$i] - $(if ($il[$i] -gt 127) { 256 } else { 0 })); $i++; $arg = '{0:X4}' -f ($i + $d) }
            'ShortInlineI' { $arg = [string]$il[$i]; $i++ }
            'ShortInlineVar' { $arg = [string]$il[$i]; $i++ }
            'InlineVar' { $arg = [BitConverter]::ToUInt16($il, $i); $i += 2 }
            'InlineBrTarget' { $d = [BitConverter]::ToInt32($il, $i); $i += 4; $arg = '{0:X4}' -f ($i + $d) }
            'InlineI' { $arg = [BitConverter]::ToInt32($il, $i); $i += 4 }
            'InlineI8' { $arg = [BitConverter]::ToInt64($il, $i); $i += 8 }
            'InlineR' { $arg = [BitConverter]::ToDouble($il, $i); $i += 8 }
            'ShortInlineR' { $arg = [BitConverter]::ToSingle($il, $i); $i += 4 }
            'InlineSwitch' { $n = [BitConverter]::ToInt32($il, $i); $i += 4 + 4 * $n; $arg = "switch[$n]" }
            'InlineString' { $arg = Resolve-Token ([BitConverter]::ToInt32($il, $i)) 'InlineString'; $i += 4 }
            default { $arg = Resolve-Token ([BitConverter]::ToInt32($il, $i)) 'member'; $i += 4 }
        }
        "  {0:X4} {1} {2}" -f $start, $op.Name, $arg
    }
}

$bf = [Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly'
foreach ($tn in $TypeNames) {
    $t = $types | Where-Object { $_.FullName -eq $tn } | Select-Object -First 1
    if (-not $t) { "TIPO NAO ENCONTRADO: $tn"; continue }
    "`n===== $($t.FullName) base=$($t.BaseType.FullName)"
    if ($t.IsEnum) {
        foreach ($f in $t.GetFields('Public,Static')) { "  $($f.Name) = $($f.GetRawConstantValue())" }
        continue
    }
    foreach ($f in $t.GetFields($bf)) {
        $val = ''
        if ($f.IsLiteral) { try { $val = " = $($f.GetRawConstantValue())" } catch {} }
        "  field $($f.FieldType.Name) $($f.Name)$val"
    }
    foreach ($m in $t.GetMethods($bf)) { if ($m.Name -match $MethodFilter) { Dump-Method $m } }
    foreach ($m in $t.GetConstructors($bf)) { if ('.ctor' -match $MethodFilter) { Dump-Method $m } }
}
