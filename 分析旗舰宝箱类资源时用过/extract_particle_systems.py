"""
提取ParticleSystem的详细配置
粒子系统配置包含了特效的核心参数
"""
import UnityPy
import json
from pathlib import Path

def extract_particle_system_config(ps_data):
    """提取单个粒子系统的配置"""
    config = {
        'duration': getattr(ps_data, 'lengthInSec', 0),
        'looping': getattr(ps_data, 'looping', False),
        'start_delay': getattr(ps_data, 'startDelay', 0),
        'start_lifetime': getattr(ps_data, 'startLifetime', 0),
        'start_speed': getattr(ps_data, 'startSpeed', 0),
        'start_size': getattr(ps_data, 'startSize', 0),
        'start_rotation': getattr(ps_data, 'startRotation', 0),
        'start_color': None,
        'gravity_modifier': getattr(ps_data, 'gravityModifier', 0),
        'simulation_space': getattr(ps_data, 'moveWithTransform', 0),
        'max_particles': getattr(ps_data, 'maxNumParticles', 0),
        'emission': {},
        'shape': {},
        'velocity_over_lifetime': {},
        'color_over_lifetime': {},
        'size_over_lifetime': {},
        'rotation_over_lifetime': {},
    }

    # StartColor
    if hasattr(ps_data, 'startColor'):
        try:
            color = ps_data.startColor
            if hasattr(color, 'r'):
                config['start_color'] = {
                    'r': getattr(color, 'r', 0),
                    'g': getattr(color, 'g', 0),
                    'b': getattr(color, 'b', 0),
                    'a': getattr(color, 'a', 0),
                }
        except:
            pass

    # Emission Module
    if hasattr(ps_data, 'EmissionModule'):
        em = ps_data.EmissionModule
        config['emission'] = {
            'enabled': getattr(em, 'enabled', False),
            'rate_over_time': getattr(em, 'rateOverTime', 0),
            'rate_over_distance': getattr(em, 'rateOverDistance', 0),
        }

    # Shape Module
    if hasattr(ps_data, 'ShapeModule'):
        shape = ps_data.ShapeModule
        config['shape'] = {
            'enabled': getattr(shape, 'enabled', False),
            'type': getattr(shape, 'type', 0),  # 0=Sphere, 1=Hemisphere, 2=Cone, 4=Box, 5=Mesh, etc.
            'radius': getattr(shape, 'radius', 0),
            'angle': getattr(shape, 'angle', 0),
            'randomDirectionAmount': getattr(shape, 'randomDirectionAmount', 0),
        }

    # Velocity Over Lifetime
    if hasattr(ps_data, 'VelocityModule'):
        vel = ps_data.VelocityModule
        config['velocity_over_lifetime'] = {
            'enabled': getattr(vel, 'enabled', False),
        }

    # Color Over Lifetime
    if hasattr(ps_data, 'ColorModule'):
        col = ps_data.ColorModule
        config['color_over_lifetime'] = {
            'enabled': getattr(col, 'enabled', False),
        }

    # Size Over Lifetime
    if hasattr(ps_data, 'SizeModule'):
        size = ps_data.SizeModule
        config['size_over_lifetime'] = {
            'enabled': getattr(size, 'enabled', False),
        }

    # Rotation Over Lifetime
    if hasattr(ps_data, 'RotationModule'):
        rot = ps_data.RotationModule
        config['rotation_over_lifetime'] = {
            'enabled': getattr(rot, 'enabled', False),
        }

    return config


def analyze_particle_systems(bundle_path):
    """分析bundle中的所有粒子系统"""
    try:
        env = UnityPy.load(bundle_path)

        particle_systems = []
        gameobject_map = {}  # PathID -> Name

        # 先收集所有GameObject
        for obj in env.objects:
            if obj.type.name == "GameObject":
                try:
                    data = obj.read()
                    name = getattr(data, 'name', None) or getattr(data, 'm_Name', None)
                    gameobject_map[obj.path_id] = name
                except:
                    pass

        # 提取粒子系统
        for obj in env.objects:
            if obj.type.name == "ParticleSystem":
                try:
                    data = obj.read()

                    # 尝试找到关联的GameObject
                    go_name = "Unknown"
                    if hasattr(data, 'm_GameObject'):
                        try:
                            go_path_id = data.m_GameObject.path_id
                            if go_path_id in gameobject_map:
                                go_name = gameobject_map[go_path_id]
                        except:
                            pass

                    ps_config = extract_particle_system_config(data)
                    ps_config['gameobject'] = go_name
                    ps_config['path_id'] = obj.path_id

                    particle_systems.append(ps_config)

                    print(f"  [ParticleSystem] {go_name}")
                    print(f"    Duration: {ps_config['duration']:.2f}s, Looping: {ps_config['looping']}")
                    print(f"    Max Particles: {ps_config['max_particles']}")
                    print(f"    Start Lifetime: {ps_config['start_lifetime']}")
                    print(f"    Start Speed: {ps_config['start_speed']}")
                    print(f"    Start Size: {ps_config['start_size']}")
                    if ps_config['start_color']:
                        print(f"    Start Color: RGBA({ps_config['start_color']['r']:.2f}, {ps_config['start_color']['g']:.2f}, {ps_config['start_color']['b']:.2f}, {ps_config['start_color']['a']:.2f})")
                    print(f"    Gravity: {ps_config['gravity_modifier']}")
                    print(f"    Emission: {ps_config['emission']}")
                    print(f"    Shape: {ps_config['shape']}")
                    print()

                except Exception as e:
                    print(f"  解析粒子系统失败: {e}")
                    continue

        return particle_systems

    except Exception as e:
        print(f"加载bundle失败: {e}")
        return []


def main():
    print("=" * 70)
    print("ParticleSystem 配置提取工具")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent
    game_data_path = base_dir / "Modern Warships_Data/StreamingAssets/aa/w64"

    target_bundles = [
        "contentseparated_assets_prefabs/effects/lootboxes/la96_premium.bundle",
    ]

    output_dir = Path(__file__).parent / "lootbox_particle_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    for bundle_rel_path in target_bundles:
        bundle_path = game_data_path / bundle_rel_path

        if not bundle_path.exists():
            print(f"\n[跳过] {bundle_rel_path}\n")
            continue

        print(f"\n分析: {bundle_rel_path}")
        print("=" * 70)

        particle_systems = analyze_particle_systems(str(bundle_path))

        if particle_systems:
            # 保存JSON
            bundle_name = Path(bundle_rel_path).stem
            json_path = output_dir / f"{bundle_name}_particles.json"

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(particle_systems, f, indent=2, ensure_ascii=False, default=str)

            print(f"[1] 详细数据已保存: {json_path}")
            print(f"[1] 共提取 {len(particle_systems)} 个粒子系统配置")

    print("\n" + "=" * 70)
    print("提取完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
