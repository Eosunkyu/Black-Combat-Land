-- 공지사항 댓글 기능 추가를 위한 데이터베이스 업데이트

-- 공지사항 댓글 테이블 생성
CREATE TABLE IF NOT EXISTS notice_comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    notice_id INT NOT NULL,
    user_id INT NOT NULL DEFAULT 0,
    content TEXT NOT NULL,
    is_anonymous TINYINT(1) NOT NULL DEFAULT 0,
    ip_address VARCHAR(45) NULL,
    anonymous_password VARCHAR(255) NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (notice_id) REFERENCES notices(id) ON DELETE CASCADE,
    INDEX idx_notice_id (notice_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; 