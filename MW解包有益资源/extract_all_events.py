import UnityPy
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

# 路径配置
BASE_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64"

# 要搜索的目录配置
SEARCH_CONFIG = {
    # 活动资源
    "contentseparated_assets_offers": ["activity_gacha_", "eventgachaoffer_"],
    "contentseparated_assets_activities": ["activity_gacha_", "eventgachaoffer_", "lootbox_activity_"],
    "contentseparated_assets_camouflages": ["activity_gacha_", "eventgachaoffer_"],
    "contentseparated_assets_flags": ["activity_gacha_", "eventgachaoffer_"],
    # UI资源 - eventhub活动中心（在w64根目录）
    ".": ["contentseparated_assets_ui_eventhub_"],
    # UI资源 - sprites目录
    "contentseparated_assets_content/textures/sprites": [
        "currency.spriteatlas.bundle",
        "weapons.spriteatlas.bundle",
        "units_ships.spriteatlas.bundle",
        "avataricons.spriteatlas.bundle",
        "flags.spriteatlas.bundle",
        "titles.spriteatlas.bundle"
    ],
    # 迷彩资源
    "contentseparated_assets_content/textures/sprites/camouflages": [
        "camouflages.spriteatlas.bundle"
    ],
    # 宝箱券资源
    "contentseparated_assets_assets/content/textures/sprites": [
        "lootboxtickets.spriteatlas.bundle"
    ]
}

# activities.spriteatlas 中需要提取的activity_gacha资源
ACTIVITIES_SPRITEATLAS_PATH = "contentseparated_assets_content/textures/sprites/activities.spriteatlas.bundle"

def extract_bundle_task(args):
    """并行提取任务包装函数"""
    bundle_path, output_dir, is_spriteatlas, bundle_name, force_lowercase, is_eventhub = args

    try:
        env = UnityPy.load(bundle_path)
        extracted_count = 0
        skipped_count = 0

        for obj in env.objects:
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    data = obj.read()
                    if hasattr(data, 'image'):
                        img = data.image
                        img_name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or f"unnamed_{obj.path_id}"

                        # eventhub 特殊处理：提取 event_*_gacha* 和 event_*_background 资源
                        if is_eventhub:
                            if not img_name.startswith('event_'):
                                continue

                            # gacha 和 background 资源都输出到 eventhub 目录
                            if 'gacha' in img_name or 'background' in img_name.lower():
                                img_path = os.path.join(output_dir, f"{img_name}.png")
                            else:
                                continue
                        # spriteatlas 每个sprite单独保存
                        elif is_spriteatlas:
                            # 如果需要强制小写，转换文件名
                            if force_lowercase:
                                img_name = img_name.lower()

                            img_path = os.path.join(output_dir, f"{img_name}.png")
                        # 其他直接用包名
                        else:
                            img_path = os.path.join(output_dir, f"{bundle_name}.png")

                        # 检查文件是否已存在
                        if os.path.exists(img_path):
                            skipped_count += 1
                            continue

                        img.save(img_path)
                        extracted_count += 1
                except Exception as e:
                    continue

        return (bundle_name, extracted_count, skipped_count, None)

    except Exception as e:
        return (bundle_name, 0, 0, str(e))

def extract_activity_gacha_from_spriteatlas(spriteatlas_path, output_dir):
    """从activities.spriteatlas中提取所有活动相关资源"""
    try:
        env = UnityPy.load(str(spriteatlas_path))
        extracted_count = 0
        skipped_count = 0

        for obj in env.objects:
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)

                    # 提取所有活动相关的资源（activity开头或lootbox_activity开头）
                    if name and (name.lower().startswith('activity') or name.startswith('lootbox_activity')):
                        if hasattr(data, 'image'):
                            img = data.image
                            img_path = os.path.join(output_dir, f"{name}.png")

                            # 检查文件是否已存在
                            if os.path.exists(img_path):
                                skipped_count += 1
                                continue

                            img.save(img_path)
                            extracted_count += 1
                except:
                    continue

        return extracted_count, skipped_count

    except Exception as e:
        return 0, 0

