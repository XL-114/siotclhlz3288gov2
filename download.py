#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import zipfile
import shutil
import requests

# ===== 请在此处更新图床小镇的直链 =====
ZIP_URL = "https://test.fukit.cn/autoupload/f/yhunPk8G_eht2NpMlrWpZNiO_OyvX7mIgxFBfDMDErs/default/sys.z"  # 每次更新时修改这里
# ===================================

def download_file(url, save_path):
    """下载文件"""
    try:
        print(f"开始下载: {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r下载进度: {progress:.1f}%", end='')
        
        print(f"\n下载完成: {save_path}")
        return True
    except Exception as e:
        print(f"下载失败: {e}")
        return False

def extract_zip(zip_path, extract_to):
    """解压ZIP文件"""
    try:
        print(f"开始解压: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"解压完成到: {extract_to}")
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
            print(f"已移动: {source_db} -> {target_db}")
            return True
        except Exception as e:
            print(f"移动db.txt失败: {e}")
            return False
    else:
        print(f"警告: {source_db} 不存在")
        return False

def main():
    # 设置路径
    zip_save_path = "/storage/emulated/0/sys.z"
    extract_path = "/storage/emulated/0/sys"
    
    # 清理旧的sys目录（如果存在）
    if os.path.exists(extract_path):
        try:
            shutil.rmtree(extract_path)
            print(f"已删除旧目录: {extract_path}")
        except Exception as e:
            print(f"删除旧目录失败: {e}")
            return False
    
    # 下载ZIP文件
    if not download_file(ZIP_URL, zip_save_path):
        return False
    
    # 解压ZIP文件
    if not extract_zip(zip_save_path, extract_path):
        return False
    
    # 移动db.txt
    if not move_db_txt():
        return False
    
    # 删除ZIP文件（可选）
    try:
        os.remove(zip_save_path)
        print(f"已删除ZIP文件: {zip_save_path}")
    except:
        pass
    
    print("所有操作完成！")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)