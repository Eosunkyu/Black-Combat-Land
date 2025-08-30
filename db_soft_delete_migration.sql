-- 소프트 삭제 기능을 위한 데이터베이스 마이그레이션
-- 2025년 게시물/댓글 기록 보관을 위한 업데이트

-- posts 테이블에 소프트 삭제 관련 컬럼 추가
ALTER TABLE posts ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE posts ADD COLUMN deleted_at DATETIME NULL;
ALTER TABLE posts ADD COLUMN deleted_by INT NULL;

-- comments 테이블에 소프트 삭제 관련 컬럼 추가
ALTER TABLE comments ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE comments ADD COLUMN deleted_at DATETIME NULL;
ALTER TABLE comments ADD COLUMN deleted_by INT NULL;

-- 외래키 제약조건 추가 (삭제한 사용자 추적용)
ALTER TABLE posts ADD FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE comments ADD FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE SET NULL;

-- 인덱스 추가 (성능 향상용)
CREATE INDEX idx_posts_is_deleted ON posts(is_deleted);
CREATE INDEX idx_comments_is_deleted ON comments(is_deleted);
CREATE INDEX idx_posts_deleted_at ON posts(deleted_at);
CREATE INDEX idx_comments_deleted_at ON comments(deleted_at);

-- 기존 데이터 확인용 쿼리 (실행 후 결과 확인)
SELECT 'posts 테이블 컬럼 추가 완료' as status;
DESCRIBE posts;

SELECT 'comments 테이블 컬럼 추가 완료' as status;
DESCRIBE comments;
