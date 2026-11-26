(function () {
    function inicializarLogin(root) {
        const form = root.querySelector("#login-form");

        if (!form || form.dataset.pageBound === "true") {
            return;
        }

        form.dataset.pageBound = "true";
        form.addEventListener("submit", enviarLogin);
        if (window.self !== window.top) {
            definirErro(form.querySelector("#login-error"),
                "Esta prévia pode bloquear sua sessão. Abra o endereço da escola em uma aba do Edge ou Chrome para entrar.");
        }
    }
    document.addEventListener("react-shell:mounted", function (event) { inicializarLogin(event.detail.root); });
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { inicializarLogin(document); });
    } else {
        inicializarLogin(document);
    }

    function enviarLogin(event) {
        event.preventDefault();

        const form = event.currentTarget;
        if (form.dataset.sending === "true") return;
        form.dataset.sending = "true";
        const error = form.querySelector("#login-error");
        const button = form.querySelector("button[type='submit']");

        definirErro(error, "");
        definirCarregamento(button, true);

        fetch(new URL("/login", window.location.origin), {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": form.elements.namedItem("csrf_token").value
            },
            body: JSON.stringify({
                email: form.email.value,
                senha: form.senha.value
            })
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok) {
                        throw new Error(data?.erro || "Falha ao logar");
                    }

                    return data;
                });
            })
            .then(function (data) {
                return fetch(new URL("/auth/session", window.location.origin), {
                    credentials: "same-origin", cache: "no-store"
                }).then(function (response) {
                    if (!response.ok) {
                        throw new Error("Não foi possível manter sua sessão. Abra esta escola em uma aba do Edge ou Chrome e tente novamente.");
                    }
                    return response.json();
                }).then(function (identity) {
                    if (!identity.authenticated || identity.role !== data.role) {
                        throw new Error("Sua sessão mudou. Recarregue a página e entre novamente.");
                    }
                    redirecionarPorPerfil(data);
                });
            })
            .catch(function (erroRequisicao) {
                const message = erroRequisicao.message || "Erro ao conectar com o servidor";
                definirErro(error, window.self !== window.top
                    ? message + " Abra o endereço da escola em uma aba do Edge ou Chrome, fora desta prévia."
                    : message);
            })
            .finally(function () {
                delete form.dataset.sending;
                definirCarregamento(button, false);
            });
    }

    function redirecionarPorPerfil(data) {
        const destinos = {
            SUPER_ADMIN: "/admin/dashboard",  // U4: a direção começa pela Visão geral (checklist)
            SUPERADMIN: "/admin/dashboard",
            ADMIN: "/admin/dashboard",
            ALUNO: "/aluno",
            PROFESSOR: "/professor"
        };

        if (!destinos[data.tipo]) {
            throw new Error("Tipo de usuário sem área configurada");
        }

        window.location.href = destinos[data.tipo];
    }

    function definirErro(element, message) {
        element.textContent = message;
        element.classList.toggle("hidden", !message);
        element.hidden = !message;
    }

    function definirCarregamento(button, loading) {
        if (!button.dataset.originalLabel) button.dataset.originalLabel = button.innerHTML;
        button.disabled = loading;
        if (loading) button.textContent = "Entrando…";
        else button.innerHTML = button.dataset.originalLabel;
    }
})();
