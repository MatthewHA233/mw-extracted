import UnityPy
import os
from pathlib import Path

# 配置路径
GAME_DATA_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64\contentseparated_assets_content\textures\sprites"
OUTPUT_PATH = r"MW资源\extracted"

# 要提取的UI资源包及其中文名
UI_BUNDLES = {
    "units_ships.spriteatlas.bundle": "船只图标 (Ships)",
    "units_aircrafts.spriteatlas.bundle": "飞机图标 (Aircrafts)",
    "units_uniticons.spriteatlas.bundle": "单位图标 (Unit Icons)",
    "weapons.spriteatlas.bundle": "武器图标 (Weapons)",
    "consumables.spriteatlas.bundle": "消耗品图标 (Consumables)",
    "itemtypes.spriteatlas.bundle": "物品类型 (Item Types)",
    "itemclasstypes.spriteatlas.bundle": "物品等级类型 (Item Class Types)",
    "subsystemtypes.spriteatlas.bundle": "子系统类型 (Subsystem Types)",
    "subclasstypes.spriteatlas.bundle": "子等级类型 (Subclass Types)",
    "skins.spriteatlas.bundle": "皮肤 (Skins)",
    "camouflages.spriteatlas.bundle": "迷彩 (Camouflages)",
    "flags.spriteatlas.bundle": "旗帜 (Flags)",
    "avatars.spriteatlas.bundle": "头像 (Avatars)",
    "avataricons.spriteatlas.bundle": "头像图标 (Avatar Icons)",
    "currency.spriteatlas.bundle": "货币 (Currency)",
    "ranks.spriteatlas.bundle": "军衔 (Ranks)",
    "offers.spriteatlas.bundle": "优惠 (Offers)",
    "premiumshop.spriteatlas.bundle": "高级商店 (Premium Shop)",
    "activities.spriteatlas.bundle": "活动 (Activities)",
    "gacha.spriteatlas.bundle": "抽奖 (Gacha)",
    "eventpass.spriteatlas.bundle": "活动通行证 (Event Pass)",
    "mainmenu.spriteatlas.bundle": "主菜单 (Main Menu)",
    "titles.spriteatlas.bundle": "称号 (Titles)",
    "teamicons.spriteatlas.bundle": "队伍图标 (Team Icons)",
    "projectilemarkers.spriteatlas.bundle": "弹道标记 (Projectile Markers)",
    "playerraritytypes.spriteatlas.bundle": "玩家稀有度 (Player Rarity)",
    "dailymissiontypes.spriteatlas.bundle": "每日任务类型 (Daily Mission Types)",
    "clanflags.spriteatlas.bundle": "军团旗帜 (Clan Flags)",
}

def extract_bundle(bundle_path, output_dir):
    """提取单个bundle中的所有图片"""
    bundle_filename = os.path.basename(bundle_path)
    bundle_name = bundle_filename.replace('.spriteatlas.bundle', '')

    # 获取中文名
    chinese_name = UI_BUNDLES.get(bundle_filename, bundle_name)
    folder_name = f"{bundle_name} - {chinese_name}"

    print(f"\n正在处理: {chinese_name}")

    # 创建输出目录
    output_folder = os.path.join(output_dir, folder_name)
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

    # 提取每个bundle
    for bundle_filename in UI_BUNDLES.keys():
        bundle_path = sprites_dir / bundle_filename

        if not bundle_path.exists():
            print(f"\nSkip: {UI_BUNDLES[bundle_filename]} (not found)")
            continue

        count = extract_bundle(str(bundle_path), str(output_dir))
        if count > 0:
            successful_bundles += 1
            total_extracted += count

    print("\n" + "=" * 60)
    print(f"Extraction Complete!")
    print(f"Successful: {successful_bundles}/{len(UI_BUNDLES)} bundles")
    print(f"Total: {total_extracted} images")
    print(f"Location: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
