#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os
import sys
import zipfile
import shutil

# ==================== db.py 原有函数 ====================

def get_script_dir():
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))

def parse_db_txt(file_path):
    """解析db.txt文件，支持多数据库和多表，支持#:删除标记和#:@清空表标记"""
    if not os.path.exists(file_path):
        print(f"错误：找不到文件 {file_path}")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if not lines:
        print("错误：db.txt 文件为空")
        return None
    
    # 解析多个数据库
    databases = {}
    current_db_path = None
    current_schema = None
    current_data = []
    current_delete_data = []
    current_truncate = False  # 标记是否需要清空当前表
    
    for line in lines:
        # 检查是否是数据库路径行（以path:开头）
        if line.startswith('path:'):
            # 保存上一个数据库的数据
            if current_db_path is not None and current_schema is not None:
                if current_data or current_delete_data or current_truncate:
                    if current_db_path not in databases:
                        databases[current_db_path] = {}
                    if current_schema not in databases[current_db_path]:
                        databases[current_db_path][current_schema] = {'insert': [], 'delete': [], 'truncate': False}
                    if current_data:
                        databases[current_db_path][current_schema]['insert'].extend(current_data)
                    if current_delete_data:
                        databases[current_db_path][current_schema]['delete'].extend(current_delete_data)
                    if current_truncate:
                        databases[current_db_path][current_schema]['truncate'] = True
                    current_data = []
                    current_delete_data = []
                    current_truncate = False
            
            # 切换到新数据库
            current_db_path = line[5:].strip()
            current_schema = None
            current_data = []
            current_delete_data = []
            current_truncate = False
            print(f"发现数据库: {current_db_path}")
            
        # 检查是否是以@开头的表名
        elif line.startswith('@'):
            # 保存上一个表的数据
            if current_db_path is not None and current_schema is not None:
                if current_data or current_delete_data or current_truncate:
                    if current_db_path not in databases:
                        databases[current_db_path] = {}
                    if current_schema not in databases[current_db_path]:
                        databases[current_db_path][current_schema] = {'insert': [], 'delete': [], 'truncate': False}
                    if current_data:
                        databases[current_db_path][current_schema]['insert'].extend(current_data)
                    if current_delete_data:
                        databases[current_db_path][current_schema]['delete'].extend(current_delete_data)
                    if current_truncate:
                        databases[current_db_path][current_schema]['truncate'] = True
                    current_data = []
                    current_delete_data = []
                    current_truncate = False
            
            # 切换到新表
            current_schema = line[1:]
            current_data = []
            current_delete_data = []
            current_truncate = False
            
        # 检查是否是清空表行（#:@）
        elif line == '#:@':
            if current_db_path is not None and current_schema is not None:
                current_truncate = True
                
        # 检查是否是删除行（以#:开头，但不是#:@）
        elif line.startswith('#:') and line != '#:@':
            # 删除行，去掉#:前缀
            delete_content = line[2:].strip()
            if current_db_path is not None and current_schema is not None and delete_content:
                if '⎮' in delete_content:
                    values = [v.strip() if v.strip() else None for v in delete_content.split('⎮')]
                else:
                    values = [delete_content]
                current_delete_data.append(values)
                
        else:
            # 普通数据行（插入），使用⎮分隔符
            if current_db_path is not None and current_schema is not None:
                if '⎮' in line:
                    values = [v.strip() if v.strip() else None for v in line.split('⎮')]
                else:
                    values = [line]
                current_data.append(values)
    
    # 保存最后一个数据库的最后一张表的数据
    if current_db_path is not None and current_schema is not None:
        if current_data or current_delete_data or current_truncate:
            if current_db_path not in databases:
                databases[current_db_path] = {}
            if current_schema not in databases[current_db_path]:
                databases[current_db_path][current_schema] = {'insert': [], 'delete': [], 'truncate': False}
            if current_data:
                databases[current_db_path][current_schema]['insert'].extend(current_data)
            if current_delete_data:
                databases[current_db_path][current_schema]['delete'].extend(current_delete_data)
            if current_truncate:
                databases[current_db_path][current_schema]['truncate'] = True
    
    return databases

def get_table_columns(conn, table_name):
    """获取表的列信息"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [(col[1], col[2]) for col in columns]

def table_exists(conn, table_name):
    """检查表是否存在"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def truncate_table(conn, table_name):
    """清空表的所有内容"""
    cursor = conn.cursor()
    cursor.execute(f'DELETE FROM "{table_name}"')
    deleted_count = cursor.rowcount
    conn.commit()
    return deleted_count

