"""
分析已提取的lootbox资源
找出实际可用的动画资源：序列帧图片、精灵图集等
"""
import os
from pathlib import Path
import re

def analyze_extracted():
    """分析提取结果"""

    extracted_dir = Path(__file__).parent / "extracted_lootbox_animations"

    if not extracted_dir.exists():
        print("错误: 找不到提取目录")
        return

    print("=" * 70)
    print("分析 Lootbox 提取资源")
    print("=" * 70)
    print(f"分析目录: {extracted_dir}\n")

    # 统计
    stats = {
        'textures': [],      # 纹理图片
        'animations': [],    # 动画信息
        'audio': [],         # 音频
        'bundles': {}        # 按bundle分类
    }

    # 遍历所有bundle文件夹
    for bundle_dir in sorted(extracted_dir.iterdir()):
        if not bundle_dir.is_dir():
            continue

        bundle_name = bundle_dir.name
        stats['bundles'][bundle_name] = {
            'textures': [],
            'animations': [],
            'audio': [],
            'other': []
        }

        # 遍历bundle内的文件
        for file in bundle_dir.iterdir():
            if file.suffix == '.png':
                stats['textures'].append(str(file.relative_to(extracted_dir)))
                stats['bundles'][bundle_name]['textures'].append(file.name)
            elif file.suffix == '.wav':
                stats['audio'].append(str(file.relative_to(extracted_dir)))
                stats['bundles'][bundle_name]['audio'].append(file.name)
            elif '_animation_info_' in file.name:
                stats['animations'].append(str(file.relative_to(extracted_dir)))
                stats['bundles'][bundle_name]['animations'].append(file.name)
            else:
                stats['bundles'][bundle_name]['other'].append(file.name)

    # ============ 输出总体统计 ============
    print("=" * 70)
    print("总体统计")
    print("=" * 70)
    print(f"Bundle数量: {len(stats['bundles'])}")
    print(f"纹理图片: {len(stats['textures'])} 个")
    print(f"音频文件: {len(stats['audio'])} 个")
    print(f"动画信息: {len(stats['animations'])} 个\n")

    # ============ 找出有纹理的bundle（可能包含动画序列帧） ============
    print("=" * 70)
    print("重点: 包含纹理的Bundle（可能是动画序列帧）")
    print("=" * 70)

    texture_bundles = []
    for bundle_name, content in stats['bundles'].items():
        if content['textures']:
            texture_bundles.append({
                'name': bundle_name,
                'texture_count': len(content['textures']),
                'textures': content['textures']
            })

    # 按纹理数量排序
    texture_bundles.sort(key=lambda x: x['texture_count'], reverse=True)

    for i, bundle in enumerate(texture_bundles[:20], 1):  # 显示前20个
        print(f"\n{i}. {bundle['name']} ({bundle['texture_count']} 张图片)")
        for texture in bundle['textures'][:5]:  # 显示前5张
            print(f"   - {texture}")
        if len(bundle['textures']) > 5:
            print(f"   ... 还有 {len(bundle['textures']) - 5} 张")

    # ============ 找出关键的bundle ============
    print(f"\n{'=' * 70}")
    print("建议优先查看这些Bundle")
    print("=" * 70)

    priority_keywords = ['common', 'default', 'premium', 'flagship']
    priority_bundles = []

    for bundle_name, content in stats['bundles'].items():
        for keyword in priority_keywords:
            if keyword in bundle_name.lower():
                if content['textures'] or content['audio']:
                    priority_bundles.append({
                        'name': bundle_name,
                        'textures': len(content['textures']),
                        'audio': len(content['audio']),
                        'keyword': keyword
                    })
                    break

    for bundle in priority_bundles:
        print(f"\n✓ {bundle['name']}")
        print(f"  关键词: {bundle['keyword']}")
        print(f"  纹理: {bundle['textures']} 张, 音频: {bundle['audio']} 个")
        print(f"  路径: extracted_lootbox_animations/{bundle['name']}/")

    # ============ 生成详细报告 ============
    report_file = extracted_dir / "资源分析报告.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("Lootbox资源分析报告\n")
        f.write("=" * 70 + "\n\n")

        f.write("Unity动画说明:\n")
        f.write("-" * 70 + "\n")
        f.write("Unity的动画由以下部分组成:\n")
        f.write("1. AnimationClip - 动画数据（关键帧、曲线等）\n")
        f.write("2. Texture2D - 纹理图片（特效、粒子、UI元素）\n")
        f.write("3. AudioClip - 音效\n")
        f.write("4. GameObject/Prefab - 场景对象\n\n")

        f.write("本次提取的内容:\n")
        f.write("-" * 70 + "\n")
        f.write("- PNG文件: 特效纹理、粒子贴图、UI元素\n")
        f.write("- WAV文件: 开箱音效\n")
        f.write("- 动画信息文件: AnimationClip的元数据\n\n")

        f.write("如何使用这些资源:\n")
        f.write("-" * 70 + "\n")
        f.write("1. 纹理图片可以直接使用（PNG格式）\n")
        f.write("2. 音效可以直接播放（WAV格式）\n")
        f.write("3. 动画需要在Unity中重建，或者:\n")
        f.write("   - 如果有序列帧图片，可以组合成GIF/视频\n")
        f.write("   - 使用粒子特效图片制作特效动画\n\n")

        f.write("详细清单:\n")
        f.write("=" * 70 + "\n\n")

        for bundle_name, content in sorted(stats['bundles'].items()):
            f.write(f"Bundle: {bundle_name}\n")
            f.write("-" * 70 + "\n")

            if content['textures']:
                f.write(f"纹理 ({len(content['textures'])} 个):\n")
                for tex in content['textures']:
                    f.write(f"  - {tex}\n")

            if content['audio']:
                f.write(f"音频 ({len(content['audio'])} 个):\n")
                for aud in content['audio']:
                    f.write(f"  - {aud}\n")

            if content['animations']:
                f.write(f"动画 ({len(content['animations'])} 个):\n")
                for ani in content['animations']:
                    f.write(f"  - {ani}\n")

            f.write("\n")

    print(f"\n{'=' * 70}")
    print(f"详细报告已保存: {report_file}")
    print("=" * 70)

    # ============ 说明 ============
    print("\n" + "=" * 70)
    print("关于Unity动画的说明")
    print("=" * 70)
    print("""
Unity动画不是视频文件，而是由多个组件组成：

1. 【纹理图片】(PNG) - 可以直接使用
   - 特效纹理
   - 粒子贴图
   - UI元素

2. 【音效】(WAV) - 可以直接播放
   - 开箱音效
   - 背景音效

3. 【动画数据】(AnimationClip) - 需要Unity引擎
   - 控制对象的位置、旋转、缩放
   - 控制材质属性、透明度等
   - 需要配合Unity引擎才能播放

要获得完整的动画效果，通常需要：
a) 在Unity中加载这些资源并重建场景
b) 或者从游戏中录屏获取动画效果
c) 使用提取的纹理和音效自己制作动画

建议查看 'common' 和 'default' bundle中的PNG图片，
这些可能是开箱特效的关键资源！
    """)
    print("=" * 70)

if __name__ == "__main__":
    analyze_extracted()
