"""
搜索Flagship Container相关素材
重点查找：打开动画、UI素材、特效等
"""
import UnityPy
import os
from pathlib import Path
import re

def search_flagship_container():
    """搜索Flagship Container相关的所有资源"""

    # 脚本在 MW资源/ 目录，游戏根目录在上一级
    base_dir = Path(__file__).parent.parent
    game_data_path = base_dir / "Modern Warships_Data/StreamingAssets/aa/w64"

    if not game_data_path.exists():
        print(f"错误: 找不到游戏资源目录: {game_data_path}")
        return

    print("=" * 70)
    print("搜索 Flagship Container 相关素材")
    print("=" * 70)
    print(f"游戏目录: {game_data_path}\n")

    # 搜索关键词（多个变体）
    keywords = [
        'flagship',
        'container',
        'lootbox',
        'gacha',
        'open',
        'opening',
        'reward',
    ]

    results = {
        'files': [],           # 文件名匹配
        'bundles': {},         # bundle内容匹配
        'animations': [],      # 动画资源
    }

    # ============ 1. 搜索文件名 ============
    print("=" * 70)
    print("[步骤1] 搜索文件名中包含关键词的文件")
    print("=" * 70)

    for root, dirs, files in os.walk(game_data_path):
        for file in files:
            file_lower = file.lower()
            for keyword in keywords:
                if keyword in file_lower:
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, game_data_path)

                    if relative_path not in results['files']:
                        results['files'].append(relative_path)
                        print(f"  [文件] {relative_path}")
                    break

    print(f"\n找到 {len(results['files'])} 个相关文件\n")

    # ============ 2. 深度扫描bundle内容 ============
    print("=" * 70)
    print("[步骤2] 深度扫描bundle内容")
    print("=" * 70)
    print("提示: 这将扫描所有bundle文件，可能需要几分钟...\n")

    bundle_count = 0
    animation_types = [
        'Animation',
        'AnimationClip',
        'Animator',
        'AnimatorController',
        'AnimatorOverrideController',
        'RuntimeAnimatorController'
    ]

    for root, dirs, files in os.walk(game_data_path):
        for file in files:
            if file.endswith('.bundle'):
                bundle_count += 1
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, game_data_path)

                # 每100个bundle显示进度
                if bundle_count % 100 == 0:
                    print(f"  已扫描 {bundle_count} 个bundle...")

                try:
                    env = UnityPy.load(full_path)
                    bundle_matches = []

                    for obj in env.objects:
                        try:
                            obj_type = obj.type.name

                            # 检查是否是动画相关类型
                            is_animation = obj_type in animation_types

                            # 读取对象数据
                            data = obj.read()

                            # 获取对象名称
                            name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)

                            if name:
                                name_lower = name.lower()

                                # 检查名称是否包含关键词
                                for keyword in keywords:
                                    if keyword in name_lower:
                                        match_info = {
                                            'type': obj_type,
                                            'name': name,
                                            'is_animation': is_animation
                                        }

                                        if match_info not in bundle_matches:
                                            bundle_matches.append(match_info)
                                        break

                            # 特别关注：所有动画资源（即使名称不匹配）
                            elif is_animation:
                                # 尝试获取更多信息
                                if hasattr(data, 'm_GameObject'):
                                    try:
                                        go = data.m_GameObject.read()
                                        go_name = getattr(go, 'name', None) or getattr(go, 'm_Name', None)
                                        if go_name:
                                            go_lower = go_name.lower()
                                            for keyword in keywords:
                                                if keyword in go_lower:
                                                    match_info = {
                                                        'type': obj_type,
                                                        'name': f"[GameObject] {go_name}",
                                                        'is_animation': True
                                                    }
                                                    if match_info not in bundle_matches:
                                                        bundle_matches.append(match_info)
                                                    break
                                    except:
                                        pass

                        except:
                            continue

                    if bundle_matches:
                        results['bundles'][relative_path] = bundle_matches

                        print(f"\n  [BUNDLE] {relative_path}")
                        for match in bundle_matches:
                            icon = "[ANIM]" if match['is_animation'] else "[ASSET]"
                            print(f"     {icon} {match['type']}: {match['name']}")

                        # 如果有动画，单独记录
                        for match in bundle_matches:
                            if match['is_animation']:
                                results['animations'].append({
                                    'bundle': relative_path,
                                    'type': match['type'],
                                    'name': match['name']
                                })

                except Exception as e:
                    continue

    print(f"\n  总共扫描了 {bundle_count} 个bundle文件")

    # ============ 3. 汇总结果 ============
    print(f"\n{'=' * 70}")
    print("[汇总] Flagship Container 资源")
    print("=" * 70)

    print(f"\n文件名匹配: {len(results['files'])} 个")
    print(f"Bundle内容匹配: {len(results['bundles'])} 个")
    print(f"动画资源: {len(results['animations'])} 个")

    if results['animations']:
        print(f"\n{'=' * 70}")
        print("[重点] 动画资源详情")
        print("=" * 70)
        for i, anim in enumerate(results['animations'], 1):
            print(f"\n{i}. {anim['type']}: {anim['name']}")
            print(f"   位置: {anim['bundle']}")

    # ============ 4. 建议提取的文件 ============
    print(f"\n{'=' * 70}")
    print("[建议] 优先提取以下bundle")
    print("=" * 70)

    priority_bundles = []

    # 优先级1：包含动画的bundle
    for bundle_path in results['bundles'].keys():
        has_animation = any(m['is_animation'] for m in results['bundles'][bundle_path])
        if has_animation:
            priority_bundles.append((bundle_path, "包含动画"))

    # 优先级2：文件名直接包含flagship或container
    for file_path in results['files']:
        if 'flagship' in file_path.lower() or 'container' in file_path.lower():
            if file_path not in [p[0] for p in priority_bundles]:
                priority_bundles.append((file_path, "文件名明确"))

    if priority_bundles:
        for i, (bundle, reason) in enumerate(priority_bundles, 1):
            print(f"{i}. {bundle}")
            print(f"   原因: {reason}")
    else:
        print("未找到明确的相关资源")

    # ============ 5. 保存结果 ============
    output_file = Path(__file__).parent / "flagship_container_搜索结果.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Flagship Container 资源搜索结果\n")
        f.write("=" * 70 + "\n\n")

        f.write("文件名匹配:\n")
        f.write("-" * 70 + "\n")
        for file_path in results['files']:
            f.write(f"  {file_path}\n")

        f.write(f"\nBundle内容匹配:\n")
        f.write("-" * 70 + "\n")
        for bundle_path, matches in results['bundles'].items():
            f.write(f"\n[BUNDLE] {bundle_path}\n")
            for match in matches:
                icon = "[ANIM]" if match['is_animation'] else "[ASSET]"
                f.write(f"  {icon} {match['type']}: {match['name']}\n")

        f.write(f"\n动画资源汇总:\n")
        f.write("-" * 70 + "\n")
        for anim in results['animations']:
            f.write(f"\n{anim['type']}: {anim['name']}\n")
            f.write(f"  位置: {anim['bundle']}\n")

        f.write(f"\n优先提取建议:\n")
        f.write("-" * 70 + "\n")
        for bundle, reason in priority_bundles:
            f.write(f"  {bundle}\n")
            f.write(f"    原因: {reason}\n")

    print(f"\n{'=' * 70}")
    print(f"结果已保存到: {output_file}")
    print("=" * 70)

if __name__ == "__main__":
    search_flagship_container()
