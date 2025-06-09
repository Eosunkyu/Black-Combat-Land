from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
import secrets
from markupsafe import Markup
import json
import re
import random
import pytz

# 애플리케이션 팩토리 패턴 적용
def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = secrets.token_hex(16)
    app.config['TIMEZONE'] = 'Asia/Seoul'
    app.config['MYSQL_TIMEZONE'] = '+09:00'  # 한국 시간(UTC+9)
    # 세션 설정 개선
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # 세션 유지 기간 7일로 설정
    app.config['SESSION_COOKIE_SECURE'] = False  # 개발환경에서는 False, 배포 시 True로 변경
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_USE_SIGNER'] = True  # 쿠키 서명 활성화
    # 이모티콘 지원을 위한 MySQL 설정 강화
    app.config['MYSQL_CHARSET'] = 'utf8mb4'
    app.config['MYSQL_USE_UNICODE'] = True
    app.config['MYSQL_CUSTOM_OPTIONS'] = {
        'charset': 'utf8mb4',
        'use_unicode': True,
        'init_command': "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci; SET character_set_connection=utf8mb4; SET character_set_client=utf8mb4; SET character_set_results=utf8mb4;"
    }
    #app.config['MYSQL_HOST'] = 'localhost'
    #app.config['MYSQL_USER'] = 'root'
    #app.config['MYSQL_PASSWORD'] = '1234' # MySQL 비밀번호 설정
    app.config['MYSQL_HOST'] = '13.125.219.53'
    app.config['MYSQL_USER'] = 'adminUser'
    app.config['MYSQL_PASSWORD'] = 'tjsrbQhshd!@34' # MySQL 비밀번호 설정
    app.config['MYSQL_DB'] = 'blackcombat'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 최대 16MB 파일
    
    # MySQL, Bcrypt, LoginManager 초기화
    mysql = MySQL(app)
    bcrypt = Bcrypt(app)
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'  # 로그인 페이지 경로 설정

    # CSRF 보호 기능 활성화
    csrf = CSRFProtect(app)
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_SECRET_KEY'] = app.config['SECRET_KEY']  # 또는 별도의 키 사용

    # Extensions를 current_app에서 접근할 수 있도록 등록
    app.extensions['mysql'] = mysql
    app.extensions['bcrypt'] = bcrypt

    # Blueprint 등록은 create_app 함수 내부에서
    from routes.auth import auth
    from routes.board import board_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(board_bp)
    app.register_blueprint(admin_bp)
    
    return app, mysql, bcrypt, login_manager, csrf

app, mysql, bcrypt, login_manager, csrf = create_app()

# CSRF 예외 경로 추가 (필요한 경우)
@csrf.exempt
def some_view_func():
    pass

# 사용자 로더 콜백 함수
@login_manager.user_loader
def load_user(user_id):
    try:
        # user_id가 올바른 형식인지 확인
        user_id = int(user_id)
        
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close()
        
        if user:
            # 실제 UserMixin 상속 클래스 반환
            user_obj = UserMixin()
            user_obj.id = user['id']
            user_obj.username = user['username']
            user_obj.nickname = user['nickname']
            user_obj.is_admin = user['is_admin']
            user_obj.is_vip = user['is_vip']
            return user_obj
        
    except Exception as e:
        print(f"Error loading user: {e}")
    
    return None

# 전역 컨텍스트 프로세서
@app.context_processor
def inject_board_list():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT id, name, route FROM boards ORDER BY id')
        boards = cursor.fetchall()
        cursor.close()
        return dict(boards=boards)
    except:
        # DB 연결 실패 등의 경우 기본값 사용
        boards = [
            {'id': 1, 'name': '자유', 'route': 'free'},
            {'id': 2, 'name': '익명', 'route': 'anonymous'},
            {'id': 3, 'name': '경기소식', 'route': 'game_news'},
            {'id': 4, 'name': 'VIP', 'route': 'vip'},
            {'id': 5, 'name': '블컴뉴스', 'route': 'news'},
            {'id': 6, 'name': '경기예측/분석', 'route': 'analysis'},
            {'id': 7, 'name': '질문', 'route': 'question'},
            {'id': 8, 'name': '선수응원', 'route': 'support'}
        ]
        return dict(boards=boards)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf())

