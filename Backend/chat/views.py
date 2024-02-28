from django.shortcuts import render
import os
from django.conf import settings
from .models import UploadedPDF
from .serializers import UploadedPDFSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_pdf_view(request):
    if request.method == 'POST':
        try:
            description = request.POST.get('description', '')
            files = request.FILES.getlist('pdf_files[]')

            # Check if files were uploaded
            if 'pdf_files[]' in request.FILES:
                pdf_files = request.FILES.getlist('pdf_files[]')

                # Loop through the uploaded PDF files
                for pdf_file in pdf_files:
                    # Create a new UploadedPDF instance and save the PDF
                    uploaded_pdf = UploadedPDF(pdf_file=pdf_file, description=description)
                    uploaded_pdf.save()

                # Retrieve all PDFs saved in the model
                pdf_docs = UploadedPDF.objects.all()

                # Serialize the PDFs using the UploadedPDFSerializer
                serializer = UploadedPDFSerializer(pdf_docs, many=True)

                return Response({"message": "PDFs uploaded successfully", "status": 200})
            else:
                return Response({"error": "No PDF files were uploaded"}, status=400)
        except Exception as e:
            # Handle the exception and return it as a JSON response
            print("error occured: ", e)
            return Response({"error": str(e)}, status=500)
    else:
        return Response({"error": "Unsupported request method"}, status=405)

import os
from django.conf import settings

@csrf_exempt
def get_uploaded_pdf_paths():
    pdf_docs = []

    # Loop through all the UploadedPDF objects in the database
    for uploaded_pdf in UploadedPDF.objects.all():
        # Get the PDF file's relative path (without media root)
        pdf_relative_path = str(uploaded_pdf.pdf_file)

        # Create the full path to the PDF file by joining with the media root
        pdf_full_path = os.path.abspath(os.path.join(settings.MEDIA_ROOT, pdf_relative_path))

        # Append the PDF file's full path to the list
        pdf_docs.append(pdf_full_path)
    print("pdf_docs inside function: ", pdf_docs)

    # You should return a response, for example, a JSON response with the data
    return pdf_docs


#Display pdf files
def get_recent_pdfs(request):
    if request.method == "GET":
        # Retrieve all items from the UploadedPDF model, ordered by upload_date in descending order
        recent_pdfs = UploadedPDF.objects.order_by('-upload_date')

        # Create a list of dictionaries with file names, descriptions, and primary keys
        pdf_list = []
        for pdf in recent_pdfs:
            pdf_dict = {
                'pdf_name': pdf.pdf_file.name.split('/')[-1],
                'description': pdf.description,
                'pk': pdf.pk,  # Add the primary key
            }
            pdf_list.append(pdf_dict)

        # Create a JSON response with the list of dictionaries
        response_data = {
            'pdfs': pdf_list
        }

        return JsonResponse(response_data, safe=False)
    return JsonResponse({"message": "Not allowed"}, status=405)


from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
import os

#Deleting doccuments
@csrf_exempt
def delete_document(request, pk):
    # Initialize the response data
    response_data = {}

    try:
        # Try to get the document based on its primary key
        document = UploadedPDF.objects.get(pk=pk)
        print("document: ", document)

        # Extract the actual file name
        file_name = os.path.basename(document.pdf_file.name)

        # Delete the document from the database
        document.delete()

        # Delete the document file from the media folder
        document_path = os.path.join(settings.MEDIA_ROOT, document.pdf_file.name)
        if os.path.exists(document_path):
            os.remove(document_path)

        response_data['success'] = True
        response_data['message'] = f'Document "{file_name}" has been deleted.'
    except ObjectDoesNotExist:
        response_data['success'] = False
        response_data['message'] = f'Document not found in the database.'
    except Exception as e:
        response_data['success'] = False
        response_data['message'] = f'An error occurred: {str(e)}'

    return JsonResponse(response_data)


# Process documents and save into vectorstore 
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.llms import OpenAI
from langchain.document_loaders import TextLoader, DirectoryLoader
from langchain.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFDirectoryLoader


global_db = None


@csrf_exempt
def process_documents(request):
    #global global_db2
    try:
        # Initialize the loader to process PDF files from the specified directory
        pdfs_folder_path = os.path.join(settings.MEDIA_ROOT, 'pdfs')
        print(pdfs_folder_path)
        loader = PyPDFDirectoryLoader(pdfs_folder_path)
        documents = loader.load()

        # Check if no PDF files are found
        if not documents:
            return JsonResponse({"error": "No files found"}, status=404)

        # Splitting the text into smaller documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)

        # Proceed only if there are texts
        if texts:
            # Load environment variables
            load_dotenv(".env")
            OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

            # Embed and store the texts
            embedding_function = OpenAIEmbeddings(model='text-embedding-ada-002', openai_api_key=OPENAI_API_KEY)
            global_db = Chroma.from_documents(texts, embedding_function, persist_directory="./chroma_db")
        else:
            return JsonResponse({"error": "No texts found in documents"}, status=404)
        return JsonResponse({"success": True, "message": "Embeddings created successfully"})
    except Exception as e:
        print("Error : ", e)
        return JsonResponse({"error": f"Error in creating embeddings: {str(e)}"}, status=500)



from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.memory import ConversationBufferMemory

load_dotenv(".env")
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


@csrf_exempt
def document_search_view(request):
    try:
        query = request.POST.get('query', '')
        print("question: ", query)
        # Embed and store the texts
        embedding_function = OpenAIEmbeddings(model='text-embedding-ada-002', openai_api_key=OPENAI_API_KEY)
        db3 = Chroma(persist_directory="./chroma_db", embedding_function=embedding_function)
        retriever = db3.as_retriever(search_kwargs={"k": 10})
        docs = retriever.get_relevant_documents(query) # Here we are filtering documents with similar meaning to the query
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

        # Create a ConversationBufferMemory object
        memory = ConversationBufferMemory(memory_key="chat_history", input_key="question")

        # Load the memory variables
        memory.load_memory_variables({})

        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        template = """Use the following pieces of context to answer the question at the end.
                    If you don't know the answer, just say that you don't know, don't try to 
                    make up an answer.
                    
    
                    {context}

                    Question: {question}

                    Helpful Answer:"""
        custom_rag_prompt = PromptTemplate.from_template(template)

        rag_chain = (
                    {"context": retriever | format_docs , "question": RunnablePassthrough()}
                    | custom_rag_prompt
                    | llm
                    | StrOutputParser()
                )
        
        answer = rag_chain.invoke(query)

        return JsonResponse({"success": True, "answer": answer})

    except Exception as e:
        print("Error : ", e)
        return JsonResponse({"error": f"Error in chatbot creation: {str(e)}"}, status=500)

from django.shortcuts import redirect
from django.contrib import messages

def clear_chroma_db(request):
    try:
        embedding_function = OpenAIEmbeddings(model='text-embedding-ada-002', openai_api_key=OPENAI_API_KEY)
        db= Chroma(persist_directory="./chroma_db", embedding_function=embedding_function)
        db.delete_collection()
        return JsonResponse ({"success": "Vectorstore has been reset!. Retrain the bot to get answers"})
    except Exception as e:
        return JsonResponse ({"Error" : f"An error occured {e}"})
       
    


def upload_docs_view(request):
    return render(request, 'upload.html')

def send_message_get_response(request):
    return render(request, 'chat.html')

def view_docs(request):
    return render(request, 'view_docs.html')

def process_documents_template(request):
    return render(request, 'process.html')

def reset(request):
    return render(request, 'reset.html')
