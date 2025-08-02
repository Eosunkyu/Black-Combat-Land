-- 게시판 명칭 변경 및 VIP 시스템 확장 업데이트
-- 실행일: 2025년 

-- 1. 기존 데이터 백업을 위한 임시 테이블 생성 (선택사항)
-- CREATE TABLE boards_backup AS SELECT * FROM boards;

-- 2. 게시판 명칭 변경
-- 2-1. 경기예측/분석 → EVENT (회색 VIP 전용)
UPDATE boards 
SET name = 'VIP', 
    description = 'vip게시판입니다.'
WHERE route = 'vip';


UPDATE boards 
SET name = 'EVENT', 
    description = 'EVENT 관련 정보를 공유하는 게시판입니다.'
WHERE route = 'analysis';

-- 2-2. 경기소식 → 넘버링 (회색 VIP 전용)
UPDATE boards 
SET name = '넘버링', 블컴소식식
    description = '넘버링 관련 정보를 공유하는 게시판입니다.'
WHERE route = 'news';

-- 2-3. BCN → STORE (노란색 VIP 전용)
UPDATE boards 
SET name = 'BCN', 
    description = '기자 관련 게시판입니다.'
WHERE route = 'support';

-- 3. VIP 시스템 확장
-- 3-1. users 테이블에 VIP 등급 컬럼 추가
ALTER TABLE users ADD COLUMN vip_type ENUM('none', 'gray', 'yellow') NOT NULL DEFAULT 'none' AFTER is_vip;

-- 3-2. 기존 VIP 사용자들을 회색 VIP로 설정 (기본값)
UPDATE users SET vip_type = 'gray' WHERE is_vip = 1;

-- 3-3. boards 테이블에 VIP 권한 컬럼 추가
ALTER TABLE boards ADD COLUMN required_vip_type ENUM('none', 'gray', 'yellow') NULL AFTER description;

-- 3-4. 게시판별 VIP 권한 설정
UPDATE boards SET required_vip_type = 'gray' WHERE route = 'analysis';  -- EVENT (회색 VIP)
UPDATE boards SET required_vip_type = 'gray' WHERE route = 'game_news'; -- 넘버링 (회색 VIP)
UPDATE boards SET required_vip_type = 'yellow' WHERE route = 'support'; -- STORE (노란색 VIP)
UPDATE boards SET required_vip_type = 'gray' WHERE route = 'vip';       -- 기존 VIP 게시판 (회색 VIP)

-- 4. 변경사항 확인 쿼리
SELECT id, name, route, description, required_vip_type FROM boards ORDER BY id;

-- 5. VIP 사용자 현황 확인 쿼리
SELECT id, username, nickname, is_vip, vip_type FROM users WHERE is_vip = 1; 