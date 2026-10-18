@echo off
REM -------------------------------------------------------------
REM provision_new_dongle.bat - One-click factory provisioning pipeline
REM -------------------------------------------------------------

pushd "%~dp0" >nul

C:\Users\god\AppData\Local\Python\pythoncore-3.14-64\python.exe provision_new_dongle.py %*
set RET=%ERRORLEVEL%

popd >nul
exit /b %RET%
