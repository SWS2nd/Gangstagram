from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)

from pymongo import MongoClient
import certifi

client = MongoClient('mongodb+srv://test:sparta@cluster0.nggqc.mongodb.net/Cluster0?retryWrites=true&w=majority', tlsCAFile=certifi.where())
db = client.dbsparta

# JWT 토큰을 만들 때 필요한 비밀문자열입니다. 아무거나 입력해도 괜찮습니다.
# 이 문자열은 서버만 알고있기 때문에, 내 서버에서만 토큰을 인코딩(=만들기)/디코딩(=풀기) 할 수 있습니다.
SECRET_KEY = 'SPARTA'

# JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import jwt

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

# 회원가입 시엔, 비밀번호를 암호화하여 DB에 저장해두는 게 좋습니다.
# 그렇지 않으면, 개발자(=나)가 회원들의 비밀번호를 볼 수 있으니까요.^^;
import hashlib

#################################
##  HTML을 주는 부분             ##
#################################
# 메인 페이지 출력 및 새로고침(로그인 시, 메인 페이지의 로고 클릭시 등)
@app.route('/')
def home():
    # 현재 이용자의 컴퓨터에 저장된 cookie 에서 mytoken 을 가져옵니다.
    token_receive = request.cookies.get('mytoken')
    try:
        # 암호화되어있는 token의 값을 우리가 사용할 수 있도록 디코딩(암호화 풀기)해줍니다!
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # email로 db에서 유저를 찾아 user_info 변수에 저장해줍니다.
        user_info = db.members.find_one({"email": payload['email']})
        # 해당 유저 정보의 닉네임을 가져와 nickname 변수에 저장하여 index.html을 출력할때 nickname 변수를 같이 넘겨줍니다.
        return render_template('index.html', nickname=user_info["nickname"])
    # 만약 해당 token의 로그인 시간이 만료되었다면, 아래와 같은 코드를 실행합니다.
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        # 만약 해당 token이 올바르게 디코딩되지 않는다면, 아래와 같은 코드를 실행합니다.
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    print("login")
    msg = request.args.get("msg")
    return render_template('sign.html', msg=msg)


#################################
##  로그인을 위한 API            ##
#################################

# [회원가입 API]
@app.route('/sign_up')
def register():
    return render_template('signup.html')

# id, pw, nickname, gender, address, dogbreed, dogsize를 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route('/sign_up/request', methods=['POST'])
def register_post():
    email_receive = request.form['email_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']
    owner_gender_receive = request.form['owner_gender_give']
    address_city_receive = request.form['address_city_give']
    address_gu_receive = request.form['address_gu_give']
    address_dong_receive = request.form['address_dong_give']
    dog_breed_receive = request.form['dog_breed_give']
    dog_size_receive = request.form['dog_size_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    doc = {
        'email': email_receive,
        'pw': pw_hash,
        'nickname': nickname_receive,
        'owner_gender': owner_gender_receive,
        'address': {
            'address_city': address_city_receive,
            'address_gu': address_gu_receive,
            'address_dong': address_dong_receive
        },
        'dog_breed': dog_breed_receive,
        'dog_size': dog_size_receive
    }

    db.members.insert_one(doc)

    return jsonify({'result': 'success'})


