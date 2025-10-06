import UnityPy
import os
from pathlib import Path

# 主资源文件路径
GAME_DATA_PATH = r"Modern Warships_Data"
OUTPUT_PATH = r"MW资源\extracted_main_audio"

def extract_audio_from_file(file_path, output_dir, keywords=None):
    """从资源文件中提取音频"""
    file_name = os.path.basename(file_path)
    print(f"\n正在扫描: {file_name}")

    try:
        env = UnityPy.load(str(file_path))
        audio_count = 0

        for obj in env.objects:
            if obj.type.name == "AudioClip":
                try:
                    data = obj.read()
                    audio_name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or f"audio_{obj.path_id}"

                    # 如果提供了关键词，只提取包含关键词的音频
                    if keywords:
                        if not any(keyword.lower() in audio_name.lower() for keyword in keywords):
                            continue

                    # 保存音频
                    for ext, audio_data in data.samples.items():
                        output_path = os.path.join(output_dir, f"{audio_name}.{ext}")

                        # 如果文件已存在，添加来源标记
                        if os.path.exists(output_path):
                            output_path = os.path.join(output_dir, f"{audio_name}_{file_name}.{ext}")

                        with open(output_path, 'wb') as f:
                            f.write(audio_data)
                        audio_count += 1
                        print(f"  + {audio_name}.{ext}")

                except Exception as e:
                    continue

        print(f"从 {file_name} 提取了 {audio_count} 个音频")
        return audio_count

    except Exception as e:
        print(f"  ERROR: {e}")
        return 0

def main():
    print("=" * 60)
    print("主资源音频提取工具 (Main Assets Audio Extractor)")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / GAME_DATA_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not data_dir.exists():
        print(f"ERROR: 找不到游戏数据目录: {data_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # 可能包含UI音效的关键词
    ui_keywords = [
        "ui", "button", "click", "open", "close", "reward",
        "loot", "box", "gacha", "roll", "spin", "reveal",
        "appear", "pop", "drop", "obtain", "get", "item",
        "prize", "unlock", "chest"
    ]

    print(f"\n搜索关键词: {', '.join(ui_keywords)}")

    # 要扫描的文件
    files_to_scan = [
        data_dir / "resources.assets",
        data_dir / "sharedassets0.assets",
        data_dir / "sharedassets1.assets",
        data_dir / "sharedassets2.assets",
    ]

    total_audio = 0

    for file_path in files_to_scan:
        if file_path.exists():
            count = extract_audio_from_file(file_path, str(output_dir), ui_keywords)
            total_audio += count

    print("\n" + "=" * 60)
    print(f"提取完成!")
    print(f"共提取 {total_audio} 个UI相关音频")
    print(f"保存位置: {output_dir}")
    print("=" * 60)

    if total_audio == 0:
        print("\n未找到匹配的音频，尝试提取所有音频...")
        print("请稍候，这可能需要几分钟...")

        # 提取所有音频（无关键词过滤）
        for file_path in files_to_scan:
            if file_path.exists():
                count = extract_audio_from_file(file_path, str(output_dir), keywords=None)
                total_audio += count

        print(f"\n提取了 {total_audio} 个音频文件")

if __name__ == "__main__":
    main()
