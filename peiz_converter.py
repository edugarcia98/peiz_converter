import os

import re
import unidecode

import pyodbc

#Conexão com o banco de dados
DRIVER_SQL_SERVER = os.environ['DRIVER_SQL_SERVER']
SERVER_SQL_SERVER = os.environ['SERVER_SQL_SERVER']
TRUSTED_CONNECTION = os.environ['TRUSTED_CONNECTION']
USERNAME_SQL_SERVER = os.environ['USERNAME_SQL_SERVER']
PASSWORD_SQL_SERVER = os.environ['PASSWORD_SQL_SERVER']

# Tipos de Tokens
T_K = "keyword"

T_ID = "identifier"
T_DB = "database"
T_T = "table"
T_TI = "table_identifier"

T_OP = "op"
T_C = "conditional"
T_L = "logic_operator"

T_SEP = "separator"

T_OD = "opening"
T_CD = "closing"

T_INT = "int"
T_STRING = "string"

T_COMMENTARY = "commentary"
T_EOF = "eof"

class StopExecution(Exception):
    def _render_traceback(self):
        pass

class Token():

    def __init__(self, tipo, valor=None):
        self.tipo = tipo
        self.valor = valor
    
    def toDict(self):
        return {'%s' % self.tipo: '%s' % self.valor} 

def verify_token_matches_regex(token, expression):
    regex = re.compile(expression)
    r = regex.match(token)
    if (r is not None) and (r.group() == token):
        return True
    else:
        return False

def afd(token):
    if token in keywords:
        tipo = T_K
    elif token in operators:
        tipo = T_OP
    elif token in logic_operators:
        tipo = T_L
    elif token in conditionals:
        tipo = T_C
    elif token == ',':
        tipo = T_SEP
    elif token == '#':
        tipo = T_COMMENTARY
    elif token in opening_delimiters:
        tipo = T_OD
    elif token in closing_delimiters:
        tipo = T_CD
    elif verify_token_matches_regex(token, '[0-9]*'):
        tipo = T_INT
    elif verify_token_matches_regex(token, '".*"'):
        tipo = T_STRING
    elif verify_token_matches_regex(token, '&[a-zA-Z][a-zA-Z0-9_]*'):
        tipo = T_DB
    elif verify_token_matches_regex(token, '_[a-zA-Z][a-zA-Z0-9_]*'):
        tipo = T_T
    elif verify_token_matches_regex(token, '([a-zA-Z][a-zA-Z0-9_]*)\.([a-zA-Z][a-zA-Z0-9_]*)'):
        tipo = T_TI
    elif verify_token_matches_regex(token, '[a-zA-Z][a-zA-Z0-9_]*'):
        tipo = T_ID
    else:
        raise ValueError("Valor inesperado")

    return Token(tipo, token)

