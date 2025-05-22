from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, Response, send_file
from datetime import datetime
import pandas as pd
import os
from werkzeug.utils import secure_filename
import mimetypes
import cv2
import numpy as np
import re
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # 실제 운영시에는 안전한 키로 변경해야 합니다

# 데이터베이스 설정
DB_FILE = 'accidents.db'

def get_db():
    """데이터베이스 연결을 반환하는 함수"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return None

def init_db():
    """데이터베이스 초기화"""
    if not os.path.exists(DB_FILE):
        conn = get_db()
        if conn:
            # 빈 테이블 생성
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accidents (
                    사고번호 TEXT PRIMARY KEY,
                    차량번호 TEXT,
                    성명 TEXT,
                    생년월일 TEXT,
                    사원번호 TEXT,
                    운전면허번호 TEXT,
                    나이 TEXT,
                    연락처 TEXT,
                    운전경력 TEXT,
                    당사경력 TEXT,
                    주소 TEXT,
                    구분 TEXT,
                    사고유형 TEXT,
                    사고장소 TEXT,
                    사고발생시속도 TEXT,
                    날씨 TEXT,
                    경찰서 TEXT,
                    조사관성명 TEXT,
                    전화 TEXT,
                    휴대폰 TEXT,
                    차량파손부위 TEXT,
                    출동보험기사 TEXT,
                    보험회사 TEXT,
                    보험접수번호 TEXT,
                    보험상담자 TEXT,
                    대물담당 TEXT,
                    대인담당 TEXT,
                    운전자상해 TEXT,
                    치료병원 TEXT,
                    이미지파일 TEXT,
                    동영상파일 TEXT,
                    사고일시 TEXT,
                    상대차량번호1 TEXT,
                    상대차량성명1 TEXT,
                    상대차량연락처1 TEXT,
                    상대차량차종1 TEXT,
                    상대차량남여1 TEXT,
                    상대차량비고1 TEXT,
                    상대차량번호2 TEXT,
                    상대차량성명2 TEXT,
                    상대차량연락처2 TEXT,
                    상대차량차종2 TEXT,
                    상대차량남여2 TEXT,
                    상대차량비고2 TEXT,
                    상대차량번호3 TEXT,
                    상대차량성명3 TEXT,
                    상대차량연락처3 TEXT,
                    상대차량차종3 TEXT,
                    상대차량남여3 TEXT,
                    상대차량비고3 TEXT,
                    상해승객성명1 TEXT,
                    상해승객연락처1 TEXT,
                    상해승객병원1 TEXT,
                    상해승객나이1 TEXT,
                    상해승객남여1 TEXT,
                    상해승객비고1 TEXT,
                    상해승객성명2 TEXT,
                    상해승객연락처2 TEXT,
                    상해승객병원2 TEXT,
                    상해승객나이2 TEXT,
                    상해승객남여2 TEXT,
                    상해승객비고2 TEXT,
                    상해승객성명3 TEXT,
                    상해승객연락처3 TEXT,
                    상해승객병원3 TEXT,
                    상해승객나이3 TEXT,
                    상해승객남여3 TEXT,
                    상해승객비고3 TEXT
                )
            ''')
            conn.commit()
            conn.close()

# 업로드 설정
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {
    'images': {'png', 'jpg', 'jpeg', 'gif'},
    'videos': {'mp4', 'avi', 'mov', 'wmv'}
}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = None

# MIME 타입 설정
mimetypes.add_type('video/avi', '.avi')
mimetypes.add_type('video/x-msvideo', '.avi')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/quicktime', '.mov')
mimetypes.add_type('video/x-ms-wmv', '.wmv')

# 업로드 디렉토리 생성
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'images'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)

def allowed_file(filename, file_type):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS[file_type]

def convert_avi_to_mp4(input_path, output_path):
    """AVI 파일을 MP4로 변환 (OpenCV 사용)"""
    try:
        # 비디오 캡처 객체 생성
        cap = cv2.VideoCapture(input_path)
        
        # 비디오 속성 가져오기
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        # 비디오 작성자 생성
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # 프레임 읽기 및 쓰기
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
        
        # 자원 해제
        cap.release()
        out.release()
        return True
    except Exception as e:
        print(f"변환 중 오류 발생: {e}")
        return False

def convert_accident_id(old_id):
    """기존 사고번호를 새로운 형식(yyyymmdd-자동연번)으로 변환"""
    if not old_id or not isinstance(old_id, str):
        return old_id
        
    # 이미 새로운 형식인 경우 그대로 반환
    if re.match(r'^\d{8}-\d{2}$', old_id):
        return old_id
        
    # 기존 형식에서 날짜 부분 추출
    parts = old_id.split('-')
    if len(parts) >= 1:
        date_part = parts[0]
        if len(date_part) == 8:  # yyyymmdd 형식인 경우
            # 기존 데이터 로드
            df = load_accidents()
            # 해당 날짜의 마지막 사고번호 찾기
            same_date_accidents = df[df['사고번호'].str.startswith(date_part)]
            if not same_date_accidents.empty:
                last_seq = max([int(id.split('-')[1]) for id in same_date_accidents['사고번호']])
                new_seq = last_seq + 1
            else:
                new_seq = 1
            return f"{date_part}-{new_seq:02d}"
    return old_id

def generate_accident_id():
    """사고번호 생성 (yyyymmdd-자동연번 형식)"""
    now = datetime.now()
    date_str = now.strftime('%Y%m%d')
    
    # 기존 데이터 로드
    df = load_accidents()
    
    # 해당 날짜의 마지막 사고번호 찾기
    same_date_accidents = df[df['사고번호'].str.startswith(date_str)]
    if not same_date_accidents.empty:
        # 마지막 번호에서 연번 추출
        last_seq = max([int(id.split('-')[1]) for id in same_date_accidents['사고번호']])
        new_seq = last_seq + 1
    else:
        new_seq = 1
    
    return f"{date_str}-{new_seq:02d}"

def format_accident_date(date_str):
    """사고일시 형식 변환 (yyyymmddhhmm -> yyyy-mm-dd hh:mm)"""
    try:
        if len(date_str) == 12:
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            hour = date_str[8:10]
            minute = date_str[10:12]
            return f"{year}-{month}-{day} {hour}:{minute}"
    except:
        pass
    return date_str

def load_accidents():
    """사고 데이터를 데이터베이스에서 로드"""
    try:
        conn = get_db()
        if conn is None:
            return pd.DataFrame()

        # 테이블 존재 여부 확인
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accidents'")
        if not cursor.fetchone():
            conn.close()
            return pd.DataFrame()

        # 데이터 조회
        query = "SELECT * FROM accidents ORDER BY 사고번호 DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        if conn:
            conn.close()
        return pd.DataFrame()

def save_accident(data):
    """새 사고 데이터를 데이터베이스에 저장"""
    try:
        conn = get_db()
        df = pd.DataFrame([data])
        df.to_sql('accidents', conn, if_exists='append', index=False)
        conn.commit()  # 트랜잭션 커밋 추가
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving accident data: {str(e)}")
        if conn:
            conn.rollback()  # 에러 시 롤백
            conn.close()
        return False

def update_accident(accident_id, data):
    """사고 데이터 업데이트"""
    conn = get_db()
    try:
        # SQL UPDATE 문을 사용하여 데이터를 업데이트합니다
        cursor = conn.cursor()
        update_fields = []
        params = []
        
        for key, value in data.items():
            if key != '사고번호':  # 사고번호는 업데이트하지 않습니다
                update_fields.append(f"{key} = ?")
                params.append(value)
        
        params.append(accident_id)  # WHERE 절의 파라미터
        
        query = f"""
            UPDATE accidents 
            SET {', '.join(update_fields)}
            WHERE 사고번호 = ?
        """
        
        cursor.execute(query, params)
        conn.commit()
    except Exception as e:
        print(f"Error updating accident: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def delete_accident(accident_id):
    """사고 데이터 삭제"""
    conn = get_db()
    conn.execute("DELETE FROM accidents WHERE 사고번호 = ?", (accident_id,))
    conn.commit()
    conn.close()

@app.route('/uploads/<file_type>/<filename>')
def uploaded_file(file_type, filename):
    """파일 제공 엔드포인트"""
    try:
        return send_from_directory(
            os.path.join(app.config['UPLOAD_FOLDER'], file_type),
            filename,
            as_attachment=False
        )
    except Exception as e:
        print(f"Error serving file: {str(e)}")
        return "File not found", 404

@app.route('/')
def index():
    try:
        df = load_accidents()
        if df.empty:
            return render_template('index.html', accidents=[])
        accidents = df.to_dict('records')
        return render_template('index.html', accidents=accidents)
    except Exception:
        return render_template('index.html', accidents=[])

@app.route('/accident/new', methods=['GET', 'POST'])
def new_accident():
    """새 사고 등록"""
    if request.method == 'POST':
        # 필수 입력 항목 체크
        required_fields = {
            'car_number': '차량번호',
            'name': '성명',
            'accident_date': '사고일시',
            'accident_category': '사고유형'
        }
        
        missing_fields = []
        for field, label in required_fields.items():
            value = request.form.get(field, '').strip()
            if not value:
                missing_fields.append(label)
        
        if missing_fields:
            flash(f'다음 항목은 필수 입력입니다: {", ".join(missing_fields)}', 'error')
            return redirect(url_for('new_accident'))

        try:
            accident_id = generate_accident_id()
            
            # 이미지 파일 처리
            image_files = request.files.getlist('images')
            image_paths = []
            for image in image_files:
                if image and allowed_file(image.filename, 'images'):
                    filename = secure_filename(f"{accident_id}_{image.filename}")
                    image_path = os.path.join('images', filename)
                    full_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                    try:
                        image.save(full_path)
                        image_paths.append(filename)
                    except Exception as e:
                        print(f"Error saving image: {str(e)}")
                        flash('이미지 저장 중 오류가 발생했습니다.', 'error')
            
            # 비디오 파일 처리
            video_files = request.files.getlist('videos')
            video_paths = []
            for video in video_files:
                if video and allowed_file(video.filename, 'videos'):
                    filename = secure_filename(f"{accident_id}_{video.filename}")
                    video_path = os.path.join('videos', filename)
                    full_path = os.path.join(app.config['UPLOAD_FOLDER'], video_path)
                    try:
                        video.save(full_path)
                        video_paths.append(filename)
                    except Exception as e:
                        print(f"Error saving video: {str(e)}")
                        flash('비디오 저장 중 오류가 발생했습니다.', 'error')

            # 기본 데이터 수집
            data = {
                '사고번호': accident_id,
                '차량번호': request.form.get('car_number', '').strip(),
                '성명': request.form.get('name', '').strip(),
                '생년월일': request.form.get('birth_date', '').strip(),
                '사원번호': request.form.get('employee_number', '').strip(),
                '운전면허번호': request.form.get('license_number', '').strip(),
                '나이': request.form.get('age', '').strip(),
                '연락처': request.form.get('phone', '').strip(),
                '운전경력': request.form.get('driving_experience', '').strip(),
                '당사경력': request.form.get('company_experience', '').strip(),
                '주소': request.form.get('address', '').strip(),
                '구분': request.form.get('accident_type', '').strip(),
                '사고유형': request.form.get('accident_category', '').strip(),
                '사고장소': request.form.get('accident_location', '').strip(),
                '사고발생시속도': request.form.get('speed', '').strip(),
                '날씨': request.form.get('weather', '').strip(),
                '경찰서': request.form.get('police_station', '').strip(),
                '조사관성명': request.form.get('investigator', '').strip(),
                '전화': request.form.get('police_phone', '').strip(),
                '휴대폰': request.form.get('police_mobile', '').strip(),
                '차량파손부위': request.form.get('damage_parts', '').strip(),
                '출동보험기사': request.form.get('insurance_agent', '').strip(),
                '보험회사': request.form.get('insurance_company', '').strip(),
                '보험접수번호': request.form.get('insurance_number', '').strip(),
                '보험상담자': request.form.get('insurance_consultant', '').strip(),
                '대물담당': request.form.get('property_handler', '').strip(),
                '대인담당': request.form.get('personal_handler', '').strip(),
                '운전자상해': request.form.get('driver_injury', '').strip(),
                '치료병원': request.form.get('hospital', '').strip(),
                '이미지파일': ','.join(image_paths) if image_paths else '',
                '동영상파일': ','.join(video_paths) if video_paths else '',
                '사고일시': format_accident_date(request.form.get('accident_date', '').strip())
            }

            # 상대차량 정보 추가
            for i in range(1, 4):
                data[f'상대차량번호{i}'] = request.form.get(f'other_car_number{i}', '').strip()
                data[f'상대차량성명{i}'] = request.form.get(f'other_car_name{i}', '').strip()
                data[f'상대차량연락처{i}'] = request.form.get(f'other_car_phone{i}', '').strip()
                data[f'상대차량차종{i}'] = request.form.get(f'other_car_type{i}', '').strip()
                data[f'상대차량남여{i}'] = request.form.get(f'other_car_gender{i}', '').strip()
                data[f'상대차량비고{i}'] = request.form.get(f'other_car_note{i}', '').strip()

            # 상해승객 정보 추가
            for i in range(1, 4):
                data[f'상해승객성명{i}'] = request.form.get(f'injured_name{i}', '').strip()
                data[f'상해승객연락처{i}'] = request.form.get(f'injured_phone{i}', '').strip()
                data[f'상해승객병원{i}'] = request.form.get(f'injured_hospital{i}', '').strip()
                data[f'상해승객나이{i}'] = request.form.get(f'injured_age{i}', '').strip()
                data[f'상해승객남여{i}'] = request.form.get(f'injured_gender{i}', '').strip()
                data[f'상해승객비고{i}'] = request.form.get(f'injured_note{i}', '').strip()
            
            # 데이터베이스에 저장
            if save_accident(data):
                flash('사고가 성공적으로 등록되었습니다.', 'success')
                return redirect(url_for('index'))
            else:
                flash('사고 등록 중 오류가 발생했습니다.', 'error')
                return redirect(url_for('new_accident'))
                
        except Exception as e:
            print(f"Error in new_accident: {str(e)}")
            flash('사고 등록 중 오류가 발생했습니다.', 'error')
            return redirect(url_for('new_accident'))
    
    return render_template('new_accident.html')

@app.route('/accident/<accident_id>')
def view_accident(accident_id):
    """사고 상세 보기"""
    accidents = load_accidents()
    accident = accidents[accidents['사고번호'] == accident_id].iloc[0]
    
    # 이미지와 비디오 파일 경로 처리
    image_files = accident['이미지파일'].split(',') if pd.notna(accident['이미지파일']) else []
    video_files = accident['동영상파일'].split(',') if pd.notna(accident['동영상파일']) else []
    
    return render_template('view_accident.html', 
                         accident=accident,
                         image_files=image_files,
                         video_files=video_files)

@app.route('/download/<file_type>/<filename>')
def download_file(file_type, filename):
    """파일 다운로드 엔드포인트"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_type, filename)
    
    if not os.path.exists(file_path):
        flash('파일을 찾을 수 없습니다.', 'error')
        return redirect(url_for('index'))
    
    # AVI 파일인 경우 MP4 버전이 있는지 확인
    if filename.lower().endswith('.avi'):
        mp4_path = file_path.rsplit('.', 1)[0] + '.mp4'
        if os.path.exists(mp4_path):
            return send_file(
                mp4_path,
                as_attachment=True,
                download_name=os.path.basename(mp4_path)
            )
    
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename
    )

