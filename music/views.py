# music/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.views.decorators.http import require_POST, require_http_methods
from django.db.models import Q, Count, Sum, Avg
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models.functions import Coalesce
from datetime import timedelta
import json
import os

from .models import Song, Genre, SongPlay, SongDownload, NewsArticle, Chart, ChartEntry, YouTubeVideo, NewsView
from .models import NewsComment, NewsSubscription, NewsLike, CommentLike
from .forms import NewsCommentForm, NewsSubscriptionForm
from artists.models import Artist, Follow
# Import for image and audio processing
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Pillow not installed - cover art branding disabled")

try:
    import mutagen
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, APIC, COMM
    from mutagen.mp3 import MP3
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    print("Mutagen not installed - metadata branding disabled")

# Utility function to get client IP
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def create_branded_cover(song, output_path):
    """Create branded cover art with Sangabiz branding"""
    try:
        if not HAS_PIL:
            # Fallback without PIL
            if song.cover_image and os.path.exists(song.cover_image.path):
                shutil.copy2(song.cover_image.path, output_path)
            return
        
        # Create a new cover image
        width, height = 500, 500
        
        # Use original cover if available, otherwise create new
        if song.cover_image and os.path.exists(song.cover_image.path):
            image = Image.open(song.cover_image.path).convert('RGB')
            image = image.resize((width, height), Image.LANCZOS)
        else:
            # Create default background
            image = Image.new('RGB', (width, height), '#1DB954')  # Sangabiz green
        
        draw = ImageDraw.Draw(image)
        
        # Add text branding
        try:
            # Use default font (works on all systems)
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            
            # Song title
            title = song.title
            title_bbox = draw.textbbox((0, 0), title, font=font_large)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (width - title_width) // 2
            draw.text((title_x, height//2 - 30), title, fill='white', font=font_large)
            
            # Artist name
            artist = f"by {song.artist.name}"
            artist_bbox = draw.textbbox((0, 0), artist, font=font_small)
            artist_width = artist_bbox[2] - artist_bbox[0]
            artist_x = (width - artist_width) // 2
            draw.text((artist_x, height//2), artist, fill='#333333', font=font_small)
            
            # Sangabiz branding
            branding = "Downloaded from Sangabiz"
            branding_bbox = draw.textbbox((0, 0), branding, font=font_small)
            branding_width = branding_bbox[2] - branding_bbox[0]
            branding_x = (width - branding_width) // 2
            draw.text((branding_x, height - 40), branding, fill='#666666', font=font_small)
            
        except Exception as e:
            print(f"Text rendering error: {e}")
        
        # Save the branded cover
        image.save(output_path, 'JPEG', quality=90)
        
    except Exception as e:
        print(f"Cover creation error: {e}")
        # Final fallback
        if song.cover_image and os.path.exists(song.cover_image.path):
            shutil.copy2(song.cover_image.path, output_path)

def add_branded_metadata(audio_path, song, cover_path=None):
    """Add Sangabiz branding to audio file metadata"""
    try:
        if not HAS_MUTAGEN:
            return
        
        # Load the audio file
        audio = MP3(audio_path, ID3=ID3)
        
        # Ensure ID3 tag exists
        try:
            audio.add_tags()
        except mutagen.id3.error:
            pass  # Tags already exist
        
        # Set basic metadata
        audio.tags.add(TIT2(encoding=3, text=song.title))
        audio.tags.add(TPE1(encoding=3, text=song.artist.name))
        audio.tags.add(TALB(encoding=3, text="Sangabiz Music"))
        
        if song.genre:
            audio.tags.add(TCON(encoding=3, text=song.genre.name))
        
        # Add comment with branding
        comment_text = "Downloaded from Sangabiz - Your Favorite Music Platform"
        audio.tags.add(COMM(encoding=3, text=comment_text))
        
        # Add cover art if available
        if cover_path and os.path.exists(cover_path):
            try:
                with open(cover_path, 'rb') as cover_file:
                    cover_data = cover_file.read()
                
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=cover_data
                    )
                )
            except Exception as e:
                print(f"Cover art embedding error: {e}")
        
        # Save metadata
        audio.save()
        
    except Exception as e:
        print(f"Metadata error: {e}")

def home(request):
    """Home page with featured content"""
    # Get featured songs
    featured_songs = Song.objects.filter(
        is_approved=True
    ).select_related('artist', 'genre').order_by('-plays', '-upload_date')[:12]
    
    # Most played songs
    most_played = Song.objects.filter(is_approved=True).select_related('artist', 'genre').order_by('-plays')[:10]
    
    # Most downloaded songs
    most_downloaded = Song.objects.filter(is_approved=True).select_related('artist', 'genre').order_by('-downloads')[:10]
    
    # New artists
    new_artists = Artist.objects.filter(is_verified=True).annotate(
        total_songs_count=Count('songs', filter=Q(songs__is_approved=True)),
        total_plays_count=Coalesce(Sum('songs__plays', filter=Q(songs__is_approved=True)), 0),
        total_downloads_count=Coalesce(Sum('songs__downloads', filter=Q(songs__is_approved=True)), 0),
        followers_count=Count('followers')
    ).order_by('-created_at')[:8]
    
    # Trending artists
    seven_days_ago = timezone.now() - timedelta(days=7)
    trending_artists = Artist.objects.filter(is_verified=True).annotate(
        weekly_plays=Coalesce(Sum(
            'songs__plays',
            filter=Q(songs__upload_date__gte=seven_days_ago, songs__is_approved=True)
        ), 0),
        weekly_downloads=Coalesce(Sum(
            'songs__downloads',
            filter=Q(songs__upload_date__gte=seven_days_ago, songs__is_approved=True)
        ), 0),
        weekly_followers=Count(
            'followers',
            filter=Q(followers__followed_at__gte=seven_days_ago)
        )
    ).filter(
        Q(weekly_plays__gt=0) | Q(weekly_downloads__gt=0) | Q(weekly_followers__gt=0)
    ).order_by('-weekly_plays', '-weekly_downloads', '-weekly_followers')[:8]
    
    # Genres with song counts
    genres = Genre.objects.annotate(
        song_count=Count('songs', filter=Q(songs__is_approved=True)),
        total_plays=Coalesce(Sum('songs__plays', filter=Q(songs__is_approved=True)), 0),
        total_downloads=Coalesce(Sum('songs__downloads', filter=Q(songs__is_approved=True)), 0)
    ).filter(song_count__gt=0).order_by('-song_count')[:12]
    
    # Get stats
    total_songs = Song.objects.filter(is_approved=True).count()
    total_plays = SongPlay.objects.count()
    total_downloads = SongDownload.objects.count()
    total_artists = Artist.objects.filter(is_verified=True).count()
    
    # Get recent activity
    recent_activity = []
    
    if request.user.is_authenticated:
        recent_plays = SongPlay.objects.filter(
            user=request.user
        ).select_related('song', 'song__artist').order_by('-played_at')[:10]
        recent_activity.extend([{
            'type': 'play',
            'item': play.song,
            'time': play.played_at,
            'user': play.user
        } for play in recent_plays])
    
    recent_uploads = Song.objects.filter(
        is_approved=True
    ).select_related('artist', 'genre').order_by('-upload_date')[:5]
    recent_activity.extend([{
        'type': 'upload',
        'item': song,
        'time': song.upload_date,
        'user': song.artist.user
    } for song in recent_uploads])
    
    recent_activity.sort(key=lambda x: x['time'], reverse=True)
    recent_activity = recent_activity[:15]
    
    # Get additional content
    try:
        featured_videos = YouTubeVideo.objects.filter(
            is_active=True, 
            is_featured=True
        ).order_by('-added_date')[:6]
        latest_news = NewsArticle.objects.filter(
            is_published=True
        ).order_by('-published_date')[:3]
        featured_charts = Chart.objects.filter(
            is_active=True
        ).prefetch_related('entries__song')[:2]
    except Exception as e:
        print(f"Error loading additional content: {e}")
        featured_videos = []
        latest_news = []
        featured_charts = []
    
    context = {
        'featured_songs': featured_songs,
        'most_played': most_played,
        'most_downloaded': most_downloaded,
        'new_artists': new_artists,
        'trending_artists': trending_artists,
        'genres': genres,
        'recent_activity': recent_activity,
        'total_songs': total_songs,
        'total_plays': total_plays,
        'total_downloads': total_downloads,
        'total_artists': total_artists,
        'featured_videos': featured_videos,
        'latest_news': latest_news,
        'featured_charts': featured_charts,
    }
    return render(request, 'music/home.html', context)

def discover(request):
    """Discover page with all songs and enhanced content"""
    songs_list = Song.objects.filter(is_approved=True).select_related('artist', 'genre').order_by('-upload_date')
    genres = Genre.objects.all()
    
    # Filtering
    genre_filter = request.GET.get('genre')
    if genre_filter:
        songs_list = songs_list.filter(genre_id=genre_filter)
    
    search_query = request.GET.get('q')
    if search_query:
        songs_list = songs_list.filter(
            Q(title__icontains=search_query) |
            Q(artist__name__icontains=search_query) |
            Q(genre__name__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(songs_list, 20)
    page_number = request.GET.get('page')
    songs = paginator.get_page(page_number)
    
    # Get trending artists
    seven_days_ago = timezone.now() - timedelta(days=7)
    discover_trending_artists = Artist.objects.filter(is_verified=True).annotate(
        recent_followers=Count(
            'followers', 
            filter=Q(followers__followed_at__gte=seven_days_ago)
        ),
        recent_plays=Coalesce(Sum(
            'songs__plays',
            filter=Q(songs__upload_date__gte=seven_days_ago, songs__is_approved=True)
        ), 0),
        recent_downloads=Coalesce(Sum(
            'songs__downloads',
            filter=Q(songs__upload_date__gte=seven_days_ago, songs__is_approved=True)
        ), 0)
    ).filter(
        Q(recent_followers__gt=0) | Q(recent_plays__gt=0) | Q(recent_downloads__gt=0)
    ).order_by('-recent_plays', '-recent_downloads', '-recent_followers')[:6]
    
    # Get additional content
    try:
        trending_videos = YouTubeVideo.objects.filter(is_active=True).order_by('-added_date')[:8]
        discover_news = NewsArticle.objects.filter(is_published=True).order_by('-published_date')[:4]
    except Exception as e:
        trending_videos = []
        discover_news = []
    
    context = {
        'songs': songs,
        'genres': genres,
        'selected_genre': genre_filter,
        'search_query': search_query or '',
        'trending_artists': discover_trending_artists,
        'trending_videos': trending_videos,
        'discover_news': discover_news,
    }
    return render(request, 'music/discover.html', context)

def song_detail(request, song_id):
    """Individual song detail page"""
    song = get_object_or_404(
        Song.objects.select_related('artist', 'genre'), 
        id=song_id, 
        is_approved=True
    )
    
    can_access = song.can_be_accessed_by(request.user)
    
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user, 
            artist=song.artist
        ).exists()
    
    similar_songs = Song.objects.filter(
        genre=song.genre,
        is_approved=True
    ).exclude(id=song.id).select_related('artist', 'genre').order_by('-plays')[:6]
    
    play_stats = SongPlay.objects.filter(song=song).aggregate(
        total_plays=Count('id'),
        avg_duration=Avg('duration_played')
    )
    
    download_stats = SongDownload.objects.filter(song=song).aggregate(
        total_downloads=Count('id')
    )
    
    recent_plays = SongPlay.objects.filter(song=song).select_related('user').order_by('-played_at')[:10]
    
    context = {
        'song': song,
        'similar_songs': similar_songs,
        'can_access': can_access,
        'is_following': is_following,
        'play_stats': play_stats,
        'download_stats': download_stats,
        'recent_plays': recent_plays,
    }
    return render(request, 'music/song_detail.html', context)

def search(request):
    """Search functionality"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('discover')
    
    # Search songs
    songs = Song.objects.filter(
        Q(title__icontains=query) | 
        Q(artist__name__icontains=query) |
        Q(genre__name__icontains=query),
        is_approved=True
    ).select_related('artist', 'genre').distinct().order_by('-plays')[:50]
    
    # Get related artists
    related_artists = Artist.objects.filter(
        Q(name__icontains=query) |
        Q(bio__icontains=query)
    ).distinct().annotate(
        song_count=Count('songs', filter=Q(songs__is_approved=True)),
        total_plays=Coalesce(Sum('songs__plays', filter=Q(songs__is_approved=True)), 0),
        total_downloads=Coalesce(Sum('songs__downloads', filter=Q(songs__is_approved=True)), 0),
        followers_count=Count('followers')
    ).filter(song_count__gt=0).order_by('-song_count')[:10]
    
    # Add follow status
    for artist in related_artists:
        artist.is_following = False
        if request.user.is_authenticated:
            artist.is_following = Follow.objects.filter(
                follower=request.user, 
                artist=artist
            ).exists()
    
    # Get related genres
    related_genres = Genre.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query)
    ).distinct().annotate(
        song_count=Count('songs', filter=Q(songs__is_approved=True)),
        total_plays=Coalesce(Sum('songs__plays', filter=Q(songs__is_approved=True)), 0),
        total_downloads=Coalesce(Sum('songs__downloads', filter=Q(songs__is_approved=True)), 0)
    ).filter(song_count__gt=0).order_by('-song_count')[:8]
    
    context = {
        'songs': songs,
        'related_artists': related_artists,
        'related_genres': related_genres,
        'query': query,
        'results_count': len(songs) + len(related_artists) + len(related_genres),
    }
    return render(request, 'music/search.html', context)

def genres(request):
    """All genres page"""
    genres = Genre.objects.annotate(
        song_count=Count('songs', filter=Q(songs__is_approved=True)),
        total_plays=Coalesce(Sum('songs__plays'), 0),
        total_downloads=Coalesce(Sum('songs__downloads'), 0)
    ).filter(song_count__gt=0).order_by('name')
    
    context = {
        'genres': genres,
    }
    return render(request, 'music/genres.html', context)

def genre_songs(request, genre_id):
    """Songs by specific genre"""
    genre = get_object_or_404(Genre, id=genre_id)
    songs = Song.objects.filter(
        genre=genre, 
        is_approved=True
    ).select_related('artist', 'genre').order_by('-upload_date')
    
    genre_stats = songs.aggregate(
        total_songs=Count('id'),
        total_plays=Sum('plays'),
        total_downloads=Sum('downloads')
    )
    
    top_artists = Artist.objects.filter(
        songs__genre=genre,
        songs__is_approved=True
    ).annotate(
        genre_songs_count=Count('songs', filter=Q(songs__genre=genre, songs__is_approved=True)),
        genre_plays=Sum('songs__plays', filter=Q(songs__genre=genre)),
        genre_downloads=Sum('songs__downloads', filter=Q(songs__genre=genre))
    ).distinct().order_by('-genre_plays', '-genre_downloads')[:8]
    
    context = {
        'genre': genre,
        'songs': songs,
        'genre_stats': genre_stats,
        'top_artists': top_artists,
    }
    return render(request, 'music/genre_songs.html', context)

@login_required
def play_song(request, song_id):
    """Play song and increment play count"""
    song = get_object_or_404(Song, id=song_id)
    
    if not song.can_be_accessed_by(request.user):
        return JsonResponse({
            'error': 'Premium content requires subscription',
            'can_preview': song.preview_duration > 0,
            'preview_duration': song.preview_duration
        }, status=403)
    
    # Increment play count on the song model
    song.increment_plays()
    
    # Create play record for detailed tracking
    play = SongPlay.objects.create(
        song=song,
        user=request.user,
        ip_address=get_client_ip(request),
        duration_played=0,
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        audio_quality='high' if request.user.userprofile.is_premium else 'standard'
    )
    
    return JsonResponse({
        'id': song.id,
        'title': song.title,
        'artist': song.artist.name,
        'artist_id': song.artist.id,
        'cover': song.cover_image.url if song.cover_image else '/static/images/default-cover.jpg',
        'audio': song.audio_file.url,
        'duration': song.duration,
        'plays': song.plays,
        'downloads': song.downloads,
        'is_premium': song.is_premium_only,
        'play_id': play.id
    })

@login_required
def download_song(request, song_id):
    """Download song with Sangabiz branding"""
    song = get_object_or_404(Song, id=song_id, is_approved=True)
    
    if not song.can_be_accessed_by(request.user):
        messages.error(request, 'Premium content requires subscription')
        return redirect('song_detail', song_id=song_id)
    
    try:
        # Check if file exists
        if not song.audio_file or not os.path.exists(song.audio_file.path):
            raise FileNotFoundError("Audio file not found")
        
        file_path = song.audio_file.path
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, f"branded_{os.path.basename(file_path)}")
            
            # Copy original file
            shutil.copy2(file_path, output_path)
            
            # Create branded cover
            branded_cover_path = os.path.join(temp_dir, "branded_cover.jpg")
            create_branded_cover(song, branded_cover_path)
            
            # Add branded metadata
            add_branded_metadata(output_path, song, branded_cover_path)
            
            # Increment download count on the song model
            song.increment_downloads()
            
            # Record download for detailed tracking
            SongDownload.objects.create(
                song=song,
                user=request.user,
                ip_address=get_client_ip(request),
                file_size=os.path.getsize(output_path)
            )
            
            # Serve the branded file
            filename = f"Sangabiz - {song.title} - {song.artist.name}.mp3"
            response = FileResponse(
                open(output_path, 'rb'),
                content_type='audio/mpeg'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = os.path.getsize(output_path)
            
            return response
            
    except FileNotFoundError as e:
        messages.error(request, 'Audio file not found on server')
        return redirect('song_detail', song_id=song_id)
    except Exception as e:
        print(f"Download error: {str(e)}")
        messages.error(request, f'Download failed: {str(e)}')
        return redirect('song_detail', song_id=song_id)

def top_songs(request):
    """Top songs page with various rankings"""
    most_played = Song.objects.filter(is_approved=True).select_related('artist', 'genre').order_by('-plays')[:20]
    most_downloaded = Song.objects.filter(is_approved=True).select_related('artist', 'genre').order_by('-downloads')[:20]
    
    seven_days_ago = timezone.now() - timedelta(days=7)
    trending = Song.objects.filter(
        is_approved=True,
        play_history__played_at__gte=seven_days_ago
    ).annotate(
        recent_plays=Count('play_history'),
        recent_downloads=Count('download_history', filter=Q(download_history__downloaded_at__gte=seven_days_ago))
    ).select_related('artist', 'genre').order_by('-recent_plays', '-recent_downloads')[:20]
    
    trending_artists = Artist.objects.filter(is_verified=True).annotate(
        recent_followers=Count(
            'followers', 
            filter=Q(followers__followed_at__gte=seven_days_ago)
        ),
        recent_plays=Coalesce(Sum(
            'songs__plays',
            filter=Q(songs__upload_date__gte=seven_days_ago, songs__is_approved=True)
        ), 0),
        recent_downloads=Coalesce(Sum(
            'songs__downloads',
            filter=Q(songs__upload_date__gte=seven_days_ago, songs__is_approved=True)
        ), 0)
    ).filter(
        Q(recent_followers__gt=0) | Q(recent_plays__gt=0) | Q(recent_downloads__gt=0)
    ).order_by('-recent_plays', '-recent_downloads', '-recent_followers')[:5]
    
    context = {
        'most_played': most_played,
        'most_downloaded': most_downloaded,
        'trending': trending,
        'trending_artists': trending_artists,
    }
    return render(request, 'music/top_songs.html', context)

@login_required
def update_play_duration(request, song_id):
    """Update play duration when playback ends"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            duration_played = data.get('duration_played', 0)
            play_id = data.get('play_id')
            
            if play_id:
                play = SongPlay.objects.get(id=play_id, user=request.user)
                play.duration_played = duration_played
                play.save()
            else:
                play = SongPlay.objects.filter(
                    song_id=song_id,
                    user=request.user
                ).order_by('-played_at').first()
                if play:
                    play.duration_played = duration_played
                    play.save()
                    
            return JsonResponse({'success': True})
            
        except (json.JSONDecodeError, SongPlay.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'Invalid data'})
    
    return JsonResponse({'success': False, 'error': 'Invalid method'})

@require_POST
@login_required
def follow_artist_from_music(request, artist_id):
    """API endpoint to follow/unfollow an artist"""
    try:
        artist = get_object_or_404(Artist, id=artist_id, is_verified=True)
        
        if hasattr(request.user, 'artist_profile') and request.user.artist_profile == artist:
            return JsonResponse({
                'success': False,
                'error': 'You cannot follow yourself'
            }, status=400)
        
        follow_exists = Follow.objects.filter(
            follower=request.user, 
            artist=artist
        ).exists()
        
        if follow_exists:
            Follow.objects.filter(follower=request.user, artist=artist).delete()
            followed = False
            message = f"You unfollowed {artist.name}"
        else:
            Follow.objects.create(follower=request.user, artist=artist)
            followed = True
            message = f"You are now following {artist.name}"
        
        followers_count = artist.followers.count()
        
        return JsonResponse({
            'success': True,
            'followed': followed,
            'followers_count': followers_count,
            'message': message
        })
        
    except Artist.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Artist not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'}, status=500)
    
# music/views.py (update your news views)

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

@require_POST
@login_required
def like_news_article(request, article_id):
    """Like/unlike a news article"""
    article = get_object_or_404(NewsArticle, id=article_id, is_published=True)
    
    if article.user_has_liked(request.user):
        # Unlike the article
        NewsLike.objects.filter(user=request.user, article=article).delete()
        liked = False
        message = "Article unliked"
    else:
        # Like the article
        NewsLike.objects.get_or_create(user=request.user, article=article)
        liked = True
        message = "Article liked"
    
    like_count = article.get_like_count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count,
            'message': message
        })
    
    messages.success(request, message)
    return redirect('news_detail', slug=article.slug)

