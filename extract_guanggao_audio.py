import UnityPy
import os
from pathlib import Path

# 路径配置
SOUNDS_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64\contentseparated_assets_sounds"
OUTPUT_PATH = r"MW资源\extracted_audio"

def extract_audio_bundle(bundle_path, output_dir):
    """提取bundle中的音频文件"""
    bundle_name = os.path.basename(bundle_path).replace('.wav.bundle', '').replace('.mp3.bundle', '').replace('.ogg.bundle', '').replace('.bundle', '')

    print(f"\n提取: {bundle_name}")

    try:
        env = UnityPy.load(str(bundle_path))
        extracted_count = 0

        for obj in env.objects:
            if obj.type.name == "AudioClip":
                try:
                    data = obj.read()

                    # 获取音频名称
                    audio_name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or bundle_name

                    # 保存音频
                    for name, audio_data in data.samples.items():
                        output_path = os.path.join(output_dir, f"{audio_name}.{name}")
                        with open(output_path, 'wb') as f:
                            f.write(audio_data)
                        extracted_count += 1
                        print(f"  + {audio_name}.{name}")

                except Exception as e:
                    print(f"  - Error: {e}")
                    continue

        return extracted_count > 0

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("音频提取工具 (Audio Extractor)")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent
    sounds_dir = base_dir / SOUNDS_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not sounds_dir.exists():
        print(f"ERROR: 找不到音频目录: {sounds_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # 查找所有音频bundle
    audio_bundles = []
    audio_bundles.extend(sounds_dir.glob("**/*.wav.bundle"))
    audio_bundles.extend(sounds_dir.glob("**/*.mp3.bundle"))
    audio_bundles.extend(sounds_dir.glob("**/*.ogg.bundle"))

    print(f"\n找到 {len(audio_bundles)} 个音频文件")
    print("\n开始提取...\n")

    successful = 0

    for bundle_path in sorted(audio_bundles):
        if extract_audio_bundle(str(bundle_path), str(output_dir)):
            successful += 1

    print("\n" + "=" * 60)
    print(f"提取完成!")
    print(f"成功: {successful}/{len(audio_bundles)} 个")
    print(f"保存位置: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
