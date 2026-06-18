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

@app.route('/usuarios/cadastrar', methods=['GET', 'POST'])
@login_required
def usuarios_cadastrar():

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cpf = request.form.get('cpf', '').strip()
        data_nascimento = request.form.get('data_nascimento', '').strip() or None
        email = request.form.get('email', '').strip()
        celular = request.form.get('celular', '').strip()
        cep = request.form.get('cep', '').strip()
        logradouro = request.form.get('logradouro', '').strip()
        numero = request.form.get('numero', '').strip()
        complemento = request.form.get('complemento', '').strip()
        bairro = request.form.get('bairro', '').strip()
        cidade = request.form.get('cidade', '').strip()
        estado = request.form.get('estado', '').strip()
        senha = request.form.get('senha', '').strip()
        confirmar_senha = request.form.get('confirmar_senha', '').strip()
        funcao_id = request.form.get('funcao_id', '').strip()
        status = request.form.get('status', '').strip()

        if not all([nome, cpf, email, celular, estado, senha]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

        if senha != confirmar_senha:
            flash('As senhas não conferem.', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

        if len(senha) < 8:
            flash('A senha deve ter pelo menos 8 caracteres.', 'danger')
            return redirect(url_for('usuarios_cadastrar'))
        
        sql = '''SELECT nome AS qtde FROM usuarios
                WHERE email = %s OR cpf = %s;
                '''
        existente = execute_one(sql, (email, cpf))
        if existente:
            flash('E-mail ou CPF já cadastrados!', 'danger')
            return redirect(url_for('usuarios_cadastrar'))
        
        senha_hash = generate_password_hash(senha)
        
        try:
            execute_query(
                """INSERT INTO usuarios (nome, cpf, data_nascimento, email, celular,
                   cep, logradouro, numero, complemento, bairro, cidade, estado,
                   senha, status, funcao_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (nome, cpf, data_nascimento, email, celular,
                 cep, logradouro, numero, complemento, bairro, cidade, estado,
                 senha_hash, status, funcao_id)
            )
            flash('Usuário cadastrado com sucesso', 'success')
            return redirect(url_for('usuarios_listar'))
        except Exception as e:
            flash(f'Erro ao criar Usuário: {e}', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

    sql = 'SELECT id_funcao, nome FROM funcoes'
    lista_funcoes = execute_query(sql, fetch=True)
    return render_template('dashboard/usuarios/form.html', titulo='Cadastrar Usuário', modo='cadastrar', item=None, lista_funcoes=lista_funcoes)

@app.route('/usuarios/alterar/<int:id>', methods=['GET', 'POST'])
@login_required
def usuarios_alterar(id):

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        cpf = request.form.get('cpf', '').strip()
        data_nascimento = request.form.get('data_nascimento', '').strip() or None
        email = request.form.get('email', '').strip()
        celular = request.form.get('celular', '').strip()
        cep = request.form.get('cep', '').strip()
        logradouro = request.form.get('logradouro', '').strip()
        numero = request.form.get('numero', '').strip()
        complemento = request.form.get('complemento', '').strip()
        bairro = request.form.get('bairro', '').strip()
        cidade = request.form.get('cidade', '').strip()
        estado = request.form.get('estado', '').strip()
        senha = request.form.get('senha', '').strip()
        confirmar_senha = request.form.get('confirmar_senha', '').strip()
        funcao_id = request.form.get('funcao_id', '').strip()
        status = request.form.get('status', '').strip()

        if not all([nome, cpf, email, celular, estado]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('usuarios_alterar', id=id))

        existente = execute_one(
            '''SELECT id_usuario FROM usuarios
               WHERE (email = %s OR cpf = %s) AND id_usuario <> %s''',
            (email, cpf, id)
        )
        if existente:
            flash('E-mail ou CPF já cadastrados em outro usuário!', 'danger')
            return redirect(url_for('usuarios_alterar', id=id))

        if senha:
            if senha != confirmar_senha:
                flash('As senhas não conferem.', 'danger')
                return redirect(url_for('usuarios_alterar', id=id))
            if len(senha) < 8:
                flash('A senha deve ter pelo menos 8 caracteres.', 'danger')
                return redirect(url_for('usuarios_alterar', id=id))

        try:
            if senha:
                execute_query(
                    """UPDATE usuarios SET
                       nome=%s, cpf=%s, data_nascimento=%s, email=%s, celular=%s,
                       cep=%s, logradouro=%s, numero=%s, complemento=%s, bairro=%s,
                       cidade=%s, estado=%s, senha=%s, status=%s, funcao_id=%s
                       WHERE id_usuario=%s""",
                    (nome, cpf, data_nascimento, email, celular,
                     cep, logradouro, numero, complemento, bairro, cidade, estado,
                     generate_password_hash(senha), status, funcao_id, id)
                )
            else:
                execute_query(
                    """UPDATE usuarios SET
                       nome=%s, cpf=%s, data_nascimento=%s, email=%s, celular=%s,
                       cep=%s, logradouro=%s, numero=%s, complemento=%s, bairro=%s,
                       cidade=%s, estado=%s, status=%s, funcao_id=%s
                       WHERE id_usuario=%s""",
                    (nome, cpf, data_nascimento, email, celular,
                     cep, logradouro, numero, complemento, bairro, cidade, estado,
                     status, funcao_id, id)
                )
            flash('Usuário alterado com sucesso', 'success')
            return redirect(url_for('usuarios_listar'))
        except Exception as e:
            flash(f'Erro ao alterar Usuário: {e}', 'danger')
            return redirect(url_for('usuarios_alterar', id=id))

    item = execute_one('SELECT * FROM usuarios WHERE id_usuario = %s', (id,))
    if not item:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('usuarios_listar'))

    lista_funcoes = execute_query('SELECT id_funcao, nome FROM funcoes', fetch=True)
    return render_template('dashboard/usuarios/form.html', titulo='Alterar Usuário', modo='alterar', item=item, lista_funcoes=lista_funcoes)

@app.route('/usuarios/visualizar/<int:id>')
@login_required
def usuarios_visualizar(id):
    item = execute_one(
        '''SELECT u.*, f.nome AS funcao
           FROM usuarios AS u
           INNER JOIN funcoes AS f ON u.funcao_id = f.id_funcao
           WHERE u.id_usuario = %s''',
        (id,)
    )
    if not item:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('usuarios_listar'))
    return render_template('dashboard/usuarios/visualizar.html', item=item)

@app.route('/usuarios/excluir/<int:id>', methods=['POST'])
@login_required
def usuarios_excluir(id):
    try:
        execute_query('DELETE FROM usuarios WHERE id_usuario = %s', (id,))
        flash('Usuário excluído com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro ao excluir usuário: {e}', 'danger')
    return redirect(url_for('usuarios_listar'))

@app.route('/usuarios/relatorio')
@login_required
def usuarios_relatorio():
    return render_template('dashboard/usuarios/relatorio.html')

# ── Funções ───────────────────────────────────────────────────────────────────

@app.route('/funcoes/listar')
@login_required
def funcoes_listar():
    sql = '''
            SELECT 
                id_funcao, 
                nome, 
                status, 
                descricao, 
                gerenciar_funcao,
                gerenciar_usuario,
                gerenciar_paciente,
                gerenciar_consulta,
                criado_em,
                alterado_em
            FROM funcoes
            ORDER BY id_funcao DESC;
        '''
    lista_dados = execute_query(sql, fetch=True)
    return render_template('dashboard/funcoes/listar.html', 
    dados=lista_dados)

@app.route('/funcoes/cadastrar', methods=['GET', 'POST'])
@login_required
def funcoes_cadastrar():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        status = request.form.get('status', 'Ativo')
        descricao = request.form.get('descricao', '').strip()
        gerenciar_funcao = 1 if request.form.get('gerenciar_funcao') else 0
        gerenciar_usuario = 1 if request.form.get('gerenciar_usuario') else 0
        gerenciar_paciente = 1 if request.form.get('gerenciar_paciente') else 0
        gerenciar_consulta = 1 if request.form.get('gerenciar_consulta') else 0

        if not nome:
            flash('O campo <b>NOME</b> é obrigatório', 'danger')
            return redirect(url_for('funcoes_cadastrar'))

        try:
            sql = '''INSERT INTO funcoes (nome, status, descricao, gerenciar_funcao, gerenciar_usuario, gerenciar_paciente, gerenciar_consulta)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                '''
            dados = (nome, status, descricao, gerenciar_funcao, gerenciar_usuario, gerenciar_paciente, gerenciar_consulta)
            
            execute_query(sql, dados)
            flash(f'A função <b>{nome}</b> inserida com sucesso!', 'success')
            return redirect(url_for('funcoes_listar'))
            
        except Exception as e:
            flash(f'Erro ao salvar:{e}', 'danger')
            return redirect(url_for('funcoes_cadastrar'))
    
    return render_template('dashboard/funcoes/form.html', titulo='Cadastrar Função', modo='cadastrar', item=None)


@app.route('/funcoes/alterar/<int:id>', methods=['GET', 'POST'])
@login_required
def funcoes_alterar(id):
    item = execute_one(
        "SELECT * FROM funcoes WHERE id_funcao = %s",
        (id,)
    )

    if request.method == 'POST':
        nome = request.form.get('nome')
        status = request.form.get('status')
        descricao = request.form.get('descricao')
        gerenciar_funcao = 1 if request.form.get('gerenciar_funcao') else 0
        gerenciar_usuario = 1 if request.form.get('gerenciar_usuario') else 0
        gerenciar_paciente = 1 if request.form.get('gerenciar_paciente') else 0
        gerenciar_consulta = 1 if request.form.get('gerenciar_consulta') else 0

        # Atualiza os dados da função selecionada
        execute_query(
            """
            UPDATE funcoes
            SET nome=%s,
                status=%s,
                descricao=%s,
                gerenciar_funcao=%s,
                gerenciar_usuario=%s,
                gerenciar_paciente=%s,
                gerenciar_consulta=%s
            WHERE id_funcao=%s
            """,
            (
                nome,
                status,
                descricao,
                gerenciar_funcao,
                gerenciar_usuario,
                gerenciar_paciente,
                gerenciar_consulta,
                id
            )
        )

        flash('Função atualizada!', 'success')
        return redirect(url_for('funcoes_listar'))

    return render_template(
        'dashboard/funcoes/form.html',
        modo='alterar',
        item=item
    )


@app.route('/funcoes/visualizar/<int:id>')
@login_required
def funcoes_visualizar(id):
    item = execute_one(
        "SELECT * FROM funcoes WHERE id_funcao = %s",
        (id,)
    )
    return render_template('dashboard/funcoes/visualizar.html', item=item)


@app.route('/funcoes/excluir/<int:id>', methods=['POST'])
@login_required
def funcoes_excluir(id):
    execute_query(
        "DELETE FROM funcoes WHERE id_funcao = %s", (id,)
    )
    flash('Função removida com sucesso.', 'success')
    return redirect(url_for('funcoes_listar'))

@app.route('/funcoes/relatorio')
@login_required
def funcoes_relatorio():
    return render_template('dashboard/funcoes/relatorio.html')

@app.route('/pacientes/listar')
@login_required
def pacientes_listar():
    dados = execute_query("SELECT * FROM pacientes ORDER BY nome", fetch=True)
    return render_template('dashboard/pacientes/listar.html', dados=dados)


