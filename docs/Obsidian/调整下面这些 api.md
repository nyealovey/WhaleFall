下沉到各个对应的 databases 和 instances

| --- | ------------------------- | ------- |
| GET | /api/v1/databases/options | 获取数据库选项 |
| GET | /api/v1/instances/options | 获取实例选项  |
下沉到 instances

| Method | Path                                        | Summary  |
| ------ | ------------------------------------------- | -------- |
| POST   | /api/v1/connections/actions/batch-test      | 执行批量连接测试 |
| POST   | /api/v1/connections/actions/test            | 执行连接测试   |
| POST   | /api/v1/connections/actions/validate-params | 验证连接参数   |
| GET    | /api/v1/connections/status/{instance_id}    | 获取连接状态   |

跟 tags 放一起

| Method | Path                                 | Summary      |
| ------ | ------------------------------------ | ------------ |
| POST   | /api/v1/tags/bulk/actions/assign     | 批量分配标签       |
| POST   | /api/v1/tags/bulk/actions/remove     | 批量移除标签       |
| POST   | /api/v1/tags/bulk/actions/remove-all | 批量移除所有标签     |
| POST   | /api/v1/tags/bulk/instance-tags      | 获取实例标签列表     |
| GET    | /api/v1/tags/bulk/instances          | 获取可分配标签的实例列表 |
| GET    | /api/v1/tags/bulk/tags               | 获取标签选项       |

移除

| Method | Path                   | Summary |
| ------ | ---------------------- | ------- |
| GET    | /api/v1/admin/app-info | 获取应用信息  |
