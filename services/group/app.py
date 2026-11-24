import time

from flask import Flask, g, jsonify, request
from flask_cors import CORS

import config
import database
from group.routes import group_blueprint


def create_app() -> Flask:
    """build the Flask app and register its routes and error handlers"""
    app = Flask(__name__)
    # browsers may only call this service from the UI's address, and only send JSON bodies
    CORS(app, origins=config.get_cors_origin(), allow_headers=["Content-Type"])
    # wait for the database and bring its schema up to date before serving any request
    database.wait_for_database()
    database.run_migrations()
    app.register_blueprint(group_blueprint)

    @app.before_request
    def start_timer():
        """remember when the request started, so its duration can be logged"""
        g.start_time = time.perf_counter()

    @app.after_request
    def log_request(response):
        """print one line per request with its method, path, status and duration"""
        duration_ms = (time.perf_counter() - g.start_time) * 1000
        print(f"{request.method} {request.path} {response.status_code} {duration_ms:.0f}ms")
        return response

    @app.get("/health")
    def health():
        """report whether this service can use its own database, without asking any other service"""
        version = config.get_app_version()
        if database.check_database():
            return jsonify({"status": "ok", "db": "ok", "version": version}), 200
        return jsonify({"status": "error", "db": "unavailable", "version": version}), 503

    @app.get("/")
    def index():
        """return a short status message so callers know the app is up."""
        return jsonify({"service": "group", "status": "ok"})
    
    @app.errorhandler(404)
    def not_found(error):
        """return json instead of flask's default html error page"""
        return jsonify({"error": "not found"}), 404
    
    @app.errorhandler(500)
    def server_error(error):
        """log the real error but only tell the caller something went wrong"""
        print(f"Unexpected error: {error}")
        return jsonify({"error": "something went wrong"}), 500

    return app
    
if __name__ == "__main__":
    port = config.get_port()
    print(f"Starting group on 0.0.0.0:{port}")
    create_app().run(host="0.0.0.0", port=port)
