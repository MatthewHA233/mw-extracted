"""
数据资源比对工具
用于查看CSV数据与PNG图片资源的对应关系
"""

import os
import csv
import json
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, send_from_directory

app = Flask(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "MW数据站爬虫" / "爬取数据"
IMAGE_DIR = BASE_DIR / "MW解包有益资源" / "contentseparated_assets_content" / "textures" / "sprites"
NEW_DATA_CONFIG_FILE = BASE_DIR / "新数据管理.json"
ITEM_TYPE_MAPPING_FILE = BASE_DIR / "物品类型映射.json"

# 分类与图片目录映射
CATEGORY_IMAGE_MAP = {
    "战舰": "units_ships",
    "无人舰艇": "units_ships",
    "武器": "weapons",
    "主炮": "weapons",
    "导弹": "weapons",
    "火箭炮": "weapons",
    "自卫炮": "weapons",
    "防空设备": "weapons",
    "鱼雷发射器": "weapons",
    "鱼雷": "weapons",
    "航空器": "weapons",
    "战斗机": "weapons",
    "攻击机": "weapons",
    "无人机": "weapons",
    "直升机": "weapons",
    "轰炸机": "weapons",
    "头像": "avataricons",
    "旗帜": "flags",
    "头衔": "titles",
    "涂装": "camouflages",
    "皮肤": "camouflages",
    "资源": "currency",
    "道具": "currency",
}

def load_item_type_mappings():
    """从JSON文件加载物品类型映射"""
    if not ITEM_TYPE_MAPPING_FILE.exists():
        print(f"警告: 找不到物品类型映射文件: {ITEM_TYPE_MAPPING_FILE}")
        return {"common_items": [], "category_mappings": {}}

    try:
        with open(ITEM_TYPE_MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading item type mappings: {e}")
        return {"common_items": [], "category_mappings": {}}

def load_new_data_config():
    """加载新数据管理配置"""
    if not NEW_DATA_CONFIG_FILE.exists():
        return {"excluded_items": [], "recorded_items": []}

    try:
        with open(NEW_DATA_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading new data config: {e}")
        return {"excluded_items": [], "recorded_items": []}

def save_new_data_config(config):
    """保存新数据管理配置"""
    try:
        with open(NEW_DATA_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving new data config: {e}")
        return False

def get_all_csv_ids():
    """获取所有CSV中的ID集合"""
    all_ids = set()
    exclude_files = {"活动.csv", "战斗通行证.csv"}

    for root, dirs, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith('.csv') and file not in exclude_files:
                csv_path = Path(root) / file
                try:
                    with open(csv_path, 'r', encoding='utf-8-sig') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            item_id = row.get('id', '')
                            if item_id:
                                all_ids.add(item_id)
                                all_ids.add(item_id.lower())  # 同时添加小写版本
                except Exception as e:
                    print(f"Error reading {csv_path}: {e}")

    # 添加已录入的新数据ID（这些不应该在"新数据"区显示）
    config = load_new_data_config()
    for recorded_item in config.get('recorded_items', []):
        item_id = recorded_item.get('id', '')
        if item_id:
            all_ids.add(item_id)
            all_ids.add(item_id.lower())

    return all_ids

def scan_new_data():
    """扫描图片目录，找出CSV中不存在的新数据，按文件夹分类"""
    csv_ids = get_all_csv_ids()
    config = load_new_data_config()
    excluded_ids = set(config.get('excluded_items', []))
    new_items_by_folder = {}

    # 图片目录与友好名称映射（移除currency、titles）
    folder_friendly_names = {
        "avataricons": "头像",
        "camouflages": "涂装",
        "flags": "旗帜",
        "units_ships": "战舰",
        "weapons": "武器"
    }

    # 扫描每个图片目录
    for folder_name, friendly_name in folder_friendly_names.items():
        folder_path = IMAGE_DIR / folder_name
        if not folder_path.exists():
            continue

        folder_items = []
        for png_file in folder_path.glob("*.png"):
            # 跳过缩略图
            if "_Thumbnail" in png_file.stem:
                continue

            item_id = png_file.stem

            # 跳过被排除的项目
            if item_id in excluded_ids or item_id.lower() in excluded_ids:
                continue

            # 检查是否在CSV中存在
            if item_id not in csv_ids and item_id.lower() not in csv_ids:
                folder_items.append({
                    "id": item_id,
                    "folder": folder_name,
                    "folder_name": friendly_name,
                    "image_path": str(png_file.relative_to(BASE_DIR))
                })

        if folder_items:
            new_items_by_folder[folder_name] = {
                "friendly_name": friendly_name,
                "items": folder_items
            }

    return new_items_by_folder

def scan_csv_structure():
    """扫描CSV文件结构，构建分类树"""
    categories = {}

    # 排除的文件
    exclude_files = {"活动.csv", "战斗通行证.csv"}

    for root, dirs, files in os.walk(DATA_DIR):
        rel_path = Path(root).relative_to(DATA_DIR)

        for file in files:
            if file.endswith('.csv') and file not in exclude_files:
                # 获取分类名
                if str(rel_path) == ".":
                    # 根目录的CSV
                    category_name = file.replace('.csv', '')
                    if category_name not in categories:
                        categories[category_name] = {
                            "name": category_name,
                            "path": str(Path(root) / file),
                            "subcategories": []
                        }
                else:
                    # 子目录的CSV
                    parent = str(rel_path)
                    subcategory = file.replace('.csv', '')

                    if parent not in categories:
                        categories[parent] = {
                            "name": parent,
                            "path": None,
                            "subcategories": []
                        }

                    categories[parent]["subcategories"].append({
                        "name": subcategory,
                        "path": str(Path(root) / file),
                        "parent": parent
                    })

    # 添加"新数据"分类（带子分类）
    new_items_by_folder = scan_new_data()
    if new_items_by_folder:
        total_new_items = sum(len(folder_data["items"]) for folder_data in new_items_by_folder.values())

        subcategories = []
        for folder_name, folder_data in new_items_by_folder.items():
            subcategories.append({
                "name": f"{folder_data['friendly_name']} ({len(folder_data['items'])})",
                "path": f"__new_data__{folder_name}",  # 特殊标识加文件夹名
                "parent": "新数据",
                "folder": folder_name
            })

        categories["新数据"] = {
            "name": f"新数据 ({total_new_items})",
            "path": None,
            "subcategories": subcategories,
            "is_new_data": True
        }

    # 添加"已录入数据"分类（按月份分组）
    config = load_new_data_config()
    recorded_items = config.get('recorded_items', [])
    if recorded_items:
        # 按月份分组
        by_month = {}
        for item in recorded_items:
            month = item.get('added_date', '未知')
            if month not in by_month:
                by_month[month] = []
            by_month[month].append(item)

        # 创建子分类
        subcategories = []
        for month in sorted(by_month.keys(), reverse=True):  # 最新月份在前
            items = by_month[month]
            subcategories.append({
                "name": f"{month} ({len(items)})",
                "path": f"__recorded_data__{month}",  # 特殊标识加月份
                "parent": "已录入数据",
                "month": month
            })

        categories["已录入数据"] = {
            "name": f"已录入数据 ({len(recorded_items)})",
            "path": None,
            "subcategories": subcategories,
            "is_recorded_data": True
        }

    return categories

def load_csv_data(csv_path):
    """加载CSV数据"""
    items = []

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(row)
    except Exception as e:
        print(f"Error loading {csv_path}: {e}")

    return items

def check_image_exists(item_id, category_name):
    """检查图片是否存在"""
    # 根据分类确定图片目录
    image_folder = CATEGORY_IMAGE_MAP.get(category_name)

    if not image_folder:
        # 尝试从父级分类推断
        for cat_key, img_folder in CATEGORY_IMAGE_MAP.items():
            if cat_key in category_name or category_name in cat_key:
                image_folder = img_folder
                break

    if not image_folder:
        return None, None

    image_dir = IMAGE_DIR / image_folder

    if not image_dir.exists():
        return None, None

    # 检查PNG文件
    image_path = image_dir / f"{item_id}.png"
    if image_path.exists():
        return str(image_path.relative_to(BASE_DIR)), True

    # 检查小写
    image_path_lower = image_dir / f"{item_id.lower()}.png"
    if image_path_lower.exists():
        return str(image_path_lower.relative_to(BASE_DIR)), True

    return None, False

def generate_item_image_path(item_id, item_type, activity_id=None):
    """根据物品ID和类型生成图片路径（用于活动加载）"""
    if not item_id or not item_type:
        return None

    # 根据类型确定图片目录列表（资源/道具需要检查多个目录）
    image_folders = []

    if item_type in ["资源", "道具"]:
        # 资源类物品需要检查currency和common-items目录
        image_folders = [
            IMAGE_DIR / "currency",
            BASE_DIR / "MW解包有益资源" / "common-items"
        ]
    else:
        # 其他类型使用映射表
        image_folder = CATEGORY_IMAGE_MAP.get(item_type)
        if image_folder:
            image_folders = [IMAGE_DIR / image_folder]

    if not image_folders:
        return None

    # 特殊处理：机密货物类专用货币需要带上活动ID
    special_currency_ids = ['bigevent_currency_gacha_gameplay', 'bigevent_currency_gacha_rm']

    # 在所有可能的目录中查找图片
    for image_dir in image_folders:
        if not image_dir.exists():
            continue

        # 如果是特殊货币且有活动ID，使用 {item_id}_{activity_id}.png 格式
        if item_id in special_currency_ids and activity_id:
            special_image_path = image_dir / f"{item_id}_{activity_id}.png"
            if special_image_path.exists():
                return str(special_image_path.relative_to(BASE_DIR))

        # 检查PNG文件（普通格式）
        image_path = image_dir / f"{item_id}.png"
        if image_path.exists():
            return str(image_path.relative_to(BASE_DIR))

        # 检查小写
        image_path_lower = image_dir / f"{item_id.lower()}.png"
        if image_path_lower.exists():
            return str(image_path_lower.relative_to(BASE_DIR))

    return None

# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>现代战舰 - 数据资源比对</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: "Microsoft YaHei", Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* 左侧导航栏 */
        .sidebar {
            width: 250px;
            background: #16213e;
            border-right: 2px solid #0f3460;
            overflow-y: auto;
            padding: 20px 0;
        }

        .sidebar h2 {
            padding: 0 20px 15px;
            color: #e94560;
            font-size: 20px;
            border-bottom: 2px solid #0f3460;
            margin-bottom: 15px;
        }

        .category {
            margin-bottom: 10px;
        }

        .category-title {
            padding: 12px 20px;
            cursor: pointer;
            background: #16213e;
            transition: all 0.3s;
            font-weight: bold;
            color: #fff;
        }

        .category-title:hover {
            background: #0f3460;
            padding-left: 25px;
        }

        .category-title.active {
            background: #e94560;
            color: #fff;
        }

        .subcategory {
            padding: 10px 20px 10px 40px;
            cursor: pointer;
            background: #1a1a2e;
            transition: all 0.3s;
            color: #bbb;
            border-left: 3px solid transparent;
        }

        .subcategory:hover {
            background: #0f3460;
            padding-left: 45px;
            color: #fff;
            border-left-color: #e94560;
        }

        .subcategory.active {
            background: #0f3460;
            color: #e94560;
            border-left-color: #e94560;
            font-weight: bold;
        }

        /* 主内容区 */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .header {
            background: #16213e;
            padding: 20px 30px;
            border-bottom: 2px solid #0f3460;
        }

        .header h1 {
            color: #e94560;
            font-size: 24px;
            margin-bottom: 10px;
        }

        .header-info {
            color: #bbb;
            font-size: 14px;
        }

        .controls {
            background: #16213e;
            padding: 15px 30px;
            border-bottom: 2px solid #0f3460;
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .search-box {
            flex: 1;
            max-width: 400px;
        }

        .search-box input {
            width: 100%;
            padding: 10px 15px;
            background: #1a1a2e;
            border: 2px solid #0f3460;
            color: #fff;
            border-radius: 5px;
            font-size: 14px;
        }

        .search-box input:focus {
            outline: none;
            border-color: #e94560;
        }

        .filter-info {
            color: #bbb;
            font-size: 14px;
        }

        .filter-info .count {
            color: #e94560;
            font-weight: bold;
        }

        /* 物品网格 */
        .items-container {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
        }

        .items-grid {
            display: grid;
            grid-template-columns: repeat(10, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }

        /* 右侧面板激活时，网格改为5列 */
        body.activity-panel-active .items-grid {
            grid-template-columns: repeat(5, 1fr);
        }

        .item-card {
            background: rgba(30, 41, 59, 0.3);
            border: 2px solid #4b5563;
            border-radius: 0;
            padding: 4px;
            transition: all 0.3s;
            cursor: grab;
            position: relative;
            overflow: hidden;
        }

        .item-card:active {
            cursor: grabbing;
        }

        .item-card.dragging {
            opacity: 0.5;
        }

        .item-card:hover {
            transform: scale(1.05);
            box-shadow: 0 0 20px rgba(233, 69, 96, 0.4);
        }

        .item-card.no-image {
            border-color: #ff6b6b;
            opacity: 0.6;
        }

        .item-card.no-image::after {
            content: "缺失";
            position: absolute;
            top: 3px;
            left: 3px;
            background: #ff6b6b;
            color: #fff;
            padding: 2px 6px;
            border-radius: 0;
            font-size: 10px;
            z-index: 10;
        }

        .item-card.new-item {
            border-color: #4ade80;
        }

        .item-card.new-item::before {
            content: "NEW";
            position: absolute;
            top: 3px;
            left: 3px;
            background: #4ade80;
            color: #000;
            padding: 2px 6px;
            border-radius: 0;
            font-size: 10px;
            font-weight: bold;
            z-index: 10;
        }

        .item-card.recorded-item::before {
            content: "已录入";
            position: absolute;
            top: 3px;
            left: 3px;
            background: #60a5fa;
            color: #fff;
            padding: 2px 6px;
            border-radius: 0;
            font-size: 10px;
            font-weight: bold;
            z-index: 10;
        }

        .item-image-container {
            width: 100%;
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }

        .item-image {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }

        .item-name {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.9);
            font-size: 11px;
            color: #fff;
            text-align: center;
            padding: 4px 2px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            opacity: 1;
            z-index: 5;
        }

        .item-id {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.9);
            font-size: 9px;
            color: #bbb;
            text-align: center;
            padding: 3px 2px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            opacity: 1;
            z-index: 5;
        }

        /* 右下角三角形装饰（史诗/传说专属） */
        .rarity-triangle {
            position: absolute;
            right: 0;
            bottom: 0;
            width: 30px;
            height: 30px;
            clip-path: polygon(100% 0%, 100% 100%, 0% 100%);
            z-index: 1;
        }

        /* 稀有度颜色（参考游戏原色） */
        .rarity-legendary {
            border-color: #7c5ca8;
            background: rgba(124, 92, 168, 0.08);
        }

        .rarity-legendary .rarity-triangle {
            background: linear-gradient(135deg, rgba(162, 128, 210, 0.4) 0%, #a280d2 30%, #a280d2 100%);
        }

        .rarity-epic {
            border-color: #b8761f;
            background: rgba(184, 118, 31, 0.08);
        }

        .rarity-epic .rarity-triangle {
            background: linear-gradient(135deg, rgba(224, 147, 46, 0.4) 0%, #e0932e 30%, #e0932e 100%);
        }

        .rarity-rare {
            border-color: #2563eb;
            background: rgba(37, 99, 235, 0.08);
        }

        .rarity-common {
            border-color: #4b5563;
            background: rgba(30, 41, 59, 0.3);
        }

        /* 分页 */
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            padding: 20px;
        }

        .pagination button {
            padding: 8px 16px;
            background: #16213e;
            border: 2px solid #0f3460;
            color: #fff;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .pagination button:hover:not(:disabled) {
            background: #e94560;
            border-color: #e94560;
        }

        .pagination button:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }

        .pagination span {
            color: #bbb;
        }

        /* 加载状态 */
        .loading {
            text-align: center;
            padding: 50px;
            color: #bbb;
            font-size: 18px;
        }

        /* 打开活动按钮 */
        .activity-btn {
            padding: 10px 20px;
            background: #4ade80;
            border: none;
            color: #000;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
            transition: all 0.3s;
        }

        .activity-btn:hover {
            background: #22c55e;
            transform: translateY(-2px);
        }

        /* 右侧活动编辑面板 */
        .activity-panel {
            width: 0;
            background: #16213e;
            border-left: 2px solid #0f3460;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: width 0.3s;
        }

        .activity-panel.active {
            width: 450px;
            overflow-y: auto;
        }

        .activity-panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 2px solid #0f3460;
            flex-shrink: 0;
        }

        .activity-panel-header h2 {
            color: #e94560;
            font-size: 20px;
        }

        .close-btn {
            background: transparent;
            border: none;
            color: #bbb;
            font-size: 24px;
            cursor: pointer;
            transition: color 0.3s;
            padding: 0;
            width: 30px;
            height: 30px;
        }

        .close-btn:hover {
            color: #e94560;
        }

        .activity-selector {
            padding: 20px;
            border-bottom: 2px solid #0f3460;
            flex-shrink: 0;
        }

        .activity-selector label {
            display: block;
            color: #bbb;
            font-size: 14px;
            margin: 15px 0 5px;
        }

        .activity-selector select,
        .activity-selector input[type="text"] {
            width: 100%;
            padding: 10px;
            background: #1a1a2e;
            border: 2px solid #0f3460;
            color: #fff;
            border-radius: 5px;
            font-size: 14px;
        }

        .activity-selector select:focus,
        .activity-selector input:focus {
            outline: none;
            border-color: #e94560;
        }

        .btn-primary, .btn-secondary, .btn-success, .btn-danger {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
            transition: all 0.3s;
        }

        .btn-primary {
            background: #e94560;
            color: #fff;
        }

        .btn-primary:hover {
            background: #d63851;
        }

        .btn-secondary {
            background: #0f3460;
            color: #fff;
        }

        .btn-secondary:hover {
            background: #1a4d8f;
        }

        /* 池子标题和添加按钮 */
        .pool-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .pool-header h3 {
            margin: 0;
            flex: 1;
        }

        .add-item-btn {
            background: #4ade80;
            color: #000;
            border: none;
            border-radius: 5px;
            width: 32px;
            height: 32px;
            font-size: 20px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            flex-shrink: 0;
            margin-left: 10px;
        }

        .add-item-btn:hover {
            background: #22c55e;
            transform: scale(1.1);
        }

        /* 资源/道具选择对话框网格 */
        .common-items-modal-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 15px;
            padding: 10px;
            background: #1a1a2e;
            border: 2px solid #0f3460;
            border-radius: 5px;
        }

        .common-item-card {
            background: rgba(30, 41, 59, 0.5);
            border: 2px solid #4b5563;
            border-radius: 5px;
            padding: 8px;
            cursor: pointer;
            transition: all 0.3s;
            position: relative;
            text-align: center;
        }

        .common-item-card:hover {
            transform: scale(1.05);
            box-shadow: 0 0 15px rgba(74, 222, 128, 0.4);
            border-color: #4ade80;
        }

        .common-item-card img {
            width: 100%;
            height: 50px;
            object-fit: contain;
            margin-bottom: 5px;
        }

        .common-item-card .item-id {
            font-size: 9px;
            color: #888;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-bottom: 2px;
        }

        .common-item-card .item-name {
            font-size: 11px;
            color: #fff;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-weight: bold;
        }

        .btn-success {
            background: #4ade80;
            color: #000;
        }

        .btn-success:hover {
            background: #22c55e;
        }

        .btn-danger {
            background: #ff6b6b;
            color: #fff;
        }

        .btn-danger:hover {
            background: #ff5252;
        }

        .activity-info, .activity-items, .activity-actions {
            padding: 20px;
            border-bottom: 2px solid #0f3460;
            flex-shrink: 0;
        }

        .activity-info h3, .activity-items h3 {
            color: #e94560;
            font-size: 16px;
            margin-bottom: 15px;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            color: #bbb;
            font-size: 14px;
            margin-bottom: 5px;
        }

        .form-group input {
            width: 100%;
            padding: 10px;
            background: #1a1a2e;
            border: 2px solid #0f3460;
            color: #fff;
            border-radius: 5px;
            font-size: 14px;
        }

        .form-group input:focus {
            outline: none;
            border-color: #e94560;
        }

        .item-count {
            color: #4ade80;
            font-weight: normal;
        }

        .activity-pools {
            padding: 20px;
            border-bottom: 2px solid #0f3460;
        }

        .activity-pools h3 {
            color: #e94560;
            font-size: 16px;
            margin-bottom: 15px;
            margin-top: 15px;
        }

        .activity-pools h3:first-child {
            margin-top: 0;
        }

        .drop-zone {
            min-height: 150px;
            background: #1a1a2e;
            border: 2px dashed #0f3460;
            border-radius: 5px;
            padding: 15px;
            transition: all 0.3s;
            margin-bottom: 15px;
        }

        .drop-zone.drag-over {
            border-color: #4ade80;
            background: rgba(74, 222, 128, 0.1);
        }

        .drop-hint {
            text-align: center;
            color: #666;
            padding: 20px;
            font-size: 14px;
        }

        .pool-items-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        /* 横向物品卡片 */
        .pool-item-card {
            background: rgba(30, 41, 59, 0.5);
            border: 2px solid #4b5563;
            border-radius: 5px;
            padding: 8px;
            display: flex;
            gap: 10px;
            align-items: center;
            transition: all 0.3s;
        }

        .pool-item-card:hover {
            border-color: #e94560;
        }

        .pool-item-card .item-image {
            width: 60px;
            height: 60px;
            flex-shrink: 0;
            border: 2px solid #4b5563;
            border-radius: 3px;
            object-fit: contain;
            background: rgba(0, 0, 0, 0.3);
        }

        .pool-item-card .item-fields {
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            font-size: 11px;
        }

        .pool-item-card .field-group {
            display: flex;
            flex-direction: column;
        }

        .pool-item-card .field-group label {
            color: #888;
            font-size: 10px;
            margin-bottom: 2px;
        }

        .pool-item-card .field-group input,
        .pool-item-card .field-group select {
            width: 100%;
            padding: 4px 6px;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            color: #fff;
            border-radius: 3px;
            font-size: 11px;
        }

        .pool-item-card .field-group input:focus,
        .pool-item-card .field-group select:focus {
            outline: none;
            border-color: #e94560;
        }

        .pool-item-card .field-group input[type="number"] {
            -moz-appearance: textfield;
        }

        .pool-item-card .field-group input[type="number"]::-webkit-outer-spin-button,
        .pool-item-card .field-group input[type="number"]::-webkit-inner-spin-button {
            -webkit-appearance: none;
            margin: 0;
        }

        .pool-item-card .remove-btn {
            flex-shrink: 0;
            background: #ff6b6b;
            color: #fff;
            border: none;
            border-radius: 3px;
            width: 24px;
            height: 60px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }

        .pool-item-card .remove-btn:hover {
            background: #ff5252;
        }

        /* 拖拽时的样式 */
        .pool-item-card.dragging {
            opacity: 0.5;
        }

        .pool-item-card {
            cursor: grab;
        }

        .pool-item-card:active {
            cursor: grabbing;
        }

        /* 插入位置指示器 */
        .drop-indicator {
            height: 3px;
            background: #4ade80;
            margin: 4px 0;
            border-radius: 2px;
            box-shadow: 0 0 10px rgba(74, 222, 128, 0.5);
        }

        /* 右键菜单 */
        .context-menu {
            position: fixed;
            background: #16213e;
            border: 2px solid #0f3460;
            border-radius: 5px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            z-index: 10000;
            min-width: 150px;
            display: none;
        }

        .context-menu.show {
            display: block;
        }

        .context-menu-item {
            padding: 10px 15px;
            cursor: pointer;
            color: #fff;
            transition: all 0.3s;
            border-bottom: 1px solid #0f3460;
        }

        .context-menu-item:last-child {
            border-bottom: none;
        }

        .context-menu-item:hover {
            background: #e94560;
        }

        .context-menu-item.danger:hover {
            background: #ff6b6b;
        }

        /* 录入对话框 */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        }

        .modal-overlay.show {
            display: flex;
        }

        .modal-dialog {
            background: #16213e;
            border: 2px solid #0f3460;
            border-radius: 10px;
            width: 90%;
            max-width: 500px;
            max-height: 90vh;
            overflow-y: auto;
        }

        .modal-header {
            padding: 20px;
            border-bottom: 2px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-header h3 {
            color: #e94560;
            font-size: 18px;
        }

        .modal-close {
            background: transparent;
            border: none;
            color: #bbb;
            font-size: 24px;
            cursor: pointer;
            width: 30px;
            height: 30px;
        }

        .modal-close:hover {
            color: #e94560;
        }

        .modal-body {
            padding: 20px;
        }

        .modal-form-group {
            margin-bottom: 15px;
        }

        .modal-form-group label {
            display: block;
            color: #bbb;
            font-size: 14px;
            margin-bottom: 5px;
        }

        .modal-form-group label .required {
            color: #e94560;
        }

        .modal-form-group input,
        .modal-form-group select {
            width: 100%;
            padding: 10px;
            background: #1a1a2e;
            border: 2px solid #0f3460;
            color: #fff;
            border-radius: 5px;
            font-size: 14px;
        }

        .modal-form-group input:focus,
        .modal-form-group select:focus {
            outline: none;
            border-color: #e94560;
        }

        .modal-form-group input:read-only {
            color: #666;
            background: #0f1419;
        }

        .modal-footer {
            padding: 15px 20px;
            border-top: 2px solid #0f3460;
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }

        .modal-footer button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: all 0.3s;
        }

        .modal-footer .btn-cancel {
            background: #4b5563;
            color: #fff;
        }

        .modal-footer .btn-cancel:hover {
            background: #6b7280;
        }

        .modal-footer .btn-submit {
            background: #4ade80;
            color: #000;
        }

        .modal-footer .btn-submit:hover {
            background: #22c55e;
        }

        /* 滚动条样式 */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #1a1a2e;
        }

        ::-webkit-scrollbar-thumb {
            background: #0f3460;
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #e94560;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>数据分类</h2>
        <div id="categories"></div>
    </div>

    <div class="main-content">
        <div class="header">
            <h1>现代战舰 - 数据资源比对</h1>
            <div class="header-info">
                <span id="current-category">请选择一个分类</span>
            </div>
        </div>

        <div class="controls">
            <div class="search-box">
                <input type="text" id="search-input" placeholder="搜索物品名称或ID...">
            </div>
            <div class="filter-info">
                共 <span class="count" id="total-count">0</span> 项 |
                缺失图片: <span class="count" id="missing-count">0</span> 项
            </div>
            <button id="open-activity-btn" class="activity-btn">📂 打开活动</button>
        </div>

        <div class="items-container">
            <div id="items-grid" class="items-grid"></div>
            <div class="pagination">
                <button id="prev-page">上一页</button>
                <span id="page-info">第 1 页 / 共 1 页</span>
                <button id="next-page">下一页</button>
            </div>
        </div>
    </div>

    <!-- 右侧活动编辑面板 -->
    <div class="activity-panel" id="activity-panel">
        <div class="activity-panel-header">
            <h2>活动编辑器</h2>
            <button id="close-activity-btn" class="close-btn">✕</button>
        </div>

        <div class="activity-selector">
            <label for="activity-type">活动类型:</label>
            <select id="activity-type">
                <option value="">选择类型...</option>
                <option value="chip">筹码类</option>
                <option value="flagship">旗舰宝箱类</option>
                <option value="cargo">机密货物类</option>
            </select>

            <label for="activity-id">活动ID:</label>
            <select id="activity-id" disabled>
                <option value="">先选择活动类型...</option>
            </select>

            <button id="load-activity-btn" class="btn-primary" disabled>加载活动</button>
            <button id="new-activity-btn" class="btn-secondary" disabled>新建活动</button>
        </div>

        <div class="activity-info" id="activity-info" style="display:none;">
            <h3>活动信息</h3>
            <div class="form-group">
                <label>活动名称:</label>
                <input type="text" id="activity-name" placeholder="活动名称">
            </div>
            <div class="form-group">
                <label>活动日期:</label>
                <input type="text" id="activity-date" placeholder="2024年10月">
            </div>
        </div>

        <!-- 筹码类单池 -->
        <div class="activity-pools" id="activity-pools-chip" style="display:none;">
            <div class="pool-header">
                <h3>奖池物品 <span class="item-count">(<span id="pool-chip-count">0</span>)</span></h3>
                <button class="add-item-btn" data-pool="chip" title="添加资源/道具">+</button>
            </div>
            <div class="drop-zone" data-pool="chip">
                <p class="drop-hint">从左侧拖拽物品到这里</p>
                <div class="pool-items-list" id="pool-chip-list"></div>
            </div>
        </div>

        <!-- 旗舰宝箱类双池 -->
        <div class="activity-pools" id="activity-pools-flagship" style="display:none;">
            <div class="pool-header">
                <h3>旗舰宝箱 <span class="item-count">(<span id="pool-flagship-count">0</span>)</span></h3>
                <button class="add-item-btn" data-pool="flagship" title="添加资源/道具">+</button>
            </div>
            <div class="drop-zone" data-pool="flagship">
                <p class="drop-hint">从左侧拖拽物品到这里</p>
                <div class="pool-items-list" id="pool-flagship-list"></div>
            </div>

            <div class="pool-header">
                <h3>宝箱券 <span class="item-count">(<span id="pool-voucher-count">0</span>)</span></h3>
                <button class="add-item-btn" data-pool="voucher" title="添加资源/道具">+</button>
            </div>
            <div class="drop-zone" data-pool="voucher">
                <p class="drop-hint">从左侧拖拽物品到这里</p>
                <div class="pool-items-list" id="pool-voucher-list"></div>
            </div>
        </div>

        <!-- 机密货物类双池 -->
        <div class="activity-pools" id="activity-pools-cargo" style="display:none;">
            <div class="pool-header">
                <h3>货运无人机 <span class="item-count">(<span id="pool-gameplay-count">0</span>)</span></h3>
                <button class="add-item-btn" data-pool="gameplay" title="添加资源/道具">+</button>
            </div>
            <div class="drop-zone" data-pool="gameplay">
                <p class="drop-hint">从左侧拖拽物品到这里</p>
                <div class="pool-items-list" id="pool-gameplay-list"></div>
            </div>

            <div class="pool-header">
                <h3>机密货物 <span class="item-count">(<span id="pool-rm-count">0</span>)</span></h3>
                <button class="add-item-btn" data-pool="rm" title="添加资源/道具">+</button>
            </div>
            <div class="drop-zone" data-pool="rm">
                <p class="drop-hint">从左侧拖拽物品到这里</p>
                <div class="pool-items-list" id="pool-rm-list"></div>
            </div>
        </div>

        <div class="activity-actions" id="activity-actions" style="display:none;">
            <button id="save-activity-btn" class="btn-success">💾 保存活动</button>
            <button id="clear-activity-btn" class="btn-danger">清空物品</button>
        </div>
    </div>

    <!-- 右键菜单 -->
    <div class="context-menu" id="contextMenu">
        <div class="context-menu-item" id="menu-record">📝 录入主数据区</div>
        <div class="context-menu-item danger" id="menu-exclude">🚫 排除此项</div>
    </div>

    <!-- 选择资源/道具对话框 -->
    <div class="modal-overlay" id="commonItemModal">
        <div class="modal-dialog">
            <div class="modal-header">
                <h3>选择资源/道具</h3>
                <button class="modal-close" id="commonItemModalClose">✕</button>
            </div>
            <div class="modal-body">
                <div class="modal-form-group">
                    <label>类型筛选</label>
                    <select id="common-item-filter">
                        <option value="">全部</option>
                        <option value="资源">资源</option>
                        <option value="道具">道具</option>
                    </select>
                </div>
                <div class="modal-form-group">
                    <label>搜索</label>
                    <input type="text" id="common-item-search" placeholder="搜索物品名称...">
                </div>
                <div class="common-items-modal-grid" id="common-items-modal-grid"></div>
            </div>
        </div>
    </div>

    <!-- 录入数据对话框 -->
    <div class="modal-overlay" id="recordModal">
        <div class="modal-dialog">
            <div class="modal-header">
                <h3>录入新数据到主数据区</h3>
                <button class="modal-close" id="modalClose">✕</button>
            </div>
            <div class="modal-body">
                <div class="modal-form-group">
                    <label>ID <span class="required">*</span></label>
                    <input type="text" id="record-id" readonly>
                </div>
                <div class="modal-form-group">
                    <label>中文名 <span class="required">*</span></label>
                    <input type="text" id="record-name-cn" placeholder="请输入中文名称">
                </div>
                <div class="modal-form-group">
                    <label>英文名 <span class="required">*</span></label>
                    <input type="text" id="record-name-en" placeholder="请输入英文名称">
                </div>
                <div class="modal-form-group">
                    <label>类型 <span class="required">*</span></label>
                    <select id="record-type">
                        <option value="">请选择类型</option>
                        <optgroup label="舰船">
                            <option value="战舰">战舰</option>
                            <option value="无人舰艇">无人舰艇</option>
                        </optgroup>
                        <optgroup label="武器">
                            <option value="主炮">主炮</option>
                            <option value="导弹">导弹</option>
                            <option value="火箭炮">火箭炮</option>
                            <option value="自卫炮">自卫炮</option>
                            <option value="防空设备">防空设备</option>
                            <option value="鱼雷">鱼雷</option>
                        </optgroup>
                        <optgroup label="航空器">
                            <option value="战斗机">战斗机</option>
                            <option value="攻击机">攻击机</option>
                            <option value="无人机">无人机</option>
                            <option value="直升机">直升机</option>
                            <option value="轰炸机">轰炸机</option>
                        </optgroup>
                        <optgroup label="其他">
                            <option value="头像">头像</option>
                            <option value="旗帜">旗帜</option>
                            <option value="涂装">涂装</option>
                        </optgroup>
                    </select>
                </div>
                <div class="modal-form-group">
                    <label>分类 <span class="required">*</span></label>
                    <input type="text" id="record-category" readonly>
                </div>
                <div class="modal-form-group">
                    <label>稀有度</label>
                    <select id="record-rarity">
                        <option value="">无</option>
                        <option value="rare">稀有</option>
                        <option value="epic">史诗</option>
                        <option value="legendary">传说</option>
                    </select>
                </div>
                <div class="modal-form-group">
                    <label>录入日期 <span class="required">*</span></label>
                    <input type="text" id="record-date" placeholder="格式: 2025.10">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-cancel" id="modalCancel">取消</button>
                <button class="btn-submit" id="modalSubmit">确定录入</button>
            </div>
        </div>
    </div>

    <script>
        let currentCategory = null;
        let currentData = [];
        let filteredData = [];
        let currentPage = 1;
        const itemsPerPage = 60; // 10列 x 6排

        // 新数据管理相关变量
        let currentContextItem = null; // 当前右键点击的项
        const contextMenu = document.getElementById('contextMenu');
        const recordModal = document.getElementById('recordModal');

        // 全局点击事件 - 关闭右键菜单
        document.addEventListener('click', () => {
            contextMenu.classList.remove('show');
        });

        // 阻止默认右键菜单
        document.addEventListener('contextmenu', (e) => {
            // 只在特定元素上禁用默认右键菜单
            if (e.target.closest('.item-card')) {
                e.preventDefault();
            }
        });

        // 加载分类
        async function loadCategories() {
            const response = await fetch('/api/categories');
            const categories = await response.json();

            const container = document.getElementById('categories');
            container.innerHTML = '';

            for (const [key, category] of Object.entries(categories)) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'category';

                if (category.path) {
                    // 单独的分类
                    const titleDiv = document.createElement('div');
                    titleDiv.className = 'category-title';
                    titleDiv.textContent = category.name;
                    titleDiv.onclick = function(e) {
                        loadCategoryData(category.name, category.path, null, e.currentTarget);
                    };
                    categoryDiv.appendChild(titleDiv);
                } else if (category.subcategories.length > 0) {
                    // 有子分类
                    const titleDiv = document.createElement('div');
                    titleDiv.className = 'category-title';
                    titleDiv.textContent = category.name;
                    categoryDiv.appendChild(titleDiv);

                    category.subcategories.forEach(sub => {
                        const subDiv = document.createElement('div');
                        subDiv.className = 'subcategory';
                        subDiv.textContent = sub.name;
                        subDiv.onclick = (e) => {
                            e.stopPropagation();
                            loadCategoryData(sub.name, sub.path, sub.parent, e.currentTarget);
                        };
                        categoryDiv.appendChild(subDiv);
                    });
                }

                container.appendChild(categoryDiv);
            }
        }

        // 加载分类数据
        async function loadCategoryData(name, path, parent = null, clickedElement = null) {
            currentCategory = parent ? `${parent} - ${name}` : name;
            document.getElementById('current-category').textContent = currentCategory;

            const response = await fetch('/api/items', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({csv_path: path, category: name})
            });

            currentData = await response.json();
            filteredData = currentData;
            currentPage = 1;

            updateStats();
            renderItems();

            // 更新选中状态
            document.querySelectorAll('.category-title, .subcategory').forEach(el => {
                el.classList.remove('active');
            });
            if (clickedElement) {
                clickedElement.classList.add('active');
            }
        }

        // 更新统计信息
        function updateStats() {
            const total = filteredData.length;
            const missing = filteredData.filter(item => !item.has_image).length;

            document.getElementById('total-count').textContent = total;
            document.getElementById('missing-count').textContent = missing;
        }

        // 渲染物品
        function renderItems() {
            const start = (currentPage - 1) * itemsPerPage;
            const end = start + itemsPerPage;
            const pageItems = filteredData.slice(start, end);

            const container = document.getElementById('items-grid');
            container.innerHTML = '';

            pageItems.forEach(item => {
                const card = document.createElement('div');
                card.className = 'item-card';

                if (!item.has_image) {
                    card.classList.add('no-image');
                }

                // 新数据特殊标记
                if (item.is_new) {
                    card.classList.add('new-item');

                    // 为新数据项添加右键菜单支持
                    card.addEventListener('contextmenu', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        currentContextItem = item;

                        // 显示右键菜单
                        contextMenu.style.left = e.pageX + 'px';
                        contextMenu.style.top = e.pageY + 'px';
                        contextMenu.classList.add('show');
                    });
                }

                // 已录入数据特殊标记
                if (item.is_recorded) {
                    card.classList.add('recorded-item');
                }

                // 根据稀有度添加边框颜色（支持中英文）
                const rarity = item.data.rarityTypeString || '';
                if (rarity.includes('传说') || rarity === 'legendary') {
                    card.classList.add('rarity-legendary');
                } else if (rarity.includes('史诗') || rarity === 'epic') {
                    card.classList.add('rarity-epic');
                } else if (rarity.includes('稀有') || rarity === 'rare') {
                    card.classList.add('rarity-rare');
                } else if (!item.is_new && !item.is_recorded) {
                    // 新数据和已录入数据不添加普通稀有度颜色
                    card.classList.add('rarity-common');
                }

                // 图片容器
                const imageContainer = document.createElement('div');
                imageContainer.className = 'item-image-container';

                const img = document.createElement('img');
                img.className = 'item-image';
                if (item.has_image) {
                    img.src = `/image/${item.image_path}`;
                } else {
                    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="%23333"/><text x="50" y="50" text-anchor="middle" dominant-baseline="middle" fill="%23666" font-size="12">无图片</text></svg>';
                }
                img.onerror = () => {
                    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="%23333"/><text x="50" y="50" text-anchor="middle" dominant-baseline="middle" fill="%23666" font-size="12">加载失败</text></svg>';
                };

                imageContainer.appendChild(img);

                // 名称（hover显示）
                const name = document.createElement('div');
                name.className = 'item-name';
                name.textContent = item.data.name || item.data.name_en || item.id;
                name.title = item.data.name || item.data.name_en || item.id;

                // ID（hover显示）
                const id = document.createElement('div');
                id.className = 'item-id';
                // 如果是新数据，显示文件夹信息
                if (item.is_new && item.data.folder_name) {
                    id.textContent = `[${item.data.folder_name}] ${item.id}`;
                } else if (item.is_recorded && item.data.added_date) {
                    // 如果是已录入数据，显示录入月份
                    id.textContent = `[${item.data.added_date}] ${item.id}`;
                } else {
                    id.textContent = item.id;
                }
                id.title = item.id;

                imageContainer.appendChild(name);
                imageContainer.appendChild(id);

                // 右下角三角形（史诗/传说）
                if (rarity.includes('传说') || rarity.includes('史诗')) {
                    const triangle = document.createElement('div');
                    triangle.className = 'rarity-triangle';
                    imageContainer.appendChild(triangle);
                }

                card.appendChild(imageContainer);

                container.appendChild(card);
            });

            // 更新分页信息
            const totalPages = Math.ceil(filteredData.length / itemsPerPage);
            document.getElementById('page-info').textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;
            document.getElementById('prev-page').disabled = currentPage === 1;
            document.getElementById('next-page').disabled = currentPage >= totalPages;
        }

        // 搜索
        document.getElementById('search-input').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();

            if (!query) {
                filteredData = currentData;
            } else {
                filteredData = currentData.filter(item => {
                    const name = (item.data.name || '').toLowerCase();
                    const nameEn = (item.data.name_en || '').toLowerCase();
                    const id = item.id.toLowerCase();

                    return name.includes(query) || nameEn.includes(query) || id.includes(query);
                });
            }

            currentPage = 1;
            updateStats();
            renderItems();
        });

        // 分页
        document.getElementById('prev-page').addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderItems();
                document.querySelector('.items-container').scrollTop = 0;
            }
        });

        document.getElementById('next-page').addEventListener('click', () => {
            const totalPages = Math.ceil(filteredData.length / itemsPerPage);
            if (currentPage < totalPages) {
                currentPage++;
                renderItems();
                document.querySelector('.items-container').scrollTop = 0;
            }
        });

        // ==================== 活动编辑器功能 ====================
        let activityPanelOpen = false;
        let currentActivityType = '';
        let currentActivityId = '';
        let poolsData = {}; // {poolName: [items]}

        // 打开活动面板
        document.getElementById('open-activity-btn').addEventListener('click', () => {
            const panel = document.getElementById('activity-panel');
            panel.classList.add('active');
            document.body.classList.add('activity-panel-active');
            activityPanelOpen = true;
            currentPage = 1;
            renderItems();
        });

        // 关闭活动面板
        document.getElementById('close-activity-btn').addEventListener('click', () => {
            const panel = document.getElementById('activity-panel');
            panel.classList.remove('active');
            document.body.classList.remove('activity-panel-active');
            activityPanelOpen = false;
            currentPage = 1;
            renderItems();
        });

        // 活动类型切换，加载该类型的活动ID列表
        document.getElementById('activity-type').addEventListener('change', async (e) => {
            const type = e.target.value;
            const idSelect = document.getElementById('activity-id');
            const loadBtn = document.getElementById('load-activity-btn');
            const newBtn = document.getElementById('new-activity-btn');

            if (!type) {
                idSelect.disabled = true;
                idSelect.innerHTML = '<option value="">先选择活动类型...</option>';
                loadBtn.disabled = true;
                newBtn.disabled = true;
                return;
            }

            try {
                const response = await fetch(`/api/activity/${type}/list`);
                const activityIds = await response.json();

                idSelect.innerHTML = '<option value="">选择活动ID...</option>';
                activityIds.forEach(id => {
                    const option = document.createElement('option');
                    option.value = id;
                    option.textContent = id;
                    idSelect.appendChild(option);
                });

                idSelect.disabled = false;
                loadBtn.disabled = false;
                newBtn.disabled = false;
            } catch (error) {
                alert('加载活动列表失败: ' + error.message);
            }
        });

        // 新建活动
        document.getElementById('new-activity-btn').addEventListener('click', () => {
            const type = document.getElementById('activity-type').value;
            const id = document.getElementById('activity-id').value;

            if (!type) {
                alert('请选择活动类型');
                return;
            }
            if (!id) {
                alert('请选择活动ID');
                return;
            }

            currentActivityType = type;
            currentActivityId = id;
            poolsData = {};

            // 根据类型初始化池子
            if (type === 'chip') {
                poolsData.chip = [];
            } else if (type === 'flagship') {
                poolsData.flagship = [];
                poolsData.voucher = [];
            } else if (type === 'cargo') {
                poolsData.gameplay = [];
                poolsData.rm = [];
            }

            document.getElementById('activity-info').style.display = 'block';
            document.getElementById('activity-actions').style.display = 'block';

            // 显示对应的池子
            showActivityPools(type);

            document.getElementById('activity-name').value = '';
            document.getElementById('activity-date').value = '';

            updateAllPools();
        });

        // 加载活动
        document.getElementById('load-activity-btn').addEventListener('click', async () => {
            const type = document.getElementById('activity-type').value;
            const id = document.getElementById('activity-id').value;

            if (!type) {
                alert('请选择活动类型');
                return;
            }
            if (!id) {
                alert('请选择活动ID');
                return;
            }

            try {
                const response = await fetch(`/api/activity/${type}/${id}`);
                if (!response.ok) {
                    alert('活动不存在或加载失败');
                    return;
                }

                const data = await response.json();
                currentActivityType = type;
                currentActivityId = id;

                document.getElementById('activity-name').value = data.metadata?.name || '';
                document.getElementById('activity-date').value = data.metadata?.formattedDate || '';

                // 根据不同类型加载物品到对应池子
                poolsData = {};
                if (type === 'chip') {
                    poolsData.chip = data.items || [];
                } else if (type === 'flagship') {
                    poolsData.flagship = [];
                    poolsData.voucher = [];
                    if (data.lootboxes) {
                        data.lootboxes.forEach(box => {
                            if (box.type === 'flagship' && box.items) {
                                poolsData.flagship = box.items;
                            } else if (box.type === 'voucher' && box.items) {
                                poolsData.voucher = box.items;
                            }
                        });
                    }
                } else if (type === 'cargo') {
                    poolsData.gameplay = [];
                    poolsData.rm = [];
                    if (data.cargos) {
                        data.cargos.forEach(cargo => {
                            if (cargo.type === 'gameplay' && cargo.items) {
                                poolsData.gameplay = cargo.items;
                            } else if (cargo.type === 'rm' && cargo.items) {
                                poolsData.rm = cargo.items;
                            }
                        });
                    }
                }

                document.getElementById('activity-info').style.display = 'block';
                document.getElementById('activity-actions').style.display = 'block';

                // 显示对应的池子
                showActivityPools(type);

                updateAllPools();
            } catch (error) {
                alert('加载活动失败: ' + error.message);
            }
        });

        // 保存活动
        document.getElementById('save-activity-btn').addEventListener('click', async () => {
            if (!currentActivityType || !currentActivityId) {
                alert('请先加载或新建活动');
                return;
            }

            const activityData = {
                id: currentActivityId,
                gacha_type: currentActivityType === 'chip' ? '筹码类' :
                           currentActivityType === 'flagship' ? '旗舰宝箱类' : '机密货物类',
                metadata: {
                    name: document.getElementById('activity-name').value || '',
                    formattedDate: document.getElementById('activity-date').value || ''
                }
            };

            // 根据类型构建数据结构
            if (currentActivityType === 'chip') {
                activityData.items = poolsData.chip || [];
            } else if (currentActivityType === 'flagship') {
                activityData.lootboxes = [
                    {
                        type: 'flagship',
                        items: poolsData.flagship || []
                    },
                    {
                        type: 'voucher',
                        items: poolsData.voucher || []
                    }
                ];
            } else if (currentActivityType === 'cargo') {
                activityData.cargos = [
                    {
                        type: 'gameplay',
                        items: poolsData.gameplay || []
                    },
                    {
                        type: 'rm',
                        items: poolsData.rm || []
                    }
                ];
            }

            try {
                const response = await fetch(`/api/activity/${currentActivityType}/${currentActivityId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(activityData)
                });

                if (response.ok) {
                    alert('保存成功！');
                } else {
                    alert('保存失败');
                }
            } catch (error) {
                alert('保存失败: ' + error.message);
            }
        });

        // 清空物品
        document.getElementById('clear-activity-btn').addEventListener('click', () => {
            if (confirm('确定要清空所有池子的物品吗？')) {
                // 清空所有池子
                Object.keys(poolsData).forEach(poolName => {
                    poolsData[poolName] = [];
                });
                updateAllPools();
            }
        });

        // 显示对应类型的池子
        function showActivityPools(type) {
            // 隐藏所有池子
            document.getElementById('activity-pools-chip').style.display = 'none';
            document.getElementById('activity-pools-flagship').style.display = 'none';
            document.getElementById('activity-pools-cargo').style.display = 'none';

            // 显示对应池子
            if (type === 'chip') {
                document.getElementById('activity-pools-chip').style.display = 'block';
            } else if (type === 'flagship') {
                document.getElementById('activity-pools-flagship').style.display = 'block';
            } else if (type === 'cargo') {
                document.getElementById('activity-pools-cargo').style.display = 'block';
            }
        }

        // 更新所有池子
        function updateAllPools() {
            Object.keys(poolsData).forEach(poolName => {
                updatePoolItems(poolName);
            });
        }

        // 更新单个池子的物品显示
        function updatePoolItems(poolName) {
            const listContainer = document.getElementById(`pool-${poolName}-list`);
            const countSpan = document.getElementById(`pool-${poolName}-count`);
            const items = poolsData[poolName] || [];

            countSpan.textContent = items.length;

            if (items.length === 0) {
                listContainer.innerHTML = '';
                return;
            }

            listContainer.innerHTML = '';

            items.forEach((item, index) => {
                const card = document.createElement('div');
                card.className = 'pool-item-card';

                // 图片
                const img = document.createElement('img');
                img.className = 'item-image';
                img.src = item.image_path ? `/image/${item.image_path}` : 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect width="60" height="60" fill="%23333"/></svg>';
                img.onerror = () => {
                    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect width="60" height="60" fill="%23333"/></svg>';
                };

                // 属性输入区域
                const fieldsDiv = document.createElement('div');
                fieldsDiv.className = 'item-fields';

                // ID
                const idGroup = createFieldGroup('ID', item.id, 'text', true);
                // 名称
                const nameGroup = createFieldGroup('名称', item.name, 'text', false, (value) => {
                    item.name = value;
                });
                // 类型
                const typeGroup = createFieldGroup('类型', item.type, 'text', true);
                // 稀有度（只读）
                const rarityGroup = createFieldGroup('稀有度', item.rarity, 'text', true);
                // 概率
                const probabilityGroup = createFieldGroup('概率', item.probability || 0, 'number', false, (value) => {
                    item.probability = parseFloat(value) || 0;
                });
                // 限制
                const limitGroup = createFieldGroup('限制', item.limit || 0, 'number', false, (value) => {
                    item.limit = parseInt(value) || 0;
                });

                fieldsDiv.appendChild(idGroup);
                fieldsDiv.appendChild(nameGroup);
                fieldsDiv.appendChild(typeGroup);
                fieldsDiv.appendChild(rarityGroup);
                fieldsDiv.appendChild(probabilityGroup);
                fieldsDiv.appendChild(limitGroup);

                // 删除按钮
                const removeBtn = document.createElement('button');
                removeBtn.className = 'remove-btn';
                removeBtn.textContent = '✕';
                removeBtn.onclick = () => {
                    poolsData[poolName].splice(index, 1);
                    updatePoolItems(poolName);
                };

                card.appendChild(img);
                card.appendChild(fieldsDiv);
                card.appendChild(removeBtn);

                // 添加拖拽功能
                card.setAttribute('draggable', 'true');
                card.addEventListener('dragstart', (e) => {
                    card.classList.add('dragging');
                    draggedItem = item;
                    draggedFromPool = poolName;
                    draggedIndex = index;
                    e.dataTransfer.effectAllowed = 'move';
                });

                card.addEventListener('dragend', () => {
                    card.classList.remove('dragging');
                });

                listContainer.appendChild(card);
            });
        }

        // 创建字段组
        function createFieldGroup(labelText, value, inputType, readonly, onchange, options) {
            const group = document.createElement('div');
            group.className = 'field-group';

            const label = document.createElement('label');
            label.textContent = labelText;

            let input;
            if (inputType === 'select') {
                input = document.createElement('select');
                options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt;
                    option.textContent = opt;
                    if (opt === value) option.selected = true;
                    input.appendChild(option);
                });
            } else {
                input = document.createElement('input');
                input.type = inputType;
                input.value = value || '';
            }

            if (readonly) {
                input.readOnly = true;
                input.style.color = '#666';
            }

            if (onchange) {
                input.addEventListener('change', (e) => onchange(e.target.value));
            }

            group.appendChild(label);
            group.appendChild(input);
            return group;
        }

        // ==================== 资源/道具选择对话框 ====================
        let commonItems = [];  // 所有资源/道具
        let filteredCommonItems = [];  // 过滤后的资源/道具
        let targetPool = '';  // 目标池子

        const commonItemModal = document.getElementById('commonItemModal');
        const commonItemModalClose = document.getElementById('commonItemModalClose');
        const commonItemFilter = document.getElementById('common-item-filter');
        const commonItemSearch = document.getElementById('common-item-search');

        // 加载资源/道具列表
        async function loadCommonItems() {
            if (commonItems.length > 0) return; // 只加载一次

            try {
                const response = await fetch('/api/common-items');
                commonItems = await response.json();
            } catch (error) {
                console.error('加载资源/道具失败:', error);
            }
        }

        // 渲染资源/道具网格
        function renderCommonItemsModal() {
            const grid = document.getElementById('common-items-modal-grid');
            grid.innerHTML = '';

            filteredCommonItems.forEach(item => {
                const card = document.createElement('div');
                card.className = 'common-item-card';
                card.dataset.itemId = item.id;

                const img = document.createElement('img');
                if (item.image_path) {
                    img.src = `/image/${item.image_path}`;
                } else {
                    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect width="60" height="60" fill="%23333"/></svg>';
                }
                img.onerror = () => {
                    img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect width="60" height="60" fill="%23333"/></svg>';
                };

                const id = document.createElement('div');
                id.className = 'item-id';
                id.textContent = item.id;
                id.title = item.id;

                const name = document.createElement('div');
                name.className = 'item-name';
                name.textContent = item.name;
                name.title = item.name;

                card.appendChild(img);
                card.appendChild(id);
                card.appendChild(name);

                // 点击添加到池子
                card.addEventListener('click', () => {
                    addCommonItemToPool(item, targetPool);
                    closeCommonItemModal();
                });

                grid.appendChild(card);
            });
        }

        // 添加资源/道具到池子
        function addCommonItemToPool(item, poolName) {
            if (!poolsData[poolName]) return;

            // 检查是否已存在
            const exists = poolsData[poolName].some(poolItem => poolItem.id === item.id);
            if (exists) {
                alert('该物品已在此池子中');
                return;
            }

            // 构建新物品
            const newItem = {
                id: item.id,
                name: item.name,
                type: item.type,
                rarity: 'common',
                probability: 0,
                limit: 0,
                image_path: item.image_path
            };

            poolsData[poolName].push(newItem);
            updatePoolItems(poolName);
        }

        // 过滤资源/道具
        function filterCommonItems() {
            const filterType = commonItemFilter.value;
            const searchQuery = commonItemSearch.value.toLowerCase();

            filteredCommonItems = commonItems.filter(item => {
                const matchType = !filterType || item.type === filterType;
                const matchSearch = !searchQuery || item.name.toLowerCase().includes(searchQuery);
                return matchType && matchSearch;
            });

            renderCommonItemsModal();
        }

        // 打开对话框
        async function openCommonItemModal(poolName) {
            targetPool = poolName;
            await loadCommonItems();
            filteredCommonItems = commonItems;
            commonItemFilter.value = '';
            commonItemSearch.value = '';
            renderCommonItemsModal();
            commonItemModal.classList.add('show');
        }

        // 关闭对话框
        function closeCommonItemModal() {
            commonItemModal.classList.remove('show');
        }

        // 添加按钮事件
        document.querySelectorAll('.add-item-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const poolName = btn.getAttribute('data-pool');
                openCommonItemModal(poolName);
            });
        });

        // 对话框关闭事件
        commonItemModalClose.addEventListener('click', closeCommonItemModal);
        commonItemModal.addEventListener('click', (e) => {
            if (e.target === commonItemModal) {
                closeCommonItemModal();
            }
        });

        // 筛选和搜索事件
        commonItemFilter.addEventListener('change', filterCommonItems);
        commonItemSearch.addEventListener('input', filterCommonItems);

        // ==================== 拖拽功能 ====================
        let draggedItem = null;
        let draggedFromPool = null; // 记录拖拽源池子
        let draggedIndex = -1; // 记录拖拽物品在池子中的索引

        // 使用事件委托处理拖拽
        const itemsGrid = document.getElementById('items-grid');

        itemsGrid.addEventListener('dragstart', (e) => {
            if (!activityPanelOpen || !currentActivityType) return;

            const card = e.target.closest('.item-card');
            if (!card) return;

            const itemIndex = parseInt(card.dataset.itemIndex);
            if (isNaN(itemIndex)) return;

            const item = filteredData[itemIndex];
            if (!item) return;

            card.classList.add('dragging');
            draggedItem = item;
            draggedFromPool = null;
            draggedIndex = -1;
            e.dataTransfer.effectAllowed = 'copy';
        });

        itemsGrid.addEventListener('dragend', (e) => {
            const card = e.target.closest('.item-card');
            if (card) {
                card.classList.remove('dragging');
            }
        });

        // 修改 renderItems，添加draggable属性和数据索引
        const originalRenderItems = renderItems;
        renderItems = function() {
            originalRenderItems();

            // 只在活动面板打开时启用拖拽
            if (activityPanelOpen && currentActivityType) {
                const cards = itemsGrid.querySelectorAll('.item-card');
                const start = (currentPage - 1) * itemsPerPage;

                cards.forEach((card, index) => {
                    const dataIndex = start + index;
                    if (filteredData[dataIndex]) {
                        card.setAttribute('draggable', 'true');
                        card.dataset.itemIndex = dataIndex;
                    }
                });
            } else {
                // 面板关闭时移除拖拽
                const cards = itemsGrid.querySelectorAll('.item-card');
                cards.forEach(card => {
                    card.removeAttribute('draggable');
                    delete card.dataset.itemIndex;
                });
            }
        };

        // 拖放区域事件 - 为所有drop-zone设置事件
        function initializeDropZones() {
            const dropZones = document.querySelectorAll('.drop-zone');

            dropZones.forEach(dropZone => {
                const poolName = dropZone.getAttribute('data-pool');
                const listContainer = dropZone.querySelector('.pool-items-list');

                dropZone.addEventListener('dragover', (e) => {
                    e.preventDefault();

                    // 根据是否从同一池子拖拽设置效果
                    if (draggedFromPool === poolName) {
                        e.dataTransfer.dropEffect = 'move';
                    } else {
                        e.dataTransfer.dropEffect = 'copy';
                    }

                    dropZone.classList.add('drag-over');

                    // 移除所有旧的插入指示器
                    document.querySelectorAll('.drop-indicator').forEach(el => el.remove());

                    // 计算插入位置并显示指示器
                    const afterElement = getDragAfterElement(listContainer, e.clientY);
                    const indicator = document.createElement('div');
                    indicator.className = 'drop-indicator';

                    if (afterElement == null) {
                        listContainer.appendChild(indicator);
                    } else {
                        listContainer.insertBefore(indicator, afterElement);
                    }
                });

                dropZone.addEventListener('dragleave', (e) => {
                    // 只有当真正离开dropZone时才移除样式和指示器
                    if (!dropZone.contains(e.relatedTarget)) {
                        dropZone.classList.remove('drag-over');
                        document.querySelectorAll('.drop-indicator').forEach(el => el.remove());
                    }
                });

                dropZone.addEventListener('drop', (e) => {
                    e.preventDefault();
                    dropZone.classList.remove('drag-over');

                    // 移除插入指示器
                    document.querySelectorAll('.drop-indicator').forEach(el => el.remove());

                    if (!draggedItem || !poolName || !poolsData[poolName]) {
                        return;
                    }

                    // 计算插入位置
                    const afterElement = getDragAfterElement(listContainer, e.clientY);
                    let insertIndex = poolsData[poolName].length; // 默认插入末尾

                    if (afterElement) {
                        // 找到 afterElement 对应的索引
                        const cards = [...listContainer.querySelectorAll('.pool-item-card')];
                        const afterIndex = cards.indexOf(afterElement);
                        if (afterIndex !== -1) {
                            insertIndex = afterIndex;
                        }
                    }

                    // 如果是从同一个池子拖拽（排序）
                    if (draggedFromPool === poolName) {
                        // 移动物品位置
                        if (draggedIndex !== -1) {
                            const item = poolsData[poolName].splice(draggedIndex, 1)[0];

                            // 如果原位置在插入位置之前，插入索引需要减1
                            if (draggedIndex < insertIndex) {
                                insertIndex--;
                            }

                            poolsData[poolName].splice(insertIndex, 0, item);
                        }
                    } else {
                        // 从左侧或其他池子添加新物品
                        // 检查是否已存在
                        const exists = poolsData[poolName].some(item => item.id === draggedItem.id);
                        if (exists) {
                            alert('该物品已在此池子中');
                            draggedItem = null;
                            draggedFromPool = null;
                            draggedIndex = -1;
                            return;
                        }

                        // 智能确定类型
                        function determineItemType() {
                            // 如果已经有类型（从池子拖拽）
                            if (draggedItem.type && draggedItem.type !== '未知') {
                                return draggedItem.type;
                            }

                            // 特殊处理：已录入数据（有专门的type字段）
                            if (currentCategory && currentCategory.includes('已录入数据')) {
                                if (draggedItem.data && draggedItem.data.typeString) {
                                    return draggedItem.data.typeString;
                                }
                                return '未知';
                            }

                            // 根据当前分类推断类型
                            if (currentCategory) {
                                // 去掉子分类，只保留主分类
                                const mainCategory = currentCategory.split(' - ')[0];
                                const subCategory = currentCategory.split(' - ')[1];

                                // 特殊处理：武器、航空器、装饰品 - 使用子分类或CSV的typeString
                                if (mainCategory === '武器' || mainCategory === '航空器' || mainCategory === '裝飾品') {
                                    // 优先使用子分类名称
                                    if (subCategory) {
                                        return subCategory;
                                    }
                                    // 其次使用CSV的typeString
                                    if (draggedItem.data && draggedItem.data.typeString) {
                                        return draggedItem.data.typeString;
                                    }
                                    // 最后使用主分类名
                                    return mainCategory;
                                }

                                // 单独的分类（战舰等）直接映射
                                const categoryToType = {
                                    '战舰': '战舰',
                                    '无人舰艇': '无人舰艇',
                                    '新数据': draggedItem.data?.folder_name || '未知'
                                };

                                if (categoryToType[mainCategory]) {
                                    return categoryToType[mainCategory];
                                }

                                // 如果分类本身就是类型名（如直接在"头像"、"旗帜"分类下）
                                return mainCategory;
                            }

                            return '未知';
                        }

                        // 构建新物品
                        const newItem = {
                            id: draggedItem.id,
                            name: draggedItem.data ? (draggedItem.data.name || draggedItem.data.name_en || draggedItem.id) : (draggedItem.name || draggedItem.id),
                            type: determineItemType(),
                            rarity: draggedItem.data ? normalizeRarity(draggedItem.data.rarityTypeString || 'common') : (draggedItem.rarity || 'common'),
                            probability: draggedItem.probability || 0,
                            limit: draggedItem.limit || 0,
                            image_path: draggedItem.image_path
                        };

                        // 在指定位置插入
                        poolsData[poolName].splice(insertIndex, 0, newItem);
                    }

                    updatePoolItems(poolName);
                    draggedItem = null;
                    draggedFromPool = null;
                    draggedIndex = -1;
                });
            });
        }

        // 获取鼠标下方的元素（用于确定插入位置）
        function getDragAfterElement(container, y) {
            const draggableElements = [...container.querySelectorAll('.pool-item-card:not(.dragging)')];

            return draggableElements.reduce((closest, child) => {
                const box = child.getBoundingClientRect();
                const offset = y - box.top - box.height / 2;

                if (offset < 0 && offset > closest.offset) {
                    return { offset: offset, element: child };
                } else {
                    return closest;
                }
            }, { offset: Number.NEGATIVE_INFINITY }).element;
        }

        // 初始化drop zones
        initializeDropZones();

        function normalizeRarity(rarityStr) {
            if (!rarityStr) return 'common';

            // 已经是英文格式，直接返回
            if (rarityStr === 'legendary' || rarityStr === 'epic' || rarityStr === 'rare' || rarityStr === 'common') {
                return rarityStr;
            }

            // 中文转英文
            if (rarityStr.includes('传说')) return 'legendary';
            if (rarityStr.includes('史诗')) return 'epic';
            if (rarityStr.includes('稀有')) return 'rare';

            return 'common';
        }

        // ==================== 新数据管理功能 ====================

        // 右键菜单 - 录入主数据区
        document.getElementById('menu-record').addEventListener('click', async (e) => {
            e.stopPropagation();
            contextMenu.classList.remove('show');

            if (!currentContextItem) return;

            // 打开录入对话框
            document.getElementById('record-id').value = currentContextItem.id;
            document.getElementById('record-name-cn').value = '';
            document.getElementById('record-name-en').value = '';
            document.getElementById('record-type').value = '';
            document.getElementById('record-category').value = currentContextItem.data.folder_name || '';
            document.getElementById('record-rarity').value = '';  // 重置稀有度

            // 自动填充当前日期
            const now = new Date();
            const currentMonth = `${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}`;
            document.getElementById('record-date').value = currentMonth;

            recordModal.classList.add('show');
        });

        // 右键菜单 - 排除此项
        document.getElementById('menu-exclude').addEventListener('click', async (e) => {
            e.stopPropagation();
            contextMenu.classList.remove('show');

            if (!currentContextItem) return;

            if (!confirm(`确定要排除 "${currentContextItem.id}" 吗？\n排除后将不再显示在新数据列表中。`)) {
                return;
            }

            try {
                const response = await fetch('/api/new-data-config/exclude', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: currentContextItem.id})
                });

                if (response.ok) {
                    alert('已排除该项');
                    // 重新加载当前分类
                    if (currentCategory) {
                        loadCategoryData(currentCategory.split(' - ').pop(), currentData[0]?.csv_path || '');
                    }
                } else {
                    const error = await response.json();
                    alert('排除失败: ' + (error.error || '未知错误'));
                }
            } catch (error) {
                alert('排除失败: ' + error.message);
            }
        });

        // 对话框 - 关闭
        function closeRecordModal() {
            recordModal.classList.remove('show');
            currentContextItem = null;
        }

        document.getElementById('modalClose').addEventListener('click', closeRecordModal);
        document.getElementById('modalCancel').addEventListener('click', closeRecordModal);

        // 点击遮罩关闭对话框
        recordModal.addEventListener('click', (e) => {
            if (e.target === recordModal) {
                closeRecordModal();
            }
        });

        // 对话框 - 提交录入
        document.getElementById('modalSubmit').addEventListener('click', async () => {
            const id = document.getElementById('record-id').value;
            const nameCn = document.getElementById('record-name-cn').value.trim();
            const nameEn = document.getElementById('record-name-en').value.trim();
            const type = document.getElementById('record-type').value;
            const category = document.getElementById('record-category').value;
            const rarity = document.getElementById('record-rarity').value;
            const addedDate = document.getElementById('record-date').value.trim();

            // 验证必填字段
            if (!nameCn || !nameEn || !type || !addedDate) {
                alert('请填写所有必填字段！');
                return;
            }

            // 验证日期格式
            if (!/^\d{4}\.\d{1,2}$/.test(addedDate)) {
                alert('日期格式错误，应为: YYYY.MM (例如: 2025.10)');
                return;
            }

            try {
                const response = await fetch('/api/new-data-config/record', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        id: id,
                        name_cn: nameCn,
                        name_en: nameEn,
                        type: type,
                        category: category,
                        rarity: rarity,  // 添加稀有度
                        added_date: addedDate,
                        folder: currentContextItem?.data?.folder || ''
                    })
                });

                if (response.ok) {
                    alert('录入成功！');
                    closeRecordModal();

                    // 重新加载分类数据
                    loadCategories();
                } else {
                    const error = await response.json();
                    alert('录入失败: ' + (error.error || '未知错误'));
                }
            } catch (error) {
                alert('录入失败: ' + error.message);
            }
        });

        // 初始化
        loadCategories();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """首页"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/categories')
def get_categories():
    """获取分类列表"""
    categories = scan_csv_structure()
    return jsonify(categories)

@app.route('/api/items', methods=['POST'])
def get_items():
    """获取分类下的物品列表"""
    data = request.json
    csv_path = data.get('csv_path')
    category = data.get('category', '')

    # 特殊处理：新数据
    if csv_path and csv_path.startswith("__new_data__"):
        new_items_by_folder = scan_new_data()

        # 提取文件夹名称
        folder_name = csv_path.replace("__new_data__", "")

        if folder_name in new_items_by_folder:
            result = []
            for item in new_items_by_folder[folder_name]["items"]:
                result.append({
                    'id': item['id'],
                    'data': {
                        'name': item['id'],
                        'name_en': item['id'],
                        'folder_name': item['folder_name']  # 添加文件夹信息
                    },
                    'image_path': item['image_path'],
                    'has_image': True,
                    'is_new': True
                })
            return jsonify(result)
        else:
            return jsonify([])

    # 特殊处理：已录入数据
    if csv_path and csv_path.startswith("__recorded_data__"):
        config = load_new_data_config()
        recorded_items = config.get('recorded_items', [])

        # 提取月份
        month = csv_path.replace("__recorded_data__", "")

        # 过滤该月份的数据
        filtered_items = [item for item in recorded_items if item.get('added_date') == month]

        result = []
        for item in filtered_items:
            # 查找对应的图片
            image_path, has_image = check_image_exists(item['id'], item.get('category', ''))

            result.append({
                'id': item['id'],
                'data': {
                    'name': item.get('name_cn', item['id']),
                    'name_en': item.get('name_en', item['id']),
                    'typeString': item.get('type', ''),
                    'added_date': item.get('added_date', ''),
                    'rarityTypeString': item.get('rarity', '')  # 添加稀有度信息
                },
                'image_path': image_path,
                'has_image': has_image,
                'is_recorded': True  # 标记为已录入数据
            })

        return jsonify(result)

    # 正常处理CSV数据
    items = load_csv_data(csv_path)

    # 检查图片并构建结果
    result = []
    for item in items:
        item_id = item.get('id', '')
        if not item_id:
            continue

        image_path, has_image = check_image_exists(item_id, category)

        result.append({
            'id': item_id,
            'data': item,
            'image_path': image_path,
            'has_image': has_image
        })

    return jsonify(result)

@app.route('/image/<path:filepath>')
def serve_image(filepath):
    """提供图片文件"""
    try:
        file_path = BASE_DIR / filepath
        return send_from_directory(file_path.parent, file_path.name)
    except Exception as e:
        return str(e), 404

@app.route('/api/activity/<activity_type>/list', methods=['GET'])
def list_activities(activity_type):
    """获取某个活动类型下的所有活动ID列表"""
    try:
        activity_dir = BASE_DIR / "MW数据站爬虫" / "抽奖物品数据" / activity_type
        if not activity_dir.exists():
            return jsonify([])

        activity_ids = []
        for json_file in activity_dir.glob("*.json"):
            activity_ids.append(json_file.stem)

        # 按名称排序
        activity_ids.sort()
        return jsonify(activity_ids)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activity/<activity_type>/<activity_id>', methods=['GET'])
def get_activity(activity_type, activity_id):
    """加载活动JSON"""
    try:
        activity_dir = BASE_DIR / "MW数据站爬虫" / "抽奖物品数据" / activity_type
        activity_file = activity_dir / f"{activity_id}.json"

        if not activity_file.exists():
            return jsonify({'error': '活动不存在'}), 404

        with open(activity_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 为每个物品添加image_path（传递activity_id用于特殊货币）
        def add_image_paths(items):
            """为物品列表添加image_path"""
            for item in items:
                item_id = item.get('id', '')
                item_type = item.get('type', '')
                image_path = generate_item_image_path(item_id, item_type, activity_id)
                if image_path:
                    item['image_path'] = image_path

        # 根据活动类型处理
        if activity_type == 'chip':
            items = data.get('items', [])
            add_image_paths(items)
        elif activity_type == 'flagship':
            lootboxes = data.get('lootboxes', [])
            for lootbox in lootboxes:
                items = lootbox.get('items', [])
                add_image_paths(items)
        elif activity_type == 'cargo':
            cargos = data.get('cargos', [])
            for cargo in cargos:
                items = cargo.get('items', [])
                add_image_paths(items)

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activity/<activity_type>/<activity_id>', methods=['POST'])
def save_activity(activity_type, activity_id):
    """保存活动JSON"""
    try:
        data = request.json

        # 移除所有物品中的image_path字段（因为这是动态生成的）
        def remove_image_paths(items):
            """从物品列表中移除image_path字段"""
            for item in items:
                if 'image_path' in item:
                    del item['image_path']

        # 根据活动类型处理
        if activity_type == 'chip':
            items = data.get('items', [])
            remove_image_paths(items)
        elif activity_type == 'flagship':
            lootboxes = data.get('lootboxes', [])
            for lootbox in lootboxes:
                items = lootbox.get('items', [])
                remove_image_paths(items)
        elif activity_type == 'cargo':
            cargos = data.get('cargos', [])
            for cargo in cargos:
                items = cargo.get('items', [])
                remove_image_paths(items)

        activity_dir = BASE_DIR / "MW数据站爬虫" / "抽奖物品数据" / activity_type
        activity_dir.mkdir(parents=True, exist_ok=True)

        activity_file = activity_dir / f"{activity_id}.json"

        with open(activity_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 物品类型映射 API ====================

@app.route('/api/common-items', methods=['GET'])
def get_common_items():
    """获取所有资源和道具列表"""
    try:
        mappings = load_item_type_mappings()
        common_items = mappings.get('common_items', [])

        # 为每个物品添加图片路径
        for item in common_items:
            item_id = item['id']
            item_type = item['type']

            # 根据类型确定图片路径
            image_path = generate_item_image_path(item_id, item_type, None)
            if image_path:
                item['image_path'] = image_path

        return jsonify(common_items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== 新数据管理 API ====================

@app.route('/api/new-data-config', methods=['GET'])
def get_new_data_config():
    """获取新数据管理配置"""
    try:
        config = load_new_data_config()
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/new-data-config/exclude', methods=['POST'])
def add_excluded_item():
    """添加排除项"""
    try:
        data = request.json
        item_id = data.get('id')

        if not item_id:
            return jsonify({'error': '缺少ID'}), 400

        config = load_new_data_config()
        if item_id not in config['excluded_items']:
            config['excluded_items'].append(item_id)
            save_new_data_config(config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/new-data-config/exclude/<item_id>', methods=['DELETE'])
def remove_excluded_item(item_id):
    """移除排除项"""
    try:
        config = load_new_data_config()
        if item_id in config['excluded_items']:
            config['excluded_items'].remove(item_id)
            save_new_data_config(config)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/new-data-config/record', methods=['POST'])
def record_new_item():
    """录入新数据到主数据区"""
    try:
        data = request.json
        required_fields = ['id', 'name_cn', 'name_en', 'type', 'category', 'added_date']

        # 检查必填字段
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'缺少必填字段: {field}'}), 400

        config = load_new_data_config()

        # 检查是否已存在
        existing_ids = [item['id'] for item in config['recorded_items']]
        if data['id'] in existing_ids:
            return jsonify({'error': '该ID已经录入过'}), 400

        # 添加录入项
        recorded_item = {
            'id': data['id'],
            'name_cn': data['name_cn'],
            'name_en': data['name_en'],
            'type': data['type'],
            'category': data['category'],
            'added_date': data['added_date'],
            'folder': data.get('folder', ''),
            'rarity': data.get('rarity', '')  # 添加稀有度字段
        }

        config['recorded_items'].append(recorded_item)
        save_new_data_config(config)

        return jsonify({'success': True, 'item': recorded_item})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/new-data-config/recorded', methods=['GET'])
def get_recorded_items():
    """获取所有已录入数据"""
    try:
        config = load_new_data_config()
        return jsonify(config.get('recorded_items', []))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/new-data-config/recorded/by-month', methods=['GET'])
def get_recorded_items_by_month():
    """按月份获取已录入数据"""
    try:
        month = request.args.get('month')  # 格式: 2025.10
        config = load_new_data_config()
        recorded_items = config.get('recorded_items', [])

        if month:
            filtered_items = [item for item in recorded_items if item.get('added_date') == month]
            return jsonify(filtered_items)
        else:
            # 按月份分组
            by_month = {}
            for item in recorded_items:
                item_month = item.get('added_date', '未知')
                if item_month not in by_month:
                    by_month[item_month] = []
                by_month[item_month].append(item)

            return jsonify(by_month)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 70)
    print("现代战舰 - 数据资源比对工具")
    print("=" * 70)
    print(f"\n数据目录: {DATA_DIR}")
    print(f"图片目录: {IMAGE_DIR}")
    print("\n正在启动Web服务器...")
    print("请在浏览器中访问: http://127.0.0.1:5000")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 70)

    app.run(debug=True, host='127.0.0.1', port=5000)
