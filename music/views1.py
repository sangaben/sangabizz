from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
import json
import os
from datetime import timedelta

from .models import Song, Genre, Playlist, UserProfile, SongPlay, SongDownload, Artist, Like, Follow
from .forms import SongUploadForm



# ===== UTILITY FUNCTIONS =====
def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ===== AUTHENTICATION VIEWS =====
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
    
    return render(request, 'login.html')


def signup(request):
    """User registration view"""
    # Get genres for the dropdown - ADD THIS LINE
    genres = Genre.objects.all()
    
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
        terms = request.POST.get('terms') == 'on'

        # Basic validation
        errors = []
        
        if not username or not email or not password1 or not password2:
            errors.append('All required fields must be filled.')
        
        if not terms:
            errors.append('You must agree to the Terms of Service.')
        
        if password1 != password2:
            errors.append('Passwords do not match.')
        
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        if User.objects.filter(email=email).exists():
            errors.append('Email already exists.')
        
        # Password strength validation
        if len(password1) < 8:
            errors.append('Password must be at least 8 characters long.')
        
        # Artist-specific validation
        if is_artist:
            if not artist_name:
                errors.append('Artist name is required when signing up as an artist.')
            elif len(artist_name) < 2:
                errors.append('Artist name must be at least 2 characters long.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            # Preserve form data on error - ADD GENRES TO CONTEXT
            context = {
                'preserved_data': {
                    'username': username,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_artist': is_artist,
                    'artist_name': artist_name,
                    'bio': bio,
                    'genre': genre_id,
                },
                'genres': genres  # ADD THIS LINE
            }
            return render(request, 'signup.html', context)
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create or update user profile
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'user_type': 'artist' if is_artist else 'listener'}
            )
            
            if not created:
                # Update existing profile
                profile.user_type = 'artist' if is_artist else 'listener'
                profile.save()
            
            # Create artist profile if user is artist
            if is_artist:
                artist_data = {
                    'user': user,
                    'name': artist_name.strip(),
                    'bio': bio.strip() if bio else None,
                }
                
                # Add genre if provided and exists
                if genre_id:
                    try:
                        genre = Genre.objects.get(id=genre_id)
                        artist_data['genre'] = genre
                    except (Genre.DoesNotExist, ValueError):
                        # Continue without genre if it doesn't exist or is invalid
                        pass
                
                # Use get_or_create to avoid duplicates
                artist, artist_created = Artist.objects.get_or_create(
                    user=user,
                    defaults=artist_data
                )
                
                if not artist_created:
                    # Update existing artist profile
                    for key, value in artist_data.items():
                        if key != 'user':  # Don't update the user relationship
                            setattr(artist, key, value)
                    artist.save()
                
                messages.success(request, 'Artist account created successfully! You can now upload your music.')
            else:
                messages.success(request, 'Account created successfully! Welcome to Sangabiz.')
            
            # Login user and redirect
            login(request, user)
            
            # Redirect based on user type
            if is_artist:
                return redirect('artist_dashboard')
            else:
                return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            # If user was created but failed later, delete it
            if 'user' in locals() and user.id:
                user.delete()
            
            # Preserve form data on exception - ADD GENRES TO CONTEXT
            context = {
                'preserved_data': {
                    'username': username,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_artist': is_artist,
                    'artist_name': artist_name,
                    'bio': bio,
                    'genre': genre_id,
                },
                'genres': genres  # ADD THIS LINE
            }
            return render(request, 'signup.html', context)
    
    # GET request - show empty form - ADD GENRES TO CONTEXT
    context = {
        'genres': genres  # ADD THIS LINE
    }
    return render(request, 'signup.html', context)


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('home')


