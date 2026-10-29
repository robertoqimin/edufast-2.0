from app import create_app


app = create_app()


if __name__ == "__main__":
    from config import Config
    if Config.DEBUG and (Config.APP_ENV != "development" or Config.BIND_HOST not in {"127.0.0.1", "localhost", "::1"}):
        raise RuntimeError("Debug permitido somente em desenvolvimento e loopback.")
    app.run(host=Config.BIND_HOST, port=5000, debug=Config.DEBUG)
