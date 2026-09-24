@echo off
chcp 65001 >nul
cls
echo ==============================================================================
echo           DESINSTALADOR DO CGMA ARCGIS GEE PLUGIN
echo ==============================================================================
echo.
echo Este assistente ira desinstalar o Add-In do ArcGIS Desktop 10.8 e limpar
echo os caches de execucao e arquivos temporarios do sistema.
echo.
set /p CONFIRM="Deseja realmente desinstalar o plugin agora? (S/N): "
if /i not "%CONFIRM%"=="S" (
    echo.
    echo [INFO] Desinstalacao cancelada pelo usuario.
    pause
    exit /b 0
)

echo.
echo [1/4] Encerrando processos da interface grafica GEE em segundo plano...
taskkill /f /im pythonw.exe 2>nul
echo    - Concluido.

echo.
echo [2/4] Removendo o Add-In oficial (.esriaddin) da pasta do ArcGIS...
set ADDIN_DIR=%USERPROFILE%\Documents\ArcGIS\AddIns\Desktop10.8\{ceae58c4-c44e-4edd-b8f4-1ba7d13b6b7d}
if exist "%ADDIN_DIR%" (
    rd /s /q "%ADDIN_DIR%"
    echo    - Pasta do Add-In removida com sucesso.
) else (
    echo    - Nenhum Add-In encontrado em Documents\ArcGIS\AddIns.
)

echo.
echo [3/4] Limpando o AssemblyCache do ArcMap...
set CACHE_DIR=%LOCALAPPDATA%\ESRI\Desktop10.8\AssemblyCache\{CEAE58C4-C44E-4EDD-B8F4-1BA7D13B6B7D}
if exist "%CACHE_DIR%" (
    rd /s /q "%CACHE_DIR%"
    echo    - Cache de assembly removido com sucesso.
) else (
    echo    - Nenhum cache residual encontrado.
)

echo.
echo [4/4] Removendo arquivos temporarios de comunicacao IPC...
del /q "%TEMP%\gee_arcgis_*.json" 2>nul
del /q "%TEMP%\arcgis_gee_*.json" 2>nul
echo    - Arquivos temporarios limpos.

echo.
echo ==============================================================================
echo           [SUCESSO] O PLUGIN FOI DESINSTALADO COM SUCESSO!
echo ==============================================================================
echo.
echo Ao abrir o ArcMap 10.8 novamente, a toolbar e o botao GEE nao serao mais carregados.
echo (Caso queira reinstalar no futuro, basta executar novamente o install.bat).
echo.
pause
