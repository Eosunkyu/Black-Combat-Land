# type: ignore
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, jsonify, current_app
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import random
import json
import re
import pytz
import hashlib

seoul_timezone = pytz.timezone('Asia/Seoul')

board_bp = Blueprint('board', __name__)

# 필요한 객체는 current_app을 통해 접근
def get_mysql():
    return current_app.extensions['mysql']

def get_bcrypt():
    return current_app.extensions['bcrypt']

# 익명 사용자 닉네임 생성 및 관리 함수들
def get_anonymous_nickname(ip_address):
    """IP 주소 기반으로 익명 닉네임을 생성하거나 기존 닉네임을 반환합니다."""
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    # IP 주소 해시 생성 (보안을 위해)
    ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()
    
    # 기존 익명 사용자 확인
    cur.execute('SELECT nickname FROM anonymous_users WHERE ip_hash = %s', (ip_hash,))
    existing_user = cur.fetchone()
    
    if existing_user:
        cur.close()
        return existing_user['nickname']
    
    # 새로운 익명 사용자 생성
    # 현재 익명 사용자 수 확인
    cur.execute('SELECT COUNT(*) as count FROM anonymous_users')
    user_count = cur.fetchone()['count']
    
    # 블랜1, 블랜2 형식으로 닉네임 생성
    nickname = f"익명"
    
    # 중복 확인 (혹시 모를 경우를 대비)
    while True:
        cur.execute('SELECT id FROM anonymous_users WHERE nickname = %s', (nickname,))
        if not cur.fetchone():
            break
        user_count += 1
        nickname = f"익명"
    
    # 새 익명 사용자 등록
    cur.execute('''
        INSERT INTO anonymous_users (ip_address, ip_hash, nickname, created_at)
        VALUES (%s, %s, %s, NOW())
    ''', (ip_address, ip_hash, nickname))
    mysql.connection.commit()
    cur.close()
    
    return nickname

def hash_anonymous_password(password):
    """익명 사용자 비밀번호 해시"""
    bcrypt = get_bcrypt()
    return bcrypt.generate_password_hash(password).decode('utf-8')

def check_anonymous_password(password, hashed):
    """익명 사용자 비밀번호 검증"""
    bcrypt = get_bcrypt()
    return bcrypt.check_password_hash(hashed, password)

# 허용된 파일 확장자 체크
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 최대 파일 크기 (16MB)
MAX_FILE_SIZE = 16 * 1024 * 1024

