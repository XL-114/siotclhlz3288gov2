import sqlite3
import os
import sys

# 固定数据库路径
DB_PATH = "/storage/emulated/0/Android/data/com.gohi.go.pro.siot.device.clazz/files/db/sys/sys-db"

def get_script_dir():
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))

def read_db_txt(file_path):
    """读取db.txt文件，支持@表名格式，返回多个schema的数据字典"""
    if not os.path.exists(file_path):
        print(f"错误：找不到文件 {file_path}")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if len(lines) < 2:
        print("错误：db.txt 格式不正确，至少需要 schema 名和数据行")
        return None
    
    # 解析多个schema
    schemas_data = {}
    current_schema = None
    current_data = []
    
    for line in lines:
        # 检查是否是以@开头的表名
        if line.startswith('@'):
            # 保存上一个schema
            if current_schema is not None and current_data:
                schemas_data[current_schema] = current_data
                current_data = []
            # 去掉@符号作为表名
            current_schema = line[1:]
        else:
            # 普通数据行
            if current_schema is not None and line:
                # 按竖线分割数据（如果没有竖线，整行作为一个值）
                if '⎮' in line:
                    values = [v.strip() if v.strip() else None for v in line.split('⎮')]
                else:
                    values = [line]
                current_data.append(values)
    
    # 保存最后一个schema
    if current_schema is not None and current_data:
        schemas_data[current_schema] = current_data
    
    return schemas_data

def get_table_columns(conn, table_name):
    """获取表的列信息"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [(col[1], col[2]) for col in columns]  # (列名, 类型)

def table_exists(conn, table_name):
    """检查表是否存在"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def create_simple_table(conn, table_name):
    """创建简单的单列表"""
    cursor = conn.cursor()
    create_sql = f'CREATE TABLE "{table_name}" (value TEXT)'
    cursor.execute(create_sql)
    print(f"✓ 已创建简单表: {table_name} (只有value列)")

def create_table_from_template(conn, schema_name, template_columns):
    """根据模板创建表"""
    cursor = conn.cursor()
    
    # 构建CREATE TABLE语句
    columns_def = []
    for col_name, col_type in template_columns:
        if col_name == '_id':
            columns_def.append(f'"{col_name}" INTEGER PRIMARY KEY')
        else:
            columns_def.append(f'"{col_name}" {col_type}')
    
    create_sql = f'CREATE TABLE "{schema_name}" ({", ".join(columns_def)})'
    cursor.execute(create_sql)
    print(f"✓ 已创建表: {schema_name}")

def insert_data_into_simple_table(conn, table_name, data_rows):
    """插入数据到简单表（单列）"""
    cursor = conn.cursor()
    inserted = 0
    
    for row in data_rows:
        try:
            # 取第一个值
            value = row[0] if row else None
            if value:
                cursor.execute(f'INSERT INTO "{table_name}" (value) VALUES (?)', (value,))
                inserted += 1
        except Exception as e:
            print(f"  ✗ 插入失败: {row}, 错误: {e}")
    
    conn.commit()
    return inserted

def insert_or_update_data(conn, table_name, data_rows, columns):
    """插入或更新数据，带_id就更新，不带_id就添加"""
    cursor = conn.cursor()
    
    # 获取列名列表
    col_names = [col[0] for col in columns]
    
    inserted = 0
    updated = 0
    
    for row in data_rows:
        try:
            # 判断第一条数据是否是_id（数字且存在于第一列）
            has_id = False
            if len(row) > 0 and row[0] is not None:
                # 尝试转换为整数，如果成功且列名包含_id，则认为有id
                try:
                    int(row[0])
                    if col_names and col_names[0] == '_id':
                        has_id = True
                except (ValueError, TypeError):
                    pass
            
            if has_id:
                # 有_id，使用 INSERT OR REPLACE（更新）
                # 匹配所有列
                data_len = min(len(row), len(col_names))
                data = row[:data_len]
                used_cols = col_names[:data_len]
                
                placeholders = ','.join(['?' for _ in used_cols])
                col_names_str = ','.join([f'"{col}"' for col in used_cols])
                sql = f'INSERT OR REPLACE INTO "{table_name}" ({col_names_str}) VALUES ({placeholders})'
                cursor.execute(sql, data)
                updated += 1
                print(f"  → 更新数据 ID={data[0]}")
            else:
                # 没有_id，使用普通 INSERT（添加）
                # 排除_id列（因为它是自增的）
                insert_cols = [col for col in col_names if col != '_id']
                data_len = min(len(row), len(insert_cols))
                data = row[:data_len]
                used_cols = insert_cols[:data_len]
                
                placeholders = ','.join(['?' for _ in used_cols])
                col_names_str = ','.join([f'"{col}"' for col in used_cols])
                sql = f'INSERT INTO "{table_name}" ({col_names_str}) VALUES ({placeholders})'
                cursor.execute(sql, data)
                inserted += 1
                print(f"  → 添加新数据")
            
        except Exception as e:
            print(f"  ✗ 操作失败: {row}, 错误: {e}")
    
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