@require_POST
@login_required
def like_news_comment(request, comment_id):
    """Like/unlike a news comment"""
    comment = get_object_or_404(NewsComment, id=comment_id, is_approved=True)
    
    if comment.user_has_liked(request.user):
        # Unlike the comment
        CommentLike.objects.filter(user=request.user, comment=comment).delete()
        liked = False
        message = "Comment unliked"
    else:
        # Like the comment
        CommentLike.objects.get_or_create(user=request.user, comment=comment)
        liked = True
        message = "Comment liked"
    
    like_count = comment.get_like_count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count,
            'message': message
        })
    
    return redirect('news_detail', slug=comment.article.slug)

@require_http_methods(["GET", "POST"])
def subscribe_news(request):
    """Subscribe to news newsletter"""
    if request.method == 'POST':
        form = NewsSubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            
            # If user is authenticated, link to their account
            if request.user.is_authenticated:
                subscription.user = request.user
            
            subscription.save()
            
            # Send welcome email
            send_subscription_welcome_email(subscription.email)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Successfully subscribed to our newsletter!'
                })
            
            messages.success(request, 'Successfully subscribed to our newsletter!')
            return redirect('news')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = NewsSubscriptionForm()
    
    return render(request, 'music/news_subscribe.html', {'form': form})

@require_POST
@login_required
def unsubscribe_news(request):
    """Unsubscribe from news newsletter"""
    if request.user.is_authenticated:
        # Unsubscribe by user
        subscriptions = NewsSubscription.objects.filter(user=request.user, is_active=True)
        for subscription in subscriptions:
            subscription.is_active = False
            subscription.save()
    else:
        # Handle email-based unsubscribe (you'd need to implement this)
        pass
    
    messages.success(request, 'You have been unsubscribed from our newsletter.')
    return redirect('news')

