@echo off
setlocal

set API_KEY=7d1fd70c60ac827d2bddc4de879804e8
set USERNAME=jiri.cechura
set PASSWORD_HASH=$2b$12$4NuMNFox0FS0Q7BIMV4gpOR7x/7k3wm9urq1j8HrR01Y.HnAx9l3u
set EMAIL=jiri.cechura@gmail.com
set APPROVED=true
set CREATED_AT=2025-08-04T10:18:45.759182

REM Install dependencies if needed
call npm install

REM Launch the Electron app
call npm start

pause
