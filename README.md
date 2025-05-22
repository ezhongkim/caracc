# 사고 관리 시스템

사고 정보를 등록하고 관리하는 웹 애플리케이션입니다.

## 주요 기능

- 사고 정보 등록 및 관리
- 사고 분석 및 통계
- 이미지 및 동영상 파일 업로드
- 차량별, 성명별, 날짜별 분석

## 설치 방법

1. 저장소 클론
```bash
git clone https://github.com/ezhongkim/caracc.git
cd caracc
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 데이터베이스 초기화
```bash
python app.py
```

## 실행 방법

```bash
python app.py
```

서버가 실행되면 웹 브라우저에서 `http://localhost:5000`으로 접속할 수 있습니다.

## 기술 스택

- Python 3.8+
- Flask
- SQLite
- Bootstrap 5
- OpenCV

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
