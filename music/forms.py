# music/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Song, Genre, Artist, UserProfile, Playlist

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'First Name',
            'class': 'form-control'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Last Name', 
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email Address',
            'class': 'form-control'
        })
    )
    is_artist = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'artist-checkbox-input'
        })
    )
    artist_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Artist Name',
            'class': 'form-control'
        })
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Tell us about your music...',
            'rows': 4,
            'class': 'form-control'
        })
    )
    genre = forms.ModelChoiceField(
        queryset=Genre.objects.all(),
        required=False,
        empty_label="Select Genre",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the terms of service'}
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2', 
                 'is_artist', 'artist_name', 'bio', 'genre', 'terms')
    
    def clean(self):
        cleaned_data = super().clean()
        is_artist = cleaned_data.get('is_artist')
        artist_name = cleaned_data.get('artist_name')
        
        if is_artist and not artist_name:
            raise forms.ValidationError("Artist name is required when registering as an artist.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Create user profile
            user_type = 'artist' if self.cleaned_data['is_artist'] else 'listener'
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'user_type': user_type}
            )
            
            # If user is artist, create artist profile
            if self.cleaned_data['is_artist']:
                artist, created = Artist.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': self.cleaned_data['artist_name'],
                        'bio': self.cleaned_data['bio'],
                        'genre': self.cleaned_data['genre'],
                        'is_verified': False
                    }
                )
                # Add artist to profile
                profile.artist_profile = artist
                profile.save()
        
        return user
# In your forms.py - UPDATE the SongUploadForm
class SongUploadForm(forms.ModelForm):
    duration_minutes = forms.IntegerField(
        min_value=0,
        max_value=59,
        required=True,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Minutes',
            'min': '0',
            'max': '59'
        })
    )
    duration_seconds = forms.IntegerField(
        min_value=0,
        max_value=59,
        required=True,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'placeholder': 'Seconds',
            'min': '0',
            'max': '59'
        })
    )

    class Meta:
        model = Song
        fields = ['title', 'genre', 'audio_file', 'cover_image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter song title'
            }),
            'genre': forms.Select(attrs={
                'class': 'form-select'
            }),
            'audio_file': forms.FileInput(attrs={'class': 'form-input'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.artist = kwargs.pop('artist', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        minutes = cleaned_data.get('duration_minutes')
        seconds = cleaned_data.get('duration_seconds')
        
        if minutes is not None and seconds is not None:
            if minutes < 0 or seconds < 0 or seconds > 59:
                raise forms.ValidationError("Invalid duration values. Minutes must be ≥ 0, seconds must be 0-59")
            
            if minutes == 0 and seconds == 0:
                raise forms.ValidationError("Duration cannot be zero")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Calculate total duration in seconds
        minutes = self.cleaned_data.get('duration_minutes', 0)
        seconds = self.cleaned_data.get('duration_seconds', 0)
        instance.duration = (minutes * 60) + seconds
        
        if self.artist:
            instance.artist = self.artist
            
        if commit:
            instance.save()
            
        return instance

class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ['name', 'description', 'is_public', 'cover_image']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Playlist Name',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Playlist description...',
                'rows': 3,
                'class': 'form-control'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }