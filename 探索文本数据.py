import UnityPy
import os
from pathlib import Path
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# 主资源文件路径
GAME_DATA_PATH = r"Modern Warships_Data"
OUTPUT_PATH = r"MW资源\\探索文本数据"

# 匹配关键词
TEXT_KEYWORDS = ["ship_", "weapon_", "localiz", "lang", "desc"]

# 并行线程数
MAX_WORKERS = 10


def extract_text_from_file(file_path, output_dir):
    """从资源文件中提取 TextAsset 与 MonoBehaviour"""
    file_name = os.path.basename(file_path)
    print(f"\n[SCAN] {file_name}")

    try:
        env = UnityPy.load(str(file_path))
        text_count = 0
        mono_count = 0

        for obj in env.objects:
            # TextAsset 导出
            if obj.type.name == "TextAsset":
                try:
                    data = obj.read()
                    text_data = getattr(data, "text", "")
                    if not text_data:
                        continue

                    # 检查关键字
                    if any(k.lower() in text_data.lower() for k in TEXT_KEYWORDS):
                        safe_name = re.sub(r'[\\/:*?"<>|]', "_", data.name or f"text_{obj.path_id}")
                        output_path = os.path.join(output_dir, f"{safe_name}.txt")

                        # 防止重名覆盖
                        if os.path.exists(output_path):
                            output_path = os.path.join(output_dir, f"{safe_name}_{file_name}.txt")

                        with open(output_path, "w", encoding="utf-8", errors="ignore") as f:
                            f.write(text_data)
                        text_count += 1
                        print(f"  + [TXT] {safe_name}")
                except Exception:
                    continue

            # MonoBehaviour 导出
            elif obj.type.name == "MonoBehaviour":
                try:
                    data = obj.read()
                    name = (data.name or "").lower()
                    if any(k in name for k in ["local", "ship", "weapon"]):
                        safe_name = re.sub(r'[\\/:*?"<>|]', "_", data.name or f"mono_{obj.path_id}")
                        output_path = os.path.join(output_dir, f"{safe_name}.json")

                        try:
                            tree = data.save_typetree()
                        except Exception:
                            try:
                                tree = data.to_dict()
                            except Exception:
                                tree = None

                        if tree:
                            with open(output_path, "w", encoding="utf-8") as f:
                                json.dump(tree, f, ensure_ascii=False, indent=2)
                            mono_count += 1
                            print(f"  + [MONO] {safe_name}")
                except Exception:
                    continue

        print(f"[DONE] {file_name}: {text_count} 文本, {mono_count} 对象")
        return text_count, mono_count

    except Exception as e:
        print(f"[ERROR] {file_name}: {e}")
        return 0, 0


def main():
    print("=" * 60)
    print("Modern Warships 资源文本提取器 (并行版, TextAsset & Mono Extractor)")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / GAME_DATA_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not data_dir.exists():
        print(f"ERROR: 找不到游戏数据目录: {data_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    print(f"\n关键词: {', '.join(TEXT_KEYWORDS)}")
    print(f"并行线程数: {MAX_WORKERS}")

    # 搜索目标文件
    files_to_scan = []
    for root, _, files in os.walk(data_dir):
        for f in files:
            if f.endswith((".assets", ".bundle", ".resS")):
                files_to_scan.append(os.path.join(root, f))

    total_texts, total_monos = 0, 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(extract_text_from_file, f, str(output_dir)): f for f in files_to_scan}

        for i, future in enumerate(as_completed(futures), 1):
            t_count, m_count = future.result()
            total_texts += t_count
            total_monos += m_count
            print(f"[进度] {i}/{len(futures)} 已完成")

    print("\n" + "=" * 60)
    print(f"提取完成!")
    print(f"共导出 {total_texts} 个 TextAsset, {total_monos} 个 MonoBehaviour")
    print(f"保存目录: {output_dir}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        import UnityPy
    except ImportError:
        print("缺少 UnityPy 模块，请先执行: pip install UnityPy")
    else:
        main()