# [로그인 API]
# email, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.
@app.route('/login', methods=['POST'])
def login_post():
    email_receive = request.form['email_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # email, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.members.find_one({'email': email_receive, 'pw': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=암호화 풀기)해서 payload 값을 볼 수 있습니다.
        # 아래에선 email과 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저email을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'email': email_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=5)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '이메일/비밀번호가 일치하지 않습니다.'})


# [유저 정보 확인 API]
# 로그인 된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)
@app.route('/api/nickname', methods=['GET'])
def api_valid():
    token_receive = request.cookies.get('mytoken')

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        # payload 안에 email 들어있습니다. 이 eamil로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        user_info = db.members.find_one({'email': payload['email']}, {'_id': False})
        return jsonify({'result': 'success', 'nickname': user_info['nickname']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})


############################
# index.html / 메인 페이지 API #
############################
# 산책 여부 페이지 출력(날씨 정보 포함한 페이지)
@app.route('/walk_possible', methods=['GET'])
def walk_possible():
    return render_template('walking_possibility_yes.html')

# 산책 메이트 찾기 페이지 출력
@app.route('/walkmate', methods=["GET"])
def walkmate():
    return render_template("walkmate_search.html")

# 스토리 게시글 추가 페이지 출력
@app.route('/add_post', methods=["GET"])
def story_post():
    return render_template("add_post.html")

# 샵 페이지 출력
@app.route('/shop', methods=["GET"])
def shop():
    return render_template("pet_goods.html")

# 마이 페이지 출력
@app.route('/my_page', methods=["GET"])
def my_page():
    return render_template("mypage.html")


############################
# walkmate_search.html / 산책 메이트 정보 입력 페이지 API #
############################
# 산책 메이트 정보 선택 사항 받기
@app.route('/walkmate/search', methods=["POST"])
def select_walkmate_conditions():
    # 산책메이트 조건에 해당하는 항목들의 값 가져오기
    address_city_receive = request.form['address_city_give']
    address_gu_receive = request.form['address_gu_give']
    address_dong_receive = request.form['address_dong_give']
    owner_gender = request.form['owner_gender']
    dog_size = request.form['dog_size']

    # 산책메이트 조건 뽑아서 dictionary에 저장
    doc = {
        'address_city_receive': address_city_receive,
        'address_gu_receive': address_gu_receive,
        'address_dong_receive': address_dong_receive,
        'owner_gender': owner_gender,
        'dog_size': dog_size
    }
    db.same_info_list.insert_one(doc)
    return jsonify({'msg': '조건에 맞는 회원을 확인합니다'})

############################
# walkmate_list.html / 산책 메이트 목록 출력 페이지 API #
############################
# 산책 메이트 조건 선택 사항과 일치하는 리스트를 회원가입 정보에서 가져오기
@app.route('/walkmate/list', methods=["GET"])
def print_walkmate_list():
    selected_info_list = list(db.same_info_list.find({}, {'_id': False}))

    return jsonify({'selected_info_list': selected_info_list})

############################
# add_post.html / 스토리 게시글 추가 API #
############################
# 스토리 게시글 추가
@app.route('/add_post/add_story', methods=["POST"])
def story_add_post():
    denote = 0  # 내 게시물에는 denote 0, 타인의 게시물에는 denote 1 표시 후 구분
    title_receive = request.form['title_give']
    file = request.files['file_give']
    hash_receive = request.form['hash_give']

    # 해당 파일에서 확장자명만 추출
    extension = file.filename.split('.')[-1]
    # 파일 이름이 중복되면 안되므로, 지금 시간을 해당 파일 이름으로 만들어서 중복이 되지 않게 함!
    today = datetime.now()
    my_time = today.strftime('%Y-%m-%d-%H-%M-%S')
    filename = f'{title_receive}-{my_time}'
    # 파일 저장 경로 설정 (파일은 db가 아니라, 서버 컴퓨터 자체에 저장됨)
    save_to = f'static/{filename}.{extension}'
    # 파일 저장!
    file.save(save_to)

    # 아래와 같이 입하면 db에 추가 가능!
    doc = {
        'denote': denote,
        'title': title_receive,
        'img': f'{filename}.{extension}',
        'hash': hash_receive
    }
    db.story.insert_one(doc)

    return jsonify({'msg': '작성 완료'}), render_template("index.html")


# 게시글 불러오기
@app.route('/add_post/add', methods=["GET"])
def story_get():
    story_list = list(db.story.find({}, {'_id': False}))
    # 리스트를 역순으로 배열해, 출력시 가장 최근 게시물이 가장 앞에 오게끔 한다.
    story_list = sorted(story_list, reverse=True)
    return jsonify({'orders': story_list})


############################
# mypage.html / 마이 페이지 내 전체 게시물 보기 API #
############################
# 마이 페이지에서 내 전체 게시물 보기
@app.route('/my_page/my_story', methods=["GET"])
def my_story():
    my_story_list = list(db.story.find({}, {'denote': 0}, {'_id': False}))
    my_story_list = sorted(my_story_list, reverse=True)
    return jsonify({'orders': my_story_list})


# __name__은 모듈의 이름이 저장되는 변수이며 import로 모듈을 가져왔을 때 모듈의 이름이 들어감.
# 그런데 파이썬 인터프리터로 스크립트 파일을 직접 실행했을 때는 모듈의 이름이 아닌 __main__ 이 들어감.
# 어떤 스크립트 파일이든 파이썬 인터프리터가 최초로 실행한 스크립트 파일의 __name__ 변수에는
# __main__ 이 들어감. 이는 프로그램의 시작점(entry point)이라는 뜻.
# 파이썬은 최로로 시작하는 스크립트 파일과 모듈의 차이가 없음.
# 따라서, __name__ 변수를 통해 현재 스크립트 파일이 시작점인지 모듈인지를 판단함.
# 해당 if문의 경우, 프로그램의 시작점 일때만 if문 안의 코드를 실행한다는 뜻.
if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)