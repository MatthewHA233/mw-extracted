"""
提取Lootbox宝箱打开动画资源
重点提取：contentseparated_assets_prefabs/effects/lootboxes/ 下的所有资源
"""
import UnityPy
import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

def extract_bundle_task(args):
    """提取单个bundle中的所有资源"""
    bundle_path, output_dir, bundle_name = args

    try:
        env = UnityPy.load(bundle_path)
        extracted_files = []

        for obj in env.objects:
            try:
                obj_type = obj.type.name

                # 提取不同类型的资源
                if obj_type in ["Texture2D", "Sprite"]:
                    # 图片资源
                    data = obj.read()
                    if hasattr(data, 'image'):
                        img = data.image
                        name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or f"unnamed_{obj.path_id}"
                        img_path = output_dir / f"{name}.png"
                        img.save(img_path)
                        extracted_files.append(f"[Texture] {name}.png")

                elif obj_type == "TextAsset":
                    # 文本资源（可能包含配置）
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)
                    text_content = getattr(data, 'text', None) or getattr(data, 'm_Script', None)
                    if name and text_content:
                        text_path = output_dir / f"{name}.txt"
                        with open(text_path, 'w', encoding='utf-8') as f:
                            f.write(text_content)
                        extracted_files.append(f"[Text] {name}.txt")

                elif obj_type == "AudioClip":
                    # 音频资源
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)
                    if name:
                        # 尝试导出音频
                        try:
                            for audio_name, audio_data in data.samples.items():
                                audio_path = output_dir / f"{name}.wav"
                                with open(audio_path, 'wb') as f:
                                    f.write(audio_data)
                                extracted_files.append(f"[Audio] {name}.wav")
                                break
                        except:
                            pass

                elif obj_type in ["AnimationClip", "Animation"]:
                    # 动画资源（记录信息）
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)
                    if name:
                        # 保存动画信息
                        info_path = output_dir / f"_animation_info_{name}.txt"
                        with open(info_path, 'w', encoding='utf-8') as f:
                            f.write(f"Animation: {name}\n")
                            f.write(f"Type: {obj_type}\n")
                            f.write(f"Path ID: {obj.path_id}\n")
                            if hasattr(data, 'm_Length'):
                                f.write(f"Length: {data.m_Length}s\n")
                        extracted_files.append(f"[Animation] {name}")

                elif obj_type == "GameObject":
                    # GameObject（记录结构）
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)
                    if name and 'lootbox' in name.lower():
                        extracted_files.append(f"[GameObject] {name}")

            except Exception as e:
                continue

        return (bundle_name, len(extracted_files), extracted_files, None)

    except Exception as e:
        return (bundle_name, 0, [], str(e))


def main():
    print("=" * 70)
    print("Lootbox 宝箱打开动画提取工具")
    print("=" * 70)

    # 路径配置
    base_dir = Path(__file__).parent.parent
    game_data_path = base_dir / "Modern Warships_Data/StreamingAssets/aa/w64"
    output_base = Path(__file__).parent / "extracted_lootbox_animations"

    if not game_data_path.exists():
        print(f"\n错误: 找不到游戏目录: {game_data_path}")
        return

    # 创建输出目录
    output_base.mkdir(parents=True, exist_ok=True)

    print(f"\n游戏目录: {game_data_path}")
    print(f"输出目录: {output_base}\n")

    # 搜索lootboxes相关的bundle
    lootbox_bundles = []

    for root, dirs, files in os.walk(game_data_path):
        for file in files:
            if file.endswith('.bundle'):
                file_lower = file.lower()
                path_lower = root.lower()

                # 判断是否是lootbox相关的bundle
                is_lootbox = (
                    'lootbox' in file_lower or
                    'lootbox' in path_lower or
                    'container' in file_lower or
                    ('effects' in path_lower and 'lootbox' in path_lower)
                )

                if is_lootbox:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, game_data_path)
                    lootbox_bundles.append(full_path)

    print(f"找到 {len(lootbox_bundles)} 个lootbox相关bundle\n")

    if not lootbox_bundles:
        print("未找到任何lootbox相关资源")
        return

    # 收集提取任务
    tasks = []
    for bundle_path in lootbox_bundles:
        bundle_name = os.path.basename(bundle_path).replace('.bundle', '')
        # 为每个bundle创建单独的输出目录
        bundle_output_dir = output_base / bundle_name
        bundle_output_dir.mkdir(parents=True, exist_ok=True)

        tasks.append((bundle_path, bundle_output_dir, bundle_name))

    # 并行提取
    print("=" * 70)
    print(f"开始并行提取 {len(tasks)} 个bundle...\n")
    print("=" * 70)

    workers = cpu_count()
    completed = 0
    success_count = 0
    total_files = 0

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(extract_bundle_task, task): task for task in tasks}

        for future in as_completed(futures):
            bundle_name, file_count, extracted_files, error = future.result()
            completed += 1

            if error:
                print(f"[{completed}/{len(tasks)}] ✗ {bundle_name}")
                print(f"  错误: {error}")
            elif file_count > 0:
                print(f"[{completed}/{len(tasks)}] ✓ {bundle_name}")
                print(f"  提取了 {file_count} 个文件:")
                for extracted_file in extracted_files[:10]:  # 只显示前10个
                    print(f"    - {extracted_file}")
                if len(extracted_files) > 10:
                    print(f"    ... 还有 {len(extracted_files) - 10} 个文件")
                success_count += 1
                total_files += file_count
            else:
                print(f"[{completed}/{len(tasks)}] - {bundle_name} (无可提取内容)")

            print()

    # 统计
    print("=" * 70)
    print("提取完成!")
    print("=" * 70)
    print(f"成功: {success_count}/{len(tasks)} 个bundle")
    print(f"总共提取: {total_files} 个文件")
    print(f"保存位置: {output_base}")
    print("=" * 70)

    # 生成说明文件
    readme_path = output_base / "README.txt"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("Lootbox 宝箱打开动画资源\n")
        f.write("=" * 70 + "\n\n")
        f.write("提取内容说明:\n")
        f.write("  [Texture] - 图片资源（PNG格式）\n")
        f.write("  [Audio] - 音频资源（WAV格式）\n")
        f.write("  [Animation] - 动画信息（TXT格式，包含动画元数据）\n")
        f.write("  [GameObject] - 游戏对象（记录结构信息）\n")
        f.write("\n")
        f.write("重要文件夹:\n")
        f.write("  - common.bundle: 普通宝箱动画\n")
        f.write("  - default.bundle: 默认宝箱动画\n")
        f.write("  - *_premium.bundle: 高级宝箱动画\n")
        f.write("  - *_common.bundle: 活动普通宝箱动画\n")
        f.write("\n")
        f.write("使用说明:\n")
        f.write("  1. 每个bundle的资源在独立文件夹中\n")
        f.write("  2. PNG文件是纹理/特效图片\n")
        f.write("  3. WAV文件是开箱音效\n")
        f.write("  4. _animation_info_*.txt 包含动画信息\n")

    print(f"\n说明文件已生成: {readme_path}")


if __name__ == "__main__":
    main()
