from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, login_required, logout_user, current_user
import re
from flask import current_app
import secrets
import datetime

auth_bp = Blueprint('auth', __name__)
# app.py가 auth라는 이름으로 import하므로 별칭 추가
auth = auth_bp

# 최대 길이 제한 상수 정의
MAX_USERNAME_LENGTH = 20
MAX_PASSWORD_LENGTH = 20
MAX_EMAIL_LENGTH = 30
MAX_NICKNAME_LENGTH = 10
MAX_MESSAGE_TITLE_LENGTH = 100
MAX_MESSAGE_CONTENT_LENGTH = 1000

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # 현재 앱 컨텍스트에서 mysql과 bcrypt 가져오기
    from app import mysql, bcrypt
    
    if request.method == 'POST':
        # 폼 데이터 가져오기
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        nickname = request.form['nickname']
        
        # 입력값 검증
        if not username or not email or not password or not confirm_password or not nickname:
            flash('모든 필드를 입력해주세요.', 'danger')
            return render_template('auth/register.html')
        
        # 최대 길이 검증
        if len(username) > MAX_USERNAME_LENGTH:
            flash(f'아이디는 최대 {MAX_USERNAME_LENGTH}자까지 입력 가능합니다.', 'danger')
            return render_template('auth/register.html')
            
        if len(email) > MAX_EMAIL_LENGTH:
            flash(f'이메일은 최대 {MAX_EMAIL_LENGTH}자까지 입력 가능합니다.', 'danger')
            return render_template('auth/register.html')
            
        if len(password) > MAX_PASSWORD_LENGTH:
            flash(f'비밀번호는 최대 {MAX_PASSWORD_LENGTH}자까지 입력 가능합니다.', 'danger')
            return render_template('auth/register.html')
            
        if len(nickname) > MAX_NICKNAME_LENGTH:
            flash(f'닉네임은 최대 {MAX_NICKNAME_LENGTH}자까지 입력 가능합니다.', 'danger')
            return render_template('auth/register.html')
        
        # 비밀번호 확인
        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.', 'danger')
            return render_template('auth/register.html')
        
        # 아이디 유효성 검사 (영문자, 숫자만 허용)
        if not re.match(r'^[A-Za-z0-9]+$', username):
            flash('아이디는 영문자와 숫자만 사용 가능합니다.', 'danger')
            return render_template('auth/register.html')
        
        # 비밀번호 복잡성 검증
        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
            flash('비밀번호는 8자 이상, 대소문자와 숫자를 포함해야 합니다.', 'danger')
            return render_template('auth/register.html')
            
        # 이메일 형식 검증
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            flash('유효한 이메일 형식이 아닙니다.', 'danger')
            return render_template('auth/register.html')
        
        # 데이터베이스 연결
        cur = mysql.connection.cursor()
        
        # 아이디 중복 확인
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cur.fetchone()
        
        if account:
            flash('이미 존재하는 아이디입니다.', 'danger')
            cur.close()
            return render_template('auth/register.html')
        
        # 닉네임 중복 확인
        cur.execute('SELECT * FROM users WHERE nickname = %s', (nickname,))
        account = cur.fetchone()
        
        if account:
            flash('이미 존재하는 닉네임입니다.', 'danger')
            cur.close()
            return render_template('auth/register.html')
            
        # 이메일 중복 확인
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cur.fetchone()
        
        if account:
            flash('이미 사용 중인 이메일입니다.', 'danger')
            cur.close()
            return render_template('auth/register.html')
        
        # 비밀번호 해싱
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # 사용자 등록
        cur.execute('''
            INSERT INTO users (username, password, nickname, email, is_admin, is_vip, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''', (username, hashed_password, nickname, email, 0, 0))
        
        mysql.connection.commit()
        cur.close()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 현재 앱 컨텍스트에서 mysql과 bcrypt 가져오기
    from app import mysql, bcrypt
    
    if request.method == 'POST':
        # 폼 데이터 가져오기
        username = request.form['username']
        password = request.form['password']
        
        # 입력값 검증
        if not username or not password:
            flash('아이디와 비밀번호를 모두 입력해주세요.', 'danger')
            return render_template('auth/login.html')
        
        # 최대 길이 검증
        if len(username) > MAX_USERNAME_LENGTH:
            flash(f'아이디는 최대 {MAX_USERNAME_LENGTH}자까지 입력 가능합니다.', 'danger')
            return render_template('auth/login.html')
            
        if len(password) > MAX_PASSWORD_LENGTH:
            flash(f'비밀번호는 최대 {MAX_PASSWORD_LENGTH}자까지 입력 가능합니다.', 'danger')
            return render_template('auth/login.html')
        
        # 데이터베이스 연결
        cur = mysql.connection.cursor()
        
        # 사용자 조회
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        
        if user and bcrypt.check_password_hash(user['password'], password):
            # 영구 세션으로 설정 (PERMANENT_SESSION_LIFETIME 적용)
            session.permanent = True
            
            # 세션에 사용자 정보 저장
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            session['nickname'] = user['nickname']
            session['is_admin'] = user['is_admin']
            session['is_vip'] = user['is_vip']
            
            # Flask-Login 사용자 객체 생성 및 로그인
            from flask_login import UserMixin
            user_obj = UserMixin()
            user_obj.id = user['id']
            login_user(user_obj, remember=True)
            
            # 마지막 로그인 시간 업데이트
            cur.execute('UPDATE users SET last_login = NOW() WHERE id = %s', (user['id'],))
            mysql.connection.commit()
            
            cur.close()
            flash('로그인 되었습니다.', 'success')
            
            # 로그인 후 원래 가려던 페이지로 리디렉션
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('로그인에 실패했습니다. 아이디 또는 비밀번호를 확인해주세요.', 'danger')
            cur.close()
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    # 세션에서 사용자 정보 삭제
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('nickname', None)
    session.pop('is_admin', None)
    session.pop('is_vip', None)
    
    flash('로그아웃 되었습니다.', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    # 현재 앱 컨텍스트에서 mysql 가져오기
    from app import mysql
    
    # 데이터베이스 연결
    cur = mysql.connection.cursor()
    
    # 사용자 정보 조회
    cur.execute('SELECT * FROM users WHERE id = %s', (current_user.id,))
    user = cur.fetchone()
    
    # 사용자 게시글 조회
    cur.execute('''
        SELECT posts.*, boards.name as board_name, boards.route as board_route
        FROM posts
        JOIN boards ON posts.board_id = boards.id
        WHERE posts.user_id = %s
        ORDER BY posts.created_at DESC
    ''', (current_user.id,))
    
    posts = cur.fetchall()
    
    # 사용자 댓글 조회
    cur.execute('''
        SELECT comments.*, posts.title as post_title, boards.route as board_route, posts.id as post_id
        FROM comments
        JOIN posts ON comments.post_id = posts.id
        JOIN boards ON posts.board_id = boards.id
        WHERE comments.user_id = %s
        ORDER BY comments.created_at DESC
    ''', (current_user.id,))
    
    comments = cur.fetchall()
    
    # 읽지 않은 쪽지 수 확인
    cur.execute('SELECT COUNT(*) as unread_count FROM messages WHERE receiver_id = %s AND is_read = 0 AND receiver_deleted = 0', (current_user.id,))
    unread_count = cur.fetchone()['unread_count']
    
    # 친구 요청 수 확인
    cur.execute('SELECT COUNT(*) as request_count FROM friendships WHERE friend_id = %s AND status = "pending"', (current_user.id,))
    friend_request_count = cur.fetchone()['request_count']
    
    cur.close()
    
    return render_template('auth/profile.html', user=user, posts=posts, comments=comments, 
                           unread_count=unread_count, friend_request_count=friend_request_count)

# 아이디/비밀번호 찾기 페이지
@auth_bp.route('/find-account', methods=['GET'])
def find_account():
    return render_template('find_account.html', 
                           id_message=None, id_message_type=None, 
                           pw_message=None, pw_message_type=None)

# 아이디 찾기 처리
@auth_bp.route('/find-id', methods=['POST'])
def find_id():
    from app import mysql
    
    email = request.form.get('email')
    nickname = request.form.get('nickname')
    
    # 입력값 검증
    if not email or not nickname:
        return render_template('find_account.html', 
                           id_message='모든 필드를 입력해주세요.', 
                           id_message_type='danger',
                           pw_message=None, pw_message_type=None)
    
    # 최대 길이 검증
    if len(email) > MAX_EMAIL_LENGTH:
        return render_template('find_account.html', 
                           id_message=f'이메일은 최대 {MAX_EMAIL_LENGTH}자까지 입력 가능합니다.', 
                           id_message_type='danger',
                           pw_message=None, pw_message_type=None)
                           
    if len(nickname) > MAX_NICKNAME_LENGTH:
        return render_template('find_account.html', 
                           id_message=f'닉네임은 최대 {MAX_NICKNAME_LENGTH}자까지 입력 가능합니다.', 
                           id_message_type='danger',
                           pw_message=None, pw_message_type=None)
    
    # 데이터베이스 연결
    cur = mysql.connection.cursor()
    
    # 이메일과 닉네임으로 사용자 조회
    cur.execute('SELECT username FROM users WHERE email = %s AND nickname = %s', (email, nickname))
    user = cur.fetchone()
    cur.close()
    
    if user:
        username = user['username']
        # 아이디 일부를 *로 마스킹
        masked_username = username[:2] + '*' * (len(username) - 4) + username[-2:] if len(username) > 4 else username[:1] + '*' * (len(username) - 2) + username[-1:]
        
        return render_template('find_account.html', 
                           id_message=f'회원님의 아이디는 {masked_username} 입니다.', 
                           id_message_type='success',
                           pw_message=None, pw_message_type=None)
    else:
        return render_template('find_account.html', 
                           id_message='일치하는 계정 정보가 없습니다.', 
                           id_message_type='danger',
                           pw_message=None, pw_message_type=None)

# 데이터베이스에 password_reset_tokens 테이블이 없을 경우 생성
def create_reset_token_table():
    from app import mysql
    
    cur = mysql.connection.cursor()
    # 테이블 존재 여부 확인
    cur.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            token VARCHAR(100) NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            used TINYINT(1) NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    mysql.connection.commit()
    cur.close()

# 비밀번호 재설정 요청 처리
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    from app import mysql
    
    username = request.form.get('username')
    email = request.form.get('email')
    
    # 입력값 검증
    if not username or not email:
        return render_template('find_account.html', 
                           id_message=None, id_message_type=None,
                           pw_message='모든 필드를 입력해주세요.', 
                           pw_message_type='danger')
    
    # 최대 길이 검증
    if len(username) > MAX_USERNAME_LENGTH:
        return render_template('find_account.html', 
                           id_message=None, id_message_type=None,
                           pw_message=f'아이디는 최대 {MAX_USERNAME_LENGTH}자까지 입력 가능합니다.', 
                           pw_message_type='danger')
                           
    if len(email) > MAX_EMAIL_LENGTH:
        return render_template('find_account.html', 
                           id_message=None, id_message_type=None,
                           pw_message=f'이메일은 최대 {MAX_EMAIL_LENGTH}자까지 입력 가능합니다.', 
                           pw_message_type='danger')
    
    # 데이터베이스 연결
    cur = mysql.connection.cursor()
    
    # 테이블 생성 확인
    create_reset_token_table()
    
    # 사용자 조회
    cur.execute('SELECT id FROM users WHERE username = %s AND email = %s', (username, email))
    user = cur.fetchone()
    
    if user:
        user_id = user['id']
        
        # 기존 토큰 비활성화
        cur.execute('UPDATE password_reset_tokens SET used = 1 WHERE user_id = %s AND used = 0', (user_id,))
        
        # 새 토큰 생성
        token = secrets.token_urlsafe(32)
        now = datetime.datetime.now()
        expires_at = now + datetime.timedelta(hours=24)  # 24시간 유효
        
        # 토큰 저장
        cur.execute('''
            INSERT INTO password_reset_tokens (user_id, token, created_at, expires_at)
            VALUES (%s, %s, %s, %s)
        ''', (user_id, token, now, expires_at))
        
        mysql.connection.commit()
        cur.close()
        
        # 실제 운영 환경에서는 이메일로 토큰 링크 전송
        reset_link = url_for('auth.reset_password_form', token=token, _external=True)
        print(f"[DEBUG] Reset link: {reset_link}")  # 콘솔에 링크 출력 (개발 환경용)
        
        # 개발 환경에서는 직접 링크로 이동
        return redirect(url_for('auth.reset_password_form', token=token))
    else:
        cur.close()
        return render_template('find_account.html', 
                           id_message=None, id_message_type=None,
                           pw_message='일치하는 계정 정보가 없습니다.', 
                           pw_message_type='danger')

# 비밀번호 재설정 폼
@auth_bp.route('/reset-password/<token>', methods=['GET'])
def reset_password_form(token):
    from app import mysql
    
    # 토큰 유효성 검사
    cur = mysql.connection.cursor()
    cur.execute('''
        SELECT user_id FROM password_reset_tokens 
        WHERE token = %s AND used = 0 AND expires_at > NOW()
    ''', (token,))
    token_data = cur.fetchone()
    cur.close()
    
    if not token_data:
        flash('유효하지 않거나 만료된 토큰입니다.', 'danger')
        return redirect(url_for('auth.find_account'))
    
    return render_template('reset_password.html', token=token)

# 비밀번호 재설정 완료
@auth_bp.route('/complete-reset-password', methods=['POST'])
def complete_reset_password():
    from app import mysql, bcrypt
    
    token = request.form.get('token')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # 입력값 검증
    if not token or not password or not confirm_password:
        return render_template('reset_password.html', 
                          message='모든 필드를 입력해주세요.', 
                          message_type='danger',
                          token=token)
    
    # 최대 길이 검증
    if len(password) > MAX_PASSWORD_LENGTH:
        return render_template('reset_password.html', 
                          message=f'비밀번호는 최대 {MAX_PASSWORD_LENGTH}자까지 입력 가능합니다.', 
                          message_type='danger',
                          token=token)
    
    if password != confirm_password:
        return render_template('reset_password.html', 
                          message='비밀번호가 일치하지 않습니다.', 
                          message_type='danger',
                          token=token)
    
    # 비밀번호 복잡성 검증
    if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
        return render_template('reset_password.html', 
                          message='비밀번호는 8자 이상, 대소문자와 숫자를 포함해야 합니다.', 
                          message_type='danger',
                          token=token)
    
    # 데이터베이스 연결
    cur = mysql.connection.cursor()
    
    # 토큰 유효성 검사
    cur.execute('''
        SELECT user_id FROM password_reset_tokens 
        WHERE token = %s AND used = 0 AND expires_at > NOW()
    ''', (token,))
    token_data = cur.fetchone()
    
    if not token_data:
        cur.close()
        flash('유효하지 않거나 만료된 토큰입니다.', 'danger')
        return redirect(url_for('auth.find_account'))
    
    user_id = token_data['user_id']
    
    # 비밀번호 해싱
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # 비밀번호 업데이트
    cur.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, user_id))
    
    # 토큰 사용 완료 처리
    cur.execute('UPDATE password_reset_tokens SET used = 1 WHERE token = %s', (token,))
    
    mysql.connection.commit()
    cur.close()
    
    flash('비밀번호가 성공적으로 변경되었습니다. 새 비밀번호로 로그인해주세요.', 'success')
    return redirect(url_for('auth.login'))