def send_subscription_welcome_email(email):
    """Send welcome email to new subscribers"""
    subject = 'Welcome to Sangabiz News!'
    message = render_to_string('emails/news_subscription_welcome.html', {
        'email': email
    })
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
        html_message=message
    )

# Update your existing news_detail_view
def news_detail_view(request, slug):
    """Individual news article detail page"""
    article = get_object_or_404(NewsArticle, slug=slug, is_published=True)
    
    article.increment_views()
    
    ip = get_client_ip(request)
    NewsView.objects.get_or_create(
        article=article,
        ip_address=ip,
        defaults={'user': request.user if request.user.is_authenticated else None}
    )
    
    # Handle comment submission
    if request.method == 'POST' and request.user.is_authenticated:
        if 'comment_submit' in request.POST:
            comment_form = NewsCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.article = article
                comment.user = request.user
                comment.save()
                messages.success(request, 'Your comment has been posted!')
                return redirect('news_detail', slug=slug)
        elif 'subscribe_submit' in request.POST:
            subscription_form = NewsSubscriptionForm(request.POST)
            if subscription_form.is_valid():
                subscription = subscription_form.save(commit=False)
                if request.user.is_authenticated:
                    subscription.user = request.user
                subscription.save()
                send_subscription_welcome_email(subscription.email)
                messages.success(request, 'Successfully subscribed to our newsletter!')
                return redirect('news_detail', slug=slug)
    else:
        comment_form = NewsCommentForm()
        subscription_form = NewsSubscriptionForm()
    
    # Check if user has liked the article
    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = article.user_has_liked(request.user)
    
    # Get comments with like status for current user
    comments = article.comments.filter(is_approved=True)
    for comment in comments:
        comment.user_has_liked = comment.user_has_liked(request.user)
    
    related_articles = NewsArticle.objects.filter(
        is_published=True,
        category=article.category
    ).exclude(id=article.id).order_by('-published_date')[:3]
    
    context = {
        'article': article,
        'related_articles': related_articles,
        'comments': comments,
        'comment_form': comment_form,
        'subscription_form': subscription_form,
        'user_has_liked': user_has_liked,
        'like_count': article.get_like_count(),
    }
    return render(request, 'music/news_detail.html', context)