# VIP 타입 정보를 템플릿에 제공하는 함수
@app.context_processor
def inject_vip_types():
    # VIP 타입 상수 정의
    return dict(VIP_YELLOW=1, VIP_BLUE=2)

# 알림 정보 주입
@app.context_processor
def inject_notification_counts():
    if 'loggedin' in session and session['loggedin']:
        try:
            cur = mysql.connection.cursor()
            
            # 읽지 않은 쪽지 수 확인
            cur.execute('SELECT COUNT(*) as unread_count FROM messages WHERE receiver_id = %s AND is_read = 0 AND receiver_deleted = 0', (session['id'],))
            unread_count = cur.fetchone()['unread_count']
            
            # 친구 요청 수 확인
            cur.execute('SELECT COUNT(*) as request_count FROM friendships WHERE friend_id = %s AND status = "pending"', (session['id'],))
            friend_request_count = cur.fetchone()['request_count']
            
            cur.close()
            return dict(unread_count=unread_count, friend_request_count=friend_request_count)
        except:
            # 오류 발생 시 기본값 제공
            return dict(unread_count=0, friend_request_count=0)
    else:
        # 로그인하지 않은 경우 0으로 설정
        return dict(unread_count=0, friend_request_count=0)

# 이미지 업로드 API 엔드포인트
@app.route('/upload_image', methods=['POST'])
def upload_image():
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_FILE_SIZE = 16 * 1024 * 1024
    
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': '파일이 없습니다.'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': '파일이 선택되지 않았습니다.'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '허용되지 않는 파일 형식입니다.'})
    
    # 파일 크기 체크
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({'success': False, 'error': '파일 크기가 16MB를 초과합니다.'})
    
    try:
        seoul_timezone = pytz.timezone('Asia/Seoul')
        filename = secure_filename(file.filename or '')
        filename = f"{datetime.now(seoul_timezone).strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}_{filename}"
        
        upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        relative_path = os.path.join('static', 'uploads', filename).replace('\\', '/')
        
        return jsonify({'success': True, 'path': relative_path})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 홈페이지 라우트
