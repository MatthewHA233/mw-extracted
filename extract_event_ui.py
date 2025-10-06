import UnityPy
import os
from pathlib import Path

# 活动UI路径
EVENT_UI_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64\contentseparated_assets_ui\eventhub"
OUTPUT_PATH = r"MW资源\extracted_events"

# 活动名称翻译（根据缩写推测）
EVENT_NAMES = {
    "lny24": "农历新年2024 (Lunar New Year)",
    "easteregghunt": "复活节寻蛋 (Easter Egg Hunt)",
    "birthdayparty": "生日派对 (Birthday Party)",
    "mwwg24": "冬季运动会2024 (MW Winter Games)",
    "al24": "周年庆典24 (Anniversary)",
    "bf25": "黑色星期五25 (Black Friday)",
    "bfe24": "黑色星期五活动24 (Black Friday Event)",
    "dbf": "双倍奖励 (Double Bonus)",
    "ds24": "龙舟24 (Dragon Ship)",
    "fd23": "父亲节23 (Father's Day)",
    "fp23": "愚人节23 (Fool's Prank)",
    "fp24": "愚人节24 (Fool's Prank)",
    "lfp25": "农历25 (Lunar Festival)",
    "mdc": "月中挑战 (Mid-Month Challenge)",
    "mf23": "五月节23 (May Festival)",
    "oe": "海洋探索 (Ocean Explorer)",
    "ph25": "菲律宾25 (Philippines)",
    "ps24": "海盗季节24 (Pirate Season)",
    "ps25": "海盗季节25 (Pirate Season)",
    "re1": "赛车活动1 (Racing Event 1)",
    "re2": "赛车活动2 (Racing Event 2)",
    "sj25": "夏季狂欢25 (Summer Jam)",
    "sp01": "特别活动01 (Special 01)",
    "sp02": "特别活动02 (Special 02)",
    "sp03": "特别活动03 (Special 03)",
    "sp04": "特别活动04 (Special 04)",
    "sp05": "特别活动05 (Special 05)",
    "sp06": "特别活动06 (Special 06)",
    "sph24": "超级英雄24 (Super Hero)",
    "tg25": "感恩节25 (Thanksgiving)",
    "wa25": "冬季突袭25 (Winter Assault)",
    "wd25": "冬季防御25 (Winter Defense)",
    "az24": "亚洲24 (Asia Zone)",
    "as02": "突击季节02 (Assault Season)",
    "be96": "战斗活动96 (Battle Event 96)",
    "be97": "战斗活动97 (Battle Event 97)",
    "me96id": "中东活动96印尼 (Middle East ID)",
    "me96tr": "中东活动96土耳其 (Middle East TR)",
    "me97de": "中东活动97德国 (Middle East DE)",
    "me97tr": "中东活动97土耳其 (Middle East TR)",
}

def extract_event_bundle(bundle_path, output_dir):
    """提取活动UI bundle"""
    bundle_name = os.path.basename(bundle_path).replace('.bundle', '')

    # 获取翻译名称
    display_name = EVENT_NAMES.get(bundle_name, bundle_name)
    folder_name = f"{bundle_name} - {EVENT_NAMES[bundle_name]}" if bundle_name in EVENT_NAMES else bundle_name

    print(f"\n提取活动: {display_name}")

    # 创建输出目录
    output_folder = os.path.join(output_dir, folder_name)
    os.makedirs(output_folder, exist_ok=True)

    try:
        env = UnityPy.load(bundle_path)
        extracted_count = 0

        for obj in env.objects:
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    data = obj.read()

                    if hasattr(data, 'image'):
                        img = data.image
                        img_name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or f"unnamed_{obj.path_id}"
                        img_path = os.path.join(output_folder, f"{img_name}.png")

                        img.save(img_path)
                        extracted_count += 1
                        print(f"  + {img_name}.png")

                except Exception as e:
                    continue

        print(f"完成! 提取 {extracted_count} 张图片")
        return extracted_count

    except Exception as e:
        print(f"ERROR: {e}")
        return 0

def main():
    print("=" * 60)
    print("月中活动 UI 提取工具")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent
    event_dir = base_dir / EVENT_UI_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not event_dir.exists():
        print(f"ERROR: 找不到活动目录: {event_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # 获取所有活动bundle
    event_bundles = list(event_dir.glob("*.bundle"))
    print(f"\n找到 {len(event_bundles)} 个活动UI包\n")

    total_extracted = 0

    for bundle_path in sorted(event_bundles):
        count = extract_event_bundle(str(bundle_path), str(output_dir))
        total_extracted += count

    print("\n" + "=" * 60)
    print(f"提取完成!")
    print(f"总共提取: {total_extracted} 张活动UI图片")
    print(f"保存位置: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
