import json
import os
from typing import Any
import requests
from openai import OpenAI
import json
from dotenv import load_dotenv, find_dotenv
from openai.types.beta import Assistant
from openai.types.beta.threads.run import Run
import time
import streamlit as st
import requests
import os

FMP_API_KEY: str | None = os.environ.get("FMP_API_KEY")

_ : bool = load_dotenv(find_dotenv()) 
client : OpenAI = OpenAI()

def process_run_status(thread_id, run_id, available_functions):
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        run_steps = client.beta.threads.runs.steps.list(thread_id=thread_id, run_id=run_id)

        if run_status.status == "requires_action":
            if run_status.required_action.submit_tool_outputs and run_status.required_action.submit_tool_outputs.tool_calls:
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []

                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"Calling {function_name} with arguments {function_args}")

                    if function_name in available_functions:
                        function_to_call = available_functions[function_name]
                        output = function_to_call(**function_args)
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": output,
                        })

                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=tool_outputs
                )

        elif run_status.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            print(messages)
            full_response = process_message_with_citations(messages)
            print(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

            with st.chat_message("assistant"):
                st.markdown(full_response, unsafe_allow_html=True)

            for message in messages.data:
                if hasattr(message.content[0], 'text'):
                    role_label = "User" if message.role == "user" else "Assistant"
                    
            break 

        elif run_status.status == "failed":
            print("Run failed.")
            print(f"Unexpected status: {run_status.status}")
            break

        elif run_status.status in ["in_progress", "queued"]:
            print(f"Run is {run_status.status}. Waiting...")
            time.sleep(5)

        else:
            print(f"Unexpected status: {run_status.status}")
            break








def download_save_display_image(file_id: str) -> None:
    image_data = client.files.content(file_id)
    image_data_bytes = image_data.read()
    image_save_path = f"image_{file_id}.png"

    with open(image_save_path, "wb") as file:
        file.write(image_data_bytes)
        image_save_path_1 = f"image_{file_id}.png"
        st.image(image_save_path_1, caption="AI generated Image", use_column_width=True)




def process_message_with_citations(messages):
    """Extract content and annotations from the messages and format citations as footnotes."""
    result_list = []

    for message in messages:
        message_content = message.content[0] if message.content else None
        citations = []
        image_contents = []
        annotations = []

        if message_content:
            if hasattr(message_content, 'image_file'):
                file_id = message_content.image_file.file_id
                download_save_display_image(file_id)
                image_contents.append(file_id)
            elif hasattr(message_content, 'text'):
                annotations = message_content.annotations if hasattr(message_content, 'annotations') else []

        for index, annotation in enumerate(annotations):
            if annotation.type == 'text' and hasattr(message_content, 'text'):
                message_content.text.value = message_content.text.value.replace(annotation.text.value, f'[{index + 1}]')
            elif annotation.type == 'file_citation':
                cited_file = {'filename': 'cited_document.pdf'}
                citations.append(f'[{index + 1}] {annotation.quote} from {cited_file["filename"]}')
            elif annotation.type == 'file_path':
                cited_file = {'filename': 'downloaded_document.pdf'}
                citations.append(f'[{index + 1}] Click [here](#) to download {cited_file["filename"]}')

        if hasattr(message_content, 'text'):
            full_response = message_content.text.value + '\n\n' + '\n'.join(citations)
        else:
            full_response = '\n'.join(citations)

        result_list.append((full_response, image_contents))

    return result_list



def get_balance_sheet(ticker, period, limit):
    url = f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}?period={period}&limit={limit}&apikey={FMP_API_KEY}"
    response = requests.get(url)
    return json.dumps(response.json())

available_functions = {
   
    "get_balance_sheet": get_balance_sheet,
 
}
assistant:Assistant = client.beta.assistants.create(
      instructions="Act as a financial analyst by accessing detailed financial data through the Financial Modeling Prep API. Your capabilities include analyzing key metrics, comprehensive financial statements, vital financial ratios, and tracking financial growth trends. ",
   
     model="gpt-3.5-turbo-16k",
      
  tools=[ {"type": "code_interpreter"},
           
            {"type": "function", "function": {"name": "get_balance_sheet", "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}, "period": {"type": "string"}, "limit": {"type": "integer"}}}}},
           
           
          ])

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

    run : Run= client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )
    process_run_status(thread.id, run.id, available_functions)


# prompt:Could you please compare the financial health of Microsoft and Apple over the past four years, 
# with a focus on their balance sheets and key financial ratios? It would be helpful if you could visualize the 
# data by creating a graph and presenting it as an image. Additionally, could you provide the data in text format? 