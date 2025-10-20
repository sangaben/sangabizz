from django.contrib import admin
from .models import Genre, Artist, Song, Playlist, UserProfile, SongPlay, SongDownload

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'color']
    search_fields = ['name']

@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ['title', 'artist', 'genre', 'duration', 'plays', 'downloads', 'upload_date']
    list_filter = ['genre', 'upload_date']
    search_fields = ['title', 'artist__name']
    readonly_fields = ['plays', 'downloads', 'upload_date']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'artist', 'genre', 'duration')
        }),
        ('Media Files', {
            'fields': ('audio_file', 'cover_image')
        }),
        ('Statistics', {
            'fields': ('plays', 'downloads', 'upload_date')
        }),
    )

@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'created_at', 'is_public']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'user__username']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user']
    filter_horizontal = ['favorite_genres', 'liked_songs']

@admin.register(SongPlay)
class SongPlayAdmin(admin.ModelAdmin):
    list_display = ['song', 'user', 'ip_address', 'played_at']
    list_filter = ['played_at']
    search_fields = ['song__title', 'user__username']
    readonly_fields = ['played_at']

@admin.register(SongDownload)
class SongDownloadAdmin(admin.ModelAdmin):
    list_display = ['song', 'user', 'ip_address', 'downloaded_at']
    list_filter = ['downloaded_at']
    search_fields = ['song__title', 'user__username']
    readonly_fields = ['downloaded_at']