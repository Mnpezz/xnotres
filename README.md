# Nano-Powered Gallery

This is a Flask-based web application that allows users to upload and view photo galleries, with payments handled using Nano cryptocurrency. The platform offers a unique blend of content sharing and cryptocurrency integration.

live onrender: https://xnotres.onrender.com/ 
*It will take up to 50 seconds to boot up the server. Nothing is Permanent.

## Key Features

1. Gallery Upload: Users can upload multiple images to create a gallery.
2. Payment System: Utilizes NanoPay for handling Nano cryptocurrency payments for uploads, viewing galleries, liking, and commenting.
3. Moderation: Galleries require moderator approval before becoming publicly visible.
4. View Counting: Tracks the number of views for each gallery.
5. Dynamic Pricing: Upload fees are calculated based on the total size of uploaded files.
6. Delete/Tip Functionality: Users can delete their own galleries or tip other creators.
7. Watermarking: Preview images are watermarked automatically.
8. Responsive Design: Consistent navbar across all pages for easy navigation.
9. Social Features: Users can like galleries and leave comments.
10. Image Preview: Click on images to view them in full size.
11. Moderator Dashboard: Efficient management of pending galleries with image previews.

## Roles

### Admin
- Receives payments for uploads and gallery views.
- Configures application settings (e.g., fees, allowed file types).

### Moderator
- Reviews and approves/denies pending galleries.
- Can delete inappropriate comments.
- Accesses the moderator dashboard for efficient gallery management.

### Users
- Upload galleries (payment required).
- View galleries (payment may be required).
- Like galleries and leave comments (small payment required).
- Delete their own galleries.
- Tip other creators.

## Setup

1. Install required packages: `pip install -r requirements.txt`
2. Set up your configuration in `app.py`
3. Initialize the database: `flask init-db`
4. Run the application: `python app.py`

## Configuration

Key configuration options in `app.py`:
- `ADMIN_NANO_ADDRESS`: The Nano address for receiving admin payments.
- `MODERATOR_ADDRESSES`: List of Nano addresses with moderator privileges.
- `BASE_FEE`: Base fee for uploads.
- `FEE_PER_MB`: Additional fee per MB of uploaded content.

## Usage

1. Visit the homepage to view approved galleries.
2. Use the "Create a Gallery" link to upload new galleries.
3. Pay the required fee to view full galleries.
4. Like or comment on galleries (requires small Nano payment).
5. Moderators can log in to approve or deny pending galleries.
6. Gallery creators can delete their galleries or receive tips from other users.

## Security Features

- Moderator authentication using Nano addresses.
- Watermarking of preview images.
- Secure file uploads with allowed extensions.

## Recent Updates

- Implemented social features (likes and comments).
- Added image modal for full-size viewing.
- Improved moderator dashboard with image previews and gallery cleanup functionality.
- Enhanced delete/tip system for galleries.
- Implemented dynamic fee calculation based on upload size.
- Added user session management for moderators.
- Improved error handling and logging.

## Future Improvements

- Implement user accounts for better gallery management.
- Add more detailed analytics for gallery creators.
- Enhance the moderation system with more granular controls.
- Implement a tagging system for better content discovery.
- Develop a mobile app for easier access on smartphones.

## Security Notes

- Ensure that the `SECRET_KEY` is kept secret and changed in production.
- Regularly review and update the list of moderator addresses.
- Implement additional security measures for a production environment.

## Contribution

Contributions to improve the Nano-Powered Gallery are welcome. Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

[Specify your license here]