# 내 정보 수정 페이지
@auth_bp.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    from app import mysql, bcrypt
    
    if request.method == 'POST':
        # 폼 데이터 가져오기
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # 데이터베이스 연결
        cur = mysql.connection.cursor()
        
        # 현재 사용자 정보 가져오기
        cur.execute('SELECT * FROM users WHERE id = %s', (current_user.id,))
        user = cur.fetchone()
        
        # 최대 길이 검증
        if nickname and len(nickname) > MAX_NICKNAME_LENGTH:
            flash(f'닉네임은 최대 {MAX_NICKNAME_LENGTH}자까지 입력 가능합니다.', 'danger')
            cur.close()
            return redirect(url_for('auth.edit_profile'))
            
        if email and len(email) > MAX_EMAIL_LENGTH:
            flash(f'이메일은 최대 {MAX_EMAIL_LENGTH}자까지 입력 가능합니다.', 'danger')
            cur.close()
            return redirect(url_for('auth.edit_profile'))
            
        if new_password and len(new_password) > MAX_PASSWORD_LENGTH:
            flash(f'비밀번호는 최대 {MAX_PASSWORD_LENGTH}자까지 입력 가능합니다.', 'danger')
            cur.close()
            return redirect(url_for('auth.edit_profile'))
        
        # 비밀번호 변경 확인
        if current_password and new_password and confirm_password:
            # 현재 비밀번호 확인
            if not bcrypt.check_password_hash(user['password'], current_password):
                flash('현재 비밀번호가 일치하지 않습니다.', 'danger')
                cur.close()
                return redirect(url_for('auth.edit_profile'))
            
            # 새 비밀번호 확인
            if new_password != confirm_password:
                flash('새 비밀번호가 일치하지 않습니다.', 'danger')
                cur.close()
                return redirect(url_for('auth.edit_profile'))
            
            # 비밀번호 복잡성 검증
            if len(new_password) < 8 or not re.search(r'[A-Z]', new_password) or not re.search(r'[a-z]', new_password) or not re.search(r'\d', new_password):
                flash('비밀번호는 8자 이상, 대소문자와 숫자를 포함해야 합니다.', 'danger')
                cur.close()
                return redirect(url_for('auth.edit_profile'))
            
            # 비밀번호 업데이트
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cur.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, current_user.id))
            flash('비밀번호가 변경되었습니다.', 'success')
        
        # 닉네임 변경
        if nickname and nickname != user['nickname']:
            # 닉네임 중복 확인
            cur.execute('SELECT * FROM users WHERE nickname = %s AND id != %s', (nickname, current_user.id))
            if cur.fetchone():
                flash('이미 사용 중인 닉네임입니다.', 'danger')
                cur.close()
                return redirect(url_for('auth.edit_profile'))
            
            # 닉네임 업데이트
            cur.execute('UPDATE users SET nickname = %s WHERE id = %s', (nickname, current_user.id))
            session['nickname'] = nickname
            flash('닉네임이 변경되었습니다.', 'success')
        
        # 이메일 변경
        if email and email != user['email']:
            # 이메일 중복 확인
            cur.execute('SELECT * FROM users WHERE email = %s AND id != %s', (email, current_user.id))
            if cur.fetchone():
                flash('이미 사용 중인 이메일입니다.', 'danger')
                cur.close()
                return redirect(url_for('auth.edit_profile'))
            
            # 이메일 형식 검증
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                flash('유효한 이메일 형식이 아닙니다.', 'danger')
                cur.close()
                return redirect(url_for('auth.edit_profile'))
            
            # 이메일 업데이트
            cur.execute('UPDATE users SET email = %s WHERE id = %s', (email, current_user.id))
            flash('이메일이 변경되었습니다.', 'success')
        
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('auth.profile'))
    
    # 현재 사용자 정보 가져오기
    cur = mysql.connection.cursor()
    cur.execute('SELECT * FROM users WHERE id = %s', (current_user.id,))
    user = cur.fetchone()
    cur.close()
    
    return render_template('auth/edit_profile.html', user=user)