def ensure_db_directory():
    """确保数据库目录存在"""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        print(f"数据库目录不存在，正在创建: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)
        print("✓ 目录创建成功")

def main():
    script_dir = get_script_dir()
    db_txt_path = os.path.join(script_dir, 'db.txt')
    
    print("=" * 60)
    print("数据库修改工具")
    print("=" * 60)
    print(f"脚本目录: {script_dir}")
    print(f"配置文件: {db_txt_path}")
    print(f"数据库文件: {DB_PATH}")
    print("-" * 60)
    
    # 检查Termux存储权限
    if not os.path.exists("/storage/emulated/0"):
        print("✗ 错误：无法访问 /storage/emulated/0")
        print("请在Termux中运行: termux-setup-storage")
        print("然后按提示授予存储权限")
        return
    
    # 确保数据库目录存在
    ensure_db_directory()
    
    # 1. 读取 db.txt
    schemas_data = read_db_txt(db_txt_path)
    if not schemas_data:
        print("✗ 读取 db.txt 失败")
        return
    
    print(f"\n找到 {len(schemas_data)} 个要处理的表:")
    for schema in schemas_data.keys():
        print(f"  - {schema} ({len(schemas_data[schema])} 条数据)")
    print("-" * 60)
    
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    templates = get_table_template()
    
    try:
        for schema_name, data_rows in schemas_data.items():
            print(f"\n处理表: {schema_name}")
            print(f"  数据行数: {len(data_rows)}")
            
            # 检查表是否存在
            if table_exists(conn, schema_name):
                print(f"  ✓ 表 '{schema_name}' 已存在")
                existing_columns = get_table_columns(conn, schema_name)
                print(f"  现有列数: {len(existing_columns)}")
                
                # 获取现有表结构，判断是简单表还是复杂表
                if len(existing_columns) == 1 and existing_columns[0][0] == 'value':
                    # 简单表，直接插入数据
                    inserted_count = insert_data_into_simple_table(conn, schema_name, data_rows)
                    print(f"  ✓ 完成: 添加 {inserted_count} 条数据")
                else:
                    # 复杂表，使用原有的插入更新逻辑
                    columns = get_table_columns(conn, schema_name)
                    inserted_count, updated_count = insert_or_update_data(conn, schema_name, data_rows, columns)
                    print(f"  ✓ 完成: 添加 {inserted_count} 条，更新 {updated_count} 条")
            else:
                print(f"  → 表 '{schema_name}' 不存在，正在创建...")
                
                # 检查是否是预定义模板
                if schema_name in templates:
                    create_table_from_template(conn, schema_name, templates[schema_name])
                    # 插入数据
                    columns = get_table_columns(conn, schema_name)
                    inserted_count, updated_count = insert_or_update_data(conn, schema_name, data_rows, columns)
                    print(f"  ✓ 完成: 添加 {inserted_count} 条，更新 {updated_count} 条")
                else:
                    # 创建简单表（单列）
                    create_simple_table(conn, schema_name)
                    # 插入数据
                    inserted_count = insert_data_into_simple_table(conn, schema_name, data_rows)
                    print(f"  ✓ 完成: 添加 {inserted_count} 条数据")
            
            # 验证数据
            cursor = conn.cursor()
            cursor.execute(f'SELECT COUNT(*) FROM "{schema_name}"')
            count = cursor.fetchone()[0]
            print(f"  → 表 '{schema_name}' 中共有 {count} 条数据")
        
        print("\n" + "=" * 60)
        print("✓ 所有数据修改完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()