def create_simple_table(conn, table_name):
    """创建简单的单列表"""
    cursor = conn.cursor()
    create_sql = f'CREATE TABLE "{table_name}" (value TEXT)'
    cursor.execute(create_sql)
    print(f"  ✓ 已创建简单表: {table_name}")

def create_table_from_template(conn, schema_name, template_columns):
    """根据模板创建表"""
    cursor = conn.cursor()
    
    columns_def = []
    for col_name, col_type in template_columns:
        if col_name == '_id':
            columns_def.append(f'"{col_name}" INTEGER PRIMARY KEY')
        else:
            columns_def.append(f'"{col_name}" {col_type}')
    
    create_sql = f'CREATE TABLE "{schema_name}" ({", ".join(columns_def)})'
    cursor.execute(create_sql)
    print(f"  ✓ 已创建表: {schema_name}")

def delete_data_from_table(conn, table_name, delete_rows, columns):
    """从表中删除数据"""
    cursor = conn.cursor()
    col_names = [col[0] for col in columns]
    deleted = 0
    
    for row in delete_rows:
        try:
            # 构建删除条件
            conditions = []
            values = []
            
            # 判断是否有_id
            has_id = False
            if len(row) > 0 and row[0] is not None and col_names and col_names[0] == '_id':
                try:
                    int(row[0])
                    has_id = True
                except (ValueError, TypeError):
                    pass
            
            if has_id and len(row) >= 1:
                # 使用_id删除
                conditions.append(f'"_id" = ?')
                values.append(row[0])
                sql = f'DELETE FROM "{table_name}" WHERE {" AND ".join(conditions)}'
                cursor.execute(sql, values)
                if cursor.rowcount > 0:
                    deleted += cursor.rowcount
                    print(f"    → 删除数据 ID={row[0]}")
                else:
                    print(f"    → 未找到匹配数据: {row}")
            else:
                # 使用所有非空字段作为条件
                for i, val in enumerate(row):
                    if val is not None and i < len(col_names):
                        conditions.append(f'"{col_names[i]}" = ?')
                        values.append(val)
                
                if conditions:
                    sql = f'DELETE FROM "{table_name}" WHERE {" AND ".join(conditions)}'
                    cursor.execute(sql, values)
                    if cursor.rowcount > 0:
                        deleted += cursor.rowcount
                        print(f"    → 删除数据: {row}")
                    else:
                        print(f"    → 未找到匹配数据: {row}")
                else:
                    print(f"    → 无效的删除条件: {row}")
                    
        except Exception as e:
            print(f"    ✗ 删除失败: {row}, 错误: {e}")
    
    conn.commit()
    return deleted

def insert_data_into_simple_table(conn, table_name, data_rows):
    """插入数据到简单表（单列）"""
    cursor = conn.cursor()
    inserted = 0
    
    for row in data_rows:
        try:
            value = row[0] if row else None
            if value:
                cursor.execute(f'INSERT INTO "{table_name}" (value) VALUES (?)', (value,))
                inserted += 1
        except Exception as e:
            print(f"    ✗ 插入失败: {row}, 错误: {e}")
    
    conn.commit()
    return inserted

def delete_from_simple_table(conn, table_name, delete_rows):
    """从简单表中删除数据"""
    cursor = conn.cursor()
    deleted = 0
    
    for row in delete_rows:
        try:
            value = row[0] if row else None
            if value:
                cursor.execute(f'DELETE FROM "{table_name}" WHERE value = ?', (value,))
                if cursor.rowcount > 0:
                    deleted += cursor.rowcount
                    print(f"    → 删除数据: {value}")
                else:
                    print(f"    → 未找到匹配数据: {value}")
        except Exception as e:
            print(f"    ✗ 删除失败: {row}, 错误: {e}")
    
    conn.commit()
    return deleted

