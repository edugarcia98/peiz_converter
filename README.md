# Conversor PEIZ - SQL
PEIZ é uma linguagem que possui o objetivo de simplificar a escrita de consultas SQL em **Microsoft SQL Server**.

## Configuração
Para se configurar o conversor PEIZ - SQL, inicialmente deve-se criar um novo ambiente virtual Python, clonar o repositório e instalar as bibliotecas necessárias. Esse procedimento pode ser realizado a partir dos seguintes comandos:

```
python -m venv [ENVIRONMENT_NAME]
cd [ENVIRONMENT_NAME]
Scripts\activate
git clone https://github.com/edugarcia98/peiz_converter.git
cd peiz_converter
pip install -r requirements.txt
```
Com o ambiente já configurado, deve-se então definir as variáveis de ambiente referentes ao banco de dados do Microsoft SQL Server que será acessado. Para isso, deve-se criar um arquivo com o nome **`sitecustomize.py`** no seguinte caminho do ambiente virtual:

```
[ENVIRONMENT_NAME]\Lib\site-packages
```
Criado este arquivo, deve-se então colar o seguinte código dentro do mesmo e preencher as informações de cada item:

```
import os

os.environ['DRIVER_SQL_SERVER'] =  'YOUR_DRIVER_SQL_SERVER'
os.environ['SERVER_SQL_SERVER'] =  'YOUR_SERVER_SQL_SERVER'
os.environ['TRUSTED_CONNECTION'] =  'IS_YOUR_CONNECTION_TRUSTED'
os.environ['USERNAME_SQL_SERVER'] =  'YOUR_USERNAME_SQL_SERVER'
os.environ['PASSWORD_SQL_SERVER'] =  'YOUR_PASSWORD_SQL_SERVER'
```

> Caso não seja necessário usuário e senha para acessar o Microsoft SQL Server, este arquivo pode ser configurado da seguinte maneira:
```
import os

os.environ['DRIVER_SQL_SERVER'] =  'YOUR_DRIVER_SQL_SERVER'
os.environ['SERVER_SQL_SERVER'] =  'YOUR_SERVER_SQL_SERVER'
os.environ['TRUSTED_CONNECTION'] =  'yes'
os.environ['USERNAME_SQL_SERVER'] =  ''
os.environ['PASSWORD_SQL_SERVER'] =  ''
```
Com o ambiente devidamente configurado, basta modificar o arquivo **`test_code.peiz`** e executar o arquivo  **`peiz_converter.py`** para gerar um arquivo SQL contendo todas as consultas implementadas no código PEIZ

## Conjunto de regras da linguagem PEIZ
### Legenda
```
k (keywords): db, tb, all, cols, filter, join, iwith, lwith, rwith, owith

id (identifiers): Ex.: nome, altura, X, Y
db (databases): Ex.: &Teste, &Sistema
t (tables): Ex.: _Carro, _Estacionamento
ti (table_identifier): Ex.: X.id, Y.cor

op (ops): :, ->
c (conditionals): =, !=, >, >=, <, <=
l (logic_operators): and, or, not

sep (separators): ,

od (opening_delimiters): (, [, {
cd (closing_delimiters): ), ], }
    
@: vazio
```

### Regras
```
statement ::= <k> ids expr | <k join> cols_join <op ->> <id> ( joins <id> <od [> <ti> <c> <ti> <cd ]> )+ fil

expr ::= <op :> ids | ( <k cols> <id> ( <sep ,> <id> )* )? <op ->>? cond_expr | @
cond_expr ::= ( <od (>? <id> <c> factor <cd )>? <l>? )*

cols_join ::= <k cols> <ti> ( <sep ,> <ti> )* | @
joins ::= <k iwith> | <k lwith> | <k rwith> | <k owith>
fil ::= <op ->> <k filter> ( <od (>? <ti> <c> factor <cd )>? <l>? )+ | @

ids ::= <id> | <db> | <t>
factor ::= <int> | <string> | <float>
```