---
inclusion: always
---
## BACKEND

### Guidelines for PYTHON

#### FLASK

- Use Flask Blueprints to organize routes and views by feature or domain for better code organization
- Implement Flask-SQLAlchemy with proper session management to prevent connection leaks and memory issues
- Use Flask-Marshmallow for serialization and request validation of {{data_types}}
- Apply the application factory pattern to enable testing and multiple deployment configurations
- Implement Flask-Limiter for rate limiting on public endpoints to prevent abuse of {{public_apis}}
- Use Flask-Login or Flask-JWT-Extended for authentication with proper session timeout and refresh mechanisms

#### SECURITY_REQUIREMENTS

- **SQL注入防护**: 禁止使用字符串拼接构建SQL查询，必须使用参数化查询或ORM方法
- **密码安全**: 禁止硬编码密码，使用环境变量或安全的密钥管理系统
- **输入验证**: 对所有用户输入进行严格验证和过滤，防止恶意输入
- **CSRF防护**: 在所有状态改变操作中使用CSRF令牌
- **错误处理**: 避免使用裸露的except语句，必须记录具体错误信息

#### CODE_QUALITY

- **格式化**: 使用Black进行代码格式化，行长度限制为88字符
- **类型提示**: 所有函数参数和返回值必须包含类型提示
- **文档**: 所有公共函数、类和方法必须有docstring
- **导入排序**: 使用isort进行导入排序，按标准库、第三方库、本地模块分组
- **异常处理**: 避免try-except-pass模式，必须记录错误信息

#### ERROR_HANDLING

- **具体异常**: 避免裸露的except语句，必须指定具体的异常类型
- **错误记录**: 使用logging记录异常详情，包括堆栈跟踪
- **优雅降级**: 当非关键功能失败时，应用应该继续运行
- **错误恢复**: 对于可恢复的错误，实现重试机制
- **资源清理**: 在发生错误时正确清理已分配的资源
