from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont, ImageColor
from functools import wraps
import os
import zipfile
import io
from datetime import datetime
import random
import shutil
from markdown import markdown
import bleach
from flask_wtf import FlaskForm
from wtforms import BooleanField

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gallery.db'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'zip'}
app.config['ADMIN_NANO_ADDRESS'] = 'nano_3urn99zwefm5q8miwqkiypfqx3ikh59ujpiuggewnynoke6eqpntgu78do7j'
app.config['BASE_FEE'] = 0.01  # Base fee in NANO
app.config['FEE_PER_MB'] = 0.001  # Additional fee per MB
app.config['MODERATOR_ADDRESSES'] = ['nano_3urn99zwefm5q8miwqkiypfqx3ikh59ujpiuggewnynoke6eqpntgu78do7j', '@development']

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)

class Gallery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    preview_image = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    total_size = db.Column(db.Float, nullable=False)  # Total size in MB
    view_count = db.Column(db.Integer, default=0)
    is_approved = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    creator_address = db.Column(db.String(65), nullable=False)
    likes = db.Column(db.Integer, default=0)
    private_comments = db.Column(db.Boolean, default=False)
    
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    gallery_id = db.Column(db.Integer, db.ForeignKey('gallery.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)
    is_approved = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    creator_address = db.Column(db.String(65), nullable=False)
    likes = db.Column(db.Integer, default=0)  # Make sure this line is present
    private_comments = db.Column(db.Boolean, default=False)

class BlogComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blog_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def calculate_upload_fee(total_size_mb):
    base_fee = app.config['BASE_FEE']
    fee_per_mb = app.config['FEE_PER_MB']
    storage_fee = total_size_mb * fee_per_mb
    total_fee = base_fee + storage_fee
    return round(total_fee, 6)  # Round to 6 decimal places

def add_watermark(image, watermark_text=None, watermark_type=None):
    try:
        watermark_type = watermark_type or app.config.get('WATERMARK_TYPE', 'text')
        app.logger.info(f"Adding watermark. Type: {watermark_type}")
        
        # Create a copy of the image to avoid modifying the original
        watermarked = image.copy()
        
        # Convert the image to RGBA if it's not already
        if watermarked.mode != 'RGBA':
            watermarked = watermarked.convert('RGBA')
        
        # Create a transparent overlay
        overlay = Image.new('RGBA', watermarked.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        if watermark_type == "text":
            watermark_text = watermark_text or app.config.get('WATERMARK_TEXT', 'Preview')
            app.logger.info(f"Using text watermark: {watermark_text}")
            font_size = int(min(watermarked.width, watermarked.height) / 10)  # Adjust size as needed
            font = ImageFont.truetype("arial.ttf", font_size)  # Use a system font or provide path to a custom font
            text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_position = ((watermarked.width - text_bbox[2]) // 2, (watermarked.height - text_bbox[3]) // 2)
            draw.text(text_position, watermark_text, font=font, fill=(255, 255, 255, 192))
        else:
            logo_path = app.config.get('WATERMARK_LOGO')
            app.logger.info(f"Using logo watermark. Path: {logo_path}")
            if logo_path and os.path.exists(logo_path):
                logo = Image.open(logo_path).convert('RGBA')
                logo_size = (min(watermarked.width, watermarked.height) // 2, min(watermarked.width, watermarked.height) // 2)
                logo = logo.resize(logo_size, Image.LANCZOS)
                position = ((watermarked.width - logo_size[0]) // 2, (watermarked.height - logo_size[1]) // 2)
                overlay.paste(logo, position, logo)
            else:
                app.logger.warning("Logo file not found. Falling back to text watermark.")
                watermark_text = "Preview"
                font_size = int(min(watermarked.width, watermarked.height) / 10)
                font = ImageFont.truetype("arial.ttf", font_size)
                text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
                text_position = ((watermarked.width - text_bbox[2]) // 2, (watermarked.height - text_bbox[3]) // 2)
                draw.text(text_position, watermark_text, font=font, fill=(255, 255, 255, 192))
        
        # Combine the original image with the overlay
        watermarked = Image.alpha_composite(watermarked, overlay)
        
        app.logger.info("Watermark added successfully")
        return watermarked.convert('RGB')  # Convert back to RGB for saving as JPEG
    except Exception as e:
        app.logger.error(f"Error adding watermark: {str(e)}")
        return image  # Return the original image if watermarking fails
    
def truncate_description(description, max_length=200):
    if len(description) <= max_length:
        return description
    return description[:max_length].rsplit(' ', 1)[0] + '...'

def sanitize_markdown(content):
    allowed_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre']
    allowed_attributes = {'*': ['class']}
    return bleach.clean(markdown(content), tags=allowed_tags, attributes=allowed_attributes)

@app.route('/')
def index():
    galleries = Gallery.query.filter_by(is_approved=True).all()
    blogs = BlogPost.query.filter_by(is_approved=True).all()
    
    for gallery in galleries:
        gallery.total_size = round(gallery.total_size, 2)  # Round to 2 decimal places
    
    for blog in blogs:
        blog.short_description = truncate_description(blog.description)
        blog.preview_content = truncate_description(sanitize_markdown(blog.content), max_length=300)
        blog.total_size = round(blog.total_size, 2)  # Round to 2 decimal places
    
    return render_template('index.html', galleries=galleries, blogs=blogs)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        try:
            if 'files[]' not in request.files:
                return jsonify({"success": False, "message": "No file part"})
            files = request.files.getlist('files[]')
            if not files or files[0].filename == '':
                return jsonify({"success": False, "message": "No selected files"})
            
            gallery_name = request.form.get('gallery_name')
            if not gallery_name:
                return jsonify({"success": False, "message": "Gallery name is required"})
            
            base_fee = float(request.form.get('base_fee', 0))
            storage_fee = float(request.form.get('storage_fee', 0))
            total_fee = float(request.form.get('total_fee', 0))
            user_price = float(request.form.get('user_price', 0))

            total_size_mb = sum(file.content_length for file in files) / (1024 * 1024)
            
            gallery_folder = os.path.join(app.config['UPLOAD_FOLDER'], gallery_name)
            os.makedirs(gallery_folder, exist_ok=True)
            
            preview_image = None
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(gallery_folder, filename)
                    file.save(file_path)
                    
                    if not preview_image and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        preview_image = filename
                        with Image.open(file_path) as img:
                            watermarked = add_watermark(img)
                            watermarked.save(file_path, "JPEG")
            
            if not preview_image:
                return jsonify({"success": False, "message": "No valid image files found"})
            
            session['pending_gallery_upload'] = {
                'name': gallery_name,
                'preview_image': preview_image,
                'user_price': user_price,
                'total_size': total_size_mb,
                'base_fee': base_fee,
                'storage_fee': storage_fee,
                'total_fee': total_fee
            }
            
            return jsonify({
                "success": True, 
                "base_fee": base_fee,
                "storage_fee": round(storage_fee, 6),
                "total_fee": round(total_fee, 6)
            })
        except Exception as e:
            app.logger.error(f"Error during upload: {str(e)}")
            return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})
    return render_template('upload.html', base_fee=app.config['BASE_FEE'], fee_per_mb=app.config['FEE_PER_MB'])

@app.route('/finalize_gallery_upload', methods=['POST'])
def finalize_gallery_upload():
    try:
        pending_upload = session.pop('pending_gallery_upload', None)
        if not pending_upload:
            return jsonify({"success": False, "message": "No pending gallery upload found"})

        creator_address = request.form.get('creator_address')
        if not creator_address:
            return jsonify({"success": False, "message": "Creator address is missing"})

        new_gallery = Gallery(
            name=pending_upload['name'],
            preview_image=pending_upload['preview_image'],
            price=pending_upload['user_price'],
            user_id=1,  # Assuming a default user for now
            total_size=pending_upload['total_size'],
            is_approved=False,  # Explicitly set to False to ensure it's queued for moderation
            date_created=datetime.utcnow(),
            creator_address=creator_address
        )
        db.session.add(new_gallery)
        db.session.commit()

        return jsonify({"success": True, "message": "Gallery uploaded successfully and sent for moderation"})
    except Exception as e:
        app.logger.error(f"Error during gallery upload finalization: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})

@app.route('/gallery/<int:gallery_id>')
def view_gallery(gallery_id):
    gallery = Gallery.query.get_or_404(gallery_id)
    gallery.view_count += 1
    db.session.commit()
    
    gallery_path = os.path.join(app.config['UPLOAD_FOLDER'], gallery.name)
    if os.path.isdir(gallery_path):
        images = [f for f in os.listdir(gallery_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    else:
        images = [gallery.preview_image]
    
    total_size_mb = round(gallery.total_size, 2)  # Keep it in MB and round to 2 decimal places
    
    return render_template('gallery.html', gallery=gallery, images=images, total_size_mb=total_size_mb, 
                           comments_visible=True)

@app.route('/pay/<int:gallery_id>', methods=['POST'])
def pay(gallery_id):
    gallery = Gallery.query.get_or_404(gallery_id)
    gallery.is_paid = True
    db.session.commit()
    return jsonify({"success": True, "message": "Payment successful"})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/moderator_login', methods=['POST'])
def moderator_login():
    data = request.json
    received_address = data['address'].strip().lower()
    app.logger.info(f"Received login attempt from address: {received_address}")
    
    normalized_moderator_addresses = [addr.strip().lower() for addr in app.config['MODERATOR_ADDRESSES']]
    app.logger.info(f"Normalized moderator addresses: {normalized_moderator_addresses}")
    
    if received_address in normalized_moderator_addresses:
        session['moderator'] = received_address
        return jsonify({"success": True, "message": "Login successful"})
    return jsonify({"success": False, "message": "Unauthorized"})

@app.route('/moderator_logout')
def moderator_logout():
    session.pop('moderator', None)
    return redirect(url_for('index'))

def moderator_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'moderator' not in session:
            return redirect(url_for('moderator_login_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/moderator_login_page')
def moderator_login_page():
    return render_template('moderator_login.html')

@app.route('/moderator')
@moderator_required
def moderator_view():
    pending_galleries = Gallery.query.filter_by(is_approved=False).all()
    pending_blogs = BlogPost.query.filter_by(is_approved=False).all()
    for gallery in pending_galleries:
        gallery_path = os.path.join(app.config['UPLOAD_FOLDER'], gallery.name)
        gallery.images = [f for f in os.listdir(gallery_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        gallery.total_size = round(gallery.total_size, 2)  # Round to 2 decimal places
    for blog in pending_blogs:
        blog.formatted_content = sanitize_markdown(blog.content)
        blog.total_size = round(os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], blog.cover_image)) / (1024 * 1024), 2)  # Size in MB
    return render_template('moderator.html', galleries=pending_galleries, blogs=pending_blogs)

@app.route('/approve/<int:gallery_id>', methods=['POST'])
def approve_gallery(gallery_id):
    gallery = Gallery.query.get_or_404(gallery_id)
    gallery.is_approved = True
    db.session.commit()
    return jsonify({"success": True, "message": "Gallery approved"})

@app.route('/deny/<int:gallery_id>', methods=['POST'])
def deny_gallery(gallery_id):
    gallery = Gallery.query.get_or_404(gallery_id)
    db.session.delete(gallery)
    db.session.commit()
    return jsonify({"success": True, "message": "Gallery denied and removed"})

@app.route('/request_delete/<int:gallery_id>', methods=['POST'])
def request_delete(gallery_id):
    gallery = Gallery.query.get_or_404(gallery_id)
    delete_amount = round(random.uniform(0.01, 0.1), 6)  # Random amount between 0.01 and 0.1 NANO
    return jsonify({
        "success": True,
        "delete_amount": delete_amount,
        "message": f"To delete/tip this gallery, please send exactly {delete_amount} NANO."
    })

@app.route('/cleanup_galleries', methods=['POST'])
@moderator_required
def cleanup_galleries():
    try:
        galleries = Gallery.query.all()
        blogs = BlogPost.query.all()
        cleaned_count = 0
        
        for gallery in galleries:
            gallery_path = os.path.join(app.config['UPLOAD_FOLDER'], gallery.name)
            if not os.path.exists(gallery_path):
                db.session.delete(gallery)
                cleaned_count += 1
        
        for blog in blogs:
            cover_image_path = os.path.join(app.config['UPLOAD_FOLDER'], blog.cover_image)
            if not os.path.exists(cover_image_path):
                db.session.delete(blog)
                cleaned_count += 1
        
        db.session.commit()
        return jsonify({"success": True, "message": f"Cleaned up {cleaned_count} items"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})

@app.route('/delete_gallery/<int:gallery_id>', methods=['POST'])
def delete_gallery(gallery_id):
    data = request.json
    gallery = Gallery.query.get_or_404(gallery_id)
    
    app.logger.info(f"Delete request for gallery {gallery_id}")
    app.logger.info(f"Request data: {data}")
    app.logger.info(f"Gallery creator address: {gallery.creator_address}")
    
    if data['address'] == gallery.creator_address:
        gallery_path = os.path.join(app.config['UPLOAD_FOLDER'], gallery.name)
        shutil.rmtree(gallery_path)
        db.session.delete(gallery)
        db.session.commit()
        app.logger.info(f"Gallery {gallery_id} deleted by creator")
        return jsonify({"success": True, "message": "Gallery successfully deleted"})
    else:
        app.logger.info(f"Tip sent to creator of gallery {gallery_id}")
        return jsonify({"success": True, "message": f"Tip of {data['amount']} NANO sent to gallery creator"})

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
@moderator_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"success": True, "message": "Comment deleted successfully"})

@app.route('/delete_tip/<int:gallery_id>')
def delete_tip_page(gallery_id):
    gallery = Gallery.query.get_or_404(gallery_id)
    app.logger.info(f"Delete/Tip page accessed for gallery {gallery_id}")
    app.logger.info(f"Creator address: {gallery.creator_address}")
    return render_template('delete_tip.html', gallery=gallery)

@app.route('/like/<int:gallery_id>', methods=['POST'])
def like_gallery(gallery_id):
    payment_data = request.json
    # Verify payment here if needed
    gallery = Gallery.query.get_or_404(gallery_id)
    gallery.likes += 1
    db.session.commit()
    return jsonify({"success": True, "likes": gallery.likes})

@app.route('/get_comments/<int:gallery_id>')
def get_comments(gallery_id):
    comments = Comment.query.filter_by(gallery_id=gallery_id).order_by(Comment.date_created.desc()).all()
    return jsonify({
        "success": True, 
        "comments": [
            {
                "id": c.id, 
                "content": c.content, 
                "date_created": c.date_created.isoformat()
            } for c in comments
        ]
    })

@app.route('/comment/<int:gallery_id>', methods=['POST'])
def add_comment(gallery_id):
    data = request.json
    content = data.get('content')
    new_comment = Comment(content=content, user_id=1, gallery_id=gallery_id)
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({
        "success": True, 
        "comment": content, 
        "comment_id": new_comment.id,
        "date_created": new_comment.date_created.isoformat()
    })

@app.route('/upload_blog', methods=['GET', 'POST'])
def upload_blog():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        content = request.form.get('content')
        price = float(request.form.get('price', 0))
        creator_address = request.form.get('creator_address')

        if 'cover_image' not in request.files:
            return jsonify({"success": False, "message": "No cover image uploaded"})
        
        cover_image = request.files['cover_image']
        if cover_image.filename == '':
            return jsonify({"success": False, "message": "No cover image selected"})
        
        if cover_image and allowed_file(cover_image.filename):
            filename = secure_filename(cover_image.filename)
            cover_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            cover_image.save(cover_image_path)

            total_size_mb = os.path.getsize(cover_image_path) / (1024 * 1024)
            upload_fee = calculate_upload_fee(total_size_mb)

            session['pending_blog_upload'] = {
                'title': title,
                'description': description,
                'content': content,
                'cover_image': filename,
                'price': price,
                'upload_fee': upload_fee
            }

            return jsonify({"success": True, "upload_fee": upload_fee})
        else:
            return jsonify({"success": False, "message": "Invalid file type"})
    return render_template('upload_blog.html', base_fee=app.config['BASE_FEE'], fee_per_mb=app.config['FEE_PER_MB'])

@app.route('/finalize_blog_upload', methods=['POST'])
def finalize_blog_upload():
    try:
        pending_upload = session.pop('pending_blog_upload', None)
        if not pending_upload:
            return jsonify({"success": False, "message": "No pending blog upload found"})

        creator_address = request.form.get('creator_address')
        if not creator_address:
            return jsonify({"success": False, "message": "Creator address is missing"})

        total_price = pending_upload['price'] + pending_upload['upload_fee']

        new_blog = BlogPost(
            title=pending_upload['title'],
            description=pending_upload['description'],
            content=pending_upload['content'],
            cover_image=pending_upload['cover_image'],
            price=total_price,
            user_id=1,  # Assuming a default user for now
            is_approved=False,
            creator_address=creator_address
        )
        db.session.add(new_blog)
        db.session.commit()

        return jsonify({"success": True, "message": "Blog post uploaded successfully"})
    except Exception as e:
        app.logger.error(f"Error during blog upload finalization: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})

@app.route('/blog/<int:blog_id>')
def view_blog(blog_id):
    blog = BlogPost.query.get_or_404(blog_id)
    blog.view_count += 1
    db.session.commit()
    
    short_description = truncate_description(blog.description, max_length=200)
    preview_content = truncate_description(sanitize_markdown(blog.content), max_length=300)
    
    return render_template('blog.html', blog=blog, short_description=short_description, preview_content=preview_content, comments_visible=True)

@app.route('/pay_blog/<int:blog_id>', methods=['POST'])
def pay_blog(blog_id):
    blog = BlogPost.query.get_or_404(blog_id)
    blog.is_paid = True
    db.session.commit()
    return jsonify({"success": True, "message": "Payment successful", "content": markdown(blog.content)})

@app.route('/approve_blog/<int:blog_id>', methods=['POST'])
@moderator_required
def approve_blog(blog_id):
    blog = BlogPost.query.get_or_404(blog_id)
    blog.is_approved = True
    db.session.commit()
    return jsonify({"success": True, "message": "Blog post approved"})

@app.route('/deny_blog/<int:blog_id>', methods=['POST'])
@moderator_required
def deny_blog(blog_id):
    blog = BlogPost.query.get_or_404(blog_id)
    # Delete the cover image
    cover_image_path = os.path.join(app.config['UPLOAD_FOLDER'], blog.cover_image)
    if os.path.exists(cover_image_path):
        os.remove(cover_image_path)
    db.session.delete(blog)
    db.session.commit()
    return jsonify({"success": True, "message": "Blog post denied and removed"})

@app.route('/like_blog/<int:blog_id>', methods=['POST'])
def like_blog(blog_id):
    payment_data = request.json
    # Verify payment here if needed
    blog = BlogPost.query.get_or_404(blog_id)
    blog.likes += 1
    db.session.commit()
    return jsonify({"success": True, "likes": blog.likes})

@app.route('/get_blog_comments/<int:blog_id>')
def get_blog_comments(blog_id):
    comments = BlogComment.query.filter_by(blog_id=blog_id).order_by(BlogComment.date_created.desc()).all()
    return jsonify({
        "success": True, 
        "comments": [
            {
                "id": c.id, 
                "content": c.content, 
                "date_created": c.date_created.isoformat()
            } for c in comments
        ]
    })

@app.route('/add_blog_comment/<int:blog_id>', methods=['POST'])
def add_blog_comment(blog_id):
    data = request.json
    content = data.get('content')
    new_comment = BlogComment(content=content, user_id=1, blog_id=blog_id)
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({
        "success": True, 
        "comment": content, 
        "comment_id": new_comment.id,
        "date_created": new_comment.date_created.isoformat()
    })

@app.route('/delete_blog_comment/<int:comment_id>', methods=['POST'])
@moderator_required
def delete_blog_comment(comment_id):
    comment = BlogComment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"success": True, "message": "Comment deleted successfully"})

@app.route('/delete_blog/<int:blog_id>', methods=['POST'])
def delete_blog(blog_id):
    data = request.json
    blog = BlogPost.query.get_or_404(blog_id)
    
    app.logger.info(f"Delete request for blog {blog_id}")
    app.logger.info(f"Request data: {data}")
    app.logger.info(f"Blog creator address: {blog.creator_address}")
    
    if data['address'] == blog.creator_address:
        cover_image_path = os.path.join(app.config['UPLOAD_FOLDER'], blog.cover_image)
        if os.path.exists(cover_image_path):
            os.remove(cover_image_path)
        db.session.delete(blog)
        db.session.commit()
        app.logger.info(f"Blog {blog_id} deleted by creator")
        return jsonify({"success": True, "message": "Blog post successfully deleted"})
    else:
        app.logger.info(f"Tip sent to creator of blog {blog_id}")
        return jsonify({"success": True, "message": f"Tip of {data['amount']} NANO sent to blog creator"})

@app.route('/delete_blog_page/<int:blog_id>')
def delete_blog_page(blog_id):
    blog = BlogPost.query.get_or_404(blog_id)
    app.logger.info(f"Delete/Tip page accessed for blog {blog_id}")
    app.logger.info(f"Creator address: {blog.creator_address}")
    return render_template('delete_blog.html', blog=blog)

def init_db():
    with app.app_context():
        db.drop_all()  # This will drop all existing tables
        db.create_all()  # This will create all tables defined in your models
        print("Database initialized.")

@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Initialized the database.")

@app.route('/reset_db')
def reset_db():
    init_db()
    return "Database reset successfully"

@app.route('/adjust_watermark', methods=['POST'])
@moderator_required
def adjust_watermark():
    watermark_type = request.form.get('watermark_type')
    app.config['WATERMARK_TYPE'] = watermark_type

    if watermark_type == 'text':
        watermark_text = request.form.get('watermark_text')
        app.config['WATERMARK_TEXT'] = watermark_text
        return jsonify({"success": True, "message": "Text watermark updated successfully", "type": "text", "text": watermark_text})
    elif watermark_type == 'logo':
        if 'watermark_logo' not in request.files:
            return jsonify({"success": False, "message": "No file part"})
        file = request.files['watermark_logo']
        if file.filename == '':
            return jsonify({"success": False, "message": "No selected file"})
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'watermark_logo.png')
            file.save(logo_path)
            app.config['WATERMARK_LOGO'] = logo_path
            return jsonify({"success": True, "message": "Logo watermark uploaded successfully", "type": "logo"})
        else:
            return jsonify({"success": False, "message": "Invalid file type"})
    else:
        return jsonify({"success": False, "message": "Invalid watermark type"})
    
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/delete_gallery_comment/<int:comment_id>', methods=['POST'])
@moderator_required
def delete_gallery_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({"success": True, "message": "Comment deleted successfully"})

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
