-- 익명게시판 기능 향상을 위한 데이터베이스 업데이트

-- posts 테이블에 익명 사용자용 비밀번호 필드 추가
ALTER TABLE posts ADD COLUMN anonymous_password VARCHAR(255) NULL AFTER ip_address;

-- comments 테이블에 익명 사용자용 비밀번호 필드 추가  
ALTER TABLE comments ADD COLUMN anonymous_password VARCHAR(255) NULL AFTER ip_address;

-- IP 기반 익명 사용자 닉네임 관리 테이블 생성
CREATE TABLE IF NOT EXISTS anonymous_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip_address VARCHAR(45) NOT NULL,
    ip_hash VARCHAR(64) NOT NULL UNIQUE,
    nickname VARCHAR(50) NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_ip_hash (ip_hash),
    INDEX idx_ip_address (ip_address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 기존 익명 게시글/댓글의 IP 주소가 누락된 경우를 위한 기본값 설정
UPDATE posts SET ip_address = '0.0.0.0' WHERE is_anonymous = 1 AND ip_address IS NULL;
UPDATE comments SET ip_address = '0.0.0.0' WHERE is_anonymous = 1 AND ip_address IS NULL; 