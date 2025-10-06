"""
MW数据站批量数据爬取器
读取字段数据文件夹，批量爬取所有页面的中英文数据并保存为CSV
"""
import requests
import re
import json
import csv
import html
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://mwstats.info"
FIELDS_DIR = Path(__file__).parent / "字段数据"
OUTPUT_DIR = Path(__file__).parent / "爬取数据"


def read_field_file(field_file):
    """
    读取字段列表文件，提取URL和字段信息
    返回: (标题, URL, 字段列表)
    """
    with open(field_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    title = None
    url = None
    fields = []

    for line in lines:
        line = line.strip()
        if line.startswith('# 标题:'):
            title = line.replace('# 标题:', '').strip()
        elif line.startswith('# URL:'):
            url = line.replace('# URL:', '').strip()
        elif line and not line.startswith('#') and ',' in line:
            # 解析字段行: 字段名,类型,示例值
            parts = line.split(',')
            if len(parts) >= 1 and parts[0] != '字段名':
                fields.append(parts[0])

    return title, url, fields


def fetch_page_data(url, page=1):
    """获取单页数据"""
    page_url = f"{url}&page={page}" if '?' in url else f"{url}?page={page}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    response = requests.get(page_url, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = 'utf-8'

    # 查找list组件的context数据（通用模式）
    patterns = [
        r'<ship-list\s+v-bind:context="([^"]+)"',
        r'<weapon-list\s+v-bind:context="([^"]+)"',
        r'<aircraft-list\s+v-bind:context="([^"]+)"',
        r'<item-list\s+v-bind:context="([^"]+)"',
        r'<(\w+)-list\s+v-bind:context="([^"]+)"',
    ]

    for pattern in patterns:
        match = re.search(pattern, response.text)
        if match:
            if len(match.groups()) == 2:
                json_str = html.unescape(match.group(2))
            else:
                json_str = html.unescape(match.group(1))

            try:
                data = json.loads(json_str)
                items_list = data.get('list', {}).get('items', [])
                total = data.get('list', {}).get('total', 0)
                return items_list, total
            except json.JSONDecodeError:
                continue

    return None, 0


def fetch_all_data(url, lang_name=""):
    """爬取所有数据（并发爬取所有页面）"""
    print(f"  [{lang_name}] 获取数据...")

    try:
        # 获取第一页
        items_list, total = fetch_page_data(url, 1)

        if items_list is None:
            print(f"    获取失败")
            return []

        per_page = len(items_list)
        total_pages = (total + per_page - 1) // per_page
        print(f"    总共 {total} 条, {total_pages} 页")

        all_items = items_list.copy()

        # 如果只有一页，直接返回
        if total_pages == 1:
            return all_items

        # 并发获取剩余页面
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(fetch_page_data, url, page): page
                for page in range(2, total_pages + 1)
            }

            for future in as_completed(futures):
                page = futures[future]
                try:
                    items, _ = future.result()
                    if items:
                        all_items.extend(items)
                except Exception as e:
                    print(f"    Page {page} 错误: {e}")

        print(f"    完成: {len(all_items)} 条")
        return all_items

    except Exception as e:
        print(f"    爬取失败: {e}")
        return []


def find_id_field(items):
    """
    自动查找ID字段
    常见的ID字段: id, ship_id, weapon_id, unit_id等
    """
    if not items:
        return None

    first_item = items[0]
    # 优先查找包含'id'的字段
    for key in first_item.keys():
        if 'id' in key.lower():
            return key

    # 如果没找到，返回None
    return None


def merge_bilingual_data(items_zh, items_en):
    """
    合并中英文数据
    """
    if not items_zh or not items_en:
        return items_zh if items_zh else items_en

    # 查找ID字段
    id_field = find_id_field(items_zh)

    if not id_field:
        print("    警告: 未找到ID字段，无法匹配中英文数据")
        return items_zh

    # 创建英文数据的ID映射
    en_dict = {}
    for item in items_en:
        item_id = item.get(id_field)
        if item_id:
            en_dict[item_id] = item

    # 合并数据
    merged_items = []
    for item_zh in items_zh:
        item_id = item_zh.get(id_field)
        item_en = en_dict.get(item_id, {})

        # 创建合并项
        merged_item = item_zh.copy()

        # 为主要的名称字段添加英文版本
        for key in item_zh.keys():
            if 'name' in key.lower() or 'title' in key.lower():
                en_value = item_en.get(key, '')
                if en_value:
                    merged_item[f"{key}_en"] = en_value

        merged_items.append(merged_item)

    return merged_items


