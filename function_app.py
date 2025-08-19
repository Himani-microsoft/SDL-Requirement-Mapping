import azure.functions as func
import logging
from azure.ai.agents.models import ListSortOrder
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.ai.agents import AgentsClient
import time
from azure.search.documents import SearchClient
import json


logging.basicConfig(level=logging.INFO)
app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
print("test")

@app.route(route="http_trigger_2")


def http_trigger_2(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    user_input = req.params.get('user_input')
    if not user_input:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            user_input = req_body.get('user_input')

    if user_input:
        logging.info(f"Received user_input: {user_input}")
        resp = invoke_agent(user_input)
        return func.HttpResponse(f"{resp}")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a user_input in the query string or in the request body for a personalized response.",
             status_code=200
        )
    

def search_index(index_name, user_input):
   
    # Replace with your Azure AI Search service endpoint and index name
    search_service_endpoint = "https://getsecurepirsearch.search.windows.net"

    # Create a SearchClient
    search_client = SearchClient(endpoint=search_service_endpoint, index_name=index_name, credential=DefaultAzureCredential())

    # Perform a search query
    search_results = search_client.search(user_input)
    logging.info(f"Search results for '{user_input}': {search_results}")

    results_list = []
    for result in search_results:
        # Convert result to dict (SearchDocument is already dict-like)
        results_list.append(dict(result))
    sdl_context_json = json.dumps(results_list[:10], indent=2, default=str)
    logging.info(f"JSON dumps results for '{user_input}': {sdl_context_json}")
    return sdl_context_json

    
def invoke_agent(user_input):
    try:
        credential = DefaultAzureCredential()  
        project_client = AIProjectClient(
            endpoint="https://gotagripfoundry.services.ai.azure.com/api/projects/foundryProject",
            credential=credential
        )
        
        logging.info("AIProjectClient initialized successfully.")

        agent_id = "asst_jiY0SSIgNefYeB89YIyqK7p9"

        agent = project_client.agents.get_agent(
            agent_id=agent_id
        )

        logging.info(f"Agent retrieved: {agent.name} (ID: {agent.id})")

        index_result = search_index("pirsdlrequirementvectordata", user_input)
        logging.info(f"This is index result {index_result})")
        
        # Step 1: Create a thread and run
        run = project_client.agents.create_thread_and_run(
            agent_id=agent_id,
            body={
                "assistant_id": agent_id,
                "thread": {
                    "messages": [
                        {
                            "role": "user",
                            "content": index_result
                        }
                    ]
                }
            }
        )

        logging.info(f"Run created with ID: {run.id}")

        # Step 2: Poll until the run completes
        while run.status not in ["completed", "failed", "cancelled"]:
            time.sleep(1)
            run = project_client.agents.runs.get(run.thread_id, run.id)
            project_client.agents.messages

        # Step 3: Retrieve messages from the thread
        messages = project_client.agents.messages.list(run.thread_id)

        logging.info(f"Messages retrieved for thread ID: {run.thread_id}")

        response = ""
        for message in messages:
            if message.role == "assistant":
                logging.info(f"Assistant message: {message.content}")
                response = message.content

        return_value = ""
        for item in response:
            if hasattr(item, 'text'):
                return_value = item.text.value
        
        logging.info(f"Final response: {return_value}")

        return return_value
    
    except Exception as e:
        logging.error(f"Error in invoke_agent: {e}")
        return f"Error in invoke_agent: {e}"
    
#invoke_agent("cross-site scripting")