def insert_or_update_data(conn, table_name, data_rows, columns):
    """插入或更新数据，带_id就更新，不带_id就添加"""
    cursor = conn.cursor()
    col_names = [col[0] for col in columns]
    
    inserted = 0
    updated = 0
    
    for row in data_rows:
        try:
            has_id = False
            if len(row) > 0 and row[0] is not None:
                try:
                    int(row[0])
                    if col_names and col_names[0] == '_id':
                        has_id = True
                except (ValueError, TypeError):
                    pass
            
            if has_id:
                data_len = min(len(row), len(col_names))
                data = row[:data_len]
                used_cols = col_names[:data_len]
                
                placeholders = ','.join(['?' for _ in used_cols])
                col_names_str = ','.join([f'"{col}"' for col in used_cols])
                sql = f'INSERT OR REPLACE INTO "{table_name}" ({col_names_str}) VALUES ({placeholders})'
                cursor.execute(sql, data)
                updated += 1
                print(f"    → 更新数据 ID={data[0]}")
            else:
                insert_cols = [col for col in col_names if col != '_id']
                data_len = min(len(row), len(insert_cols))
                data = row[:data_len]
                used_cols = insert_cols[:data_len]
                
                placeholders = ','.join(['?' for _ in used_cols])
                col_names_str = ','.join([f'"{col}"' for col in used_cols])
                sql = f'INSERT INTO "{table_name}" ({col_names_str}) VALUES ({placeholders})'
                cursor.execute(sql, data)
                inserted += 1
                print(f"    → 添加新数据")
            
        except Exception as e:
            print(f"    ✗ 操作失败: {row}, 错误: {e}")
    
    conn.commit()
    return inserted, updated

def get_table_template():
    """返回预定义的表结构模板"""
    return {
        'NOTICE': [('_id', 'INTEGER'), ('TITLE', 'TEXT'), ('CONTENT', 'TEXT'),
                   ('START_TIME', 'INTEGER'), ('END_TIME', 'INTEGER'), ('UPDATE_TIME', 'INTEGER')],
        'NEWS': [('_id', 'INTEGER'), ('TITLE', 'TEXT'), ('CONTENT', 'TEXT'),
                 ('START_TIME', 'INTEGER'), ('END_TIME', 'INTEGER')]
    }

def ensure_db_directory(db_path):
    """确保数据库目录存在"""
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        print(f"  数据库目录不存在，正在创建: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
        print("  ✓ 目录创建成功")

def process_database(db_path, schemas_data):
    """处理单个数据库的所有表"""
    print(f"\n{'='*60}")
    print(f"处理数据库: {db_path}")
    print(f"{'='*60}")
    
    # 确保目录存在
    ensure_db_directory(db_path)
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    templates = get_table_template()
    
    try:
        for schema_name, operations in schemas_data.items():
            insert_rows = operations.get('insert', [])
            delete_rows = operations.get('delete', [])
            truncate = operations.get('truncate', False)
            
            print(f"\n处理表: {schema_name}")
            print(f"  清空表: {'是' if truncate else '否'}")
            print(f"  插入数据: {len(insert_rows)} 条")
            print(f"  删除数据: {len(delete_rows)} 条")
            
            # 检查表是否存在
            if not table_exists(conn, schema_name):
                if insert_rows or truncate:
                    print(f"  → 表 '{schema_name}' 不存在，正在创建...")
                    if schema_name in templates:
                        create_table_from_template(conn, schema_name, templates[schema_name])
                    else:
                        create_simple_table(conn, schema_name)
                else:
                    print(f"  → 表 '{schema_name}' 不存在且无插入数据，跳过")
                    continue
            
            # 获取表结构
            existing_columns = get_table_columns(conn, schema_name)
            is_simple_table = (len(existing_columns) == 1 and existing_columns[0][0] == 'value')
            
            # 先执行清空表操作（如果标记了#:@）
            if truncate:
                print(f"\n  执行清空表操作:")
                deleted_count = truncate_table(conn, schema_name)
                print(f"  ✓ 已清空表，删除 {deleted_count} 条数据")
            
            # 再执行删除操作（精确删除）
            if delete_rows:
                print(f"\n  执行精确删除操作:")
                if is_simple_table:
                    deleted_count = delete_from_simple_table(conn, schema_name, delete_rows)
                else:
                    deleted_count = delete_data_from_table(conn, schema_name, delete_rows, existing_columns)
                print(f"  ✓ 已删除 {deleted_count} 条数据")
            
            # 最后执行插入/更新操作
            if insert_rows:
                print(f"\n  执行插入/更新操作:")
                if is_simple_table:
                    inserted_count = insert_data_into_simple_table(conn, schema_name, insert_rows)
                    print(f"  ✓ 完成: 添加 {inserted_count} 条数据")
                else:
                    inserted_count, updated_count = insert_or_update_data(conn, schema_name, insert_rows, existing_columns)
                    print(f"  ✓ 完成: 添加 {inserted_count} 条，更新 {updated_count} 条")
            
            # 验证数据
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM "{schema_name}"')
            count = cursor.fetchone()[0]
            print(f"\n  → 表 '{schema_name}' 中共有 {count} 条数据")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 处理数据库出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

def process_databases_main(db_txt_path):
    """执行数据库处理的主逻辑，返回是否成功"""
    print("=" * 60)
    print("数据库处理模块")
    print("=" * 60)
    
    # 检查Termux存储权限
    if not os.path.exists("/storage/emulated/0"):
        print("✗ 错误：无法访问 /storage/emulated/0")
        print("请在Termux中运行: termux-setup-storage")
        print("然后按提示授予存储权限")
        return False
    
    # 解析 db.txt
    databases = parse_db_txt(db_txt_path)
    if not databases:
        print("✗ 解析 db.txt 失败")
        return False
    
    print(f"\n找到 {len(databases)} 个数据库:")
    for db_path, schemas in databases.items():
        table_count = len(schemas)
        total_insert = sum(len(schemas[t].get('insert', [])) for t in schemas)
        total_delete = sum(len(schemas[t].get('delete', [])) for t in schemas)
        total_truncate = sum(1 for t in schemas if schemas[t].get('truncate', False))
        print(f"  - {db_path} ({table_count} 个表, 清空 {total_truncate} 个, 插入 {total_insert} 条, 删除 {total_delete} 条)")
    
    # 处理每个数据库
    success_count = 0
    for db_path, schemas_data in databases.items():
        if process_database(db_path, schemas_data):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"数据库处理完成！成功处理 {success_count}/{len(databases)} 个数据库")
    print("=" * 60)
    
    return success_count == len(databases)


