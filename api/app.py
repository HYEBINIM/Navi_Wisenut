from flask import Flask, jsonify, request, render_template
import mysql.connector
import requests

app = Flask(__name__)

# MySQL 데이터베이스 연결 설정
db_config = {
    'user': 'server',
    'password': 'dltmxm1234',
    'host': 'localhost',
    'database': 'dataset'
}

# 위도와 경도를 주소로 변환하는 함수
def get_address_from_location(location):
    location = location.strip("'\"").replace(" ", "")
    try:
        lat, lon = map(float, location.split(','))
        print("============위도:", lat)
        print("============경도:", lon)
    except ValueError:
        print("Error: Invalid location format.")
        return None
    
    url = f'https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json'
    print("============Nominatim URL:", url)
    
    headers = {
        'User-Agent': 'YourAppName/1.0 (your_email@example.com)'  # 사용자 에이전트 설정
    }
    
    response = requests.get(url, headers=headers)
    print("============Nominatim 상태:", response.status_code)
    print("============Nominatim 응답 내용:", response.text)

    if response.status_code == 200:
        data = response.json()
        # 주소 구성
        # road = data['address'].get('road', '')
        quarter = data['address'].get('quarter', '')
        city = data['address'].get('city', '')
        borough = data['address'].get('borough', '')
        province = data['address'].get('province', '')
        # postcode = data['address'].get('postcode', '')

        # 원하는 형식으로 주소 조합
        if borough and quarter:
            formatted_address = f"{province} {city} {borough} {quarter}"
        elif quarter:
            formatted_address = f"{province} {city} {quarter}"
        else:
            formatted_address = f"{province} {city}"

        print("============위경도->주소:", formatted_address)  # 최종 주소 출력
        return formatted_address
    
    return None



# 기본 라우트 정의
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/llm_local', methods=['GET'])
def send_request():
    question = request.args.get('question')
    location = request.args.get('location')
    voice_id = request.args.get('id')

    print("============전송한 위경도:", location)  # 받은 위치 출력

    # location을 주소로 변환
    address = get_address_from_location(location)

    if address:

        data = {
            "question": question,
            "location": address  # 변환된 주소를 사용
        }
        
        print("============와이즈넛으로 전송", data)

        url = "https://labs.wisenut.kr/clusters/local/namespaces/rag/services/wise-irag/local"
    
        headers = {
            "Content-Type": "application/json",
            "x-token": "wisenut",
            "wisenut-authorization": "miracle-wisenut"
        }
    
        try:
            # POST 요청 보내기
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
    
            response_json = response.json()
            answer = response_json.get('result', {}).get('answer', '')
    
            print("============와이즈넛 응답내용", response_json)

            # 데이터베이스 연결
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
    
            # 데이터베이스 업데이트
            if answer and voice_id:
                cursor.execute("UPDATE voice SET voice = %s WHERE id = %s", (answer, voice_id))
                conn.commit()
    
            # 연결 종료
            cursor.close()
            conn.close()
    
            return jsonify(response_json), response.status_code, {'Content-Type': 'application/json; charset=utf-8'}
    
        except requests.exceptions.RequestException as e:
            error_response = {
                "error": str(e)
            }
            return jsonify(error_response), 500
        except mysql.connector.Error as db_error:
            error_response = {
                "error": str(db_error)
            }
            return jsonify(error_response), 500
    else:
        return jsonify({"error": "주소 변환 실패", "location": location}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234, debug=True)
