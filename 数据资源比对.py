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
}

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

    return all_ids

def scan_new_data():
    """扫描图片目录，找出CSV中不存在的新数据，按文件夹分类"""
    csv_ids = get_all_csv_ids()
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

        .item-card {
            background: rgba(30, 41, 59, 0.3);
            border: 2px solid #4b5563;
            border-radius: 0;
            padding: 4px;
            transition: all 0.3s;
            cursor: pointer;
            position: relative;
            overflow: hidden;
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
            background: rgba(0, 0, 0, 0.8);
            font-size: 11px;
            color: #fff;
            text-align: center;
            padding: 4px 2px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 5;
        }

        .item-card:hover .item-name {
            opacity: 1;
        }

        .item-id {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(0, 0, 0, 0.8);
            font-size: 9px;
            color: #bbb;
            text-align: center;
            padding: 3px 2px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 5;
        }

        .item-card:hover .item-id {
            opacity: 1;
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

    <script>
        let currentCategory = null;
        let currentData = [];
        let filteredData = [];
        let currentPage = 1;
        const itemsPerPage = 60; // 10列 x 6排

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
                    titleDiv.onclick = () => loadCategoryData(category.name, category.path);
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
                            loadCategoryData(sub.name, sub.path, sub.parent);
                        };
                        categoryDiv.appendChild(subDiv);
                    });
                }

                container.appendChild(categoryDiv);
            }
        }

        // 加载分类数据
        async function loadCategoryData(name, path, parent = null) {
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
            event.target.classList.add('active');
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
                }

                // 根据稀有度添加边框颜色
                const rarity = item.data.rarityTypeString || '';
                if (rarity.includes('传说')) card.classList.add('rarity-legendary');
                else if (rarity.includes('史诗')) card.classList.add('rarity-epic');
                else if (rarity.includes('稀有')) card.classList.add('rarity-rare');
                else if (!item.is_new) card.classList.add('rarity-common');  // 新数据不添加普通稀有度颜色

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
