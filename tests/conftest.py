import os
import pytest
from app import create_app, db as _db
from app.models import * # Import all models to ensure they are registered with SQLAlchemy

# 设置测试环境变量
os.environ['TESTING'] = 'True'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['CACHE_TYPE'] = 'null'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    app = create_app('testing') # Use a 'testing' configuration
    with app.app_context():
        yield app

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db(app):
    """Set up and tear down the database for each test function."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()