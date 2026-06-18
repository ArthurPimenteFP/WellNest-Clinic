from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from db import execute_one, iniciar_bd, execute_query
from werkzeug.security import generate_password_hash, check_password_hash

import datetime

app = Flask(__name__)
app.secret_key = 'wellnest-clinic-secret-2026'

iniciar_bd() # inicia o BD e as tabelas

def garantir_admin():
    """Cria um administrador padrão caso não exista nenhum usuário (evita lockout)."""
    try:
        total = execute_one('SELECT COUNT(*) AS total FROM usuarios')
        if total and total['total'] == 0:
            funcao = execute_one("SELECT id_funcao FROM funcoes WHERE nome = %s", ('Administrador',))
            if not funcao:
                execute_query(
                    """INSERT INTO funcoes (nome, status, descricao,
                       gerenciar_funcao, gerenciar_usuario, gerenciar_paciente, gerenciar_consulta)
                       VALUES (%s, 'Ativo', %s, 1, 1, 1, 1)""",
                    ('Administrador', 'Acesso total ao sistema')
                )
                funcao = execute_one("SELECT id_funcao FROM funcoes WHERE nome = %s", ('Administrador',))
            execute_query(
                """INSERT INTO usuarios (nome, cpf, email, celular, estado, senha, status, funcao_id)
                   VALUES (%s, %s, %s, %s, %s, %s, 'Ativo', %s)""",
                ('Administrador', '000.000.000-00', 'admin@wellnest.com', '(00) 00000-0000', 'SP',
                 generate_password_hash('admin1234'), funcao['id_funcao'])
            )
            print('Usuário administrador padrão criado: admin@wellnest.com / admin1234')
    except Exception as e:
        print(f'Erro ao garantir admin: {e}')


garantir_admin()


def login_required(f):
    """Bloqueia o acesso às rotas do dashboard quando não há usuário logado."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('usuario'):
            flash('Faça login para acessar o sistema.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


@app.context_processor
def injetar_usuario():
    """Disponibiliza o usuário logado em todos os templates."""
    return dict(usuario_logado=session.get('usuario'))

# ── Rotas públicas ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sobre')
def sobre():
    return render_template('sobre_equipe.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()

        usuario = execute_one(
            '''SELECT u.id_usuario, u.nome, u.email, u.senha, u.status,
                      f.nome AS funcao,
                      f.gerenciar_funcao, f.gerenciar_usuario,
                      f.gerenciar_paciente, f.gerenciar_consulta
               FROM usuarios AS u
               INNER JOIN funcoes AS f ON u.funcao_id = f.id_funcao
               WHERE u.email = %s''',
            (email,)
        )

        if not usuario or not check_password_hash(usuario['senha'], senha):
            flash('E-mail ou senha inválidos.', 'danger')
            return redirect(url_for('login'))

        if usuario['status'] != 'Ativo':
            flash('Usuário inativo. Contate o administrador.', 'warning')
            return redirect(url_for('login'))

        partes = usuario['nome'].split()
        iniciais = (partes[0][0] + partes[-1][0]).upper() if len(partes) > 1 else partes[0][:2].upper()

        session['usuario'] = {
            'id': usuario['id_usuario'],
            'nome': usuario['nome'],
            'email': usuario['email'],
            'funcao': usuario['funcao'],
            'iniciais': iniciais,
            'gerenciar_funcao': usuario['gerenciar_funcao'],
            'gerenciar_usuario': usuario['gerenciar_usuario'],
            'gerenciar_paciente': usuario['gerenciar_paciente'],
            'gerenciar_consulta': usuario['gerenciar_consulta'],
        }
        flash(f'Bem-vindo(a), {usuario["nome"]}!', 'success')
        return redirect(url_for('home'))

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        # salvar usuário
        return redirect(url_for('login'))

    return render_template('auth/register.html')

@app.route('/recuperar-senha')
def recuperar_senha():
    return render_template('auth/forgot_password.html')

# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/home')
@login_required
def home():
    return render_template('dashboard/home.html')

@app.route('/usuarios/listar')
@login_required
def usuarios_listar():
    sql = '''
            SELECT
                id_usuario,
                u.nome AS nome,
                email,
                celular,
                f.nome AS funcao,
                u.status
            FROM usuarios AS u
            INNER JOIN funcoes AS f ON u.funcao_id = f.id_funcao
            ORDER BY id_usuario DESC;                
        '''
    lista_dados = execute_query(sql, fetch=True)
    return render_template('dashboard/usuarios/listar.html', dados=lista_dados)

