from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from datetime import timedelta

class Genre(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#6c5ce7')  # Hex color
    
    def __str__(self):
        return self.name

class ArtistManager(models.Manager):
    def verified(self):
        return self.filter(is_verified=True)
    
    def with_stats(self):
        return self.annotate(
            total_songs=models.Count('songs'),
            total_plays=models.Sum('songs__plays'),
            total_downloads=models.Sum('songs__downloads')
        )
    
    def active_artists(self):
        """Artists who have at least one approved song"""
        return self.filter(songs__is_approved=True).distinct()

class Artist(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='artist_profile'
    )
    name = models.CharField(max_length=200)
    bio = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='artists/', blank=True, null=True)
    genre = models.ForeignKey('Genre', on_delete=models.SET_NULL, null=True, blank=True)
    website = models.URLField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ArtistManager()
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_artist_user')
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def total_plays(self):
        return sum(song.plays for song in self.songs.all())
    
    @property
    def total_downloads(self):
        return sum(song.downloads for song in self.songs.all())
    
    @property
    def total_songs(self):
        return self.songs.count()
    
    @property
    def approved_songs_count(self):
        return self.songs.filter(is_approved=True).count()
    
    @property
    def is_new_artist(self):
        """Check if artist was created in the last 30 days"""
        return (timezone.now() - self.created_at).days <= 30
    
    @property
    def is_active(self):
        """Check if artist has approved songs"""
        return self.songs.filter(is_approved=True).exists()
    
    @property
    def recent_songs(self):
        """Get recent songs (last 30 days)"""
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return self.songs.filter(upload_date__gte=thirty_days_ago, is_approved=True)

class Song(models.Model):
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='songs')
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
    audio_file = models.FileField(
        upload_to='songs/',
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])]
    )
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    duration = models.PositiveIntegerField(help_text="Duration in seconds", default=0)
    upload_date = models.DateTimeField(auto_now_add=True)
    plays = models.PositiveIntegerField(default=0)
    downloads = models.PositiveIntegerField(default=0)
    is_approved = models.BooleanField(default=False)  # For moderation
    is_featured = models.BooleanField(default=False)
    
    # Premium content fields
    is_premium_only = models.BooleanField(default=False, help_text="Only available to premium users")
    preview_duration = models.PositiveIntegerField(default=30, help_text="Preview duration in seconds for free users")
    
    class Meta:
        ordering = ['-upload_date']
    
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
    
    def can_be_accessed_by(self, user):
        """Check if user can access this song"""
        if not self.is_premium_only:
            return True
        if user.is_authenticated and hasattr(user, 'userprofile'):
            return user.userprofile.is_premium_active
        return False

