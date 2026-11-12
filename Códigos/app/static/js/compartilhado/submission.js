(function () {
    function setBusy(form, busy) {
        Array.from(form.elements).forEach(function (element) {
            if (element.type !== "submit" && element.type !== "reset") return;
            if (busy) {
                element.dataset.wasDisabled = String(element.disabled);
                element.disabled = true;
            } else {
                element.disabled = element.dataset.wasDisabled === "true";
                delete element.dataset.wasDisabled;
            }
        });
        form.setAttribute("aria-busy", String(busy));
    }
    function renewKey(form) {
        const input = form.elements.namedItem("idempotency_key");
        if (input) { input.value = crypto.randomUUID(); input.defaultValue = input.value; }
    }
    function syncGrade(form) {
        const select = form.elements.namedItem("disciplina_id");
        form.elements.namedItem("versao").value = select.selectedOptions[0]?.dataset.versao || "0";
    }
    document.addEventListener("react-shell:mounted", function (event) {
        event.detail.root.querySelectorAll(".professor-grade-form").forEach(syncGrade);
    });
    document.addEventListener("change", function (event) {
        const form = event.target.form;
        if (form?.classList.contains("professor-grade-form") && event.target.name === "disciplina_id") syncGrade(form);
    });
    // Bubble after AJAX handlers; they own their busy state and recovery.
    document.addEventListener("submit", function (event) {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || event.defaultPrevented) return;
        if (form.dataset.sending === "true") { event.preventDefault(); return; }
        if (event.submitter?.name) {
            let input = form.querySelector("input[data-submitter]");
            if (!input) { input = document.createElement("input"); input.type = "hidden"; input.dataset.submitter = "true"; form.appendChild(input); }
            input.name = event.submitter.name;
            input.value = event.submitter.value;
        }
        form.dataset.sending = "true";
        setBusy(form, true);
    });
    window.addEventListener("pageshow", function () {
        document.querySelectorAll("form[data-sending]").forEach(function (form) {
            delete form.dataset.sending;
            setBusy(form, false);
        });
    });
    window.EduFastSubmission = { setBusy: setBusy, renewKey: renewKey };
})();
