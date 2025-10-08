"""
抽奖物品数据爬取脚本
读取抽奖活动.csv中的抽奖活动
解析每个URL页面中的物品和概率数据
生成JSON格式文件，按活动id命名

支持类型：
- 筹码类：单个抽奖池，输出到 chip/ 目录
- 旗舰宝箱类：双抽奖池（普通宝箱+旗舰宝箱），输出到 flagship/ 目录
"""
import csv
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import re


# 路径配置
INPUT_FILE = Path(__file__).parent / "抽奖活动.csv"
OUTPUT_ROOT_DIR = Path(__file__).parent / "抽奖物品数据"
OUTPUT_CHIP_DIR = OUTPUT_ROOT_DIR / "chip"
OUTPUT_FLAGSHIP_DIR = OUTPUT_ROOT_DIR / "flagship"
CRAWLED_DATA_DIR = Path(__file__).parent / "爬取数据"
ACTIVITIES_DIR = Path(__file__).parent.parent / "MW解包有益资源" / "contentseparated_assets_activities"
CURRENCY_DIR = Path(__file__).parent.parent / "MW解包有益资源" / "contentseparated_assets_content" / "textures" / "sprites" / "currency"
BASE_URL = "https://mwstats.info"


# 物品数据库（从爬取数据CSV加载）
items_database = {}

# 普通物品名称到id的映射
COMMON_ITEM_ID_MAP = {
    # 货币类/资源
    '艺术硬币': 'Artstorm',
    '黄金': 'Hard',
    '美金': 'Soft',
    '筹码': 'currency_gachacoins',
    '1 天高级账户': 'v1_premium_1d',
    '旗舰钥匙': 'currency_premium_lootboxkey',
    '钥匙': 'currency_common_lootboxkey',
    '升级芯片': 'Upgrades',
    '修理包': 'RepairKit',

    # 高级道具
    '高级机载导弹诱饵': 'PremiumAircraftMissileDecoy',
    '高级弹药储备': 'PremiumAmmunitionReserve',
    '高级导弹诱饵': 'PremiumMissileDecoy',
    '高级修理包': 'PremiumRepairKit',
    '高级鱼雷诱饵': 'PremiumTorpedoDecoy',

    # 特殊道具
    '机载电子对抗': 'AirElectronicWarfare',
    '弹药储备': 'AmmunitionReserve',
    '电子对抗': 'ElectronicWarfare',
    '引擎过载': 'EngineBoost',
    '氧气储备': 'SubmarineOxygenReserve',
    '应急制氧': 'SubmarineOxygenReserve',
    '烟幕': 'TankSmokeBombs',
    '鱼雷诱饵': 'TorpedoDecoy',
}

# 资源类物品列表（用于判断类型）
RESOURCE_ITEMS = ['艺术硬币', '黄金', '美金', '筹码', '1 天高级账户', '旗舰钥匙', '钥匙', '升级芯片', '修理包']


