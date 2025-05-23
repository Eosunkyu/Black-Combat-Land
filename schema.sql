-- 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS blackcombat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE blackcombat;

-- 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    is_admin TINYINT(1) NOT NULL DEFAULT 0,
    is_vip TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    last_login DATETIME NULL
);

-- 비밀번호 재설정 토큰 테이블
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    used TINYINT(1) NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 게시판 테이블
CREATE TABLE IF NOT EXISTS boards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    route VARCHAR(50) NOT NULL UNIQUE,
    description TEXT NULL,
    created_at DATETIME NOT NULL
);

-- 게시글 테이블
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    board_id INT NOT NULL,
    user_id INT NOT NULL DEFAULT 0,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    image_path VARCHAR(255) NULL,
    images_data TEXT NULL,
    video_data TEXT NULL,
    view_count INT NOT NULL DEFAULT 0,
    is_anonymous TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NULL,
    FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
);

-- 댓글 테이블
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL DEFAULT 0,
    content TEXT NOT NULL,
    is_anonymous TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- 게시글 좋아요 테이블
CREATE TABLE IF NOT EXISTS post_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    UNIQUE KEY unique_post_user (post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- 광고 테이블
CREATE TABLE IF NOT EXISTS ads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    image_path VARCHAR(255) NULL,
    link VARCHAR(255) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL
);

-- 공지사항 테이블
CREATE TABLE IF NOT EXISTS notices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 쪽지 테이블
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    sender_deleted TINYINT(1) NOT NULL DEFAULT 0,
    receiver_deleted TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 친구 관계 테이블
CREATE TABLE IF NOT EXISTS friendships (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    friend_id INT NOT NULL,
    status ENUM('pending', 'accepted', 'rejected', 'blocked') NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL,
    updated_at DATETIME NULL,
    UNIQUE KEY unique_friendship (user_id, friend_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (friend_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 기본 게시판 데이터 삽입
INSERT INTO boards (name, route, description, created_at) VALUES
('자유', 'free', '자유롭게 이야기를 나눌 수 있는 게시판입니다.', NOW()),
('익명', 'anonymous', '익명으로 글을 작성할 수 있는 게시판입니다.', NOW()),
('경기소식', 'game_news', '블랙 컴뱃 경기 소식을 공유하는 게시판입니다.', NOW()),
('VIP', 'vip', 'VIP 회원만 접근할 수 있는 게시판입니다.', NOW()),
('블컴뉴스', 'news', '블랙 컴뱃 관련 뉴스를 공유하는 게시판입니다.', NOW()),
('경기예측/분석', 'analysis', '경기 예측과 분석을 공유하는 게시판입니다.', NOW()),
('질문', 'question', '질문과 답변을 주고받는 게시판입니다.', NOW()),
('선수응원', 'support', '선수들을 응원하는 메시지를 작성하는 게시판입니다.', NOW());

-- 기본 관리자 계정 생성 (비밀번호: admin123)
INSERT INTO users (username, password, nickname, is_admin, is_vip, created_at, email) VALUES
('admin', '$2b$12$1NvVOdMZrMvTJ/lYZx0QpuX8dxH5YLiDL9o/NbcRkCvEBHOCKf9gG', '관리자', 1, 1, NOW(), "altaicahorse@gmail.com"); 