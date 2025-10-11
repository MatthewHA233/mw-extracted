"""
验证并更新抽奖物品JSON中的物品信息
使用爬取数据库中的准确信息更新id、type、rarity等字段
保留probability和limit字段（这些字段来自网站，是可信的）
"""
import csv
import json
import re
from pathlib import Path

# 路径配置
CHIP_DIR = Path(__file__).parent / "抽奖物品数据" / "chip"
CRAWLED_DATA_DIR = Path(__file__).parent / "爬取数据"

# 物品数据库
items_database = {}

# 普通物品名称到id的映射
COMMON_ITEM_ID_MAP = {
    # 货币类/资源
    '艺术硬币': 'Artstorm',
    '黄金': 'Hard',
    '筹码': 'currency',
    '1 天高级账户': 'v1_premium_1d',

    # 高级战斗增益
    '高级机载导弹诱饵': 'PremiumAircraftMissileDecoy',
    '高级弹药储备': 'PremiumAmmunitionReserve',
    '高级导弹诱饵': 'PremiumMissileDecoy',
    '高级修理包': 'PremiumRepairKit',
    '高级鱼雷诱饵': 'PremiumTorpedoDecoy',

    # 特殊战斗增益
    '机载电子对抗': 'AirElectronicWarfare',
    '弹药储备': 'AmmunitionReserve',
    '电子对抗': 'ElectronicWarfare',
    '引擎过载': 'EngineBoost',
    '氧气储备': 'SubmarineOxygenReserve',
    '应急制氧': 'SubmarineOxygenReserve',
    '烟幕': 'TankSmokeBombs',
    '鱼雷诱饵': 'TorpedoDecoy',
}


def load_items_database():
    """从爬取数据目录加载所有物品信息"""
    global items_database

    print("加载物品数据库...")

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

    # 加载所有文件
    for csv_file, default_type in files_to_load:
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('name', '').strip()
                    if name:
                        type_string = row.get('typeString', '').strip()
                        if not type_string:
                            type_string = default_type

                        items_database[name.lower()] = {
                            'id': row.get('id', ''),
                            'name': name,
                            'nameEn': row.get('name_en', ''),
                            'rarityTypeString': row.get('rarityTypeString', ''),
                            'typeString': type_string,
                        }
        except Exception as e:
            print(f"  加载失败 {csv_file.name}: {e}")

    print(f"  加载了 {len(items_database)} 个物品\n")


def find_item_by_name(item_name):
    """通过物品名称在数据库中查找"""
    if not item_name:
        return None

    clean_name = item_name.strip()

    # 直接查找
    item_info = items_database.get(clean_name.lower())
    if item_info:
        return item_info

    # 如果有国家前缀，尝试去除前缀再查找
    match = re.match(r'\[.+?\](.+)', clean_name)
    if match:
        name_without_prefix = match.group(1).strip()
        item_info = items_database.get(name_without_prefix.lower())
        if item_info:
            return item_info

    return None


def normalize_rarity(rarity_str):
    """将中文稀有度转换为英文"""
    if not rarity_str:
        return "common"

    rarity_map = {
        '传说': 'legendary',
        '史诗': 'epic',
        '稀有': 'rare',
        '普通': 'common',
    }

    for chinese, english in rarity_map.items():
        if chinese in rarity_str:
            return english

    rarity_lower = rarity_str.lower()
    if rarity_lower in ['legendary', 'epic', 'rare', 'common']:
        return rarity_lower

    return "common"


def classify_rarity(type_str):
    """根据类型字符串判断稀有度"""
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

    return "common"


def update_item_info(item):
    """
    更新物品信息
    保留: probability, limit
    更新: id, type, rarity, tier, nameEn
    """
    item_name = item.get('name', '')

    # 保留原始的probability和limit
    probability = item.get('probability')
    limit = item.get('limit')

    # 检查是否是普通物品（资源/战斗增益）
    is_common_item = False
    for common_name, common_id in COMMON_ITEM_ID_MAP.items():
        if common_name in item_name:
            item['id'] = common_id
            if common_name in ['艺术硬币', '黄金', '筹码', '1 天高级账户']:
                item['type'] = '资源'
            else:
                item['type'] = '战斗增益'
            item['rarity'] = 'common'
            is_common_item = True
            break

    if not is_common_item:
        # 从数据库查找
        db_item = find_item_by_name(item_name)

        if db_item:
            # 从数据库获取信息
            item['id'] = db_item.get('id', '')
            item['type'] = db_item.get('typeString', '')

            # 涂装直接使用rarityTypeString，其他类型通过classify_rarity转换
            rarity_type_string = db_item.get('rarityTypeString', '')
            if item['type'] == '涂装':
                item['rarity'] = normalize_rarity(rarity_type_string)
            else:
                item['rarity'] = normalize_rarity(classify_rarity(rarity_type_string))

            # 添加nameEn（如果有）
            name_en = db_item.get('nameEn', '')
            if name_en:
                item['nameEn'] = name_en

            # 如果是舰船/武器/飞机，添加tier（默认3）
            if item['type'] in ['战舰', '武器', '航空器']:
                if 'tier' not in item:
                    item['tier'] = 3

            return True, "已更新（数据库）"
        else:
            return False, f"未在数据库找到: {item_name}"

    return True, "已更新（普通物品）"


def process_gacha_file(json_file):
    """处理单个抽奖JSON文件"""
    print(f"处理: {json_file.name}")

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        items = data.get('items', [])
        updated_count = 0
        failed_items = []

        for item in items:
            success, message = update_item_info(item)
            if success:
                updated_count += 1
            else:
                failed_items.append(message)

        # 保存更新后的文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  ✓ 更新 {updated_count}/{len(items)} 个物品")
        if failed_items:
            for msg in failed_items:
                print(f"  ✗ {msg}")

        return True

    except Exception as e:
        print(f"  ✗ 处理失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("验证并更新抽奖物品数据")
    print("=" * 70)

    if not CHIP_DIR.exists():
        print(f"\n错误: 找不到chip目录")
        print(f"路径: {CHIP_DIR}")
        return

    # 加载物品数据库
    load_items_database()

    # 查找所有JSON文件
    json_files = list(CHIP_DIR.glob("*.json"))

    # 排除index.json
    json_files = [f for f in json_files if f.name != 'index.json']

    if not json_files:
        print("\n未找到抽奖JSON文件")
        return

    print(f"找到 {len(json_files)} 个抽奖文件\n")
    print("=" * 70)

    # 处理每个文件
    success_count = 0
    for json_file in json_files:
        if process_gacha_file(json_file):
            success_count += 1
        print()

    print("=" * 70)
    print(f"处理完成: {success_count}/{len(json_files)} 个文件")
    print("=" * 70)


if __name__ == "__main__":
    main()
