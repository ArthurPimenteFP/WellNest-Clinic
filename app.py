"""
APP.PY - ARQUIVO PRINCIPAL DO SISTEMA

Este arquivo:
- Inicializa o Flask.
- Controla autenticação (login/logout).
- Gerencia sessões.
- Define todas as rotas do sistema.
- Executa operações CRUD de Usuários, Funções, Pacientes e Consultas.
- Renderiza templates HTML.
- Utiliza funções do db.py para acesso ao banco de dados.

OBSERVAÇÃO:
Os comentários originais foram preservados e complementados por este bloco
explicativo para facilitar a apresentação e entendimento do projeto.
"""

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from db import execute_one, execute_query, iniciar_bd
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'wellnest-clinic-secret-2026'

def fix_timedelta(rows):
    """Converte campos hora de timedelta para time (MySQL retorna TIME como timedelta)."""
    import datetime
    for row in (rows or []):
        if isinstance(row.get('hora'), datetime.timedelta):
            total = int(row['hora'].total_seconds())
            row['hora'] = datetime.time(total // 3600, (total % 3600) // 60, total % 60)
    return rows

iniciar_bd()  # Inicia o BD e as tabelas ao subir o app


def garantir_admin():
    """Cria um administrador padrão caso não exista nenhum usuário (evita lockout)."""
    try:
        total = execute_one('SELECT COUNT(*) AS total FROM usuarios')
        if total and total['total'] == 0:
            funcao = execute_one("SELECT id_funcao FROM funcoes WHERE nome = %s", ('Administrador',))
            if funcao:
                execute_query(
                    """INSERT INTO usuarios (nome, cpf, email, celular, estado, senha, status, funcao_id)
                       VALUES (%s, %s, %s, %s, %s, %s, 'Ativo', %s)""",
                    ('Administrador', '000.000.000-00', 'admin@wellnest.com',
                     '(00) 00000-0000', 'SP',
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
            'id':                  usuario['id_usuario'],
            'nome':                usuario['nome'],
            'email':               usuario['email'],
            'funcao':              usuario['funcao'],
            'iniciais':            iniciais,
            'gerenciar_funcao':    usuario['gerenciar_funcao'],
            'gerenciar_usuario':   usuario['gerenciar_usuario'],
            'gerenciar_paciente':  usuario['gerenciar_paciente'],
            'gerenciar_consulta':  usuario['gerenciar_consulta'],
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
        nome            = request.form.get('nome', '').strip()
        email           = request.form.get('email', '').strip()
        senha           = request.form.get('senha', '').strip()
        confirmar_senha = request.form.get('confirmar_senha', '').strip()

        if not all([nome, email, senha, confirmar_senha]):
            flash('Preencha todos os campos.', 'warning')
            return render_template('auth/register.html')

        if senha != confirmar_senha:
            flash('As senhas não coincidem.', 'warning')
            return render_template('auth/register.html')

        if len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'warning')
            return render_template('auth/register.html')

        if execute_one('SELECT id_usuario FROM usuarios WHERE email=%s', (email,)):
            flash('E-mail já cadastrado.', 'danger')
            return render_template('auth/register.html')

        # Busca a função padrão (primeira função ativa disponível)
        funcao = execute_one("SELECT id_funcao FROM funcoes WHERE status='Ativo' ORDER BY id_funcao LIMIT 1")
        if not funcao:
            flash('Nenhuma função disponível. Contate o administrador.', 'danger')
            return render_template('auth/register.html')

        try:
            import uuid
            # Gera placeholder único pois CPF é NOT NULL UNIQUE no banco
            cpf_placeholder = f'ID-{uuid.uuid4().hex[:11].upper()}'
            execute_query(
                """INSERT INTO usuarios (nome, cpf, email, celular, estado, senha, status, funcao_id)
                   VALUES (%s, %s, %s, %s, %s, %s, 'Ativo', %s)""",
                (nome, cpf_placeholder, email, '', 'SP',
                 generate_password_hash(senha), funcao['id_funcao'])
            )
            flash('Cadastro realizado com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Erro ao cadastrar: {e}', 'danger')
            return render_template('auth/register.html')

    return render_template('auth/register.html')

@app.route('/recuperar-senha')
def recuperar_senha():
    return render_template('auth/forgot_password.html')


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/home')
@login_required
def home():
    stats = {
        'agendadas':  (execute_one("SELECT COUNT(*) AS t FROM consultas WHERE status='Agendada'") or {}).get('t', 0),
        'realizadas': (execute_one("SELECT COUNT(*) AS t FROM consultas WHERE status='Realizada'") or {}).get('t', 0),
        'canceladas': (execute_one("SELECT COUNT(*) AS t FROM consultas WHERE status='Cancelada'") or {}).get('t', 0),
        'pacientes':  (execute_one("SELECT COUNT(*) AS t FROM pacientes") or {}).get('t', 0),
    }
    consultas_recentes = fix_timedelta(execute_query(
        '''SELECT c.id_consulta, p.nome AS paciente, u.nome AS medico,
                  c.data, c.hora, c.especialidade, c.status
           FROM consultas c
           JOIN pacientes p ON c.paciente_id = p.id_paciente
           JOIN usuarios u  ON c.medico_id   = u.id_usuario
           ORDER BY c.criado_em DESC LIMIT 5''',
        fetch=True
    ))
    return render_template('dashboard/home.html', stats=stats, consultas_recentes=consultas_recentes)


# ── Usuários ──────────────────────────────────────────────────────────────────

@app.route('/usuarios/listar')
@login_required
def usuarios_listar():
    dados = execute_query(
        '''SELECT u.id_usuario, u.nome, u.email, u.celular, f.nome AS funcao, u.status
           FROM usuarios u INNER JOIN funcoes f ON u.funcao_id = f.id_funcao
           ORDER BY u.id_usuario DESC''',
        fetch=True
    )
    return render_template('dashboard/usuarios/listar.html', dados=dados)


@app.route('/usuarios/cadastrar', methods=['GET', 'POST'])
@login_required
def usuarios_cadastrar():
    if request.method == 'POST':
        nome            = request.form.get('nome', '').strip()
        cpf             = request.form.get('cpf', '').strip()
        data_nascimento = request.form.get('data_nascimento', '').strip() or None
        email           = request.form.get('email', '').strip()
        celular         = request.form.get('celular', '').strip()
        cep             = request.form.get('cep', '').strip()
        logradouro      = request.form.get('logradouro', '').strip()
        numero          = request.form.get('numero', '').strip()
        complemento     = request.form.get('complemento', '').strip()
        bairro          = request.form.get('bairro', '').strip()
        cidade          = request.form.get('cidade', '').strip()
        estado          = request.form.get('estado', '').strip()
        senha           = request.form.get('senha', '').strip()
        confirmar_senha = request.form.get('confirmar_senha', '').strip()
        funcao_id       = request.form.get('funcao_id', '').strip()
        status          = request.form.get('status', 'Ativo').strip()

        if not all([nome, cpf, email, celular, estado, senha]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

        if senha != confirmar_senha:
            flash('As senhas não conferem.', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

        if len(senha) < 8:
            flash('A senha deve ter pelo menos 8 caracteres.', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

        if execute_one('SELECT id_usuario FROM usuarios WHERE email=%s OR cpf=%s', (email, cpf)):
            flash('E-mail ou CPF já cadastrados!', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

        try:
            execute_query(
                """INSERT INTO usuarios
                   (nome, cpf, data_nascimento, email, celular, cep, logradouro, numero,
                    complemento, bairro, cidade, estado, senha, status, funcao_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (nome, cpf, data_nascimento, email, celular, cep, logradouro, numero,
                 complemento, bairro, cidade, estado, generate_password_hash(senha), status, funcao_id)
            )
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('usuarios_listar'))
        except Exception as e:
            flash(f'Erro ao cadastrar usuário: {e}', 'danger')
            return redirect(url_for('usuarios_cadastrar'))

    lista_funcoes = execute_query('SELECT id_funcao, nome FROM funcoes WHERE status=%s', ('Ativo',), fetch=True)
    return render_template('dashboard/usuarios/form.html', titulo='Cadastrar Usuário', modo='cadastrar', item=None, lista_funcoes=lista_funcoes)


@app.route('/usuarios/alterar/<int:id>', methods=['GET', 'POST'])
@login_required
def usuarios_alterar(id):
    if request.method == 'POST':
        nome            = request.form.get('nome', '').strip()
        cpf             = request.form.get('cpf', '').strip()
        data_nascimento = request.form.get('data_nascimento', '').strip() or None
        email           = request.form.get('email', '').strip()
        celular         = request.form.get('celular', '').strip()
        cep             = request.form.get('cep', '').strip()
        logradouro      = request.form.get('logradouro', '').strip()
        numero          = request.form.get('numero', '').strip()
        complemento     = request.form.get('complemento', '').strip()
        bairro          = request.form.get('bairro', '').strip()
        cidade          = request.form.get('cidade', '').strip()
        estado          = request.form.get('estado', '').strip()
        senha           = request.form.get('senha', '').strip()
        confirmar_senha = request.form.get('confirmar_senha', '').strip()
        funcao_id       = request.form.get('funcao_id', '').strip()
        status          = request.form.get('status', 'Ativo').strip()

        if not all([nome, cpf, email, celular, estado]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('usuarios_alterar', id=id))

        if execute_one('SELECT id_usuario FROM usuarios WHERE (email=%s OR cpf=%s) AND id_usuario<>%s', (email, cpf, id)):
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
                    """UPDATE usuarios SET nome=%s,cpf=%s,data_nascimento=%s,email=%s,celular=%s,
                       cep=%s,logradouro=%s,numero=%s,complemento=%s,bairro=%s,cidade=%s,estado=%s,
                       senha=%s,status=%s,funcao_id=%s WHERE id_usuario=%s""",
                    (nome,cpf,data_nascimento,email,celular,cep,logradouro,numero,complemento,
                     bairro,cidade,estado,generate_password_hash(senha),status,funcao_id,id)
                )
            else:
                execute_query(
                    """UPDATE usuarios SET nome=%s,cpf=%s,data_nascimento=%s,email=%s,celular=%s,
                       cep=%s,logradouro=%s,numero=%s,complemento=%s,bairro=%s,cidade=%s,estado=%s,
                       status=%s,funcao_id=%s WHERE id_usuario=%s""",
                    (nome,cpf,data_nascimento,email,celular,cep,logradouro,numero,complemento,
                     bairro,cidade,estado,status,funcao_id,id)
                )
            flash('Usuário alterado com sucesso!', 'success')
            return redirect(url_for('usuarios_listar'))
        except Exception as e:
            flash(f'Erro ao alterar usuário: {e}', 'danger')
            return redirect(url_for('usuarios_alterar', id=id))

    item = execute_one(
        'SELECT u.*, f.nome AS funcao FROM usuarios u JOIN funcoes f ON u.funcao_id=f.id_funcao WHERE u.id_usuario=%s', (id,)
    )
    if not item:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('usuarios_listar'))
    lista_funcoes = execute_query('SELECT id_funcao, nome FROM funcoes', fetch=True)
    return render_template('dashboard/usuarios/form.html', titulo='Alterar Usuário', modo='alterar', item=item, lista_funcoes=lista_funcoes)


@app.route('/usuarios/visualizar/<int:id>')
@login_required
def usuarios_visualizar(id):
    item = execute_one(
        'SELECT u.*, f.nome AS funcao FROM usuarios u JOIN funcoes f ON u.funcao_id=f.id_funcao WHERE u.id_usuario=%s', (id,)
    )
    if not item:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('usuarios_listar'))
    return render_template('dashboard/usuarios/visualizar.html', item=item)


@app.route('/usuarios/excluir/<int:id>', methods=['POST'])
@login_required
def usuarios_excluir(id):
    try:
        execute_query('DELETE FROM usuarios WHERE id_usuario=%s', (id,))
        flash('Usuário excluído com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro ao excluir usuário: {e}', 'danger')
    return redirect(url_for('usuarios_listar'))


@app.route('/usuarios/relatorio')
@login_required
def usuarios_relatorio():
    nome   = request.args.get('nome', '').strip()
    status = request.args.get('status', '').strip()
    funcao = request.args.get('funcao', '').strip()
    filtros_ativos = any([nome, status, funcao])
    dados = None
    if filtros_ativos:
        sql = '''SELECT u.id_usuario, u.nome, u.email, u.celular, f.nome AS funcao, u.status
                 FROM usuarios u INNER JOIN funcoes f ON u.funcao_id = f.id_funcao WHERE 1=1'''
        params = []
        if nome:   sql += ' AND u.nome LIKE %s';   params.append(f'%{nome}%')
        if status: sql += ' AND u.status = %s';    params.append(status)
        if funcao: sql += ' AND f.nome LIKE %s';   params.append(f'%{funcao}%')
        sql += ' ORDER BY u.nome'
        dados = execute_query(sql, tuple(params), fetch=True) or []
    funcoes_lista = execute_query('SELECT nome FROM funcoes ORDER BY nome', fetch=True) or []
    return render_template('dashboard/usuarios/relatorio.html',
                           dados=dados, filtros_ativos=filtros_ativos, funcoes_lista=funcoes_lista,
                           f_nome=nome, f_status=status, f_funcao=funcao)


# ── Funções ───────────────────────────────────────────────────────────────────

@app.route('/funcoes/listar')
@login_required
def funcoes_listar():
    dados = execute_query(
        'SELECT * FROM funcoes ORDER BY id_funcao DESC', fetch=True
    )
    return render_template('dashboard/funcoes/listar.html', dados=dados)


@app.route('/funcoes/cadastrar', methods=['GET', 'POST'])
@login_required
def funcoes_cadastrar():
    if request.method == 'POST':
        nome               = request.form.get('nome', '').strip()
        status             = request.form.get('status', 'Ativo')
        descricao          = request.form.get('descricao', '').strip()
        gerenciar_usuario  = 1 if request.form.get('gerenciar_usuario') else 0
        gerenciar_funcao   = 1 if request.form.get('gerenciar_funcao') else 0
        gerenciar_paciente = 1 if request.form.get('gerenciar_paciente') else 0
        gerenciar_consulta = 1 if request.form.get('gerenciar_consulta') else 0

        if not nome:
            flash('O nome da função é obrigatório!', 'danger')
            return redirect(url_for('funcoes_cadastrar'))

        # Verifica duplicata ignorando acentos/maiúsculas
        if execute_one('SELECT id_funcao FROM funcoes WHERE nome=%s', (nome,)):
            flash(f'Já existe uma função com o nome <b>{nome}</b>!', 'danger')
            return redirect(url_for('funcoes_cadastrar'))

        try:
            execute_query(
                """INSERT INTO funcoes (nome, status, descricao, gerenciar_usuario,
                   gerenciar_funcao, gerenciar_paciente, gerenciar_consulta)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (nome, status, descricao, gerenciar_usuario, gerenciar_funcao, gerenciar_paciente, gerenciar_consulta)
            )
            flash(f'Função <b>{nome}</b> cadastrada com sucesso!', 'success')
            return redirect(url_for('funcoes_listar'))
        except Exception as e:
            flash(f'Já existe uma função com esse nome!', 'danger')
            return redirect(url_for('funcoes_cadastrar'))

    return render_template('dashboard/funcoes/form.html', titulo='Cadastrar Função', modo='cadastrar', item=None)


@app.route('/funcoes/alterar/<int:id>', methods=['GET', 'POST'])
@login_required
def funcoes_alterar(id):
    if request.method == 'POST':
        nome               = request.form.get('nome', '').strip()
        status             = request.form.get('status', 'Ativo')
        descricao          = request.form.get('descricao', '').strip()
        gerenciar_usuario  = 1 if request.form.get('gerenciar_usuario') else 0
        gerenciar_funcao   = 1 if request.form.get('gerenciar_funcao') else 0
        gerenciar_paciente = 1 if request.form.get('gerenciar_paciente') else 0
        gerenciar_consulta = 1 if request.form.get('gerenciar_consulta') else 0

        if not nome:
            flash('O nome da função é obrigatório!', 'danger')
            return redirect(url_for('funcoes_alterar', id=id))

        try:
            execute_query(
                """UPDATE funcoes SET nome=%s,status=%s,descricao=%s,gerenciar_usuario=%s,
                   gerenciar_funcao=%s,gerenciar_paciente=%s,gerenciar_consulta=%s
                   WHERE id_funcao=%s""",
                (nome, status, descricao, gerenciar_usuario, gerenciar_funcao, gerenciar_paciente, gerenciar_consulta, id)
            )
            flash('Função alterada com sucesso!', 'success')
            return redirect(url_for('funcoes_listar'))
        except Exception as e:
            flash(f'Erro ao alterar função: {e}', 'danger')
            return redirect(url_for('funcoes_alterar', id=id))

    item = execute_one('SELECT * FROM funcoes WHERE id_funcao=%s', (id,))
    if not item:
        flash('Função não encontrada.', 'danger')
        return redirect(url_for('funcoes_listar'))
    return render_template('dashboard/funcoes/form.html', titulo='Alterar Função', modo='alterar', item=item)


@app.route('/funcoes/visualizar/<int:id>')
@login_required
def funcoes_visualizar(id):
    item = execute_one('SELECT * FROM funcoes WHERE id_funcao=%s', (id,))
    if not item:
        flash('Função não encontrada.', 'danger')
        return redirect(url_for('funcoes_listar'))
    return render_template('dashboard/funcoes/visualizar.html', item=item)


@app.route('/funcoes/excluir/<int:id>', methods=['POST'])
@login_required
def funcoes_excluir(id):
    try:
        execute_query('DELETE FROM funcoes WHERE id_funcao=%s', (id,))
        flash('Função excluída com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro ao excluir função: {e}', 'danger')
    return redirect(url_for('funcoes_listar'))


@app.route('/funcoes/relatorio')
@login_required
def funcoes_relatorio():
    nome   = request.args.get('nome', '').strip()
    status = request.args.get('status', '').strip()
    filtros_ativos = any([nome, status])
    dados = None
    if filtros_ativos:
        sql = 'SELECT id_funcao, nome, status, descricao FROM funcoes WHERE 1=1'
        params = []
        if nome:   sql += ' AND nome LIKE %s';   params.append(f'%{nome}%')
        if status: sql += ' AND status = %s';    params.append(status)
        sql += ' ORDER BY nome'
        dados = execute_query(sql, tuple(params), fetch=True) or []
    return render_template('dashboard/funcoes/relatorio.html',
                           dados=dados, filtros_ativos=filtros_ativos,
                           f_nome=nome, f_status=status)


# ── Pacientes ─────────────────────────────────────────────────────────────────

@app.route('/pacientes/listar')
@login_required
def pacientes_listar():
    dados = execute_query('SELECT * FROM pacientes ORDER BY id_paciente DESC', fetch=True)
    return render_template('dashboard/pacientes/listar.html', dados=dados)


@app.route('/pacientes/cadastrar', methods=['GET', 'POST'])
@login_required
def pacientes_cadastrar():
    if request.method == 'POST':
        nome            = request.form.get('nome', '').strip()
        cpf             = request.form.get('cpf', '').strip()
        data_nascimento = request.form.get('data_nascimento', '').strip() or None
        telefone        = request.form.get('telefone', '').strip()
        email           = request.form.get('email', '').strip() or None
        convenio        = request.form.get('convenio', '').strip() or None
        tipo_sanguineo  = request.form.get('tipo_sanguineo', '').strip() or None
        cep             = request.form.get('cep', '').strip()
        logradouro      = request.form.get('logradouro', '').strip()
        numero          = request.form.get('numero', '').strip()
        complemento     = request.form.get('complemento', '').strip()
        bairro          = request.form.get('bairro', '').strip()
        cidade          = request.form.get('cidade', '').strip()
        estado          = request.form.get('estado', '').strip() or None

        if not all([nome, cpf, telefone]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('pacientes_cadastrar'))

        if execute_one('SELECT id_paciente FROM pacientes WHERE cpf=%s', (cpf,)):
            flash('CPF já cadastrado!', 'danger')
            return redirect(url_for('pacientes_cadastrar'))

        try:
            execute_query(
                """INSERT INTO pacientes
                   (nome,cpf,data_nascimento,telefone,email,convenio,tipo_sanguineo,
                    cep,logradouro,numero,complemento,bairro,cidade,estado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (nome,cpf,data_nascimento,telefone,email,convenio,tipo_sanguineo,
                 cep,logradouro,numero,complemento,bairro,cidade,estado)
            )
            flash('Paciente cadastrado com sucesso!', 'success')
            return redirect(url_for('pacientes_listar'))
        except Exception as e:
            flash(f'Erro ao cadastrar paciente: {e}', 'danger')
            return redirect(url_for('pacientes_cadastrar'))

    return render_template('dashboard/pacientes/form.html', titulo='Cadastrar Paciente', modo='cadastrar', item=None)


@app.route('/pacientes/alterar/<int:id>', methods=['GET', 'POST'])
@login_required
def pacientes_alterar(id):
    if request.method == 'POST':
        nome            = request.form.get('nome', '').strip()
        cpf             = request.form.get('cpf', '').strip()
        data_nascimento = request.form.get('data_nascimento', '').strip() or None
        telefone        = request.form.get('telefone', '').strip()
        email           = request.form.get('email', '').strip() or None
        convenio        = request.form.get('convenio', '').strip() or None
        tipo_sanguineo  = request.form.get('tipo_sanguineo', '').strip() or None
        cep             = request.form.get('cep', '').strip()
        logradouro      = request.form.get('logradouro', '').strip()
        numero          = request.form.get('numero', '').strip()
        complemento     = request.form.get('complemento', '').strip()
        bairro          = request.form.get('bairro', '').strip()
        cidade          = request.form.get('cidade', '').strip()
        estado          = request.form.get('estado', '').strip() or None

        if not all([nome, cpf, telefone]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('pacientes_alterar', id=id))

        if execute_one('SELECT id_paciente FROM pacientes WHERE cpf=%s AND id_paciente<>%s', (cpf, id)):
            flash('CPF já cadastrado em outro paciente!', 'danger')
            return redirect(url_for('pacientes_alterar', id=id))

        try:
            execute_query(
                """UPDATE pacientes SET nome=%s,cpf=%s,data_nascimento=%s,telefone=%s,email=%s,
                   convenio=%s,tipo_sanguineo=%s,cep=%s,logradouro=%s,numero=%s,
                   complemento=%s,bairro=%s,cidade=%s,estado=%s WHERE id_paciente=%s""",
                (nome,cpf,data_nascimento,telefone,email,convenio,tipo_sanguineo,
                 cep,logradouro,numero,complemento,bairro,cidade,estado,id)
            )
            flash('Paciente alterado com sucesso!', 'success')
            return redirect(url_for('pacientes_listar'))
        except Exception as e:
            flash(f'Erro ao alterar paciente: {e}', 'danger')
            return redirect(url_for('pacientes_alterar', id=id))

    item = execute_one('SELECT * FROM pacientes WHERE id_paciente=%s', (id,))
    if not item:
        flash('Paciente não encontrado.', 'danger')
        return redirect(url_for('pacientes_listar'))
    return render_template('dashboard/pacientes/form.html', titulo='Alterar Paciente', modo='alterar', item=item)


@app.route('/pacientes/visualizar/<int:id>')
@login_required
def pacientes_visualizar(id):
    item = execute_one('SELECT * FROM pacientes WHERE id_paciente=%s', (id,))
    if not item:
        flash('Paciente não encontrado.', 'danger')
        return redirect(url_for('pacientes_listar'))
    return render_template('dashboard/pacientes/visualizar.html', item=item)


@app.route('/pacientes/excluir/<int:id>', methods=['POST'])
@login_required
def pacientes_excluir(id):
    try:
        execute_query('DELETE FROM pacientes WHERE id_paciente=%s', (id,))
        flash('Paciente excluído com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro ao excluir paciente: {e}', 'danger')
    return redirect(url_for('pacientes_listar'))


@app.route('/pacientes/relatorio')
@login_required
def pacientes_relatorio():
    nome          = request.args.get('nome', '').strip()
    tipo_sanguineo = request.args.get('tipo_sanguineo', '').strip()
    convenio      = request.args.get('convenio', '').strip()
    filtros_ativos = any([nome, tipo_sanguineo, convenio])
    dados = None
    if filtros_ativos:
        sql = 'SELECT id_paciente, nome, cpf, telefone, email, convenio, tipo_sanguineo FROM pacientes WHERE 1=1'
        params = []
        if nome:           sql += ' AND nome LIKE %s';           params.append(f'%{nome}%')
        if tipo_sanguineo: sql += ' AND tipo_sanguineo = %s';    params.append(tipo_sanguineo)
        if convenio:       sql += ' AND convenio LIKE %s';       params.append(f'%{convenio}%')
        sql += ' ORDER BY nome'
        dados = execute_query(sql, tuple(params), fetch=True) or []
    return render_template('dashboard/pacientes/relatorio.html',
                           dados=dados, filtros_ativos=filtros_ativos,
                           f_nome=nome, f_tipo_sanguineo=tipo_sanguineo, f_convenio=convenio)


# ── Consultas ─────────────────────────────────────────────────────────────────

@app.route('/consultas/listar')
@login_required
def consultas_listar():
    dados = fix_timedelta(execute_query(
        '''SELECT c.id_consulta, p.nome AS paciente, u.nome AS medico,
                  c.data, c.hora, c.especialidade, c.status
           FROM consultas c
           JOIN pacientes p ON c.paciente_id = p.id_paciente
           JOIN usuarios u  ON c.medico_id   = u.id_usuario
           ORDER BY c.data DESC, c.hora DESC''',
        fetch=True
    ))
    return render_template('dashboard/consultas/listar.html', dados=dados)


@app.route('/consultas/cadastrar', methods=['GET', 'POST'])
@login_required
def consultas_cadastrar():
    lista_pacientes = execute_query('SELECT id_paciente, nome FROM pacientes ORDER BY nome', fetch=True)
    lista_medicos   = execute_query(
        "SELECT u.id_usuario, u.nome FROM usuarios u JOIN funcoes f ON u.funcao_id=f.id_funcao WHERE f.nome IN ('Médico','Administrador') ORDER BY u.nome",
        fetch=True
    )

    if request.method == 'POST':
        paciente_id   = request.form.get('paciente_id', '').strip()
        medico_id     = request.form.get('medico_id', '').strip()
        data          = request.form.get('data', '').strip()
        hora          = request.form.get('hora', '').strip()
        especialidade = request.form.get('especialidade', '').strip()
        status        = request.form.get('status', 'Agendada').strip()
        observacoes   = request.form.get('observacoes', '').strip() or None

        if not all([paciente_id, medico_id, data, hora, especialidade]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('consultas_cadastrar'))

        try:
            execute_query(
                """INSERT INTO consultas (paciente_id,medico_id,data,hora,especialidade,status,observacoes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (int(paciente_id), int(medico_id), data, hora, especialidade, status, observacoes)
            )
            flash('Consulta agendada com sucesso!', 'success')
            return redirect(url_for('consultas_listar'))
        except Exception as e:
            flash(f'Erro ao agendar consulta: {e}', 'danger')
            return redirect(url_for('consultas_cadastrar'))

    return render_template('dashboard/consultas/form.html', titulo='Agendar Consulta', modo='cadastrar', item=None,
                           lista_pacientes=lista_pacientes, lista_medicos=lista_medicos)


@app.route('/consultas/alterar/<int:id>', methods=['GET', 'POST'])
@login_required
def consultas_alterar(id):
    lista_pacientes = execute_query('SELECT id_paciente, nome FROM pacientes ORDER BY nome', fetch=True)
    lista_medicos   = execute_query(
        "SELECT u.id_usuario, u.nome FROM usuarios u JOIN funcoes f ON u.funcao_id=f.id_funcao WHERE f.nome IN ('Médico','Administrador') ORDER BY u.nome",
        fetch=True
    )

    if request.method == 'POST':
        paciente_id   = request.form.get('paciente_id', '').strip()
        medico_id     = request.form.get('medico_id', '').strip()
        data          = request.form.get('data', '').strip()
        hora          = request.form.get('hora', '').strip()
        especialidade = request.form.get('especialidade', '').strip()
        status        = request.form.get('status', 'Agendada').strip()
        observacoes   = request.form.get('observacoes', '').strip() or None

        if not all([paciente_id, medico_id, data, hora, especialidade]):
            flash('Preencha todos os campos obrigatórios.', 'danger')
            return redirect(url_for('consultas_alterar', id=id))

        try:
            execute_query(
                """UPDATE consultas SET paciente_id=%s,medico_id=%s,data=%s,hora=%s,
                   especialidade=%s,status=%s,observacoes=%s WHERE id_consulta=%s""",
                (int(paciente_id), int(medico_id), data, hora, especialidade, status, observacoes, id)
            )
            flash('Consulta alterada com sucesso!', 'success')
            return redirect(url_for('consultas_listar'))
        except Exception as e:
            flash(f'Erro ao alterar consulta: {e}', 'danger')
            return redirect(url_for('consultas_alterar', id=id))

    item = execute_one(
        '''SELECT c.*, p.nome AS paciente, u.nome AS medico
           FROM consultas c
           JOIN pacientes p ON c.paciente_id=p.id_paciente
           JOIN usuarios u  ON c.medico_id=u.id_usuario
           WHERE c.id_consulta=%s''', (id,)
    )
    if not item:
        flash('Consulta não encontrada.', 'danger')
        return redirect(url_for('consultas_listar'))
    return render_template('dashboard/consultas/form.html', titulo='Alterar Consulta', modo='alterar', item=item,
                           lista_pacientes=lista_pacientes, lista_medicos=lista_medicos)


@app.route('/consultas/visualizar/<int:id>')
@login_required
def consultas_visualizar(id):
    item = execute_one(
        '''SELECT c.*, p.nome AS paciente, u.nome AS medico
           FROM consultas c
           JOIN pacientes p ON c.paciente_id=p.id_paciente
           JOIN usuarios u  ON c.medico_id=u.id_usuario
           WHERE c.id_consulta=%s''', (id,)
    )
    if not item:
        flash('Consulta não encontrada.', 'danger')
        return redirect(url_for('consultas_listar'))
    return render_template('dashboard/consultas/visualizar.html', item=item)


@app.route('/consultas/excluir/<int:id>', methods=['POST'])
@login_required
def consultas_excluir(id):
    try:
        execute_query('DELETE FROM consultas WHERE id_consulta=%s', (id,))
        flash('Consulta excluída com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro ao excluir consulta: {e}', 'danger')
    return redirect(url_for('consultas_listar'))


@app.route('/consultas/relatorio')
@login_required
def consultas_relatorio():
    data_ini     = request.args.get('data_ini', '').strip()
    data_fim     = request.args.get('data_fim', '').strip()
    status       = request.args.get('status', '').strip()
    especialidade = request.args.get('especialidade', '').strip()
    filtros_ativos = any([data_ini, data_fim, status, especialidade])
    dados = None
    if filtros_ativos:
        sql = '''SELECT c.id_consulta, p.nome AS paciente, u.nome AS medico,
                        c.data, c.hora, c.especialidade, c.status
                 FROM consultas c
                 JOIN pacientes p ON c.paciente_id = p.id_paciente
                 JOIN usuarios u  ON c.medico_id   = u.id_usuario
                 WHERE 1=1'''
        params = []
        if data_ini:      sql += ' AND c.data >= %s';                params.append(data_ini)
        if data_fim:      sql += ' AND c.data <= %s';                params.append(data_fim)
        if status:        sql += ' AND c.status = %s';               params.append(status)
        if especialidade: sql += ' AND c.especialidade LIKE %s';     params.append(f'%{especialidade}%')
        sql += ' ORDER BY c.data DESC, c.hora DESC'
        dados = execute_query(sql, tuple(params), fetch=True) or []
        fix_timedelta(dados)
    return render_template('dashboard/consultas/relatorio.html',
                           dados=dados, filtros_ativos=filtros_ativos,
                           f_data_ini=data_ini, f_data_fim=data_fim,
                           f_status=status, f_especialidade=especialidade)


if __name__ == '__main__':
    app.run(debug=True)