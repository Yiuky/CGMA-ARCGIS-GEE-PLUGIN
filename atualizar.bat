@echo off
chcp 65001 >nul
cls
echo ==============================================================================
echo                 ATUALIZADOR DO CGMA ARCGEE EXPLORER
echo ==============================================================================
echo.
echo Este utilitario sincroniza os arquivos mais recentes do GitHub e
echo recompila o Add-In para o ArcGIS Desktop 10.8.
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/3] Verificando conexao e buscando atualizacoes no GitHub...
if exist ".git" (
    git pull origin main
    if %errorlevel% neq 0 (
        echo [AVISO] Falha no git pull. Tentando download direto via PowerShell...
        goto download_zip
    )
    goto compile_deploy
)

:download_zip
echo Baixando versao mais recente via GitHub ZIP...
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/Yiuky/CGMA-ARCGIS-GEE-PLUGIN/archive/refs/heads/main.zip' -OutFile '%TEMP%\gee_plugin_update.zip'"
if %errorlevel% neq 0 (
    echo [ERRO] Nao foi possivel baixar o arquivo do GitHub. Verifique sua conexao.
    pause
    exit /b 1
)

echo Extraindo arquivos atualizados...
powershell -Command "Expand-Archive -Path '%TEMP%\gee_plugin_update.zip' -DestinationPath '%TEMP%\gee_plugin_extracted' -Force; Copy-Item '%TEMP%\gee_plugin_extracted\CGMA-ARCGIS-GEE-PLUGIN-main\*' '%SCRIPT_DIR%' -Recurse -Force; Remove-Item '%TEMP%\gee_plugin_extracted' -Recurse -Force; Remove-Item '%TEMP%\gee_plugin_update.zip' -Force"

:compile_deploy
echo.
echo [2/3] Recompilando pacote Add-In (.esriaddin)...
if exist "C:\Python27\ArcGIS10.8\python.exe" (
    "C:\Python27\ArcGIS10.8\python.exe" arcgis_addin\makeaddin.py
) else (
    python arcgis_addin\makeaddin.py
)

echo.
echo [3/3] Atualizando AssemblyCache e instalando Add-In...
powershell -ExecutionPolicy Bypass -File deploy.ps1

echo.
echo ==============================================================================
echo           [SUCESSO] PLUGIN ATUALIZADO COM SUCESSO!
echo ==============================================================================
echo Voce ja pode abrir o ArcMap ou iniciar o plugin.
echo.
pause