# 쪽지함 목록
@auth_bp.route('/messages')
@login_required
def messages():
    from app import mysql
    
    # 받은 쪽지/보낸 쪽지 구분
    message_type = request.args.get('type', 'received')
    
    cur = mysql.connection.cursor()
    
    if message_type == 'sent':
        # 보낸 쪽지 목록
        cur.execute('''
            SELECT m.*, u.nickname as receiver_nickname 
            FROM messages m
            JOIN users u ON m.receiver_id = u.id
            WHERE m.sender_id = %s AND m.sender_deleted = 0
            ORDER BY m.created_at DESC
        ''', (current_user.id,))
    else:
        # 받은 쪽지 목록
        cur.execute('''
            SELECT m.*, u.nickname as sender_nickname 
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.receiver_id = %s AND m.receiver_deleted = 0
            ORDER BY m.created_at DESC
        ''', (current_user.id,))
    
    messages = cur.fetchall()
    
    # 읽지 않은 쪽지 수 확인
    cur.execute('SELECT COUNT(*) as unread_count FROM messages WHERE receiver_id = %s AND is_read = 0 AND receiver_deleted = 0', (current_user.id,))
    unread_count = cur.fetchone()['unread_count']
    
    cur.close()
    
    return render_template('auth/messages.html', messages=messages, message_type=message_type, unread_count=unread_count)

