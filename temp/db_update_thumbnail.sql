-- 썸네일 기능 추가를 위한 데이터베이스 업데이트
-- 실행 방법: mysql -u root -p blackcombat < db_update_thumbnail.sql

USE blackcombat;

-- posts 테이블에 thumbnail_path 컬럼 추가
ALTER TABLE posts ADD COLUMN thumbnail_path VARCHAR(255) NULL AFTER image_path;

-- 업데이트 완료 확인
SELECT 'Thumbnail feature database update completed successfully!' as status; 