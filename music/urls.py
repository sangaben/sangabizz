from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('discover/', views.discover, name='discover'),
    path('search/', views.search, name='search'),
    path('genres/', views.genres, name='genres'),
    path('genre/<int:genre_id>/', views.genre_songs, name='genre_songs'),
    path('download-song/<int:song_id>/', views.download_song, name='download_song'),
    path('song/<int:song_id>/', views.song_detail, name='song_detail'),
    
    # Play and interaction URLs
    path('play-song/<int:song_id>/', views.play_song, name='play_song'),
    path('update-play-duration/<int:song_id>/', views.update_play_duration, name='update_play_duration'),
    path('follow-artist/<int:artist_id>/', views.follow_artist_from_music, name='follow_artist_music'),
    
    # Activity and rankings
    path('top-songs/', views.top_songs, name='top_songs'),
    path('activity/', views.recent_activity, name='recent_activity'),
    
    # News section URLs
    path('news/', views.news_view, name='news'),
    path('news/<slug:slug>/', views.news_detail_view, name='news_detail'),
    #path('api/track-news-view/', views.track_news_view, name='track_news_view'),
    
    # Video interaction URLs
    path('api/track-video-play/', views.track_video_play, name='track_video_play'),
    #path('api/like-video/', views.like_video, name='like_video'),
    
    # Charts and events
   # path('charts/', views.charts_view, name='charts'),
    #path('charts/<int:chart_id>/', views.chart_detail_view, name='chart_detail'),
    #path('events/', views.events_view, name='events'),
    #path('radio/', views.radio_view, name='radio'),
    path('videos/', views.videos_view, name='videos'),

     # API endpoints for tracking
    path('api/track-play/', views.api_track_play, name='api_track_play'),
    path('api/track-download/', views.api_track_download, name='api_track_download'),
    path('api/songs/<int:song_id>/like/', views.api_like_song, name='api_like_song'),
    path('api/artists/<int:artist_id>/follow/', views.api_follow_artist, name='api_follow_artist'),
    
    # Alternative endpoints for compatibility
    path('api/play/', views.api_track_play, name='play_track'),
    path('api/download/', views.api_track_download, name='download_track'),


    path('news/', views.news_view, name='news'),
    path('news/<slug:slug>/', views.news_detail_view, name='news_detail'),
    path('news/<int:article_id>/like/', views.like_news_article, name='like_news_article'),
    path('news/comment/<int:comment_id>/like/', views.like_news_comment, name='like_news_comment'),
    path('news/subscribe/', views.subscribe_news, name='subscribe_news'),
    path('news/unsubscribe/', views.unsubscribe_news, name='unsubscribe_news'),

]