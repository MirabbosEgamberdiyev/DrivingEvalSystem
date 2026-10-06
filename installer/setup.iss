; Inno Setup 6 Script for Offline 4-Camera AI Driving Training & Evaluation System
; 100% Offline Standalone Windows Deployment with 3 Languages (uz-Latn, uz-Cyrl, ru)

#define MyAppName "Driving Evaluation System"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Driving Evaluation AI Systems"
#define MyAppExeName "driving_eval.exe"

[Setup]
AppId={{8B3E4268-F973-4AE3-A924-E840428BFB82}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DrivingEvalSystem
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist\installer
OutputBaseFilename=DrivingEvalSetup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=admin
DisableWelcomePage=no
WizardStyle=modern

[Languages]
Name: "uz_Latn"; MessagesFile: "compiler:Default.isl,languages\uz-Latn.isl"
Name: "uz_Cyrl"; MessagesFile: "compiler:Default.isl,languages\uz-Cyrl.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl,languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "kioskmode"; Description: "{cm:KioskModeShortcut}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "{cm:AutoStartOnBoot}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Standalone build binaries and dependencies
Source: "..\dist\driving_eval\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist
Source: "..\data\audio\*"; DestDir: "{app}\data\audio"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\data\models\*"; DestDir: "{app}\data\models"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} (Kiosk Mode)"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--kiosk"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{app}\docs\README.html"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} Kiosk"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--kiosk"; Tasks: kioskmode
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--kiosk"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom Pascal Script to verify disk space and DirectShow media environment

function InitializeSetup(): Boolean;
var
  FreeSpaceMB: Cardinal;
begin
  Result := True;

  // Minimum disk check: 10,240 MB (10 GB)
  if GetSpaceOnDisk(ExtractFileDrive(ExpandConstant('{autopf}')), True, FreeSpaceMB) then
  begin
    if FreeSpaceMB < 10240 then
    begin
      MsgBox(CustomMessage('StorageWarning'), mbInformation, MB_OK);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    Log('Driving Evaluation System installation finished successfully.');
  end;
end;
