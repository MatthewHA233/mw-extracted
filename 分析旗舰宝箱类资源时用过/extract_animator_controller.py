"""
提取AnimatorController的状态机数据
这是Unity动画的核心控制逻辑
"""
import UnityPy
import json
from pathlib import Path

def extract_animator_controller(bundle_path):
    """提取Animator Controller的状态机"""
    try:
        env = UnityPy.load(bundle_path)

        controller_data = None

        for obj in env.objects:
            if obj.type.name == "AnimatorController":
                try:
                    data = obj.read()
                    controller_data = {
                        'name': getattr(data, 'name', None) or getattr(data, 'm_Name', None),
                        'path_id': obj.path_id,
                        'layers': [],
                        'parameters': [],
                    }

                    # 提取参数
                    if hasattr(data, 'm_AnimatorParameters'):
                        for param in data.m_AnimatorParameters:
                            param_info = {
                                'name': getattr(param, 'm_Name', ''),
                                'type': getattr(param, 'm_Type', 0),  # 1=Float, 3=Int, 4=Bool, 9=Trigger
                                'default': getattr(param, 'm_DefaultFloat', 0) if hasattr(param, 'm_DefaultFloat') else getattr(param, 'm_DefaultInt', 0) if hasattr(param, 'm_DefaultInt') else getattr(param, 'm_DefaultBool', False),
                            }
                            controller_data['parameters'].append(param_info)

                    # 提取层
                    if hasattr(data, 'm_AnimatorLayers'):
                        for layer in data.m_AnimatorLayers:
                            layer_info = {
                                'name': getattr(layer, 'm_Name', ''),
                                'default_weight': getattr(layer, 'm_DefaultWeight', 1.0),
                                'state_machine': None,
                            }

                            # 提取状态机
                            if hasattr(layer, 'm_StateMachine'):
                                try:
                                    sm = layer.m_StateMachine.read()
                                    sm_info = {
                                        'name': getattr(sm, 'name', '') or getattr(sm, 'm_Name', ''),
                                        'states': [],
                                        'transitions': [],
                                        'entry_transitions': [],
                                        'default_state': None,
                                    }

                                    # 默认状态
                                    if hasattr(sm, 'm_DefaultState'):
                                        try:
                                            default_state = sm.m_DefaultState.read()
                                            sm_info['default_state'] = getattr(default_state, 'name', '') or getattr(default_state, 'm_Name', '')
                                        except:
                                            pass

                                    # 提取状态
                                    if hasattr(sm, 'm_ChildStates'):
                                        for child_state in sm.m_ChildStates:
                                            try:
                                                state = child_state.m_State.read()
                                                state_info = {
                                                    'name': getattr(state, 'name', '') or getattr(state, 'm_Name', ''),
                                                    'speed': getattr(state, 'm_Speed', 1.0),
                                                    'cycle_offset': getattr(state, 'm_CycleOffset', 0.0),
                                                    'motion': None,
                                                    'transitions': [],
                                                }

                                                # Motion (AnimationClip)
                                                if hasattr(state, 'm_Motion'):
                                                    try:
                                                        motion = state.m_Motion.read()
                                                        state_info['motion'] = getattr(motion, 'name', '') or getattr(motion, 'm_Name', '')
                                                    except:
                                                        pass

                                                # 状态转换
                                                if hasattr(state, 'm_Transitions'):
                                                    for trans in state.m_Transitions:
                                                        try:
                                                            trans_data = trans.read()
                                                            trans_info = {
                                                                'destination': None,
                                                                'duration': getattr(trans_data, 'm_TransitionDuration', 0),
                                                                'offset': getattr(trans_data, 'm_TransitionOffset', 0),
                                                                'exit_time': getattr(trans_data, 'm_ExitTime', 0),
                                                                'has_exit_time': getattr(trans_data, 'm_HasExitTime', False),
                                                                'has_fixed_duration': getattr(trans_data, 'm_HasFixedDuration', True),
                                                                'conditions': [],
                                                            }

                                                            # 目标状态
                                                            if hasattr(trans_data, 'm_DstState'):
                                                                try:
                                                                    dst_state = trans_data.m_DstState.read()
                                                                    trans_info['destination'] = getattr(dst_state, 'name', '') or getattr(dst_state, 'm_Name', '')
                                                                except:
                                                                    pass

                                                            # 条件
                                                            if hasattr(trans_data, 'm_Conditions'):
                                                                for cond in trans_data.m_Conditions:
                                                                    cond_info = {
                                                                        'mode': getattr(cond, 'm_ConditionMode', 0),  # 1=If, 2=IfNot, 3=Greater, 4=Less, 5=Equals, 6=NotEqual
                                                                        'parameter': getattr(cond, 'm_ConditionEvent', ''),
                                                                        'threshold': getattr(cond, 'm_EventTreshold', 0),
                                                                    }
                                                                    trans_info['conditions'].append(cond_info)

                                                            state_info['transitions'].append(trans_info)
                                                        except:
                                                            continue

                                                sm_info['states'].append(state_info)
                                            except:
                                                continue

                                    layer_info['state_machine'] = sm_info
                                except Exception as e:
                                    print(f"    提取状态机失败: {e}")

                            controller_data['layers'].append(layer_info)

                    print(f"\n[AnimatorController] {controller_data['name']}")
                    print(f"  参数: {len(controller_data['parameters'])} 个")
                    for param in controller_data['parameters']:
                        type_name = ['Float', 'Int', 'Bool', 'Trigger'][param['type'] - 1] if 1 <= param['type'] <= 4 else 'Unknown'
                        print(f"    - {param['name']} ({type_name}) = {param['default']}")

                    print(f"  层: {len(controller_data['layers'])} 个")
                    for layer in controller_data['layers']:
                        print(f"    [{layer['name']}]")
                        if layer['state_machine']:
                            sm = layer['state_machine']
                            print(f"      默认状态: {sm['default_state']}")
                            print(f"      状态数量: {len(sm['states'])}")
                            for state in sm['states']:
                                print(f"        -> {state['name']}")
                                print(f"           Motion: {state['motion']}")
                                print(f"           Speed: {state['speed']}")
                                if state['transitions']:
                                    for trans in state['transitions']:
                                        print(f"           => {trans['destination']} (exit_time={trans['exit_time']}, duration={trans['duration']})")
                                        for cond in trans['conditions']:
                                            print(f"              条件: {cond}")

                    break

                except Exception as e:
                    print(f"解析AnimatorController失败: {e}")
                    import traceback
                    traceback.print_exc()

        return controller_data

    except Exception as e:
        print(f"加载bundle失败: {e}")
        return None


def main():
    print("=" * 70)
    print("AnimatorController 状态机提取工具")
    print("=" * 70)

    base_dir = Path(__file__).parent.parent
    game_data_path = base_dir / "Modern Warships_Data/StreamingAssets/aa/w64"

    target_bundles = [
        "contentseparated_assets_prefabs/effects/lootboxes/la96_premium.bundle",
    ]

    output_dir = Path(__file__).parent / "lootbox_animator_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    for bundle_rel_path in target_bundles:
        bundle_path = game_data_path / bundle_rel_path

        if not bundle_path.exists():
            print(f"\n[跳过] {bundle_rel_path}\n")
            continue

        print(f"\n分析: {bundle_rel_path}")
        print("=" * 70)

        controller_data = extract_animator_controller(str(bundle_path))

        if controller_data:
            # 保存JSON
            bundle_name = Path(bundle_rel_path).stem
            json_path = output_dir / f"{bundle_name}_animator.json"

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(controller_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"\n详细数据已保存: {json_path}")

    print("\n" + "=" * 70)
    print("提取完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