@app.route('/edit/<accident_id>', methods=['GET', 'POST'])
def edit_accident(accident_id):
    if request.method == 'POST':
        try:
            # 업데이트할 데이터를 딕셔너리로 준비
            data = {
                '차량번호': request.form['car_number'],
                '성명': request.form['name'],
                '생년월일': request.form['birth_date'],
                '사원번호': request.form['employee_number'],
                '운전면허번호': request.form['license_number'],
                '나이': request.form.get('age'),
                '연락처': request.form.get('phone'),
                '운전경력': request.form.get('driving_experience'),
                '당사경력': request.form.get('company_experience'),
                '주소': request.form.get('address'),
                '사고일시': request.form['accident_date'],
                '구분': request.form['accident_type'],
                '사고유형': request.form['accident_category'],
                '사고장소': request.form['accident_location'],
                '사고발생시속도': request.form['speed'],
                '날씨': request.form['weather'],
                '경찰서': request.form['police_station'],
                '조사관성명': request.form['investigator'],
                '전화': request.form['police_phone'],
                '휴대폰': request.form['police_mobile'],
                '차량파손부위': request.form['damage_parts'],
                '출동보험기사': request.form['insurance_agent'],
                '보험회사': request.form['insurance_company'],
                '보험접수번호': request.form['insurance_number'],
                '보험상담자': request.form.get('insurance_consultant'),
                '대물담당': request.form.get('property_handler'),
                '대인담당': request.form.get('personal_handler')
            }

            # 상대차량 정보 추가
            for i in range(1, 4):
                data[f'상대차량번호{i}'] = request.form.get(f'other_car_number{i}')
                data[f'상대차량성명{i}'] = request.form.get(f'other_car_name{i}')
                data[f'상대차량연락처{i}'] = request.form.get(f'other_car_phone{i}')
                data[f'상대차량차종{i}'] = request.form.get(f'other_car_type{i}')
                data[f'상대차량남여{i}'] = request.form.get(f'other_car_gender{i}')
                data[f'상대차량비고{i}'] = request.form.get(f'other_car_note{i}')

            # 상해승객 정보 추가
            for i in range(1, 4):
                data[f'상해승객성명{i}'] = request.form.get(f'injured_name{i}')
                data[f'상해승객연락처{i}'] = request.form.get(f'injured_phone{i}')
                data[f'상해승객병원{i}'] = request.form.get(f'injured_hospital{i}')
                data[f'상해승객나이{i}'] = request.form.get(f'injured_age{i}')
                data[f'상해승객남여{i}'] = request.form.get(f'injured_gender{i}')
                data[f'상해승객비고{i}'] = request.form.get(f'injured_note{i}')

            # 이미지 파일 처리
            if 'images' in request.files:
                images = request.files.getlist('images')
                if images and images[0].filename:
                    image_filenames = []
                    for image in images:
                        if image and allowed_file(image.filename, 'images'):
                            filename = secure_filename(f"{accident_id}_{image.filename}")
                            image_path = os.path.join('images', filename)
                            full_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
                            try:
                                image.save(full_path)
                                image_filenames.append(filename)
                            except Exception as e:
                                print(f"Error saving image: {str(e)}")
                                flash('이미지 저장 중 오류가 발생했습니다.', 'error')
                    if image_filenames:
                        data['이미지파일'] = ','.join(image_filenames)

            # 비디오 파일 처리
            if 'videos' in request.files:
                videos = request.files.getlist('videos')
                if videos and videos[0].filename:
                    video_filenames = []
                    for video in videos:
                        if video and allowed_file(video.filename, 'videos'):
                            filename = secure_filename(f"{accident_id}_{video.filename}")
                            video_path = os.path.join('videos', filename)
                            full_path = os.path.join(app.config['UPLOAD_FOLDER'], video_path)
                            try:
                                video.save(full_path)
                                video_filenames.append(filename)
                            except Exception as e:
                                print(f"Error saving video: {str(e)}")
                                flash('비디오 저장 중 오류가 발생했습니다.', 'error')
                    if video_filenames:
                        data['동영상파일'] = ','.join(video_filenames)

            # 데이터베이스 업데이트
            update_accident(accident_id, data)
            flash('사고 정보가 성공적으로 수정되었습니다.', 'success')
            return redirect(url_for('view_accident', accident_id=accident_id))
            
        except Exception as e:
            print(f"Error in edit_accident: {str(e)}")
            flash('사고 정보 수정 중 오류가 발생했습니다.', 'error')
            return redirect(url_for('edit_accident', accident_id=accident_id))
    
    # GET 요청 처리
    conn = get_db()
    accident = conn.execute("SELECT * FROM accidents WHERE 사고번호 = ?", (accident_id,)).fetchone()
    conn.close()
    
    if accident:
        return render_template('edit_accident.html', accident=dict(accident))
    
    flash('사고 정보를 찾을 수 없습니다.', 'error')
    return redirect(url_for('index'))

