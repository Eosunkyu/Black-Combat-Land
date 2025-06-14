-- post_likes 테이블에 ip_address 컬럼 추가 및 user_id NULL 허용
ALTER TABLE post_likes 
    MODIFY COLUMN user_id INT NULL,
    ADD COLUMN ip_address VARCHAR(45) NULL;

-- 기존 데이터의 ip_address를 NULL로 설정 (로그인 사용자의 추천)
UPDATE post_likes SET ip_address = NULL WHERE user_id IS NOT NULL; 