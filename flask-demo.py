from flask import Flask, render_template, redirect, url_for, flash
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask.ext.admin import Admin, AdminIndexView, expose
from flask.ext.admin.contrib.sqla import ModelView

# Create app
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

# Create database connection object
db = SQLAlchemy(app)

# Define models
roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return self.name

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return self.email

    @property
    def is_admin(self):
        return self.roles and self.roles[0].name == 'admin'

# Setup Flask-Security
users = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, users)

class DemoAdminIndexView(AdminIndexView):

    def is_accessible(self):
        return current_user.is_authenticated() and current_user.is_admin

admin = Admin(app, url='/admin', base_template='admin_layout.html',
              index_view=DemoAdminIndexView())

class ExtendedModelView(ModelView):

    def is_accessible(self):
        return current_user.roles[0].name == 'admin'

    def __init__(self, model, session, **kwargs):
        # You can pass name and other parameters if you want to
        available_settings = [
            'column_list',
            'column_searchable_list',
            'list_template',
            'column_filters'
        ]
        for setting in available_settings:
            if setting in kwargs:
                self.__setattr__(setting, kwargs[setting])
                del(kwargs[setting])
        super(ExtendedModelView, self).__init__(model, session, **kwargs)



class UserView(ExtendedModelView):

    @expose('/userview/approve/<id>')
    def approval_view(self, id):
        flash('%s is approved' % str(id))
        return redirect(url_for('.index_view'))

    def __init__(self, session, **kwargs):
        # You can pass name and other parameters if you want to
        super(UserView, self).__init__(User, session, **kwargs)


admin.add_view(UserView(db.session,
                        column_list=('id', 'email', 'active'),
                        list_template='user_list.html',
                        column_searchable_list=('email',),
                        column_filters=('id', 'email', 'active'))
               )
admin.add_view(ExtendedModelView(Role, db.session))

# Create a user to test with
@app.before_first_request
def create_user():
    db.drop_all()
    db.create_all()
    roles = ['admin', 'member']
    for r in roles:
        new_role = Role(name=r)
        db.session.add(new_role)
    db.session.commit()
    demo_users = [
        {
            'email': 'umutcan@umutcan',
            'password': 'password',
            'role': 'admin'
        },
        {
            'email': 'deneme',
            'password': 'password',
            'role': 'member'
        }
    ]
    for u in demo_users:
        new_user = users.create_user(email=u['email'], password=u['password'])
        print u['role']
        role = Role.query.filter(Role.name == u['role']).first()
        print role
        new_user.roles.append(role)
    db.session.commit()

# Views
@app.route('/')
@login_required
def home():
    return render_template('index.html', user=current_user)

if __name__ == '__main__':
    app.run(debug=True)