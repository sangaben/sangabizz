from django.urls import path
from . import views

urlpatterns = [
    path('artists/', views.artists, name='artists'),
    path('artists/trending/', views.trending_artists, name='trending_artists'),
    path('artist/<int:artist_id>/', views.artist_detail, name='artist_detail'),
    path('dashboard/', views.artist_dashboard, name='artist_dashboard'),
    path('upload/', views.upload_music, name='upload_music'),
    path('my-uploads/', views.my_uploads, name='my_uploads'),
    path('follow/<int:artist_id>/', views.follow_artist, name='follow_artist'),
    
    # Song interaction URLs
    path('play-song/<int:song_id>/', views.play_song, name='play_song'),
    path('like-song/<int:song_id>/', views.like_song, name='like_song'),
    path('download-song/<int:song_id>/', views.download_song, name='download_song'),
    path('follow-artist/<int:artist_id>/', views.follow_artist_from_music, name='follow_artist_music'),
    path('update-play-duration/<int:song_id>/', views.update_play_duration, name='update_play_duration'),
    path('increment-play-count/<int:song_id>/', views.increment_play_count, name='increment_play_count'),
    path('artist-analytics/<int:artist_id>/', views.artist_analytics, name='artist_analytics'),
    path('edit-profile/', views.edit_artist_profile, name='edit_artist_profile'),
    path('earnings_details/', views.earnings_details, name='earnings_details'),
    path('activity-log/', views.activity_log, name='activity_log'),
]