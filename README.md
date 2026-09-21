# Painel SPED

Aplicação para visualizar, filtrar, alterar, resumir e converter arquivos EFD ICMS/IPI no formato SPED.

O projeto oferece uma interface web com Streamlit e duas interfaces desktop com PySide6. Atualmente, a interface Qt nova é a opção desktop principal; a versão Qt original permanece disponível como implementação anterior.

## Funcionalidades

- Leitura de arquivos SPED em codificação Latin-1.
- Separação e preservação do bloco 9 de encerramento.
- Visualização das primeiras 100 linhas do arquivo.
- Filtros por registro, campo e texto livre.
- Alteração de campos com base no layout SPED carregado.
- Detecção e remoção segura de registros `0200` duplicados: mantém a ocorrência com filhos ou, quando não há filhos, a mais completa, sem reposicionar linhas.
- Remoção opcional dos registros `C101` relacionados ao DIFAL.
- Recálculo dos totalizadores após a remoção de registros.
- Resumo de valores de ICMS e agrupamentos por CFOP e tipo de operação.
- Exportação para Excel, com uma aba por registro.
- Exportação para arquivo delimitado por ponto e vírgula.
- Salvamento do arquivo SPED processado.

## Requisitos

- Windows.
- Python 3.11 ou superior.
- `pip` disponível no ambiente Python.
- Arquivo de layout `sped_descricao/sped_descritivo.txt` presente no projeto.

O ambiente utilizado na validação atual possui Python 3.13, Streamlit, pandas, PySide6 e XlsxWriter.

## Instalação

No PowerShell, a partir da raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se a execução de scripts estiver bloqueada no PowerShell, ative o ambiente pelo Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

Não versione a pasta `.venv`.

## Como executar

### Interface web — Streamlit

Com o ambiente virtual ativado:

```powershell
python -m streamlit run main.py
```

Alternativamente, execute:

```bat
run_app.bat
```

O Streamlit normalmente disponibiliza a aplicação em `http://localhost:8501`.

### Interface desktop — Qt nova

```powershell
python main_qt_novo.py
```

Ou:

```bat
run_qt_novo.bat
```

### Interface desktop — Qt original

```powershell
python main_qt.py
```

Ou:

```bat
run_qt.bat
```

## Uso básico

1. Inicie uma das interfaces.
2. Selecione um arquivo SPED com extensão `.txt`.
3. Escolha entre visualizar, alterar campos, gerar resumo, converter, remover duplicados ou remover DIFAL.
4. Ao alterar dados, confira os registros filtrados e a pré-visualização.
5. Salve o resultado em um novo arquivo e preserve o original para rollback.

## Variáveis de ambiente

O projeto não exige variáveis de ambiente no estado atual e não utiliza serviços externos, banco de dados ou credenciais.

Caso sejam adicionadas configurações sensíveis futuramente:

- não salve segredos diretamente no código;
- documente apenas os nomes das variáveis em `.env.example`;
- mantenha o arquivo `.env` fora do versionamento.

## Estrutura do projeto

```text
PainelSpedApp/
├── main.py                     # Entrada da interface Streamlit
├── main_qt_novo.py             # Entrada da interface Qt nova
├── main_qt.py                  # Entrada da interface Qt original
├── qt_backend.py               # Regras compartilhadas pelas interfaces Qt
├── utils.py                    # Leitura, layout e download no Streamlit
├── modules/
│   ├── alterar.py              # Filtros, seleção e alteração no Streamlit
│   ├── converter.py            # Exportações Excel e CSV no Streamlit
│   ├── remover_registros.py    # Confirmação e remoção de 0200/C101
│   ├── resumo.py               # Resumos fiscais no Streamlit
│   └── visualizar.py           # Visualização do conteúdo no Streamlit
├── services/
│   └── sped_cleanup.py         # Análise, remoção e recálculo de totalizadores
├── ui/
│   └── qt_ui.py                # Componentes da interface Qt original
├── ui_nova/
│   ├── filtered_lines_model.py # Modelo de registros filtrados
│   └── qt_ui.py                # Componentes da interface Qt nova
├── sped_descricao/             # Layout ativo e referências da EFD
├── sintegra_descricao/         # Referências de arquivos SINTEGRA
├── requirements.txt            # Dependências Python
├── tests/                       # Testes automatizados das regras de limpeza
└── run_*.bat                   # Atalhos de execução no Windows
```

## Layout SPED

O arquivo ativo é `sped_descricao/sped_descritivo.txt`. Cada linha relaciona um código de registro aos respectivos campos. Esse mapeamento é usado para localizar campos, aplicar filtros, produzir resumos e nomear colunas no Excel.

Ao atualizar o layout, preserve o formato delimitado por `|` e valide os índices dos registros utilizados pelo sistema.

## Comandos úteis

Verificar as versões instaladas:

```powershell
python --version
python -m streamlit version
python -m pip list
```

Limpar o cache de dados do Streamlit:

```powershell
python -m streamlit cache clear
```

Atualizar as dependências conforme o arquivo atual:

```powershell
python -m pip install -r requirements.txt
```

## Cuidados de integridade

O projeto está em evolução. Antes de utilizar um arquivo alterado em ambiente fiscal:

- mantenha uma cópia do arquivo original;
- não insira `|` ou quebras de linha nos valores;
- valide o arquivo gerado no PVA correspondente;
- confira totalizadores e relacionamentos entre registros;
- trate o resumo apresentado como auxiliar, não como apuração fiscal definitiva.

Os testes automatizados podem ser executados com:

```powershell
python -m unittest discover -s tests -v
```
