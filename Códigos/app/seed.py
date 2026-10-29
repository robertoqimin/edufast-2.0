def run_seed():
    raise RuntimeError(
        "Seed destrutivo desativado. Use flask --app app:create_app() create-admin "
        "com email e senha proprios; contas existentes serao preservadas."
    )


if __name__ == "__main__":
    run_seed()
