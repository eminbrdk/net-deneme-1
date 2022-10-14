# flask for backend
from flask import Flask, render_template, redirect, url_for, flash, abort
# bootstrap for html
from flask_bootstrap import Bootstrap
# ckeditor for typing body of blog
from flask_ckeditor import CKEditor
# datetime for time module
from datetime import date
# hashing password and checking is it correct ot not
from werkzeug.security import generate_password_hash, check_password_hash
# sqlalchemy for database
from flask_sqlalchemy import SQLAlchemy
# tablelar arası bağ kurduk
from sqlalchemy.orm import relationship
# flask_login for users
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
# ??????????????????
from forms import CreatePostForm, CreateNewUser, LoginForm, CommentForm
# gmail resmini kullandık
from flask_gravatar import Gravatar
# wrap function yarattık
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False,
                    force_lower=False, use_ssl=False, base_url=None) # gmaildeki resmi kullanmak için yazdık

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ****************************************************************************************************************
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function
# ****************************************************************************************************************


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# ilk parent table yazılmalı sonra child
#

# User Table
class User(UserMixin, db.Model):
    __tablename__ = "users" # tablea isim verdik
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    name = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)

    #This will act like a List of BlogPost objects attached to each User.
    #The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # users.id bulunamadığından ilk User tablasunu yaratmamız gerekti
    # {{post.author.name}} = user.name ile aynı

    comments = relationship("Comment", back_populates="author")


#Post Table
class BlogPost(db.Model):
    __tablename__ = "blog_posts" # tabloya isim atadık
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")
# One User can create Many BlogPost objects, we can use the SQLAlchemy docs to achieve this.
# the author property of BlogPost is now a User object.

    comments = relationship("Comment", back_populates="posts")


# Comment Table
# One to Many relationship Between the User Table (Parent) and the Comment table (Child).
# Where One User is linked to Many Comment objects.
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    # comment (child) user (parent) oldu bu kod ile
    author_id = db.Column(db.Integer, db.ForeignKey("users.id")) # user.id oluyor kendisi otamatikman
    author = relationship("User", back_populates="comments") # artık author = user author.name = user.name
    # comment.author = user , comment.author.name = user.name aynı

    # posts (parent) comment (child) oldu
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id")) # postun id si oluyor otomatikman
    posts = relationship("BlogPost", back_populates="comments") # posts.text = blogpost.text ile aynı
    # comment.posts = BlogPost


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = CreateNewUser()
    if form.validate_on_submit():

        if db.session.query(User).filter_by(email=form.email.data).first():
            flash("You have already sign up with that email, Log in instead!")
            return redirect(url_for("login"))

        hash_and_salted_password = generate_password_hash(
            password=form.password.data,
            method="pbkdf2:sha256",
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password
        )

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash("That email does not have account, try to register instead!")
            return render_template("login.html", form=form)

        elif not check_password_hash(user.password, form.password.data):
            flash("password does not match, please try again!")
            return render_template("login.html", form=form)

        else:
            user = User.query.filter_by(email=form.email.data).first()
            login_user(user)
            return redirect(url_for("get_all_posts"))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.filter_by(post_id=post_id) # düzeltilecek

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to log in or register to comment!")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment.data,
            author=current_user, # author üzerine current_user bilgilerine ulaşabileceğiz
            posts=requested_post # posts üzerinden şuanki post bilgilerine ulaşabileceğiz
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))

    return render_template("post.html", post=requested_post, current_user=current_user, form=form, comments=comments)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only # sadece adminin erişimi var
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>")
@admin_only # sadece adminin erişimi var
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only # sadece adminin girebileceği şekilde ayarladık
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.


def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi('PyCharm')

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