def load_items_database():
    """从爬取数据目录加载所有物品信息"""
    global items_database

    print("  加载物品数据库...")

    # 需要加载的文件和对应的默认type
    files_to_load = []

    # 战舰
    ship_file = CRAWLED_DATA_DIR / '战舰.csv'
    if ship_file.exists():
        files_to_load.append((ship_file, '战舰'))

    # 无人舰艇
    uuv_file = CRAWLED_DATA_DIR / '无人舰艇.csv'
    if uuv_file.exists():
        files_to_load.append((uuv_file, '无人舰艇'))

    # 航空器文件夹全部CSV
    aircraft_dir = CRAWLED_DATA_DIR / '航空器'
    if aircraft_dir.exists():
        for csv_file in aircraft_dir.glob('*.csv'):
            files_to_load.append((csv_file, '航空器'))

    # 武器文件夹全部CSV
    weapons_dir = CRAWLED_DATA_DIR / '武器'
    if weapons_dir.exists():
        for csv_file in weapons_dir.glob('*.csv'):
            files_to_load.append((csv_file, '武器'))

    # 裝飾品/涂装
    camo_file = CRAWLED_DATA_DIR / '裝飾品' / '涂装.csv'
    if camo_file.exists():
        files_to_load.append((camo_file, '涂装'))

    # 裝飾品/头像
    avatar_file = CRAWLED_DATA_DIR / '裝飾品' / '头像.csv'
    if avatar_file.exists():
        files_to_load.append((avatar_file, '头像'))

    # 裝飾品/旗帜
    flag_file = CRAWLED_DATA_DIR / '裝飾品' / '旗帜.csv'
    if flag_file.exists():
        files_to_load.append((flag_file, '旗帜'))

    # 裝飾品/头衔
    title_file = CRAWLED_DATA_DIR / '裝飾品' / '头衔.csv'
    if title_file.exists():
        files_to_load.append((title_file, '头衔'))

    # 加载所有文件
    for csv_file, default_type in files_to_load:
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('name', '').strip()
                    if name:
                        # 获取typeString，如果没有则使用默认值
                        type_string = row.get('typeString', '').strip()
                        if not type_string:
                            type_string = default_type

                        # 使用name作为key（小写）
                        items_database[name.lower()] = {
                            'id': row.get('id', ''),
                            'name': name,
                            'nameEn': row.get('name_en', ''),
                            'rarityTypeString': row.get('rarityTypeString', ''),
                            'typeString': type_string,
                        }
        except Exception as e:
            print(f"    加载失败 {csv_file.name}: {e}")

    print(f"    加载了 {len(items_database)} 个物品")


def parse_probability(prob_str):
    """
    解析概率字符串为浮点数
    例如: "0.08% (1/1)" -> 0.08
          "8%" -> 8
    """
    if not prob_str:
        return 0.0

    # 提取百分比数字
    match = re.search(r'([0-9]+\.?[0-9]*)\s*%', prob_str)
    if match:
        percent = float(match.group(1))
        return percent

    return 0.0


def parse_limit(prob_str):
    """
    解析限制次数
    例如: "0.08% (1/1)" -> 1
          "8%" -> 0
    """
    if not prob_str:
        return 0

    # 提取 (x/y) 中的x
    match = re.search(r'\((\d+)/\d+\)', prob_str)
    if match:
        return int(match.group(1))

    return 0


def find_item_by_name(item_name):
    """
    通过物品名称在数据库中查找
    返回: 物品信息字典，如果找不到返回None
    """
    if not item_name:
        return None

    # 清理名称（去除前缀如[俄]、[美]等）
    clean_name = item_name.strip()

    # 直接查找
    item_info = items_database.get(clean_name.lower())
    if item_info:
        return item_info

    # 如果有国家前缀，尝试去除前缀再查找
    # 例如: [俄]22350M型 -> 22350M型
    match = re.match(r'\[.+?\](.+)', clean_name)
    if match:
        name_without_prefix = match.group(1).strip()
        item_info = items_database.get(name_without_prefix.lower())
        if item_info:
            return item_info

    return None


def normalize_rarity(rarity_str):
    """
    稀有度过滤器：将中文稀有度转换为英文
    """
    if not rarity_str:
        return "common"

    # 中文到英文映射
    rarity_map = {
        '传说': 'legendary',
        '史诗': 'epic',
        '稀有': 'rare',
        '普通': 'common',
    }

    # 检查是否包含中文稀有度
    for chinese, english in rarity_map.items():
        if chinese in rarity_str:
            return english

    # 如果已经是英文，转换为小写
    rarity_lower = rarity_str.lower()
    if rarity_lower in ['legendary', 'epic', 'rare', 'common']:
        return rarity_lower

    # 默认为common
    return "common"


