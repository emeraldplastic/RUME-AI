from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

db = SQLAlchemy()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object('app.config.Config')
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    # Register blueprints
    from app.routes import api
    app.register_blueprint(api)
    
    # SPA Route
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return render_template('index.html')
        
    # Security Headers
    @app.after_request
    def add_security_headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self';"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    with app.app_context():
        db.create_all()
        
    return app
