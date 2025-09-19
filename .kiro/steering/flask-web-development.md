---
inclusion: always
---

## FLASK

### Guidelines for WEB_DEVELOPMENT

#### APPLICATION_STRUCTURE

- 使用应用工厂模式创建Flask应用
- 使用Blueprint组织路由和视图
- 分离配置、模型、视图和业务逻辑
- 使用工厂函数初始化扩展
- 实现模块化的应用结构

#### ROUTING

- 使用装饰器定义路由
- 路由函数名应该描述其功能
- 使用RESTful API设计原则
- 实现适当的HTTP方法
- 使用URL参数和查询参数

#### REQUEST_HANDLING

- 验证所有请求参数
- 使用Flask-WTF处理表单
- 实现CSRF保护
- 处理文件上传安全
- 限制请求大小和频率

#### RESPONSE_HANDLING

- 返回适当的HTTP状态码
- 使用JSON响应API请求
- 实现统一的响应格式
- 处理错误响应
- 使用模板渲染HTML页面

#### AUTHENTICATION

- 使用Flask-Login管理用户会话
- 实现安全的密码哈希
- 使用JWT进行API认证
- 实现会话超时
- 记录登录和登出事件

#### AUTHORIZATION

- 实现基于角色的访问控制
- 使用装饰器保护路由
- 检查用户权限
- 实现资源级权限控制
- 记录权限检查失败

#### DATABASE_INTEGRATION

- 使用Flask-SQLAlchemy进行ORM操作
- 实现数据库迁移
- 使用连接池管理连接
- 实现事务管理
- 处理数据库错误

#### ERROR_HANDLING

- 实现全局错误处理器
- 记录详细的错误信息
- 返回用户友好的错误消息
- 实现自定义异常类
- 处理不同环境的错误显示

#### LOGGING

- 配置结构化日志记录
- 记录请求和响应信息
- 实现日志轮转
- 使用不同的日志级别
- 不在日志中记录敏感信息

#### TESTING

- 编写单元测试和集成测试
- 使用测试客户端模拟请求
- 使用测试数据库
- 测试错误处理
- 实现API测试

#### SECURITY

- 实现HTTPS重定向
- 设置安全HTTP头
- 防止SQL注入攻击
- 防止XSS攻击
- 实现CSRF保护

#### PERFORMANCE

- 使用缓存减少数据库查询
- 实现数据库查询优化
- 使用CDN加速静态资源
- 实现请求压缩
- 监控应用性能

#### CONFIGURATION

- 使用环境变量管理配置
- 实现不同环境的配置
- 验证配置参数
- 使用配置文件管理复杂配置
- 实现配置热重载

#### API_DESIGN

- 使用RESTful API设计
- 实现API版本控制
- 使用适当的HTTP状态码
- 实现API文档
- 使用API限流

#### TEMPLATE_ENGINE

- 使用Jinja2模板引擎
- 实现模板继承
- 使用模板宏
- 实现模板缓存
- 防止模板注入攻击

#### STATIC_FILES

- 组织静态文件结构
- 使用CDN加速静态资源
- 实现静态文件版本控制
- 压缩CSS和JavaScript
- 使用适当的MIME类型

#### SESSION_MANAGEMENT

- 配置安全的会话设置
- 实现会话超时
- 使用服务器端会话存储
- 实现会话固定攻击防护
- 在登出时清除会话

#### MIDDLEWARE

- 实现自定义中间件
- 处理跨域请求
- 实现请求日志记录
- 处理请求预处理
- 实现响应后处理

#### DEPLOYMENT

- 使用WSGI服务器部署
- 配置反向代理
- 实现健康检查
- 使用环境变量配置
- 实现日志收集

#### MONITORING

- 实现应用监控
- 记录性能指标
- 实现错误追踪
- 监控数据库性能
- 实现告警机制

#### CACHING

- 使用Redis进行缓存
- 实现缓存策略
- 处理缓存失效
- 使用缓存预热
- 监控缓存性能

#### BACKGROUND_TASKS

- 使用Celery处理后台任务
- 实现任务队列
- 处理任务失败
- 实现任务监控
- 使用任务调度

#### API_DOCUMENTATION

- 使用Swagger生成API文档
- 实现API测试界面
- 记录API变更
- 提供API示例
- 实现API版本管理
