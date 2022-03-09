from datetime import datetime

from flask import Flask, render_template, jsonify, request, flash, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user as cur_user
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = '68889432240cf6ea8a796e959a9f647026cc9cbe1f78501bc4adca769e450dd1'
db = SQLAlchemy(app)
manager = LoginManager(app)
jwt = JWTManager(app)


class School(db.Model):
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String)
    amount = db.Column('amount', db.Integer)
    edit_data = db.Column(db.DateTime, default=datetime.now)
    editor = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    users = db.relationship('User', backref='classes', lazy=True)

    def __init__(self, name, amount):
        self.name = name
        self.amount = amount

    def __str__(self):
        return f'{self.id:>5} | {self.name:^20} | {self.amount:<5}'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))


db.create_all()


def find_user(email):
    return User.query.filter_by(email=email).one_or_none()


@manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@jwt.user_identity_loader
def user_identity(user):
    print(user.id)
    return user.id


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    print(jwt_data)
    identity = jwt_data['sub']
    print(User.query.filter_by(id=identity).one_or_none().name)
    return User.query.filter_by(id=identity).one_or_none()


def create_start():
   db.session.add_all([School('1a', 10, 'windn@e1.com'),
                       School('2b', 20, 'windn@e1.com'),
                       School('3c', 30, 'windn@e1.com')])
   db.session.commit()


@app.route('/', methods=['GET', 'POST'])
def start():
    c = School.query.count()
    if request.method == 'POST':
        cl = request.form.get('class').strip()
        ss = School.query.filter_by(name=cl)
        if ss.count() > 0:
            count_cl = ss.first().amount
        else:
            count_cl = 'Такого класса не существует'
        return render_template('index1.html', cl=cl, count_st=count_cl, count=c)
    return render_template('index1.html', count=c)


@app.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        print('Here')
        print(cur_user.name)
        name = request.form.get('name').strip()
        amount = request.form.get('count').strip()
        cur_user.classes.append(School(name=name, amount=amount))
        db.session.add(cur_user)
        db.session.commit()

        flash(f'Создан класс {name}, а в нем {amount}  учеников')
        return redirect(url_for('start'))
    return render_template('create.html')


@app.route('/show')
@login_required
def show():
    school = {x.name: x.amount for x in School.query}
    return render_template('show.html', items=school)


@app.route('/<id>/edit', methods=('GET', 'POST'))
@login_required
def edit(id):
    cls = School.query.filter_by(name=id).first()
    val = cls.amount
    if request.method == 'POST':
        c = request.form.get('name')
        a = request.form.get('count')
        cls.name = c
        cls.amount = a
        cls.edit_data = datetime.now()
        cls.editor = cur_user.id
        db.session.commit()

        flash(f'Отредактирован класс {c}, теперь в нем {a}  учеников')
        return redirect(url_for('show'))
    return render_template('edit.html', cl=id, count=val)


@app.route('/<idx>/delete')
@login_required
def delete(idx):
    flash(f'Удален класс {idx}')
    db.session.delete(School.query.filter_by(name=idx).first())
    db.session.commit()
    return redirect(url_for('show'))


@app.route('/json/create', methods=['POST'])
def json_create():
    new = request.get_json()
    c = new['class']
    a = new['count']
    db.session.add(School(c, a))
    db.session.commit()
    return jsonify({'action': 'add',
                    'driver': {'class': c,
                               'amount': a}})


@app.route('/json/edit', methods=['POST'])
@jwt_required()
def json_edit():
    new = request.get_json()
    old_key = new['old_key']
    new_key = new['new_key']
    amount = new['amount']
    print(School.query.filter_by(name=old_key).first())
    db.session.delete(School.query.filter_by(name=old_key).first())
    db.session.commit()
    current_user.classes.append(School(name=new_key, amount=amount))
    db.session.commit()
    return jsonify({'action': 'edit',
                    'driver': {'class': new_key,
                               'amount': amount}})


@app.route('/json/delete', methods=['POST'])
@jwt_required()
def json_delete():
    new = request.get_json()
    key = new['key']
    db.session.delete(School.query.filter_by(name=key).first())
    db.session.commit()
    return jsonify({'action': 'delete',
                    'driver': {'class': key}})


@app.route('/json/show')
@jwt_required()
def json_show():
    all_cl = School.query
    return jsonify({'action': 'show',
                    'request_by': current_user.name,
                    'driver': [{'class': obj.name,
                               'amount': obj.amount} for obj in all_cl]})


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_post():
    source = request.form
    email = source.get('email')
    pas = source.get('password')
    user = User.query.filter_by(email=email).one_or_none()
    print(user.name)
    if not user or not check_password_hash(user.password, pas):
        flash('Проверьте правильность написания логина, пароля и попробуйте снова')
        return redirect(url_for('login'))
    login_user(user)
    return redirect(url_for('start'))


@app.route('/json/login', methods=['POST'])
def json_login():
    source = request.json
    email = source.get('email')
    psw = source.get('password')
    user = User.query.filter_by(email=email).one_or_none()
    # print(user.email)
    if not user or not check_password_hash(user.password, psw):
        return jsonify('Неправильный логин или пароль'), 401
    access_token = create_access_token(identity=user)
    return jsonify(access_token=access_token)


@app.route('/registration')
def registration():
    return render_template('register.html')


@app.route('/registration', methods=['POST'])
def registration_post():
    source = request.form
    name = source.get('name')
    email = source.get('email')
    pas = source.get('password')
    pas2 = source.get('password2')
    if not email or pas != pas2:
        flash('Незаполненный логин, или пароли не равны друг другу')
        return redirect(url_for('registration'))
    db.session.add(User(email=email,
                        password=generate_password_hash(pas, method='sha256'),
                        name=name))
    db.session.commit()
    flash('Пользователь добавлен')
    return redirect(url_for('login'))


@app.route('/json/registration', methods=['POST'])
def json_registration():
    source = request.json
    email = source.get('email')
    psw = source.get('password')
    name = source.get('name')
    print(email, psw, name)
    if not email or not psw:
        return jsonify({'msg': 'Отсутствует email или пароль пользователя'}), 401
    db.session.add(User(email=email, password=generate_password_hash(psw, method='sha256'), name=name))
    db.session.commit()
    return jsonify({'msg': 'Пользователь зарегистрирован.'})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('start'))
