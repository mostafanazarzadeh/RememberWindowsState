[Setup]
AppName=RememberWindowsState
AppVersion=1.0.0
AppVerName=RememberWindowsState 1.0.0
AppPublisher=RememberWindowsState
AppPublisherURL=https://github.com/rememberwindowsstate
DefaultDirName={autopf}\RememberWindowsState
DefaultGroupName=RememberWindowsState
OutputDir=dist\installer
OutputBaseFilename=RememberWindowsState_Setup_1.0.0
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\RememberWindowsState.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "Create a &desktop shortcut"; \
  GroupDescription: "Additional icons:"
Name: "startuprun"; \
  Description: "Start RememberWindowsState automatically when Windows starts"; \
  GroupDescription: "Startup:"

[Files]
Source: "dist\RememberWindowsState.exe"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Icons]
Name: "{group}\RememberWindowsState"; \
  Filename: "{app}\RememberWindowsState.exe"
Name: "{group}\Uninstall RememberWindowsState"; \
  Filename: "{uninstallexe}"
Name: "{commondesktop}\RememberWindowsState"; \
  Filename: "{app}\RememberWindowsState.exe"; \
  Tasks: desktopicon

[Registry]
; Add to startup if user chose the startup task
Root: HKCU; \
  Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; \
  ValueName: "RememberWindowsState"; \
  ValueData: """{app}\RememberWindowsState.exe"" --startup"; \
  Flags: uninsdeletevalue; \
  Tasks: startuprun

[Run]
Filename: "{app}\RememberWindowsState.exe"; \
  Description: "Launch RememberWindowsState now"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove from startup on uninstall
Filename: "reg"; \
  Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v RememberWindowsState /f"; \
  Flags: runhidden waituntilterminated

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