# ===== MAIN PAGES VIEWS =====
def home(request):
    """Home page with featured content"""
    # Get featured songs (most played)
    featured_songs = Song.objects.all().order_by('-plays')[:8]
    
    # Get most played songs for charts
    most_played = Song.objects.all().order_by('-plays')[:5]
    most_downloaded = Song.objects.all().order_by('-downloads')[:5]
    
    # Get genres with song counts
    genres = Genre.objects.annotate(song_count=Count('song'))

    genres = Genre.objects.annotate(song_count=Count('song')).filter(song_count__gt=0)
    
    # Get total stats
    total_songs = Song.objects.count()
    total_plays = Song.objects.aggregate(total=Sum('plays'))['total'] or 0
    total_downloads = Song.objects.aggregate(total=Sum('downloads'))['total'] or 0
    total_artists = Artist.objects.filter(is_verified=True).count()
    
    # Get recent plays for authenticated users
    recent_plays = []
    if request.user.is_authenticated:
        recent_plays = SongPlay.objects.filter(user=request.user).select_related('song').order_by('-played_at')[:5]
    
    # Get new artists (last 30 days) - Using existing properties instead of annotations
    thirty_days_ago = timezone.now() - timedelta(days=30)
    new_artists = Artist.objects.filter(
        created_at__gte=thirty_days_ago,
        is_verified=True
    ).order_by('-created_at')[:8]
    
    # Get trending artists (most plays in last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    trending_artists = Artist.objects.filter(
        is_verified=True
    ).annotate(
        weekly_plays=Sum(
            'songs__plays',
            filter=Q(songs__upload_date__gte=seven_days_ago)
        ),
        followers_count=Count('followers')
    ).filter(
        weekly_plays__isnull=False
    ).order_by('-weekly_plays')[:8]
    
    context = {
        'featured_songs': featured_songs,
        'most_played': most_played,
        'most_downloaded': most_downloaded,
        'genres': genres,
        'total_songs': total_songs,
        'total_plays': total_plays,
        'total_downloads': total_downloads,
        'total_artists': total_artists,
        'recent_plays': recent_plays,
        'new_artists': new_artists,
        'trending_artists': trending_artists,
    }
    return render(request, 'home.html', context)


def discover(request):
    """Discover page with all songs"""
    songs = Song.objects.all().order_by('-upload_date')
    genres = Genre.objects.all()
    
    context = {
        'songs': songs,
        'genres': genres,
    }
    return render(request, 'discover.html', context)


def search(request):
    """Search functionality"""
    query = request.GET.get('q', '')
    songs = Song.objects.filter(
        title__icontains=query, 
        is_approved=True
    ) | Song.objects.filter(
        artist__name__icontains=query
    )
    
    context = {
        'songs': songs,
        'query': query,
    }
    return render(request, 'search.html', context)


# ===== ARTIST-RELATED VIEWS =====
def artists(request):
    """All artists page"""
    artists_list = Artist.objects.filter(is_verified=True).order_by('-created_at')
    
    context = {
        'artists': artists_list,
        'title': 'All Artists'
    }
    return render(request, 'artists.html', context)


def trending_artists(request):
    """Trending artists page"""
    seven_days_ago = timezone.now() - timedelta(days=7)
    trending_artists_list = Artist.objects.filter(
        is_verified=True
    ).annotate(
        weekly_plays=Sum(
            'songs__plays',
            filter=Q(songs__upload_date__gte=seven_days_ago)
        ),
        followers_count=Count('followers')
    ).filter(
        weekly_plays__isnull=False
    ).order_by('-weekly_plays')
    
    context = {
        'artists': trending_artists_list,
        'title': 'Trending Artists'
    }
    return render(request, 'artists.html', context)


def artist_detail(request, artist_id):
    """Artist profile page"""
    artist = get_object_or_404(Artist, id=artist_id, is_verified=True)
    songs = artist.songs.filter(is_approved=True).order_by('-upload_date')
    
    # Check if current user follows this artist
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user, 
            artist=artist
        ).exists()
    
    context = {
        'artist': artist,
        'songs': songs,
        'is_following': is_following,
    }
    return render(request, 'artist_detail.html', context)


