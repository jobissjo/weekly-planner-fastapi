import os
from typing import List, Optional

from fastapi import APIRouter, Depends
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Langchain imports
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.permissions import any_user_role
from app.core.settings import setting
from app.models.user import User
from app.schemas.common_schema import BaseResponse

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatQuery(BaseModel):
    message: str
    chat_history: Optional[List[ChatMessage]] = None
    current_date: Optional[str] = None


class ChatReply(BaseModel):
    reply: str


@router.post("/chat", response_model=BaseResponse[ChatReply])
async def chat_with_bot(data: ChatQuery, current_user: User = Depends(any_user_role)):
    """
    Chat with the Weekly Planner AI bot.
    Allows the user to manage their tasks in natural language.
    Strictly isolated: one user cannot ask or get another user's tasks.
    """
    # 1. Resolve LLM API keys & instantiate model
    openai_key = setting.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY")
    gemini_key = setting.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    groq_key = setting.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")

    llm = None
    if setting.LLM_PROVIDER == "google" and gemini_key:
        llm = ChatGoogleGenerativeAI(
            model=setting.GEMINI_MODEL_NAME, google_api_key=gemini_key, temperature=0.3
        )
    elif setting.LLM_PROVIDER == "groq" and groq_key:
        llm = ChatGroq(model=setting.GROQ_MODEL_NAME, api_key=groq_key, temperature=0.3)
    elif openai_key:
        llm = ChatOpenAI(
            model=setting.OPENAI_MODEL_NAME, api_key=openai_key, temperature=0.3
        )
    elif gemini_key:
        llm = ChatGoogleGenerativeAI(
            model=setting.GEMINI_MODEL_NAME, google_api_key=gemini_key, temperature=0.3
        )
    elif groq_key:
        llm = ChatGroq(model=setting.GROQ_MODEL_NAME, api_key=groq_key, temperature=0.3)

    if not llm:
        return BaseResponse(
            status="error",
            message="No LLM API keys configured. Set OPENAI_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY in .env.",
            data=ChatReply(
                reply="I'm sorry, but my chatbot brain is offline. Please configure `OPENAI_API_KEY`, `GEMINI_API_KEY`, or `GROQ_API_KEY` in the server's `.env` file to activate me!"
            ),
        )

    # 2. Build dynamic Langchain tools bound strictly to the current user
    from app.services import mcp_tools

    @tool
    async def create_task(
        title: str,
        date: str,
        startTime: str,
        endTime: str,
        priority: str = "medium",
        description: Optional[str] = None,
    ) -> str:
        """
        Create a new task for the current user.
        - title: Title of the task
        - date: Date in YYYY-MM-DD format
        - startTime: Start time in HH:mm format
        - endTime: End time in HH:mm format
        - priority: Priority, one of 'high', 'medium', 'low'
        - description: Optional description of the task
        """
        return await mcp_tools.create_task_tool(
            user=current_user,
            title=title,
            date=date,
            startTime=startTime,
            endTime=endTime,
            priority=priority,
            description=description,
        )

    @tool
    async def list_my_tasks(
        from_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> str:
        """
        List tasks belonging to the current user.
        - from_date: Optional filter in YYYY-MM-DD format
        - end_date: Optional filter in YYYY-MM-DD format
        """
        return await mcp_tools.list_my_tasks_tool(
            user=current_user, from_date=from_date, end_date=end_date
        )

    @tool
    async def get_task_by_title(title: str) -> str:
        """
        Search for tasks matching a given title/name for the current user.
        - title: Title of the task to search for
        """
        return await mcp_tools.get_task_by_title_tool(user=current_user, title=title)

    @tool
    async def update_task(
        task_id: str,
        title: Optional[str] = None,
        date: Optional[str] = None,
        startTime: Optional[str] = None,
        endTime: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        description: Optional[str] = None,
        completedDate: Optional[str] = None,
        completionNotes: Optional[str] = None,
    ) -> str:
        """
        Update details of a task belonging to the current user.
        - task_id: The ID of the task to update
        - title: Optional new title
        - date: Optional new date in YYYY-MM-DD format
        - startTime: Optional new start time in HH:mm format
        - endTime: Optional new end time in HH:mm format
        - priority: Optional new priority (high, medium, low)
        - status: Optional new status (pending, completed, skipped)
        - description: Optional new description
        - completedDate: Optional date when the task was completed in YYYY-MM-DD format
        - completionNotes: Optional notes or achievements about the task's completion
        """
        return await mcp_tools.update_task_tool(
            user=current_user,
            task_id=task_id,
            title=title,
            date=date,
            startTime=startTime,
            endTime=endTime,
            priority=priority,
            status=status,
            description=description,
            completedDate=completedDate,
            completionNotes=completionNotes,
        )

    @tool
    async def mark_task_completed(
        task_id: str,
        completedDate: Optional[str] = None,
        completionNotes: Optional[str] = None,
    ) -> str:
        """
        Mark a task belonging to the current user as completed, optionally providing completion details.
        - task_id: The ID of the task to complete
        - completedDate: Optional date when the task was completed in YYYY-MM-DD format
        - completionNotes: Optional notes, thoughts, or achievements about the task's completion
        """
        return await mcp_tools.mark_task_completed_tool(
            user=current_user,
            task_id=task_id,
            completedDate=completedDate,
            completionNotes=completionNotes,
        )

    @tool
    async def delete_task(task_id: str) -> str:
        """
        Delete a task belonging to the current user.
        - task_id: The ID of the task to delete
        """
        return await mcp_tools.delete_task_tool(user=current_user, task_id=task_id)

    tools = [
        create_task,
        list_my_tasks,
        get_task_by_title,
        update_task,
        mark_task_completed,
        delete_task,
    ]

    # 3. Add admin tools if the caller has admin permissions
    from app.models.enums import UserRole

    if current_user.role == UserRole.ADMIN or current_user.is_superuser:

        @tool
        async def admin_list_all_tasks() -> str:
            """
            [ADMIN ONLY] List all tasks of all users in the system.
            """
            return await mcp_tools.admin_list_all_tasks_tool(user=current_user)

        @tool
        async def admin_get_users_by_name(name: str) -> str:
            """
            [ADMIN ONLY] Search for users in the system by name or email.
            - name: Query string (name or email fragment)
            """
            return await mcp_tools.admin_get_users_by_name_tool(
                user=current_user, name=name
            )

        tools.extend([admin_list_all_tasks, admin_get_users_by_name])

    # 4. Format chat history
    formatted_history = []
    if data.chat_history:
        for msg in data.chat_history:
            if msg.role == "user":
                formatted_history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                formatted_history.append(AIMessage(content=msg.content))

    # Resolve date context (fallback to server local time if not provided by frontend)
    import datetime

    try:
        if data.current_date:
            parsed_date = datetime.datetime.strptime(
                data.current_date, "%Y-%m-%d"
            ).date()
        else:
            parsed_date = datetime.date.today()
        user_date = parsed_date.isoformat()
        user_weekday = parsed_date.strftime("%A")
    except Exception:
        parsed_date = datetime.date.today()
        user_date = parsed_date.isoformat()
        user_weekday = parsed_date.strftime("%A")

    # 5. Build and execute agent prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are an intelligent weekly planner chatbot. You help the user manage their tasks.\n"
                    f"The current user's email is: {current_user.email}.\n"
                    f"The current user's name is: {current_user.first_name} {current_user.last_name}.\n"
                    f"The current user's role is: {current_user.role.value}.\n"
                    f"Today's date is: {user_date} ({user_weekday}).\n"
                    "You can create tasks, list them, search for them, update them, and delete them. "
                    "You can also mark tasks as completed, optionally specifying a completedDate and completionNotes.\n"
                    "You can only perform actions for the current user. "
                    "For administration features, you must verify the user has the admin role via tools.\n"
                    "CRITICAL CONSTRAINT: Do NOT mention technical implementation details, internal function names (e.g. 'list_my_tasks', 'create_task', etc.), or tools you are using under the hood in your responses to the user. "
                    "Always formulate your replies using natural, user-friendly language as a helpful personal assistant."
                ),
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    try:
        response = await agent_executor.ainvoke(
            {"input": data.message, "chat_history": formatted_history}
        )
        reply_content = response.get("output", "No response generated.")
        return BaseResponse(
            status="success",
            message="Chat message processed successfully",
            data=ChatReply(reply=reply_content),
        )
    except Exception as e:
        return BaseResponse(
            status="error",
            message=f"Error executing chatbot agent: {str(e)}",
            data=ChatReply(
                reply=f"An error occurred while processing your request: {str(e)}"
            ),
        )
