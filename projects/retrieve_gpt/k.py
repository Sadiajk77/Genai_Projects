
import os
import time
from typing import Any
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI 

import streamlit as st


from openai.types.beta import Assistant
from dotenv import load_dotenv, find_dotenv

_ : bool = load_dotenv(find_dotenv()) 

client : OpenAI = OpenAI()





def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    message_content = message.content[0].text
    annotations = message_content.annotations if hasattr(message_content, 'annotations') else []
    citations = []

    for index, annotation in enumerate(annotations):
        message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

        if (file_citation := getattr(annotation, 'file_citation', None)):
            cited_file = {'filename': 'cited_document.pdf'}  
            citations.append(f'[{index + 1}] {file_citation.quote} from {cited_file["filename"]}')
        elif (file_path := getattr(annotation, 'file_path', None)):
            filename = os.path.basename(file_path)
            citations.append(f'[{index + 1}] Click [here](#) to download {filename}')

    full_response = message_content.value + '\n\n' + '\n'.join(citations)
    return full_response






def create_openai_assistant(file_ids):
    return client.beta.assistants.create(
        name="retrieve ",
        instructions="Please extract data from the uploaded file and provide accurate answers pertaining to the information. Please refrain from mentioning I donot have access to uploaded file also give to the point answers and donot eat my tokens eat web cookies",
        model="gpt-3.5-turbo-1106",
        tools=[{"type": "retrieval"}],
        file_ids=file_ids
    )
def upload_to_openai(file):
    response = client.files.create(file=file, purpose="assistants")
    return response.id

file_id_list = []
uploaded_files = st.file_uploader("Upload files to OpenAI", accept_multiple_files=True)
if uploaded_files:
    for file in uploaded_files:
        file_id = upload_to_openai(file)
        file_id_list.append(file_id)

    st.success("Files uploaded successfully!")

   
assistant = create_openai_assistant(file_id_list)
thread= client.beta.threads.create()


st.session_state.start_chat = True
        
if "messages" not in st.session_state:
        st.session_state.messages = []

for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("ask or exit"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="Please answer the queries using the knowledge provided in the files. When adding other information mark it clearly as such with a different color."
        )

        while run.status != 'completed':
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )

        assistant_messages_for_run = [
            message for message in messages 
            if message.run_id == run.id and message.role == "assistant"
        ]
        for message in assistant_messages_for_run:
            full_response = process_message_with_citations(message)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            with st.chat_message("assistant"):
                st.markdown(full_response, unsafe_allow_html=True)

