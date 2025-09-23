## Gemini's Core Rules for Flask Development

### APPLICATION_STRUCTURE
- **Application Factory**: Always use the application factory pattern (`create_app`) for better testability and configuration management.
- **Blueprints**: Organize routes and views into feature-specific Blueprints for a modular and clean codebase.
- **Separation of Concerns**: Strictly separate models, views, services, and configurations into their own modules.

### CODE_QUALITY
- **Formatting**: Use `black` for code formatting (line length: 88) and `isort` for import sorting.
- **Type Hints**: All function signatures (arguments and returns) MUST have type hints.
- **Docstrings**: All public modules, functions, classes, and methods MUST have Google-style docstrings.
- **Naming**: Use `snake_case` for variables/functions and `PascalCase` for classes.

### DATABASE & ORM
- **ORM Usage**: Use Flask-SQLAlchemy for all database interactions. Prevent SQL injection by using the ORM's methods, not raw SQL with string formatting.
- **Migrations**: Use `alembic` (via Flask-Migrate) for all database schema changes.
- **Session Management**: Ensure proper SQLAlchemy session scoping and lifecycle to prevent leaks.

### SECURITY
- **Input Validation**: Validate ALL incoming data from users and external services, preferably with Pydantic or Marshmallow.
- **Authentication**: Use Flask-Login for session-based authentication or Flask-JWT-Extended for token-based APIs.
- **Password Hashing**: Never store plain-text passwords. Use a strong hashing algorithm like Argon2 or bcrypt.
- **CSRF Protection**: Enable and enforce CSRF protection on all state-changing form submissions.

### ERROR_HANDLING & LOGGING
- **Specific Exceptions**: Catch specific exceptions, not bare `except:`. Create custom exception classes for your application's domain errors.
- **Structured Logging**: Use `structlog` for structured, context-rich logging. Log errors with stack traces. Never log sensitive information.

### API_DESIGN
- **RESTful Principles**: Design APIs following RESTful conventions, using correct HTTP verbs and status codes.
- **Standardized Response**: Use a consistent JSON response format for all API endpoints (e.g., `{"data": ..., "error": ...}`).

### PERFORMANCE
- **Caching**: Use Redis for caching expensive database queries or computations.
- **Background Tasks**: Offload long-running tasks to a Celery worker to avoid blocking web requests.