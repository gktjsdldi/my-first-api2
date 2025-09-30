# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import random
import math
import requests # API 호출을 위해 requests 라이브러리를 추가합니다.
from urllib.parse import urljoin

app = Flask(__name__)
CORS(app)

# 김포공항의 대략적인 위도와 경도 및 감시 반경(km)
GMP_LATITUDE = 37.558
GMP_LONGITUDE = 126.794
MONITORING_RADIUS_KM = 5

def is_within_radius(lat, lon):
    """주어진 위도/경도가 김포공항 반경 내에 있는지 간단히 계산합니다."""
    # 실제로는 Haversine 공식을 사용해야 하지만, 시뮬레이션을 위해 간단한 유클리드 거리 근사치를 사용합니다.
    # 1도(degree)는 대략 111km에 해당합니다.
    deg_per_km = 1.0 / 111.0
    radius_in_deg = MONITORING_RADIUS_KM * deg_per_km
    
    distance_sq = (lat - GMP_LATITUDE)**2 + (lon - GMP_LONGITUDE)**2
    return distance_sq < radius_in_deg**2

# --- 기존 API 엔드포인트 ---
@app.route('/api/random')
def random_number():
    """1부터 99 사이의 랜덤한 정수를 생성하고 JSON 형태로 반환합니다."""
    number = random.randint(1, 99)
    return jsonify({'number': number})

# --- 신규 추가된 API 엔드포인트 ---

# 1. 외부 API 시뮬레이터 (기상청 낙뢰 API라고 가정)
@app.route('/api/kma/lightning-strikes')
def kma_lightning_simulator():
    """
    김포공항 주변에 무작위로 낙뢰 데이터를 생성하는 가상 API입니다.
    일부 데이터는 5km 반경 안으로, 일부는 밖으로 생성됩니다.
    """
    strikes = []
    num_strikes = random.randint(0, 5) # 0개에서 5개의 낙뢰가 발생했다고 가정

    for i in range(num_strikes):
        # 5km 반경보다 약간 더 넓은 영역에 무작위로 좌표 생성
        lat_offset = random.uniform(-0.06, 0.06) 
        lon_offset = random.uniform(-0.06, 0.06)
        
        strike = {
            'id': f"strike_{random.randint(1000, 9999)}",
            'latitude': round(GMP_LATITUDE + lat_offset, 6),
            'longitude': round(GMP_LONGITUDE + lon_offset, 6),
            'intensity_kA': random.randint(10, 100)
        }
        strikes.append(strike)
        
    return jsonify({
        'status': 'success',
        'source': 'KMA Virtual Lightning Detector',
        'data': strikes
    })

# 2. 메인 로직 API (위 시뮬레이터 API를 호출하여 데이터를 가공)
@app.route('/api/gmp/lightning-report')
def gmp_lightning_report():
    """
    내부적으로 KMA 낙뢰 API를 호출하고, 김포공항 5km 반경 내의 낙뢰만 필터링하여 반환합니다.
    """
    try:
        # 같은 서버 내의 다른 API를 호출하기 위해 전체 URL을 동적으로 생성합니다.
        # request.host_url => http://localhost:5000/ 또는 https://your-render-app.onrender.com/
        kma_api_url = urljoin(request.host_url, 'api/kma/lightning-strikes')
        
        # KMA API 호출
        response = requests.get(kma_api_url)
        response.raise_for_status()  # 200 OK가 아니면 에러를 발생시킴
        
        all_strikes = response.json().get('data', [])
        
        # 5km 반경 내 낙뢰만 필터링
        nearby_strikes = [
            strike for strike in all_strikes 
            if is_within_radius(strike['latitude'], strike['longitude'])
        ]
        
        return jsonify({
            'status': 'success',
            'report_for': 'Gimpo Airport (GMP)',
            'nearby_strikes_count': len(nearby_strikes),
            'strikes': nearby_strikes
        })

    except requests.exceptions.RequestException as e:
        # API 호출 실패 시 에러 처리
        return jsonify({'status': 'error', 'message': f"Failed to call KMA API: {e}"}), 500


if __name__ == '__main__':
    # Render.com 배포 시에는 gunicorn이 이 파일을 실행하므로, 아래 코드는 로컬 테스트용입니다.
    app.run(host='0.0.0.0', port=5000)