def classify_rarity(type_str):
    """
    根据类型字符串判断稀有度
    """
    if not type_str:
        return "common"

    type_lower = type_str.lower()

    if '传说' in type_str or 'legendary' in type_lower:
        return "legendary"
    elif '史诗' in type_str or 'epic' in type_lower:
        return "epic"
    elif '稀有' in type_str or 'rare' in type_lower:
        return "rare"
    elif '普通' in type_str or 'common' in type_lower:
        return "common"

    # 默认为common
    return "common"


def classify_item_type(name, url, type_str):
    """
    判断物品类型
    """
    # 根据URL判断
    if '/ships/' in url:
        return "舰船"
    elif '/modules/' in url or '/weapons/' in url:
        return "武器"
    elif '/aircraft/' in url:
        return "飞机"
    elif '/camo/' in url:
        return "涂装"

    # 根据名称判断（无URL的资源类）
    if '硬币' in name or '黄金' in name or '筹码' in name:
        return "资源"
    elif '诱饵' in name or '探测器' in name or '账户' in name:
        return "道具"

    return "其它"


def fetch_gacha_data(url):
    """
    访问gacha URL，提取完整数据
    返回: (metadata, items_list)
    """
    if not url:
        return None, None

    try:
        # 添加语言参数
        if 'lang=' not in url:
            separator = '&' if '?' in url else '?'
            full_url = f"{url}{separator}lang=zh-hans"
        else:
            full_url = url

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

        response = requests.get(full_url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取metadata
        metadata = {}

        # 名称
        title_tag = soup.find('h1')
        if title_tag:
            metadata['name'] = title_tag.get_text(strip=True)

        # 查找<h2>抽奖货币</h2>区域，提取筹码图片
        currency_image_url = None
        for h2 in soup.find_all('h2'):
            if h2.get_text(strip=True) == '抽奖货币':
                container = h2.parent.parent
                currency_container = container.find_next_sibling()
                if currency_container:
                    # 查找图片标签
                    img_tag = currency_container.find('img')
                    if img_tag:
                        # 优先使用data-src，其次使用src
                        currency_image_url = img_tag.get('data-src') or img_tag.get('src')
                        if currency_image_url:
                            # 如果是相对路径，补全为完整URL
                            if currency_image_url.startswith('/'):
                                currency_image_url = BASE_URL + currency_image_url
                            # 提取原始URL（去除CDN参数）
                            # 例如: https://mwstats.info/cdn-cgi/image/width=300%2Cformat=auto%2Cquality=85/images/sprites-2024-transparent/currency_gachacoins_fw25.webp?v=63491759
                            # 转换为: https://mwstats.info/images/sprites-2024-transparent/currency_gachacoins_fw25.webp?v=63491759
                            currency_image_url = re.sub(r'/cdn-cgi/image/[^/]+/', '/', currency_image_url)
                            metadata['currency_gachacoins_image'] = currency_image_url
                break

        # 查找<h2>物品</h2>区域
        items_container = None
        for h2 in soup.find_all('h2'):
            if h2.get_text(strip=True) == '物品':
                container = h2.parent.parent
                items_container = container.find_next_sibling()
                break

        if not items_container:
            return metadata, []

        # 提取所有物品
        items = []
        modules = items_container.find_all('a', class_='battle-pass-module')

        for module in modules:
            item = {}

            # 物品链接
            href = module.get('href', '')
            if href.startswith('/'):
                item_url = BASE_URL + href
            else:
                item_url = href

            # 物品名称
            name_div = module.find('div', class_='battle-pass-module__text-primary')
            if name_div:
                item_name = name_div.get_text(strip=True)
            else:
                item_name = ''

            # 类型/稀有度信息
            type_span = module.find('span', class_='battle-pass-module__text-secondary-name')
            if type_span:
                type_str = type_span.get_text(strip=True)
            else:
                type_str = ''

            # 抽奖概率
            prob_span = module.find('span', class_='battle-pass-module__text-secondary-points')
            if prob_span:
                prob_str = prob_span.get_text(strip=True)
            else:
                prob_str = ''

            # 构建物品对象
            item['name'] = item_name
            item['probability'] = parse_probability(prob_str)
            item['limit'] = parse_limit(prob_str)

            # 先检查是否是普通物品（资源/道具）
            is_common_item = False
            for common_name, common_id in COMMON_ITEM_ID_MAP.items():
                if common_name in item_name:
                    item['id'] = common_id
                    # 判断是资源还是道具
                    if common_name in RESOURCE_ITEMS:
                        item['type'] = '资源'
                    else:
                        item['type'] = '道具'
                    item['rarity'] = 'common'
                    is_common_item = True
                    break

            if not is_common_item:
                # 不是普通物品，从数据库查找
                db_item = find_item_by_name(item_name)

                if db_item:
                    # 从数据库获取信息
                    item['id'] = db_item.get('id', '')
                    item['type'] = db_item.get('typeString', '')

                    # 涂装、头像、旗帜、头衔直接使用rarityTypeString，其他类型通过classify_rarity转换
                    rarity_type_string = db_item.get('rarityTypeString', '')
                    if item['type'] in ['涂装', '头像', '旗帜', '头衔']:
                        item['rarity'] = normalize_rarity(rarity_type_string)
                    else:
                        item['rarity'] = normalize_rarity(classify_rarity(rarity_type_string))

                    # 添加nameEn（如果有）
                    name_en = db_item.get('nameEn', '')
                    if name_en:
                        item['nameEn'] = name_en

                    # 如果是舰船/武器，尝试添加tier
                    if item['type'] in ['舰船', '武器', '飞机']:
                        item['tier'] = 3  # 默认3，可以从数据库扩展
                else:
                    # 数据库中也找不到，使用备用方案
                    item['id'] = ''
                    item['type'] = classify_item_type(item_name, item_url, type_str)
                    item['rarity'] = normalize_rarity(classify_rarity(type_str))

            items.append(item)

        return metadata, items

    except Exception as e:
        print(f"    获取失败: {e}")
        return None, None


def save_gacha_json(gacha_id, gacha_type, metadata, items):
    """保存抽奖数据为JSON"""
    if not items:
        return False

    output_file = OUTPUT_CHIP_DIR / f"{gacha_id}.json"

    data = {
        "id": gacha_id,
        "gacha_type": gacha_type,
        "metadata": metadata,
        "items": items
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"    保存: {output_file.name} ({len(items)} 个物品)")
    return True


def save_flagship_json(gacha_id, gacha_type, metadata, lootboxes):
    """保存旗舰宝箱类数据为JSON"""
    if not lootboxes:
        return False

    output_file = OUTPUT_FLAGSHIP_DIR / f"{gacha_id}.json"

    data = {
        "id": gacha_id,
        "gacha_type": gacha_type,
        "metadata": metadata,
        "lootboxes": lootboxes
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_items = sum(len(lb.get('items', [])) for lb in lootboxes)
    print(f"    保存: {output_file.name} ({len(lootboxes)} 个宝箱, {total_items} 个物品)")
    return True


def parse_date_for_sorting(formatted_date):
    """
    解析日期字符串用于排序
    例如: "2024年10月" -> (2024, 10)
    返回元组用于排序，越新的日期排序值越大
    """
    if not formatted_date:
        return (0, 0)

    # 提取年份和月份
    year_match = re.search(r'(\d{4})', formatted_date)
    month_match = re.search(r'(\d{1,2})月', formatted_date)

    year = int(year_match.group(1)) if year_match else 0
    month = int(month_match.group(1)) if month_match else 0

    return (year, month)


def check_activity_gacha_exists(gacha_id):
    """
    检查activity_gacha资源文件是否存在
    返回: True如果存在background或widget文件，否则False
    """
    if not ACTIVITIES_DIR.exists():
        return False

    # 检查是否存在background或widget文件
    background_file = ACTIVITIES_DIR / f"activity_gacha_{gacha_id}_background.png"
    widget_file = ACTIVITIES_DIR / f"activity_gacha_{gacha_id}_widget.png"

    return background_file.exists() or widget_file.exists()


def check_currency_gachacoins_exists(gacha_id):
    """
    检查currency_gachacoins资源文件是否存在
    返回: True如果存在，否则False
    """
    if not CURRENCY_DIR.exists():
        return False

    # 检查是否存在currency_gachacoins文件
    currency_file = CURRENCY_DIR / f"currency_gachacoins_{gacha_id}.png"

    return currency_file.exists()


def check_lootbox_activity_exists(gacha_id):
    """
    检查lootbox_activity资源文件是否存在
    返回: True如果存在widget文件，否则False
    """
    if not ACTIVITIES_DIR.exists():
        return False

    # 检查是否存在widget文件
    widget_file = ACTIVITIES_DIR / f"lootbox_activity_{gacha_id}_widget.png"

    return widget_file.exists()


def generate_index_json(activities_info):
    """
    生成统一的index.json索引文件（包含所有类型的活动）
    支持增量更新，按日期排序
    activities_info: 新爬取的活动信息列表（筹码类 + 旗舰宝箱类混合）
    """
    output_file = OUTPUT_ROOT_DIR / "index.json"

    # 读取现有的index.json
    existing_activities = []
    if output_file.exists():
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_activities = existing_data.get('activities', [])
                print(f"  读取现有索引: {len(existing_activities)} 个活动")
        except Exception as e:
            print(f"  读取现有索引失败: {e}")

    # 创建现有活动id到活动对象的映射
    existing_dict = {act.get('id'): act for act in existing_activities}

    # 合并逻辑：对新爬取的每个活动
    updated_count = 0
    new_count = 0

    for new_act in activities_info:
        act_id = new_act.get('id')
        if act_id in existing_dict:
            # 已存在：合并字段（保留旧字段，更新/添加新字段）
            existing_dict[act_id].update(new_act)
            updated_count += 1
        else:
            # 不存在：添加新活动
            existing_dict[act_id] = new_act
            new_count += 1

    if new_count > 0:
        print(f"  新增 {new_count} 个活动")
    if updated_count > 0:
        print(f"  更新 {updated_count} 个活动")
    if new_count == 0 and updated_count == 0:
        print(f"  没有新活动或更新")

    # 转回列表
    all_activities = list(existing_dict.values())

    # 按日期排序（从新到旧）
    sorted_activities = sorted(
        all_activities,
        key=lambda x: parse_date_for_sorting(x.get('formattedDate', '')),
        reverse=True
    )

    index_data = {
        "activities": sorted_activities
    }

    # 保存到根目录
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"\n生成索引: {output_file.name} (总计 {len(sorted_activities)} 个活动)")
    print(f"位置: {output_file}")
    return True


def process_gacha(row):
    """
    处理单个抽奖活动
    返回: (success, activity_info)
    """
    gacha_id = row.get('id', '').strip()
    name = row.get('name', '未知')
    name_en = row.get('name_en', '')
    gacha_type = row.get('gacha_type', '').strip()
    gacha_1_url = row.get('gacha_1_url', '').strip()
    formatted_date = row.get('formattedDate', '')
    image_data = row.get('image', '')

    if not gacha_id or not gacha_1_url:
        return False, None

    print(f"  [{name}] ({gacha_id})")

    metadata, items = fetch_gacha_data(gacha_1_url)

    if metadata is None or items is None:
        print(f"    失败")
        return False, None

    if not items:
        print(f"    无物品数据")
        return False, None

    # 补充metadata中的字段
    if name_en:
        metadata['nameEn'] = name_en

    # 填充formattedDate
    if formatted_date:
        metadata['formattedDate'] = formatted_date

    # 检查是否存在activity_gacha资源，如果不存在则添加image数据
    if not check_activity_gacha_exists(gacha_id) and image_data:
        try:
            # image_data是字符串形式的字典，需要解析
            import ast
            image_dict = ast.literal_eval(image_data)
            # 只保留default URL，精简数据
            if 'default' in image_dict:
                metadata['image'] = image_dict['default']
                print(f"    [无activity_gacha资源] 添加image URL")
        except:
            # 解析失败则忽略
            pass

    # 检查是否存在currency_gachacoins资源，如果存在则删除metadata中的currency_gachacoins_image
    if check_currency_gachacoins_exists(gacha_id):
        # 本地有资源，删除URL字段（如果存在）
        if 'currency_gachacoins_image' in metadata:
            del metadata['currency_gachacoins_image']
    else:
        # 本地没有资源，保留URL字段（如果fetch_gacha_data已经提取到）
        if 'currency_gachacoins_image' in metadata:
            print(f"    [无currency_gachacoins资源] 保留currency_gachacoins_image URL")

    # 保存JSON
    success = save_gacha_json(gacha_id, gacha_type, metadata, items)

    if success:
        # 返回活动信息用于index.json
        activity_info = {
            'id': gacha_id,
            'gacha_type': gacha_type,
            'name': metadata.get('name', name),
            'formattedDate': formatted_date
        }
        if name_en:
            activity_info['nameEn'] = name_en

        # 如果metadata中有image，也添加到index中
        if 'image' in metadata:
            activity_info['image'] = metadata['image']

        # 如果metadata中有currency_gachacoins_image，也添加到index中
        if 'currency_gachacoins_image' in metadata:
            activity_info['currency_gachacoins_image'] = metadata['currency_gachacoins_image']

        return True, activity_info
    else:
        return False, None


def process_flagship_gacha(row):
    """
    处理单个旗舰宝箱类活动
    返回: (success, activity_info)
    """
    gacha_id = row.get('id', '').strip()
    name = row.get('name', '未知')
    name_en = row.get('name_en', '')
    gacha_type = row.get('gacha_type', '').strip()
    gacha_1_url = row.get('gacha_1_url', '').strip()  # 普通宝箱
    gacha_2_url = row.get('gacha_2_url', '').strip()  # 旗舰宝箱
    formatted_date = row.get('formattedDate', '')
    image_data = row.get('image', '')

    if not gacha_id or not gacha_1_url or not gacha_2_url:
        return False, None

    print(f"  [{name}] ({gacha_id})")

    # 爬取两个宝箱的数据
    container_metadata, container_items = fetch_gacha_data(gacha_1_url)
    flagship_metadata, flagship_items = fetch_gacha_data(gacha_2_url)

    if container_metadata is None or flagship_metadata is None:
        print(f"    失败")
        return False, None

    if not container_items and not flagship_items:
        print(f"    无物品数据")
        return False, None

    # 构建全局metadata
    metadata = {
        'name': name,
        'formattedDate': formatted_date
    }
    if name_en:
        metadata['nameEn'] = name_en

    # 检查是否存在lootbox_activity资源，如果不存在则添加image数据
    if not check_lootbox_activity_exists(gacha_id) and image_data:
        try:
            import ast
            image_dict = ast.literal_eval(image_data)
            if 'default' in image_dict:
                metadata['image'] = image_dict['default']
                print(f"    [无lootbox_activity资源] 添加image URL")
        except:
            pass

    # 构建lootboxes列表
    lootboxes = []

    # 普通宝箱
    if container_items:
        lootboxes.append({
            'type': 'container',
            'metadata': container_metadata,
            'items': container_items
        })

    # 旗舰宝箱
    if flagship_items:
        lootboxes.append({
            'type': 'flagship',
            'metadata': flagship_metadata,
            'items': flagship_items
        })

    # 保存JSON
    success = save_flagship_json(gacha_id, gacha_type, metadata, lootboxes)

    if success:
        # 返回活动信息用于index.json
        activity_info = {
            'id': gacha_id,
            'gacha_type': gacha_type,
            'name': name,
            'formattedDate': formatted_date
        }
        if name_en:
            activity_info['nameEn'] = name_en
        if 'image' in metadata:
            activity_info['image'] = metadata['image']

        return True, activity_info
    else:
        return False, None


def main():
    """主函数"""
    print("=" * 70)
    print("抽奖物品数据爬取脚本")
    print("=" * 70)

    # 检查输入文件
    if not INPUT_FILE.exists():
        print(f"\n错误: 找不到输入文件")
        print(f"路径: {INPUT_FILE}")
        print("\n请先运行 3活动数据加工.py 生成抽奖活动数据")
        return

    # 创建输出目录
    OUTPUT_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_CHIP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FLAGSHIP_DIR.mkdir(parents=True, exist_ok=True)

    # 加载物品数据库
    print(f"\n准备数据...")
    load_items_database()

    # 读取抽奖活动数据
    print(f"\n读取抽奖活动数据...")
    print(f"输入: {INPUT_FILE}")

    chip_gachas = []
    flagship_gachas = []

    with open(INPUT_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            gacha_type = row.get('gacha_type', '').strip()
            if gacha_type == '筹码类':
                chip_gachas.append(row)
            elif gacha_type == '旗舰宝箱类':
                flagship_gachas.append(row)

    print(f"  找到 {len(chip_gachas)} 个筹码类抽奖")
    print(f"  找到 {len(flagship_gachas)} 个旗舰宝箱类抽奖")

    # 收集所有活动信息（用于最后生成统一的index.json）
    all_activities_info = []

    # ==================== 处理筹码类 ====================
    if chip_gachas:
        print(f"\n{'=' * 70}")
        print("开始处理筹码类...")
        print("=" * 70)

        success_count = 0

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(process_gacha, row): row
                for row in chip_gachas
            }

            for future in as_completed(futures):
                row = futures[future]
                try:
                    success, activity_info = future.result()
                    if success:
                        success_count += 1
                        if activity_info:
                            all_activities_info.append(activity_info)
                except Exception as e:
                    print(f"  [{row.get('name', '未知')}] 错误: {e}")

        print("\n" + "=" * 70)
        print("筹码类爬取完成!")
        print("=" * 70)
        print(f"成功: {success_count}/{len(chip_gachas)}")
        print(f"保存位置: {OUTPUT_CHIP_DIR}")
        print("=" * 70)

    # ==================== 处理旗舰宝箱类 ====================
    if flagship_gachas:
        print(f"\n{'=' * 70}")
        print("开始处理旗舰宝箱类...")
        print("=" * 70)

        success_count = 0

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(process_flagship_gacha, row): row
                for row in flagship_gachas
            }

            for future in as_completed(futures):
                row = futures[future]
                try:
                    success, activity_info = future.result()
                    if success:
                        success_count += 1
                        if activity_info:
                            all_activities_info.append(activity_info)
                except Exception as e:
                    print(f"  [{row.get('name', '未知')}] 错误: {e}")

        print("\n" + "=" * 70)
        print("旗舰宝箱类爬取完成!")
        print("=" * 70)
        print(f"成功: {success_count}/{len(flagship_gachas)}")
        print(f"保存位置: {OUTPUT_FLAGSHIP_DIR}")
        print("=" * 70)

    # ==================== 生成统一的index.json ====================
    if all_activities_info:
        print(f"\n生成统一索引文件...")
        generate_index_json(all_activities_info)
    elif not chip_gachas and not flagship_gachas:
        print("\n没有需要处理的抽奖活动")

    print("\n" + "=" * 70)



if __name__ == "__main__":
    main()
