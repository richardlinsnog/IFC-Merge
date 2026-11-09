# IFC Merger

Aplicativo desktop simples para unificar (merge) múltiplos arquivos IFC em um
único arquivo IFC, substituindo o fluxo manual feito no BlenderBIM por um
executável de clique único.

## Funcionalidades

- Selecionar múltiplos modelos IFC (`.ifc`, `.ifczip`, `.ifcxml`), preservando
  a ordem de seleção (o primeiro arquivo é o modelo base).
- Adicionar modelos de **pastas diferentes** (cada seleção acumula na lista) e
  remover modelos da lista com o botão "✕".
- Escolher a pasta de exportação (exibida em uma caixa de texto para
  confirmação).
- Acompanhar o progresso do merge em um **log de status** (com opção de
  cancelar entre as etapas).
- Unificar os modelos em um único `merged.ifc` via `ifcpatch` (recipe
  `MergeProjects`), que converte automaticamente as unidades de comprimento dos
  modelos adicionais para a unidade do modelo base.
- Converter automaticamente modelos com **schema diferente** (ex.: `IFC2X3` +
  `IFC4`) para o schema **mais novo** presente entre eles antes de mesclar
  (recipe `Migrate`), evitando downgrade com perda de dados.

## Requisitos

- Python 3.10 ou superior
- `ifcopenshell`
- `ifcpatch` (recipe `MergeProjects` — nas versões atuais é um pacote PyPI
  separado, não vem embutido no `ifcopenshell`)

## Instalação (Windows)

1. Instale o Python 3.10+ em <https://www.python.org/downloads/> (marque a opção
   *"Add Python to PATH"* durante a instalação).
2. Abra o terminal (PowerShell ou CMD) na pasta do projeto:

   ```powershell
   cd caminho\para\ifc-merger
   ```

3. Crie e ative um ambiente virtual (opcional, mas recomendado):

   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

4. Instale as dependências:

   ```powershell
   pip install -r requirements.txt
   ```

## Execução

```powershell
python app.py
```

## Uso

1. Clique em **"Select models"** e selecione os arquivos IFC. Repita para
   adicionar modelos de outras pastas; use o "✕" para remover um modelo da lista.
2. Clique em **"Export path"** e escolha a pasta onde o resultado será salvo.
3. Clique em **"Merge IFC files"** e acompanhe o progresso no log (pode
   cancelar com **"Cancelar"**).
4. O resultado será salvo como `merged.ifc` na pasta escolhida.

## Gerar o executável (.exe)

Instale o PyInstaller (usado apenas para build, não é dependência de runtime):

```powershell
pip install pyinstaller
```

Gere o executável:

```powershell
pyinstaller --onefile --windowed --name "IFC Merger" --collect-all ifcpatch --collect-all ifcopenshell app.py
```

O executável será gerado na pasta `dist\IFC Merger.exe`.

> **Atenção:** o executável final fica grande (dezenas de MB), pois o
> `ifcopenshell` é uma biblioteca compilada que é embutida no `.exe`.

## Estrutura do projeto

```
ifc-merger/
├── app.py             # código principal (GUI + lógica de merge)
├── requirements.txt   # dependências
└── README.md          # instruções de instalação, execução e build
```
