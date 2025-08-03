from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, jsonify, current_app
from functools import wraps
from datetime import datetime
import hashlib
import re

# Blueprint 생성
notice_bp = Blueprint('notice', __name__)

# 필요한 객체는 current_app을 통해 접근
def get_mysql():
    return current_app.extensions['mysql']

def get_bcrypt():
    return current_app.extensions['bcrypt']

# IP 주소 가져오기 함수
def get_client_ip():
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    return request.remote_addr or '0.0.0.0'

# 공지사항 상세 보기
@notice_bp.route('/notice/<int:notice_id>')
def view_notice(notice_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    try:
        # 공지사항 조회
        cur.execute('''
            SELECT notices.*, users.nickname, users.is_admin
            FROM notices
            JOIN users ON notices.user_id = users.id
            WHERE notices.id = %s AND notices.is_active = 1
        ''', (notice_id,))
        notice = cur.fetchone()
        
        if not notice:
            abort(404)
        
        # 댓글 조회 - JOIN 조건 개선하여 중복 방지
        cur.execute('''
            SELECT nc.id, nc.notice_id, nc.user_id, nc.content, nc.is_anonymous, nc.created_at,
                   CASE 
                       WHEN nc.is_anonymous = 1 AND nc.user_id = 0 THEN 
                           COALESCE((SELECT au.nickname FROM anonymous_users au 
                                   WHERE au.ip_address = nc.ip_address 
                                   ORDER BY au.created_at ASC LIMIT 1), '익명')
                       WHEN nc.is_anonymous = 1 THEN '익명'
                       ELSE COALESCE(u.nickname, '익명')
                   END as nickname,
                   CASE 
                       WHEN nc.is_anonymous = 1 THEN 0
                       ELSE COALESCE(u.is_vip, 0) 
                   END as is_vip
            FROM notice_comments nc
            LEFT JOIN users u ON nc.user_id = u.id AND nc.is_anonymous = 0
            WHERE nc.notice_id = %s
            ORDER BY nc.created_at ASC
        ''', (notice_id,))
        comments = cur.fetchall()
        
        # 광고 조회
        cur.execute('SELECT * FROM ads WHERE is_active = 1 ORDER BY RAND()')
        ads = cur.fetchall()
        
        # 광고를 위치별로 분리
        sidebar_ad = next((ad for ad in ads if 'sidebar' in ad.get('title', '').lower()), None)
        banner_ad = next((ad for ad in ads if 'banner' in ad.get('title', '').lower()), None)
        center_ad = next((ad for ad in ads if 'center' in ad.get('title', '').lower()), None)
        footer_ad = next((ad for ad in ads if 'footer' in ad.get('title', '').lower()), None)
        
        # 현재 시간
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template('notice_view.html', 
                             notice=notice, 
                             comments=comments,
                             now=now,
                             sidebar_ad=sidebar_ad,
                             banner_ad=banner_ad,
                             center_ad=center_ad,
                             footer_ad=footer_ad)
    
    except Exception as e:
        print(f"Error in view_notice: {e}")
        abort(500)
    finally:
        cur.close()

# 공지사항 댓글 작성
@notice_bp.route('/notice/<int:notice_id>/comment', methods=['POST'])
def write_comment(notice_id):
    mysql = get_mysql()
    bcrypt = get_bcrypt()
    cur = mysql.connection.cursor()
    
    try:
        # 공지사항 존재 확인
        cur.execute('SELECT id FROM notices WHERE id = %s AND is_active = 1', (notice_id,))
        if not cur.fetchone():
            abort(404)
        
        content = request.form.get('content', '').strip()
        anonymous_password = request.form.get('anonymous_password', '').strip()
        
        # 입력값 검증
        if not content:
            flash('댓글 내용을 입력해주세요.', 'danger')
            return redirect(url_for('notice.view_notice', notice_id=notice_id))
        
        if len(content) > 500:
            flash('댓글은 최대 500자까지 입력 가능합니다.', 'danger')
            return redirect(url_for('notice.view_notice', notice_id=notice_id))
        
        # 로그인하지 않은 사용자의 경우 비밀번호 필수
        if 'loggedin' not in session:
            if not anonymous_password or len(anonymous_password) < 4:
                flash('비밀번호는 4자리 이상 입력해야 합니다.', 'danger')
                return redirect(url_for('notice.view_notice', notice_id=notice_id))
        
        # IP 주소 가져오기
        ip_address = get_client_ip()
        
        # 익명 사용자 닉네임 처리 - 중복 방지 개선
        if 'loggedin' not in session:
            # IP 해시 생성
            ip_hash = hashlib.md5(ip_address.encode('utf-8')).hexdigest()
            
            # 기존 익명 사용자 확인 (중복 방지를 위해 트랜잭션 사용)
            cur.execute('SELECT nickname FROM anonymous_users WHERE ip_hash = %s LIMIT 1', (ip_hash,))
            existing_user = cur.fetchone()
            
            if not existing_user:
                # 새로운 익명 사용자 생성 시 중복 방지
                try:
                    cur.execute('SELECT COUNT(*) as count FROM anonymous_users')
                    count_result = cur.fetchone()
                    count = count_result['count'] if count_result else 0
                    anonymous_nickname = f'익명{count + 1}'
                    
                    cur.execute('''
                        INSERT INTO anonymous_users (ip_address, ip_hash, nickname, created_at)
                        VALUES (%s, %s, %s, NOW())
                    ''', (ip_address, ip_hash, anonymous_nickname))
                except Exception as e:
                    # 중복 삽입 시도 시 기존 사용자 다시 조회
                    cur.execute('SELECT nickname FROM anonymous_users WHERE ip_hash = %s LIMIT 1', (ip_hash,))
                    existing_user = cur.fetchone()
        
        # 댓글 저장
        user_id = session.get('id', 0) if 'loggedin' in session else 0
        is_anonymous = 1 if 'loggedin' not in session else 0
        
        # 비밀번호 해시화
        hashed_password = None
        if anonymous_password:
            hashed_password = bcrypt.generate_password_hash(anonymous_password).decode('utf-8')
        
        cur.execute('''
            INSERT INTO notice_comments (notice_id, user_id, content, created_at, is_anonymous, ip_address, anonymous_password)
            VALUES (%s, %s, %s, NOW(), %s, %s, %s)
        ''', (notice_id, user_id, content, is_anonymous, ip_address, hashed_password))
        
        mysql.connection.commit()
        flash('댓글이 등록되었습니다.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error in write_comment: {e}")
        flash('댓글 등록 중 오류가 발생했습니다.', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('notice.view_notice', notice_id=notice_id))

# 공지사항 댓글 삭제
@notice_bp.route('/notice/<int:notice_id>/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(notice_id, comment_id):
    mysql = get_mysql()
    cur = mysql.connection.cursor()
    
    try:
        # 댓글 조회
        cur.execute('''
            SELECT * FROM notice_comments 
            WHERE id = %s AND notice_id = %s
        ''', (comment_id, notice_id))
        comment = cur.fetchone()
        
        if not comment:
            flash('댓글을 찾을 수 없습니다.', 'danger')
            return redirect(url_for('notice.view_notice', notice_id=notice_id))
        
        # 삭제 권한 확인
        can_delete = False
        
        # 관리자는 모든 댓글 삭제 가능
        if session.get('is_admin'):
            can_delete = True
        # 로그인한 사용자는 자신의 댓글만 삭제 가능
        elif 'loggedin' in session and session.get('id') == comment['user_id']:
            can_delete = True
        
        if not can_delete:
            flash('댓글 삭제 권한이 없습니다.', 'danger')
            return redirect(url_for('notice.view_notice', notice_id=notice_id))
        
        # 댓글 삭제
        cur.execute('DELETE FROM notice_comments WHERE id = %s', (comment_id,))
        mysql.connection.commit()
        
        flash('댓글이 삭제되었습니다.', 'success')
        
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error in delete_comment: {e}")
        flash('댓글 삭제 중 오류가 발생했습니다.', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('notice.view_notice', notice_id=notice_id))

# 익명 댓글 비밀번호 확인 후 삭제
@notice_bp.route('/notice/<int:notice_id>/comment/<int:comment_id>/verify_password', methods=['POST'])
def verify_comment_password(notice_id, comment_id):
    mysql = get_mysql()
    bcrypt = get_bcrypt()
    cur = mysql.connection.cursor()
    
    try:
        password = request.form.get('password', '').strip()
        
        if not password:
            flash('비밀번호를 입력해주세요.', 'danger')
            return redirect(url_for('notice.view_notice', notice_id=notice_id))
        
        # 댓글 조회
        cur.execute('''
            SELECT * FROM notice_comments 
            WHERE id = %s AND notice_id = %s AND is_anonymous = 1
        ''', (comment_id, notice_id))
        comment = cur.fetchone()
        
        if not comment:
            flash('댓글을 찾을 수 없습니다.', 'danger')
            return redirect(url_for('notice.view_notice', notice_id=notice_id))
        
        # 비밀번호 확인
        if comment['anonymous_password'] and bcrypt.check_password_hash(comment['anonymous_password'], password):
            # 댓글 삭제
            cur.execute('DELETE FROM notice_comments WHERE id = %s', (comment_id,))
            mysql.connection.commit()
            flash('댓글이 삭제되었습니다.', 'success')
        else:
            flash('비밀번호가 올바르지 않습니다.', 'danger')
    
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error in verify_comment_password: {e}")
        flash('댓글 삭제 중 오류가 발생했습니다.', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('notice.view_notice', notice_id=notice_id)) 