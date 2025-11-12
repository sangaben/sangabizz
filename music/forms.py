# music/forms.py
from django import forms
from .models import Song

class SongUploadForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = [
            'title', 'genre', 'audio_file', 'cover_image', 
            'lyrics', 'bpm', 'release_year', 'is_premium_only'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter song title'
            }),
            'genre': forms.Select(attrs={'class': 'form-control'}),
            'lyrics': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter song lyrics (optional)'
            }),
            'bpm': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Beats per minute (optional)'
            }),
            'release_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Release year (optional)'
            }),
            'is_premium_only': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_audio_file(self):
        audio_file = self.cleaned_data.get('audio_file')
        if audio_file:
            # Check file size (10MB limit)
            if audio_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Audio file must be less than 10MB")
            
            # Check file extension
            allowed_extensions = ['mp3', 'wav', 'ogg', 'm4a']
            file_extension = audio_file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
                )
        
        return audio_file
    
    def clean_release_year(self):
        release_year = self.cleaned_data.get('release_year')
        if release_year:
            current_year = timezone.now().year
            if release_year < 1900 or release_year > current_year + 1:
                raise forms.ValidationError("Please enter a valid release year")
        return release_year
    

# music/forms.py (add these forms)

from django import forms
from .models import NewsComment, NewsSubscription

class NewsCommentForm(forms.ModelForm):
    class Meta:
        model = NewsComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write your comment...',
                'rows': 4,
                'maxlength': 1000
            }),
        }
        labels = {
            'content': 'Your Comment'
        }

# music/forms.py (add these forms)

from django import forms
from .models import NewsComment, NewsSubscription

class NewsCommentForm(forms.ModelForm):
    class Meta:
        model = NewsComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write your comment...',
                'rows': 4,
                'maxlength': 1000
            }),
        }
        labels = {
            'content': 'Your Comment'
        }

class NewsSubscriptionForm(forms.ModelForm):
    class Meta:
        model = NewsSubscription
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address...'
            })
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if NewsSubscription.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("This email is already subscribed to our newsletter.")
        return email
    