@login_required
def artist_dashboard(request):
    """Artist dashboard"""
    try:
        artist = request.user.artist_profile
    except Artist.DoesNotExist:
        messages.error(request, "You need to be an artist to access the dashboard.")
        return redirect('home')

    # Get artist stats
    total_plays = artist.songs.aggregate(total=Sum('plays'))['total'] or 0
    total_downloads = artist.songs.aggregate(total=Sum('downloads'))['total'] or 0
    total_likes = Like.objects.filter(song__artist=artist).count()
    total_followers = Follow.objects.filter(artist=artist).count()

    # Get recent songs
    recent_songs = artist.songs.all().order_by('-upload_date')[:6]

    # Get top songs
    top_songs = artist.songs.all().order_by('-plays')[:5]

    # Get genres for upload form
    genres = Genre.objects.all()

    # Mock recent activity
    recent_activity = [
        {'icon': 'play', 'message': 'Your song "Summer Vibes" got 15 new plays', 'time': '2 hours ago'},
        {'icon': 'heart', 'message': 'Someone liked your song "Night Dreams"', 'time': '5 hours ago'},
        {'icon': 'user-plus', 'message': 'You gained 3 new followers', 'time': '1 day ago'},
        {'icon': 'download', 'message': 'Your song "Ocean Waves" was downloaded 8 times', 'time': '2 days ago'},
    ]

    context = {
        'artist': artist,
        'total_plays': total_plays,
        'total_downloads': total_downloads,
        'total_likes': total_likes,
        'total_followers': total_followers,
        'recent_songs': recent_songs,
        'top_songs': top_songs,
        'genres': genres,
        'recent_activity': recent_activity,
    }

    return render(request, 'artist_dashboard.html', context)


# ===== GENRE VIEWS =====
def genres(request):
    """All genres page"""
    genres = Genre.objects.all()
    
    context = {
        'genres': genres,
    }
    return render(request, 'genres.html', context)


def genre_songs(request, genre_id):
    """Songs by specific genre"""
    genre = get_object_or_404(Genre, id=genre_id)
    songs = Song.objects.filter(genre=genre)
    
    context = {
        'genre': genre,
        'songs': songs,
    }
    return render(request, 'genre_songs.html', context)


# ===== LIBRARY & PLAYLIST VIEWS =====
@login_required
def library(request):
    """User library with liked songs and playlists"""
    user_profile = UserProfile.objects.get(user=request.user)
    liked_songs = user_profile.liked_songs.all()
    playlists = Playlist.objects.filter(user=request.user)
    
    context = {
        'liked_songs': liked_songs,
        'playlists': playlists,
    }
    return render(request, 'library.html', context)


@login_required
def playlists(request):
    """User playlists management"""
    playlists = Playlist.objects.filter(user=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Playlist.objects.create(name=name, user=request.user)
            messages.success(request, 'Playlist created successfully!')
            return redirect('playlists')
    
    context = {
        'playlists': playlists,
    }
    return render(request, 'playlists.html', context)


@login_required
def playlist_detail(request, playlist_id):
    """Individual playlist detail"""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    
    if request.method == 'POST':
        song_id = request.POST.get('song_id')
        if song_id:
            song = get_object_or_404(Song, id=song_id)
            playlist.songs.add(song)
            messages.success(request, 'Song added to playlist!')
    
    context = {
        'playlist': playlist,
    }
    return render(request, 'playlist_detail.html', context)


# ===== SONG UPLOAD & MANAGEMENT =====
@login_required
def upload_music(request):
    """Song upload for artists"""
    # Check if user is an artist
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_artist:
        messages.error(request, "You need to be an artist to upload music.")
        return redirect('discover')
    
    try:
        artist_profile = Artist.objects.get(user=request.user)
    except Artist.DoesNotExist:
        messages.error(request, "Artist profile not found.")
        return redirect('discover')
    
    if request.method == 'POST':
        form = SongUploadForm(request.POST, request.FILES)
        if form.is_valid():
            song = form.save(commit=False)
            song.artist = artist_profile
            song.plays = 0
            song.downloads = 0
            song.is_approved = False
            
            song.save()
            messages.success(request, "Your song has been uploaded successfully and is pending review!")
            return redirect('my_uploads')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SongUploadForm()
    
    # Get all genres to pass to template
    genres = Genre.objects.all()
    
    context = {
        'form': form,
        'genres': genres,
    }
    return render(request, 'upload_music.html', context)


@login_required
def my_uploads(request):
    """Artist's uploaded songs"""
    # Check if user is an artist
    if not hasattr(request.user, 'userprofile') or not request.user.userprofile.is_artist:
        messages.error(request, "You need to be an artist to view uploads.")
        return redirect('discover')
    
    try:
        artist_profile = Artist.objects.get(user=request.user)
        songs = Song.objects.filter(artist=artist_profile).order_by('-upload_date')
    except Artist.DoesNotExist:
        messages.error(request, "Artist profile not found.")
        songs = []
    
    context = {
        'songs': songs,
    }
    return render(request, 'my_uploads.html', context)


# ===== SONG ACTIONS (API ENDPOINTS) =====
@csrf_exempt
def play_song(request, song_id):
    """Play song and increment play count"""
    song = get_object_or_404(Song, id=song_id)
    
    # Increment play count
    song.increment_plays()
    
    # Record play in SongPlay model
    SongPlay.objects.create(
        song=song,
        user=request.user if request.user.is_authenticated else None,
        ip_address=get_client_ip(request)
    )
    
    return JsonResponse({
        'id': song.id,
        'title': song.title,
        'artist': song.artist.name,
        'cover': song.cover_image.url if song.cover_image else '/static/images/default-cover.jpg',
        'audio': song.audio_file.url,
        'duration': song.duration,
        'plays': song.plays
    })


@login_required
def like_song(request, song_id):
    """Like/unlike a song"""
    song = get_object_or_404(Song, id=song_id)
    user_profile = UserProfile.objects.get(user=request.user)
    
    if song in user_profile.liked_songs.all():
        user_profile.liked_songs.remove(song)
        liked = False
    else:
        user_profile.liked_songs.add(song)
        liked = True
    
    return JsonResponse({'liked': liked})


@login_required
def download_song(request, song_id):
    """Download song and increment download count"""
    song = get_object_or_404(Song, id=song_id)
    
    # Increment download count
    song.increment_downloads()
    
    # Record download in SongDownload model
    SongDownload.objects.create(
        song=song,
        user=request.user,
        ip_address=get_client_ip(request)
    )
    
    # Serve the file for download
    file_path = song.audio_file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="audio/mpeg")
            response['Content-Disposition'] = f'attachment; filename="{song.title} - {song.artist.name}.mp3"'
            return response
    else:
        return JsonResponse({'error': 'File not found'}, status=404)


