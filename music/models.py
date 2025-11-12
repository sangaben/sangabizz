# music/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from datetime import timedelta
from django.utils.text import slugify   

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#6c5ce7')  # Hex color
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['name']
        app_label = 'music'  # Add this line
    
    def __str__(self):
        return self.name

class Song(models.Model):
    AUDIO_QUALITY_CHOICES = [
        ('standard', 'Standard'),
        ('high', 'High (320kbps)'),
        ('ultra', 'Ultra HD (FLAC)'),
    ]
    
    title = models.CharField(max_length=200)
    artist = models.ForeignKey('artists.Artist', on_delete=models.CASCADE, related_name='songs')
    
    # FIXED: Only ONE genre field
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True, related_name='songs')
    
    audio_file = models.FileField(
        upload_to='songs/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])]
    )
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    duration = models.PositiveIntegerField(help_text="Duration in seconds", default=0)
    upload_date = models.DateTimeField(auto_now_add=True)
    plays = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    
    # REMOVED: Duplicate genre field that was here
    
    is_approved = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    # Premium content fields
    is_premium_only = models.BooleanField(default=False, help_text="Only available to premium users")
    preview_duration = models.PositiveIntegerField(default=30, help_text="Preview duration in seconds for free users")
    audio_quality = models.CharField(max_length=20, choices=AUDIO_QUALITY_CHOICES, default='standard')
    
    # Metadata
    lyrics = models.TextField(blank=True, null=True)
    bpm = models.PositiveIntegerField(blank=True, null=True, help_text="Beats per minute")
    release_year = models.PositiveIntegerField(blank=True, null=True)
    
    class Meta:
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['-upload_date']),
            models.Index(fields=['is_approved', 'is_featured']),
        ]
        app_label = 'music'  # Add this line
    
    def __str__(self):
        return f"{self.title} - {self.artist.name}"
    
    def increment_plays(self):
        self.plays += 1
        self.save()
    
    def increment_downloads(self):
        self.downloads += 1
        self.save()
    
    @property
    def formatted_duration(self):
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes}:{seconds:02d}"
    
    @property
    def is_recent(self):
        return (timezone.now() - self.upload_date).days <= 7
    
    @property
    def popularity_score(self):
        """Calculate a simple popularity score based on plays and downloads"""
        return self.plays + (self.downloads * 2)
    
    def can_be_accessed_by(self, user):
        """Check if user can access this song"""
        if not self.is_premium_only:
            return True
        if user.is_authenticated and hasattr(user, 'userprofile'):
            return user.userprofile.is_premium_active
        return False

class SongPlay(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='play_history')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='song_plays')
    played_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    duration_played = models.PositiveIntegerField(default=0, help_text="Seconds played")
    
    # Device and session info
    user_agent = models.TextField(blank=True, null=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Premium analytics
    audio_quality = models.CharField(
        max_length=20, 
        choices=Song.AUDIO_QUALITY_CHOICES,
        default='standard'
    )
    
    class Meta:
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['-played_at']),
            models.Index(fields=['song', 'played_at']),
        ]
        app_label = 'music'  # Add this line
    
    def __str__(self):
        return f"{self.song.title} played by {self.user.username if self.user else 'Anonymous'}"

class SongDownload(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE, related_name='download_history')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='song_downloads')
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Download details
    is_offline_download = models.BooleanField(default=False)
    audio_quality = models.CharField(
        max_length=20, 
        choices=Song.AUDIO_QUALITY_CHOICES,
        default='standard'
    )
    file_size = models.PositiveIntegerField(help_text="File size in bytes", null=True, blank=True)
    
    class Meta:
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['-downloaded_at']),
            models.Index(fields=['song', 'downloaded_at']),
        ]
        app_label = 'music'  # Add this line
    
    def __str__(self):
        return f"{self.song.title} downloaded by {self.user.username if self.user else 'Anonymous'}"

# music/models.py (update your existing models)

from django.utils.crypto import get_random_string
from django.db.models import Count

