#!/usr/bin/env python3
"""
Navicat连接配置转换为鲸落实例CSV模板格式
"""

import xml.etree.ElementTree as ET
import csv
import sys
from typing import List, Dict

def parse_navicat_xml(xml_content: str) -> List[Dict[str, str]]:
    """解析Navicat XML配置"""
    root = ET.fromstring(xml_content)
    connections = []
    
    for connection in root.findall('Connection'):
        conn_data = {
            'name': connection.get('ConnectionName', ''),
            'db_type': connection.get('ConnType', '').lower(),
            'host': connection.get('Host', ''),
            'port': connection.get('Port', ''),
            'database_name': 'mysql',  # 默认数据库名
            'description': f"{connection.get('ConnectionName', '')} - {connection.get('Host', '')}",
            'credential_id': '1'  # 默认凭据ID，需要根据实际情况调整
        }
        connections.append(conn_data)
    
    return connections

def generate_csv(connections: List[Dict[str, str]], output_file: str = 'navicat_instances.csv'):
    """生成CSV文件"""
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'db_type', 'host', 'port', 'database_name', 'description', 'credential_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for conn in connections:
            writer.writerow(conn)
    
    print(f"已生成CSV文件: {output_file}")
    print(f"共转换 {len(connections)} 个连接")

def main():
    # 从标准输入读取XML内容
    xml_content = sys.stdin.read()
    
    # 解析XML
    connections = parse_navicat_xml(xml_content)
    
    # 生成CSV
    generate_csv(connections)
    
    # 打印前几个示例
    print("\n前5个转换结果:")
    for i, conn in enumerate(connections[:5]):
        print(f"{i+1}. {conn['name']} - {conn['host']}:{conn['port']}")

if __name__ == "__main__":
    main()
