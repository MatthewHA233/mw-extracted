"""
资源同步工具
功能：
1. 同步 MW解包有益资源 到本地项目和 OSS
2. 同步 MW数据站爬虫\抽奖物品数据 到本地项目和 OSS
同步模式：增量同步（只新增和更新，不删除）
"""
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

# ========== 配置区域 ==========
# 本地路径配置
SYNC_RULES = [
    {
        "name": "解包资源",
        "source": "MW解包有益资源",
        "targets": [
            r"D:\my_pro\web_ob\现代战舰抽奖模拟器\public\assets"
        ],
        "oss_path": "mw-gacha-simulation/assets/",
        "exclude_patterns": ["*.py", "*.pyc", "__pycache__"]
    },
    {
        "name": "抽奖配置",
        "source": r"MW数据站爬虫\抽奖物品数据",
        "targets": [
            r"D:\my_pro\web_ob\现代战舰抽奖模拟器\public\gacha-configs"
        ],
        "oss_path": "mw-gacha-simulation/gacha-configs/",
        "exclude_patterns": []
    }
]

# 阿里云 OSS 配置
OSS_CONFIG = {
    "enabled": False,  # 是否启用 OSS 同步（需要先配置 access_key）
    "endpoint": "oss-accelerate.aliyuncs.com",
    "bucket_name": "",  # TODO: 填写你的 bucket 名称
    "access_key_id": "",  # TODO: 填写你的 AccessKeyId
    "access_key_secret": ""  # TODO: 填写你的 AccessKeySecret
}


def calculate_file_md5(file_path):
    """计算文件MD5值"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def should_exclude(file_path, exclude_patterns):
    """检查文件是否应该被排除"""
    file_name = os.path.basename(file_path)
    for pattern in exclude_patterns:
        if pattern.startswith("*."):
            # 扩展名匹配
            ext = pattern[1:]  # 去掉 *
            if file_name.endswith(ext):
                return True
        elif pattern == file_name:
            # 完整文件名匹配
            return True
    return False


def sync_to_local(source_root, target_root, exclude_patterns):
    """同步文件到本地目录（增量）"""
    source_path = Path(source_root)
    target_path = Path(target_root)

    if not source_path.exists():
        print(f"  ✗ 源目录不存在: {source_path}")
        return 0, 0

    # 创建目标目录
    target_path.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    skipped_count = 0

    # 遍历源目录
    for src_file in source_path.rglob("*"):
        if src_file.is_dir():
            continue

        # 检查是否排除
        if should_exclude(str(src_file), exclude_patterns):
            continue

        # 计算相对路径
        rel_path = src_file.relative_to(source_path)
        dst_file = target_path / rel_path

        # 创建目标子目录
        dst_file.parent.mkdir(parents=True, exist_ok=True)

        # 检查是否需要复制
        need_copy = False
        if not dst_file.exists():
            need_copy = True
        else:
            # 比较文件大小和修改时间
            if src_file.stat().st_size != dst_file.stat().st_size:
                need_copy = True
            elif src_file.stat().st_mtime > dst_file.stat().st_mtime:
                need_copy = True

        if need_copy:
            shutil.copy2(src_file, dst_file)
            copied_count += 1
            print(f"    ✓ {rel_path}")
        else:
            skipped_count += 1

    return copied_count, skipped_count


def sync_to_oss(source_root, oss_prefix, exclude_patterns, oss_client, bucket):
    """同步文件到阿里云OSS（增量）"""
    source_path = Path(source_root)

    if not source_path.exists():
        print(f"  ✗ 源目录不存在: {source_path}")
        return 0, 0

    uploaded_count = 0
    skipped_count = 0

    # 遍历源目录
    for src_file in source_path.rglob("*"):
        if src_file.is_dir():
            continue

        # 检查是否排除
        if should_exclude(str(src_file), exclude_patterns):
            continue

        # 计算相对路径和OSS key
        rel_path = src_file.relative_to(source_path)
        oss_key = oss_prefix + str(rel_path).replace("\\", "/")

        # 检查OSS上是否存在
        need_upload = False
        try:
            # 获取OSS对象信息
            meta = bucket.get_object_meta(oss_key)
            remote_size = int(meta.headers.get('Content-Length', 0))
            local_size = src_file.stat().st_size

            # 比较大小
            if local_size != remote_size:
                need_upload = True
        except:
            # OSS上不存在
            need_upload = True

        if need_upload:
            bucket.put_object_from_file(oss_key, str(src_file))
            uploaded_count += 1
            print(f"    ✓ {rel_path} → {oss_key}")
        else:
            skipped_count += 1

    return uploaded_count, skipped_count


def main():
    print("=" * 70)
    print("MW资源同步工具")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 脚本所在目录作为基准
    base_dir = Path(__file__).parent

    # 初始化OSS客户端
    oss_client = None
    bucket = None

    if OSS_CONFIG["enabled"]:
        try:
            import oss2
            auth = oss2.Auth(OSS_CONFIG["access_key_id"], OSS_CONFIG["access_key_secret"])
            bucket = oss2.Bucket(auth, OSS_CONFIG["endpoint"], OSS_CONFIG["bucket_name"])
            print("✓ OSS 连接成功\n")
        except ImportError:
            print("✗ 未安装 oss2 库，跳过 OSS 同步")
            print("  安装命令: pip install oss2\n")
            OSS_CONFIG["enabled"] = False
        except Exception as e:
            print(f"✗ OSS 连接失败: {e}\n")
            OSS_CONFIG["enabled"] = False

    # 执行同步
    for rule in SYNC_RULES:
        print("=" * 70)
        print(f"同步任务: {rule['name']}")
        print("=" * 70)

        source = base_dir / rule["source"]
        print(f"源目录: {source}")

        if not source.exists():
            print(f"✗ 源目录不存在，跳过\n")
            continue

        # 同步到本地目标
        for target in rule["targets"]:
            print(f"\n目标: {target}")
            copied, skipped = sync_to_local(
                source,
                target,
                rule["exclude_patterns"]
            )
            print(f"  结果: 复制 {copied} 个文件，跳过 {skipped} 个")

        # 同步到OSS
        if OSS_CONFIG["enabled"] and bucket:
            print(f"\nOSS: {rule['oss_path']}")
            uploaded, skipped = sync_to_oss(
                source,
                rule["oss_path"],
                rule["exclude_patterns"],
                oss_client,
                bucket
            )
            print(f"  结果: 上传 {uploaded} 个文件，跳过 {skipped} 个")

        print()

    print("=" * 70)
    print("同步完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