class Playlist(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    songs = models.ManyToManyField(Song, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='playlist_covers/', blank=True, null=True)
    
    # Premium playlist features
    is_premium_curated = models.BooleanField(default=False, help_text="Premium-only curated playlist")
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']

class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('listener', 'Listener'),
        ('artist', 'Artist'),
    ]
    
    PREMIUM_PLAN_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
        ('premium_plus', 'Premium Plus'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='listener')
    favorite_genres = models.ManyToManyField(Genre, blank=True)
    liked_songs = models.ManyToManyField('Song', related_name='liked_by', blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Premium subscription fields
    premium_plan = models.CharField(
        max_length=20, 
        choices=PREMIUM_PLAN_CHOICES, 
        default='free'
    )
    premium_since = models.DateTimeField(blank=True, null=True)
    premium_expires = models.DateTimeField(blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Premium features usage tracking
    offline_downloads_used = models.PositiveIntegerField(default=0)
    max_offline_downloads = models.PositiveIntegerField(default=0)  # 0 = unlimited for premium
    
    def __str__(self):
        return self.user.username
    
    @property
    def is_artist(self):
        return self.user_type == 'artist'
    
    @property
    def is_premium(self):
        """Check if user has an active premium subscription"""
        return self.premium_plan in ['premium', 'premium_plus'] and self.is_premium_active
    
    @property
    def is_premium_active(self):
        """Check if premium subscription is currently active"""
        if self.premium_plan == 'free':
            return False
        if not self.premium_expires:
            return True  # Lifetime subscription
        return timezone.now() < self.premium_expires
    
    @property
    def days_until_expiry(self):
        """Days until premium expires"""
        if not self.is_premium_active or not self.premium_expires:
            return 0
        delta = self.premium_expires - timezone.now()
        return max(0, delta.days)
    
    @property
    def artist_profile(self):
        if self.is_artist:
            try:
                return self.user.artist_profile
            except Artist.DoesNotExist:
                # Auto-correct if artist profile doesn't exist
                self.user_type = 'listener'
                self.save()
                return None
        return None
    
    def upgrade_to_premium(self, plan_type='premium', duration_days=30):
        """Upgrade user to premium plan"""
        self.premium_plan = plan_type
        self.premium_since = timezone.now()
        self.premium_expires = timezone.now() + timedelta(days=duration_days)
        
        # Set download limits based on plan
        if plan_type == 'premium':
            self.max_offline_downloads = 100  # 100 songs for premium
        elif plan_type == 'premium_plus':
            self.max_offline_downloads = 0  # Unlimited for premium plus
        
        self.save()
    
    def downgrade_to_free(self):
        """Downgrade user to free plan"""
        self.premium_plan = 'free'
        self.premium_expires = None
        self.max_offline_downloads = 0
        self.offline_downloads_used = 0
        self.save()
    
    def can_download_offline(self):
        """Check if user can download more songs offline"""
        if not self.is_premium_active:
            return False
        if self.max_offline_downloads == 0:  # Unlimited
            return True
        return self.offline_downloads_used < self.max_offline_downloads
    
    def record_offline_download(self):
        """Record an offline download"""
        if self.can_download_offline():
            self.offline_downloads_used += 1
            self.save()
            return True
        return False
    
    def get_premium_plan_display_name(self):
        """Get formatted premium plan name"""
        return dict(self.PREMIUM_PLAN_CHOICES).get(self.premium_plan, 'Free')

class SubscriptionPlan(models.Model):
    """Model to manage subscription plans"""
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=UserProfile.PREMIUM_PLAN_CHOICES)
    price_monthly = models.DecimalField(max_digits=6, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    description = models.TextField()
    features = models.JSONField(default=list)  # List of features
    is_active = models.BooleanField(default=True)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - ${self.price_monthly}/month"
    
    class Meta:
        ordering = ['price_monthly']

class Payment(models.Model):
    """Model to track payments"""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']

class SongPlay(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    played_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    duration_played = models.PositiveIntegerField(default=0)  # Seconds played
    
    # Premium analytics
    audio_quality = models.CharField(
        max_length=20, 
        choices=[('standard', 'Standard'), ('high', 'High'), ('ultra', 'Ultra HD')],
        default='standard'
    )
    
    class Meta:
        ordering = ['-played_at']

class SongDownload(models.Model):
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Premium download info
    is_offline_download = models.BooleanField(default=False)
    audio_quality = models.CharField(
        max_length=20, 
        choices=[('standard', 'Standard'), ('high', 'High'), ('ultra', 'Ultra HD')],
        default='standard'
    )
    
    class Meta:
        ordering = ['-downloaded_at']

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    liked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'song']
        ordering = ['-liked_at']

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='followers')
    followed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['follower', 'artist']
        ordering = ['-followed_at']

# ===== SIGNAL HANDLERS =====
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    try:
        instance.userprofile.save()
    except ObjectDoesNotExist:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=Song)
def auto_create_artist_profile_on_song_upload(sender, instance, created, **kwargs):
    """
    Automatically create artist profile when a user uploads their first song
    This is the key function that auto-adds artists to the artists page
    """
    if created:
        try:
            # Get the user from the song's artist field
            # IMPORTANT: The song.artist should be the Artist instance, not User
            # We need to get the user from the artist instance
            user = instance.artist.user
            
            print(f"Processing song upload for user: {user.username}")
            
            # Check if artist profile already exists
            if not hasattr(user, 'artist_profile'):
                print(f"Creating artist profile for {user.username}")
                
                # Create artist profile using the utility function
                artist_profile, created = create_artist_profile(
                    user,
                    name=user.get_full_name() or user.username,
                    bio=f"Artist on Sangabiz - {instance.genre.name} artist" if instance.genre else "Artist on Sangabiz",
                    genre=instance.genre
                )
                
                if created:
                    print(f"✅ Auto-created artist profile for {user.username}")
                    # Send notification or perform other actions
                else:
                    print(f"ℹ️ Updated existing artist profile for {user.username}")
            else:
                print(f"ℹ️ Artist profile already exists for {user.username}")
                    
        except Exception as e:
            print(f"❌ Error auto-creating artist profile: {e}")