# 게시판 메인 화면
@board_bp.route('/board/<string:board_route>')
def board_main(board_route):
    # MySQL 연결 가져오기
    mysql = get_mysql()
    cur = mysql.connection.cursor()

    user_agent = request.headers.get('User-Agent')
    is_mobile = 'Mobile' in user_agent

    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    
    
    # 페이지네이션
    page = request.args.get('page', 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page
    
    # 활성화된 공지사항 조회 (최대 10개까지)
    cur.execute('''
        SELECT notices.*, users.nickname
        FROM notices
        JOIN users ON notices.user_id = users.id
        WHERE notices.is_active = 1
        ORDER BY notices.created_at DESC
        LIMIT 10
    ''')
    notices = cur.fetchall()
    
    # 게시글 조회
    if board['route'] == 'anonymous':
        # 익명 게시판은 단순히 '익명'으로 표시
        cur.execute('''
            SELECT posts.*, posts.ip_address, posts.images_data, posts.content, posts.created_at,
                  (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                  (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count, boards.name as board_name
            FROM posts
            JOIN boards ON posts.board_id = boards.id
            WHERE posts.board_id = %s
            ORDER BY posts.created_at DESC
            LIMIT %s OFFSET %s
        ''', (board['id'], per_page, offset))
        
        posts = cur.fetchall()
        # 익명 게시판에서는 게시글에 단순히 '익명' 설정
        for post in posts:
            post['nickname'] = '익명'
    else:
        # 일반 게시판은 작성자 정보 표시
        cur.execute('''
            SELECT posts.*, users.nickname, users.is_vip, posts.images_data, posts.content, posts.created_at,
                  (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                  (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count,
                  boards.name as board_name, boards.route as route
            FROM posts
            JOIN users ON posts.user_id = users.id
            JOIN boards ON posts.board_id = boards.id
            WHERE posts.board_id = %s
            ORDER BY posts.created_at DESC
            LIMIT %s OFFSET %s
        ''', (board['id'], per_page, offset))
        
        posts = cur.fetchall()
    
    # 총 게시글 수 조회 (페이지네이션용)
    cur.execute('SELECT COUNT(*) as count FROM posts WHERE board_id = %s', (board['id'],))
    total_count = cur.fetchone()['count']
    total_pages = (total_count + per_page - 1) // per_page
    
    # 위치별 광고 선택
    # 사이드바 광고
    cur.execute('SELECT * FROM ads WHERE position = "side" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    sidebar_ad = cur.fetchone()
    
    # 배너 광고
    cur.execute('SELECT * FROM ads WHERE position = "banner" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    banner_ad = cur.fetchone()
    
    # 푸터 광고
    cur.execute('SELECT * FROM ads WHERE position = "footer" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    footer_ad = cur.fetchone()
    
    cur.close()
    
    # 현재 날짜 정보 가져오기
    now = datetime.now(seoul_timezone).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('board/list.html', board=board, posts=posts, notices=notices,
                          page=page, total_pages=total_pages, now=now,
                          sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)

# 게시글 작성 화면
@board_bp.route('/board/<string:board_route>/write', methods=['GET', 'POST'])
def write_post(board_route):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    cur = mysql.connection.cursor()

    user_agent = request.headers.get('User-Agent')
    is_mobile = 'Mobile' in user_agent

    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    # VIP 게시판 접근 권한 체크
    if board['route'] == 'support' and ('loggedin' not in session or not session.get('is_vip') == 2):
        flash('BCN 게시판은 BCN 회원만 글을 작성할 수 있습니다.', 'danger')
        return redirect(url_for('board.board_main', board_route=board_route))

    # VIP 게시판 접근 권한 체크
    if board['route'] == 'vip' and ('loggedin' not in session or not session.get('is_vip') == 1):
        flash('VIP 게시판은 VIP 회원만 글을 작성할 수 있습니다.', 'danger')
        return redirect(url_for('board.board_main', board_route=board_route))
    
    # 익명 게시판이 아닌 경우 로그인 필요
    if board['route'] != 'anonymous' and 'loggedin' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))
    
    # 위치별 광고 선택
    # 사이드바 광고
    cur.execute('SELECT * FROM ads WHERE position = "side" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    sidebar_ad = cur.fetchone()
    
    # 배너 광고
    cur.execute('SELECT * FROM ads WHERE position = "banner" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    banner_ad = cur.fetchone()
    
    # 푸터 광고
    cur.execute('SELECT * FROM ads WHERE position = "footer" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    footer_ad = cur.fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        ip_address = request.remote_addr
        
        # 익명 게시판인 경우 비밀번호 처리
        anonymous_password = None
        if board['route'] == 'anonymous':
            password = request.form.get('anonymous_password', '').strip()
            if not password:
                flash('익명 게시판에서는 비밀번호를 입력해야 합니다.', 'danger')
                return render_template('board/write.html', board=board, 
                                      sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
            if len(password) < 4:
                flash('비밀번호는 최소 4자리 이상이어야 합니다.', 'danger')
                return render_template('board/write.html', board=board, 
                                      sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
            anonymous_password = hash_anonymous_password(password)
        
        cur.execute('''
            SELECT * FROM blocked_ips 
            WHERE ip_address = %s AND (expires_at IS NULL OR expires_at > NOW())
        ''', (ip_address,))
        blocked_ip = cur.fetchone()
        
        if blocked_ip:
            reason = f" (사유: {blocked_ip['reason']})" if blocked_ip['reason'] else ""
            cur.close()
            flash(f'차단된 IP 주소입니다{reason}. 관리자에게 문의하세요.', 'danger')
            return redirect(url_for('board.board_main', board_route=board_route))
        # 차단된 사용자인지 확인
        if board['route'] != 'anonymous' and 'loggedin' in session:
            user_id = session['id']
            cur.execute('''
                SELECT * FROM blocked_users 
                WHERE user_id = %s AND (expires_at IS NULL OR expires_at > NOW())
            ''', (user_id,))
            blocked_user = cur.fetchone()
            
            if blocked_user:
                reason = f" (사유: {blocked_user['reason']})" if blocked_user['reason'] else ""
                cur.close()
                flash(f'차단된 사용자입니다{reason}. 관리자에게 문의하세요.', 'danger')
                return redirect(url_for('board.board_main', board_route=board_route))
        # 입력값 검증
        if not title or not content:
            flash('제목과 내용을 모두 입력해주세요.', 'danger')
            return render_template('board/write.html', board=board, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        # 제목 길이 검증
        if len(title) > 50:
            flash('제목은 50자 이내로 입력해주세요.', 'danger')
            return render_template('board/write.html', board=board, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        # 동영상 데이터 처리
        video_data = request.form.get('video_data', '[]')
        
        # 게시글 저장
        user_id = session.get('id', 0) if board['route'] != 'anonymous' else 0
        
        cur.execute('''
            INSERT INTO posts (board_id, user_id, title, content, video_data, created_at, view_count, is_anonymous, ip_address, anonymous_password)
            VALUES (%s, %s, %s, %s, %s, NOW(), 0, %s, %s, %s)
        ''', (board['id'], user_id, title, content, video_data, 1 if board['route'] == 'anonymous' else 0, ip_address, anonymous_password))
        
        mysql.connection.commit()
        post_id = cur.lastrowid
        cur.close()
        
        flash('게시글이 등록되었습니다.', 'success')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    return render_template('board/write.html', board=board, 
                          sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad)

# 게시글 상세보기
@board_bp.route('/board/<string:board_route>/<int:post_id>')
def view_post(board_route, post_id):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    cur = mysql.connection.cursor()

    user_agent = request.headers.get('User-Agent')
    is_mobile = 'Mobile' in user_agent

    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    
    
    # 게시글 조회
    cur.execute('''
        SELECT posts.*, users.nickname, users.is_vip
        FROM posts
        LEFT JOIN users ON posts.user_id = users.id
        WHERE posts.id = %s AND posts.board_id = %s
    ''', (post_id, board['id']))
    
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    
    # 익명 게시판인 경우 IP 기반 닉네임 설정
    if post['is_anonymous'] and post['ip_address']:
        post['nickname'] = '익명'  # 게시글은 단순히 '익명'으로 표시
    elif post['is_anonymous']:
        post['nickname'] = '익명'
    
    # 현재 로그인한 사용자가 관리자인지 확인
    is_admin = session.get('is_admin', False)
    
    # 이미지 데이터 처리
    images_data = None
    if post.get('images_data'):
        try:
            images_data = json.loads(post['images_data'])
        except (json.JSONDecodeError, TypeError):
            pass
    
    # 이전 형식의 단일 이미지 처리
    if post.get('image_path') and not images_data:
        # 단일 이미지를 images_data 형식에 맞게 변환
        images_data = {
            'paths': [post['image_path']],
            'captions': ['']
        }
    
    # 조회수 증가
    cur.execute('UPDATE posts SET view_count = view_count + 1 WHERE id = %s', (post_id,))
    mysql.connection.commit()
    
    # 댓글 조회
    cur.execute('''
        SELECT comments.*, users.nickname, users.is_vip
        FROM comments
        LEFT JOIN users ON comments.user_id = users.id
        WHERE comments.post_id = %s
        ORDER BY comments.created_at ASC
    ''', (post_id,))
    
    comments = cur.fetchall()
    
    # 익명 댓글의 IP 기반 닉네임 설정
    for comment in comments:
        if comment['is_anonymous'] and comment['ip_address']:
            comment['nickname'] = '익명'  # 댓글도 단순히 '익명'으로 표시
        elif comment['is_anonymous']:
            comment['nickname'] = '익명'
    
    # 좋아요 정보 조회
    like_count = 0
    is_liked = False
    
    cur.execute('SELECT COUNT(*) as count FROM post_likes WHERE post_id = %s', (post_id,))
    like_result = cur.fetchone()
    like_count = like_result['count'] if like_result else 0
    
    if 'loggedin' in session:
        cur.execute('SELECT * FROM post_likes WHERE post_id = %s AND user_id = %s', (post_id, session['id']))
        is_liked = bool(cur.fetchone())
    
    # 위치별 광고 선택
    # 사이드바 광고
    cur.execute('SELECT * FROM ads WHERE position = "side" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    sidebar_ad = cur.fetchone()
    
    # 배너 광고
    cur.execute('SELECT * FROM ads WHERE position = "banner" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    banner_ad = cur.fetchone()
    
    # 푸터 광고
    cur.execute('SELECT * FROM ads WHERE position = "footer" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    footer_ad = cur.fetchone()

    # 푸터 광고
    cur.execute('SELECT * FROM ads WHERE position = "center" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    center_ad = cur.fetchone()
    
    # 댓글 아래에 표시할 게시판 리스트 조회
    page = request.args.get('page', 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page
    
    # 총 게시글 수 조회 (페이지네이션용)
    cur.execute('SELECT COUNT(*) as count FROM posts WHERE board_id = %s', (board['id'],))
    total_count = cur.fetchone()['count']
    total_pages = (total_count + per_page - 1) // per_page
    
    if board['route'] == 'anonymous':
        cur.execute('''
            SELECT posts.*, '익명' as nickname,
                   (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                   (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count
            FROM posts
            WHERE posts.board_id = %s
            ORDER BY posts.created_at DESC
            LIMIT %s OFFSET %s
        ''', (board['id'], per_page, offset))
    else:
        cur.execute('''
            SELECT posts.*, users.nickname, users.is_vip,
                   (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                   (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count
            FROM posts
            JOIN users ON posts.user_id = users.id
            WHERE posts.board_id = %s
            ORDER BY posts.created_at DESC
            LIMIT %s OFFSET %s
        ''', (board['id'], per_page, offset))
    posts = cur.fetchall()
    now = datetime.now(seoul_timezone).strftime('%Y-%m-%d %H:%M:%S')

    cur.close()
    
    return render_template('board/view.html', board=board, post=post,
                          comments=comments, like_count=like_count,
                          is_liked=is_liked, images_data=images_data,
                          sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad,
                          center_ad=center_ad, posts=posts, now=now, is_admin=is_admin, 
                          is_mobile=is_mobile, page=page, total_pages=total_pages)

# 댓글 작성
@board_bp.route('/board/<string:board_route>/<int:post_id>/comment', methods=['POST'])
def write_comment(board_route, post_id):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    
    cur.execute('SELECT * FROM posts WHERE id = %s AND board_id = %s', (post_id, board['id']))
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    # 클라이언트 IP 주소 가져오기
    ip_address = request.remote_addr
    
    # 차단된 IP 주소인지 확인
    cur.execute('''
        SELECT * FROM blocked_ips 
        WHERE ip_address = %s AND (expires_at IS NULL OR expires_at > NOW())
    ''', (ip_address,))
    blocked_ip = cur.fetchone()
    
    if blocked_ip:
        reason = f" (사유: {blocked_ip['reason']})" if blocked_ip['reason'] else ""
        cur.close()
        flash(f'차단된 IP 주소입니다{reason}. 관리자에게 문의하세요.', 'danger')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    # 익명 게시판이 아닌 경우 로그인 필요
    if board['route'] != 'anonymous' and 'loggedin' not in session:
        flash('로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))
    
    content = request.form['content']
    
    # 익명 게시판인 경우 비밀번호 처리
    anonymous_password = None
    if board['route'] == 'anonymous':
        password = request.form.get('anonymous_password', '').strip()
        if not password:
            flash('익명 게시판에서는 비밀번호를 입력해야 합니다.', 'danger')
            return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
        if len(password) < 4:
            flash('비밀번호는 최소 4자리 이상이어야 합니다.', 'danger')
            return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
        anonymous_password = hash_anonymous_password(password)
    
    # 로그인한 사용자이고 익명 게시판이 아닌 경우 차단 여부 확인
    if 'loggedin' in session and board['route'] != 'anonymous':
        user_id = session['id']
        
        # 차단된 사용자인지 확인
        cur.execute('''
            SELECT * FROM blocked_users 
            WHERE user_id = %s AND (expires_at IS NULL OR expires_at > NOW())
        ''', (user_id,))
        blocked_user = cur.fetchone()
        
        if blocked_user:
            reason = f" (사유: {blocked_user['reason']})" if blocked_user['reason'] else ""
            cur.close()
            flash(f'차단된 사용자입니다{reason}. 관리자에게 문의하세요.', 'danger')
            return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    # 입력값 검증
    if not content:
        flash('댓글 내용을 입력해주세요.', 'danger')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 댓글 저장
    user_id = session.get('id', 0) if board['route'] != 'anonymous' else 0
    
    cur.execute('''
        INSERT INTO comments (post_id, user_id, content, created_at, is_anonymous, ip_address, anonymous_password)
        VALUES (%s, %s, %s, NOW(), %s, %s, %s)
    ''', (post_id, user_id, content, 1 if board['route'] == 'anonymous' else 0, ip_address, anonymous_password))
    
    mysql.connection.commit()
    cur.close()
    
    flash('댓글이 등록되었습니다.', 'success')
    return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))

# 게시글 좋아요
@board_bp.route('/board/<string:board_route>/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(board_route, post_id):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    
    cur.execute('SELECT * FROM posts WHERE id = %s AND board_id = %s', (post_id, board['id']))
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    
    # 이미 좋아요 했는지 확인
    cur.execute('SELECT * FROM post_likes WHERE post_id = %s AND user_id = %s', (post_id, session['id']))
    like = cur.fetchone()
    
    if like:
        # 이미 좋아요 했으면 취소
        cur.execute('DELETE FROM post_likes WHERE post_id = %s AND user_id = %s', (post_id, session['id']))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    else:
        # 좋아요 추가
        cur.execute('INSERT INTO post_likes (post_id, user_id, created_at) VALUES (%s, %s, NOW())', (post_id, session['id']))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))

# 게시글 수정 화면
@board_bp.route('/board/<string:board_route>/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_post(board_route, post_id):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    cur = mysql.connection.cursor()

    user_agent = request.headers.get('User-Agent')
    is_mobile = 'Mobile' in user_agent
    
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    
    # LEFT JOIN으로 변경하여 익명 게시글(user_id=0)도 처리할 수 있도록 함
    cur.execute('''
        SELECT posts.*, users.nickname
        FROM posts
        LEFT JOIN users ON posts.user_id = users.id
        WHERE posts.id = %s AND posts.board_id = %s
    ''', (post_id, board['id']))
    
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    
    # 익명 게시판이면 닉네임을 '익명'으로 설정
    if board['route'] == 'anonymous' or post['is_anonymous']:
        post['nickname'] = '익명'
    
    # 작성자 확인 (관리자는 항상 가능)
    if not session.get('is_admin') and post['user_id'] != session['id']:
        flash('게시글 수정 권한이 없습니다.', 'danger')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 이미지 데이터 처리
    images_data = None
    if post.get('images_data'):
        try:
            images_data = json.loads(post['images_data'])
        except (json.JSONDecodeError, TypeError):
            pass
    
    # 이전 형식의 단일 이미지 처리
    if post.get('image_path') and not images_data:
        # 단일 이미지를 images_data 형식에 맞게 변환
        images_data = {
            'paths': [post['image_path']],
            'captions': ['']
        }
    
    # 위치별 광고 선택
    # 사이드바 광고
    cur.execute('SELECT * FROM ads WHERE position = "side" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    sidebar_ad = cur.fetchone()
    
    # 배너 광고
    cur.execute('SELECT * FROM ads WHERE position = "banner" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    banner_ad = cur.fetchone()
    
    # 푸터 광고
    cur.execute('SELECT * FROM ads WHERE position = "footer" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    footer_ad = cur.fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        # 제목 길이 검증
        if len(title) > 40:
            flash('제목은 40자 이내로 입력해주세요.', 'danger')
            return render_template('board/edit.html', board=board, post=post, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        # 동영상 데이터 처리
        video_data = request.form.get('video_data', '[]')
        
        # 게시글 수정
        cur.execute('''
            UPDATE posts 
            SET title = %s, content = %s, video_data = %s, updated_at = NOW()
            WHERE id = %s
        ''', (title, content, video_data, post_id))
        
        mysql.connection.commit()
        cur.close()
        
        flash('게시글이 수정되었습니다.', 'success')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # JSON 데이터를 템플릿에서 사용할 수 있도록 문자열로 변환
    post['images_data_json'] = json.dumps(images_data or {'paths': [], 'captions': []})
    
    return render_template('board/edit.html', board=board, post=post, 
                          sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad)

# 게시글 삭제
@board_bp.route('/board/<string:board_route>/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(board_route, post_id):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    
    # 세션 확인 로깅 추가
    print(f"Session data: {session}")
    print(f"Current user: {current_user.id if current_user.is_authenticated else 'Not authenticated'}")
    
    if not current_user.is_authenticated:
        flash('이 작업을 수행하려면 로그인이 필요합니다.', 'danger')
        return redirect(url_for('auth.login'))
    
    # 게시판 및 게시글 데이터 조회
    cur = mysql.connection.cursor()
    
    try:
        cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
        board = cur.fetchone()

        if not board:
            cur.close()
            abort(404)
        
        cur.execute('SELECT * FROM posts WHERE id = %s AND board_id = %s', (post_id, board['id']))
        post = cur.fetchone()
        
        if not post:
            cur.close()
            abort(404)
        
        # 작성자 확인 (명시적으로 세션 검사) - 관리자는 항상 삭제 가능하도록 수정
        # session.get('is_admin')을 먼저 체크하여 관리자면 바로 통과되도록 변경
        if not session.get('is_admin') and post['user_id'] != session.get('id'):
            flash('게시글 삭제 권한이 없습니다.', 'danger')
            cur.close()
            return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
        
        # 트랜잭션 시작
        try:
            # 댓글 삭제
            cur.execute('DELETE FROM comments WHERE post_id = %s', (post_id,))
            
            # 좋아요 삭제
            cur.execute('DELETE FROM post_likes WHERE post_id = %s', (post_id,))
            
            # 게시글 삭제
            cur.execute('DELETE FROM posts WHERE id = %s', (post_id,))
            
            # 변경사항 커밋
            mysql.connection.commit()
            flash('게시글이 삭제되었습니다.', 'success')
            
        except Exception as e:
            # 오류 발생 시 롤백
            mysql.connection.rollback()
            flash(f'게시글 삭제 중 오류가 발생했습니다: {str(e)}', 'danger')
            
    except Exception as e:
        flash(f'오류가 발생했습니다: {str(e)}', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('board.board_main', board_route=board_route))

# 댓글 삭제
@board_bp.route('/board/<string:board_route>/<int:post_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(board_route, post_id, comment_id):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    # 게시판 데이터 조회
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    
    # 게시글 조회
    cur.execute('SELECT * FROM posts WHERE id = %s AND board_id = %s', (post_id, board['id']))
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    
    # 댓글 조회
    cur.execute('SELECT * FROM comments WHERE id = %s AND post_id = %s', (comment_id, post_id))
    comment = cur.fetchone()
    
    if not comment:
        cur.close()
        abort(404)
    
    # 권한 확인: 댓글 작성자 또는 게시글 작성자 또는 관리자만 삭제 가능
    # 관리자는 항상 삭제 가능하도록 조건 순서 변경
    if not session.get('is_admin') and session['id'] != comment['user_id'] and session['id'] != post['user_id']:
        flash('댓글 삭제 권한이 없습니다.', 'danger')
        cur.close()
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 댓글 삭제
    cur.execute('DELETE FROM comments WHERE id = %s', (comment_id,))
    mysql.connection.commit()
    cur.close()
    
    flash('댓글이 삭제되었습니다.', 'success')
    return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))

# 게시물 목록만 JSON으로 반환하는 API 엔드포인트
@board_bp.route('/board/<string:board_route>/posts', methods=['GET'])
def board_posts_json(board_route):
    # 필요한 객체는 current_app을 통해 접근
    mysql = get_mysql()
    cur = mysql.connection.cursor()

    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()

    if not board:
        cur.close()
        abort(404)
    
    # 페이지네이션
    page = request.args.get('page', 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page
    
    # 총 게시글 수 조회 (페이지네이션용)
    cur.execute('SELECT COUNT(*) as count FROM posts WHERE board_id = %s', (board['id'],))
    total_count = cur.fetchone()['count']
    total_pages = (total_count + per_page - 1) // per_page
    
    # 게시글 조회
    if board['route'] == 'anonymous':
        cur.execute('''
            SELECT posts.*, '익명' as nickname,
                   (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                   (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count
            FROM posts
            WHERE posts.board_id = %s
            ORDER BY posts.created_at DESC
            LIMIT %s OFFSET %s
        ''', (board['id'], per_page, offset))
    else:
        cur.execute('''
            SELECT posts.*, users.nickname, users.is_vip,
                   (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                   (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count
            FROM posts
            JOIN users ON posts.user_id = users.id
            WHERE posts.board_id = %s
            ORDER BY posts.created_at DESC
            LIMIT %s OFFSET %s
        ''', (board['id'], per_page, offset))
    
    posts = cur.fetchall()
    cur.close()
    
    # 현재 날짜 정보 가져오기
    now = datetime.now(seoul_timezone).strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'board': board,
        'posts': posts,
        'now': now,
        'page': page,
        'total_pages': total_pages
    })

# 익명 게시글 비밀번호 확인
@board_bp.route('/board/<string:board_route>/<int:post_id>/verify_password', methods=['POST'])
def verify_anonymous_post_password(board_route, post_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()
    
    if not board or board['route'] != 'anonymous':
        cur.close()
        abort(404)
    
    password = request.form.get('password', '').strip()
    action = request.form.get('action', '')  # 'edit' or 'delete'
    
    if not password:
        flash('비밀번호를 입력해주세요.', 'danger')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 게시글 정보 조회
    cur.execute('SELECT * FROM posts WHERE id = %s AND board_id = %s AND is_anonymous = 1', 
               (post_id, board['id']))
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    
    # 비밀번호 확인
    if not post['anonymous_password'] or not check_anonymous_password(password, post['anonymous_password']):
        flash('비밀번호가 일치하지 않습니다.', 'danger')
        cur.close()
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    cur.close()
    
    # 세션에 인증 정보 저장 (10분간 유효)
    session[f'anonymous_post_{post_id}_verified'] = {
        'verified': True,
        'timestamp': datetime.now().timestamp()
    }
    
    if action == 'edit':
        return redirect(url_for('board.edit_anonymous_post', board_route=board_route, post_id=post_id))
    elif action == 'delete':
        return redirect(url_for('board.delete_anonymous_post', board_route=board_route, post_id=post_id))
    else:
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))

# 익명 게시글 수정 (비밀번호 인증 후)
@board_bp.route('/board/<string:board_route>/<int:post_id>/edit_anonymous', methods=['GET', 'POST'])
def edit_anonymous_post(board_route, post_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()
    
    if not board or board['route'] != 'anonymous':
        cur.close()
        abort(404)
    
    # 비밀번호 인증 확인
    auth_key = f'anonymous_post_{post_id}_verified'
    if (auth_key not in session or 
        not session[auth_key].get('verified') or
        datetime.now().timestamp() - session[auth_key].get('timestamp', 0) > 600):  # 10분 제한
        flash('비밀번호 인증이 필요합니다.', 'danger')
        cur.close()
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 게시글 조회
    cur.execute('SELECT * FROM posts WHERE id = %s AND board_id = %s AND is_anonymous = 1', 
               (post_id, board['id']))
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    
    user_agent = request.headers.get('User-Agent')
    is_mobile = 'Mobile' in user_agent
    
    # 위치별 광고 선택
    cur.execute('SELECT * FROM ads WHERE position = "side" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    sidebar_ad = cur.fetchone()
    cur.execute('SELECT * FROM ads WHERE position = "banner" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    banner_ad = cur.fetchone()
    cur.execute('SELECT * FROM ads WHERE position = "footer" AND is_active = 1 ORDER BY RAND() LIMIT 1')
    footer_ad = cur.fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        # 입력값 검증
        if not title or not content:
            flash('제목과 내용을 모두 입력해주세요.', 'danger')
            return render_template('board/edit_anonymous.html', board=board, post=post, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        if len(title) > 50:
            flash('제목은 50자 이내로 입력해주세요.', 'danger')
            return render_template('board/edit_anonymous.html', board=board, post=post, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        # 동영상 데이터 처리
        video_data = request.form.get('video_data', '[]')
        
        # 게시글 수정
        cur.execute('''
            UPDATE posts 
            SET title = %s, content = %s, video_data = %s, updated_at = NOW()
            WHERE id = %s AND is_anonymous = 1
        ''', (title, content, video_data, post_id))
        
        mysql.connection.commit()
        cur.close()
        
        # 인증 세션 삭제
        if auth_key in session:
            del session[auth_key]
        
        flash('게시글이 수정되었습니다.', 'success')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 닉네임 설정
    if post['ip_address']:
        post['nickname'] = get_anonymous_nickname(post['ip_address'])
    else:
        post['nickname'] = '익명'
    
    # JSON 데이터를 템플릿에서 사용할 수 있도록 문자열로 변환
    post['images_data_json'] = json.dumps({} or {'paths': [], 'captions': []})
    
    return render_template('board/edit_anonymous.html', board=board, post=post, 
                          sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad)

# 익명 게시글 삭제 (비밀번호 인증 후)
@board_bp.route('/board/<string:board_route>/<int:post_id>/delete_anonymous', methods=['GET', 'POST'])
def delete_anonymous_post(board_route, post_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()
    
    if not board or board['route'] != 'anonymous':
        cur.close()
        abort(404)
    
    # 비밀번호 인증 확인
    auth_key = f'anonymous_post_{post_id}_verified'
    if (auth_key not in session or 
        not session[auth_key].get('verified') or
        datetime.now().timestamp() - session[auth_key].get('timestamp', 0) > 600):  # 10분 제한
        flash('비밀번호 인증이 필요합니다.', 'danger')
        cur.close()
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 게시글 확인
    cur.execute('SELECT * FROM posts WHERE id = %s AND board_id = %s AND is_anonymous = 1', 
               (post_id, board['id']))
    post = cur.fetchone()
    
    if not post:
        cur.close()
        abort(404)
    
    # GET 요청일 때는 확인 페이지 표시
    if request.method == 'GET':
        cur.close()
        return render_template('board/confirm_delete.html', 
                             board=board, post=post, 
                             action_url=url_for('board.delete_anonymous_post', 
                                              board_route=board_route, post_id=post_id))
    
    # POST 요청일 때 실제 삭제 수행
    try:
        # 댓글 삭제
        cur.execute('DELETE FROM comments WHERE post_id = %s', (post_id,))
        
        # 좋아요 삭제
        cur.execute('DELETE FROM post_likes WHERE post_id = %s', (post_id,))
        
        # 게시글 삭제
        cur.execute('DELETE FROM posts WHERE id = %s AND is_anonymous = 1', (post_id,))
        
        mysql.connection.commit()
        
        # 인증 세션 삭제
        if auth_key in session:
            del session[auth_key]
        
        flash('게시글이 삭제되었습니다.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        flash('게시글 삭제 중 오류가 발생했습니다.', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('board.board_main', board_route=board_route))

# 익명 댓글 비밀번호 확인
@board_bp.route('/board/<string:board_route>/<int:post_id>/comment/<int:comment_id>/verify_password', methods=['POST'])
def verify_anonymous_comment_password(board_route, post_id, comment_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    cur.execute('SELECT * FROM boards WHERE route = %s', (board_route,))
    board = cur.fetchone()
    
    if not board or board['route'] != 'anonymous':
        cur.close()
        abort(404)
    
    password = request.form.get('password', '').strip()
    
    if not password:
        flash('비밀번호를 입력해주세요.', 'danger')
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 댓글 정보 조회
    cur.execute('SELECT * FROM comments WHERE id = %s AND post_id = %s AND is_anonymous = 1', 
               (comment_id, post_id))
    comment = cur.fetchone()
    
    if not comment:
        cur.close()
        abort(404)
    
    # 비밀번호 확인
    if not comment['anonymous_password'] or not check_anonymous_password(password, comment['anonymous_password']):
        flash('비밀번호가 일치하지 않습니다.', 'danger')
        cur.close()
        return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))
    
    # 댓글 삭제
    cur.execute('DELETE FROM comments WHERE id = %s AND is_anonymous = 1', (comment_id,))
    mysql.connection.commit()
    cur.close()
    
    flash('댓글이 삭제되었습니다.', 'success')
    return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id)) 
