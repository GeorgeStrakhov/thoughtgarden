import os
from openai import AzureOpenAI, OpenAI

# Convert the environment variable to a boolean
USE_AZURE = os.getenv('USE_AZURE', 'False').lower() in ('true', '1', 't')

ENDPOINT = os.getenv('GPT_ENDPOINT', 'https://omc-ia-advertising.openai.azure.com')
API_KEY = os.getenv('GPT_API_KEY')
DEPLOYMENT = os.getenv('GPT_DEPLOYMENT', "")

# Adjust the default embedding model based on the desired default behavior
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', "text-embedding-ada-002")

if USE_AZURE:
    GPT_CLIENT = AzureOpenAI(
        api_key=API_KEY,
        azure_endpoint=ENDPOINT,
        api_version=DEPLOYMENT
    )
else:
    GPT_CLIENT = OpenAI(
        api_key=API_KEY,
    )

def get_embedding(text: str, model: str = EMBEDDING_MODEL, USE_AZURE=USE_AZURE):
    if len(str(text)) < 5 or len(str(text)) > 4000:
        return [0.0] * 1536 
    if USE_AZURE:
        result = GPT_CLIENT.embeddings.create(model=model,
                                        input=str(text))
    else:
        result = GPT_CLIENT.embeddings.create(model=model, input=str(text))
    return result.data[0].embedding
    


#Get Ideas tags from the text

tags_prompt = """
You are an assistant tasked with extracting the main tags from a text, focusing on specific information that aligns with predefined fields. Based on the text provided, you need to extract and fill in the following information in a dictionary format. If certain information is not mentioned in the text, leave the corresponding field blank.

{
    'Author': 'Extracted author name from the text, if mentioned',
    'Language': 'The language in which the text is written, if specified',
    'Topics': 'The main themes or subjects of the text, identified through analysis',
    'Tags': 'Specific keywords or tags that are relevant to the text, identified from the content',
    'Year': 'The year related to the text, such as publication year or the year the described events occurred, if mentioned',
    'Title': 'The title of the idea, inferred from the text if applicable',
    'Description': 'A brief description of the idea, based on the text',
    'Content URL': 'If the text mentions or implies a source URL for more content, provide it here',
    'Thumbnail': 'A mention or description of a thumbnail image, if the text provides clues about it',
    'Transcript': 'Any detailed transcript mentioned or alluded to in the text, related to the idea',
}

This task requires attentive reading of the text to identify and extract information that aligns with each field listed. Some fields may not be applicable depending on the text provided.
"""

tags_video_prompt = """
You are an assistant tasked with extracting the main tags from a text, focusing on specific information that aligns with predefined fields. 
Based on the text provided, you need to extract and fill in the following information in a dictionary format. 
If certain information is not mentioned in the text, leave the corresponding field blank.

you will recieve video transcript and some additional description from authors.

{
    'Author': 'Extracted author name from the text, if mentioned',
    'Language': 'The language in which the text is written, if specified',
    'Topics': 'The main themes or subjects of the text, identified through analysis',
    'Tags': 'Specific keywords or tags that are relevant to the text, identified from the content',
    'Year': 'The year related to the text, such as publication year or the year the described events occurred, if mentioned',
    'Title': 'The title of the idea, inferred from the text if applicable',
    'Description': 'A brief description of the idea, based on the text',
    'Content URL': 'If the text mentions or implies a source URL for more content, provide it here',
    'Thumbnail': 'A mention or description of a thumbnail image, if the text provides clues about it',
    'Transcript': 'Any detailed transcript mentioned or alluded to in the text, related to the idea',
}

This task requires attentive reading of the text to identify and extract information that aligns with each field listed. Some fields may not be applicable depending on the text provided.
"""


def get_tags(text: str, model: str = "gpt-3.5-turbo"):

    messages = []
    messages.append({
        "role": "system",
        "content": tags_prompt
    })
    messages.append({
        "role": "user",
        "content": text
    })
    
    completion = GPT_CLIENT.chat.completions.create(
        model = model,
        messages = messages)
    
    tags = completion.choices[0].message.content
    return tags
