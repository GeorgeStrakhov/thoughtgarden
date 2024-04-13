from django import forms

class SearchForm(forms.Form):
    search_text = forms.CharField(label="Search", max_length=1000)

class SeedForm(forms.Form):
    title = forms.CharField(
        label='Title',
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})  # Adding Bootstrap class for styling
    )
    content = forms.CharField(
        label='Content',
        widget=forms.Textarea(attrs={'class': 'form-control'})  # Textarea with Bootstrap class
    )

class FileUploadForm(forms.Form):
    title = forms.CharField(
        label="Title",
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'})  # Bootstrap class for consistent styling
    )
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'})  # Bootstrap class for file input
    )
    upload_to_s3 = forms.BooleanField(
        required=False,
        label="Upload to S3",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})  # Checkbox with Bootstrap class
    )

class YouTubeForm(forms.Form):
    url = forms.URLField(
        label='YouTube URL',
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Enter the full URL of the YouTube video.'
    )
    download = forms.BooleanField(
        label='Download Video',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Check this box if you want to download the video.'
    )