# ==================== sync.py 原有函数 ====================

def extract_zip(zip_path, extract_to):
    """解压ZIP文件"""
    print(f"解压: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"解压完成: {extract_to}")
        return True
    except Exception as e:
        print(f"解压失败: {e}")
        return False

def copy_files(source_dir, target_dir):
    """复制文件"""
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


def sync_main():
    """执行同步模块的主逻辑，返回是否成功"""
    print("=" * 60)
    print("文件同步模块")
    print("=" * 60)
    
    zip_path = "/storage/emulated/0/sys.zip"
    extract_path = "/storage/emulated/0/sys"
    source_dir = "/storage/emulated/0/sys/files"
    target_dir = "/storage/emulated/0/Android/data/com.gohi.go.pro.siot.device.clazz/files"
    target_db = "/storage/emulated/0/db.txt"
    
    # 删除旧目录
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
        print(f"删除旧目录: {extract_path}")
    
    # 解压ZIP
    if not extract_zip(zip_path, extract_path):
        return False
    
    # 移动db.txt文件
    source_db = os.path.join(extract_path, "db.txt")
    if os.path.exists(source_db):
        # 如果目标已存在，先删除
        if os.path.exists(target_db):
            os.remove(target_db)
        shutil.move(source_db, target_db)
        print(f"移动: {source_db} -> {target_db}")
    else:
        print(f"警告: {source_db} 不存在")
    
    # 复制文件
    if not copy_files(source_dir, target_dir):
        return False
    
    # 删除解压目录
    shutil.rmtree(extract_path)
    print(f"删除: {extract_path}")
    print(f"保留: {zip_path}")
    
    print("文件同步完成！")
    return True


# ==================== 主入口 ====================

def main():
    """主函数：先执行同步，再执行数据库处理"""
    print("\n" + "=" * 60)
    print("数据同步与数据库处理一体化工具")
    print("=" * 60)
    
    # 第一步：执行同步
    if not sync_main():
        print("\n✗ 文件同步失败，终止执行")
        return False
    
    print("\n")
    
    # 第二步：执行数据库处理
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_txt_path = os.path.join(script_dir, 'db.txt')
    
    # 如果当前目录没有db.txt，尝试从/storage/emulated/0/读取
    if not os.path.exists(db_txt_path):
        db_txt_path = "/storage/emulated/0/db.txt"
    
    if not process_databases_main(db_txt_path):
        print("\n✗ 数据库处理失败")
        return False
    
    print("\n" + "=" * 60)
    print("✓ 全部任务执行成功！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)