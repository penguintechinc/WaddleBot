@echo off
REM WaddleBot Premium Desktop Bridge Build Script for Windows
REM Builds for Windows 11 and creates distribution packages

echo.
echo 🤖 WaddleBot Premium Desktop Bridge Build Script
echo ==============================================

REM Configuration
set APP_NAME=waddlebot-bridge
set VERSION=1.0.0
set BUILD_DIR=build
set DIST_DIR=dist

REM Check if Go is installed
where go >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Go is not installed or not in PATH
    exit /b 1
)

REM Check Go version
echo [INFO] Checking Go version...
go version

REM Clean previous builds
echo [INFO] Cleaning previous builds...
if exist %BUILD_DIR% rmdir /s /q %BUILD_DIR%
if exist %DIST_DIR% rmdir /s /q %DIST_DIR%
mkdir %BUILD_DIR%
mkdir %DIST_DIR%

REM Build module examples
echo [INFO] Building module examples...
cd internal\modules\examples\system
go build -buildmode=plugin -o ..\..\..\..\%BUILD_DIR%\system.so system.go
if %errorlevel% neq 0 (
    echo [WARNING] Module plugin build failed, continuing...
)
cd ..\..\..\..

REM Build Windows Binary
echo [INFO] Building Windows Binary...
set CGO_ENABLED=0
set GOOS=windows
set GOARCH=amd64
go build -ldflags="-s -w -X main.version=%VERSION%" -o %BUILD_DIR%\%APP_NAME%-windows-amd64.exe cmd\main.go

if %errorlevel% neq 0 (
    echo [ERROR] Windows build failed
    exit /b 1
)

REM Build for other platforms (if desired)
echo [INFO] Building Linux Binary...
set GOOS=linux
go build -ldflags="-s -w -X main.version=%VERSION%" -o %BUILD_DIR%\%APP_NAME%-linux-amd64 cmd\main.go

echo [INFO] Building macOS Binary...
set GOOS=darwin
set GOARCH=amd64
go build -ldflags="-s -w -X main.version=%VERSION%" -o %BUILD_DIR%\%APP_NAME%-darwin-amd64 cmd\main.go

REM Reset environment
set GOOS=
set GOARCH=
set CGO_ENABLED=

REM Create distribution packages
echo [INFO] Creating distribution packages...

REM Windows Package
echo [INFO] Creating Windows package...
set WINDOWS_DIR=%DIST_DIR%\WaddleBot-Bridge-Windows-%VERSION%
mkdir "%WINDOWS_DIR%"
copy %BUILD_DIR%\%APP_NAME%-windows-amd64.exe "%WINDOWS_DIR%\waddlebot-bridge.exe"
if exist README.md copy README.md "%WINDOWS_DIR%\"
if exist LICENSE copy LICENSE "%WINDOWS_DIR%\"

REM Create Windows batch file
echo @echo off > "%WINDOWS_DIR%\start.bat"
echo cd /d "%%~dp0" >> "%WINDOWS_DIR%\start.bat"
echo waddlebot-bridge.exe --config config.yaml >> "%WINDOWS_DIR%\start.bat"
echo pause >> "%WINDOWS_DIR%\start.bat"

REM Create sample config for Windows
echo # WaddleBot Bridge Configuration > "%WINDOWS_DIR%\config.yaml"
echo api-url: "https://api.waddlebot.io" >> "%WINDOWS_DIR%\config.yaml"
echo community-id: "" >> "%WINDOWS_DIR%\config.yaml"
echo user-id: "" >> "%WINDOWS_DIR%\config.yaml"
echo poll-interval: 30 >> "%WINDOWS_DIR%\config.yaml"
echo web-port: 8080 >> "%WINDOWS_DIR%\config.yaml"
echo web-host: "127.0.0.1" >> "%WINDOWS_DIR%\config.yaml"
echo log-level: "info" >> "%WINDOWS_DIR%\config.yaml"

REM Create Windows installer script
echo [INFO] Creating Windows installer script...
echo @echo off > "%WINDOWS_DIR%\install.bat"
echo echo Installing WaddleBot Bridge... >> "%WINDOWS_DIR%\install.bat"
echo echo. >> "%WINDOWS_DIR%\install.bat"
echo echo Before running, please configure your community-id and user-id in config.yaml >> "%WINDOWS_DIR%\install.bat"
echo echo. >> "%WINDOWS_DIR%\install.bat"
echo echo You can run the bridge by executing start.bat >> "%WINDOWS_DIR%\install.bat"
echo echo Or run directly: waddlebot-bridge.exe --config config.yaml >> "%WINDOWS_DIR%\install.bat"
echo echo. >> "%WINDOWS_DIR%\install.bat"
echo echo Installation complete! >> "%WINDOWS_DIR%\install.bat"
echo pause >> "%WINDOWS_DIR%\install.bat"

REM Create archives
echo [INFO] Creating archives...
cd %DIST_DIR%

REM Windows Archive
where powershell >nul 2>nul
if %errorlevel% equ 0 (
    powershell -Command "Compress-Archive -Path 'WaddleBot-Bridge-Windows-%VERSION%' -DestinationPath 'WaddleBot-Bridge-Windows-%VERSION%.zip' -Force"
    echo [INFO] Windows archive created: WaddleBot-Bridge-Windows-%VERSION%.zip
) else (
    echo [WARNING] PowerShell not found, skipping archive creation
)

cd ..

REM Generate checksums
echo [INFO] Generating checksums...
cd %DIST_DIR%
where powershell >nul 2>nul
if %errorlevel% equ 0 (
    powershell -Command "Get-FileHash *.zip -Algorithm SHA256 | Format-Table Hash, Path -AutoSize | Out-File -FilePath checksums.txt -Encoding utf8"
    echo [INFO] Checksums generated
)
cd ..

REM Build summary
echo.
echo [INFO] Build Summary:
echo ==============================================
echo Version: %VERSION%
echo Build Directory: %BUILD_DIR%
echo Distribution Directory: %DIST_DIR%
echo.
echo Built Binaries:
dir %BUILD_DIR%
echo.
echo Distribution Packages:
dir %DIST_DIR%
echo.

REM Get binary sizes
echo [INFO] Binary Sizes:
for %%f in (%BUILD_DIR%\*.exe) do (
    for /f "tokens=3" %%s in ('dir "%%f" ^| findstr /C:"%%~nxf"') do (
        echo Windows x64: %%s bytes
    )
)

echo.
echo 🎉 Build completed successfully!
echo 📦 Distribution packages are ready in the %DIST_DIR% directory
echo.
echo Installation Instructions:
echo ==========================
echo Windows: Extract the .zip file and run install.bat
echo Then run start.bat to launch the bridge
echo.
echo Before running, configure your community-id and user-id in config.yaml
echo.
echo Web Interface: http://localhost:8080
echo.
pause