# 쪽지 상세 보기
@auth_bp.route('/messages/<int:message_id>')
@login_required
def view_message(message_id):
    from app import mysql
    
    cur = mysql.connection.cursor()
    
    # 쪽지 정보 가져오기
    cur.execute('''
        SELECT m.*, 
               sender.nickname as sender_nickname, 
               receiver.nickname as receiver_nickname
        FROM messages m
        JOIN users sender ON m.sender_id = sender.id
        JOIN users receiver ON m.receiver_id = receiver.id
        WHERE m.id = %s AND (m.sender_id = %s OR m.receiver_id = %s)
    ''', (message_id, current_user.id, current_user.id))
    
    message = cur.fetchone()
    
    if not message:
        flash('존재하지 않는 쪽지입니다.', 'danger')
        return redirect(url_for('auth.messages'))
    
    # 받은 쪽지일 경우 읽음 처리
    if message['receiver_id'] == current_user.id and message['is_read'] == 0:
        cur.execute('UPDATE messages SET is_read = 1 WHERE id = %s', (message_id,))
        mysql.connection.commit()
    
    cur.close()
    
    return render_template('auth/view_message.html', message=message)

# 쪽지 보내기
@auth_bp.route('/send-message', methods=['GET', 'POST'])
@login_required
def send_message():
    from app import mysql
    
    # 답장인 경우 수신자 정보 미리 설정
    receiver_id = request.args.get('to')
    receiver_nickname = None
    
    if receiver_id:
        cur = mysql.connection.cursor()
        cur.execute('SELECT nickname FROM users WHERE id = %s', (receiver_id,))
        user = cur.fetchone()
        if user:
            receiver_nickname = user['nickname']
        cur.close()
    
    if request.method == 'POST':
        # 폼 데이터 가져오기
        receiver = request.form.get('receiver')
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not receiver or not title or not content:
            flash('모든 항목을 입력해주세요.', 'danger')
            return redirect(url_for('auth.send_message'))
        
        # 최대 길이 검증
        if len(receiver) > MAX_NICKNAME_LENGTH:
            flash(f'수신자 닉네임은 최대 {MAX_NICKNAME_LENGTH}자까지 입력 가능합니다.', 'danger')
            return redirect(url_for('auth.send_message'))
            
        if len(title) > MAX_MESSAGE_TITLE_LENGTH:
            flash(f'제목은 최대 {MAX_MESSAGE_TITLE_LENGTH}자까지 입력 가능합니다.', 'danger')
            return redirect(url_for('auth.send_message'))
            
        if len(content) > MAX_MESSAGE_CONTENT_LENGTH:
            flash(f'내용은 최대 {MAX_MESSAGE_CONTENT_LENGTH}자까지 입력 가능합니다.', 'danger')
            return redirect(url_for('auth.send_message'))
        
        cur = mysql.connection.cursor()
        
        # 수신자 확인
        cur.execute('SELECT id FROM users WHERE nickname = %s', (receiver,))
        receiver_data = cur.fetchone()
        
        if not receiver_data:
            flash('존재하지 않는 사용자입니다.', 'danger')
            cur.close()
            return redirect(url_for('auth.send_message'))
        
        # 자기 자신에게 쪽지 보내는 것 방지
        if receiver_data['id'] == current_user.id:
            flash('자기 자신에게 쪽지를 보낼 수 없습니다.', 'danger')
            cur.close()
            return redirect(url_for('auth.send_message'))
        
        # 쪽지 저장
        cur.execute('''
            INSERT INTO messages (sender_id, receiver_id, title, content, is_read, created_at)
            VALUES (%s, %s, %s, %s, 0, NOW())
        ''', (current_user.id, receiver_data['id'], title, content))
        
        mysql.connection.commit()
        cur.close()
        
        flash('쪽지를 성공적으로 보냈습니다.', 'success')
        return redirect(url_for('auth.messages', type='sent'))
    
    return render_template('auth/send_message.html', receiver_id=receiver_id, receiver_nickname=receiver_nickname)

