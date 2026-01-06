from flask import Flask
from flask_cors import CORS
from config import config
from routes.analysis import analysis_bp
from routes.live_price import live_price_bp
from routes.search import search_bp
from utils.logger import logger

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register blueprints
    app.register_blueprint(analysis_bp)
    app.register_blueprint(live_price_bp)
    app.register_blueprint(search_bp)

    logger.info("Trading App initialized")

    return app

app = create_app()

if __name__ == '__main__':
    app.run(port=config.PORT, debug=config.DEBUG)
