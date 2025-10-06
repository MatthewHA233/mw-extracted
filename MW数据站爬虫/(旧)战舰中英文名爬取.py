"""
战舰数据爬虫
从 https://mwstats.info/ships 爬取战舰信息并保存到CSV
直接提取页面中的JSON数据
使用并发加速爬取
"""
import requests
import re
import json
import csv
from pathlib import Path
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def fetch_page_data(url, page=1):
    """
    获取单页数据
    """
    # 添加page参数
    page_url = f"{url}&page={page}" if '?' in url else f"{url}?page={page}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    response = requests.get(page_url, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = 'utf-8'

    # 查找ship-list组件的context数据
    pattern = r'<ship-list\s+v-bind:context="([^"]+)"'
    match = re.search(pattern, response.text)

    if not match:
        return None, 0

    # 解码HTML实体
    json_str = html.unescape(match.group(1))
    data = json.loads(json_str)

    # 提取数据
    ships_list = data.get('list', {}).get('items', [])
    total = data.get('list', {}).get('total', 0)

    return ships_list, total


def parse_ship_items(ships_list):
    """解析战舰列表"""
    ships = []
    for item in ships_list:
        try:
            ship_name = item.get('name', '')
            ship_type = item.get('unitTypeString', '')
            ship_tier = item.get('tierString', '')
            ship_rarity = item.get('rarityTypeString', '')
            ship_url = item.get('url', '')
            ship_id = item.get('id', '')

            # 提取图片URL
            image_data = item.get('image', {})
            ship_image = image_data.get('default', '')

            # 是否为新船
            is_new = item.get('isNew', False)
            is_alpha = item.get('isAlpha', False)

            if ship_name:
                ships.append({
                    'ship_name': ship_name,
                    'type': ship_type,
                    'tier': ship_tier,
                    'rarity': ship_rarity,
                    'url': ship_url,
                    'image': ship_image,
                    'ship_id': ship_id,
                    'is_new': 'Yes' if is_new else 'No',
                    'is_alpha': 'Yes' if is_alpha else 'No'
                })
        except Exception as e:
            continue
    return ships


def fetch_single_page(url, page):
    """获取单页数据（用于并发）"""
    try:
        ships_list, _ = fetch_page_data(url, page)
        if ships_list:
            return parse_ship_items(ships_list)
        return []
    except Exception as e:
        print(f"  Page {page} error: {e}")
        return []


def fetch_ships_data(url, lang_name=""):
    """
    爬取所有战舰数据（并发爬取所有页面）
    """
    print(f"\n[{lang_name}] 获取数据...")

    try:
        # 先获取第一页，确定总页数
        print(f"  获取总页数...")
        ships_list, total = fetch_page_data(url, 1)

        if ships_list is None:
            print(f"  获取失败")
            return []

        # 从第一页实际返回的条数确定每页条数
        per_page = len(ships_list)
        total_pages = (total + per_page - 1) // per_page
        print(f"  总共 {total} 艘, 每页 {per_page} 条, {total_pages} 页")

        # 解析第一页
        all_ships = parse_ship_items(ships_list)
        print(f"  第1页: {len(all_ships)} 艘")

        # 如果只有一页，直接返回
        if total_pages == 1:
            print(f"  完成: {len(all_ships)} 艘")
            return all_ships

        # 并发获取剩余页面
        print(f"  并发获取剩余 {total_pages - 1} 页...")

        with ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有页面任务
            futures = {
                executor.submit(fetch_single_page, url, page): page
                for page in range(2, total_pages + 1)
            }

            # 收集结果
            for future in as_completed(futures):
                page = futures[future]
                try:
                    ships = future.result()
                    count = len(ships)
                    all_ships.extend(ships)
                    print(f"  Page {page}: {count} 艘 (累计: {len(all_ships)})")
                except Exception as e:
                    print(f"  Page {page} 失败: {e}")

        print(f"  完成: {len(all_ships)} 艘")
        return all_ships

    except Exception as e:
        print(f"  爬取失败: {e}")
        return []


def merge_bilingual_data(ships_zh, ships_en):
    """
    合并中英文数据
    根据ship_id匹配，在中文名称后添加英文名称列
    """
    # 创建英文数据的ID映射
    en_dict = {ship['ship_id']: ship for ship in ships_en}

    merged_ships = []

    for ship_zh in ships_zh:
        ship_id = ship_zh['ship_id']

        # 查找对应的英文数据
        ship_en = en_dict.get(ship_id, {})
        ship_name_en = ship_en.get('ship_name', '')

        # 合并数据
        merged_ship = ship_zh.copy()
        merged_ship['ship_name_en'] = ship_name_en

        merged_ships.append(merged_ship)

    return merged_ships


def save_to_csv(ships, output_file):
    """
    保存战舰数据到CSV文件
    """
    if not ships:
        print("没有数据可保存")
        return

    # 确保输出目录存在
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['ship_name', 'ship_name_en', 'type', 'tier', 'rarity', 'url', 'image', 'ship_id', 'is_new', 'is_alpha']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(ships)

    print(f"\n已保存 {len(ships)} 艘战舰数据到 {output_file}")


def main():
    """
    主函数 - 并发爬取中英文数据并合并
    """
    print("=" * 60)
    print("战舰数据爬虫 (中英文双语版 - 并发加速)")
    print("=" * 60)
    start_time = time.time()

    # 并发爬取中英文数据
    print("\n并发爬取中英文数据...")

    with ThreadPoolExecutor(max_workers=2) as executor:
        # 同时提交中文和英文任务
        future_zh = executor.submit(fetch_ships_data, "https://mwstats.info/ships?lang=zh-hans", "中文")
        future_en = executor.submit(fetch_ships_data, "https://mwstats.info/ships", "英文")

        # 等待结果
        ships_zh = future_zh.result()
        ships_en = future_en.result()

    # 合并数据
    if ships_zh and ships_en:
        print(f"\n合并中英文数据...")
        print(f"  中文: {len(ships_zh)} 艘")
        print(f"  英文: {len(ships_en)} 艘")

        merged_ships = merge_bilingual_data(ships_zh, ships_en)
        print(f"  合并: {len(merged_ships)} 艘")

        # 保存到当前目录，使用中文文件名
        output_file = Path(__file__).parent / "战舰中英文名对照表.csv"
        save_to_csv(merged_ships, str(output_file))

        # 打印统计信息
        print(f"\n统计信息:")
        print(f"总计: {len(merged_ships)} 艘")

        # 按类型统计
        type_count = {}
        for ship in merged_ships:
            ship_type = ship['type'] or '未知'
            type_count[ship_type] = type_count.get(ship_type, 0) + 1

        print("\n按类型统计:")
        for ship_type, count in sorted(type_count.items(), key=lambda x: -x[1]):
            print(f"  {ship_type}: {count}")

    else:
        print("\n数据爬取失败，无法合并")

    elapsed = time.time() - start_time
    print(f"\n总耗时: {elapsed:.2f}秒")
    print("=" * 60)


if __name__ == "__main__":
    main()