@csrf_exempt
@login_required
def increment_play_count(request, song_id):
    """API endpoint to increment play count"""
    if request.method == 'POST':
        song = get_object_or_404(Song, id=song_id)
        song.plays += 1
        song.save()
        
        return JsonResponse({
            'success': True,
            'new_play_count': song.plays
        })
    
    return JsonResponse({'success': False})


@csrf_exempt
@login_required
def increment_download_count(request, song_id):
    """API endpoint to increment download count"""
    if request.method == 'POST':
        song = get_object_or_404(Song, id=song_id)
        song.downloads += 1
        song.save()
        
        return JsonResponse({
            'success': True,
            'new_download_count': song.downloads
        })
    
    return JsonResponse({'success': False})


@csrf_exempt
@login_required
def follow_artist(request, artist_id):
    """API endpoint to follow/unfollow an artist"""
    if request.method == 'POST':
        artist = get_object_or_404(Artist, id=artist_id)
        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            artist=artist
        )
        
        if not created:
            follow.delete()
        
        return JsonResponse({
            'followed': created,
            'followers_count': artist.followers.count()
        })
    
    return JsonResponse({'success': False})


# ===== ANALYTICS VIEWS =====
@login_required
def song_analytics(request, song_id):
    """Song analytics for artist"""
    song = get_object_or_404(Song, id=song_id)
    
    # Check if user owns the song
    if not request.user.userprofile.is_artist or song.artist.user != request.user:
        messages.error(request, "You don't have permission to view these analytics.")
        return redirect('my_uploads')
    
    # Get play history (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_plays = SongPlay.objects.filter(song=song, played_at__gte=thirty_days_ago)
    
    # Get download history
    recent_downloads = SongDownload.objects.filter(song=song, downloaded_at__gte=thirty_days_ago)
    
    context = {
        'song': song,
        'recent_plays': recent_plays,
        'recent_downloads': recent_downloads,
        'total_plays': song.plays,
        'total_downloads': song.downloads,
    }
    return render(request, 'analytics/song_analytics.html', context)


@login_required
def top_songs(request):
    """Top songs analytics"""
    # Get top played songs
    top_played = Song.objects.filter(is_approved=True).order_by('-plays')[:10]
    
    # Get top downloaded songs
    top_downloaded = Song.objects.filter(is_approved=True).order_by('-downloads')[:10]
    
    context = {
        'top_played': top_played,
        'top_downloaded': top_downloaded,
    }
    return render(request, 'analytics/top_songs.html', context)


