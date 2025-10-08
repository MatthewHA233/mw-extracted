"""
深度反编译Lootbox动画数据
提取AnimationClip的详细信息：动画曲线、关键帧、属性变化等
"""
import UnityPy
import json
from pathlib import Path

def extract_animation_curves(animation_clip):
    """提取AnimationClip的曲线数据"""
    curves_data = {
        'name': getattr(animation_clip, 'name', None) or getattr(animation_clip, 'm_Name', None),
        'length': getattr(animation_clip, 'm_MuscleClipInfo', {}).get('m_StopTime', 0) - getattr(animation_clip, 'm_MuscleClipInfo', {}).get('m_StartTime', 0) if hasattr(animation_clip, 'm_MuscleClipInfo') else 0,
        'fps': getattr(animation_clip, 'm_SampleRate', 60),
        'legacy': getattr(animation_clip, 'm_Legacy', False),
        'curves': [],
        'float_curves': [],
        'pptr_curves': [],
        'events': []
    }

    # 提取浮点曲线（Float Curves）
    if hasattr(animation_clip, 'm_FloatCurves'):
        for curve in animation_clip.m_FloatCurves:
            curve_info = {
                'path': getattr(curve, 'path', ''),
                'attribute': getattr(curve, 'attribute', ''),
                'classID': getattr(curve, 'classID', 0),
                'script': str(getattr(curve, 'script', '')),
                'keyframes': []
            }

            # 提取关键帧
            if hasattr(curve, 'curve') and hasattr(curve.curve, 'm_Curve'):
                for keyframe in curve.curve.m_Curve:
                    curve_info['keyframes'].append({
                        'time': getattr(keyframe, 'time', 0),
                        'value': getattr(keyframe, 'value', 0),
                        'inSlope': getattr(keyframe, 'inSlope', 0),
                        'outSlope': getattr(keyframe, 'outSlope', 0),
                        'tangentMode': getattr(keyframe, 'tangentMode', 0),
                    })

            curves_data['float_curves'].append(curve_info)

    # 提取对象曲线（PPtrCurve - 用于sprite切换等）
    if hasattr(animation_clip, 'm_PPtrCurves'):
        for curve in animation_clip.m_PPtrCurves:
            curve_info = {
                'path': getattr(curve, 'path', ''),
                'attribute': getattr(curve, 'attribute', ''),
                'classID': getattr(curve, 'classID', 0),
                'keyframes': []
            }

            if hasattr(curve, 'curve'):
                for keyframe in curve.curve:
                    curve_info['keyframes'].append({
                        'time': getattr(keyframe, 'time', 0),
                        'value': str(getattr(keyframe, 'value', '')),
                    })

            curves_data['pptr_curves'].append(curve_info)

    # 提取事件
    if hasattr(animation_clip, 'm_Events'):
        for event in animation_clip.m_Events:
            curves_data['events'].append({
                'time': getattr(event, 'time', 0),
                'functionName': getattr(event, 'functionName', ''),
                'stringParameter': getattr(event, 'stringParameter', ''),
                'floatParameter': getattr(event, 'floatParameter', 0),
                'intParameter': getattr(event, 'intParameter', 0),
            })

    return curves_data


def decompile_lootbox_animation(bundle_path, output_dir):
    """反编译单个bundle的动画数据"""
    try:
        env = UnityPy.load(bundle_path)
        animations_data = []

        for obj in env.objects:
            if obj.type.name == "AnimationClip":
                try:
                    data = obj.read()
                    curves = extract_animation_curves(data)
                    animations_data.append(curves)

                    print(f"  [AnimationClip] {curves['name']}")
                    print(f"    长度: {curves['length']:.2f}s")
                    print(f"    帧率: {curves['fps']} fps")
                    print(f"    浮点曲线: {len(curves['float_curves'])} 条")
                    print(f"    对象曲线: {len(curves['pptr_curves'])} 条")
                    print(f"    事件: {len(curves['events'])} 个")

                    # 显示曲线详情
                    for fc in curves['float_curves']:
                        print(f"      -> {fc['path']} | {fc['attribute']} ({len(fc['keyframes'])} keyframes)")

                    print()

                except Exception as e:
                    print(f"  解析AnimationClip失败: {e}")
                    continue

        return animations_data

    except Exception as e:
        print(f"加载bundle失败: {e}")
        return []


def main():
    print("=" * 70)
    print("Lootbox 动画深度反编译工具")
    print("=" * 70)

    # 路径配置
    base_dir = Path(__file__).parent.parent
    game_data_path = base_dir / "Modern Warships_Data/StreamingAssets/aa/w64"

    # 重点分析la96的bundle
    target_bundles = [
        "contentseparated_assets_prefabs/effects/lootboxes/la96_premium.bundle",
        "contentseparated_assets_prefabs/effects/lootboxes/la96_common.bundle",
    ]

    output_dir = Path(__file__).parent / "lootbox_animation_curves"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n游戏目录: {game_data_path}")
    print(f"输出目录: {output_dir}\n")

    for bundle_rel_path in target_bundles:
        bundle_path = game_data_path / bundle_rel_path

        if not bundle_path.exists():
            print(f"[跳过] {bundle_rel_path} (文件不存在)\n")
            continue

        print("=" * 70)
        print(f"反编译: {bundle_rel_path}")
        print("=" * 70)

        animations_data = decompile_lootbox_animation(str(bundle_path), output_dir)

        if animations_data:
            # 保存为JSON
            bundle_name = Path(bundle_rel_path).stem
            json_path = output_dir / f"{bundle_name}_curves.json"

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(animations_data, f, indent=2, ensure_ascii=False)

            print(f"[1] 保存曲线数据: {json_path}\n")

    print("=" * 70)
    print("反编译完成！")
    print("=" * 70)
    print(f"输出目录: {output_dir}")
    print("\n现在你可以查看JSON文件了解每个动画的详细参数：")
    print("- 动画长度、帧率")
    print("- 每条曲线控制的对象路径和属性")
    print("- 关键帧的时间、数值、切线")
    print("- 动画事件（如音效触发时机）")


if __name__ == "__main__":
    main()
