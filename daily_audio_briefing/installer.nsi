; Daily Audio Briefing - NSIS Installer Script
; Creates a professional Windows installer with:
; - Welcome screen
; - License agreement (optional)
; - Install location selection
; - Start menu shortcuts
; - Desktop shortcut (optional)
; - Uninstaller
;
; To build: makensis installer.nsi
; Requires: NSIS 3.x (https://nsis.sourceforge.io/)

;--------------------------------
; Includes

!include "MUI2.nsh"
!include "FileFunc.nsh"

;--------------------------------
; General

Name "Daily Audio Briefing"
OutFile "dist\DailyAudioBriefing-1.0.0-Windows-Setup.exe"
InstallDir "$PROGRAMFILES64\Daily Audio Briefing"
InstallDirRegKey HKLM "Software\DailyAudioBriefing" "InstallDir"
RequestExecutionLevel admin
Unicode True

; Version info for the installer
VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "Daily Audio Briefing"
VIAddVersionKey "CompanyName" "Daily Audio Briefing"
VIAddVersionKey "FileDescription" "Daily Audio Briefing Installer"
VIAddVersionKey "FileVersion" "1.0.0"
VIAddVersionKey "ProductVersion" "1.0.0"
VIAddVersionKey "LegalCopyright" "Copyright 2024"

;--------------------------------
; Interface Settings

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!define MUI_WELCOMEPAGE_TITLE "Welcome to Daily Audio Briefing Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of Daily Audio Briefing.$\r$\n$\r$\nDaily Audio Briefing automatically creates personalized audio news briefings from your favorite YouTube channels and websites.$\r$\n$\r$\nClick Next to continue."

; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\DailyAudioBriefing.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Daily Audio Briefing"
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

;--------------------------------
; Pages

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Languages

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Sections

Section "Install" SecInstall
    SetOutPath "$INSTDIR"

    ; Copy all application files
    ; The dist\DailyAudioBriefing folder contains the PyInstaller output
    File /r "dist\DailyAudioBriefing\*.*"

    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\Daily Audio Briefing"
    CreateShortcut "$SMPROGRAMS\Daily Audio Briefing\Daily Audio Briefing.lnk" "$INSTDIR\DailyAudioBriefing.exe"
    CreateShortcut "$SMPROGRAMS\Daily Audio Briefing\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\Daily Audio Briefing.lnk" "$INSTDIR\DailyAudioBriefing.exe"

    ; Write registry keys for uninstaller
    WriteRegStr HKLM "Software\DailyAudioBriefing" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "DisplayName" "Daily Audio Briefing"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "DisplayIcon" "$INSTDIR\DailyAudioBriefing.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "Publisher" "Daily Audio Briefing"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "DisplayVersion" "1.0.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "NoRepair" 1

    ; Calculate and write install size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing" "EstimatedSize" "$0"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

;--------------------------------
; Uninstaller Section

Section "Uninstall"
    ; Remove application files
    RMDir /r "$INSTDIR"

    ; Remove Start Menu shortcuts
    RMDir /r "$SMPROGRAMS\Daily Audio Briefing"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\Daily Audio Briefing.lnk"

    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\DailyAudioBriefing"
    DeleteRegKey HKLM "Software\DailyAudioBriefing"
SectionEnd
