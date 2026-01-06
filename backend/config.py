import os

class Config:
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', 300))  # 5 minutes
    MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'saved_models')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

config = Config()