class NewsArticle(models.Model):
    CATEGORY_CHOICES = [
        ('local', 'Local News'),
        ('international', 'International News'),
        ('interviews', 'Artist Interviews'),
        ('releases', 'New Releases'),
        ('events', 'Music Events'),
    ]
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    excerpt = models.TextField(max_length=300, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='local')
    featured_image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    author = models.CharField(max_length=100, default='Sangabiz Team')
    published_date = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True)
    views = models.PositiveIntegerField(default=0)
    
    # Add these fields for liking functionality
    likes = models.ManyToManyField(
        User, 
        through='NewsLike',
        related_name='liked_news',
        blank=True
    )
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.excerpt and self.content:
            self.excerpt = self.content[:300] + '...' if len(self.content) > 300 else self.content
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
    
    def get_like_count(self):
        return self.likes.count()
    
    def user_has_liked(self, user):
        if user.is_authenticated:
            return self.likes.filter(id=user.id).exists()
        return False
    
    def get_popular_articles(cls, limit=5):
        """Get most popular articles based on views and likes"""
        return cls.objects.filter(is_published=True).annotate(
            total_likes=Count('likes')
        ).order_by('-views', '-total_likes')[:limit]
    
    class Meta:
        ordering = ['-published_date']

class NewsLike(models.Model):
    """Track news article likes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'article']
        ordering = ['-created_at']

class NewsComment(models.Model):
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=True)
    
    # Add likes for comments
    likes = models.ManyToManyField(
        User, 
        through='CommentLike',
        related_name='liked_news_comments',
        blank=True
    )
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"
    
    def get_like_count(self):
        return self.likes.count()
    
    def user_has_liked(self, user):
        if user.is_authenticated:
            return self.likes.filter(id=user.id).exists()
        return False

class CommentLike(models.Model):
    """Track comment likes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(NewsComment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'comment']
        ordering = ['-created_at']

class NewsView(models.Model):
    article = models.ForeignKey(NewsArticle, on_delete=models.CASCADE, related_name='article_views')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-viewed_at']

class NewsSubscription(models.Model):
    """News email subscriptions"""
    email = models.EmailField(unique=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    subscription_token = models.CharField(max_length=100, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.subscription_token:
            self.subscription_token = get_random_string(50)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.email} - {'Active' if self.is_active else 'Inactive'}"
    
    class Meta:
        ordering = ['-subscribed_at']

class Chart(models.Model):
    CHART_TYPE_CHOICES = [
        ('top_songs', 'Top Songs'),
        ('trending', 'Trending Now'),
        ('new_releases', 'New Releases'),
        ('local_charts', 'Local Charts'),
    ]
    
    title = models.CharField(max_length=100)
    chart_type = models.CharField(max_length=20, choices=CHART_TYPE_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title

class ChartEntry(models.Model):
    chart = models.ForeignKey(Chart, on_delete=models.CASCADE, related_name='entries')
    song = models.ForeignKey('music.Song', on_delete=models.CASCADE)  # Adjust based on your Song model
    position = models.PositiveIntegerField()
    previous_position = models.PositiveIntegerField(null=True, blank=True)
    weeks_on_chart = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['position']
        unique_together = ['chart', 'position']
import re

class YouTubeVideo(models.Model):
    title = models.CharField(max_length=200)
    youtube_url = models.URLField()
    youtube_id = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    added_date = models.DateTimeField(auto_now_add=True)
    views = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    duration = models.CharField(max_length=10, blank=True)
    
    def extract_youtube_id(self, url):
        """Extract YouTube video ID from various URL formats"""
        # Regular expression for YouTube ID extraction
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&?\n]+)',
            r'youtube\.com\/watch\?.*v=([^&?\n]+)',
            r'youtu\.be\/([^&?\n]+)',
            r'youtube\.com\/embed\/([^&?\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def save(self, *args, **kwargs):
        # Extract YouTube ID from URL
        if self.youtube_url and not self.youtube_id:
            self.youtube_id = self.extract_youtube_id(self.youtube_url)
        
        # Set thumbnail URL if we have a YouTube ID
        if self.youtube_id and not self.thumbnail_url:
            self.thumbnail_url = f'https://img.youtube.com/vi/{self.youtube_id}/hqdefault.jpg'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    def increment_views(self):
        self.views += 1
        self.save(update_fields=['views'])
    
    def increment_likes(self):
        self.likes += 1
        self.save(update_fields=['likes'])
    
    def get_embed_url(self):
        """Get the embed URL for the YouTube video"""
        if self.youtube_id:
            return f'https://www.youtube.com/embed/{self.youtube_id}'
        return None
    
    class Meta:
        ordering = ['-added_date']