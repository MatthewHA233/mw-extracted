import UnityPy
import os
from pathlib import Path

# 路径配置
BASE_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64"
OUTPUT_PATH = r"MW资源\extracted_ag97"

# 要搜索的目录
SEARCH_DIRS = [
    "contentseparated_assets_offers",
    "contentseparated_assets_activities",
    "contentseparated_assets_camouflages",
    "contentseparated_assets_flags",
]

def extract_bundle(bundle_path, output_dir, category=""):
    """提取bundle中的图片"""
    bundle_name = os.path.basename(bundle_path).replace('.png.bundle', '').replace('.bundle', '')

    # 根据类型添加中文后缀
    if category:
        final_name = f"{bundle_name} - {category}"
    else:
        final_name = bundle_name

    try:
        env = UnityPy.load(bundle_path)
        extracted = False

        for obj in env.objects:
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    data = obj.read()

                    if hasattr(data, 'image'):
                        img = data.image
                        img_name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or final_name
                        img_path = os.path.join(output_dir, f"{final_name}_{img_name}.png" if img_name != final_name else f"{final_name}.png")
                        img.save(img_path)
                        extracted = True

                except Exception as e:
                    continue

        return extracted

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("AG97活动资源提取工具 (AG97 Event Resources)")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent
    base_path = base_dir / BASE_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not base_path.exists():
        print(f"ERROR: 找不到游戏目录: {base_path}")
        return

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 收集所有包含 ag97 的 bundle
    all_bundles = []

    print("\n搜索 AG97 相关资源...")

    for search_dir in SEARCH_DIRS:
        dir_path = base_path / search_dir
        if dir_path.exists():
            # 查找所有包含 ag97 的文件
            bundles = list(dir_path.glob("*ag97*.bundle"))
            if bundles:
                print(f"\n在 {search_dir} 找到 {len(bundles)} 个文件")
                all_bundles.extend(bundles)

    if not all_bundles:
        print("\n未找到任何 AG97 相关资源")
        return

    print(f"\n总共找到 {len(all_bundles)} 个 AG97 相关文件")
    print("\n开始提取...\n")

    # 分类统计
    stats = {
        "背景": 0,
        "组件": 0,
        "缩略图": 0,
        "迷彩": 0,
        "旗帜": 0,
        "其他": 0
    }

    for bundle_path in sorted(all_bundles):
        name = bundle_path.stem.replace('.png', '')

        # 判断类型
        if 'background' in name:
            category = "背景"
        elif 'widget' in name:
            category = "组件"
        elif 'thumbnail' in name:
            category = "缩略图"
        elif 'camo' in name:
            category = "迷彩"
        elif 'flag' in name:
            category = "旗帜"
        else:
            category = "其他"

        print(f"[{category}] {name}")
        success = extract_bundle(str(bundle_path), str(output_dir), category)

        if success:
            print(f"  + Success")
            stats[category] += 1
        else:
            print(f"  - Failed")

    print("\n" + "=" * 60)
    print(f"提取完成!")
    for cat, count in stats.items():
        if count > 0:
            print(f"  {cat}: {count} 个")
    print(f"\n总计: {len(all_bundles)} 个文件")
    print(f"保存位置: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
