; Script generated for Spectra PDF Windows Installer
; Developed by Shaheer Ul Hassan (shaheerulhassan.com)

#define MyAppName "Spectra PDF"
#define MyAppVersion "1.3.0"
#define MyAppPublisher "Shaheer Ul Hassan"
#define MyAppURL "https://shaheerulhassan.com"
#define MyAppExeName "SpectraPDF.exe"
#define MyAppAssocName "PDF Document"
#define MyAppAssocExt ".pdf"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{D8C84A96-4F1E-4E38-9B2F-9B67C98A28B1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

DefaultDirName={autopf}\Spectra PDF
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

OutputDir=d:\zylo\tools\dist
OutputBaseFilename=SpectraPDF_Setup_v1.3.0
SetupIconFile=d:\zylo\tools\pyacrobat\resources\icons\spectra_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associate"; Description: "Associate with PDF files (.pdf)"; GroupDescription: "File Associations:"; Flags: checkedonce

[Files]
Source: "d:\zylo\tools\dist\SpectraPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "spectra.pdf.workstation.1.0"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"; AppUserModelID: "spectra.pdf.workstation.1.0"

[Registry]
; AppUserModelID for taskbar pinning and grouping
Root: HKA; Subkey: "Software\Classes\AppUserModelId\spectra.pdf.workstation.1.0"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\AppUserModelId\spectra.pdf.workstation.1.0"; ValueType: string; ValueName: "IconUri"; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey

; File Association (.pdf)
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "SpectraPDF.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\SpectraPDF.Document"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\SpectraPDF.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\SpectraPDF.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey

; Explorer Context Menu: "Open with Spectra PDF"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SpectraPDF"; ValueType: string; ValueName: ""; ValueData: "Open with Spectra PDF"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SpectraPDF"; ValueType: string; ValueName: "Icon"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\SpectraPDF\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
