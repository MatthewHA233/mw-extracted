import UnityPy
import os
from pathlib import Path

# 配置路径
GAME_DATA_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64\contentseparated_assets_content\textures\sprites"
OUTPUT_PATH = r"MW资源\extracted"

# 要提取的UI资源包列表（实际存在的所有 spriteatlas.bundle 文件）
UI_BUNDLES = [
    "activities.spriteatlas.bundle",
    "avataricons.spriteatlas.bundle",
    "avatars.spriteatlas.bundle",
    "camouflages.spriteatlas.bundle",
    "clanflags.spriteatlas.bundle",
    "consumables.spriteatlas.bundle",
    "currency.spriteatlas.bundle",
    "dailymissiontypes.spriteatlas.bundle",
    "eventpass.spriteatlas.bundle",
    "fallbacknoalpha.spriteatlas.bundle",
    "flags.spriteatlas.bundle",
    "gacha.spriteatlas.bundle",
    "itemclasstypes.spriteatlas.bundle",
    "itemtypes.spriteatlas.bundle",
    "mainmenu.spriteatlas.bundle",
    "offers.spriteatlas.bundle",
    "playerraritytypes.spriteatlas.bundle",
    "premiumshop.spriteatlas.bundle",
    "projectilemarkers.spriteatlas.bundle",
    "ranks.spriteatlas.bundle",
    "skins.spriteatlas.bundle",
    "subclasstypes.spriteatlas.bundle",
    "subsystemtypes.spriteatlas.bundle",
    "teamicons.spriteatlas.bundle",
    "titles.spriteatlas.bundle",
    "units_aircrafts.spriteatlas.bundle",
    "units_ships.spriteatlas.bundle",
    "units_uniticons.spriteatlas.bundle",
    "weapons.spriteatlas.bundle",
]

def extract_bundle(bundle_path, output_dir):
    """提取单个bundle中的所有图片"""
    bundle_filename = os.path.basename(bundle_path)
    bundle_name = bundle_filename.replace('.spriteatlas.bundle', '')

    print(f"\nProcessing: {bundle_name}")

    # 创建输出目录（使用原名称）
    output_folder = os.path.join(output_dir, bundle_name)

    # 检查文件夹是否已存在
    if os.path.exists(output_folder):
        print(f"  Skip: Folder already exists")
        return -1  # 返回-1表示跳过

    os.makedirs(output_folder, exist_ok=True)

    try:
        # 加载bundle
        env = UnityPy.load(bundle_path)

        extracted_count = 0

        # 遍历所有对象
        for obj in env.objects:
            # 只处理 Texture2D 和 Sprite
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    data = obj.read()

                    # 获取图片
                    if hasattr(data, 'image'):
                        img = data.image

                        # 保存为PNG
                        img_name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or f"unnamed_{obj.path_id}"
                        img_path = os.path.join(output_folder, f"{img_name}.png")

                        img.save(img_path)
                        extracted_count += 1
                        print(f"  + {img_name}.png")

                except Exception as e:
                    print(f"  - Skip: {e}")
                    continue

        print(f"Done! Extracted {extracted_count} images to: {output_folder}")
        return extracted_count

    except Exception as e:
        print(f"ERROR: {e}")
        return 0

def main():
    print("=" * 60)
    print("Modern Warships UI Extractor")
    print("=" * 60)

    # 获取脚本所在目录（应该是游戏根目录）
    base_dir = Path(__file__).parent.parent
    sprites_dir = base_dir / GAME_DATA_PATH
    output_dir = base_dir / OUTPUT_PATH

    print(f"\nSource: {sprites_dir}")
    print(f"Output: {output_dir}")

    if not sprites_dir.exists():
        print(f"\nERROR: Cannot find resource directory: {sprites_dir}")
        return

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    total_extracted = 0
    successful_bundles = 0
    skipped_bundles = 0

    # 提取每个bundle
    for bundle_filename in UI_BUNDLES:
        bundle_path = sprites_dir / bundle_filename

        if not bundle_path.exists():
            print(f"\nSkip: {bundle_filename} (not found)")
            continue

        count = extract_bundle(str(bundle_path), str(output_dir))
        if count == -1:
            skipped_bundles += 1
        elif count > 0:
            successful_bundles += 1
            total_extracted += count

    print("\n" + "=" * 60)
    print(f"Extraction Complete!")
    print(f"Successful: {successful_bundles} bundles")
    print(f"Skipped: {skipped_bundles} bundles (already exist)")
    print(f"Total: {total_extracted} images")
    print(f"Location: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
