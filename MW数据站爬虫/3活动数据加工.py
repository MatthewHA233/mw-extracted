"""
活动数据加工脚本
处理活动.csv，过滤并生成抽奖活动.csv
对于typeString="活动"的数据，访问URL提取抽奖信息
"""
import csv
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


# 路径配置
INPUT_FILE = Path(__file__).parent / "爬取数据" / "活动.csv"
OUTPUT_FILE = Path(__file__).parent / "抽奖活动.csv"
BASE_URL = "https://mwstats.info"


def load_activities(input_file):
    """读取活动CSV文件"""
    activities = []

    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            activities.append(row)

    return activities, reader.fieldnames


def fetch_gacha_info(url):
    """
    访问活动URL，提取抽奖信息
    返回: (gacha_type, gacha_1_url, gacha_2_url)
    """
    if not url:
        return None, None, None

    try:
        # 构建完整URL
        if url.startswith('/'):
            full_url = BASE_URL + url
        else:
            full_url = url

        # 添加中文语言参数
        if 'lang=' not in full_url:
            separator = '&' if '?' in full_url else '?'
            full_url = f"{full_url}{separator}lang=zh-hans"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        response = requests.get(full_url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找<h2>抽奖</h2>或<h2>战利品箱</h2>区域
        gacha_section = None
        for h2 in soup.find_all('h2'):
            h2_text = h2.get_text(strip=True)
            if h2_text in ['抽奖', '战利品箱']:
                # 向上查找包含gacha/lootboxes链接的容器
                container = h2.parent
                while container and container.parent and container.parent.name != 'body':
                    container = container.parent
                    # 检查是否包含gacha或lootboxes链接
                    if container.find('a', href=lambda x: x and ('/gacha/' in x or '/lootboxes/' in x)):
                        gacha_section = container
                        break
                break

        if not gacha_section:
            return None, None, None

        # 提取所有gacha/lootboxes链接和名称
        gacha_links = []
        gacha_names = []

        # 查找所有gacha/lootboxes卡片
        for link in gacha_section.find_all('a', href=True):
            href = link['href']
            if '/gacha/' in href or '/lootboxes/' in href:
                # 提取gacha名称
                name_tag = link.find('h2')
                if name_tag:
                    name = name_tag.get_text(strip=True)
                    gacha_names.append(name)

                    # 构建完整URL
                    if href.startswith('/'):
                        gacha_url = BASE_URL + href
                    else:
                        gacha_url = href
                    gacha_links.append(gacha_url)

        # 抽奖类型：取最后一个gacha的名称 + "类"
        gacha_type = None
        if gacha_names:
            gacha_type = f"{gacha_names[-1]}类"

        # 填充URL字段
        gacha_1_url = gacha_links[0] if len(gacha_links) > 0 else None
        gacha_2_url = gacha_links[1] if len(gacha_links) > 1 else None

        return gacha_type, gacha_1_url, gacha_2_url

    except Exception as e:
        print(f"    获取失败 ({url}): {e}")
        return None, None, None


def enrich_event_activities(activities):
    """
    对typeString为"活动"的数据，并行访问URL获取抽奖信息
    对typeString为"抽奖"的数据，直接填充gacha_1_url
    """
    # 处理typeString为"抽奖"的数据
    gacha_activities = [a for a in activities if a.get('typeString') == '抽奖']
    for activity in gacha_activities:
        activity['gacha_1_url'] = activity.get('url', '')
        activity['gacha_type'] = ''
        activity['gacha_2_url'] = ''

    if gacha_activities:
        print(f"  找到 {len(gacha_activities)} 个抽奖，直接填充gacha_1_url")

    # 处理typeString为"活动"的数据
    event_activities = [a for a in activities if a.get('typeString') == '活动']

    if not event_activities:
        print("  没有需要访问的活动数据")
        return

    print(f"  找到 {len(event_activities)} 个活动，开始并行访问URL...")

    # 并行获取gacha信息
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_gacha_info, activity.get('url', '')): activity
            for activity in event_activities
        }

        completed = 0
        for future in as_completed(futures):
            activity = futures[future]
            completed += 1

            try:
                gacha_type, gacha_1_url, gacha_2_url = future.result()

                # 添加新字段
                activity['gacha_type'] = gacha_type or ''
                activity['gacha_1_url'] = gacha_1_url or ''
                activity['gacha_2_url'] = gacha_2_url or ''

                if gacha_type:
                    print(f"  [{completed}/{len(event_activities)}] {activity.get('name', '未知')} -> {gacha_type}")
                else:
                    print(f"  [{completed}/{len(event_activities)}] {activity.get('name', '未知')} -> 无抽奖")

            except Exception as e:
                print(f"  [{completed}/{len(event_activities)}] {activity.get('name', '未知')} -> 错误: {e}")
                activity['gacha_type'] = ''
                activity['gacha_1_url'] = ''
                activity['gacha_2_url'] = ''

    print("  URL访问完成")