@app.route('/delete/<accident_id>')
def delete_accident_route(accident_id):
    try:
        delete_accident(accident_id)
        flash('사고 정보가 삭제되었습니다.', 'success')
    except Exception as e:
        flash(f'사고 정보 삭제 중 오류가 발생했습니다: {str(e)}', 'error')
    
    return redirect(url_for('index'))

def filter_accidents(df, start_date=None, end_date=None, accident_type=None, weather=None, car_number=None, name=None, employee_number=None, classification=None):
    """검색 조건에 따라 사고 데이터를 필터링"""
    if not df.empty:
        # 날짜 필터링
        if start_date:
            start_datetime = pd.to_datetime(start_date)
            df = df[pd.to_datetime(df['사고일시']) >= start_datetime]
        if end_date:
            end_datetime = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            df = df[pd.to_datetime(df['사고일시']) <= end_datetime]
        
        # 사고유형 필터링
        if accident_type and accident_type.strip():
            df = df[df['사고유형'] == accident_type]
        
        # 날씨 필터링
        if weather and weather.strip():
            df = df[df['날씨'] == weather]
        
        # 차량번호 필터링
        if car_number and car_number.strip():
            df = df[df['차량번호'].str.contains(car_number, na=False, case=False)]
        
        # 성명 필터링
        if name and name.strip():
            df = df[df['성명'].str.contains(name, na=False, case=False)]
        
        # 사원번호 필터링
        if employee_number and employee_number.strip():
            df = df[df['사원번호'].str.contains(employee_number, na=False, case=False)]
        
        # 구분 필터링
        if classification and classification.strip():
            df = df[df['구분'].str.contains(classification, na=False, case=False)]
    
    return df

