#!/usr/bin/env python3
"""
测试实例详情页面新功能（带认证）
"""

import requests
from bs4 import BeautifulSoup

def test_instance_detail_with_auth():
    """测试实例详情页面功能（带认证）"""
    
    session = requests.Session()
    
    # 登录
    login_url = "http://localhost:5001/auth/login"
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        # 获取登录页面和CSRF token
        login_page = session.get(login_url)
        soup = BeautifulSoup(login_page.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
        login_data['csrf_token'] = csrf_token
        
        # 登录
        login_response = session.post(login_url, data=login_data)
        print(f"登录状态码: {login_response.status_code}")
        
        if login_response.status_code == 200 or login_response.status_code == 302:
            # 测试实例详情页面
            detail_url = "http://localhost:5001/instances/14"
            detail_response = session.get(detail_url)
            print(f"详情页面状态码: {detail_response.status_code}")
            
            if detail_response.status_code == 200:
                soup = BeautifulSoup(detail_response.text, 'html.parser')
                
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
                scripts = soup.find_all('script')
                js_found = False
                for script in scripts:
                    if script.string and 'toggleDeletedAccounts' in script.string:
                        js_found = True
                        break
                
                if js_found:
                    print("✅ JavaScript切换函数已添加")
                else:
                    print("❌ JavaScript切换函数未找到")
                    
                print(f"\n表格头部列: {header_texts}")
                
                # 检查是否有账户数据
                account_rows = soup.find_all('tr', class_='account-row')
                print(f"账户行数: {len(account_rows)}")
                
            else:
                print(f"❌ 详情页面请求失败: {detail_response.status_code}")
                print(detail_response.text[:500])
        else:
            print(f"❌ 登录失败: {login_response.status_code}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_instance_detail_with_auth()