def get_song_stats(request, song_id):
    """Get current song statistics"""
    song = get_object_or_404(Song, id=song_id)
    return JsonResponse({
        'plays': song.plays,
        'downloads': song.downloads
    })


# ===== PLAYLIST API VIEWS =====
@csrf_exempt
@login_required
def add_to_playlist(request, song_id):
    """Add song to playlist"""
    if request.method == 'POST':
        song = get_object_or_404(Song, id=song_id)
        playlist_id = request.POST.get('playlist_id')
        
        if playlist_id:
            playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
            playlist.songs.add(song)
            return JsonResponse({'success': True})
        
    return JsonResponse({'success': False})


@login_required
def remove_from_playlist(request, playlist_id, song_id):
    """Remove song from playlist"""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    song = get_object_or_404(Song, id=song_id)
    
    playlist.songs.remove(song)
    messages.success(request, 'Song removed from playlist!')
    return redirect('playlist_detail', playlist_id=playlist_id)


@login_required
def delete_playlist(request, playlist_id):
    """Delete playlist"""
    playlist = get_object_or_404(Playlist, id=playlist_id, user=request.user)
    playlist.delete()
    messages.success(request, 'Playlist deleted!')
    return redirect('playlists')


# ===== ERROR HANDLERS =====
def handler404(request, exception):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)


# ===== PREMIUM SUBSCRIPTION VIEWS =====
def premium_pricing(request):
    """Premium pricing page"""
    plans = [
        {
            'name': 'Free',
            'price': 0,
            'period': 'forever',
            'description': 'Basic access to our music library',
            'features': [
                {'text': 'Access to all songs', 'included': True},
                {'text': 'Standard audio quality', 'included': True},
                {'text': 'Limited skips (5 per hour)', 'included': True},
                {'text': 'With occasional ads', 'included': True},
                {'text': 'Offline downloads', 'included': False},
                {'text': 'High quality audio', 'included': False},
                {'text': 'Unlimited skips', 'included': False},
                {'text': 'Ad-free experience', 'included': False},
                {'text': 'Early access to new releases', 'included': False},
                {'text': 'Exclusive content', 'included': False},
            ],
            'popular': False,
            'cta_text': 'Current Plan',
            'cta_disabled': True
        },
        {
            'name': 'Premium',
            'price': 4.99,
            'period': 'month',
            'description': 'Enhanced listening experience',
            'features': [
                {'text': 'Access to all songs', 'included': True},
                {'text': 'High quality audio (320kbps)', 'included': True},
                {'text': 'Unlimited skips', 'included': True},
                {'text': 'Ad-free experience', 'included': True},
                {'text': 'Offline downloads', 'included': True},
                {'text': 'Early access to new releases', 'included': True},
                {'text': 'Exclusive content', 'included': True},
                {'text': 'Priority support', 'included': True},
                {'text': 'Multiple device support', 'included': True},
                {'text': 'Custom playlists', 'included': True},
            ],
            'popular': True,
            'cta_text': 'Upgrade to Premium',
            'cta_disabled': False
        },
        {
            'name': 'Premium Plus',
            'price': 9.99,
            'period': 'month',
            'description': 'Ultimate music experience',
            'features': [
                {'text': 'Everything in Premium', 'included': True},
                {'text': 'Ultra HD audio (FLAC)', 'included': True},
                {'text': 'Exclusive artist content', 'included': True},
                {'text': 'Concert pre-sales', 'included': True},
                {'text': 'Artist meet & greets', 'included': True},
                {'text': 'Limited edition merch', 'included': True},
                {'text': 'Personalized concierge', 'included': True},
                {'text': 'Family plan (up to 6 users)', 'included': True},
                {'text': 'Lyrics integration', 'included': True},
                {'text': 'Music videos', 'included': True},
            ],
            'popular': False,
            'cta_text': 'Go Premium Plus',
            'cta_disabled': False
        }
    ]
    
    # Check if user already has premium
    user_has_premium = False
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            user_has_premium = user_profile.is_premium
        except UserProfile.DoesNotExist:
            pass
    
    context = {
        'plans': plans,
        'user_has_premium': user_has_premium,
        'title': 'Upgrade to Premium'
    }
    return render(request, 'premium/pricing.html', context)