# 쪽지 삭제
@auth_bp.route('/delete-message/<int:message_id>', methods=['POST'])
@login_required
def delete_message(message_id):
    from app import mysql
    
    cur = mysql.connection.cursor()
    
    # 쪽지 정보 가져오기
    cur.execute('SELECT * FROM messages WHERE id = %s', (message_id,))
    message = cur.fetchone()
    
    if not message:
        flash('존재하지 않는 쪽지입니다.', 'danger')
        cur.close()
        return redirect(url_for('auth.messages'))
    
    # 권한 확인
    if message['sender_id'] != current_user.id and message['receiver_id'] != current_user.id:
        flash('삭제 권한이 없습니다.', 'danger')
        cur.close()
        return redirect(url_for('auth.messages'))
    
    # 보낸 사람이 삭제하는 경우
    if message['sender_id'] == current_user.id:
        cur.execute('UPDATE messages SET sender_deleted = 1 WHERE id = %s', (message_id,))
    
    # 받은 사람이 삭제하는 경우
    if message['receiver_id'] == current_user.id:
        cur.execute('UPDATE messages SET receiver_deleted = 1 WHERE id = %s', (message_id,))
    
    # 양쪽 다 삭제했으면 실제로 삭제
    cur.execute('SELECT * FROM messages WHERE id = %s', (message_id,))
    updated_message = cur.fetchone()
    
    if updated_message['sender_deleted'] == 1 and updated_message['receiver_deleted'] == 1:
        cur.execute('DELETE FROM messages WHERE id = %s', (message_id,))
    
    mysql.connection.commit()
    cur.close()
    
    flash('쪽지가 삭제되었습니다.', 'success')
    
    message_type = 'received'
    if message['sender_id'] == current_user.id:
        message_type = 'sent'
    
    return redirect(url_for('auth.messages', type=message_type))

