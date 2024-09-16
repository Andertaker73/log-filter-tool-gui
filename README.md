# Log Filter Tool

## Descrição
Esta é uma versão desktop da ferramenta Log Filter Tool, que processa, filtra e concatena arquivos de log. 
A aplicação foi adaptada para rodar localmente, utilizando uma interface gráfica (GUI) construída com PyQt5.

## Requisitos
- Python 3.8+
- PyQt5

## Instalação

### Clonar o repositório
```
git clone https://github.com/Andertaker73/log-filter-tool-local-gui.git
cd log-filter-tool-gui
```
### Ativar o ambiente virtual

#### Para Windows
```
.venv\Scripts\activate
```

#### Para Linux ou MacOS
```
source .venv/bin/activate
```

### Instalar as dependências
```
pip install -r requirements.txt
```
### Executar a aplicação
```
python main.py
```

## Funcionalidades

- Selecionar arquivo de log: Abra um arquivo .log a partir da interface gráfica para ser processado.
- Filtrar logs: Aplique filtros para isolar URLs específicas ou outras entradas no arquivo de log.
- Concatenar logs: Insira múltiplos parâmetros de concatenação para unir logs de acordo com o critério fornecido.
- Salvar arquivos processados: Selecione o diretório onde deseja salvar os arquivos filtrados e concatenados.
- Criar Atalho: Crie um atalho na área de trabalho (ou onde quiser) para execução rápida da aplicação.

## Observação

Esta versão foi desenvolvida para rodar de forma independente, sem necessidade de servidor ou API. 
Todos os arquivos gerados serão salvos localmente no diretório escolhido pelo usuário através da interface.

## Dependências

As dependências estão listadas no arquivo requirements.txt, que inclui as bibliotecas necessárias para a interface gráfica, manipulação de logs e criação de atalhos no Windows.