class Parser():

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = -1
        self.token_atual = None

        self.proximo()
    
    def proximo(self):
        self.pos += 1

        if self.pos >= len(self.tokens):
            self.token_atual = Token(T_EOF)
        else:
            self.token_atual = self.tokens[self.pos]
        
        #print('<' + self.token_atual.tipo + ' ' + str(self.token_atual.valor) + '>')
        return self.token_atual
    
    def erro(self):
        raise Exception('Sintaxe inválida')

    def exec(self, tipo, valor=None):
        
        if self.token_atual.tipo != tipo:
            self.erro()
        elif (valor is not None) and (self.token_atual.valor != valor):
            self.erro()
        else:
            self.proximo()

            if (tipo == T_L) and (self.token_atual.tipo == T_EOF):
                self.erro() 
    
    def statement(self):
        # statement ::= <k> ids expr | <k join> cols_join <op ->> <id> ( joins <id> <od [> <ti> <c> <ti> <cd ]> )+ fil
        if self.token_atual.tipo != T_COMMENTARY:
            if self.token_atual.tipo == T_K:

                if self.token_atual.valor == 'join':
                    self.exec(T_K, 'join')
                    self.cols_join()
                    self.exec(T_OP, '->')
                    self.exec(T_ID)
                    
                    needToDoJoins = True
                    while (needToDoJoins) or (self.token_atual.tipo == T_K):
                        self.joins()
                        self.exec(T_ID)
                        self.exec(T_OD, '[')
                        self.exec(T_TI)
                        self.exec(T_C)
                        self.exec(T_TI)
                        self.exec(T_CD, ']')
                        needToDoJoins = False
                    
                    self.fil()

                else:
                    self.exec(T_K)
                    self.ids()
                    self.expr()

            else:
                self.erro()
    
    def expr(self):
        # expr ::= <op :> ids | ( <k cols> <id> ( <sep ,> <id> )* )? <op ->>? cond_expr | @

        if not self.token_atual.tipo == T_EOF:

            if (self.token_atual.tipo == T_OP) and (self.token_atual.valor == ':'):
                self.exec(T_OP, ':')
                self.ids()
            else:
                
                if (self.token_atual.tipo == T_K) and (self.token_atual.valor == 'cols'):
                    self.exec(T_K, 'cols')
                    self.exec(T_ID)
                    while self.token_atual.tipo == T_SEP:
                        self.exec(T_SEP)
                        self.exec(T_ID)

                if (self.token_atual.tipo == T_OP) and (self.token_atual.valor == '->'):
                    self.exec(T_OP, '->')
                
                self.cond_expr()

    def cond_expr(self):
        # Utilizar recursividade para os exemplos: 
        # (id = 30 and (cor = "red" or cor = "blue")) or id = 15
        # (id = 30 and (cor = "red" or cor = "blue") and tipo = "sedan") or id = 15
        # id = 1 or (id = 30 and (cor = "red" or cor = "blue") and tipo = "sedan") or id = 15
        # cond_expr ::= ( <od (>? <id> <c> factor <cd )>? <l>? )*
        count_fechamentos = 0

        # verificar se fechamentos == 0 também
        while (self.token_atual.tipo != T_EOF) or (count_fechamentos != 0):

            if (self.token_atual.tipo == T_OD) and (self.token_atual.valor == '('):
                self.exec(T_OD, '(')
                count_fechamentos += 1
                #criar variável para contar fechamentos

            self.exec(T_ID)
            self.exec(T_C)
            self.factor()

            # jogar while para enquanto for isso, realizar
            while (self.token_atual.tipo == T_CD) and (self.token_atual.valor == ')'):
                self.exec(T_CD, ')')
                count_fechamentos -= 1
            
            if (not self.token_atual.tipo == T_EOF):
                self.exec(T_L)

    def cols_join(self):
        # cols_join ::= <k cols> <ti> ( <sep ,> <ti> )* | @

        if (self.token_atual.tipo == T_K) and (self.token_atual.valor == 'cols'):
            self.exec(T_K, 'cols')
            self.exec(T_TI)
            #self.exec(T_ID)
            #self.exec(T_OD, '{')
            #self.exec(T_ID)
            #self.exec(T_CD, '}')
            while self.token_atual.tipo == T_SEP:
                self.exec(T_SEP)
                self.exec(T_TI)
                #self.exec(T_ID)
                #self.exec(T_OD, '{')
                #self.exec(T_ID)
                #self.exec(T_CD, '}')

    def fil(self):
        # fil ::= <op ->> <k filter> ( <od (>? <ti> <c> factor <cd )>? <l>? )+ | @
        if (self.token_atual.tipo == T_OP) and (self.token_atual.valor == '->'):
            self.exec(T_OP, '->')
            self.exec(T_K, 'filter')
            needToCompare = True
            while (needToCompare) or (self.token_atual.tipo != T_EOF):
                if (self.token_atual.tipo == T_OD) and (self.token_atual.valor == '('):
                    self.exec(T_OD, '(')

                self.exec(T_TI)
                self.exec(T_C)
                self.factor()

                if (self.token_atual.tipo == T_CD) and (self.token_atual.valor == ')'):
                    self.exec(T_CD, ')')
                
                if (not self.token_atual.tipo == T_EOF):
                    self.exec(T_L)
                
                needToCompare = False

    def joins(self):
        # joins ::= <k iwith> | <k lwith> | <k rwith> | <k owith>
        if (self.token_atual.tipo == T_K) and (self.token_atual.valor in ['iwith', 'lwith', 'rwith', 'owith']):
            self.exec(self.token_atual.tipo)
        else:
            self.erro

    def ids(self):
        # ids ::= <id> | <db> | <t>
        if self.token_atual.tipo in [T_ID, T_DB, T_T]:
            self.exec(self.token_atual.tipo)
        else:
            self.erro()

    def factor(self):
        # factor ::= <int> | <string>
        if self.token_atual.tipo in [T_INT, T_STRING]:
            self.exec(self.token_atual.tipo)
        else:
            self.erro()