@receiver(post_save, sender=UserProfile)
def sync_artist_profile_with_user_type(sender, instance, created, **kwargs):
    """
    Sync artist profile when user type changes to 'artist'
    """
    if not created and instance.user_type == 'artist':
        # Ensure artist profile exists when user becomes artist
        if not hasattr(instance.user, 'artist_profile'):
            print(f"Creating artist profile for {instance.user.username} (user type changed to artist)")
            create_artist_profile(
                instance.user,
                name=instance.user.get_full_name() or instance.user.username,
                bio=instance.bio or "Artist on Sangabiz"
            )

# ===== UTILITY FUNCTIONS =====
def create_artist_profile(user, **kwargs):
    """
    Safely create an artist profile for a user
    Returns (artist, created) tuple
    """
    try:
        # Check if artist profile already exists
        if hasattr(user, 'artist_profile'):
            artist = user.artist_profile
            # Update existing artist with new data
            for key, value in kwargs.items():
                if hasattr(artist, key):
                    setattr(artist, key, value)
            artist.save()
            return artist, False
        else:
            # Create new artist profile
            artist = Artist.objects.create(user=user, **kwargs)
            # Update user profile
            profile = user.userprofile
            profile.user_type = 'artist'
            profile.save()
            return artist, True
    except Exception as e:
        print(f"❌ Error creating artist profile: {e}")
        return None, False

def get_user_audio_quality(user):
    """Get appropriate audio quality for user based on subscription"""
    if not user.is_authenticated or not hasattr(user, 'userprofile'):
        return 'standard'
    
    profile = user.userprofile
    if profile.premium_plan == 'premium_plus':
        return 'ultra'
    elif profile.premium_plan == 'premium':
        return 'high'
    else:
        return 'standard'

def get_or_create_artist_for_user(user, **kwargs):
    """
    Get existing artist profile or create one for user
    This ensures every user who uploads songs becomes an artist automatically
    """
    try:
        if hasattr(user, 'artist_profile'):
            return user.artist_profile, False
        else:
            artist = Artist.objects.create(user=user, **kwargs)
            # Update user profile type
            user_profile = user.userprofile
            user_profile.user_type = 'artist'
            user_profile.save()
            return artist, True
    except Exception as e:
        print(f"Error in get_or_create_artist_for_user: {e}")
        return None, False

# ===== MODEL METHODS FOR AUTO-ARTIST SYSTEM =====
def user_has_artist_access(user):
    """Check if user has access to artist features"""
    return (user.is_authenticated and 
            hasattr(user, 'userprofile') and 
            user.userprofile.is_artist)

def get_artists_with_songs():
    """Get all artists who have at least one approved song"""
    return Artist.objects.filter(songs__is_approved=True).distinct()

def get_trending_artists(days=7):
    """Get trending artists based on recent plays"""
    date_threshold = timezone.now() - timedelta(days=days)
    return Artist.objects.filter(
        songs__songplay__played_at__gte=date_threshold
    ).annotate(
        recent_plays=models.Count('songs__songplay')
    ).order_by('-recent_plays')

# ===== MIGRATION NOTES =====
"""
After updating this models.py, run these commands:

1. python manage.py makemigrations
2. python manage.py migrate

If you encounter any issues with the Song.artist field, you might need to:
1. Check if the Song.artist field properly links to Artist model
2. Ensure the signal handler correctly gets the user from song.artist.user
3. Verify that when a song is uploaded, the artist field is set correctly

The auto-artist system works like this:
1. User uploads a song → Song object is created
2. post_save signal triggers auto_create_artist_profile_on_song_upload
3. Function checks if user has artist profile
4. If not, creates artist profile automatically
5. Artist now appears on artists page (if they have approved songs)
"""