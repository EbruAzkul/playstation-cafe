from django import forms
from django.core.exceptions import ValidationError

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel Dosyası',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls'})
    )
    
    update_existing = forms.BooleanField(
        label='Mevcut ürünleri güncelle',
        initial=True,
        required=False
    )
    
    create_categories = forms.BooleanField(
        label='Yeni kategoriler oluştur', 
        initial=True,
        required=False
    )
    
    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            raise ValidationError('Sadece Excel dosyaları kabul edilir.')
        
        if excel_file.size > 10 * 1024 * 1024:  # 10MB
            raise ValidationError('Dosya çok büyük.')
        
        return excel_file