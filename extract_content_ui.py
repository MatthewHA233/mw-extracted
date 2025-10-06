import UnityPy
import os
from pathlib import Path

# 路径配置
CONTENT_PATH = r"Modern Warships_Data\StreamingAssets\aa\w64\contentseparated_assets_content"
OUTPUT_PATH = r"MW资源\extracted_content_ui"

def extract_bundle(bundle_path, output_dir, chinese_name=None):
    """提取bundle中的所有图片"""
    bundle_name = os.path.basename(bundle_path).replace('.bundle', '').replace('.spriteatlas', '').replace('.jpg', '').replace('.png', '')

    # 如果有中文名，使用中文名创建文件夹
    if chinese_name:
        folder_name = f"{bundle_name} - {chinese_name}"
        print(f"\n提取: {chinese_name}")
    else:
        folder_name = bundle_name
        print(f"\n提取: {bundle_name}")

    # 创建输出目录
    output_folder = os.path.join(output_dir, folder_name)
    os.makedirs(output_folder, exist_ok=True)

    try:
        env = UnityPy.load(str(bundle_path))
        extracted_count = 0

        for obj in env.objects:
            if obj.type.name in ["Texture2D", "Sprite"]:
                try:
                    data = obj.read()

                    if hasattr(data, 'image'):
                        img = data.image
                        img_name = getattr(data, 'name', None) or getattr(data, 'm_Name', None) or f"unnamed_{obj.path_id}"
                        img_path = os.path.join(output_folder, f"{img_name}.png")

                        img.save(img_path)
                        extracted_count += 1
                        print(f"  + {img_name}.png")

                except Exception as e:
                    continue

        print(f"完成! 提取 {extracted_count} 张图片")
        return extracted_count

    except Exception as e:
        print(f"ERROR: {e}")
        return 0

def main():
    print("=" * 60)
    print("Content UI 资源提取工具")
    print("=" * 60)

    base_dir = Path(__file__).parent.parent
    content_dir = base_dir / CONTENT_PATH
    output_dir = base_dir / OUTPUT_PATH

    if not content_dir.exists():
        print(f"ERROR: 找不到content目录: {content_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)

    # 要提取的资源
    resources_to_extract = [
        # Sprite Atlases
        ("spriteatlases/loginpage.spriteatlas.bundle", "登录页图集"),
        ("spriteatlases/ui.spriteatlas.bundle", "UI图集"),

        # Splash Screens
        ("ui/splashscreens/splashscreen.jpg.bundle", "启动画面"),
        ("ui/splashscreens/splashscreenhelicarrier.jpg.bundle", "直升机航母启动画面"),
    ]

    total_extracted = 0
    successful = 0

    for relative_path, description in resources_to_extract:
        full_path = content_dir / relative_path

        if not full_path.exists():
            print(f"\n跳过: {description} (文件不存在)")
            continue

        print(f"\n{'='*60}")
        print(f"类别: {description}")
        print(f"{'='*60}")

        count = extract_bundle(str(full_path), str(output_dir), description)
        if count > 0:
            successful += 1
            total_extracted += count

    print("\n" + "=" * 60)
    print(f"提取完成!")
    print(f"成功: {successful}/{len(resources_to_extract)} 个资源包")
    print(f"总计: {total_extracted} 张图片")
    print(f"保存位置: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    main()