@app.route('/analysis')
def analysis():
    """사고 분석 메인 페이지"""
    now = datetime.now()
    
    # 검색 조건이 있는 경우에만 데이터를 로드하고 필터링
    if request.query_string:
        df = load_accidents()
        if not df.empty:
            # 검색 조건 적용
            df = filter_accidents(
                df,
                request.args.get('start_date'),
                request.args.get('end_date'),
                request.args.get('accident_type'),
                request.args.get('weather'),
                request.args.get('car_number'),
                request.args.get('name'),
                request.args.get('employee_number'),
                request.args.get('classification')
            )
            
            if not df.empty:
                # 검색 결과 요약 데이터 계산
                total_accidents = len(df)
                accident_types = df['사고유형'].value_counts().to_dict()
                
                # 상세 분석 데이터 계산
                classifications = df['구분'].value_counts().to_dict()
                weathers = df['날씨'].value_counts().to_dict()
                
                # 월별 통계 계산
                df['월'] = pd.to_datetime(df['사고일시']).dt.month
                monthly_stats = df['월'].value_counts().sort_index().to_dict()
                
                return render_template('analysis.html', 
                                    now=now,
                                    total_accidents=total_accidents,
                                    accident_types=accident_types,
                                    classifications=classifications,
                                    weathers=weathers,
                                    monthly_stats=monthly_stats)
    
    return render_template('analysis.html', now=now)

