# Log Filter Tool

## Descrição
Esta ferramenta processa, filtra e concatena arquivos de log.

## Requisitos
- Python 3.8+
- Flask
- texttable

## Instalação

### Clonar o repositório
```
git clone https://github.com/Andertaker73/log-filter-tool.git
cd log_filter_tool
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

## Uso
Realize a importação da requisição utilizando o cURL abaixo:
```
curl --location 'http://127.0.0.1:5000/filter-log' \
--form 'log_file=@"/path/to/file"' \
--form 'concat_params="content/b2b-ecommerceequipments-servlets/ecommerceEquipmentWebService./orgUsers/anonymous/carts,content/b2b-ecommerceequipments-servlets/ecommerceEquipmentWebService./orgUsers/anonymous/orgUnits"' \
--form 'save_dir="C:\\Projetos\\AEM\\vivo\\automation"'
```

Envie arquivos de log no endpoint /filter-log com os parâmetros desejados para filtrar e gerar os arquivos processados.