def fetch_gacha_currency_type(gacha_url):
    """
    访问gacha URL，从"抽奖货币"容器获取真实的gacha_type
    返回: gacha_type (如"筹码类"、"其它类")
    """
    if not gacha_url:
        return "其它类"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        response = requests.get(gacha_url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找<h2>抽奖货币</h2>区域
        for h2 in soup.find_all('h2'):
            if h2.get_text(strip=True) == '抽奖货币':
                # 查找battle-pass-module__text-primary（货币名称在这里）
                # 从h2往上找到外层容器，然后找所有的battle-pass-module__text-primary
                container = h2.parent
                for _ in range(5):  # 最多向上找5层
                    if container and container.parent:
                        container = container.parent
                    else:
                        break

                # 在容器中查找货币名称
                currency_div = container.find('div', class_='battle-pass-module__text-primary')
                if currency_div:
                    currency_name = currency_div.get_text(strip=True)
                    if currency_name:
                        return f"{currency_name}类"
                break

        return "其它类"

    except Exception as e:
        print(f"    获取gacha货币类型失败 ({gacha_url}): {e}")
        return "其它类"


def refine_special_gacha_types(activities):
    """
    对特殊的gacha进行二次访问，获取真实的gacha_type
    处理对象：
    1. typeString为"抽奖"的所有数据
    2. typeString为"活动"且gacha_type == name + "类"的数据
    """
    # 找出需要处理的活动
    special_activities = []

    for activity in activities:
        type_string = activity.get('typeString', '')
        gacha_type = activity.get('gacha_type', '')
        name = activity.get('name', '')

        # typeString为"抽奖"，或者是特殊的活动gacha
        if type_string == '抽奖' or (type_string == '活动' and gacha_type == f"{name}类"):
            special_activities.append(activity)

    if not special_activities:
        print("  没有需要二次访问的gacha数据")
        return

    print(f"  找到 {len(special_activities)} 个特殊gacha，开始并行访问获取真实类型...")

    # 并行获取gacha货币类型
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_gacha_currency_type, activity.get('gacha_1_url', '')): activity
            for activity in special_activities
        }

        completed = 0
        for future in as_completed(futures):
            activity = futures[future]
            completed += 1

            try:
                real_gacha_type = future.result()
                activity['gacha_type'] = real_gacha_type
                print(f"  [{completed}/{len(special_activities)}] {activity.get('name', '未知')} -> {real_gacha_type}")

            except Exception as e:
                print(f"  [{completed}/{len(special_activities)}] {activity.get('name', '未知')} -> 错误: {e}")
                activity['gacha_type'] = '其它类'

    print("  gacha类型获取完成")


def filter_activities(activities):
    """
    过滤活动数据
    剔除：
    1. name 为 "金色狩猎"
    2. typeString 为 "社区目标"
    """
    filtered = []

    removed_count = {
        '金色狩猎': 0,
        '社区目标': 0
    }

    for activity in activities:
        name = activity.get('name', '')
        name_en = activity.get('name_en', '')
        type_string = activity.get('typeString', '')

        # 检查是否需要剔除
        should_remove = False
        remove_reason = None

        # 剔除name为"金色狩猎"（中英文都检查）
        if name == '金色狩猎' or name_en == 'Golden Hunt':
            should_remove = True
            remove_reason = '金色狩猎'

        # 剔除typeString为"社区目标"
        elif type_string == '社区目标':
            should_remove = True
            remove_reason = '社区目标'

        if should_remove:
            removed_count[remove_reason] += 1
        else:
            filtered.append(activity)

    return filtered, removed_count


def filter_gacha_activities(activities):
    """
    过滤gacha_type不符合条件的数据行
    规则：
    1. 保留 typeString 为 "抽奖" 的所有数据
    2. 对于其他数据，删除 gacha_type 为空的（无抽奖活动）
    3. 保留 gacha_type 为 "旗舰宝箱类"、"机密货物类"、"无人机补给类" 的所有数据
    4. 对于其他 gacha_type，只保留 gacha_type == name + "类" 的数据
    """
    filtered = []
    removed_no_gacha = 0
    removed_mismatch = 0

    # 白名单gacha类型
    whitelist_types = ['旗舰宝箱类', '机密货物类', '无人机补给类']

    for activity in activities:
        gacha_type = activity.get('gacha_type', '')
        name = activity.get('name', '')
        type_string = activity.get('typeString', '')

        # typeString为"抽奖"，直接保留
        if type_string == '抽奖':
            filtered.append(activity)
            continue

        # gacha_type为空，删除
        if not gacha_type:
            removed_no_gacha += 1
            continue

        # gacha_type在白名单中，保留
        if gacha_type in whitelist_types:
            filtered.append(activity)
            continue

        # 其他类型，检查是否等同于name
        expected_type = f"{name}类"
        if gacha_type == expected_type:
            filtered.append(activity)
        else:
            removed_mismatch += 1
            print(f"  剔除: {name} (gacha_type={gacha_type} != {expected_type})")

    if removed_no_gacha > 0:
        print(f"  剔除无抽奖活动: {removed_no_gacha} 条")
    if removed_mismatch > 0:
        print(f"  剔除gacha不匹配: {removed_mismatch} 条")

    return filtered


