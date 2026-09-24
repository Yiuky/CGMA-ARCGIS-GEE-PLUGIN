@echo off
chcp 65001 >nul
title Autenticação - Google Earth Engine (ArcGIS Plugin)
cls
echo ======================================================================
echo           AUTENTICADOR DO GOOGLE EARTH ENGINE PARA O ARCGIS
echo ======================================================================
echo.
echo Este utilitário vai abrir o seu navegador para conectar sua conta Google
echo ao Google Earth Engine e gerar as credenciais locais.
echo.

set PY3_CMD=
if exist "C:\CGMA_GEE_PLUGIN\venv\Scripts\python.exe" set PY3_CMD="C:\CGMA_GEE_PLUGIN\venv\Scripts\python.exe"
if not defined PY3_CMD if exist "C:\PRODUTIVIDADE_SIMCAR_DIGITAL\venv_p3\Scripts\python.exe" set PY3_CMD="C:\PRODUTIVIDADE_SIMCAR_DIGITAL\venv_p3\Scripts\python.exe"
if not defined PY3_CMD if exist "C:\Python312\python.exe" set PY3_CMD="C:\Python312\python.exe"
if not defined PY3_CMD if exist "C:\Python311\python.exe" set PY3_CMD="C:\Python311\python.exe"
if not defined PY3_CMD if exist "C:\Python310\python.exe" set PY3_CMD="C:\Python310\python.exe"
if not defined PY3_CMD if exist "C:\Program Files\QGIS 3.44.10\apps\Python312\python.exe" set PY3_CMD="C:\Program Files\QGIS 3.44.10\apps\Python312\python.exe"
if not defined PY3_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PY3_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY3_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set PY3_CMD="%LOCALAPPDATA%\Programs\Python\Python311\python.exe"

if not defined PY3_CMD (
    for /f "tokens=*" %%i in ('where python 2^>nul') do (
        %%i -c "import sys; sys.exit(0 if sys.version_info[0]>=3 else 1)" 2>nul
        if not errorlevel 1 (
            set PY3_CMD="%%i"
            goto :found_py3
        )
    )
)

:found_py3
if not defined PY3_CMD (
    echo [ERRO] Python 3 nao encontrado automaticamente.
    echo Instale o Python 3 ou especifique o caminho completo.
    pause
    exit /b 1
)

echo Python 3 detectado: %PY3_CMD%
echo.
echo Iniciando autenticacao do Google Earth Engine...
%PY3_CMD% -c "import ee; ee.Authenticate()"
if errorlevel 1 (
    echo.
    echo [AVISO] Tentando autenticacao via CLI earthengine...
    %PY3_CMD% -m ee.cli.eecli authenticate
)

echo.
echo ======================================================================
echo          VERIFICANDO CONEXAO COM O GOOGLE EARTH ENGINE...
echo ======================================================================
%PY3_CMD% -c "import ee; ee.Initialize(); print('SUCESSO: Conectado ao GEE!')" 2>nul
if errorlevel 1 (
    echo.
    echo [OBSERVAÇÃO] Se for solicitado um ID de Projeto Google Cloud,
    echo voce podera defini-lo diretamente na interface do ArcMap
    echo clicando no botao 'Configurar Projeto GEE' no topo da janela.
) else (
    echo.
    echo [OK] Autenticacao e Inicializacao concluidas com sucesso!
)
echo.
pause
