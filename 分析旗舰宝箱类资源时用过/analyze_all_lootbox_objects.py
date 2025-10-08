"""
分析Lootbox bundle中的所有对象类型
找出动画是如何实现的
"""
import UnityPy
import json
from pathlib import Path

def analyze_all_objects(bundle_path):
    """分析bundle中的所有对象"""
    try:
        env = UnityPy.load(bundle_path)

        objects_info = {
            'total': 0,
            'by_type': {},
            'gameobjects': [],
            'animators': [],
            'monobehaviours': [],
            'particle_systems': [],
        }

        for obj in env.objects:
            objects_info['total'] += 1
            obj_type = obj.type.name

            # 统计类型
            if obj_type not in objects_info['by_type']:
                objects_info['by_type'][obj_type] = 0
            objects_info['by_type'][obj_type] += 1

            try:
                data = obj.read()
                name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or f'Unnamed_{obj.path_id}'

                # GameObject - 场景结构
                if obj_type == "GameObject":
                    go_info = {
                        'name': name,
                        'path_id': obj.path_id,
                        'components': []
                    }

                    if hasattr(data, 'm_Component'):
                        for comp in data.m_Component:
                            try:
                                comp_obj = comp.get('component', comp).read()
                                comp_type = comp_obj.__class__.__name__
                                go_info['components'].append(comp_type)
                            except:
                                pass

                    objects_info['gameobjects'].append(go_info)

                # Animator - 动画控制器
                elif obj_type in ["Animator", "Animation"]:
                    animator_info = {
                        'name': name,
                        'type': obj_type,
                        'path_id': obj.path_id,
                        'controller': None,
                        'avatar': None,
                    }

                    if hasattr(data, 'm_Controller'):
                        try:
                            controller = data.m_Controller
                            if controller:
                                animator_info['controller'] = str(controller)
                        except:
                            pass

                    if hasattr(data, 'm_Avatar'):
                        try:
                            avatar = data.m_Avatar
                            if avatar:
                                animator_info['avatar'] = str(avatar)
                        except:
                            pass

                    objects_info['animators'].append(animator_info)

                # MonoBehaviour - 自定义脚本（可能包含动画逻辑）
                elif obj_type == "MonoBehaviour":
                    mb_info = {
                        'name': name,
                        'path_id': obj.path_id,
                        'm_Script': None,
                        'fields': []
                    }

                    if hasattr(data, 'm_Script'):
                        try:
                            script = data.m_Script.read()
                            script_name = getattr(script, 'name', None) or getattr(script, 'm_Name', None)
                            mb_info['m_Script'] = script_name
                        except:
                            pass

                    # 尝试读取所有字段
                    try:
                        type_tree = obj.read_typetree()
                        if isinstance(type_tree, dict):
                            mb_info['fields'] = list(type_tree.keys())
                    except:
                        pass

                    objects_info['monobehaviours'].append(mb_info)

                # ParticleSystem - 粒子系统
                elif obj_type == "ParticleSystem":
                    ps_info = {
                        'name': name,
                        'path_id': obj.path_id,
                    }
                    objects_info['particle_systems'].append(ps_info)

            except Exception as e:
                continue

        return objects_info

    except Exception as e:
        print(f"加载bundle失败: {e}")
        return None


def main():
    print("=" * 70)
    print("Lootbox Bundle 对象分析工具")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent
    game_data_path = base_dir / "Modern Warships_Data/StreamingAssets/aa/w64"

    target_bundles = [
        "contentseparated_assets_prefabs/effects/lootboxes/la96_premium.bundle",
    ]

    output_dir = Path(__file__).parent / "lootbox_object_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    for bundle_rel_path in target_bundles:
        bundle_path = game_data_path / bundle_rel_path

        if not bundle_path.exists():
            print(f"\n[跳过] {bundle_rel_path} (不存在)\n")
            continue

        print(f"\n分析: {bundle_rel_path}")
        print("=" * 70)

        objects_info = analyze_all_objects(str(bundle_path))

        if not objects_info:
            continue

        # 输出统计
        print(f"\n总对象数: {objects_info['total']}")
        print(f"\n对象类型分布:")
        for obj_type, count in sorted(objects_info['by_type'].items(), key=lambda x: -x[1]):
            print(f"  {obj_type}: {count}")

        # GameObject详情
        if objects_info['gameobjects']:
            print(f"\nGameObject ({len(objects_info['gameobjects'])} 个):")
            for go in objects_info['gameobjects']:
                print(f"  - {go['name']}")
                if go['components']:
                    print(f"    组件: {', '.join(go['components'])}")

        # Animator详情
        if objects_info['animators']:
            print(f"\nAnimator/Animation ({len(objects_info['animators'])} 个):")
            for anim in objects_info['animators']:
                print(f"  - {anim['name']} ({anim['type']})")
                if anim['controller']:
                    print(f"    Controller: {anim['controller']}")

        # MonoBehaviour详情
        if objects_info['monobehaviours']:
            print(f"\nMonoBehaviour ({len(objects_info['monobehaviours'])} 个):")
            for mb in objects_info['monobehaviours']:
                print(f"  - {mb['name']}")
                if mb['m_Script']:
                    print(f"    Script: {mb['m_Script']}")
                if mb['fields']:
                    print(f"    Fields: {', '.join(mb['fields'][:10])}")

        # ParticleSystem详情
        if objects_info['particle_systems']:
            print(f"\nParticleSystem ({len(objects_info['particle_systems'])} 个):")
            for ps in objects_info['particle_systems']:
                print(f"  - {ps['name']}")

        # 保存JSON
        bundle_name = Path(bundle_rel_path).stem
        json_path = output_dir / f"{bundle_name}_objects.json"

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(objects_info, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n详细数据已保存: {json_path}")

    print("\n" + "=" * 70)
    print("分析完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