class GeneralSemantic():

    def __init__(self):
        self.db = None
        self._cursor = None
        self._table_items = {}

    def _connect_to_db(self):
        #print("Conectando-se ao banco de dados {}...".format(self.db))
        try:

            if TRUSTED_CONNECTION == 'yes':
                connection = pyodbc.connect(
                    r'DRIVER=' + DRIVER_SQL_SERVER + r';'
                    r'SERVER=' + SERVER_SQL_SERVER + r';'
                    r'DATABASE=' + self.db + r';'
                    r'Trusted_Connection=' + TRUSTED_CONNECTION + r';'
                )
            else:
                connection = pyodbc.connect(
                    r'DRIVER=' + DRIVER_SQL_SERVER + r';'
                    r'SERVER=' + SERVER_SQL_SERVER + r';'
                    r'DATABASE=' + self.db + r';'
                    r'UID=' + USERNAME_SQL_SERVER + r';'
                    r'PWD=' + PASSWORD_SQL_SERVER + r';'
                )

            #print("Conectado ao banco de dados {}!".format(self.db))
            self._cursor = connection.cursor()

        except Exception as e:
            raise Exception(e)
    
    def final_analysis(self):
        if self.db == None:
            raise Exception("Nenhum banco de dados especificado.")

class SingleSemantic():

    def __init__(self, tokens, general):
        self.tokens = tokens
        self.__general = general
        self.__is_join = False
        self.__is_atribuicao = False
        self.__list_ids = []
    
    def __get_table_fields(self, table):
        items = [item[0] for item in list(self.__general._cursor.execute("select COLUMN_NAME from INFORMATION_SCHEMA.COLUMNS where TABLE_NAME='Jogo'"))]
        
        for token in self.tokens:
            if token.tipo == T_ID:
                self.__general._table_items[token.valor] = {
                    'name': table,
                    'fields': items
                }
                break
    
    def __check_field_in_table(self):
        table = ''
        for item in self.__list_ids:
            if item in self.__general._table_items.keys():
                table = item
                break
        self.__list_ids.remove(table)
        
        for item in self.__list_ids:
            if not item in self.__general._table_items[table]['fields']:
                raise Exception("Campo \"{}\" não existe na tabela {}.".format(item, self.__general._table_items[table]['name']))
    
    def __check_field_in_table_join(self):
        for item in self.__list_ids:
            field = item.split('.')
            if not field[1] in self.__general._table_items[field[0]]['fields']:
                raise Exception("Campo \"{}\" não existe na tabela {}.".format(field[1], self.__general._table_items[field[0]]['name']))
    
    def analyze(self):
        if self.tokens[0].tipo == T_K and self.tokens[0].valor == 'join':
                self.__is_join = True

        for token in self.tokens:
            if token.tipo == T_DB:
                self.__is_atribuicao = True

                db = token.valor.replace('&', '')
                self.__general.db = db
                self.__general._connect_to_db()
            elif token.tipo == T_T:
                self.__is_atribuicao = True

                table = token.valor.replace('_', '')
                self.__get_table_fields(table)
            
            if self.__is_join:
                if token.tipo == T_TI:
                    self.__list_ids.append(token.valor)
            else:
                if token.tipo == T_ID:
                    self.__list_ids.append(token.valor)

        if not self.__is_atribuicao:
            if self.__is_join:
                self.__check_field_in_table_join()
            else:
                self.__check_field_in_table()

