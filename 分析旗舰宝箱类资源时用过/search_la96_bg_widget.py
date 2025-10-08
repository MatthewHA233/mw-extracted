"""
检索 la96 活动的 background 和 widget 相关 bundle 文件
"""
import re
from pathlib import Path

# 输入文件
INPUT_FILE = Path(__file__).parent / "分析旗舰宝箱类资源时用过/flagship_container_搜索结果.txt"
OUTPUT_FILE = Path(__file__).parent / "la96_background_widget_检索.txt"

def main():
    print("=" * 70)
    print("检索 la96 的 background 和 widget bundle")
    print("=" * 70)

    if not INPUT_FILE.exists():
        print(f"\n错误: 找不到输入文件")
        print(f"路径: {INPUT_FILE}")
        return

    print(f"\n输入文件: {INPUT_FILE}")
    print(f"输出文件: {OUTPUT_FILE}\n")

    # 读取文件
    print("正在读取文件...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检索 la96 + background
    print("检索: la96 + background")
    la96_background = []
    for line in content.split('\n'):
        if 'la96' in line.lower() and 'background' in line.lower() and '.bundle' in line:
            match = re.search(r'contentseparated[^\s]+\.bundle', line)
            if match:
                bundle_path = match.group(0).replace('\\', '/')
                if bundle_path not in la96_background:
                    la96_background.append(bundle_path)

    # 检索 la96 + widget
    print("检索: la96 + widget")
    la96_widget = []
    for line in content.split('\n'):
        if 'la96' in line.lower() and 'widget' in line.lower() and '.bundle' in line:
            match = re.search(r'contentseparated[^\s]+\.bundle', line)
            if match:
                bundle_path = match.group(0).replace('\\', '/')
                if bundle_path not in la96_widget:
                    la96_widget.append(bundle_path)

    # 写入结果
    print(f"\n找到 {len(la96_background)} 个 background 文件")
    print(f"找到 {len(la96_widget)} 个 widget 文件\n")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("la96 活动的 background 和 widget 检索结果\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"[la96 + background] - {len(la96_background)} 个文件:\n")
        f.write("-" * 70 + "\n")
        for path in sorted(la96_background):
            f.write(f"{path}\n")

        f.write(f"\n\n[la96 + widget] - {len(la96_widget)} 个文件:\n")
        f.write("-" * 70 + "\n")
        for path in sorted(la96_widget):
            f.write(f"{path}\n")

        f.write(f"\n\n" + "=" * 70 + "\n")
        f.write("统计:\n")
        f.write("=" * 70 + "\n")
        f.write(f"background: {len(la96_background)} 个\n")
        f.write(f"widget: {len(la96_widget)} 个\n")

    print("=" * 70)
    print("检索完成!")
    print("=" * 70)
    print(f"结果已保存到: {OUTPUT_FILE}")
    print("=" * 70)

if __name__ == "__main__":
    main()
