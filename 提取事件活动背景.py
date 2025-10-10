"""
提取事件活动背景图
从eventhub bundle中提取所有event_*_background资源
"""
import UnityPy
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

# 路径配置
GAME_DATA_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64"
OUTPUT_DIR = r"MW资源\事件活动背景"

def extract_backgrounds_from_bundle(bundle_path):
    """从单个bundle中提取背景图"""
    try:
        env = UnityPy.load(bundle_path)
        extracted = []
        bundle_name = Path(bundle_path).stem

        for obj in env.objects:
            if obj.type.name == "Texture2D":
                try:
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)

                    # 只提取包含background的资源
                    if name and 'background' in name.lower():
                        if hasattr(data, 'image'):
                            img = data.image
                            width, height = img.size
                            extracted.append((name, width, height, img))
                except:
                    continue

        return (bundle_name, extracted, None)

    except Exception as e:
        return (Path(bundle_path).stem, [], str(e))

def main():
    print("=" * 70)
    print("提取事件活动背景图")
    print("=" * 70)

    # 路径设置
    base_dir = Path(__file__).parent.parent
    game_path = base_dir / GAME_DATA_PATH
    output_dir = base_dir / OUTPUT_DIR

    if not game_path.exists():
        print(f"ERROR: 找不到游戏目录: {game_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n游戏目录: {game_path}")
    print(f"输出目录: {output_dir}\n")

    # 查找所有eventhub bundle文件
    print("正在扫描eventhub文件...")
    eventhub_bundles = list(game_path.glob("contentseparated_assets_ui_eventhub_*.bundle"))

    if not eventhub_bundles:
        print("未找到eventhub bundle文件")
        return

    print(f"找到 {len(eventhub_bundles)} 个eventhub文件\n")
    print("=" * 70)
    print("开始提取...\n")

    # 并行提取
    workers = cpu_count()
    total_extracted = 0
    total_skipped = 0
    completed = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(extract_backgrounds_from_bundle, str(bundle)): bundle for bundle in eventhub_bundles}

        for future in as_completed(futures):
            bundle_name, extracted, error = future.result()
            completed += 1

            if error:
                print(f"[{completed}/{len(eventhub_bundles)}] X {bundle_name} - {error}")
            elif extracted:
                print(f"[{completed}/{len(eventhub_bundles)}] ✓ {bundle_name}")

                for name, width, height, img in extracted:
                    img_path = output_dir / f"{name}_{width}x{height}.png"

                    # 检查文件是否已存在
                    if img_path.exists():
                        print(f"    - {name} ({width}x{height}) [已存在]")
                        total_skipped += 1
                    else:
                        img.save(str(img_path))
                        print(f"    ✓ {name} ({width}x{height})")
                        total_extracted += 1
            else:
                print(f"[{completed}/{len(eventhub_bundles)}] - {bundle_name} (无背景)")

    print("\n" + "=" * 70)
    print(f"提取完成!")
    print(f"  新提取: {total_extracted} 张背景图")
    print(f"  跳过: {total_skipped} 张（已存在）")
    print(f"保存位置: {output_dir}")
    print("=" * 70)

if __name__ == "__main__":
    main()
