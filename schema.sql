-- =====================================================================
-- SCHEMA.SQL
-- =====================================================================
-- Este script:
-- 1. Cria o banco wellnest_clinic.
-- 2. Cria as tabelas principais do sistema.
-- 3. Define chaves primárias e estrangeiras.
-- 4. Define regras de integridade e relacionamentos.
-- 5. Estrutura os dados de usuários, funções, pacientes e consultas.
-- =====================================================================

-- DROP DATABASE IF EXISTS wellnest_clinic;

CREATE DATABASE IF NOT EXISTS wellnest_clinic
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE wellnest_clinic;

-- Tabela de funções (perfis de acesso do sistema)
CREATE TABLE IF NOT EXISTS funcoes (
    id_funcao BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    status ENUM('Ativo', 'Inativo') DEFAULT 'Ativo',
    descricao VARCHAR(255),
    gerenciar_usuario BOOLEAN DEFAULT 0,
    gerenciar_funcao  BOOLEAN DEFAULT 0,
    gerenciar_paciente BOOLEAN DEFAULT 0,
    gerenciar_consulta BOOLEAN DEFAULT 0,

    -- logs
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    alterado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabela de usuários do sistema (funcionários da clínica)
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome       VARCHAR(255) NOT NULL,
    cpf        VARCHAR(14)  NOT NULL UNIQUE,
    data_nascimento DATE NULL,
    email      VARCHAR(255) NOT NULL UNIQUE,
    celular    VARCHAR(20)  NOT NULL,
    cep        VARCHAR(9),
    logradouro VARCHAR(255),
    numero     VARCHAR(20),
    complemento VARCHAR(100),
    bairro     VARCHAR(100),
    cidade     VARCHAR(100),
    estado     CHAR(2) NOT NULL,
    pais       VARCHAR(50) DEFAULT 'Brasil',
    senha      VARCHAR(255) NOT NULL,
    status     ENUM('Ativo', 'Inativo') DEFAULT 'Ativo',

    funcao_id  BIGINT UNSIGNED NOT NULL,

    -- logs
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    alterado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_usuario_funcao
        FOREIGN KEY (funcao_id) REFERENCES funcoes (id_funcao)
);

-- Tabela de pacientes da clínica
CREATE TABLE IF NOT EXISTS pacientes (
    id_paciente BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome        VARCHAR(255) NOT NULL,
    cpf         VARCHAR(14)  NOT NULL UNIQUE,
    data_nascimento DATE NULL,
    telefone    VARCHAR(20),
    email       VARCHAR(255),
    convenio    VARCHAR(100),
    tipo_sanguineo ENUM('A+','A-','B+','B-','AB+','AB-','O+','O-') NULL,
    cep         VARCHAR(9),
    logradouro  VARCHAR(255),
    numero      VARCHAR(20),
    complemento VARCHAR(100),
    bairro      VARCHAR(100),
    cidade      VARCHAR(100),
    estado      CHAR(2),

    -- logs
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    alterado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabela de consultas
CREATE TABLE IF NOT EXISTS consultas (
    id_consulta  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    paciente_id  BIGINT UNSIGNED NOT NULL,
    medico_id    BIGINT UNSIGNED NOT NULL,
    data         DATE NOT NULL,
    hora         TIME NOT NULL,
    especialidade VARCHAR(100) NOT NULL,
    status       ENUM('Agendada','Confirmada','Realizada','Cancelada') DEFAULT 'Agendada',
    observacoes  VARCHAR(500),

    -- logs
    criado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
    alterado_em DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_consulta_paciente
        FOREIGN KEY (paciente_id) REFERENCES pacientes (id_paciente),
    CONSTRAINT fk_consulta_medico
        FOREIGN KEY (medico_id) REFERENCES usuarios (id_usuario)
);

-- Dados iniciais: funções padrão da clínica
INSERT IGNORE INTO funcoes (nome, status, descricao, gerenciar_usuario, gerenciar_funcao, gerenciar_paciente, gerenciar_consulta)
VALUES
    ('Administrador', 'Ativo', 'Acesso total ao sistema da clínica.',             1, 1, 1, 1),
    ('Médico',        'Ativo', 'Pode visualizar e gerenciar suas consultas.',      0, 0, 1, 1),
    ('Enfermeiro',    'Ativo', 'Pode visualizar pacientes e consultas.',           0, 0, 1, 1),
    ('Recepcionista', 'Ativo', 'Pode cadastrar pacientes e agendar consultas.',    0, 0, 1, 1);
