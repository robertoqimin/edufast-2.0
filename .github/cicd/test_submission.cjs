const { test } = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");
const fs = require("node:fs");
const path = require("node:path");

function browser() {
    const listeners = {};
    const windowListeners = {};
    class Form {
        constructor() {
            this.dataset = {};
            this.elements = [];
            this.attributes = {};
        }
        setAttribute(name, value) { this.attributes[name] = value; }
        querySelector() { return this.hidden; }
        appendChild(input) { this.hidden = input; this.elements.push(input); }
    }
    const context = {
        HTMLFormElement: Form,
        crypto: { randomUUID: () => "next-intent" },
        document: { addEventListener: (name, fn) => { listeners[name] = fn; }, querySelectorAll: () => [], createElement: () => ({ dataset: {} }) },
        window: { addEventListener: (name, fn) => { windowListeners[name] = fn; } }
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../api/app/static/js/compartilhado/submission.js"), "utf8"), context);
    return { ...context, listeners };
}

test("native submit disables all associated buttons and rejects a second submission", () => {
    const { HTMLFormElement, listeners } = browser();
    const form = new HTMLFormElement();
    const externalSubmit = { type: "submit", disabled: false, dataset: {} };
    const input = { type: "text", disabled: false };
    form.elements = [externalSubmit, input];
    let blocked = 0;
    const event = { target: form, defaultPrevented: false, preventDefault: () => { blocked++; } };
    listeners.submit(event);
    listeners.submit(event);
    assert.equal(externalSubmit.disabled, true);
    assert.equal(input.disabled, false, "payload fields must remain enabled");
    assert.equal(blocked, 1);
    assert.equal(form.attributes["aria-busy"], "true");
});

test("AJAX recovery restores previously disabled controls without enabling them", () => {
    const { HTMLFormElement, window } = browser();
    const form = new HTMLFormElement();
    const submit = { type: "submit", disabled: false, dataset: {} };
    const unavailable = { type: "submit", disabled: true, dataset: {} };
    form.elements = [submit, unavailable];
    window.EduFastSubmission.setBusy(form, true);
    window.EduFastSubmission.setBusy(form, false);
    assert.equal(submit.disabled, false);
    assert.equal(unavailable.disabled, true);
});

test("disabling the approval button preserves its decision in the payload", () => {
    const { HTMLFormElement, listeners } = browser();
    const form = new HTMLFormElement();
    const button = { type: "submit", name: "decisao", value: "aprovar", disabled: false, dataset: {} };
    form.elements = [button];
    listeners.submit({ target: form, submitter: button, defaultPrevented: false });
    assert.equal(button.disabled, true);
    assert.equal(form.hidden.name, "decisao");
    assert.equal(form.hidden.value, "aprovar");
    assert.equal(form.hidden.type, "hidden");
});
