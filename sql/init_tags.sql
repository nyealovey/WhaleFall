-- 初始化默认标签数据
INSERT INTO tags (name, display_name, category, color, description, sort_order, is_active, created_at, updated_at) VALUES
-- 地区标签
('wenzhou', '温州', 'location', 'primary', '温州市', 1, true, NOW(), NOW()),
('hangzhou', '杭州', 'location', 'primary', '杭州市', 2, true, NOW(), NOW()),
('shanghai', '上海', 'location', 'info', '上海市', 3, true, NOW(), NOW()),
('beijing', '北京', 'location', 'success', '北京市', 4, true, NOW(), NOW()),
('guangzhou', '广州', 'location', 'warning', '广州市', 5, true, NOW(), NOW()),
('shenzhen', '深圳', 'location', 'info', '深圳市', 6, true, NOW(), NOW()),
('chengdu', '成都', 'location', 'success', '成都市', 7, true, NOW(), NOW()),
('xian', '西安', 'location', 'secondary', '西安市', 8, true, NOW(), NOW()),

-- 公司类型标签
('company_limited', '股份有限公司', 'company_type', 'success', '股份有限公司', 1, true, NOW(), NOW()),
('company_llc', '有限责任公司', 'company_type', 'success', '有限责任公司', 2, true, NOW(), NOW()),
('company_group', '集团', 'company_type', 'info', '集团公司', 3, true, NOW(), NOW()),
('company_branch', '分公司', 'company_type', 'secondary', '分公司', 4, true, NOW(), NOW()),
('company_subsidiary', '子公司', 'company_type', 'secondary', '子公司', 5, true, NOW(), NOW()),
('company_partnership', '合伙企业', 'company_type', 'warning', '合伙企业', 6, true, NOW(), NOW()),

-- 环境标签
('prod', '生产环境', 'environment', 'danger', '生产环境', 1, true, NOW(), NOW()),
('test', '测试环境', 'environment', 'warning', '测试环境', 2, true, NOW(), NOW()),
('dev', '开发环境', 'environment', 'info', '开发环境', 3, true, NOW(), NOW()),
('staging', '预发布环境', 'environment', 'warning', '预发布环境', 4, true, NOW(), NOW()),
('demo', '演示环境', 'environment', 'secondary', '演示环境', 5, true, NOW(), NOW()),

-- 部门标签
('it_dept', 'IT部门', 'department', 'primary', '信息技术部门', 1, true, NOW(), NOW()),
('finance_dept', '财务部门', 'department', 'success', '财务部门', 2, true, NOW(), NOW()),
('hr_dept', '人事部门', 'department', 'info', '人力资源部门', 3, true, NOW(), NOW()),
('marketing_dept', '市场部门', 'department', 'warning', '市场部门', 4, true, NOW(), NOW()),
('sales_dept', '销售部门', 'department', 'danger', '销售部门', 5, true, NOW(), NOW()),
('ops_dept', '运维部门', 'department', 'secondary', '运维部门', 6, true, NOW(), NOW()),

-- 项目标签
('project_a', '项目A', 'project', 'primary', '重要项目A', 1, true, NOW(), NOW()),
('project_b', '项目B', 'project', 'success', '重要项目B', 2, true, NOW(), NOW()),
('project_c', '项目C', 'project', 'info', '重要项目C', 3, true, NOW(), NOW()),
('project_d', '项目D', 'project', 'warning', '重要项目D', 4, true, NOW(), NOW()),
('project_e', '项目E', 'project', 'danger', '重要项目E', 5, true, NOW(), NOW()),

-- 其他标签
('high_priority', '高优先级', 'other', 'danger', '高优先级标签', 1, true, NOW(), NOW()),
('low_priority', '低优先级', 'other', 'secondary', '低优先级标签', 2, true, NOW(), NOW()),
('backup', '备份', 'other', 'info', '备份相关', 3, true, NOW(), NOW()),
('monitoring', '监控', 'other', 'warning', '监控相关', 4, true, NOW(), NOW()),
('maintenance', '维护', 'other', 'secondary', '维护相关', 5, true, NOW(), NOW());
