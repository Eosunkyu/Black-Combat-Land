# 데이터베이스 업데이트 실행 가이드

## 1. 사전 준비사항

### 1.1 백업 생성
```sql
-- 전체 데이터베이스 백업 (권장)
mysqldump -u [username] -p blackcombat > backup_$(date +%Y%m%d_%H%M%S).sql

-- 또는 중요 테이블만 백업
CREATE TABLE boards_backup AS SELECT * FROM boards;
CREATE TABLE users_backup AS SELECT * FROM users;
```

### 1.2 현재 상태 확인
```sql
-- 현재 게시판 목록 확인
SELECT id, name, route, description FROM boards ORDER BY id;

-- 현재 VIP 사용자 확인
SELECT id, username, nickname, is_vip FROM users WHERE is_vip = 1;
```

## 2. 업데이트 실행 순서

### 2.1 단계별 실행
1. **백업 생성** (필수)
2. **`db_update_board_names.sql` 실행**
3. **결과 확인**
4. **애플리케이션 코드 업데이트** (app.py, templates)

### 2.2 실행 명령어
```bash
# MySQL 접속
mysql -u [username] -p blackcombat

# SQL 파일 실행
source db_update_board_names.sql;
```

## 3. 예상 결과

### 3.1 변경된 게시판 목록
| ID | 변경 전 | 변경 후 | VIP 권한 |
|----|---------|---------|----------|
| 3 | 경기소식 | 넘버링 | 회색 VIP |
| 6 | 경기예측/분석 | EVENT | 회색 VIP |
| 8 | BCN | STORE | 노란색 VIP |

### 3.2 새로운 컬럼
- `users.vip_type`: none, gray, yellow
- `boards.required_vip_type`: none, gray, yellow

## 4. 문제 발생 시 대응

### 4.1 오류 발생 시
```sql
-- 트랜잭션 롤백 (가능한 경우)
ROLLBACK;

-- 백업에서 복원
-- boards 테이블 복원
DROP TABLE boards;
CREATE TABLE boards AS SELECT * FROM boards_backup;

-- users 테이블 복원 (VIP 컬럼 추가 후 오류 시)
ALTER TABLE users DROP COLUMN vip_type;
```

### 4.2 부분 롤백 쿼리
```sql
-- 게시판 이름만 원래대로 복원
UPDATE boards SET name = '경기소식' WHERE route = 'game_news';
UPDATE boards SET name = '경기예측/분석' WHERE route = 'analysis';
UPDATE boards SET name = 'BCN' WHERE route = 'support';

-- VIP 시스템 컬럼 제거
ALTER TABLE users DROP COLUMN vip_type;
ALTER TABLE boards DROP COLUMN required_vip_type;
```

## 5. 후속 작업

### 5.1 애플리케이션 코드 수정 필요 파일들
- `app.py` (line 104-127): boards 기본값 수정
- `templates/layout.html` (line 168-178): 네비게이션 메뉴
- 기타 템플릿 파일들에서 게시판 이름 참조 부분

### 5.2 VIP 권한 체크 로직 추가
- 게시판 접근 시 `required_vip_type` 확인
- 사용자의 `vip_type`과 매칭 검증

## 6. 테스트 체크리스트

- [ ] 백업 파일 생성 확인
- [ ] SQL 실행 완료
- [ ] 게시판 이름 변경 확인
- [ ] VIP 컬럼 추가 확인
- [ ] 기존 VIP 사용자 vip_type 설정 확인
- [ ] 웹사이트 정상 작동 확인
- [ ] VIP 권한 체크 로직 테스트 