# Update your news_view to include subscription form
def news_view(request):
    """News page"""
    featured_article = NewsArticle.objects.filter(
        is_published=True, 
        is_featured=True
    ).first()
    
    latest_news = NewsArticle.objects.filter(
        is_published=True
    ).exclude(id=featured_article.id if featured_article else None)[:8]
    
    categories = NewsArticle.CATEGORY_CHOICES
    subscription_form = NewsSubscriptionForm()
    
    context = {
        'featured_article': featured_article,
        'latest_news': latest_news,
        'categories': categories,
        'subscription_form': subscription_form,
    }
    return render(request, 'music/news.html', context)
def videos_view(request):
    """Videos page with YouTube videos"""
    featured_videos = YouTubeVideo.objects.filter(
        is_active=True,
        is_featured=True
    ).order_by('-added_date')[:4]
    
    all_videos = YouTubeVideo.objects.filter(
        is_active=True
    ).order_by('-added_date')
    
    featured_artists = Artist.objects.filter(is_verified=True).annotate(
        total_songs_count=Count('songs', filter=Q(songs__is_approved=True)),
        total_plays=Coalesce(Sum('songs__plays', filter=Q(songs__is_approved=True)), 0),
        total_downloads=Coalesce(Sum('songs__downloads', filter=Q(songs__is_approved=True)), 0),
        followers_count=Count('followers')
    ).order_by('-created_at')[:6]
    
    paginator = Paginator(all_videos, 12)
    page_number = request.GET.get('page')
    all_videos_page = paginator.get_page(page_number)
    
    context = {
        'featured_videos': featured_videos,
        'all_videos': all_videos_page,
        'featured_artists': featured_artists,
    }
    return render(request, 'music/videos.html', context)

