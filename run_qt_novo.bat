@echo off
echo Iniciando Painel SPED (Qt Novo)...
echo Aguarde enquanto a aplicacao carrega.

REM Define o diretorio do script como diretorio de trabalho
cd /d "%~dp0"

REM Verifica se o ambiente virtual existe
IF NOT EXIST "%~dp0\\.venv\\Scripts\\activate.bat" (
    echo ERRO: Ambiente virtual nao encontrado!
    pause
    exit /b
)

REM Ativa o ambiente virtual
echo Ativando ambiente virtual...
call "%~dp0\\.venv\\Scripts\\activate.bat"

REM Executa a aplicacao Qt Nova
python main_qt_novo.py

echo.
echo O Painel SPED Qt Novo foi encerrado.
pause > nul