class SQLConverter():

    def __init__(self, general, tokens):
        self.__general = general
        self.tokens = tokens
        self.__converter_dict = {
            'db': 'USE [{}]',
            'all': 'SELECT {} FROM {}',
            'filter': {
                True: 'SELECT {} FROM {} WHERE {}',
                False: 'WHERE {}'
            },
            'join': 'SELECT {} FROM {} ',
            'iwith': 'INNER JOIN',
            'lwith': 'LEFT JOIN',
            'rwith': 'RIGHT JOIN',
            'owith': 'FULL OUTER JOIN'
        }

    def __column_text(self, columns, key, tables):
        if len(columns) <= 0:
            if key == 'join':
                tables = [(table + '.*') for table in tables]
                return ', '.join(tables)
            else:          
                return '*'
        else:
            return ', '.join(columns)

    def convert_to_sql(self):
        key = ''
        sentence = ''

        is_first = True
        preenche_lista_cols = False
        preenche_filtro = False
        preenche_join = False
        join_has_filter = False

        columns = []
        tables = []
        filter_parameters = []
        join_list = []
        
        for token in self.tokens:
            if (token.tipo == T_K) and (token.valor in self.__converter_dict.keys()):
                if (is_first) or (token.valor == 'filter'):       
                    if token.valor == 'filter':
                        sentence += self.__converter_dict[token.valor][is_first]
                    else:
                        sentence += self.__converter_dict[token.valor]
                    
                    if is_first:
                        key = token.valor
                    else:
                        join_has_filter = True

                if preenche_join:
                    join_list.append(self.__converter_dict[token.valor])
            else:
                if key == 'db':
                    sentence = sentence.format(token.valor.replace('&', ''))

                if preenche_join and not (token.tipo in [T_CD, T_ID, T_OP]):
                    if (token.tipo == T_OD and token.valor == '['):
                        join_list.append('ON')
                    else:
                        join_list.append(token.valor)

                if (key == 'join') and (token.tipo == T_OP and token.valor == '->'):
                    preenche_join = not preenche_join

                if preenche_filtro or join_has_filter:
                    filter_parameters.append(token.valor.replace("\"", "\'"))
                
                if (token.tipo == T_K) and (token.valor == 'cols'):
                    preenche_lista_cols = True
                
                if (token.tipo == T_OP) and (token.valor == '->'):
                    preenche_lista_cols = False
                    if key == 'filter':
                        preenche_filtro = True

                if (token.tipo == T_ID or token.tipo == T_TI) and (preenche_lista_cols) and (key in ['all', 'filter', 'join']):
                    columns.append(token.valor)
                
                if (token.tipo == T_ID) and (token.valor in self.__general._table_items.keys()):
                    if preenche_join:
                        join_list.append('{} AS {}'.format(self.__general._table_items[token.valor]['name'], token.valor))
                        tables.append(token.valor)
                    else:
                        tables.append(self.__general._table_items[token.valor]['name'])
                    
            
            is_first = False
        
        if key == 'all':
            sentence = sentence.format(self.__column_text(columns, key, tables), tables[0])
        
        if key == 'filter':
            sentence = sentence.format(self.__column_text(columns, key, tables), tables[0], ' '.join(filter_parameters))
        
        if key == 'join':
            if join_has_filter:
                sentence = sentence.format(self.__column_text(columns, key, tables), ' '.join(join_list), ' '.join(filter_parameters))
            else:
                sentence = sentence.format(self.__column_text(columns, key, tables), ' '.join(join_list))

        return sentence


keywords = ['db', 'tb', 'all', 'cols', 'filter', 'join', 'iwith', 'lwith', 'rwith', 'owith']
operators = [':', '->']
logic_operators = ['and', 'or', 'not']
conditionals = ['=', '!=', '>', '>=', '<', '<=']
opening_delimiters = ['(', '[', '{']
closing_delimiters = [')', ']', '}']

is_string_closed = True

file = open('test_code.peiz', 'r', encoding='utf-8')

with open('peiz_converted_to_sql.sql', 'a', encoding='utf-8') as sql_file:
    try:

        general = GeneralSemantic()

        ln = 1
        for line in file.readlines():
            line = line.replace('\n', '')
            line = unidecode.unidecode(line)

            is_commentary = False

            if line != '':
                tokens = []
                value = ''
                for token in line.split(' '):
                    if token.count("\"") == 1:
                        is_string_closed = not is_string_closed
                    
                    value += token + ' '

                    if is_string_closed:
                        try:
                            token = afd(value.strip())
                            tokens.append(token)
                            value = ''

                            if token.toDict() == {T_COMMENTARY: '#'}:
                                is_commentary = True
                                break
                        except Exception as e:
                            print(line)
                            print(str(e) + " na coluna %i da linha %i" % (line.index(value), ln))
                            raise StopExecution


                #print([token.toDict() for token in tokens])
                parser = Parser(tokens)
                parser.statement()

                if not is_commentary:
                    semantic = SingleSemantic(tokens, general)
                    semantic.analyze()

                sqlConverter = SQLConverter(general, tokens)
                sentence = sqlConverter.convert_to_sql() + '\n'
                sql_file.write(sentence)

            ln += 1

        general.final_analysis()

        sql_file.close()
        print("Código SQL gerado com sucesso")
    
    except Exception as e:
        print(e)
        sql_file.close()
        os.remove('peiz_converted_to_sql.sql')