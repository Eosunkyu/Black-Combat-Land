-- 광고 테이블에 position 필드 추가
ALTER TABLE ads ADD COLUMN position VARCHAR(50) DEFAULT 'banner' AFTER link;

-- 광고 테이블에서 link 필드명을 link_url로 변경
ALTER TABLE ads CHANGE COLUMN link link_url VARCHAR(255); 