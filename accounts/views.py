# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

from music.models import Genre, SongPlay
from artists.models import Artist
from library.models import Playlist
from .models import UserProfile


def login_view(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')




def signup(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_artist = request.POST.get('is_artist') == 'on'
        artist_name = request.POST.get('artist_name', '')
        bio = request.POST.get('bio', '')
        genre_id = request.POST.get('genre')
        website = request.POST.get('website', '')
        terms = request.POST.get('terms')
        artist_image = request.FILES.get('artist_image')

        # Basic validation
        errors = []
        
        if not username or not email or not password1:
            errors.append('All required fields must be filled.')
        
        if len(password1) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        if password1 != password2:
            errors.append('Passwords do not match.')
        
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        if User.objects.filter(email=email).exists():
            errors.append('Email already exists.')
        
        if not terms:
            errors.append('You must agree to the Terms of Service.')
        
        # Artist-specific validation
        if is_artist:
            if not artist_name:
                errors.append('Artist name is required when signing up as an artist.')
            elif Artist.objects.filter(name=artist_name).exists():
                errors.append('An artist with this name already exists.')
            
            # Validate image if provided
            if artist_image:
                if artist_image.size > 5 * 1024 * 1024:  # 5MB limit
                    errors.append('Image size must be less than 5MB.')
                if not artist_image.content_type.startswith('image/'):
                    errors.append('Please upload a valid image file.')

        if errors:
            for error in errors:
                messages.error(request, error)
            
            return render(request, 'accounts/signup.html', {
                'genres': Genre.objects.all(),
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'artist_name': artist_name,
                'bio': bio,
                'website': website,
                'is_artist': is_artist,
            })
        
        try:
            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # REMOVED: Don't create UserProfile here - let the signal handle it
                # The signal will automatically create the UserProfile
                
                # Update the UserProfile created by the signal
                user_profile = user.userprofile
                user_type = 'artist' if is_artist else 'listener'
                user_profile.user_type = user_type
                user_profile.save()
                
                # Create artist profile if needed
                if is_artist:
                    artist_data = {
                        'user': user,
                        'name': artist_name,
                        'bio': bio,
                        'website': website if website else None,
                    }
                    
                    # Add image if provided
                    if artist_image:
                        artist_data['image'] = artist_image
                    
                    # Add genre if provided and exists
                    if genre_id:
                        try:
                            genre = Genre.objects.get(id=genre_id)
                            artist_data['genre'] = genre
                        except Genre.DoesNotExist:
                            # Continue without genre if it doesn't exist
                            pass
                    
                    Artist.objects.create(**artist_data)
                    messages.success(request, 'Artist account created successfully! Welcome to Sangabiz!')
                else:
                    messages.success(request, 'Account created successfully! Welcome to Sangabiz!')
                
                # Login user and redirect
                login(request, user)
                
                # Redirect based on user type
                if is_artist:
                    return redirect('artist_dashboard')
                else:
                    return redirect('home')
                
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Signup error: {str(e)}")
            
            # Return with preserved data
            return render(request, 'accounts/signup.html', {
                'genres': Genre.objects.all(),
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'artist_name': artist_name,
                'bio': bio,
                'website': website,
                'is_artist': is_artist,
            })
    
    # GET request - show empty form with genres
    return render(request, 'accounts/signup.html', {
        'genres': Genre.objects.all()
    })

def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    """User profile page"""
    user_profile = request.user.userprofile
    
    # Get user stats
    liked_songs_count = user_profile.liked_songs.count()
    playlists_count = Playlist.objects.filter(user=request.user).count()
    recent_plays = SongPlay.objects.filter(user=request.user).select_related('song').order_by('-played_at')[:10]
    
    context = {
        'user_profile': user_profile,
        'liked_songs_count': liked_songs_count,
        'playlists_count': playlists_count,
        'recent_plays': recent_plays,
    }
    return render(request, 'accounts/profile.html', context)


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from .forms import ProfileUpdateForm

@login_required
def settings_view(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            form = ProfileUpdateForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your profile has been updated!')
                return redirect('settings')
        
        elif form_type == 'password':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been changed!')
                return redirect('settings')
            else:
                for error in form.errors.values():
                    messages.error(request, error)
        
        elif form_type == 'preferences':
            # Handle preferences update
            email_notifications = request.POST.get('email_notifications') == 'on'
            newsletter = request.POST.get('newsletter') == 'on'
            theme = request.POST.get('theme', 'dark')
            
            # Update user profile if it exists
            if hasattr(request.user, 'profile'):
                request.user.profile.email_notifications = email_notifications
                request.user.profile.newsletter = newsletter
                request.user.profile.theme = theme
                request.user.profile.save()
                messages.success(request, 'Your preferences have been updated!')
    
    # Initialize forms for GET request
    profile_form = ProfileUpdateForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    
    context = {
        'profile_form': profile_form,
        'password_form': password_form,
    }
    
    return render(request, 'accounts/settings.html', context)



@login_required
def become_artist_view(request):
    if request.method == 'POST':
        artist_name = request.POST.get('artist_name')
        bio = request.POST.get('bio', '')
        genre_id = request.POST.get('genre')
        website = request.POST.get('website', '')
        terms = request.POST.get('terms')
        artist_image = request.FILES.get('artist_image')
        
        # Validation
        errors = []
        
        if not artist_name:
            errors.append('Artist name is required.')
        
        if not terms:
            errors.append('You must agree to the Terms of Service.')
        
        if Artist.objects.filter(name=artist_name).exists():
            errors.append('An artist with this name already exists.')
        
        # Validate image if provided
        if artist_image:
            if artist_image.size > 5 * 1024 * 1024:  # 5MB limit
                errors.append('Image size must be less than 5MB.')
            if not artist_image.content_type.startswith('image/'):
                errors.append('Please upload a valid image file.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'accounts/become_artist.html', {
                'artist_name': artist_name,
                'bio': bio,
                'website': website,
                'genres': Genre.objects.all(),
            })
        
        try:
            with transaction.atomic():
                # Update UserProfile to artist
                user_profile = request.user.userprofile
                user_profile.user_type = 'artist'
                user_profile.save()
                
                # Prepare artist data
                artist_data = {
                    'user': request.user,
                    'name': artist_name,
                    'bio': bio if bio else f"Welcome to {artist_name}'s artist profile!",
                    'website': website if website else None,
                    'is_verified': False
                }
                
                # Add image if provided
                if artist_image:
                    artist_data['image'] = artist_image
                
                # Add genre if provided
                if genre_id:
                    try:
                        genre = Genre.objects.get(id=genre_id)
                        artist_data['genre'] = genre
                    except Genre.DoesNotExist:
                        pass  # Continue without genre
                
                # Create Artist profile
                artist = Artist.objects.create(**artist_data)
                
                # Update user's is_artist field if it exists
                if hasattr(request.user, 'is_artist'):
                    request.user.is_artist = True
                    request.user.save()
                
                messages.success(request, f'Congratulations! You are now an artist "{artist_name}". You can now upload your music.')
                return redirect('upload_music')
                
        except Exception as e:
            messages.error(request, f'Error creating artist profile: {str(e)}')
            return render(request, 'accounts/become_artist.html', {
                'artist_name': artist_name,
                'bio': bio,
                'website': website,
                'genres': Genre.objects.all(),
            })
    
    # GET request - show the form with genres
    return render(request, 'accounts/become_artist.html', {
        'genres': Genre.objects.all()
    })


@login_required
def settings_view(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'profile':
            # Handle profile update
            request.user.email = request.POST.get('email')
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name = request.POST.get('last_name', '')
            request.user.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('settings')
        
        elif form_type == 'password':
            # Handle password change
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.forms import PasswordChangeForm
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your password has been changed!')
                return redirect('settings')
            else:
                for error in form.errors.values():
                    messages.error(request, error)
        
        elif form_type == 'preferences':
            # Handle preferences update
            # You can store these in user profile or session
            messages.success(request, 'Your preferences have been updated!')
    
    return render(request, 'accounts/settings.html')



def terms_view(request):
    """Terms and Conditions page"""
    return render(request, 'accounts/terms.html')

def privacy_view(request):
    """Privacy Policy page"""
    return render(request, 'accounts/privacy.html')

def cookies_view(request):
    """Cookies Policy page"""
    return render(request, 'accounts/cookies.html') 