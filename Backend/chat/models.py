from django.db import models

# Create your models here.

class Message(models.Model):
    prompt = models.TextField()
    response = models.TextField(default='')
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Message(prompt={self.prompt}, response={self.response})'
    
class UploadedPDF(models.Model):
    pdf_file = models.FileField(upload_to='pdfs/')
    description = models.TextField(default='')
    upload_date = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.pdf_file.name

class OpenAIModel(models.Model):
    openai_api_key = models.CharField(max_length=255)
    model_name = models.CharField(max_length=255)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.model_name

class ChunkSettings(models.Model):
    chunk_size = models.PositiveIntegerField(default=600)
    chunk_overlap = models.PositiveIntegerField(default=50)

    def __str__(self):
        return f"Chunk Settings - Chunk Size: {self.chunk_size}, Chunk Overlap: {self.chunk_overlap}"