@app.route('/')
def index():
    cur = mysql.connection.cursor()

    user_agent = request.headers.get('User-Agent')
    is_mobile = 'Mobile' in user_agent
    
    # 베스트 게시글 가져오기 (좋아요 수 기준)
    cur.execute('''
        SELECT 
            posts.id, 
            posts.title, 
            posts.created_at, 
            posts.view_count, 
            CASE 
                WHEN boards.route = 'anonymous' THEN '익명' 
                ELSE users.nickname 
            END as nickname,
            boards.name as board_name, 
            (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count,
            (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
            boards.route as board_route
        FROM posts 
        LEFT JOIN users ON posts.user_id = users.id
        JOIN boards ON posts.board_id = boards.id
        ORDER BY like_count DESC, posts.created_at DESC
        LIMIT 8
    ''')
    best_posts = cur.fetchall()
    
    # 각 게시판별 최신 게시글
    board_posts = {}
    
    # 게시판 목록 가져오기
    try:
        cur.execute('SELECT id, name, route FROM boards ORDER BY id')
        board_list = cur.fetchall()
    except:
        # DB 오류시 기본값 사용
        board_list = inject_board_list()['boards']
    
    for board in board_list:
        # 익명 게시판은 별도 처리 (user_id가 0인 게시물도 조회)
        if board['route'] == 'anonymous':
            cur.execute('''
                SELECT posts.id, posts.title, posts.created_at, posts.view_count, images_data,
                       '익명' as nickname, boards.route as board_route, boards.name as board_name,
                       (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                       (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count
                FROM posts 
                JOIN boards ON posts.board_id = boards.id
                WHERE posts.board_id = %s
                ORDER BY posts.created_at DESC
                LIMIT 8
            ''', (board['id'],))
        else:
            cur.execute('''
                SELECT posts.id, posts.title, posts.created_at, posts.view_count, images_data,
                        users.nickname, boards.route as board_route, boards.name as board_name,
                       (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                       (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count
                FROM posts 
                JOIN users ON posts.user_id = users.id
                JOIN boards ON posts.board_id = boards.id
                WHERE posts.board_id = %s
                ORDER BY posts.created_at DESC
                LIMIT 8
            ''', (board['id'],))
        board_posts[board['route']] = cur.fetchall()
    
    # 실시간 게시글 (모든 게시판에서 최신순으로)
    cur.execute('''
        SELECT 
            posts.id, 
            posts.title, 
            posts.created_at, 
            posts.view_count, 
            CASE 
                WHEN boards.route = 'anonymous' THEN '익명' 
                ELSE users.nickname 
            END as nickname,
            boards.name as board_name, 
            boards.route as board_route,
            (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count,
            (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count
        FROM posts 
        LEFT JOIN users ON posts.user_id = users.id
        JOIN boards ON posts.board_id = boards.id
        ORDER BY posts.created_at DESC
        LIMIT 15
    ''')
    realtime_posts = cur.fetchall()
    
    # 광고 가져오기 - 위치별로 구분
    banner_ad = None
    sidebar_ad = None
    footer_ad = None
    center_ad = None
    
    # 메인 배너 광고
    cur.execute('SELECT * FROM ads WHERE position = "banner" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    banner_ad = cur.fetchone()
    
    # 사이드바 광고
    cur.execute('SELECT * FROM ads WHERE position = "side" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    sidebar_ad = cur.fetchone()
    
    # 푸터 광고
    cur.execute('SELECT * FROM ads WHERE position = "footer" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    footer_ad = cur.fetchone()

    # 푸터 광고
    cur.execute('SELECT * FROM ads WHERE position = "center" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    center_ad = cur.fetchone()
    
    cur.close()
    return render_template('index.html', best_posts=best_posts, now=datetime.now(), board_posts=board_posts, 
                          realtime_posts=realtime_posts, banner_ad=banner_ad, 
                          sidebar_ad=sidebar_ad, footer_ad=footer_ad, center_ad=center_ad, is_mobile=is_mobile)

# robots.txt와 sitemap.xml 라우트 추가
@app.route('/robots.txt')
def robots_txt():
    return app.send_static_file('robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    return app.send_static_file('sitemap.xml')

# 개인정보처리방침 페이지
@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

# 템플릿 필터 등록
@app.template_filter('nl2br')
def nl2br(value):
    # 줄바꿈을 <br> 태그로 변환
    if value:
        return Markup(value.replace('\n', '<br>'))
    return value

@app.template_filter('fromjson')
def from_json(value):
    # JSON 문자열을 파이썬 객체로 변환
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []

# 동영상 URL을 임베드 URL로 변환하는 함수
@app.template_global()
def get_embed_url(url):
    """
    동영상 URL을 임베드 URL로 변환합니다.
    지원: YouTube, Vimeo, 네이버TV 등
    """
    # YouTube
    youtube_regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    youtube_match = re.search(youtube_regex, url)
    if youtube_match:
        return f'https://www.youtube.com/embed/{youtube_match.group(1)}'
    
    # Vimeo
    vimeo_regex = r'(?:https?:\/\/)?(?:www\.)?vimeo\.com\/(\d+)'
    vimeo_match = re.search(vimeo_regex, url)
    if vimeo_match:
        return f'https://player.vimeo.com/video/{vimeo_match.group(1)}'
    
    # 네이버TV
    naver_regex = r'(?:https?:\/\/)?(?:tv\.naver\.com\/v\/(\d+))'
    naver_match = re.search(naver_regex, url)
    if naver_match:
        return f'https://tv.naver.com/embed/{naver_match.group(1)}'
    
    # 지원하지 않는 URL은 그대로 반환
    return url

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0") 