# 친구 목록 페이지
@auth_bp.route('/friends')
@login_required
def friends():
    from app import mysql
    
    cur = mysql.connection.cursor()
    
    # 친구 목록 가져오기
    cur.execute('''
        SELECT f.*, u.nickname as friend_nickname
        FROM friendships f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = %s AND f.status = 'accepted'
        ORDER BY u.nickname
    ''', (current_user.id,))
    
    friends = cur.fetchall()
    
    # 받은 친구 요청 가져오기
    cur.execute('''
        SELECT f.*, u.nickname as user_nickname
        FROM friendships f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
    ''', (current_user.id,))
    
    friend_requests = cur.fetchall()
    
    # 보낸 친구 요청 가져오기
    cur.execute('''
        SELECT f.*, u.nickname as friend_nickname
        FROM friendships f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = %s AND f.status = 'pending'
        ORDER BY f.created_at DESC
    ''', (current_user.id,))
    
    sent_requests = cur.fetchall()
    
    # 차단한 사용자 목록
    cur.execute('''
        SELECT f.*, u.nickname as friend_nickname
        FROM friendships f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = %s AND f.status = 'blocked'
        ORDER BY u.nickname
    ''', (current_user.id,))
    
    blocked_users = cur.fetchall()
    
    cur.close()
    
    return render_template('auth/friends.html', 
                           friends=friends, 
                           friend_requests=friend_requests, 
                           sent_requests=sent_requests,
                           blocked_users=blocked_users)

