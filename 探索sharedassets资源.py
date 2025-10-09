"""
快速搜索 sharedassets 中包含 Background 的纹理
使用并行处理加速
"""
import UnityPy
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

# 配置
GAME_DATA_PATH = r"Modern Warships_Data"
OUTPUT_PATH = r"MW资源\sharedassets_backgrounds"

def extract_from_assets(args):
    """从assets文件中提取包含Background的纹理"""
    assets_path, output_dir = args

    try:
        env = UnityPy.load(str(assets_path))
        extracted = []

        for obj in env.objects:
            if obj.type.name == "Texture2D":
                try:
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)

                    # 只提取名称包含 Background 的纹理
                    if name and 'background' in name.lower():
                        if hasattr(data, 'image'):
                            img = data.image
                            width, height = img.size

                            # 保存图片
                            assets_name = Path(assets_path).stem
                            img_filename = f"{assets_name}_{name}_{width}x{height}.png"
                            img_path = os.path.join(output_dir, img_filename)

                            img.save(img_path)
                            extracted.append({
                                'name': name,
                                'width': width,
                                'height': height,
                                'source': assets_name,
                            })
                except Exception as e:
                    continue

        return (Path(assets_path).name, extracted, None)
    except Exception as e:
        return (Path(assets_path).name, [], str(e))

def main():
    print("=" * 70)
    print("快速搜索 Background 纹理（并行处理）")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent
    game_data = base_dir / GAME_DATA_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not game_data.exists():
        print(f"ERROR: 找不到游戏数据目录: {game_data}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # 查找所有 sharedassets 文件
    print(f"\n正在搜索 sharedassets 文件...")
    sharedassets_files = sorted(game_data.glob("sharedassets*.assets"))

    # 也检查 resources.assets
    resources_assets = game_data / "resources.assets"
    if resources_assets.exists():
        sharedassets_files.insert(0, resources_assets)

    print(f"找到 {len(sharedassets_files)} 个文件")

    # 并行处理
    workers = cpu_count()
    print(f"使用 {workers} 个并行进程\n")
    print(f"输出目录: {output_dir}\n")
    print("开始并行提取...\n")

    # 准备任务
    tasks = [(str(path), str(output_dir)) for path in sharedassets_files]

    total_extracted = 0
    completed = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(extract_from_assets, task): task for task in tasks}

        for future in as_completed(futures):
            task = futures[future]
            filename, extracted, error = future.result()
            completed += 1

            if error:
                print(f"[{completed}/{len(tasks)}] ✗ {filename} - {error}")
            elif extracted:
                print(f"[{completed}/{len(tasks)}] ✓ {filename}")
                for item in extracted:
                    print(f"    🎯 {item['name']} ({item['width']}x{item['height']})")
                    total_extracted += 1
            else:
                print(f"[{completed}/{len(tasks)}] - {filename} (无Background)")

    print("\n" + "=" * 70)
    print(f"提取完成!")
    print(f"共提取 {total_extracted} 张 Background 纹理")
    print(f"保存位置: {output_dir}")
    print("=" * 70)

if __name__ == "__main__":
    main()
