# Building a Fast AI Chatbot: Integrating Groq with Model Context Protocol (MCP) Tools in FastAPI

Imagine talking to a chatbot that doesn't just chat, but actually *does* things for you—like creating tasks, updating your calendar, or retrieving information—in less than a second. 

In this blog post, we will explore how to build a smart task-management chatbot. We will examine the actual backend codebase, showing how it uses **Groq** for fast AI processing, **Model Context Protocol (MCP)** to define standard tools, and **LangChain** to tie everything together in **FastAPI**.

---

## The Core Ingredients

Before looking at the code, let's understand the three main technologies we are using:

1. **Groq**: Groq is an AI acceleration platform. It runs Open Source Large Language Models (like Meta's Llama 3.3) at extreme speeds with very low latency. This makes chatbot conversations feel instant.
2. **Model Context Protocol (MCP)**: Developed by Anthropic, MCP is an open standard that allows developers to write "tools" (APIs) once, and expose them to any AI assistant (like Claude Desktop, Cursor, or your own custom chatbot).
3. **LangChain**: A framework that helps connect LLMs (like Groq) to external tools and manage conversation history.

---

## How the Backend is Organized

Our FastAPI project has three main layers that make this integration work:
1. **The MCP Server (`app/mcp_server.py`)**: Exposes our task-management tools to the outside world using the standardized MCP format.
2. **The Shared Tool Logic (`app/services/mcp_tools.py`)**: The database and business logic where tasks are created, read, updated, and deleted.
3. **The Chat Router (`app/routes/v1/chatbot_routes.py`)**: The FastAPI endpoint that uses Groq and LangChain to understand the user's chat message and call the right tools.

Let's look at how these parts are built.

---

### Step 1: Defining the MCP Server (`app/mcp_server.py`)

We use the lightweight `FastMCP` framework to build our MCP server. The server registers functions as tools using the `@mcp.tool()` decorator. 

Here is a simplified look at [app/mcp_server.py](file:///D:/Jobi%20Developement/Python/FastAPI/projects/weekly-planner-fastapi/app/mcp_server.py):

```python
from mcp.server.fastmcp import FastMCP
from app.services import mcp_tools

# Initialize the FastMCP server
mcp = FastMCP("WeeklyPlannerMCP")

@mcp.tool()
async def create_task(
    title: str,
    date: str,
    startTime: str,
    endTime: str,
    priority: str = "medium",
    description: str = None,
) -> str:
    """
    Create a new task for the authenticated user.
    """
    user = await get_mcp_user()
    return await mcp_tools.create_task_tool(
        user=user,
        title=title,
        date=date,
        startTime=startTime,
        endTime=endTime,
        priority=priority,
        description=description,
    )
```

#### Key Concept: Authentication
Because MCP tools can run via two different modes (CLI over `stdio` or HTTP over `SSE` streams), the backend checks both. It retrieves the current user either from a FastAPI middleware context variable (`mcp_user_var`) or from environment variables (`AUTH_TOKEN` or `MCP_USER_EMAIL`). This ensures that users can only modify their own data!

---

### Step 2: Shared Business Logic (`app/services/mcp_tools.py`)

Instead of writing database code twice, we keep the tool operations in a separate service layer at [app/services/mcp_tools.py](file:///D:/Jobi%20Developement/Python/FastAPI/projects/weekly-planner-fastapi/app/services/mcp_tools.py). 

These functions take the authenticated user and execute standard database operations. For example, here is the tool that lists tasks:

```python
async def list_my_tasks_tool(
    user: User, from_date: Optional[str] = None, end_date: Optional[str] = None
) -> str:
    try:
        tasks = await task_service.list_tasks(user.id, from_date, end_date)
        if not tasks:
            return "No tasks found."

        lines = []
        for t in tasks:
            lines.append(
                f"- [{t.status.value}] {t.title} on {t.date} from {t.startTime} to {t.endTime} (Priority: {t.priority.value}, ID: {t.id})"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing tasks: {str(e)}"
```

---

### Step 3: Connecting Groq and LangChain (`app/routes/v1/chatbot_routes.py`)

This is where the magic happens. When a user sends a chat message in the UI, it goes to the `/chatbot/chat` POST route in FastAPI. 

Here is a step-by-step breakdown of how [app/routes/v1/chatbot_routes.py](file:///D:/Jobi%20Developement/Python/FastAPI/projects/weekly-planner-fastapi/app/routes/v1/chatbot_routes.py) handles the request:

#### 1. Initializing Groq
The route checks the environment configuration. If the provider is set to `"groq"`, it instantiates LangChain's `ChatGroq` model:

```python
from langchain_groq import ChatGroq

groq_key = setting.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
llm = ChatGroq(model=setting.GROQ_MODEL_NAME, api_key=groq_key, temperature=0.3)
```

#### 2. Building Dynamic User-Bound Tools
To keep things secure, we wrap our database service functions inside LangChain's `@tool` decorator *inside* the API call. By doing this, we bind the `current_user` directly to the tools. The AI cannot accidentally access another user's tasks.

```python
from langchain_core.tools import tool

@tool
async def create_task(
    title: str,
    date: str,
    startTime: str,
    endTime: str,
    priority: str = "medium",
    description: Optional[str] = None,
) -> str:
    """Create a new task for the current user."""
    return await mcp_tools.create_task_tool(
        user=current_user,  # Bound strictly to the logged-in user!
        title=title,
        date=date,
        startTime=startTime,
        endTime=endTime,
        priority=priority,
        description=description,
    )
```

#### 3. Setting Up Chat History (Memory)
To make the conversation natural, we map the list of previous messages sent from the frontend into LangChain's `HumanMessage` and `AIMessage` classes:

```python
from langchain_core.messages import AIMessage, HumanMessage

formatted_history = []
if data.chat_history:
    for msg in data.chat_history:
        if msg.role == "user":
            formatted_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            formatted_history.append(AIMessage(content=msg.content))
```

#### 4. The System Prompt and Execution
We feed the LLM a system prompt explaining who it is (an intelligent weekly planner chatbot), details about the current user, and today's date. Then we run the agent:

```python
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an intelligent weekly planner chatbot. You help the user manage their tasks..."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the agent and runner
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Run the chatbot!
response = await agent_executor.ainvoke(
    {"input": data.message, "chat_history": formatted_history}
)
reply = response.get("output")
```

---

## Why This Architecture is So Good

1. **Dual Use**: Because our tasks are defined as MCP tools in `mcp_tools.py`, we get two bots in one. Our custom web app's chatbot can use them, *and* external tools like Cursor or Claude Desktop can connect to `mcp_server.py` to manage our tasks directly from the IDE or desktop client.
2. **Ironclad Security**: By building LangChain tools dynamically during the request context, we completely avoid data leaks between users.
3. **High Performance**: Combining Groq's high-speed inference (Llama 3.3) with LangChain's tool calling means tool decisions and replies happen in a fraction of a second.

---

## Summary

Integrating MCP tools with Groq and LangChain allows us to build powerful, secure, and fast chatbots in FastAPI. Instead of manually writing logic to parse user commands, the AI agent decides which database tools to call dynamically based on natural language. 

With this setup, users can simply type: *"Add a high-priority meeting tomorrow at 2 PM"* and the chatbot will automatically create the task for them!
