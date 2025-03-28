from flask import Flask, render_template, request, redirect, session, url_for,flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin123"
DEFAULT_ADMIN_PASSWORD = "@admin123"

# MongoDB Configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['blog_db']
users = db['users']
blogs = db['blogs']
admin_users=db['admin_users']

@app.route('/')
def homepage():
    # Fetch all blogs with author information
    all_blogs = blogs.find()
    blog_list = []
    for blog in all_blogs:
        author = users.find_one({'_id': ObjectId(blog['author_id'])})
        blog_list.append({
            'id': blog['_id'],
            'title': blog['title'],
            'content': blog['content'][:100] + '...',
            'author': author['username'] if author else 'Unknown'
        })
    return render_template('index.html', blogs=blog_list)

@app.route('/blog/<blog_id>')
def view_blog(blog_id):
    # Fetch a single blog and its author
    blog = blogs.find_one({'_id': ObjectId(blog_id)})
    if not blog:
        return "Blog not found", 404
    author = users.find_one({'_id': ObjectId(blog['author_id'])})
    return render_template('blog.html', blog=blog, author=author)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        full_name = request.form['full_name']
        email = request.form['email']

        # Check if the username or email already exists
        if users.find_one({'username': username}):
            return "Username already exists!", 400
        if users.find_one({'email': email}):
            return "Email already exists!", 400

        # Insert the new user into the database
        users.insert_one({
            'username': username,
            'password': password,
            'full_name': full_name,
            'email': email
        })
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('homepage'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Fetch blogs created by the logged-in user
    user_blogs = blogs.find({'author_id': session['user_id']})
    return render_template('dashboard.html', blogs=user_blogs)

@app.route('/blog/create', methods=['GET', 'POST'])
def create_blog():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        blogs.insert_one({'title': title, 'content': content, 'author_id': session['user_id']})
        return redirect(url_for('dashboard'))
    return render_template('create_blog.html')

@app.route('/blog/edit/<blog_id>', methods=['GET', 'POST'])
def edit_blog(blog_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    blog = blogs.find_one({'_id': ObjectId(blog_id)})
    if not blog or blog['author_id'] != session['user_id']:
        return "Unauthorized to edit this blog", 403
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        blogs.update_one({'_id': ObjectId(blog_id)}, {'$set': {'title': title, 'content': content}})
        return redirect(url_for('dashboard'))
    return render_template('edit_blog.html', blog=blog)

@app.route('/blog/delete/<blog_id>', methods=['POST'])
def delete_blog(blog_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    blog = blogs.find_one({'_id': ObjectId(blog_id)})
    if not blog or blog['author_id'] != session['user_id']:
        return "Unauthorized to delete this blog", 403
    blogs.delete_one({'_id': ObjectId(blog_id)})
    return redirect(url_for('dashboard'))

#profile
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch the logged-in user's details
    user = users.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        return "User not found!", 404

    return render_template('profile.html', user=user)

#edit profile
@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch the logged-in user's details
    user = users.find_one({'_id': ObjectId(session['user_id'])})
    if not user:
        return "User not found!", 404

    if request.method == 'POST':
        # Get updated details from the form
        full_name = request.form['full_name']
        email = request.form['email']
        bio = request.form['bio']

        # Update the user document in the database
        users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {
                'full_name': full_name,
                'email': email,
                'bio': bio
            }}
        )
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        print(f"Received username: {username}, password: {password}")

        if username == 'admin123' and password == '@admin123':
            session['admin_id'] = 'admin'  # Store admin identifier in the session
            print("Login successful!")
            return redirect(url_for('admin_dashboard'))

        print("Invalid credentials")
        flash("Invalid credentials", "error")
    return render_template('admin_login.html')



@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))  # Redirect to login if not logged in
    all_users = users.find()
    all_blogs = blogs.find()
    return render_template('admin_dashboard.html', users=all_users, blogs=all_blogs)

@app.route('/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    users.delete_one({'_id': ObjectId(user_id)})
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_blog/<blog_id>', methods=['POST'])
def admin_delete_blog(blog_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))

    blogs.delete_one({'_id': ObjectId(blog_id)})
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit_user/<user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    # Ensure admin is logged in
    if 'admin_id' not in session:  # Check if admin is logged in
        return redirect(url_for('admin_login'))  # Redirect to login if not logged in

    # Fetch the user from the database
    user = users.find_one({'_id': ObjectId(user_id)})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for('admin_dashboard'))

    # Handle POST request to update user details
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        bio = request.form['profile_info']

        # Update the user details in the database
        users.update_one({'_id': ObjectId(user_id)},
                         {'$set': {'username': username, 'email': email, 'bio': bio}})
        flash("User details updated successfully.", "success")
        return redirect(url_for('admin_dashboard'))

    # If GET request, render the edit user form with existing user data
    return render_template('admin_edit_user.html', user=user)


@app.route('/admin/edit_blog/<blog_id>', methods=['GET', 'POST'])
def admin_edit_blog(blog_id):
    blog = blogs.find_one({'_id': ObjectId(blog_id)})
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        blogs.update_one({'_id': ObjectId(blog_id)}, {'$set': {'title': title, 'content': content}})
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_edit_blog.html', blog=blog)


@app.route('/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
