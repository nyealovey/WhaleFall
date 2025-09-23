import os
import re
import sys
import csv
from collections import defaultdict
import cssutils  # 需要 pip install cssutils
from bs4 import BeautifulSoup

def find_all_files(directory, extension):
    """递归查找指定目录中具有特定扩展名的所有文件。"""
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(extension):
                file_paths.append(os.path.join(root, file))
    return file_paths

def extract_selectors_from_css(css_content):
    """从CSS内容中提取所有类和ID选择器，支持组合选择器。"""
    # 移除注释（cssutils会自动处理，但额外清理）
    css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    
    sheet = cssutils.parseString(css_content)
    selectors = set()
    
    for rule in sheet:
        if rule.type == rule.STYLE_RULE:
            selector_list = rule.selectorList
            for sel in selector_list:
                # 提取简单类/ID（即使在组合中，如 .parent .child）
                simple_pattern = re.compile(r'([.#])(-?[_a-zA-Z][_a-zA-Z0-9-]*)')
                for match in simple_pattern.finditer(str(sel)):
                    selectors.add(match.group(0))
    
    return sorted(list(selectors))

def extract_linked_css_files(html_content, html_file_path):
    """从HTML内容中提取链接的CSS文件路径。"""
    soup = BeautifulSoup(html_content, 'lxml')  # 注意：需 import BeautifulSoup from bs4
    linked_css = []
    for link_tag in soup.find_all('link', rel='stylesheet'):
        href = link_tag.get('href')
        if href:
            # 处理 url_for 生成的路径
            if 'url_for' in href:
                match = re.search(r"""filename=['"]([^'"]+)['"]""", href)
                if match:
                    relative_path = match.group(1)
                    css_path = os.path.join('app', 'static', *relative_path.split('/'))
                    linked_css.append(css_path)
            # 处理直接路径
            else:
                css_path = os.path.normpath(os.path.join(os.path.dirname(html_file_path), href))
                linked_css.append(css_path)
    return linked_css

def extract_linked_js_files(html_content, html_file_path):
    """从HTML内容中提取链接的JS文件路径，跟CSS类似。"""
    from bs4 import BeautifulSoup  # 延迟导入
    soup = BeautifulSoup(html_content, 'lxml')
    linked_js = []
    for script_tag in soup.find_all('script', src=True):
        src = script_tag.get('src')
        if src:
            # 处理 url_for 生成的路径
            if 'url_for' in src:
                match = re.search(r"""filename=['"]([^'"]+)['"]""", src)
                if match:
                    relative_path = match.group(1)
                    js_path = os.path.join('app', 'static', *relative_path.split('/'))
                    linked_js.append(js_path)
            # 处理直接路径
            else:
                js_path = os.path.normpath(os.path.join(os.path.dirname(html_file_path), src))
                linked_js.append(js_path)
    return linked_js

def count_selector_usage(selector, html_content):
    """计算选择器在HTML内容中的使用次数。"""
    selector_name = selector[1:]
    count = 0
    if selector.startswith('.'):
        # 使用正则表达式查找类属性并检查选择器是否在类列表中
        pattern = r'class\s*=\s*[\'"]([^\'"]+)[\'"]'
        matches = re.findall(pattern, html_content)
        for class_string in matches:
            if selector_name in class_string.split():
                count += 1
    elif selector.startswith('#'):
        # 搜索 id="selector_name"
        pattern = r'id\s*=\s*[\'"]' + re.escape(selector_name) + r'[\'"]'
        count = len(re.findall(pattern, html_content))
    return count

def extract_used_selectors_from_js(js_content):
    """从JS内容中提取所有使用的类和ID选择器（硬编码字符串）。"""
    used_selectors = set()
    
    # 匹配 className = "class" 或 classList.add("class")
    class_patterns = [
        r'className\s*=\s*[\'"]([^\'"]+)[\'"]',  # className = "class"
        r'classList\.add\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',  # classList.add("class")
        r'classList\.remove\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',  # classList.remove("class")
        r'classList\.toggle\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',  # classList.toggle("class")
        r'class\s*=\s*[\'"]([^\'"]+)[\'"]',  # 直接 class = "class" (虽不标准，但常见)
    ]
    
    for pattern in class_patterns:
        matches = re.findall(pattern, js_content)
        for class_string in matches:
            for class_name in class_string.split():
                used_selectors.add(f".{class_name}")
    
    # 匹配 getElementById("id")
    id_pattern = r'(getElementById|getElementsByClassName)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
    id_matches = re.findall(id_pattern, js_content)
    for _, id_name in id_matches:
        used_selectors.add(f"#{id_name}")
    
    # 额外：querySelector(".class") 或 querySelector("#id")
    query_pattern = r'querySelector\s*\(\s*([.#][^)\'"]+)\s*\)'
    query_matches = re.findall(query_pattern, js_content)
    for sel in query_matches:
        if sel.startswith(('.', '#')):
            used_selectors.add(sel)
    
    return sorted(list(used_selectors))