@app.route('/analysis/vehicle')
def analysis_by_vehicle():
    """차량별 사고 분석"""
    df = load_accidents()
    if df.empty:
        return render_template('analysis_vehicle.html', data=None)
    
    # 검색 조건 적용
    df = filter_accidents(
        df,
        request.args.get('start_date'),
        request.args.get('end_date'),
        request.args.get('accident_type'),
        request.args.get('weather'),
        request.args.get('car_number'),
        request.args.get('name'),
        request.args.get('employee_number'),
        request.args.get('classification')
    )
    
    # 차량별 사고 건수 집계
    vehicle_stats = df.groupby('차량번호').agg({
        '사고번호': 'count',
        '사고유형': lambda x: x.value_counts().to_dict(),
        '사고장소': lambda x: x.value_counts().to_dict()
    }).reset_index()
    
    vehicle_stats.columns = ['차량번호', '사고건수', '사고유형분포', '사고장소분포']
    return render_template('analysis_vehicle.html', data=vehicle_stats.to_dict('records'))

@app.route('/analysis/name')
def analysis_by_name():
    """성명별 사고 분석"""
    df = load_accidents()
    if df.empty:
        return render_template('analysis_name.html', data=None)
    
    # 검색 조건 적용
    df = filter_accidents(
        df,
        request.args.get('start_date'),
        request.args.get('end_date'),
        request.args.get('accident_type'),
        request.args.get('weather'),
        request.args.get('car_number'),
        request.args.get('name'),
        request.args.get('employee_number'),
        request.args.get('classification')
    )
    
    # 성명별 사고 건수 집계
    name_stats = df.groupby('성명').agg({
        '사고번호': 'count',
        '사고유형': lambda x: x.value_counts().to_dict(),
        '차량번호': lambda x: x.value_counts().to_dict()
    }).reset_index()
    
    name_stats.columns = ['성명', '사고건수', '사고유형분포', '차량분포']
    
    # 가해 건수 계산 및 정렬
    def get_gap_count(type_dist):
        return type_dist.get('가해', 0) if isinstance(type_dist, dict) else 0
    
    name_stats['가해건수'] = name_stats['사고유형분포'].apply(get_gap_count)
    name_stats = name_stats.sort_values(['사고건수', '가해건수'], ascending=[False, False])
    
    return render_template('analysis_name.html', data=name_stats.to_dict('records'))

