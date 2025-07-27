-- 게시판 명칭 변경 및 VIP 시스템 확장 롤백 쿼리
-- 실행일: 2025년
-- 주의: 이 쿼리는 db_update_board_names.sql의 변경사항을 되돌립니다.

-- 1. 게시판 이름 원상복구
-- 1-1. EVENT → 경기예측/분석
UPDATE boards 
SET name = '경기예측/분석', 
    description = '경기 예측과 분석을 공유하는 게시판입니다.'
WHERE route = 'analysis';

-- 1-2. 넘버링 → 경기소식
UPDATE boards 
SET name = '경기소식', 
    description = '블랙 컴뱃 경기 소식을 공유하는 게시판입니다.'
WHERE route = 'game_news';

-- 1-3. STORE → BCN
UPDATE boards 
SET name = 'BCN', 
    description = '선수들을 응원하는 메시지를 작성하는 게시판입니다.'
WHERE route = 'support';

-- 2. VIP 시스템 관련 컬럼 제거
-- 2-1. boards 테이블에서 VIP 권한 컬럼 제거
ALTER TABLE boards DROP COLUMN IF EXISTS required_vip_type;

-- 2-2. users 테이블에서 VIP 타입 컬럼 제거
ALTER TABLE users DROP COLUMN IF EXISTS vip_type;

-- 3. 변경사항 확인
SELECT id, name, route, description FROM boards ORDER BY id;

-- 4. VIP 사용자 확인
SELECT id, username, nickname, is_vip FROM users WHERE is_vip = 1;

-- 5. 백업 테이블 제거 (백업 테이블을 만들었던 경우)
-- DROP TABLE IF EXISTS boards_backup;
-- DROP TABLE IF EXISTS users_backup; 