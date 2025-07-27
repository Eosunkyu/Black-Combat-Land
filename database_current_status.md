# 데이터베이스 현재 상황

## 게시판 (boards) 테이블 현재 상태

기본 게시판 데이터 (schema.sql 기준):

| ID | 이름 | route | 설명 |
|----|------|-------|------|
| 1 | 자유 | free | 자유롭게 이야기를 나눌 수 있는 게시판 |
| 2 | 익명 | anonymous | 익명으로 글을 작성할 수 있는 게시판 |
| 3 | 경기소식 | game_news | 블랙 컴뱃 경기 소식을 공유하는 게시판 |
| 4 | VIP | vip | VIP 회원만 접근할 수 있는 게시판 |
| 5 | 블컴뉴스 | news | 블랙 컴뱃 관련 뉴스를 공유하는 게시판 |
| 6 | 경기예측/분석 | analysis | 경기 예측과 분석을 공유하는 게시판 |
| 7 | 질문 | question | 질문과 답변을 주고받는 게시판 |
| 8 | BCN | support | 선수들을 응원하는 메시지를 작성하는 게시판 |

## 변경이 필요한 항목

### 1. 예측/분석 → EVENT
- **현재**: name='경기예측/분석', route='analysis'
- **변경 후**: name='EVENT', route='event' (또는 기존 route 유지)
- **권한**: 회색 VIP만 사용 가능

### 2. 경기소식 → 넘버링
- **현재**: name='경기소식', route='game_news'
- **변경 후**: name='넘버링', route='numbering' (또는 기존 route 유지)
- **권한**: 회색 VIP만 사용 가능

### 3. 선수응원 → STORE
- **현재**: name='BCN', route='support' (UI에서는 '선수응원'으로 표시)
- **변경 후**: name='STORE', route='store' (또는 기존 route 유지)
- **권한**: 노란색 VIP만 사용 가능

## VIP 시스템 확장 필요사항

현재 users 테이블의 VIP 시스템:
- `is_vip TINYINT(1)` - 단순 VIP 여부만 표시

**확장 필요**:
- VIP 등급 구분 (회색 VIP, 노란색 VIP)
- 게시판별 접근 권한 설정

## 관련 파일들

- `schema.sql` - 데이터베이스 스키마
- `app.py` - 메인 애플리케이션 (line 104-127에 기본 boards 데이터)
- `templates/layout.html` - 네비게이션 메뉴 (line 168-178)
- 기존 업데이트 파일들:
  - `db_update.sql`
  - `db_update_anonymous.sql`
  - `db_update_thumbnail.sql`
  - `database_migration.sql` 