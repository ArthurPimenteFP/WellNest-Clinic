// ============================================================
// WellNest Clinic — JavaScript
// ============================================================

/* DOMCONTENTLOADED - Executa o código apenas depois que toda a página HTML carregar */
document.addEventListener('DOMContentLoaded', function () {

    /* CONFIRMAÇÃO DE EXCLUSÃO - Evita que o usuário exclua algo sem querer */
    document.querySelectorAll('.btn-excluir').forEach(function (btn) {

        /* EVENTO DE CLICK - Dispara quando o botão de excluir é clicado */
        btn.addEventListener('click', function (e) {

            /* PREVENTDEFAULT - Impede a ação padrão (ex: envio de formulário ou link) */
            e.preventDefault();

            /* CONFIRM - Mostra uma caixa de confirmação para o usuário */
            var confirmacao = confirm('Tem certeza que deseja excluir este registro?');

            /* VALIDAÇÃO - Só executa se o usuário confirmar */
            if (confirmacao) {

                /* ALERTA - Simula a exclusão do registro */
                alert('Registro excluído com sucesso! (simulação)');
            }
        });
    });

    /* INDICADOR DE FORÇA DE SENHA - Mostra se a senha é fraca, média ou forte */
    var campoSenha = document.getElementById('senha'); /* campo de senha */
    var indicador = document.getElementById('senha-strength'); /* texto indicador */

    /* VALIDAÇÃO DE ELEMENTOS - Só executa se os elementos existirem na página */
    if (campoSenha && indicador) {

        /* EVENTO INPUT - Dispara toda vez que o usuário digita na senha */
        campoSenha.addEventListener('input', function () {

            var senha = campoSenha.value; /* valor digitado */
            var forca = 0; /* nível de força da senha */

            /* REGRAS DE VALIDAÇÃO - Soma pontos conforme critérios */
            if (senha.length >= 6) forca++; /* tamanho mínimo */
            if (senha.length >= 10) forca++; /* tamanho maior */
            if (/[A-Z]/.test(senha)) forca++; /* letra maiúscula */
            if (/[0-9]/.test(senha)) forca++; /* número */
            if (/[^A-Za-z0-9]/.test(senha)) forca++; /* caractere especial */

            /* RESET DE CLASSES - Limpa estilos anteriores */
            indicador.className = 'form-text mt-1';

            /* VERIFICAÇÃO DE SENHA VAZIA */
            if (senha.length === 0) {

                indicador.textContent = ''; /* limpa texto */

            } else if (forca <= 2) {

                /* SENHA FRACA - Poucos critérios atendidos */
                indicador.textContent = '🔴 Senha fraca';
                indicador.classList.add('senha-fraca');

            } else if (forca <= 3) {

                /* SENHA MÉDIA - Segurança intermediária */
                indicador.textContent = '🟡 Senha média';
                indicador.classList.add('senha-media');

            } else {

                /* SENHA FORTE - Atende vários critérios de segurança */
                indicador.textContent = '🟢 Senha forte';
                indicador.classList.add('senha-forte');
            }
        });
    }

    /* AUTO-DISMISS ALERT - Fecha automaticamente alertas após alguns segundos */
    document.querySelectorAll('.alert-dismissible').forEach(function (alerta) {

        /* SETTIMEOUT - Define um tempo para executar a ação */
        setTimeout(function () {

            /* BOOTSTRAP ALERT - Cria ou pega instância do alerta */
            var bsAlert = bootstrap.Alert.getOrCreateInstance(alerta);

            /* CLOSE - Fecha o alerta */
            bsAlert.close();

        }, 5000); /* tempo de 5 segundos */
    });
});