@app.route('/analysis/date')
def analysis_by_date():
    """날짜별 사고 분석"""
    df = load_accidents()
    if df.empty:
        return render_template('analysis_date.html', data=None)
    
    # 검색 조건 적용
    df = filter_accidents(
        df,
        request.args.get('start_date'),
        request.args.get('end_date'),
        request.args.get('accident_type'),
        request.args.get('weather'),
        request.args.get('car_number'),
        request.args.get('name'),
        request.args.get('employee_number'),
        request.args.get('classification')
    )
    
    # 날짜별 사고 건수 집계
    df['사고일자'] = pd.to_datetime(df['사고일시']).dt.date
    date_stats = df.groupby('사고일자').agg({
        '사고번호': 'count',
        '사고유형': lambda x: x.value_counts().to_dict(),
        '차량번호': lambda x: x.value_counts().to_dict()
    }).reset_index()
    
    date_stats.columns = ['사고일자', '사고건수', '사고유형분포', '차량분포']
    return render_template('analysis_date.html', data=date_stats.to_dict('records'))

@app.route('/analysis/employee')
def analysis_by_employee():
    """사원번호별 사고 분석"""
    df = load_accidents()
    if df.empty:
        return render_template('analysis_employee.html', data=None)
    
    # 검색 조건 적용
    df = filter_accidents(
        df,
        request.args.get('start_date'),
        request.args.get('end_date'),
        request.args.get('accident_type'),
        request.args.get('weather'),
        request.args.get('car_number'),
        request.args.get('name'),
        request.args.get('employee_number'),
        request.args.get('classification')
    )
    
    # 사원번호별 사고 건수 집계
    employee_stats = df.groupby('사원번호').agg({
        '사고번호': 'count',
        '사고유형': lambda x: x.value_counts().to_dict(),
        '차량번호': lambda x: x.value_counts().to_dict(),
        '성명': 'first'
    }).reset_index()
    
    employee_stats.columns = ['사원번호', '사고건수', '사고유형분포', '차량분포', '성명']
    return render_template('analysis_employee.html', data=employee_stats.to_dict('records'))

@app.route('/analysis/name/<name>')
def analysis_by_name_detail(name):
    """성명별 상세 사고 분석"""
    df = load_accidents()
    if df.empty:
        return render_template('analysis_name_detail.html', name=name, accidents=None)
    
    # 검색 조건 적용
    df = filter_accidents(
        df,
        request.args.get('start_date'),
        request.args.get('end_date'),
        request.args.get('accident_type'),
        request.args.get('weather'),
        request.args.get('car_number'),
        request.args.get('name'),
        request.args.get('employee_number'),
        request.args.get('classification')
    )
    
    # 해당 성명의 모든 사고 내역 필터링
    accidents = df[df['성명'] == name].sort_values('사고일시', ascending=False)
    
    # 기본 통계 계산
    total_accidents = len(accidents)
    accident_types = accidents['사고유형'].value_counts().to_dict()
    vehicles = accidents['차량번호'].value_counts().to_dict()
    
    return render_template('analysis_name_detail.html', 
                         name=name,
                         accidents=accidents.to_dict('records'),
                         total_accidents=total_accidents,
                         accident_types=accident_types,
                         vehicles=vehicles)

if __name__ == '__main__':
    init_db()  # 데이터베이스 초기화
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True) 