@login_required
def process_payment(request, plan_type):
    """Process premium payment"""
    if plan_type not in ['premium', 'premium_plus']:
        messages.error(request, 'Invalid plan selected.')
        return redirect('premium_pricing')
    
    # Get plan details
    plan_details = {
        'premium': {'name': 'Premium', 'price': 4.99, 'duration': 30},
        'premium_plus': {'name': 'Premium Plus', 'price': 9.99, 'duration': 30}
    }
    
    plan = plan_details[plan_type]
    
    if request.method == 'POST':
        # In a real application, you would integrate with a payment gateway here
        # For now, we'll simulate successful payment
        
        try:
            # Update user profile
            user_profile = UserProfile.objects.get(user=request.user)
            user_profile.is_premium = True
            user_profile.premium_plan = plan_type
            user_profile.premium_since = timezone.now()
            user_profile.premium_expires = timezone.now() + timedelta(days=plan['duration'])
            user_profile.save()
            
            # Create payment record (you'd want a Payment model for this)
            # Payment.objects.create(...)
            
            messages.success(request, f'🎉 Welcome to {plan["name"]}! Your premium subscription is now active.')
            return redirect('premium_success')
            
        except Exception as e:
            messages.error(request, f'Payment failed: {str(e)}')
            return redirect('premium_pricing')
    
    context = {
        'plan': plan,
        'plan_type': plan_type,
    }
    return render(request, 'premium/payment.html', context)


@login_required
def premium_success(request):
    """Premium subscription success page"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        context = {
            'user_profile': user_profile,
            'plan_name': user_profile.get_premium_plan_display() if user_profile.premium_plan else 'Premium'
        }
        return render(request, 'premium/success.html', context)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def premium_features(request):
    """Showcase premium features"""
    features = [
        {
            'icon': 'fas fa-download',
            'title': 'Offline Downloads',
            'description': 'Download your favorite songs and listen offline without using data.'
        },
        {
            'icon': 'fas fa-volume-up',
            'title': 'High Quality Audio',
            'description': 'Experience crystal clear sound with 320kbps high quality audio streaming.'
        },
        {
            'icon': 'fas fa-bolt',
            'title': 'Ad-Free Listening',
            'description': 'Enjoy uninterrupted music without any advertisements.'
        },
        {
            'icon': 'fas fa-infinity',
            'title': 'Unlimited Skips',
            'description': 'Skip as many songs as you want, whenever you want.'
        },
        {
            'icon': 'fas fa-rocket',
            'title': 'Early Access',
            'description': 'Get early access to new releases from your favorite artists.'
        },
        {
            'icon': 'fas fa-headphones',
            'title': 'Exclusive Content',
            'description': 'Access exclusive tracks, live sessions, and behind-the-scenes content.'
        }
    ]
    
    user_has_premium = False
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            user_has_premium = user_profile.is_premium
        except UserProfile.DoesNotExist:
            pass
    
    context = {
        'features': features,
        'user_has_premium': user_has_premium
    }
    return render(request, 'premium/features.html', context)


@login_required
def profile_view(request):
    """User profile page"""
    user_profile = UserProfile.objects.get(user=request.user)
    
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
    return render(request, 'user/profile.html', context)

@login_required
def settings_view(request):
    """User settings page"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        # Handle settings updates
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        bio = request.POST.get('bio')
        location = request.POST.get('location')
        website = request.POST.get('website')
        
        # Update user
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()
        
        # Update profile
        user_profile.bio = bio
        user_profile.location = location
        user_profile.website = website
        user_profile.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('settings')
    
    context = {
        'user_profile': user_profile,
    }
    return render(request, 'user/settings.html', context)

def help_center(request):
    """Help center page"""
    faqs = [
        {
            'question': 'How do I upload my music?',
            'answer': 'Go to your artist dashboard and click "Upload Music". You need to be verified as an artist to upload songs.'
        },
        {
            'question': 'Can I download songs for offline listening?',
            'answer': 'Yes! Offline downloading is available for Premium and Premium Plus subscribers.'
        },
        {
            'question': 'How do I create a playlist?',
            'answer': 'Go to your Library page and click "Create Playlist". You can add songs from the discover page or search results.'
        },
        {
            'question': 'What audio formats are supported?',
            'answer': 'We support MP3, WAV, and OGG formats for audio files.'
        },
        {
            'question': 'How do I become a verified artist?',
            'answer': 'Contact our support team with your artist information and portfolio for verification.'
        },
        {
            'question': 'Can I cancel my premium subscription?',
            'answer': 'Yes, you can cancel anytime from your account settings. Your premium features will remain active until the end of your billing period.'
        }
    ]
    
    context = {
        'faqs': faqs,
    }
    return render(request, 'help/help_center.html', context)