def analyze_project():
    """分析整个项目中的CSS、JS和HTML文件。"""
    css_files = find_all_files('app/static/css', '.css')
    js_files = find_all_files('app/static/js', '.js')  # 假设JS在 app/static/js
    html_files = find_all_files('app/templates', '.html')

    if not html_files:
        print("在 'app/templates' 目录中未找到HTML文件。")
        return

    # 1. 构建 HTML -> CSS/JS 的映射
    html_to_css_map = {}
    html_to_js_map = {}
    # 2. 构建 CSS/JS -> HTML 的反向映射
    css_to_html_map = defaultdict(list)
    js_to_html_map = defaultdict(list)
    # 3. 读取所有 HTML 文件内容
    html_contents = {}

    for html_file in html_files:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            html_contents[html_file] = content
            linked_css_files = extract_linked_css_files(content, html_file)
            linked_js_files = extract_linked_js_files(content, html_file)
            html_to_css_map[html_file] = linked_css_files
            html_to_js_map[html_file] = linked_js_files
            for css_file in linked_css_files:
                css_to_html_map[css_file].append(html_file)
            for js_file in linked_js_files:
                js_to_html_map[js_file].append(html_file)

    # 分析CSS文件：为每个CSS构建选择器和使用次数
    css_analysis = {}  # {css_file: {selector: count}}
    for css_file in css_files:
        with open(css_file, 'r', encoding='utf-8', errors='ignore') as f:
            css_content = f.read()
        
        selectors = extract_selectors_from_css(css_content)
        relevant_html_files = css_to_html_map.get(css_file, [])
        if not relevant_html_files:
            css_analysis[css_file] = {sel: 0 for sel in selectors}
            continue

        combined_html_content = "".join([html_contents[hf] for hf in relevant_html_files])
        css_analysis[css_file] = {sel: count_selector_usage(sel, combined_html_content) for sel in selectors}

    # 分析JS文件：为每个JS构建使用的选择器（在HTML中的计数）
    js_analysis = {}  # {js_file: {selector: count}} - 计数基于相关HTML
    for js_file in js_files:
        with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
            js_content = f.read()
        
        selectors = extract_used_selectors_from_js(js_content)
        relevant_html_files = js_to_html_map.get(js_file, [])
        if not relevant_html_files:
            js_analysis[js_file] = {sel: 0 for sel in selectors}
            continue

        combined_html_content = "".join([html_contents[hf] for hf in relevant_html_files])
        js_analysis[js_file] = {sel: count_selector_usage(sel, combined_html_content) for sel in selectors}

    # 从模板出发生成表格数据（CSS和JS分开，但统一CSV）
    table_data = []
    # CSS部分
    for html_file, linked_css in html_to_css_map.items():
        for css_file in linked_css:
            if css_file in css_analysis:
                for selector, count in css_analysis[css_file].items():
                    table_data.append({
                        'Template File': os.path.basename(html_file),
                        'Linked File': os.path.basename(css_file),
                        'Type': 'CSS',
                        'Selector': selector,
                        'Usage Count': count,
                        'Status': 'Unused' if count == 0 else 'Used'
                    })
    # JS部分
    for html_file, linked_js in html_to_js_map.items():
        for js_file in linked_js:
            if js_file in js_analysis:
                for selector, count in js_analysis[js_file].items():
                    table_data.append({
                        'Template File': os.path.basename(html_file),
                        'Linked File': os.path.basename(js_file),
                        'Type': 'JS',
                        'Selector': selector,
                        'Usage Count': count,
                        'Status': 'Unused' if count == 0 else 'Used'
                    })

    # 生成CSV表格
    generate_csv_report(table_data)

def generate_csv_report(table_data):
    """生成CSV表格报告，从模板文件出发，包括CSS和JS。"""
    report_file = "selectors_usage_table.csv"
    if not table_data:
        print("未找到任何模板-CSS/JS-选择器关系。")
        return

    fieldnames = ['Template File', 'Linked File', 'Type', 'Selector', 'Usage Count', 'Status']
    with open(report_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(table_data)

    # 打印汇总统计
    total_selectors = len(table_data)
    unused_count = len([row for row in table_data if row['Status'] == 'Unused'])
    css_count = len([row for row in table_data if row['Type'] == 'CSS'])
    js_count = len([row for row in table_data if row['Type'] == 'JS'])
    print(f"表格已生成：{report_file}")
    print(f"总选择器数：{total_selectors} (CSS: {css_count}, JS: {js_count})")
    print(f"未使用选择器数：{unused_count}")
    if unused_count > 0:
        print("建议审查未使用选择器以优化代码。")

if __name__ == "__main__":
    analyze_project()