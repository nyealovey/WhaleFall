#!/usr/bin/env python3
"""
测试实例详情页面新功能
"""

import requests
from bs4 import BeautifulSoup

def test_instance_detail_features():
    """测试实例详情页面功能"""
    
    # 测试实例详情页面
    url = "http://localhost:5001/instances/14"
    
    try:
        # 发送请求
        response = requests.get(url, timeout=10)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查复选框是否存在
            checkbox = soup.find('input', {'id': 'showDeletedAccounts'})
            if checkbox:
                print("✅ 软删除账户复选框已添加")
            else:
                print("❌ 软删除账户复选框未找到")
            
            # 检查账户计数是否存在
            account_count = soup.find('span', {'id': 'accountCount'})
            if account_count:
                print(f"✅ 账户计数显示: {account_count.text}")
            else:
                print("❌ 账户计数未找到")
            
            # 检查表格头部是否包含新列
            table_headers = soup.find_all('th')
            header_texts = [th.get_text().strip() for th in table_headers]
            
            if '超级用户' in header_texts:
                print("✅ 超级用户列已添加")
            else:
                print("❌ 超级用户列未找到")
                
            if '最后变更时间' in header_texts:
                print("✅ 最后变更时间列已添加")
            else:
                print("❌ 最后变更时间列未找到")
            
            # 检查JavaScript函数是否存在
            script_content = soup.find('script', string=lambda text: text and 'toggleDeletedAccounts' in text)
            if script_content:
                print("✅ JavaScript切换函数已添加")
            else:
                print("❌ JavaScript切换函数未找到")
                
            print(f"\n表格头部列: {header_texts}")
            
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(response.text[:500])
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_instance_detail_features()
