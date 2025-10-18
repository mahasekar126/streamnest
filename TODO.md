# TODO List for Mini Netflix App Updates

## 1. Make Videos Public
- [x] Remove @login_required from the index route in app.py to allow everyone to view videos.

## 2. Implement Google OAuth Login
- [x] Update requirements.txt to include authlib and requests for OAuth.
- [x] Modify app.py to add Google OAuth flow (routes for login, callback, etc.).
- [x] Update templates/login.html to include a Google login button.

## 3. Fix Non-Working Buttons
- [x] Read templates/index.html and templates/library.html to identify broken buttons (e.g., category filters, "my videos").
- [x] Update templates to make buttons functional (e.g., add routes or JS for filtering).

## 4. Followup Steps
- [x] Install new dependencies using pip install -r requirements.txt.
- [x] Test the app by running it and checking functionality (public access, Google login, buttons).
