"""
MW数据站批量字段提取器
读取本地HTML文件，解析侧边栏菜单结构，自动爬取所有页面的字段信息
"""
import requests
import re
import json
import html
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://mwstats.info"
OUTPUT_BASE = Path(__file__).parent / "字段数据"


def fetch_menu_from_website():
    """从网站获取菜单结构"""
    print("=" * 70)
    print("从网站获取菜单...")
    print("=" * 70)

    url = f"{BASE_URL}/?lang=zh-hans"
    print(f"访问: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        # 查找sidebar-menu的context数据
        pattern = r'<sidebar-menu\s+v-bind:context="([^"]+)"'
        match = re.search(pattern, response.text)

        if not match:
            print("未找到侧边栏菜单数据")
            return None

        # 解码HTML实体
        json_str = html.unescape(match.group(1))
        menu_data = json.loads(json_str)

        print(f"成功获取菜单数据")
        return menu_data.get('items', [])

    except Exception as e:
        print(f"获取菜单失败: {e}")
        return None


def extract_menu_urls(items, parent_path="", parent_title=""):
    """
    递归提取菜单中的所有URL
    返回格式: [(标题, URL, 文件路径), ...]
    """
    urls = []

    for item in items:
        title = item.get('title', '')
        url = item.get('url', '')
        children = item.get('children', [])
        is_language = item.get('is_language', False)
        is_language_menu = item.get('is_language_menu', False)

        # 跳过语言选择菜单
        if is_language or is_language_menu:
            continue

        # 跳过没有URL的父菜单（但要处理它的子菜单）
        if url:
            # 构建文件路径
            if parent_title:
                file_path = f"{parent_title}/{title}"
            else:
                file_path = title

            urls.append((title, url, file_path))

        # 递归处理子菜单
        if children:
            current_title = title if title else parent_title
            child_urls = extract_menu_urls(children, parent_path, current_title)
            urls.extend(child_urls)

    return urls


def fetch_fields_from_url(url):
    """从URL提取字段信息（简化版，仅提取字段名）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        # 尝试多种组件模式
        patterns = [
            r'<ship-list\s+v-bind:context="([^"]+)"',
            r'<weapon-list\s+v-bind:context="([^"]+)"',
            r'<aircraft-list\s+v-bind:context="([^"]+)"',
            r'<item-list\s+v-bind:context="([^"]+)"',
            r'<(\w+)-list\s+v-bind:context="([^"]+)"',
        ]

        data = None
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                if len(match.groups()) == 2:
                    json_str = html.unescape(match.group(2))
                else:
                    json_str = html.unescape(match.group(1))

                try:
                    data = json.loads(json_str)
                    break
                except json.JSONDecodeError:
                    continue

        if not data:
            return None

        items = data.get('list', {}).get('items', [])
        if not items:
            return None

        # 收集所有字段
        all_fields = set()
        for item in items:
            all_fields.update(item.keys())

        # 分析字段类型和样本
        field_info = {}
        for field in all_fields:
            for item in items:
                value = item.get(field)
                if value is not None and value != '':
                    field_info[field] = {
                        'type': type(value).__name__,
                        'sample': str(value)[:50]
                    }
                    break

        return {
            'total': data.get('list', {}).get('total', 0),
            'fields': sorted(all_fields),
            'field_info': field_info
        }

    except Exception as e:
        print(f"      错误: {e}")
        return None


def save_fields_to_file(title, url, fields_data, file_path):
    """保存字段到文件"""
    if not fields_data:
        return False

    # 创建目录
    output_file = OUTPUT_BASE / f"{file_path}_字段列表.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# MW数据站字段提取结果\n")
        f.write(f"# 标题: {title}\n")
        f.write(f"# URL: {url}\n")
        f.write(f"# 总数: {fields_data['total']}\n")
        f.write(f"# 字段数: {len(fields_data['fields'])}\n\n")

        f.write("字段名,类型,示例值\n")
        for field in fields_data['fields']:
            info = fields_data['field_info'].get(field, {})
            field_type = info.get('type', 'unknown')
            sample = info.get('sample', 'N/A').replace(',', '，')
            f.write(f"{field},{field_type},{sample}\n")

    return True


def process_single_url(title, url, file_path):
    """处理单个URL"""
    full_url = BASE_URL + url if not url.startswith('http') else url
    print(f"  [{title}]")
    print(f"    URL: {url}")

    fields_data = fetch_fields_from_url(full_url)

    if fields_data:
        if save_fields_to_file(title, full_url, fields_data, file_path):
            print(f"    成功: {len(fields_data['fields'])} 个字段")
            return True
        else:
            print(f"    失败: 保存文件时出错")
            return False
    else:
        print(f"    失败: 无法提取数据")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("MW数据站 - 批量字段提取器")
    print("=" * 70)

    # 从网站获取菜单
    menu_items = fetch_menu_from_website()
    if not menu_items:
        return

    # 提取所有URL
    all_urls = extract_menu_urls(menu_items)

    print(f"\n找到 {len(all_urls)} 个页面")
    print("=" * 70)

    # 预览列表
    print("\n将要爬取的页面:")
    for i, (title, url, file_path) in enumerate(all_urls, 1):
        print(f"  {i}. {file_path}")

    # 确认
    confirm = input(f"\n是否开始爬取所有 {len(all_urls)} 个页面? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return

    print("\n" + "=" * 70)
    print("开始批量爬取...")
    print("=" * 70)

    # 并发爬取
    success_count = 0
    failed_urls = []

    start_time = time.time()

    # 使用线程池，但限制并发数避免被封
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(process_single_url, title, url, file_path): (title, url)
            for title, url, file_path in all_urls
        }

        for future in as_completed(futures):
            title, url = futures[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    failed_urls.append((title, url))
            except Exception as e:
                print(f"  [{title}] 异常: {e}")
                failed_urls.append((title, url))

            # 添加小延时
            time.sleep(0.5)

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("批量爬取完成!")
    print("=" * 70)
    print(f"成功: {success_count}/{len(all_urls)}")
    print(f"耗时: {elapsed:.2f} 秒")
    print(f"保存位置: {OUTPUT_BASE}")

    if failed_urls:
        print(f"\n失败的页面 ({len(failed_urls)}):")
        for title, url in failed_urls:
            print(f"  - {title}: {url}")

    print("=" * 70)


if __name__ == "__main__":
    main()
