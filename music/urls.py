from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('discover/', views.discover, name='discover'),
    path('library/', views.library, name='library'),
    path('playlists/', views.playlists, name='playlists'),
    path('genres/', views.genres, name='genres'),
    path('genre/<int:genre_id>/', views.genre_songs, name='genre_songs'),
    path('play-song/<int:song_id>/', views.play_song, name='play_song'),
    path('like-song/<int:song_id>/', views.like_song, name='like_song'),
    path('download-song/<int:song_id>/', views.download_song, name='download_song'),
    path('search/', views.search, name='search'),
    path('analytics/song/<int:song_id>/', views.song_analytics, name='song_analytics'),
    path('analytics/top-songs/', views.top_songs, name='top_songs'),
    
    # AUTH URLS - ADD THE ACCOUNTS/ PATHS TO HANDLE DJANGO REDIRECTS
    path('accounts/login/', views.login_view, name='login'),  # ADD THIS
    path('accounts/logout/', views.logout_view, name='logout'),  # ADD THIS
    path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    
    path('get-song-stats/<int:song_id>/', views.get_song_stats, name='get_song_stats'),
    path('upload/', views.upload_music, name='upload_music'),
    path('my-uploads/', views.my_uploads, name='my_uploads'),
    path('artist/dashboard/', views.artist_dashboard, name='artist_dashboard'),
    
    # ADD THESE MISSING URLS:
    path('artists/', views.artists, name='artists'),
    path('trending-artists/', views.trending_artists, name='trending_artists'),
    path('artist/<int:artist_id>/', views.artist_detail, name='artist_detail'),
    path('increment-play-count/<int:song_id>/', views.increment_play_count, name='increment_play_count'),
    path('increment-download-count/<int:song_id>/', views.increment_download_count, name='increment_download_count'),
    path('follow-artist/<int:artist_id>/', views.follow_artist, name='follow_artist'),
    
    # PLAYLIST MANAGEMENT URLS
    path('playlist/<int:playlist_id>/', views.playlist_detail, name='playlist_detail'),
    path('add-to-playlist/<int:song_id>/', views.add_to_playlist, name='add_to_playlist'),
    path('remove-from-playlist/<int:playlist_id>/<int:song_id>/', views.remove_from_playlist, name='remove_from_playlist'),
    path('delete-playlist/<int:playlist_id>/', views.delete_playlist, name='delete_playlist'),
    
    # User profile and settings URLs
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('help/', views.help_center, name='help_center'),
    
    # Premium URLs (you already have these from earlier)
    path('premium/', views.premium_pricing, name='premium_pricing'),
    path('premium/features/', views.premium_features, name='premium_features'),
    path('premium/payment/<str:plan_type>/', views.process_payment, name='process_payment'),
    path('premium/success/', views.premium_success, name='premium_success'),
    
    # ADD THESE MISSING PLAYLIST API ENDPOINTS
    path('play-playlist/<int:playlist_id>/', views.play_playlist, name='play_playlist'),  # ADD THIS
]