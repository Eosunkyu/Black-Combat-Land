# type: ignore
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from flask_login import login_required, current_user
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import random
import json
from flask import current_app
import re
import pytz

seoul_timezone = pytz.timezone('Asia/Seoul')


board_bp = Blueprint('board', __name__)

# 필요한 객체 가져오기 (모듈 레벨에서 가져오지 않고 라우트 내부에서 가져옴)
from app import mysql

# 허용된 파일 확장자 체크
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 최대 파일 크기 (16MB)
MAX_FILE_SIZE = 16 * 1024 * 1024

# 게시판 메인 화면
@board_bp.route('/board/<string:board_route>')
def board_main(board_route):
    # 게시판 데이터 조회
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
        # 익명 게시판은 작성자 정보 숨김
        cur.execute('''
            SELECT posts.*, '익명' as nickname, posts.images_data, posts.content, posts.created_at,
                  (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                  (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count, boards.name as board_name
            FROM posts
            JOIN boards ON posts.board_id = boards.id
            WHERE posts.board_id = %s
            ORDER BY posts.created_at DESC
            LIMIT %s OFFSET %s
        ''', (board['id'], per_page, offset))
    else:
        # 일반 게시판은 작성자 정보 표시
        cur.execute('''
            SELECT posts.*, users.nickname, users.is_vip, posts.images_data, posts.content, posts.created_at,
                  (SELECT COUNT(*) FROM comments WHERE post_id = posts.id) as comment_count,
                  (SELECT COUNT(*) FROM post_likes WHERE post_id = posts.id) as like_count, boards.name as board_name
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
    # 필요한 객체 가져오기
    from app import mysql
    
    # 게시판 데이터 조회
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
        if len(title) > 40:
            flash('제목은 40자 이내로 입력해주세요.', 'danger')
            return render_template('board/write.html', board=board, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        # 이미지 업로드 처리
        image_paths = []
        image_captions = []
        
        # 이미지 파일 처리
        if 'image_files' in request.files:
            # 여러 파일이 업로드된 경우
            files = request.files.getlist('image_files')
            image_count = min(int(request.form.get('image_count', 0)), 10)  # 최대 10개로 제한
            
            for i in range(min(len(files), image_count)):
                file = files[i]
                caption = request.form.get(f'image_caption_{i}', '')
                
                if file and file.filename != '' and allowed_file(file.filename):
                    # 파일 크기 확인
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)  # 파일 포인터를 다시 처음으로 되돌림
                    
                    if file_size > MAX_FILE_SIZE:
                        flash(f'파일 "{file.filename}"의 크기가 16MB를 초과합니다. 16MB 이하의 파일만 업로드할 수 있습니다.', 'danger')
                        continue
                    
                    filename = secure_filename(file.filename or '')
                    # 파일명이 중복되지 않도록 타임스탬프 추가
                    filename = f"{datetime.now(seoul_timezone).strftime('%Y%m%d%H%M%S')}_{i}_{filename}"
                    
                    # 업로드 폴더가 없으면 생성
                    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    
                    relative_path = os.path.join('static', 'uploads', filename).replace('\\', '/')
                    image_paths.append(relative_path)
                    image_captions.append(caption)
        
        # 이미지 태그 처리: [이미지:index:caption] 형식의 태그를 HTML로 변환
        # 내용에 삽입된 이미지 태그를 HTML로 변환
        image_pattern = r'\[이미지:(\d+)(?::([^\]]*))?\]'
        for match in re.finditer(image_pattern, content):
            index = int(match.group(1))
            if index < len(image_paths):
                # 삽입된 태그를 HTML로 변환
                replacement = f'<img src="/{image_paths[index]}" class="img-fluid my-3" alt="{image_captions[index]}">'
                if match.group(2):  # 캡션이 있는 경우
                    replacement += f'<figcaption class="figure-caption text-center mb-3">{match.group(2)}</figcaption>'
                content = content.replace(match.group(0), replacement)
        
        # 동영상 데이터 처리
        video_data = request.form.get('video_data', '[]')
        
        # 게시글 저장
        user_id = session.get('id', 0) if board['route'] != 'anonymous' else 0
        
        # DB에 이미지 경로와 캡션, 동영상 데이터를 JSON으로 저장
        images_json = json.dumps({
            'paths': image_paths,
            'captions': image_captions
        }) if image_paths else None
        
        cur.execute('''
            INSERT INTO posts (board_id, user_id, title, content, images_data, video_data, created_at, view_count, is_anonymous, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), 0, %s, %s)
        ''', (board['id'], user_id, title, content, images_json, video_data, 1 if board['route'] == 'anonymous' else 0, ip_address))
        
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
    # 필요한 객체 가져오기
    from app import mysql
    
    # 게시판 및 게시글 데이터 조회
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
    page = 1
    per_page = 15
    offset = 0
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
            SELECT posts.*, users.nickname,users.is_vip,
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
    
    # 익명 게시판인 경우 닉네임을 '익명'으로 표시
    if post['is_anonymous']:
        post['nickname'] = '익명'
        for comment in comments:
            if comment['is_anonymous']:
                comment['nickname'] = '익명'
    
    return render_template('board/view.html', board=board, post=post,
                          comments=comments, like_count=like_count,
                          is_liked=is_liked, images_data=images_data,
                          sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad,
                          center_ad=center_ad, posts=posts, now=now, is_admin=is_admin, is_mobile=is_mobile)

# 댓글 작성
@board_bp.route('/board/<string:board_route>/<int:post_id>/comment', methods=['POST'])
def write_comment(board_route, post_id):
    # 필요한 객체 가져오기
    from app import mysql
    
    # 게시판 및 게시글 데이터 조회
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
        INSERT INTO comments (post_id, user_id, content, created_at, is_anonymous, ip_address)
        VALUES (%s, %s, %s, NOW(), %s, %s)
    ''', (post_id, user_id, content, 1 if board['route'] == 'anonymous' else 0, ip_address))
    
    mysql.connection.commit()
    cur.close()
    
    flash('댓글이 등록되었습니다.', 'success')
    return redirect(url_for('board.view_post', board_route=board_route, post_id=post_id))

