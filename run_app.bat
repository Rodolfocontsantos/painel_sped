    @echo off
    echo Iniciando Painel SPED...
    echo Por favor, aguarde enquanto a aplicacao carrega no seu navegador.

    REM Define o diretório do script como diretório de trabalho
    cd /d "%~dp0"

    REM Verifica se o ambiente virtual existe
IF NOT EXIST "%~dp0\\.venv\\Scripts\\activate.bat" (
        echo ERRO: Ambiente virtual nao encontrado!
        pause
        exit /b
    )

    REM Ativa o ambiente virtual usando o caminho completo
    echo Ativando ambiente virtual...
call "%~dp0\\.venv\\Scripts\\activate.bat"

    REM Verifica se o Streamlit foi instalado corretamente
    streamlit --version > nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
     echo ERRO: Streamlit nao encontrado no ambiente virtual. Tente recriar o pacote.
     pause
     exit /b
    )

    REM Executa a aplicação Streamlit
    echo Abrindo aplicacao no navegador...
    streamlit run main.py

    echo.
    echo O Painel SPED esta rodando. Mantenha esta janela aberta.
    echo Pressione Ctrl+C nesta janela para fechar a aplicacao.
    pause > nul
