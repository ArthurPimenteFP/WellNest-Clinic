# db.py — Módulo central de acesso ao banco de dados
# Qualquer arquivo que precise do banco importa apenas este módulo

import mysql.connector
from mysql.connector import Error, pooling
import os

# Parâmetros de conexão — editados apenas aqui, usados em todo o sistema
_DB_PARAMS = {
    'host':               'localhost',
    'port':               3307,
    'user':               'root',
    'password':           '',
    'database':           'wellnest_clinic',
    'charset':            'utf8mb4',
    'sql_mode':           ('STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,'
                           'ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'),
    'use_pure':           True,       # Python puro — compatível com todos os ambientes
    'connection_timeout': 10,         # desiste após 10s sem resposta
    'autocommit':         False,      # exige commit() explícito
}

_pool = None

# Pool criado uma única vez quando o módulo é carregado pela primeira vez.
# conn.close() devolve a conexão ao pool — não fecha fisicamente.
def criar_pool():
    global _pool # Chama a Variavel global

    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name='wellnest_pool',
            pool_size=5,           # conexões abertas permanentemente
            pool_reset_session=True,
            **_DB_PARAMS
        )


def get_connection():
    """Retorna uma conexão do pool. Levanta Exception em caso de falha."""
    try:
        if _pool is None:
            criar_pool() # Garante que teremos um pool
        return _pool.get_connection()
    except Error as e:
        raise Exception(f'Não foi possível obter conexão do pool: {e}')


def execute_query(sql, params=None, fetch=False):
    """
    Executa uma query SQL de forma segura.

    Parâmetros:
        sql    — string SQL com %s como placeholders
        params — tupla ou lista com os valores dos placeholders
        fetch  — True para SELECT (retorna lista de dicts); False para INSERT/UPDATE/DELETE

    Retorna:
        fetch=True  → lista de dicionários (cada linha = {'coluna': valor})
        fetch=False → número de linhas afetadas
    """
    conn = get_connection()
    try:
        # dictionary=True: cada linha retorna como dicionário — usuario['nome'] em vez de usuario[0]
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())

        if fetch:
            return cursor.fetchall()   # retorna todas as linhas
        else:
            conn.commit()              # confirma a transação
            return cursor.rowcount     # número de linhas afetadas

    except Error as e:
        conn.rollback()  # desfaz alterações parciais em caso de erro
        raise Exception(f'Erro ao executar query: {e}')
    finally:
        cursor.close()
        conn.close()   # devolve ao pool, não fecha fisicamente


def execute_one(sql, params=None):
    """
    Executa um SELECT e retorna apenas a primeira linha (ou None).
    Útil para buscar um registro por ID.
    """
    resultados = execute_query(sql, params, fetch=True)
    return resultados[0] if resultados else None


def iniciar_bd():
    try:
        conn = mysql.connector.connect(
            host = '127.0.0.1',
            port = 3307,
            user = 'root',
            password = ''
        )
        cursor = conn.cursor()

        arquivo_sql = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(arquivo_sql, 'r', encoding='utf-8') as f:
            script_sql = f.read()

        # multi=True pega cada sql; e separa para execução
        # fazendo cada comando ser executado separado
        for stmt in script_sql.split(';'):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)

        conn.commit()
        cursor.close()
        conn.close()
        print('Banco wellnest_clinic e tabelas inicializados com sucesso!')

    except Exception as e:
        print(f"Erro ao inicializar o banco de dados: {e}")