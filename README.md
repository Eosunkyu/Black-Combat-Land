# BLACK COMBAT LAND

BLACK COMBAT LAND는 격투기 커뮤니티 웹사이트입니다. 이 프로젝트는 Flask 웹 프레임워크와 MySQL 데이터베이스를 사용하여 개발되었습니다.

## 주요 기능

- 회원 시스템: 회원가입, 로그인, 프로필 관리
- 게시판 기능: 총 8개의 게시판 (자유, 익명, 프로모션, 블컴뉴스, 선수에게, 운영진에게, VIP, 질문)
- 댓글 시스템: 게시글에 댓글 작성, 익명 댓글 지원
- 좋아요 기능: 게시글에 좋아요 추가/취소
- VIP 회원 시스템: 관리자 승인으로 VIP 회원 지정
- 광고 관리: 관리자가 광고 추가/수정/삭제, 게시글 열람 시 랜덤 광고 표시
- 파일 업로드: 게시글 작성 시 이미지 업로드
- 반응형 디자인: 모바일 환경 지원

## 기술 스택

- **Backend**: Python, Flask
- **Database**: MySQL
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Authentication**: Flask-Login, Bcrypt
- **File Upload**: Werkzeug

## 설치 및 실행 방법

### 1. 프로젝트 클론

```bash
git clone https://github.com/yourusername/blackcombat.git
cd blackcombat
```

### 2. 가상환경 설정 및 패키지 설치

```bash
python -m venv venv
source venv/bin/activate  # Windows의 경우: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 데이터베이스 설정

MySQL에 접속하여 schema.sql 파일 실행:

```bash
mysql -u root -p < schema.sql
```

### 4. 환경 변수 설정

`.env` 파일 생성 및 다음 내용 추가:

```
SECRET_KEY=your_secret_key
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DB=blackcombat
UPLOAD_FOLDER=static/uploads
```

### 5. 애플리케이션 실행

```bash
python app.py
```

서버가 실행되면 웹 브라우저에서 `http://localhost:5000`으로 접속하세요.

## 기본 계정 정보

- **관리자 계정**
  - 아이디: admin
  - 비밀번호: admin123

## 게시판 구조

1. **자유게시판**: 일반적인 주제로 자유롭게 대화
2. **익명게시판**: 로그인하지 않아도 이용 가능한 익명 게시판
3. **프로모션**: 각종 이벤트 및 프로모션 정보 공유
4. **블컴뉴스**: 블랙 컴뱃 관련 뉴스 및 정보
5. **선수에게**: 선수들에게 메시지를 남기는 게시판
6. **운영진에게**: 운영진에게 문의나 피드백을 남기는 게시판
7. **VIP게시판**: VIP 회원만 이용 가능한 특별 게시판
8. **질문게시판**: 질문과 답변을 위한 게시판
