using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Collections.Generic;
public static class EndNoteBridge {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc p, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, string l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, StringBuilder l);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
  public static string Title(IntPtr h) {var s=new StringBuilder(4096);GetWindowText(h,s,s.Capacity);return s.ToString();}
  public static string Class(IntPtr h) {var s=new StringBuilder(256);GetClassName(h,s,s.Capacity);return s.ToString();}
  public static string Text(IntPtr h) {var s=new StringBuilder(4096);SendMessage(h,13,(IntPtr)s.Capacity,s);return s.ToString();}
  public static string[] ComboItems(IntPtr h) {var r=new List<string>();int n=SendMessage(h,326,IntPtr.Zero,IntPtr.Zero).ToInt32();for(int i=0;i<n;i++){var s=new StringBuilder(4096);SendMessage(h,328,(IntPtr)i,s);r.Add(i+" | "+s);}return r.ToArray();}
  public static string[] Windows(uint pid) {var r=new List<string>();EnumWindows((h,l)=>{uint p;GetWindowThreadProcessId(h,out p);if(p==pid && IsWindowVisible(h))r.Add(h+" | "+Class(h)+" | "+Title(h));return true;},IntPtr.Zero);return r.ToArray();}
  public static string[] Children(IntPtr parent) {var r=new List<string>();EnumChildWindows(parent,(h,l)=>{if(IsWindowVisible(h))r.Add(h+" | "+GetDlgCtrlID(h)+" | "+Class(h)+" | "+Title(h));return true;},IntPtr.Zero);return r.ToArray();}
}
