Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$taskProc=Get-Process EndNote
$taskCond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$taskProc.Id)
$taskWindows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$taskCond)
function Show-Tree($e,$depth=0){
 if($depth -gt 5){return}
 $c=$e.Current
 Write-Output (((' '*$depth))+ $c.ControlType.ProgrammaticName+' | '+$c.Name+' | '+$c.AutomationId+' | '+$c.NativeWindowHandle)
 $walker=[System.Windows.Automation.TreeWalker]::ControlViewWalker
 $child=$walker.GetFirstChild($e)
 while($child){Show-Tree $child ($depth+1);$child=$walker.GetNextSibling($child)}
}
foreach($w in $taskWindows){Show-Tree $w}