# 게시글 좋아요
@board_bp.route('/board/<string:board_route>/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(board_route, post_id):
    # 필요한 객체 가져오기
    from app import mysql
    
    # 게시판 및 게시글 데이터 조회
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
    # 필요한 객체 가져오기
    from app import mysql
    
    # 게시판 및 게시글 데이터 조회
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
        
        # 입력값 검증
        if not title or not content:
            flash('제목과 내용을 모두 입력해주세요.', 'danger')
            return render_template('board/edit.html', board=board, post=post, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        # 제목 길이 검증
        if len(title) > 40:
            flash('제목은 40자 이내로 입력해주세요.', 'danger')
            return render_template('board/edit.html', board=board, post=post, 
                                  sidebar_ad=sidebar_ad, banner_ad=banner_ad, footer_ad=footer_ad, is_mobile=is_mobile)
        
        # 이미지 데이터 처리
        image_paths = []
        image_captions = []
        
        # 기존 이미지 처리
        existing_images_flag = request.form.get('existing_images', '0') == '1'
        
        # 기존 이미지 데이터가 있고 유지한다면 추가
        existing_images_data = None
        if existing_images_flag and post.get('images_data'):
            try:
                existing_images_data = json.loads(post['images_data'])
                image_paths.extend(existing_images_data.get('paths', []))
                image_captions.extend(existing_images_data.get('captions', []))
            except (json.JSONDecodeError, TypeError):
                # 기존 데이터가 올바른 JSON이 아닌 경우 무시
                pass
        elif existing_images_flag and post.get('image_path'):
            image_paths.append(post['image_path'])
            image_captions.append(request.form.get('existing_image_caption_0', ''))
        
        # 새 이미지 처리
        if 'image_files' in request.files:
            # 여러 파일이 업로드된 경우
            files = request.files.getlist('image_files')
            image_count = min(int(request.form.get('image_count', 0)), 10)  # 최대 10개로 제한
            
            for i in range(min(len(files), image_count)):
                file = files[i]
                caption = request.form.get(f'image_caption_{i}', '')
                
                if file and file.filename != '' and allowed_file(file.filename):
                    # 파일 크기 확인
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)  # 파일 포인터를 다시 처음으로 되돌림
                    
                    if file_size > MAX_FILE_SIZE:
                        flash(f'파일 "{file.filename}"의 크기가 16MB를 초과합니다. 16MB 이하의 파일만 업로드할 수 있습니다.', 'danger')
                        continue
                    
                    filename = secure_filename(file.filename or '')
                    # 파일명이 중복되지 않도록 타임스탬프 추가
                    filename = f"{datetime.now(seoul_timezone).strftime('%Y%m%d%H%M%S')}_{i}_{filename}"
                    
                    # 업로드 폴더가 없으면 생성
                    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    
                    relative_path = os.path.join('static', 'uploads', filename).replace('\\', '/')
                    image_paths.append(relative_path)
                    image_captions.append(caption)
        
        # 이미지 태그 처리: [이미지:index:caption] 형식의 태그를 HTML로 변환
        # 내용에 삽입된 이미지 태그를 HTML로 변환
        new_image_pattern = r'\[이미지:(\d+)(?::([^\]]*))?\]'
        for match in re.finditer(new_image_pattern, content):
            index = int(match.group(1))
            if index < len(image_paths):
                # 삽입된 태그를 HTML로 변환
                replacement = f'<img src="/{image_paths[index]}" class="img-fluid my-3" alt="{image_captions[index]}">'
                if match.group(2):  # 캡션이 있는 경우
                    replacement += f'<figcaption class="figure-caption text-center mb-3">{match.group(2)}</figcaption>'
                content = content.replace(match.group(0), replacement)
        
        # 기존 이미지 태그 처리
        existing_image_pattern = r'\[기존이미지:(\d+)(?::([^\]]*))?\]'
        if existing_images_data:
            for match in re.finditer(existing_image_pattern, content):
                index = int(match.group(1))
                if index < len(existing_images_data['paths']):
                    # 삽입된 태그를 HTML로 변환
                    path = existing_images_data['paths'][index]
                    replacement = f'<img src="/{path}" class="img-fluid my-3" alt="{match.group(2) or ""}">'
                    if match.group(2):  # 캡션이 있는 경우
                        replacement += f'<figcaption class="figure-caption text-center mb-3">{match.group(2)}</figcaption>'
                    content = content.replace(match.group(0), replacement)
        
        # 동영상 데이터 처리
        video_data = request.form.get('video_data', '[]')
        
        # 이미지 데이터를 JSON으로 변환
        images_json = json.dumps({
            'paths': image_paths,
            'captions': image_captions
        }) if image_paths else None
        
        # 게시글 수정
        cur.execute('''
            UPDATE posts 
            SET title = %s, content = %s, images_data = %s, video_data = %s, updated_at = NOW()
            WHERE id = %s
        ''', (title, content, images_json, video_data, post_id))
        
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
    # 필요한 객체 가져오기
    from app import mysql
    
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
    # 필요한 객체 가져오기
    from app import mysql
    
    # 게시판 데이터 조회
    cur = mysql.connection.cursor()
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
