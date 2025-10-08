"""
解包所有 lootbox_activity_ 前缀的 bundle 文件
"""
import UnityPy
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

# 路径配置
BASE_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64"
SEARCH_DIRS = [
    "contentseparated_assets_activities",
]

def extract_bundle_task(args):
    """并行提取任务"""
    bundle_path, output_dir, bundle_name = args

    try:
        env = UnityPy.load(bundle_path)
        extracted_count = 0

        for obj in env.objects:
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    data = obj.read()
                    if hasattr(data, 'image'):
                        img = data.image
                        img_path = os.path.join(output_dir, f"{bundle_name}.png")
                        img.save(img_path)
                        extracted_count += 1
                        break  # 只提取第一个图片
                except:
                    continue

        return (bundle_name, extracted_count, None)

    except Exception as e:
        return (bundle_name, 0, str(e))

def main():
    print("=" * 70)
    print("lootbox_activity 资源解包工具")
    print("=" * 70)

    # 路径设置
    base_dir = Path(__file__).parent.parent
    base_path = base_dir / BASE_PATH
    output_base = Path(__file__).parent / "lootbox_activity_解包结果"

    if not base_path.exists():
        print(f"ERROR: 找不到游戏目录: {base_path}")
        return

    # 创建输出目录
    os.makedirs(output_base, exist_ok=True)

    print(f"\n游戏目录: {base_path}")
    print(f"输出目录: {output_base}")
    print(f"并行线程: {cpu_count()} 个\n")
    print("开始扫描...\n")

    # 收集所有 lootbox_activity_ 前缀的bundle
    tasks = []
    total_found = 0

    for search_dir in SEARCH_DIRS:
        dir_path = base_path / search_dir
        if not dir_path.exists():
            continue

        # 查找所有 lootbox_activity_ 开头的bundle
        bundles = list(dir_path.glob("lootbox_activity_*.bundle"))

        if bundles:
            print(f"[{search_dir}] 找到 {len(bundles)} 个 lootbox_activity bundle")
            total_found += len(bundles)

            # 为每个bundle添加提取任务
            for bundle_path in bundles:
                bundle_name = os.path.basename(bundle_path).replace('.bundle', '')
                tasks.append((str(bundle_path), str(output_base), bundle_name))

    if not tasks:
        print("\n未找到任何 lootbox_activity bundle")
        return

    print(f"\n{'=' * 70}")
    print(f"开始并行提取 {len(tasks)} 个 bundle...\n")

    # 并行提取
    completed = 0
    total_extracted = 0
    workers = cpu_count()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(extract_bundle_task, task): task for task in tasks}

        for future in as_completed(futures):
            bundle_name, count, error = future.result()
            completed += 1

            if error:
                print(f"[{completed}/{len(tasks)}] [X] {bundle_name} - {error}")
            elif count > 0:
                print(f"[{completed}/{len(tasks)}] [OK] {bundle_name} ({count} 张)")
                total_extracted += 1
            else:
                print(f"[{completed}/{len(tasks)}] [X] {bundle_name} (无内容)")

    # 统计
    print(f"\n{'=' * 70}")
    print("提取完成!")
    print("=" * 70)
    print(f"成功: {total_extracted}/{len(tasks)} 个 bundle")
    print(f"保存位置: {output_base}")
    print("=" * 70)

if __name__ == "__main__":
    main()
