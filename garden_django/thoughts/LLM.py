import os
from openai import AzureOpenAI, OpenAI

# Convert the environment variable to a boolean
USE_AZURE = os.getenv('USE_AZURE', 'False').lower() in ('true', '1', 't')

ENDPOINT = os.getenv('GPT_ENDPOINT', 'https://omc-ia-advertising.openai.azure.com')
API_KEY = os.getenv('GPT_API_KEY')
DEPLOYMENT = os.getenv('GPT_DEPLOYMENT', "")

# Adjust the default embedding model based on the desired default behavior
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', "text-embedding-ada-002")


def get_client(user):
    api_key = get_api_key(user)
    if USE_AZURE:
        return AzureOpenAI(
            api_key=api_key,
            azure_endpoint=ENDPOINT,
            api_version=DEPLOYMENT
        )
    else:
        return OpenAI(api_key=api_key)

def get_api_key(user):
    if user.use_system_api_key:
        api_key = os.getenv('GPT_API_KEY')
        if not api_key:
            raise ValueError("No system API key available")
        return api_key
    else:
        if not user.api_key:
            raise ValueError("No user API key available")
        return user.api_key



def get_embedding(text: str, user, model: str = EMBEDDING_MODEL, USE_AZURE=USE_AZURE):
    if len(str(text)) < 5 or len(str(text)) > 4000:
        return [0.0] * 1536 
    
    client = get_client(user)
    result = client.embeddings.create(model=model, input=str(text))
    return result.data[0].embedding


#Get Ideas tags from the text

tags_prompt = """
You are an assistant tasked with extracting the main tags from a text, focusing on specific information that aligns with predefined fields. Based on the text provided, you need to extract and fill in the following information in a dictionary format. If certain information is not mentioned in the text, leave the corresponding field blank.

Here is how you should extract the information, JSON format:

{
    "Author": "Extracted author name from the text, if mentioned",
    "Language": "The language in which the text is written, if specified",
    "Topics": "The main themes or subjects of the text, identified through analysis",
    "Tags": "Specific keywords or tags that are relevant to the text, identified from the content",
    "Year": "The year related to the text, such as publication year or the year the described events occurred, if mentioned",
    "Title": "The title of the idea, inferred from the text if applicable",
    "Description": "A brief description of the idea, based on the text",
    "Content URL": "If the text mentions or implies a source URL for more content, provide it here",
}
This task requires attentive reading of the text to identify and extract information that aligns with each field listed. Some fields may not be applicable depending on the text provided.
"""


def get_tags(text: str, user,  model: str = "gpt-3.5-turbo"):
    client = get_client(user)

    messages = []
    messages.append({
        "role": "system",
        "content": tags_prompt
    })
    messages.append({
        "role": "user",
        "content": text
    })
    
    completion = client.chat.completions.create(
        model=model,
        messages=messages
    )
    
    tags = completion.choices[0].message.content

    return tags

def get_user_intent(user_message: str, user) -> str:
    client = get_client(user)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"The user says: '{user_message}'. What do they want to do? \
             Options: they can upload new content by files, youtube links, or text. They can also search for a text. List seeds, seed detail or find similar. Also they can search.\
             Your goal to return the action they want to do. Commands are: \
             list seeds, create seed, search, find similar, process youtube, upload file, seed detail, search"}
        ],
        max_tokens=5000
    )
    action = response['choices'][0]['message']['content'].strip().lower()
    return action