# 친구 추가 요청
@auth_bp.route('/add-friend', methods=['POST'])
@login_required
def add_friend():
    from app import mysql
    
    nickname = request.form.get('nickname')
    
    if not nickname:
        flash('닉네임을 입력해주세요.', 'danger')
        return redirect(url_for('auth.friends'))
    
    # 최대 길이 검증
    if len(nickname) > MAX_NICKNAME_LENGTH:
        flash(f'닉네임은 최대 {MAX_NICKNAME_LENGTH}자까지 입력 가능합니다.', 'danger')
        return redirect(url_for('auth.friends'))
    
    cur = mysql.connection.cursor()
    
    # 사용자 확인
    cur.execute('SELECT id FROM users WHERE nickname = %s', (nickname,))
    user = cur.fetchone()
    
    if not user:
        flash('존재하지 않는 사용자입니다.', 'danger')
        cur.close()
        return redirect(url_for('auth.friends'))
    
    # 자기 자신에게 친구 신청하는 것 방지
    if user['id'] == current_user.id:
        flash('자기 자신에게 친구 신청을 할 수 없습니다.', 'danger')
        cur.close()
        return redirect(url_for('auth.friends'))
    
    # 이미 친구 관계인지 확인
    cur.execute('''
        SELECT * FROM friendships 
        WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
    ''', (current_user.id, user['id'], user['id'], current_user.id))
    
    existing_friendship = cur.fetchone()
    
    if existing_friendship:
        if existing_friendship['status'] == 'accepted':
            flash('이미 친구 관계입니다.', 'warning')
        elif existing_friendship['status'] == 'pending':
            flash('이미 친구 요청을 보냈거나 받은 상태입니다.', 'warning')
        elif existing_friendship['status'] == 'blocked':
            flash('차단된 사용자입니다.', 'danger')
        
        cur.close()
        return redirect(url_for('auth.friends'))
    
    # 친구 요청 저장
    cur.execute('''
        INSERT INTO friendships (user_id, friend_id, status, created_at)
        VALUES (%s, %s, 'pending', NOW())
    ''', (current_user.id, user['id']))
    
    mysql.connection.commit()
    cur.close()
    
    flash('친구 요청을 보냈습니다.', 'success')
    return redirect(url_for('auth.friends'))

