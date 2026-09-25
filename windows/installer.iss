; Inno Setup script: wraps the built app folder into DyslexiaConverter-<version>-setup.exe
; Built by .github/workflows/windows-release.yml, or manually:
;   iscc /DMyAppVersion=1.2.0 /DSourceDir=..\dist\DyslexiaConverter windows\installer.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.2.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\DyslexiaConverter"
#endif

[Setup]
AppId={{6F0C2C1E-7B2A-4D63-9C1B-2E5D9A1F4B11}
AppName=Dyslexia Converter
AppVersion={#MyAppVersion}
AppPublisher=Dyslexia Converter
DefaultDirName={localappdata}\Programs\Dyslexia Converter
DefaultGroupName=Dyslexia Converter
DisableProgramGroupPage=yes
; installs for the current user only: no administrator rights needed
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=DyslexiaConverter-{#MyAppVersion}-setup
SetupIconFile=app.ico
UninstallDisplayIcon={app}\DyslexiaConverter.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Dyslexia Converter"; Filename: "{app}\DyslexiaConverter.exe"
Name: "{userdesktop}\Dyslexia Converter"; Filename: "{app}\DyslexiaConverter.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DyslexiaConverter.exe"; Description: "{cm:LaunchProgram,Dyslexia Converter}"; Flags: nowait postinstall skipifsilent
