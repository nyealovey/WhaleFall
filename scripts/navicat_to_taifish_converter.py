#!/usr/bin/env python3
"""
Navicat连接配置转换为鲸落实例CSV模板格式
支持批量转换和智能分类
"""

import xml.etree.ElementTree as ET
import csv
import re
from typing import List, Dict, Tuple

def categorize_instance(name: str, host: str) -> Tuple[str, str]:
    """根据实例名称和主机地址智能分类"""
    
    # 根据名称前缀分类
    if name.startswith('gf-'):
        category = 'GF集团'
        if 'mes' in name:
            subcategory = 'MES系统'
        elif 'wms' in name:
            subcategory = 'WMS系统'
        elif 'mysql' in name:
            subcategory = 'MySQL集群'
        elif 'basis' in name:
            subcategory = '基础系统'
        elif 'qm' in name:
            subcategory = '质量管理'
        else:
            subcategory = '其他系统'
    elif name.startswith('jt-'):
        category = 'JT集团'
        if 'bi' in name:
            subcategory = 'BI系统'
        elif 'crm' in name or 'crm' in name:
            subcategory = 'CRM系统'
        elif 'logistics' in name:
            subcategory = '物流系统'
        elif 'user' in name:
            subcategory = '用户系统'
        else:
            subcategory = '其他系统'
    elif name.startswith('shnyk-'):
        category = '上海NYC'
        subcategory = 'WMS系统'
    elif name.startswith('wl-'):
        category = 'WL系统'
        subcategory = '基础系统'
    elif name.startswith('yb-'):
        category = 'YB系统'
        subcategory = '薪资系统'
    else:
        category = '其他'
        subcategory = '未知'
    
    return category, subcategory

def generate_description(name: str, host: str, port: str) -> str:
    """生成详细的实例描述"""
    category, subcategory = categorize_instance(name, host)
    
    # 根据端口判断环境
    if port == '3306':
        env = '标准环境'
    elif port == '6603':
        env = '集群环境'
    else:
        env = '自定义环境'
    
    return f"{category} - {subcategory} - {env} ({host}:{port})"

def parse_navicat_xml(xml_content: str) -> List[Dict[str, str]]:
    """解析Navicat XML配置"""
    root = ET.fromstring(xml_content)
    connections = []
    
    for connection in root.findall('Connection'):
        name = connection.get('ConnectionName', '')
        host = connection.get('Host', '')
        port = connection.get('Port', '')
        conn_type = connection.get('ConnType', '').lower()
        
        # 跳过非MySQL连接
        if conn_type != 'mysql':
            continue
            
        # 生成描述
        description = generate_description(name, host, port)
        
        # 根据用户名确定凭据ID
        username = connection.get('UserName', 'jinxj')
        if username == 'jinxj':
            credential_id = '1'  # 默认凭据
        elif username == 'xmes_read':
            credential_id = '2'  # 只读凭据
        elif username == 'bpm_admin':
            credential_id = '3'  # BPM管理凭据
        elif username == 'dc_lv_etl':
            credential_id = '4'  # ETL凭据
        elif username == 'doris_binlog':
            credential_id = '5'  # Doris同步凭据
        else:
            credential_id = '1'  # 默认凭据
        
        conn_data = {
            'name': name,
            'db_type': 'mysql',
            'host': host,
            'port': port,
            'database_name': 'mysql',  # 默认数据库名
            'description': description,
            'credential_id': credential_id
        }
        connections.append(conn_data)
    
    return connections

def generate_csv(connections: List[Dict[str, str]], output_file: str = 'navicat_instances_detailed.csv'):
    """生成详细的CSV文件"""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'db_type', 'host', 'port', 'database_name', 'description', 'credential_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for conn in connections:
            writer.writerow(conn)
    
    print(f"已生成详细CSV文件: {output_file}")
    print(f"共转换 {len(connections)} 个连接")

def generate_summary(connections: List[Dict[str, str]]):
    """生成转换摘要"""
    print("\n=== 转换摘要 ===")
    
    # 按分类统计
    categories = {}
    ports = {}
    credentials = {}
    
    for conn in connections:
        # 分类统计
        category, _ = categorize_instance(conn['name'], conn['host'])
        categories[category] = categories.get(category, 0) + 1
        
        # 端口统计
        port = conn['port']
        ports[port] = ports.get(port, 0) + 1
        
        # 凭据统计
        cred_id = conn['credential_id']
        credentials[cred_id] = credentials.get(cred_id, 0) + 1
    
    print(f"总连接数: {len(connections)}")
    print(f"分类分布: {dict(categories)}")
    print(f"端口分布: {dict(ports)}")
    print(f"凭据分布: {dict(credentials)}")
    
    print("\n=== 前10个连接示例 ===")
    for i, conn in enumerate(connections[:10]):
        print(f"{i+1:2d}. {conn['name']:25s} | {conn['host']:15s}:{conn['port']:4s} | {conn['description']}")

def main():
    # 示例XML内容（实际使用时从文件读取）
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Connections Ver="1.5">
    <Connection ConnectionName="gf-mes3galera-01l" ConnType="MYSQL" Host="10.10.102.226" Port="6603" UserName="jinxj"/>
    <Connection ConnectionName="gf-mysql8-01l" ConnType="MYSQL" Host="10.10.102.101" Port="6603" UserName="jinxj"/>
    <Connection ConnectionName="jt-bimysql-02l" ConnType="MYSQL" Host="10.10.100.148" Port="6603" UserName="jinxj"/>
</Connections>"""
    
    # 解析XML
    connections = parse_navicat_xml(xml_content)
    
    # 生成CSV
    generate_csv(connections)
    
    # 生成摘要
    generate_summary(connections)

if __name__ == "__main__":
    main()