# 친구 요청 응답 (수락/거절)
@auth_bp.route('/respond-friend-request/<int:request_id>/<action>', methods=['POST'])
@login_required
def respond_friend_request(request_id, action):
    from app import mysql
    
    if action not in ['accept', 'reject']:
        flash('잘못된 요청입니다.', 'danger')
        return redirect(url_for('auth.friends'))
    
    cur = mysql.connection.cursor()
    
    # 친구 요청 확인
    cur.execute('''
        SELECT * FROM friendships 
        WHERE id = %s AND friend_id = %s AND status = 'pending'
    ''', (request_id, current_user.id))
    
    request_data = cur.fetchone()
    
    if not request_data:
        flash('존재하지 않는 친구 요청이거나 권한이 없습니다.', 'danger')
        cur.close()
        return redirect(url_for('auth.friends'))
    
    if action == 'accept':
        # 친구 요청 수락
        cur.execute('UPDATE friendships SET status = "accepted", updated_at = NOW() WHERE id = %s', (request_id,))
        
        # 양방향 친구 관계 생성
        cur.execute('''
            INSERT INTO friendships (user_id, friend_id, status, created_at)
            VALUES (%s, %s, 'accepted', NOW())
        ''', (current_user.id, request_data['user_id']))
        
        flash('친구 요청을 수락했습니다.', 'success')
    else:
        # 친구 요청 거절
        cur.execute('UPDATE friendships SET status = "rejected", updated_at = NOW() WHERE id = %s', (request_id,))
        flash('친구 요청을 거절했습니다.', 'success')
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('auth.friends'))

# 친구 삭제
@auth_bp.route('/remove-friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    from app import mysql
    
    cur = mysql.connection.cursor()
    
    # 친구 관계 확인
    cur.execute('''
        SELECT * FROM friendships 
        WHERE id = %s AND user_id = %s AND status = 'accepted'
    ''', (friend_id, current_user.id))
    
    friendship = cur.fetchone()
    
    if not friendship:
        flash('존재하지 않는 친구 관계이거나 권한이 없습니다.', 'danger')
        cur.close()
        return redirect(url_for('auth.friends'))
    
    # 양방향 친구 관계 삭제
    cur.execute('''
        DELETE FROM friendships 
        WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
    ''', (current_user.id, friendship['friend_id'], friendship['friend_id'], current_user.id))
    
    mysql.connection.commit()
    cur.close()
    
    flash('친구를 삭제했습니다.', 'success')
    return redirect(url_for('auth.friends'))

# 사용자 차단
@auth_bp.route('/block-user/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    from app import mysql
    
    cur = mysql.connection.cursor()
    
    # 이미 차단되어 있는지 확인
    cur.execute('''
        SELECT * FROM friendships 
        WHERE user_id = %s AND friend_id = %s AND status = 'blocked'
    ''', (current_user.id, user_id))
    
    if cur.fetchone():
        flash('이미 차단된 사용자입니다.', 'warning')
        cur.close()
        return redirect(url_for('auth.friends'))
    
    # 기존 친구 관계 삭제
    cur.execute('''
        DELETE FROM friendships 
        WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)
    ''', (current_user.id, user_id, user_id, current_user.id))
    
    # 차단 관계 생성
    cur.execute('''
        INSERT INTO friendships (user_id, friend_id, status, created_at)
        VALUES (%s, %s, 'blocked', NOW())
    ''', (current_user.id, user_id))
    
    mysql.connection.commit()
    cur.close()
    
    flash('사용자를 차단했습니다.', 'success')
    return redirect(url_for('auth.friends'))

# 차단 해제
@auth_bp.route('/unblock-user/<int:block_id>', methods=['POST'])
@login_required
def unblock_user(block_id):
    from app import mysql
    
    cur = mysql.connection.cursor()
    
    # 차단 관계 확인
    cur.execute('''
        SELECT * FROM friendships 
        WHERE id = %s AND user_id = %s AND status = 'blocked'
    ''', (block_id, current_user.id))
    
    if not cur.fetchone():
        flash('존재하지 않는 차단 관계이거나 권한이 없습니다.', 'danger')
        cur.close()
        return redirect(url_for('auth.friends'))
    
    # 차단 관계 삭제
    cur.execute('DELETE FROM friendships WHERE id = %s', (block_id,))
    
    mysql.connection.commit()
    cur.close()
    
    flash('차단을 해제했습니다.', 'success')
    return redirect(url_for('auth.friends')) 