import requests
import json
from django.conf import settings

# ===== MOBILE MONEY PAYMENT VIEWS =====
@login_required
def process_payment(request, plan_type):
    """Process premium payment with mobile money options"""
    if plan_type not in ['premium', 'premium_plus']:
        messages.error(request, 'Invalid plan selected.')
        return redirect('premium_pricing')
    
    # Get plan details
    plan_details = {
        'premium': {'name': 'Premium', 'price': 4.99, 'duration': 30},
        'premium_plus': {'name': 'Premium Plus', 'price': 9.99, 'duration': 30}
    }
    
    plan = plan_details[plan_type]
    
    if request.method == 'POST':
        # Get payment method and phone number
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number')
        network = request.POST.get('network')
        
        if not phone_number:
            messages.error(request, 'Please enter your phone number.')
            return redirect('process_payment', plan_type=plan_type)
        
        try:
            # Process mobile money payment
            if payment_method in ['mtn', 'airtel']:
                result = process_mobile_money_payment(
                    request.user,
                    plan_type,
                    phone_number,
                    network,
                    plan['price']
                )
                
                if result['success']:
                    messages.success(request, f'Payment initiated! {result["message"]}')
                    return redirect('payment_pending', transaction_id=result['transaction_id'])
                else:
                    messages.error(request, f'Payment failed: {result["message"]}')
                    return redirect('process_payment', plan_type=plan_type)
            
            else:
                messages.error(request, 'Invalid payment method selected.')
                return redirect('process_payment', plan_type=plan_type)
                
        except Exception as e:
            messages.error(request, f'Payment error: {str(e)}')
            return redirect('process_payment', plan_type=plan_type)
    
    context = {
        'plan': plan,
        'plan_type': plan_type,
    }
    return render(request, 'premium/payment.html', context)

@login_required
def payment_pending(request, transaction_id):
    """Show payment pending page while waiting for mobile money confirmation"""
    context = {
        'transaction_id': transaction_id,
    }
    return render(request, 'premium/payment_pending.html', context)

@login_required
def check_payment_status(request, transaction_id):
    """API endpoint to check payment status"""
    # In a real implementation, you would check with your payment provider
    # For demo purposes, we'll simulate successful payment after 30 seconds
    
    # Check if payment was completed (you'd integrate with actual API here)
    payment_completed = check_mobile_money_payment_status(transaction_id)
    
    if payment_completed:
        # Update user to premium
        user_profile = UserProfile.objects.get(user=request.user)
        user_profile.upgrade_to_premium('premium', 30)  # Default to premium for demo
        
        return JsonResponse({
            'status': 'completed',
            'message': 'Payment completed successfully!'
        })
    else:
        return JsonResponse({
            'status': 'pending',
            'message': 'Waiting for payment confirmation...'
        })

