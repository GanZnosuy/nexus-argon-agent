Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Helper {
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$processes = Get-Process -Name chrome, msedge, brave, firefox -ErrorAction SilentlyContinue
foreach ($p in $processes) {
    if ($p.MainWindowHandle -ne [IntPtr]::Zero) {
        [Win32Helper]::ShowWindow($p.MainWindowHandle, 9) # SW_RESTORE
        [Win32Helper]::SetForegroundWindow($p.MainWindowHandle)
    }
}
