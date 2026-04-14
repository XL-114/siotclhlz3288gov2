#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import zipfile
import shutil

def extract_zip(zip_path, extract_to):
    print(f"解压: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"解压完成: {extract_to}")
        return True
    except Exception as e:
        print(f"解压失败: {e}")
        return False

def copy_files():
    source_dir = "/storage/emulated/0/sys/files"
    target_dir = "/storage/emulated/0/Android/data/com.gohi.go.pro.siot.device.clazz/files"
    
    if not os.path.exists(source_dir):
        print(f"错误：源目录不存在 - {source_dir}")
        return False
    
    os.makedirs(target_dir, exist_ok=True)
    
    try:
        for root, dirs, files in os.walk(source_dir):
            rel_path = os.path.relpath(root, source_dir)
            if rel_path == '.':
                target_subdir = target_dir
            else:
                target_subdir = os.path.join(target_dir, rel_path)
            
            os.makedirs(target_subdir, exist_ok=True)
            
            for file in files:
                source_file = os.path.join(root, file)
                target_file = os.path.join(target_subdir, file)
                try:
                    shutil.copy2(source_file, target_file)
                    print(f"已复制: {source_file} -> {target_file}")
                except Exception as e:
                    print(f"复制文件失败 {source_file}: {e}")
                    return False
        print("文件复制完成！")
        return True
    except Exception as e:
        print(f"复制过程中发生错误: {e}")
        return False

def main():
    zip_path = "/storage/emulated/0/sys.zip"
    extract_path = "/storage/emulated/0/sys"
    
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
        print(f"删除旧目录: {extract_path}")
    
    if not extract_zip(zip_path, extract_path):
        return False
    
    source_db = "/storage/emulated/0/sys/db.txt"
    target_db = "/storage/emulated/0/db.txt"
    if os.path.exists(source_db):
        shutil.move(source_db, target_db)
        print(f"移动: {source_db} -> {target_db}")
    else:
        print(f"警告: {source_db} 不存在")
    
    if not copy_files():
        return False
    
    print("执行db.py...")
    result = os.system("python /storage/emulated/0/db.py")
    if result != 0:
        print("db.py执行失败")
        return False
    
    shutil.rmtree(extract_path)
    print(f"删除: {extract_path}")
    print(f"保留: {zip_path}")
    
    print("✓ 数据同步成功！退出 Termux")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)