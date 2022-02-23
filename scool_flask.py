from flask import Flask, render_template, jsonify, request, flash, url_for, redirect
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class School(db.Model):
    id = db.Column('id', db.Integer, primary_key=True)
    name = db.Column('name', db.String)
    amount = db.Column('amount', db.Integer)

    def __init__(self, name, amount):
        self.name = name
        self.amount = amount

    def __str__(self):
        return f'{self.id:>5} | {self.name:^20} | {self.amount:<5}'


db.create_all()


def create_start():
   db.session.add_all([School('1a', 10), School('2b', 20), School('3c', 30)])
   db.session.commit()


@app.route('/', methods=['GET', 'POST'])
def start():
    c = School.query.count()
    if c == 0:
        create_start()
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
def create():
    if request.method == 'POST':
        print('Here')
        name = request.form.get('name').strip()
        amount = request.form.get('count').strip()
        db.session.add(School(name, amount))
        db.session.commit()
        flash(f'Создан класс {name}, а в нем {amount}  учеников')
        return redirect(url_for('start'))
    return render_template('create.html')


@app.route('/show')
def show():
    school = {x.name: x.amount for x in School.query}
    return render_template('show.html', items=school)


@app.route('/<id>/edit', methods=('GET', 'POST'))
def edit(id):
    cls = School.query.filter_by(name=id).first()
    val = cls.amount
    if request.method == 'POST':
        c = request.form.get('name')
        a = request.form.get('count')
        cls.name = c
        cls.amount = a
        db.session.commit()
        flash(f'Отредактирован класс {c}, теперь в нем {a}  учеников')
        return redirect(url_for('show'))
    return render_template('edit.html', cl=id, count=val)


@app.route('/<idx>/delete')
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
def json_edit():
    new = request.get_json()
    old_key = new['old_key']
    new_key = new['new_key']
    amount = new['amount']
    db.session.delete(School.query.filter_by(name=old_key).first())
    db.session.commit()
    db.session.add(School(new_key, amount))
    db.session.commit()
    return jsonify({'action': 'edit',
                    'driver': {'class': new_key,
                               'amount': amount}})


@app.route('/json/delete', methods=['POST'])
def json_delete():
    new = request.get_json()
    key = new['key']
    db.session.delete(School.query.filter_by(name=key).first())
    db.session.commit()
    return jsonify({'action': 'delete',
                    'driver': {'class': key}})


@app.route('/json/show', methods=['GET'])
def json_show():
    all_cl = School.query
    return jsonify({'action': 'show',
                    'driver': [{'class': obj.name,
                               'amount': obj.amount} for obj in all_cl]})