@require_POST
def track_video_play(request):          
    """API endpoint to track video plays"""
    try:
        data = json.loads(request.body)
        video_id = data.get('video_id')
        video = get_object_or_404(YouTubeVideo, youtube_id=video_id)
        video.increment_plays()
        return JsonResponse({'success': True, 'plays': video.plays})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def recent_activity(request):
    """Page showing recent activity across the platform"""
    recent_plays = SongPlay.objects.select_related('song', 'song__artist', 'user').order_by('-played_at')[:20]
    recent_downloads = SongDownload.objects.select_related('song', 'song__artist', 'user').order_by('-downloaded_at')[:20]
    recent_follows = Follow.objects.select_related('follower', 'artist').order_by('-followed_at')[:20]
    recent_uploads = Song.objects.filter(is_approved=True).select_related('artist', 'genre').order_by('-upload_date')[:20]
    
    all_activity = []
    
    for play in recent_plays:
        all_activity.append({
            'type': 'play',
            'item': play.song,
            'user': play.user,
            'time': play.played_at,
            'description': f"played {play.song.title}",
            'plays': play.song.plays,
            'downloads': play.song.downloads
        })
    
    for download in recent_downloads:
        all_activity.append({
            'type': 'download',
            'item': download.song,
            'user': download.user,
            'time': download.downloaded_at,
            'description': f"downloaded {download.song.title}",
            'plays': download.song.plays,
            'downloads': download.song.downloads
        })
    
    for follow in recent_follows:
        all_activity.append({
            'type': 'follow',
            'item': follow.artist,
            'user': follow.follower,
            'time': follow.followed_at,
            'description': f"started following {follow.artist.name}"
        })
    
    for upload in recent_uploads:
        all_activity.append({
            'type': 'upload',
            'item': upload,
            'user': upload.artist.user,
            'time': upload.upload_date,
            'description': f"uploaded {upload.title}",
            'plays': upload.plays,
            'downloads': upload.downloads
        })
    
    all_activity.sort(key=lambda x: x['time'], reverse=True)
    all_activity = all_activity[:50]
    
    context = {
        'recent_activity': all_activity,
    }
    return render(request, 'music/recent_activity.html', context)

