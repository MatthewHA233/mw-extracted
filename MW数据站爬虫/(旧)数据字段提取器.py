"""
MW数据站字段提取器
给定URL，自动提取该页面数据的所有CSV字段名称
"""
import requests
import re
import json
import html
from pathlib import Path


def fetch_fields_from_url(url):
    """
    从给定URL提取所有数据字段
    """
    print(f"\n访问URL: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'

        # 提取页面标题（h1）
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', response.text, re.IGNORECASE | re.DOTALL)
        page_title = None
        if title_match:
            # 去除HTML标签
            title_text = re.sub(r'<[^>]+>', '', title_match.group(1))
            page_title = title_text.strip()
            print(f"  页面标题: {page_title}")

        # 如果没有h1，尝试从<title>标签提取
        if not page_title:
            title_match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if title_match:
                title_text = title_match.group(1).strip()
                # 移除常见的后缀
                page_title = title_text.split('–')[0].split('-')[0].strip()
                print(f"  页面标题: {page_title}")

        # 尝试多种可能的组件名称模式
        patterns = [
            r'<ship-list\s+v-bind:context="([^"]+)"',
            r'<weapon-list\s+v-bind:context="([^"]+)"',
            r'<aircraft-list\s+v-bind:context="([^"]+)"',
            r'<item-list\s+v-bind:context="([^"]+)"',
            r'<unit-list\s+v-bind:context="([^"]+)"',
            r'<(\w+)-list\s+v-bind:context="([^"]+)"',  # 通用模式
        ]

        data = None
        component_name = None

        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                if len(match.groups()) == 2:
                    component_name = match.group(1)
                    json_str = html.unescape(match.group(2))
                else:
                    json_str = html.unescape(match.group(1))

                try:
                    data = json.loads(json_str)
                    print(f"  找到组件: {component_name or '未知'}-list")
                    break
                except json.JSONDecodeError:
                    continue

        if not data:
            print("  未找到数据，尝试查找其他模式...")
            return None

        # 提取items列表
        items = data.get('list', {}).get('items', [])

        if not items:
            print("  未找到items数据")
            return None

        print(f"  找到 {len(items)} 条数据")

        # 收集所有字段
        all_fields = set()

        for item in items:
            all_fields.update(item.keys())

        # 分析字段类型
        field_types = {}
        field_samples = {}

        for field in all_fields:
            # 获取第一个非空值作为样本
            for item in items:
                value = item.get(field)
                if value is not None and value != '':
                    field_types[field] = type(value).__name__
                    field_samples[field] = str(value)[:50]  # 限制长度
                    break

        return {
            'url': url,
            'title': page_title,
            'component': component_name,
            'total': data.get('list', {}).get('total', 0),
            'fields': sorted(all_fields),
            'field_types': field_types,
            'field_samples': field_samples
        }

    except requests.RequestException as e:
        print(f"  请求失败: {e}")
        return None
    except Exception as e:
        print(f"  解析失败: {e}")
        return None


def print_fields_info(info):
    """打印字段信息"""
    if not info:
        return

    print("\n" + "=" * 70)
    print("数据字段分析结果")
    print("=" * 70)
    print(f"\n标题: {info['title'] or '未知'}")
    print(f"URL: {info['url']}")
    print(f"组件: {info['component'] or '未知'}")
    print(f"总数: {info['total']}")
    print(f"\n共找到 {len(info['fields'])} 个字段:\n")

    print(f"{'序号':<6} {'字段名':<30} {'类型':<12} {'示例值'}")
    print("-" * 70)

    for i, field in enumerate(info['fields'], 1):
        field_type = info['field_types'].get(field, 'unknown')
        sample = info['field_samples'].get(field, 'N/A')
        print(f"{i:<6} {field:<30} {field_type:<12} {sample}")


def save_fields_to_file(info, output_file):
    """保存字段列表到文件"""
    if not info:
        return

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# MW数据站字段提取结果\n")
        f.write(f"# 标题: {info['title'] or '未知'}\n")
        f.write(f"# URL: {info['url']}\n")
        f.write(f"# 组件: {info['component'] or '未知'}\n")
        f.write(f"# 总数: {info['total']}\n")
        f.write(f"# 字段数: {len(info['fields'])}\n\n")

        f.write("字段名,类型,示例值\n")
        for field in info['fields']:
            field_type = info['field_types'].get(field, 'unknown')
            sample = info['field_samples'].get(field, 'N/A').replace(',', '，')  # 替换逗号避免CSV混淆
            f.write(f"{field},{field_type},{sample}\n")

    print(f"\n字段列表已保存到: {output_file}")


def main():
    """
    主函数
    """
    print("=" * 70)
    print("MW数据站 - 数据字段提取器")
    print("=" * 70)
    print("\n功能: 分析MW数据站页面，提取所有CSV字段名称")
    print("\n示例URL:")
    print("  战舰: https://mwstats.info/ships?lang=zh-hans")
    print("  武器: https://mwstats.info/modules?lang=zh-hans")
    print("  航空器: https://mwstats.info/aircraft?lang=zh-hans")
    print("  迷彩: https://mwstats.info/camos?lang=zh-hans")
    print("  旗帜: https://mwstats.info/flags?lang=zh-hans")

    # 获取用户输入
    url = input("\n请输入要分析的URL: ").strip()

    if not url:
        print("URL不能为空")
        return

    # 提取字段
    info = fetch_fields_from_url(url)

    if info:
        # 打印字段信息
        print_fields_info(info)

        # 询问是否保存
        save = input("\n是否保存字段列表到文件? (y/n): ").strip().lower()

        if save == 'y':
            # 使用页面标题作为文件名
            if info['title']:
                # 移除不能用于文件名的字符
                safe_title = re.sub(r'[\\/:*?"<>|]', '_', info['title'])
                file_name = f"{safe_title}_字段列表.txt"
            else:
                # 如果没有标题，从URL提取
                url_parts = url.split('?')[0].split('/')
                page_name = url_parts[-1] if url_parts[-1] else 'data'
                file_name = f"{page_name}_字段列表.txt"

            output_file = Path(__file__).parent / file_name
            save_fields_to_file(info, str(output_file))

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