def extract_all_fields(items):
    """
    从所有项中提取所有字段
    将image相关字段放到最后
    """
    all_fields = set()
    for item in items:
        all_fields.update(item.keys())

    # 分离image字段和其他字段
    image_fields = []
    other_fields = []

    for field in sorted(all_fields):
        if 'image' in field.lower():
            image_fields.append(field)
        else:
            other_fields.append(field)

    # 其他字段在前，image字段在后
    return other_fields + image_fields


def save_to_csv(items, output_file):
    """保存数据到CSV"""
    if not items:
        print(f"    无数据可保存")
        return False

    # 提取所有字段
    all_fields = extract_all_fields(items)

    # 确保输出目录存在
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入CSV
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(items)

    print(f"    已保存 {len(items)} 条数据")
    return True


def process_single_page(field_file, relative_path):
    """处理单个字段文件"""
    print(f"\n处理: {relative_path}")

    # 读取字段文件
    title, url, fields = read_field_file(field_file)

    if not url:
        print(f"  跳过: 没有URL")
        return False

    # 构建中英文URL
    if '?lang=zh-hans' in url:
        url_zh = url
        url_en = url.replace('?lang=zh-hans', '').replace('&lang=zh-hans', '')
    else:
        url_zh = f"{url}?lang=zh-hans" if '?' not in url else f"{url}&lang=zh-hans"
        url_en = url

    # 并发爬取中英文数据
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_zh = executor.submit(fetch_all_data, url_zh, "中文")
        future_en = executor.submit(fetch_all_data, url_en, "英文")

        items_zh = future_zh.result()
        items_en = future_en.result()

    # 合并数据
    if items_zh or items_en:
        print(f"  合并数据...")
        merged_items = merge_bilingual_data(items_zh, items_en)

        # 保存CSV（将Path转为字符串再替换）
        csv_name = str(relative_path).replace('_字段列表.txt', '.csv')
        output_file = OUTPUT_DIR / csv_name
        return save_to_csv(merged_items, output_file)
    else:
        print(f"  失败: 无数据")
        return False


def find_all_field_files():
    """查找所有字段列表文件"""
    field_files = []

    for file_path in FIELDS_DIR.rglob('*_字段列表.txt'):
        # 获取相对路径
        relative_path = file_path.relative_to(FIELDS_DIR)
        field_files.append((file_path, relative_path))

    return field_files


def main():
    """主函数"""
    print("=" * 70)
    print("MW数据站 - 批量数据中英文名爬取器")
    print("=" * 70)

    # 检查字段数据文件夹
    if not FIELDS_DIR.exists():
        print(f"错误: 找不到字段数据文件夹: {FIELDS_DIR}")
        print("请先运行 批量字段提取器.py 生成字段数据")
        return

    # 查找所有字段文件
    field_files = find_all_field_files()

    if not field_files:
        print("未找到任何字段列表文件")
        return

    print(f"\n找到 {len(field_files)} 个字段文件")
    print("=" * 70)

    # 预览列表
    print("\n将要爬取的页面:")
    for i, (file_path, relative_path) in enumerate(field_files, 1):
        csv_name = str(relative_path).replace('_字段列表.txt', '.csv')
        print(f"  {i}. {csv_name}")

    # 确认
    confirm = input(f"\n是否开始爬取所有 {len(field_files)} 个页面? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return

    print("\n" + "=" * 70)
    print("开始批量爬取...")
    print("=" * 70)

    # 批量处理
    success_count = 0
    start_time = time.time()

    for file_path, relative_path in field_files:
        if process_single_page(file_path, relative_path):
            success_count += 1

        # 添加延时避免请求过快
        time.sleep(1)

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("批量爬取完成!")
    print("=" * 70)
    print(f"成功: {success_count}/{len(field_files)}")
    print(f"耗时: {elapsed:.2f} 秒")
    print(f"保存位置: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