def main():
    print("=" * 70)
    print("MW资源提取工具 - 活动+UI资源 (并行提取)")
    print("=" * 70)

    # 脚本在 MW解包有益资源/ 目录，游戏根目录在上上级
    base_dir = Path(__file__).parent.parent.parent
    base_path = base_dir / BASE_PATH
    output_base = Path(__file__).parent  # 输出到脚本同级目录

    if not base_path.exists():
        print(f"ERROR: 找不到游戏目录: {base_path}")
        return

    # 获取CPU核心数
    workers = cpu_count()
    print(f"\n游戏目录: {base_path}")
    print(f"输出目录: {output_base}")
    print(f"并行线程: {workers} 个\n")
    print("开始扫描...\n")

    # 收集所有提取任务
    tasks = []
    folder_info = {}  # 记录每个文件夹的信息

    for folder_name, patterns in SEARCH_CONFIG.items():
        folder_path = base_path / folder_name
        if not folder_path.exists():
            continue

        bundles = []
        is_spriteatlas = False

        # 检查是否是spriteatlas类型
        if any('.spriteatlas.bundle' in p for p in patterns):
            is_spriteatlas = True
            for pattern in patterns:
                bundle_file = folder_path / pattern
                if bundle_file.exists():
                    bundles.append(bundle_file)
        else:
            # 活动资源，按前缀查找
            for pattern in patterns:
                found_bundles = list(folder_path.glob(f"{pattern}*.bundle"))

                # 对于lootbox_activity，只保留widget和background
                if pattern == "lootbox_activity_":
                    found_bundles = [b for b in found_bundles if 'widget' in b.name or 'background' in b.name]

                bundles.extend(found_bundles)

        if not bundles:
            continue

        print(f"📁 {folder_name}: 找到 {len(bundles)} 个包文件")
        folder_info[folder_name] = len(bundles)

        # 创建输出目录（对eventhub使用专门的目录名）
        if folder_name == ".":
            output_dir = output_base / "contentseparated_assets_ui_eventhub"
        else:
            output_dir = output_base / folder_name
        os.makedirs(output_dir, exist_ok=True)

        # 添加任务
        for bundle_path in bundles:
            bundle_name = os.path.basename(bundle_path).replace('.bundle', '').replace('.png', '').replace('.spriteatlas', '')

            # 判断是否需要强制小写（针对 contentseparated_assets_assets/content/textures/sprites）
            force_lowercase = "contentseparated_assets_assets" in folder_name

            # 判断是否是eventhub资源
            is_eventhub = "eventhub_" in bundle_name

            if is_spriteatlas:
                bundle_output = output_dir / bundle_name
                os.makedirs(bundle_output, exist_ok=True)
                tasks.append((str(bundle_path), str(bundle_output), True, bundle_name, force_lowercase, False))
            elif is_eventhub:
                # eventhub资源提取gacha和background到同一目录
                tasks.append((str(bundle_path), str(output_dir), False, bundle_name, False, True))
            else:
                tasks.append((str(bundle_path), str(output_dir), False, bundle_name, force_lowercase, False))

    total_files = len(tasks)
    if total_files == 0:
        print("\n未找到任何资源")
        return

    print(f"\n{'=' * 70}")
    print(f"开始并行提取 {total_files} 个包...\n")

    # 并行提取
    completed = 0
    total_extracted = 0
    total_skipped = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(extract_bundle_task, task): task for task in tasks}

        for future in as_completed(futures):
            bundle_name, count, skipped, error = future.result()
            completed += 1

            if error:
                print(f"[{completed}/{total_files}] ✗ {bundle_name} - {error}")
            elif count > 0 or skipped > 0:
                status = f"✓ {bundle_name} (提取 {count} 张"
                if skipped > 0:
                    status += f", 跳过 {skipped} 张"
                status += ")"
                print(f"[{completed}/{total_files}] {status}")
                total_extracted += count
                total_skipped += skipped
            else:
                print(f"[{completed}/{total_files}] ✗ {bundle_name} (无内容)")

    # 特别处理：从activities.spriteatlas中提取所有活动资源
    print(f"\n{'=' * 70}")
    print("特别提取: activities.spriteatlas 中的所有活动资源")
    print("=" * 70)

    spriteatlas_path = base_path / ACTIVITIES_SPRITEATLAS_PATH
    if spriteatlas_path.exists():
        activities_output_dir = output_base / "contentseparated_assets_activities"
        os.makedirs(activities_output_dir, exist_ok=True)

        print(f"正在扫描: {spriteatlas_path.name}")
        activity_count, activity_skipped = extract_activity_gacha_from_spriteatlas(spriteatlas_path, str(activities_output_dir))

        if activity_count > 0 or activity_skipped > 0:
            status = f"✓ 提取了 {activity_count} 个活动资源"
            if activity_skipped > 0:
                status += f"，跳过 {activity_skipped} 个"
            print(status)
            total_extracted += activity_count
            total_skipped += activity_skipped
        else:
            print("✗ spriteatlas 中未找到活动资源")
    else:
        print(f"✗ 未找到: {ACTIVITIES_SPRITEATLAS_PATH}")

    # 统计
    print(f"\n{'=' * 70}")
    print(f"提取完成!")
    print(f"  新提取: {total_extracted} 个文件")
    print(f"  跳过: {total_skipped} 个文件（已存在）")
    print(f"保存位置: {output_base}")
    print("=" * 70)

if __name__ == "__main__":
    main()
