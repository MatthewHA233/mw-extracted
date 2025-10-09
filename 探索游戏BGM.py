"""
探索并提取《现代战舰》游戏BGM
主要提取主界面音乐和其他重要BGM
"""

import os
import UnityPy
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 游戏音乐资源路径
GAME_MUSIC_PATH = Path(r"../Modern Warships_Data/StreamingAssets/aa/w64/contentseparated_assets_music")

# 输出目录
OUTPUT_DIR = Path("bgm_探索")

# 重点关注的主界面音乐
MAIN_MENU_MUSIC = [
    "modernwarships_main_theme_ost.bundle",                    # 当前主题曲
    "modernwarships_main_theme_orchestral_ost.bundle",          # 管弦乐版主题曲
    "modernwarships_main_theme_old_ost.bundle",                 # 旧版主题曲
    "klepacki/modernwarships_maintheme_02_ost.bundle",          # Klepacki版主题曲
    "klepacki/modernwarships_customizetheme_01_ost.bundle",     # 自定义界面主题
    "klepacki/modernwarships_customizetheme_02_ost.bundle",     # 自定义界面主题2
    "modernwarships_menu_halloween_ost.bundle",                 # 万圣节菜单
    "modernwarships_menu_halloween2025_ost.bundle",             # 万圣节2025菜单
    "modernwarships_menu_parade_ost.bundle",                    # 阅兵菜单
]

# 其他分类
BATTLE_MUSIC = [
    "klepacki/modernwarships_attacktheme_01_ost.bundle",
    "klepacki/modernwarships_attacktheme_02_ost.bundle",
    "klepacki/modernwarships_attacktheme_03_ost.bundle",
    "klepacki/modernwarships_setpositiontheme_02_ost.bundle",
    "klepacki/modernwarships_scorescreentheme_01_ost.bundle",
]

def extract_audio_from_bundle(bundle_path, output_dir, category):
    """从bundle中提取音频文件"""
    bundle_name = bundle_path.stem

    try:
        env = UnityPy.load(str(bundle_path))
        extracted = []

        for obj in env.objects:
            if obj.type.name == "AudioClip":
                try:
                    data = obj.read()

                    # 获取音频名称
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or bundle_name

                    # 尝试导出音频
                    # UnityPy的AudioClip可能有samples属性
                    if hasattr(data, 'samples'):
                        # 创建分类输出目录
                        category_dir = output_dir / category
                        os.makedirs(category_dir, exist_ok=True)

                        # 保存音频文件
                        output_path = category_dir / f"{name}.wav"

                        # 检查文件是否已存在
                        if output_path.exists():
                            extracted.append((name, "skipped"))
                            continue

                        # 导出音频数据
                        for audio_name, audio_data in data.samples.items():
                            with open(output_path, 'wb') as f:
                                f.write(audio_data)
                            extracted.append((name, str(output_path)))
                            break

                except Exception as e:
                    continue

        return (bundle_name, extracted, None)

    except Exception as e:
        return (bundle_name, [], str(e))

def scan_all_music_files():
    """扫描所有音乐文件"""
    music_files = []

    if not GAME_MUSIC_PATH.exists():
        print(f"❌ 音乐路径不存在: {GAME_MUSIC_PATH}")
        return music_files

    # 递归查找所有.bundle文件
    for bundle_file in GAME_MUSIC_PATH.rglob("*.bundle"):
        # 获取相对路径
        relative_path = bundle_file.relative_to(GAME_MUSIC_PATH)
        music_files.append((str(relative_path), bundle_file))

    return music_files

def main():
    print("=" * 70)
    print("《现代战舰》游戏BGM提取工具")
    print("=" * 70)

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 扫描所有音乐文件
    print("\n[*] 正在扫描音乐文件...")
    all_music = scan_all_music_files()

    if not all_music:
        print("[X] 未找到任何音乐文件")
        return

    print(f"[OK] 找到 {len(all_music)} 个音乐文件")

    # 分类音乐文件
    tasks = []

    print("\n[*] 分类音乐文件:")

    # 主界面音乐（高优先级）
    main_menu_count = 0
    for relative_path, bundle_path in all_music:
        if relative_path in MAIN_MENU_MUSIC:
            tasks.append((bundle_path, OUTPUT_DIR, "主界面音乐"))
            main_menu_count += 1
    print(f"  ├─ 主界面音乐: {main_menu_count} 个")

    # 战斗音乐
    battle_count = 0
    for relative_path, bundle_path in all_music:
        if relative_path in BATTLE_MUSIC:
            tasks.append((bundle_path, OUTPUT_DIR, "战斗音乐"))
            battle_count += 1
    print(f"  ├─ 战斗音乐: {battle_count} 个")

    # 地图BGM
    map_count = 0
    for relative_path, bundle_path in all_music:
        if (relative_path not in MAIN_MENU_MUSIC and
            relative_path not in BATTLE_MUSIC and
            "klepacki" not in relative_path):
            tasks.append((bundle_path, OUTPUT_DIR, "地图BGM"))
            map_count += 1
    print(f"  └─ 地图BGM: {map_count} 个")

    if not tasks:
        print("\n[X] 没有需要提取的音乐文件")
        return

    print(f"\n[*] 开始提取 {len(tasks)} 个音乐文件...")
    print(f"使用线程数: 4")

    # 并行提取
    completed = 0
    total_extracted = 0
    total_skipped = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(extract_audio_from_bundle, bundle, output, cat): (bundle, cat)
            for bundle, output, cat in tasks
        }

        for future in as_completed(futures):
            bundle_path, category = futures[future]
            bundle_name, extracted, error = future.result()
            completed += 1

            if error:
                print(f"[{completed}/{len(tasks)}] [X] {category}/{bundle_name} - {error}")
                failed += 1
            elif extracted:
                extracted_count = sum(1 for _, status in extracted if status != "skipped")
                skipped_count = sum(1 for _, status in extracted if status == "skipped")

                if extracted_count > 0 or skipped_count > 0:
                    status_str = f"[OK] {category}/{bundle_name}"
                    if extracted_count > 0:
                        status_str += f" (提取 {extracted_count} 个"
                        if skipped_count > 0:
                            status_str += f", 跳过 {skipped_count} 个"
                        status_str += ")"
                    else:
                        status_str += f" (跳过 {skipped_count} 个)"

                    print(f"[{completed}/{len(tasks)}] {status_str}")
                    total_extracted += extracted_count
                    total_skipped += skipped_count

                    # 显示提取的文件
                    for name, path in extracted:
                        if path != "skipped":
                            print(f"    -> {name}")
            else:
                print(f"[{completed}/{len(tasks)}] [!] {category}/{bundle_name} (无AudioClip)")

    # 统计
    print(f"\n{'=' * 70}")
    print(f"提取完成!")
    print(f"  成功提取: {total_extracted} 个音频文件")
    print(f"  跳过: {total_skipped} 个（已存在）")
    print(f"  失败: {failed} 个")
    print(f"保存位置: {OUTPUT_DIR.absolute()}")
    print("=" * 70)

    # 列出主界面音乐
    main_menu_dir = OUTPUT_DIR / "主界面音乐"
    if main_menu_dir.exists():
        music_files = list(main_menu_dir.glob("*.wav"))
        if music_files:
            print(f"\n[*] 主界面音乐文件:")
            for music_file in music_files:
                size_mb = music_file.stat().st_size / (1024 * 1024)
                print(f"  - {music_file.name} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    main()
