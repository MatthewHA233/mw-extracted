"""
探索UI背景图
提取所有可能是UI背景的大型PNG texture文件
"""
import UnityPy
import os
from pathlib import Path

# 配置
GAME_DATA_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64"
OUTPUT_PATH = r"MW资源\ui_backgrounds_探索"

# 搜索关键词（排除特定活动ID）
EXCLUDE_KEYWORDS = [
    'activity_gacha_', 'activity_c_', 'activity_sbs_',
    'bundle_e1_', 'bundle_e2_', 'bundle_b_',
    'eventgachaoffer_', 'achievement_',
    'camo_', 'flag_', 'ship_', 'weapon_'
]

INCLUDE_KEYWORDS = [
    'background', 'panel', 'ui', 'lootbox',
    'gacha', 'window', 'popup', 'menu'
]

def should_process(file_name):
    """判断文件是否应该被处理"""
    file_lower = file_name.lower()

    # 排除特定活动
    for exclude in EXCLUDE_KEYWORDS:
        if exclude in file_lower:
            return False

    # 包含关键词
    for include in INCLUDE_KEYWORDS:
        if include in file_lower:
            return True

    return False

def extract_texture(bundle_path, output_dir):
    """提取bundle中的纹理"""
    try:
        env = UnityPy.load(bundle_path)
        extracted = []

        for obj in env.objects:
            if obj.type.name == "Texture2D":
                data = obj.read()
                if hasattr(data, 'image'):
                    img = data.image
                    width, height = img.size

                    # 只提取较大的图片（可能是背景）
                    if width >= 512 or height >= 512:
                        name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)
                        if not name:
                            name = Path(bundle_path).stem

                        img_path = os.path.join(output_dir, f"{name}_{width}x{height}.png")
                        img.save(img_path)
                        extracted.append((name, width, height))

        return extracted
    except Exception as e:
        return []

def main():
    print("=" * 70)
    print("探索UI背景图")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent
    game_path = base_dir / GAME_DATA_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not game_path.exists():
        print(f"ERROR: 找不到游戏目录: {game_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"\n游戏目录: {game_path}")
    print(f"输出目录: {output_dir}\n")

    # 搜索所有可能的bundle文件
    print("正在扫描文件...")
    all_bundles = list(game_path.rglob("*.bundle"))

    candidates = []
    for bundle in all_bundles:
        if should_process(bundle.name):
            candidates.append(bundle)

    print(f"找到 {len(candidates)} 个候选文件\n")

    # 提取
    total_extracted = 0
    for i, bundle_path in enumerate(candidates, 1):
        print(f"[{i}/{len(candidates)}] {bundle_path.name}")
        extracted = extract_texture(str(bundle_path), str(output_dir))

        if extracted:
            for name, w, h in extracted:
                print(f"  ✓ {name} ({w}x{h})")
                total_extracted += 1
        else:
            print(f"  - 无大型纹理")

    print("\n" + "=" * 70)
    print(f"提取完成!")
    print(f"共提取 {total_extracted} 张图片")
    print(f"保存位置: {output_dir}")
    print("=" * 70)
    print("\n提示: 打开输出目录，逐个查看图片，找到宝箱界面背景")

if __name__ == "__main__":
    main()
