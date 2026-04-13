#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import zipfile
import shutil

# ===== 请在此处更新图床小镇的直链 =====
ZIP_URL = "https://your-image-hosting.com/your-sys.zip"
# ===================================

def download_with_curl(url, save_path):
    """使用curl下载文件并显示进度条"""
    print(f"下载: {url}")
    # curl: -L 跟随重定向, -o 输出文件, --progress-bar 显示进度条
    result = os.system(f"curl -L -o '{save_path}' --progress-bar '{url}'")
    if result == 0 and os.path.exists(save_path) and os.path.getsize(save_path) > 0:
        print(f"下载完成: {save_path}")
        return True
    else:
        print(f"下载失败: {url}")
        return False

def extract_zip(zip_path, extract_to):
    """解压ZIP文件"""
    print(f"解压: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 获取文件列表用于显示进度
            file_list = zip_ref.namelist()
            total = len(file_list)
            for i, file in enumerate(file_list, 1):
                zip_ref.extract(file, extract_to)
                # 显示解压进度
                percent = (i / total) * 100
                print(f"\r解压进度: [{int(percent/2)*'#'}{(50-int(percent/2))*' '}] {percent:.1f}%", end='')
            print()  # 换行
        print(f"解压完成: {extract_to}")
        return True
    except Exception as e:
        print(f"解压失败: {e}")
        return False

def move_db_txt():
    """移动db.txt到/storage/emulated/0/"""
    source_db = "/storage/emulated/0/sys/db.txt"
    target_db = "/storage/emulated/0/db.txt"
    
    if os.path.exists(source_db):
        try:
            shutil.move(source_db, target_db)
            print(f"移动: {source_db} -> {target_db}")
            return True
        except Exception as e:
            print(f"移动失败: {e}")
            return False
    else:
        print(f"警告: {source_db} 不存在")
        return False

def main():
    zip_path = "/storage/emulated/0/sys.zip"
    extract_path = "/storage/emulated/0/sys"
    
    # 清理旧目录
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
        print(f"删除旧目录: {extract_path}")
    
    # 下载
    if not download_with_curl(ZIP_URL, zip_path):
        return False
    
    # 解压
    if not extract_zip(zip_path, extract_path):
        return False
    
    # 移动db.txt
    if not move_db_txt():
        return False
    
    # 删除zip文件
    os.remove(zip_path)
    print(f"删除: {zip_path}")
    
    print("✓ download.py 执行完成")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
