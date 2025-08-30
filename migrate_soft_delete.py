#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mysql.connector
from dotenv import load_dotenv
import os
import sys

def main():
    # .env 파일 로드
    load_dotenv()
    
    print("소프트 삭제 마이그레이션을 시작합니다...")
    
    try:
        # 데이터베이스 연결
        connection = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DATABASE'),
            charset='utf8mb4'
        )
        cursor = connection.cursor()
        
        print(f"데이터베이스 '{os.getenv('MYSQL_DATABASE')}'에 연결되었습니다.")
        
        # posts 테이블에 소프트 삭제 컬럼이 있는지 확인
        cursor.execute('DESCRIBE posts')
        columns = [col[0] for col in cursor.fetchall()]
        
        if 'is_deleted' not in columns:
            print('소프트 삭제 컬럼이 없습니다. 마이그레이션을 실행합니다...')
            
            # 마이그레이션 SQL 명령어들
            migration_sqls = [
                "ALTER TABLE posts ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0",
                "ALTER TABLE posts ADD COLUMN deleted_at DATETIME NULL",
                "ALTER TABLE posts ADD COLUMN deleted_by INT NULL",
                "ALTER TABLE comments ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0",
                "ALTER TABLE comments ADD COLUMN deleted_at DATETIME NULL", 
                "ALTER TABLE comments ADD COLUMN deleted_by INT NULL",
                "ALTER TABLE posts ADD FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL",
                "ALTER TABLE comments ADD FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL",
                "CREATE INDEX idx_posts_is_deleted ON posts(is_deleted)",
                "CREATE INDEX idx_comments_is_deleted ON comments(is_deleted)",
                "CREATE INDEX idx_posts_deleted_at ON posts(deleted_at)",
                "CREATE INDEX idx_comments_deleted_at ON comments(deleted_at)"
            ]
            
            for i, sql in enumerate(migration_sqls, 1):
                try:
                    cursor.execute(sql)
                    connection.commit()
                    print(f"[{i}/{len(migration_sqls)}] ✓ {sql[:50]}...")
                except Exception as e:
                    print(f"[{i}/{len(migration_sqls)}] ✗ 오류: {e}")
                    print(f"    SQL: {sql}")
                    if "Duplicate" not in str(e):  # 중복 오류가 아니면 실패로 처리
                        return False
            
            print("\n마이그레이션이 성공적으로 완료되었습니다! ✅")
            print("이제 다음 기능들을 사용할 수 있습니다:")
            print("- 게시물/댓글 소프트 삭제 (데이터 보존)")
            print("- 삭제된 게시물 복구")
            print("- 관리자 페이지에서 삭제된 게시물 관리")
            
        else:
            print('소프트 삭제 컬럼이 이미 존재합니다. ✓')
            
        # 마이그레이션 후 테이블 상태 확인
        cursor.execute('DESCRIBE posts')
        post_columns = cursor.fetchall()
        
        cursor.execute('DESCRIBE comments') 
        comment_columns = cursor.fetchall()
        
        print(f"\nposts 테이블 컬럼 수: {len(post_columns)}")
        print(f"comments 테이블 컬럼 수: {len(comment_columns)}")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 오류: {e}")
        print("\n수동으로 다음 SQL 파일을 실행해주세요:")
        print("mysql -u [username] -p [database] < db_soft_delete_migration.sql")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