# API endpoints for play and download tracking
@require_POST
def api_track_play(request):
    """API endpoint to track song plays"""
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        song = get_object_or_404(Song, id=song_id, is_approved=True)
        
        # Increment play count
        song.increment_plays()
        
        # Create detailed play record if user is authenticated
        if request.user.is_authenticated:
            SongPlay.objects.create(
                song=song,
                user=request.user,
                ip_address=get_client_ip(request),
                duration_played=data.get('duration_played', 0),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                audio_quality='high' if hasattr(request.user, 'userprofile') and request.user.userprofile.is_premium else 'standard'
            )
        
        return JsonResponse({
            'success': True,
            'plays': song.plays,
            'song_id': song.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
def api_track_download(request):
    """API endpoint to track song downloads"""
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        song = get_object_or_404(Song, id=song_id, is_approved=True)
        
        # Increment download count
        song.increment_downloads()
        
        # Create detailed download record if user is authenticated
        if request.user.is_authenticated:
            SongDownload.objects.create(
                song=song,
                user=request.user,
                ip_address=get_client_ip(request),
                file_size=data.get('file_size', 0)
            )
        
        return JsonResponse({
            'success': True,
            'downloads': song.downloads,
            'song_id': song.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def get_song_stats(request, song_id):
    """Get detailed statistics for a song"""
    song = get_object_or_404(Song, id=song_id)
    
    # Basic stats
    stats = {
        'plays': song.plays,
        'downloads': song.downloads,
        'title': song.title,
        'artist': song.artist.name
    }
    
    # Detailed play statistics
    play_stats = SongPlay.objects.filter(song=song).aggregate(
        total_plays=Count('id'),
        unique_listeners=Count('user', distinct=True),
        avg_duration=Avg('duration_played'),
        total_duration=Sum('duration_played')
    )
    
    # Download statistics
    download_stats = SongDownload.objects.filter(song=song).aggregate(
        total_downloads=Count('id'),
        unique_downloaders=Count('user', distinct=True)
    )
    
    # Recent activity (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_plays = SongPlay.objects.filter(
        song=song,
        played_at__gte=seven_days_ago
    ).count()
    
    recent_downloads = SongDownload.objects.filter(
        song=song,
        downloaded_at__gte=seven_days_ago
    ).count()
    
    stats.update({
        'play_stats': play_stats,
        'download_stats': download_stats,
        'recent_plays': recent_plays,
        'recent_downloads': recent_downloads
    })
    
    return JsonResponse(stats)


# Add these API endpoints to your music/views.py

@require_POST
@login_required
def api_track_play(request):
    """API endpoint to track song plays - FIXED VERSION"""
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        
        if not song_id:
            return JsonResponse({'success': False, 'error': 'Song ID required'}, status=400)
        
        song = get_object_or_404(Song, id=song_id, is_approved=True)
        
        # Increment play count on the song model
        song.plays += 1
        song.save()
        
        # Create detailed play record
        play = SongPlay.objects.create(
            song=song,
            user=request.user,
            ip_address=get_client_ip(request),
            duration_played=data.get('duration_played', 0),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            session_id=request.session.session_key or '',
            audio_quality='high' if hasattr(request.user, 'userprofile') and getattr(request.user.userprofile, 'is_premium', False) else 'standard'
        )
        
        return JsonResponse({
            'success': True,
            'play_count': song.plays,
            'song_id': song.id,
            'play_id': play.id,
            'message': 'Play count updated successfully'
        })
        
    except Song.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Song not found'}, status=404)
    except Exception as e:
        print(f"Play tracking error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
@login_required
def api_track_download(request):
    """API endpoint to track song downloads - FIXED VERSION"""
    try:
        data = json.loads(request.body)
        song_id = data.get('song_id')
        song_title = data.get('song_title')
        artist_name = data.get('artist_name')
        
        # Try to get song by ID first
        song = None
        if song_id:
            try:
                song = Song.objects.get(id=song_id, is_approved=True)
            except Song.DoesNotExist:
                pass
        
        # Fallback to title/artist lookup
        if not song and song_title and artist_name:
            try:
                song = Song.objects.filter(
                    title__iexact=song_title,
                    artist__name__iexact=artist_name,
                    is_approved=True
                ).first()
            except:
                pass
        
        if not song:
            return JsonResponse({'success': False, 'error': 'Song not found'}, status=404)
        
        # Increment download count
        song.downloads += 1
        song.save()
        
        # Create download record
        download = SongDownload.objects.create(
            song=song,
            user=request.user,
            ip_address=get_client_ip(request),
            file_size=data.get('file_size', 0),
            audio_quality='high' if hasattr(request.user, 'userprofile') and getattr(request.user.userprofile, 'is_premium', False) else 'standard'
        )
        
        return JsonResponse({
            'success': True,
            'download_count': song.downloads,
            'song_id': song.id,
            'message': 'Download tracked successfully'
        })
        
    except Exception as e:
        print(f"Download tracking error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
@login_required
def api_like_song(request, song_id):
    """API endpoint to like/unlike a song"""
    try:
        song = get_object_or_404(Song, id=song_id, is_approved=True)
        
        # Check if user has a profile with liked_songs
        if not hasattr(request.user, 'userprofile'):
            return JsonResponse({
                'success': False, 
                'error': 'User profile not found'
            }, status=400)
        
        user_profile = request.user.userprofile
        
        # Check if song is already liked
        if song in user_profile.liked_songs.all():
            # Unlike the song
            user_profile.liked_songs.remove(song)
            liked = False
            message = f"Removed {song.title} from liked songs"
        else:
            # Like the song
            user_profile.liked_songs.add(song)
            liked = True
            message = f"Added {song.title} to liked songs"
        
        # Get updated count
        likes_count = user_profile.liked_songs.count()
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count,
            'song_id': song.id,
            'message': message
        })
        
    except Song.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Song not found'}, status=404)
    except Exception as e:
        print(f"Like error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
@login_required
def api_follow_artist(request, artist_id):
    """API endpoint to follow/unfollow an artist"""
    try:
        from artists.models import Artist, Follow  # Import here to avoid circular imports
        
        artist = get_object_or_404(Artist, id=artist_id, is_verified=True)
        
        # Check if user is trying to follow themselves
        if hasattr(request.user, 'artist_profile') and request.user.artist_profile == artist:
            return JsonResponse({
                'success': False,
                'error': 'You cannot follow yourself'
            }, status=400)
        
        # Check if already following
        follow_exists = Follow.objects.filter(
            follower=request.user, 
            artist=artist
        ).exists()
        
        if follow_exists:
            # Unfollow
            Follow.objects.filter(follower=request.user, artist=artist).delete()
            followed = False
            message = f"Unfollowed {artist.name}"
        else:
            # Follow
            Follow.objects.create(follower=request.user, artist=artist)
            followed = True
            message = f"Now following {artist.name}"
        
        # Get updated followers count
        followers_count = artist.followers.count()
        
        return JsonResponse({
            'success': True,
            'followed': followed,
            'followers_count': followers_count,
            'artist_id': artist.id,
            'message': message
        })
        
    except Exception as e:
        print(f"Follow error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)