# ===== MOBILE MONEY SERVICE FUNCTIONS =====
class MobileMoneyService:
    """Service class to handle mobile money payments"""
    
    @staticmethod
    def initiate_mtn_payment(phone_number, amount, reference):
        """
        Initiate MTN Mobile Money payment
        Note: This is a simulation. In production, use actual MTN API
        """
        try:
            # Simulate API call to MTN Mobile Money
            # In production, you would use:
            # response = requests.post(
            #     'https://api.mtn.com/v1/mobilemoney/payments',
            #     headers={
            #         'Authorization': f'Bearer {settings.MTN_API_KEY}',
            #         'Content-Type': 'application/json'
            #     },
            #     json={
            #         'amount': str(amount),
            #         'currency': 'USD',
            #         'externalId': reference,
            #         'payer': {
            #             'partyIdType': 'MSISDN',
            #             'partyId': phone_number
            #         },
            #         'payerMessage': 'Sangabiz Premium Subscription',
            #         'payeeNote': 'Thank you for subscribing to Sangabiz Premium'
            #     }
            # )
            
            # Simulate successful API response
            return {
                'success': True,
                'transaction_id': f'MTN_{reference}',
                'message': 'MTN Mobile Money payment initiated. Please check your phone to complete the transaction.',
                'provider_reference': f'MTNREF{reference}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'MTN payment failed: {str(e)}'
            }
    
    @staticmethod
    def initiate_airtel_payment(phone_number, amount, reference):
        """
        Initiate Airtel Money payment
        Note: This is a simulation. In production, use actual Airtel API
        """
        try:
            # Simulate API call to Airtel Money
            # In production, you would use:
            # response = requests.post(
            #     'https://openapi.airtel.africa/merchant/v1/payments/',
            #     headers={
            #         'Authorization': f'Bearer {settings.AIRTEL_API_KEY}',
            #         'Content-Type': 'application/json',
            #         'X-Country': 'UG',  # Adjust country code as needed
            #         'X-Currency': 'USD'
            #     },
            #     json={
            #         'reference': reference,
            #         'subscriber': {
            #             'country': 'UG',
            #             'currency': 'USD',
            #             'msisdn': phone_number
            #         },
            #         'transaction': {
            #             'amount': amount,
            #             'country': 'UG',
            #             'currency': 'USD',
            #             'id': reference
            #         }
            #     }
            # )
            
            # Simulate successful API response
            return {
                'success': True,
                'transaction_id': f'AIRTEL_{reference}',
                'message': 'Airtel Money payment initiated. Please check your phone to complete the transaction.',
                'provider_reference': f'AIRTELREF{reference}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Airtel payment failed: {str(e)}'
            }
    
    @staticmethod
    def check_payment_status(transaction_id):
        """
        Check mobile money payment status
        In production, this would query the provider's API
        """
        # Simulate checking payment status
        # For demo, assume payment is completed after a short delay
        import time
        time.sleep(5)  # Simulate API delay
        
        # In production, you would:
        # 1. Query the provider's API with transaction_id
        # 2. Return actual status
        
        return {
            'status': 'completed',  # or 'pending', 'failed'
            'message': 'Payment completed successfully'
        }

def process_mobile_money_payment(user, plan_type, phone_number, network, amount):
    """Process mobile money payment"""
    # Generate unique reference
    import uuid
    reference = str(uuid.uuid4())[:8].upper()
    
    # Validate phone number format
    if not validate_phone_number(phone_number, network):
        return {
            'success': False,
            'message': 'Invalid phone number format for the selected network.'
        }
    
    # Process based on network
    if network == 'mtn':
        result = MobileMoneyService.initiate_mtn_payment(phone_number, amount, reference)
    elif network == 'airtel':
        result = MobileMoneyService.initiate_airtel_payment(phone_number, amount, reference)
    else:
        return {
            'success': False,
            'message': 'Unsupported mobile network.'
        }
    
    # Store transaction in database if successful
    if result['success']:
        Payment.objects.create(
            user=user,
            plan=SubscriptionPlan.objects.filter(plan_type=plan_type).first(),
            amount=amount,
            status='pending',
            transaction_id=result['transaction_id'],
            provider_reference=result.get('provider_reference'),
            payment_method=network
        )
    
    return result

def validate_phone_number(phone_number, network):
    """Validate phone number format for different networks"""
    # Remove any non-digit characters
    clean_number = ''.join(filter(str.isdigit, phone_number))
    
    if network == 'mtn':
        # MTN Uganda format: 2567XXXXXXXX, 077XXXXXXX
        return len(clean_number) in [10, 12] and clean_number.startswith(('2567', '077'))
    elif network == 'airtel':
        # Airtel Uganda format: 2567XXXXXXXX, 075XXXXXXX, 070XXXXXXX
        return len(clean_number) in [10, 12] and clean_number.startswith(('2567', '075', '070'))
    
    return False

def check_mobile_money_payment_status(transaction_id):
    """Check if mobile money payment was completed"""
    try:
        # In production, this would query the actual provider API
        result = MobileMoneyService.check_payment_status(transaction_id)
        
        if result['status'] == 'completed':
            # Update payment status in database
            payment = Payment.objects.get(transaction_id=transaction_id)
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()
            
            return True
        return False
        
    except Payment.DoesNotExist:
        return False