def clean_activity_id(activity_id):
    """
    清理活动ID
    1. 转换为小写
    2. 删除 "activity_gacha_" 前缀
    3. 删除 "gacha_c_" 前缀
    """
    if not activity_id:
        return activity_id

    # 转换为小写
    cleaned_id = activity_id.lower()

    # 删除前缀
    if cleaned_id.startswith('activity_gacha_'):
        cleaned_id = cleaned_id.replace('activity_gacha_', '', 1)
    elif cleaned_id.startswith('gacha_c_'):
        cleaned_id = cleaned_id.replace('gacha_c_', '', 1)

    return cleaned_id


def save_activities(activities, fieldnames, output_file):
    """保存活动数据到CSV，确保新字段插入到url之后"""
    # 清理所有活动的ID
    for activity in activities:
        if 'id' in activity:
            activity['id'] = clean_activity_id(activity['id'])

    # 重新排列字段顺序，将gacha相关字段插入到url之后
    new_fieldnames = []
    gacha_fields = ['gacha_type', 'gacha_1_url', 'gacha_2_url']

    for field in fieldnames:
        new_fieldnames.append(field)
        if field == 'url':
            # 在url之后插入gacha字段
            for gacha_field in gacha_fields:
                if gacha_field not in fieldnames:
                    new_fieldnames.append(gacha_field)

    # 添加任何遗漏的gacha字段（如果url不存在）
    for gacha_field in gacha_fields:
        if gacha_field not in new_fieldnames:
            new_fieldnames.append(gacha_field)

    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(activities)


def main():
    """主函数"""
    print("=" * 70)
    print("活动数据加工脚本")
    print("=" * 70)

    # 检查输入文件
    if not INPUT_FILE.exists():
        print(f"\n错误: 找不到活动数据文件")
        print(f"路径: {INPUT_FILE}")
        print("\n请先运行 2批量数据中英文名爬取.py 生成活动数据")
        return

    # 读取活动数据
    print(f"\n读取活动数据...")
    print(f"输入: {INPUT_FILE}")

    activities, fieldnames = load_activities(INPUT_FILE)
    print(f"  读取 {len(activities)} 条活动数据")

    # 过滤数据
    print(f"\n过滤数据...")
    print(f"  剔除规则:")
    print(f"    1. name = '金色狩猎'")
    print(f"    2. typeString = '社区目标'")

    filtered_activities, removed_count = filter_activities(activities)

    print(f"\n过滤结果:")
    for reason, count in removed_count.items():
        if count > 0:
            print(f"  - 剔除 '{reason}': {count} 条")

    print(f"\n保留: {len(filtered_activities)} 条")
    print(f"剔除: {sum(removed_count.values())} 条")

    # 访问活动URL，提取抽奖信息
    print(f"\n访问活动URL，提取抽奖信息...")
    enrich_event_activities(filtered_activities)

    # 过滤gacha_type不符合条件的数据
    print(f"\n过滤gacha_type数据...")
    filtered_activities = filter_gacha_activities(filtered_activities)
    print(f"  过滤后保留: {len(filtered_activities)} 条")

    # 对特殊gacha进行二次访问，获取真实类型
    print(f"\n获取特殊gacha的真实类型...")
    refine_special_gacha_types(filtered_activities)

    print(f"  最终保留: {len(filtered_activities)} 条")

    # 保存结果
    print(f"\n保存结果...")
    print(f"输出: {OUTPUT_FILE}")

    save_activities(filtered_activities, fieldnames, OUTPUT_FILE)

    print(f"\n处理完成!")
    print("=" * 70)

    # 显示统计信息
    if filtered_activities:
        print(f"\n抽奖活动统计:")
        print(f"  总数: {len(filtered_activities)} 个")

        # 按类型统计
        type_count = {}
        for activity in filtered_activities:
            type_str = activity.get('typeString', '未知')
            type_count[type_str] = type_count.get(type_str, 0) + 1

        print(f"\n按活动类型统计:")
        for type_str, count in sorted(type_count.items(), key=lambda x: -x[1]):
            print(f"  {type_str}: {count}")

        # 按抽奖类型统计
        gacha_type_count = {}
        for activity in filtered_activities:
            gacha_type = activity.get('gacha_type', '') or '无抽奖'
            gacha_type_count[gacha_type] = gacha_type_count.get(gacha_type, 0) + 1

        print(f"\n按抽奖类型统计:")
        for gacha_type, count in sorted(gacha_type_count.items(), key=lambda x: -x[1]):
            print(f"  {gacha_type}: {count}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
