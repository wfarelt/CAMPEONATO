from django import forms
from django.forms import inlineformset_factory
from .models import MatchDay, Match

class MatchDayForm(forms.ModelForm):
    class Meta:
        model = MatchDay
        fields = ['date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ej: Jornada de Apertura, Semifinal, etc.',
            }),
        }

class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['home_team', 'away_team', 'time']
        widgets = {
            'home_team': forms.Select(attrs={
                'class': 'form-control',
            }),
            'away_team': forms.Select(attrs={
                'class': 'form-control',
            }),
            'time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        home_team = cleaned_data.get('home_team')
        away_team = cleaned_data.get('away_team')
        
        if home_team and away_team:
            if home_team == away_team:
                raise forms.ValidationError("Un equipo no puede jugar contra sí mismo.")
        return cleaned_data

# Formset para crear múltiples partidos
MatchFormSet = inlineformset_factory(
    MatchDay, 
    Match, 
    form=MatchForm,
    extra=1,  # Empieza con 1 formulario vacío
    can_delete=True
)
