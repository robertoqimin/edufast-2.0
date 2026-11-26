// B3: o shell das páginas antigas não usa mais React; ele só copia o <template> da página
// para a tela e liga as abas, e JavaScript simples faz o mesmo sem baixar e interpretar 138 KiB.
// Nomes (react-shell, data-react-*, evento react-shell:mounted) mantidos por compatibilidade.
(function (window) {

    const gruposAbas = [
        {
            seletorAba: "[data-aluno-tab]",
            seletorPainel: "[data-aluno-panel]",
            chaveAba: "alunoTab",
            chavePainel: "alunoPanel",
            classeOculta: "aluno-panel-hidden"
        },
        {
            seletorAba: "[data-professor-tab]",
            seletorPainel: "[data-professor-panel]",
            chaveAba: "professorTab",
            chavePainel: "professorPanel",
            classeOculta: "professor-panel-hidden"
        },
        {
            seletorAba: "[data-documento-tab]",
            seletorPainel: "[data-documento-panel]",
            chaveAba: "documentoTab",
            chavePainel: "documentoPanel",
            classeOculta: "hidden"
        },
        {
            seletorAba: "[data-professor-section-tab]",
            seletorPainel: "[data-professor-section-panel]",
            chaveAba: "professorSectionTab",
            chavePainel: "professorSectionPanel",
            classeOculta: "hidden"
        }
    ];

    function montar(root) {
        const template = document.getElementById(root.dataset.reactTemplate);

        if (!template || root.dataset.reactMounted === "true") {
            return;
        }

        root.dataset.reactMounted = "true";
        const shell = document.createElement("div");
        shell.className = "react-shell flex w-full";
        shell.innerHTML = template.innerHTML;
        root.replaceChildren(shell);
        // Como antes: comportamentos e evento depois dos scripts da página já registrados.
        window.setTimeout(function () {
            inicializarComportamentosPagina(root);
            dispararEventoMontado(root);
        }, 0);
    }

    function montarTodos() {
        const raizes = document.querySelectorAll("[data-react-shell]");
        if (!raizes.length) {
            // U5: telas no layout padrão já vêm prontas do servidor; só liga as abas e avisa os
            // scripts da página (mesmo evento de antes, com a página inteira como raiz).
            window.setTimeout(function () {
                inicializarComportamentosPagina(document);
                dispararEventoMontado(document.body);
            }, 0);
            return;
        }
        raizes.forEach(montar);
    }

    function inicializarComportamentosPagina(scope) {
        gruposAbas.forEach(function (tabConfig) {
            inicializarAbas(scope, tabConfig);
        });
    }

    function inicializarAbas(scope, config) {
        const tabs = Array.from(scope.querySelectorAll(config.seletorAba));
        const panels = Array.from(scope.querySelectorAll(config.seletorPainel));

        if (!tabs.length || !panels.length) {
            return;
        }

        tabs.forEach(function (tab) {
            if (tab.dataset.reactBound === "true") {
                return;
            }

            tab.dataset.reactBound = "true";
            tab.addEventListener("click", function () {
                ativarAba(tabs, panels, tab.dataset[config.chaveAba], config);
            });
        });
    }

    function dispararEventoMontado(root) {
        root.dispatchEvent(new CustomEvent("react-shell:mounted", {
            bubbles: true,
            detail: { root }
        }));
    }

    function ativarAba(tabs, panels, abaAtiva, config) {
        tabs.forEach(function (tab) {
            const ativa = tab.dataset[config.chaveAba] === abaAtiva;
            // U1/O6: o item do menu acompanha a aba aberta (antes ficava preso na primeira).
            tab.classList.toggle("active", ativa);
            tab.setAttribute("aria-pressed", String(ativa));

            tab.classList.toggle("bg-cyan-500/10", ativa);
            tab.classList.toggle("text-cyan-400", ativa);
            tab.classList.toggle("border", ativa);
            tab.classList.toggle("border-cyan-500/20", ativa);
            tab.classList.toggle("border-b-2", ativa);
            tab.classList.toggle("border-cyan-400", ativa);
            tab.classList.toggle("text-white", ativa);
            tab.classList.toggle("text-gray-500", !ativa);
            tab.classList.toggle("text-gray-300", !ativa);
        });

        panels.forEach(function (panel) {
            panel.classList.toggle(config.classeOculta, panel.dataset[config.chavePainel] !== abaAtiva);
        });
    }

    window.ReactShell = {
        montar,
        montarTodos
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", montarTodos);
    } else {
        montarTodos();
    }
})(window);
